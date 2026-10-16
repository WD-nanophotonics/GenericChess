"""A failed nested legality probe must not become a partial feature vector."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
from dataclasses import replace

import pytest

from generic_chess import compile_ruleset_for_execution
from generic_chess.ai.limits import SearchLimits
from generic_chess.native import native_available, semantic as sem
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.mirror import expected_snapshot
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.session.session import GameSession
import phase19b3_s4_fixtures as s4


@pytest.fixture(scope="module")
def feature_fault_kernel(tmp_path_factory):
    if os.name != "nt" or not native_available():
        pytest.skip("optional Windows Native fault build")
    spec = importlib.util.find_spec("ziglang")
    if spec is None:
        pytest.skip("Zig unavailable")
    source = Path(__file__).resolve().parents[2] / "generic_chess/_native"
    out = tmp_path_factory.mktemp("native-feature-fault")
    module = (source / "native_module.c").read_text(encoding="utf-8")
    specs = (
        ("gc_semantic_probe_material", "const GCSemanticRules *r,const GCSemanticPosition *p,const GCSemanticProbeProfile *profile,const int *dynamic", "r,p,profile,dynamic"),
        ("gc_semantic_dynamic_feature_vector", "const GCSemanticRules *r,const GCSemanticPosition *p,int out[3]", "r,p,out"),
        ("gc_semantic_spatial_feature_vector", "const GCSemanticRules *r,const GCSemanticPosition *p,int *occupancy,int control[GC_SEMANTIC_SPATIAL_CELLS]", "r,p,occupancy,control"),
    )
    globals_code = """
int gc_test_feature_fault=0,gc_test_feature_scope=0,gc_test_feature_failures=0;
static PyObject *gc_test_feature_set(PyObject *self,PyObject *args) {
 (void)self;if(!PyArg_ParseTuple(args,"p",&gc_test_feature_fault))return NULL;
 gc_test_feature_failures=0;Py_RETURN_NONE;
}
static PyObject *gc_test_public_scope(PyObject *self,PyObject *args) {
 (void)self;if(!PyArg_ParseTuple(args,"p",&gc_test_feature_scope))return NULL;
 Py_RETURN_NONE;
}
static PyObject *gc_test_feature_get(PyObject *self,PyObject *args) {
 (void)self;(void)args;return PyLong_FromLong(gc_test_feature_failures);
}
"""
    start = module.index("static int gc_semantic_probe_material(")
    module = module[:start] + globals_code + module[start:]
    for name, signature, arguments in specs:
        needle = "static int " + name + "("
        start = module.index(needle)
        # Skip the dynamic function's forward declaration.
        if module.index(";", start) < module.index("{", start):
            start = module.index(needle, start + 1)
        end = module.index("\nstatic ", start + 1)
        body = module[start:end].replace(name + "(", name + "_test_impl(", 1)
        wrapper = ("\nstatic int " + name + "(" + signature + ") {\n"
                   " int was=gc_test_feature_scope;gc_test_feature_scope=1;\n"
                   " int ok=" + name + "_test_impl(" + arguments + ");\n"
                   " gc_test_feature_scope=was;return ok;\n}\n")
        module = module[:start] + body + wrapper + module[end:]
    needle = '    {"semantic_dynamic_features", gc_semantic_dynamic_features, METH_VARARGS,'
    module = module.replace(needle,
        '    {"test_feature_set",gc_test_feature_set,METH_VARARGS,"Private fault"},\n'
        '    {"test_public_scope",gc_test_public_scope,METH_VARARGS,"Private public scope"},\n'
        '    {"test_feature_failures",gc_test_feature_get,METH_NOARGS,"Private count"},\n' + needle)
    runtime = (source / "native_semantic_runtime.c").read_text(encoding="utf-8")
    needle = "static int semantic_has_s3_reply(const GCSemanticRules *r, const GCSemanticPosition *position) {"
    assert runtime.count(needle) == 1
    runtime = runtime.replace(needle, needle + """
 extern int gc_test_feature_fault,gc_test_feature_scope,gc_test_feature_failures;
 if(gc_test_feature_fault && gc_test_feature_scope && !gc_test_feature_failures) {
   gc_test_feature_failures++;return -1;
 }
