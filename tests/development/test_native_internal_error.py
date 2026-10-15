"""Observed Native identity failures must not become completed empty searches.

The optional Windows/Zig fixture builds the current source with a private,
ordering-scoped serializer fault. No fault hook is shipped in the product.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

import pytest

import generic_chess.native as native
from generic_chess import compile_ruleset_for_execution
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


@pytest.fixture(scope="module")
def fault_kernel(tmp_path_factory):
    if os.name != "nt" or not native.native_available():
        pytest.skip("optional Windows Native fault-build regression")
    spec = importlib.util.find_spec("ziglang")
    if spec is None:
        pytest.skip("Zig is required for the private fault build")
    zig = Path(spec.origin).parent / "zig.exe"
    if not zig.is_file():
        pytest.skip("Windows Zig executable unavailable")
    root = Path(__file__).resolve().parents[2]
    source = root / "generic_chess" / "_native"
    out = tmp_path_factory.mktemp("native-ordering-error")
    module = (source / "native_module.c").read_text(encoding="utf-8")
    start = module.index("static int gc_semantic_order_actions(")
    end = module.index("\nstatic ", start + 1)
    original = module[start:end].replace(
        "gc_semantic_order_actions(", "gc_test_order_actions_impl(", 1
    )
    wrapper = """
int gc_test_key_failure = 0;
static int gc_test_fault_enabled = 0;
static int gc_semantic_order_actions(GCSemanticIterativeContext *ctx,
    GCSemanticPosition *position, uint32_t ply, uint32_t depth,
    GCSemanticActionBuffer *actions) {
    gc_test_key_failure = gc_test_fault_enabled;
    int result = gc_test_order_actions_impl(ctx, position, ply, depth, actions);
    gc_test_key_failure = 0;
    return result;
}
static PyObject *gc_test_set_fault(PyObject *self, PyObject *args) {
    (void)self; int enabled;
    if (!PyArg_ParseTuple(args, "p", &enabled)) return NULL;
    gc_test_fault_enabled = enabled; Py_RETURN_NONE;
}
"""
    module = module[:start] + original + wrapper + module[end:]

    # A second observed chain reaches the same failure through terminal
    # availability rather than sorting. Count root calls before injecting.
    start = module.index("static int gc_semantic_has_guarded_action_impl(")
    end = module.index("\nstatic ", start + 1)
    original = module[start:end].replace(
        "gc_semantic_has_guarded_action_impl(", "gc_test_availability_impl(", 1)
    wrapper = """
static int gc_test_root_ply=0, gc_test_root_visits=0, gc_test_avail_after=999999;
static int gc_semantic_has_guarded_action_impl(const GCSemanticRules *rules,
    const GCSemanticPosition *position, int *ok, GCSemanticRuntimeAudit *audit) {
    extern int gc_test_key_failure;
    if(position->ply==gc_test_root_ply)gc_test_root_visits++;
    gc_test_key_failure=position->ply==gc_test_root_ply &&
        gc_test_root_visits>=gc_test_avail_after;
    int result=gc_test_availability_impl(rules,position,ok,audit);
    gc_test_key_failure=0;return result;
}
static PyObject *gc_test_set_avail(PyObject *self, PyObject *args) {
    (void)self;
    if(!PyArg_ParseTuple(args,"ii",&gc_test_root_ply,&gc_test_avail_after))return NULL;
    extern int gc_test_key_failures;
    gc_test_root_visits=0;gc_test_key_failures=0;Py_RETURN_NONE;
}
static PyObject *gc_test_avail_count(PyObject *self, PyObject *args) {
    (void)self;(void)args;extern int gc_test_key_failures;
    return Py_BuildValue("(ii)",gc_test_root_visits,gc_test_key_failures);
}
"""
    module = module[:start] + original + wrapper + module[end:]
    # The q0 exact-root search now also uses a fully rechecked reply hint.
    # Inject at that real availability consumer too; retain the nested
    # serializer failure and every original recovery/state assertion.
    start = module.index("static int gc_quiet_reply_available(")
    end = module.index("\nstatic ", start + 1)
    original = module[start:end].replace(
        "gc_quiet_reply_available(", "gc_test_reply_available_impl(", 1)
    wrapper = """