""")
    (out / "native_module.c").write_text(module, encoding="utf-8")
    (out / "native_semantic_runtime.c").write_text(runtime, encoding="utf-8")
    binary = out / ("_native_core" + sysconfig.get_config_var("EXT_SUFFIX"))
    command = [str(Path(spec.origin).parent / "zig.exe"), "cc", "-target",
               "x86_64-windows-gnu", "-shared", "-O2",
               "-I" + sysconfig.get_path("include"), "-I" + str(source),
               "-L" + str(Path(sys.base_prefix) / "libs"), "-lpython312"]
    command += [str(out / f.name if f.name in {"native_module.c", "native_semantic_runtime.c"} else f)
                for f in sorted(source.glob("*.c"))]
    command += ["-o", str(binary)]
    built = subprocess.run(command, capture_output=True, timeout=180,
                           env=dict(os.environ, ZIG_GLOBAL_CACHE_DIR=str(out / "zig-cache")))
    assert built.returncode == 0, built.stderr.decode(errors="replace")
    spec = importlib.util.spec_from_file_location("feature_fault._native_core", binary)
    kernel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kernel)
    return kernel


def compact_constant(compiled, rules):
    count = len(rules.type_ids)
    aux = sum((1 if slot.value_kind == "bool" else 3) * (1 if slot.scope == "global" else 2)
              for slot in compiled.ir.aux_slots)
    dimension = 2 * count * compiled.board_size ** 2 + 2 * count + 5 + aux
    return dict(input_mean=[0.0] * dimension, input_scale=[1.0] * dimension,
                target_scale=1.0, hidden_weights=[[0.0] * dimension for _ in range(16)],
                hidden_bias=[0.0] * 16, output_weights=[0.0] * 16,
                output_bias=2.0, width=16, hand_type_indices=list(range(count)))


@pytest.mark.parametrize("builder,position_for", (
    (s4.multiple_replies_ruleset, s4.multiple_replies_position),
    (s4.full_child_state_ruleset, s4.full_child_state_position),
))
@pytest.mark.parametrize("path", ("dynamic", "spatial", "linear", "localized", "compact", "mixed_control"))
def test_nested_failure_refuses_features_and_partial_evaluation(
    feature_fault_kernel, builder, position_for, path,
):
    kernel = feature_fault_kernel
    compiled = compile_semantic_ruleset(builder())
    rules = compile_native_semantic_rules(compiled, backend_module=kernel)
    position = position_for(compiled.support)
    payload = dict(expected_snapshot(position, rules, compiled), ply=0)
    payload["board"] = [None if p is None else list(p) for p in payload["board"]]
    payload["hands"] = [list(h) for h in payload["hands"]]
    packed = sem.pack_position(rules, payload)
    before = sem.snapshot(rules, packed)
    operations = {
        "dynamic": lambda: sem.dynamic_features(rules, packed),
        "spatial": lambda: sem.spatial_features(rules, packed),
        "linear": lambda: sem.evaluate(rules, packed, dynamic_values=(2, 3, 5)),
        "localized": lambda: sem.evaluate(rules, packed, localized_control_values=(1, -1, 0, 0, 0, 0, 0, 0, 0)),
        "mixed_control": lambda: sem.evaluate(rules, packed, dynamic_values=(2,3,5), localized_control_values=(1,-1,0,0,0,0,0,0,0)),
        "compact": lambda: sem.evaluate(rules, packed, compact_values=compact_constant(compiled, rules)),
    }
    kernel.test_feature_set(False)
    baseline = operations[path]()
    kernel.test_feature_set(True)
    try:
        with pytest.raises(RuntimeError, match="feature extraction failed"):
            operations[path]()
        assert kernel.test_feature_failures() == 1
        assert operations[path]() == baseline  # one-shot fault; real retry
    finally:
        kernel.test_feature_set(False)
    assert sem.snapshot(rules, packed) == before


@pytest.mark.parametrize("q", (0, 1))
@pytest.mark.parametrize("profile", ("linear", "compact", "both", "localized", "mixed_control"))
def test_feature_failure_cannot_be_a_completed_search(feature_fault_kernel, q, profile):
    definition = s4.multiple_replies_ruleset()
    support = compile_semantic_ruleset(definition).support
    position = s4.multiple_replies_position(support)
    rows = tuple(tuple(position.board[r*5:(r+1)*5]) for r in range(5))
    compiled = compile_ruleset_for_execution(replace(definition, initial_position=rows))
    session = GameSession(compiled)
    kernel = feature_fault_kernel
    rules = compile_native_semantic_rules(compiled, backend_module=kernel)
    kwargs = {}
    if profile in ("localized", "mixed_control"):
        kwargs["localized_control_values"] = (1, -1, 0, 0, 0, 0, 0, 0, 0)
    if profile in ("linear", "both", "mixed_control"):
        kwargs["dynamic_values"] = (2, 3, 5)
    if profile in ("compact", "both"):
        kwargs["compact_values"] = compact_constant(compiled, rules)
    engine = SemanticSearchEngine(compiled, rules, tt_megabytes=0,
                                  ordering_cache_enabled=False, **kwargs)
    limits = SearchLimits(max_depth=2, max_nodes=4096, max_time_seconds=None,
                          quiescence_max_depth=q, quiescence_hard_max_depth=8 if q else 0)
    before, witnesses = session.state, session._search_witnesses
    kernel.test_feature_set(True)
    try:
        try:
            failed = engine.search(session, limits, root_window_pruning=True)
        except RuntimeError as exc:
            assert "feature" in str(exc)
        else:
            assert failed.termination_reason == "internal_error"
            assert failed.completed_depth < 2
            assert failed.action is None or failed.action in session.legal_actions()
        assert kernel.test_feature_failures() == 1
    finally:
        kernel.test_feature_set(False)
    retried = engine.search(session, limits, root_window_pruning=True)
    cold = SemanticSearchEngine(compiled, rules, tt_megabytes=0,
                               ordering_cache_enabled=False, **kwargs).search(
                                   session, limits, root_window_pruning=True)
    assert (retried.action, retried.score, retried.principal_variation) == (
        cold.action, cold.score, cold.principal_variation)
    assert session.state is before and session._search_witnesses is witnesses


@pytest.mark.parametrize("builder,position_for", (
    (s4.multiple_replies_ruleset, s4.multiple_replies_position),
    (s4.full_child_state_ruleset, s4.full_child_state_position),
))
@pytest.mark.parametrize("path", (
    "guarded", "guarded_audit", "transient", "transient_audit", "subset", "checked",
))
def test_public_legality_never_returns_partial_set_after_nested_failure(
    feature_fault_kernel, builder, position_for, path,
):
    kernel = feature_fault_kernel
    compiled = compile_semantic_ruleset(builder())
    rules = compile_native_semantic_rules(compiled, backend_module=kernel)
    position = position_for(compiled.support)
    payload = dict(expected_snapshot(position, rules, compiled), ply=0)
    payload["board"] = [None if p is None else list(p) for p in payload["board"]]
    payload["hands"] = [list(h) for h in payload["hands"]]
    packed = sem.pack_position(rules, payload)
    before = sem.snapshot(rules, packed)
    candidates = sem.candidate_actions(rules, packed)
    legal = sem.guarded_actions(rules, packed)
    def checked_children():
        return tuple(sem.snapshot(rules, sem.make_checked(rules, packed, a))
                     for a in legal)
    operations = {
        "guarded": lambda: sem.guarded_actions(rules, packed),
        "guarded_audit": lambda: sem.guarded_actions_audit(rules, packed),
        "transient": lambda: sem.transient_legal_actions(rules, packed),
        "transient_audit": lambda: sem.transient_legal_actions_audit(rules, packed),
        "subset": lambda: sem.transient_legal_subset(rules, packed, candidates),
        "checked": checked_children,
    }
    baseline = operations[path]()
    kernel.test_feature_set(True)
    kernel.test_public_scope(True)
    try:
        with pytest.raises(RuntimeError, match="required checked transition"):
            operations[path]()
        assert kernel.test_feature_failures() == 1
        assert operations[path]() == baseline
    finally:
        kernel.test_public_scope(False)
        kernel.test_feature_set(False)
    assert sem.snapshot(rules, packed) == before
    assert sem.guarded_actions(rules, packed) == legal


@pytest.mark.parametrize("builder,position_for", (
    (s4.multiple_replies_ruleset, s4.multiple_replies_position),
    (s4.full_child_state_ruleset, s4.full_child_state_position),
))
@pytest.mark.parametrize("strict", (False, True))
def test_actual_provider_negative_status_selects_explicit_contract(
    feature_fault_kernel, builder, position_for, strict,
):
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.core.identity import repetition_identity_key
    from generic_chess.core.position import GameState, HistoryRecord
    from generic_chess.core.search_runtime import SearchPathRuntime
    from generic_chess.core.semantic_executor import semantic_engine_for
    from generic_chess.core.terminal import TerminalResult, TerminalStatus
    from generic_chess.core.transition import legal_actions, apply_action
    kernel = feature_fault_kernel
    compiled = compile_semantic_ruleset(builder())
    position = position_for(compiled.support)
    key = repetition_identity_key(position, compiled)
    # Imported S4 specification root, not a claimed played trajectory.
    state = GameState(position, 0, ((key, 1),), TerminalResult(TerminalStatus.ONGOING),
                      (HistoryRecord(key, -1, "", False),))
    expected = set(legal_actions(state, compiled))
    assert expected
    rules = compile_native_semantic_rules(compiled, backend_module=kernel)
    provider = NativeSemanticLegalityProvider(compiled, semantic_engine_for(compiled),
                                              rules, strict=strict)
    runtime = SearchPathRuntime.from_state(state, compiled,
        history_witnesses=(position,), legal_binding_provider=provider)
    kernel.test_feature_set(True)
    kernel.test_public_scope(True)
    try:
        if strict:
            with pytest.raises(RuntimeError, match="required checked transition"):
                runtime.legal_actions()
            assert runtime.legal_provider_operational_failures == 0
            assert runtime.legal_provider_fallbacks == 0
        else:
            assert set(runtime.legal_actions()) == expected
            assert runtime.legal_provider_operational_failures == 1
            assert runtime.legal_provider_fallbacks == 1
            assert not runtime._legal_provider_active
        assert kernel.test_feature_failures() == 1
        assert set(runtime.legal_actions()) == expected
    finally:
        kernel.test_public_scope(False)
        kernel.test_feature_set(False)
    selected = runtime.legal_actions()[0]
    child = apply_action(state, selected, compiled)
    with runtime.pushed(selected):
        assert runtime.position == child.position
        assert runtime.terminal_status == child.terminal_status
    runtime.assert_balanced()
    assert runtime.position is state.position and runtime.depth == 0