static int gc_quiet_reply_available(const GCSemanticRules *rules,
    const GCSemanticPosition *position, int *ok, uint64_t *action, int *have) {
    extern int gc_test_key_failure;
    if(position->ply==gc_test_root_ply)gc_test_root_visits++;
    gc_test_key_failure=position->ply==gc_test_root_ply &&
        gc_test_root_visits>=gc_test_avail_after;
    int result=gc_test_reply_available_impl(rules,position,ok,action,have);
    gc_test_key_failure=0;return result;
}
"""
    module = module[:start] + original + wrapper + module[end:]
    needle = '    {"semantic_make_checked", gc_semantic_make_checked, METH_VARARGS,'
    assert module.count(needle) == 1
    module = module.replace(
        needle, '    {"test_set_fault", gc_test_set_fault, METH_VARARGS,'
        ' "Private ordering serializer fault"},\n'
        '    {"test_set_availability_fault",gc_test_set_avail,METH_VARARGS,"Private availability"},\n'
        '    {"test_availability_count",gc_test_avail_count,METH_NOARGS,"Private counters"},\n' + needle
    )
    # Cover the observed old Boolean trusted path and final direct checked child.
    # Inject only around that actual consumer, never terminal availability.
    probe_start = module.index("static GCSemanticProbeSearch gc_semantic_probe_negamax(")
    probe_end = module.index("static PyObject *gc_semantic_probe_search(", probe_start)
    probe = module[probe_start:probe_end]
    trusted_name = ("gc_semantic_runtime_make_trusted_status" if
                    "gc_semantic_runtime_make_trusted_status(" in probe else
                    "gc_semantic_runtime_make_trusted")
    probe = probe.replace(trusted_name + "(", "gc_test_probe_make(")
    helper = """
static int gc_test_probe_fault=0;
static int gc_test_probe_make(GCSemanticPosition *position,
    const GCSemanticRules *rules, uint64_t action, GCSemanticUndo *undo) {
    extern int gc_test_key_failure;
    gc_test_key_failure=gc_test_probe_fault;
    int result=gc_semantic_runtime_make_trusted(position,rules,action,undo);
    gc_test_key_failure=0;return result;
}
static PyObject *gc_test_set_probe_fault(PyObject *self,PyObject *args) {
    (void)self;
    if(!PyArg_ParseTuple(args,"p",&gc_test_probe_fault))return NULL;
    Py_RETURN_NONE;
}
"""
    if "gc_semantic_runtime_make_checked_status(" in probe:
        trusted_name = "gc_semantic_runtime_make_checked_status"
        probe = probe.replace(trusted_name + "(", "gc_test_probe_make(")
        helper = """
static int gc_test_probe_fault=0;
static int gc_test_probe_make(GCSemanticPosition *child,
    const GCSemanticRules *rules, const GCSemanticPosition *parent, uint64_t action) {
    extern int gc_test_key_failure;
    gc_test_key_failure=gc_test_probe_fault;
    int result=gc_semantic_runtime_make_checked_status(child,rules,parent,action);
    gc_test_key_failure=0;return result;
}
static PyObject *gc_test_set_probe_fault(PyObject *self,PyObject *args) {
    (void)self;
    if(!PyArg_ParseTuple(args,"p",&gc_test_probe_fault))return NULL;
    Py_RETURN_NONE;
}
"""
    else:
        helper=helper.replace("gc_semantic_runtime_make_trusted(", trusted_name + "(")
    module=module[:probe_start]+helper+probe+module[probe_end:]
    module=module.replace(needle,
        '    {"test_set_probe_fault",gc_test_set_probe_fault,METH_VARARGS,"Private probe fault"},\n'+needle)
    key = (source / "native_semantic_key.c").read_text(encoding="utf-8")
    needle = ("int gc_semantic_position_key_digest(const GCSemanticRules *r, "
              "const GCSemanticPosition *p, char out_hex[65]) {")
    assert key.count(needle) == 1
    key = "int gc_test_key_failures=0;\n" + key.replace(needle, needle +
                      "\n    extern int gc_test_key_failure;"
                      "\n    if (gc_test_key_failure) {gc_test_key_failures++;return 0;}")
    (out / "native_module.c").write_text(module, encoding="utf-8")
    (out / "native_semantic_key.c").write_text(key, encoding="utf-8")
    binary = out / ("_native_core" + sysconfig.get_config_var("EXT_SUFFIX"))
    command = [str(zig), "cc", "-target", "x86_64-windows-gnu", "-shared", "-O2",
               "-I" + sysconfig.get_paths()["include"], "-I" + str(source),
               "-L" + str(Path(sys.base_prefix) / "libs"), "-lpython312"]
    command += [str(out / path.name if path.name in {
        "native_module.c", "native_semantic_key.c"} else path)
        for path in sorted(source.glob("*.c"))]
    command += ["-o", str(binary)]
    built = subprocess.run(
        command, capture_output=True, text=True, timeout=180,
        env=dict(os.environ, ZIG_GLOBAL_CACHE_DIR=str(out / "zig-cache")),
    )
    assert built.returncode == 0, built.stderr
    spec = importlib.util.spec_from_file_location("error_test._native_core", binary)
    kernel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kernel)
    return kernel


@pytest.mark.parametrize("root_windows", [False, True])
@pytest.mark.parametrize("cache_enabled", [False, True])
def test_required_serializer_error_and_discarded_view_contract(
    fault_kernel, monkeypatch, root_windows, cache_enabled,
):
    monkeypatch.setattr(native, "_MODULE", fault_kernel)
    raw_results = []
    original_search = fault_kernel.semantic_engine_search

    def counted(*args):
        result = original_search(*args)
        raw_results.append(dict(result))
        return result

    monkeypatch.setattr(fault_kernel, "semantic_engine_search", counted)
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    rules = compile_native_semantic_rules(compiled)
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    checkpoint = LearnableMaterialCheckpoint.from_profile(
        compiled, profile, dynamic_weights={}
    )
    session = GameSession(compiled)
    before, witnesses = session.state, session._search_witnesses
    limits = SearchLimits(max_depth=3, max_nodes=1000000, max_time_seconds=8,
                          quiescence_max_depth=0, quiescence_hard_max_depth=0)

    def engine():
        return SemanticSearchEngine(
            compiled, rules, checkpoint=checkpoint,
            ordering_checkpoint=checkpoint, ordering_min_depth=2,
            ordering_cache_enabled=cache_enabled, tt_megabytes=1,
        )

    baseline = engine().search(
        session, SearchLimits(max_depth=1, max_nodes=1000000,
                              max_time_seconds=8, quiescence_max_depth=0,
                              quiescence_hard_max_depth=0),
        root_window_pruning=root_windows,
    )
    tested = engine()
    fault_kernel.test_set_fault(True)
    try:
        failed = tested.search(session, limits, root_window_pruning=root_windows)
    finally:
        fault_kernel.test_set_fault(False)
    if cache_enabled:
        assert failed.termination_reason == "internal_error"
        assert failed.completed_depth == 1
        assert failed.action in session.legal_actions()
        assert (failed.action, failed.score, failed.principal_variation) == (
            baseline.action, baseline.score, baseline.principal_variation)
    else:
        # No top-level ordering digest is computed for a discarded static view.
        assert failed.termination_reason == "completed"
        assert failed.completed_depth == 3
        assert raw_results[-1]["ordering_material_view_trials"] > 0
    if cache_enabled:
        assert raw_results[-1]["ordering_material_view_trials"] == 0
    retry = tested.search(session, limits, root_window_pruning=root_windows)
    cold = engine().search(session, limits, root_window_pruning=root_windows)
    assert retry.completed_depth == cold.completed_depth == 3
    assert retry.termination_reason == cold.termination_reason == "completed"
    assert (retry.action, retry.score, retry.principal_variation) == (
        cold.action, cold.score, cold.principal_variation)
    if not cache_enabled:
        assert (failed.action, failed.score, failed.principal_variation) == (
            cold.action, cold.score, cold.principal_variation)
    assert session.state is before and session._search_witnesses is witnesses


@pytest.mark.parametrize("learned_ordering", [False, True])
@pytest.mark.parametrize("root_windows", [False, True])
@pytest.mark.parametrize("cache_enabled", [False, True])
def test_nested_terminal_failure_is_not_completed_stalemate(
    fault_kernel, monkeypatch, root_windows, cache_enabled, learned_ordering,
):
    from dataclasses import replace
    from generic_chess.core.movement import LeapAtom
    from generic_chess.core.pieces import Piece
    from phase19b3_s4_fixtures import (
        multiple_replies_ruleset, multiple_replies_position)
    monkeypatch.setattr(native, "_MODULE", fault_kernel)
    original = multiple_replies_ruleset()
    temporary = compile_ruleset_for_execution(original)
    problem = multiple_replies_position(temporary.support)
    board = list(problem.board)
    for index, piece in enumerate(board):
        if piece and piece.current_type_id == "B":
            board[index] = None
    board[18] = Piece(1, "B", "B")
    types = tuple(
        replace(t, movement_atoms=(LeapAtom((9, 9)),)) if t.is_anchor else t
        for t in original.piece_types)
    compiled = compile_ruleset_for_execution(replace(
        original, piece_types=types,
        initial_position=tuple(tuple(board[r*5:(r+1)*5]) for r in range(5))))
    session = GameSession(compiled)
    for actor in ("A", "B"):
        session.submit(next(a for a in session.legal_actions()
                            if a.actor_type_id == actor))
    assert session.state.ply_count == 2
    assert len(session.state.history) == len(session._search_witnesses) == 3
    before, witnesses = session.state, session._search_witnesses
    rules = compile_native_semantic_rules(compiled)
    checkpoint = LearnableMaterialCheckpoint.from_profile(
        compiled, build_ruleset_profile(compiled, EvaluationConfig()),
        dynamic_weights={})

    def engine():
        return SemanticSearchEngine(
            compiled, rules, checkpoint=checkpoint,
            ordering_checkpoint=checkpoint if learned_ordering else None, ordering_min_depth=2,
            ordering_cache_enabled=cache_enabled, tt_megabytes=1)

    def search(e, depth):
        return e.search(session, SearchLimits(
            max_depth=depth, max_nodes=100000, max_time_seconds=8,
            quiescence_max_depth=0, quiescence_hard_max_depth=0),
            root_window_pruning=root_windows)

    fault_kernel.test_set_availability_fault(2, 999999)
    baseline = search(engine(), 1)
    visits, failures = fault_kernel.test_availability_count()
    assert visits > 0 and failures == 0
    tested = engine()
    fault_kernel.test_set_availability_fault(2, visits + 1)
    try:
        failed = search(tested, 3)
        _, failures = fault_kernel.test_availability_count()
    finally:
        fault_kernel.test_set_availability_fault(2, 999999)
    assert failures > 0
    assert failed.termination_reason == "internal_error"
    assert failed.completed_depth == 1
    assert (failed.action, failed.score, failed.principal_variation) == (
        baseline.action, baseline.score, baseline.principal_variation)
    retry, cold = search(tested, 3), search(engine(), 3)
    assert retry.completed_depth == cold.completed_depth == 3
    assert (retry.action, retry.score, retry.principal_variation) == (
        cold.action, cold.score, cold.principal_variation)
    assert session.state is before and session._search_witnesses is witnesses


def test_fixed_depth_required_child_failure_is_not_empty_result(fault_kernel, monkeypatch):
    from generic_chess.native.adapter import pack_semantic_search_position
    from generic_chess.native.semantic import fixed_depth_search, snapshot
    monkeypatch.setattr(native, "_MODULE", fault_kernel)
    compiled=compile_ruleset_for_execution(build_western_chess_ruleset())
    session=GameSession(compiled)
    for _ in range(2):
        session.submit(session.legal_actions()[0])
    rules=compile_native_semantic_rules(compiled)
    position=pack_semantic_search_position(compiled,rules,session)
    before=snapshot(rules,position)
    assert len(session.state.history)==3
    baseline=fixed_depth_search(rules,position,2)
    assert baseline['nodes']>1 and baseline['best_action'] is not None
    fault_kernel.test_set_probe_fault(True)
    try:
        with pytest.raises(RuntimeError,match="fixed-depth search failed"):
            fixed_depth_search(rules,position,2)
    finally:
        fault_kernel.test_set_probe_fault(False)
    assert snapshot(rules,position)==before
    assert fixed_depth_search(rules,position,2)==baseline
