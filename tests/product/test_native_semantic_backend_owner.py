"""An existing semantic object keeps the kernel that created its capsules."""
import pytest
import generic_chess.native as native
from generic_chess.native import semantic as sem
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.mirror import pack_semantic_action
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.cancellation import CancellationToken
from test_native_semantic_qsearch import fixture, Material

pytestmark = pytest.mark.skipif(not native.native_available(), reason="Native unavailable")

class WrongDefault:
    def __getattr__(self, name):
        raise AssertionError("operation escaped its rules backend: " + name)

@pytest.mark.parametrize("path", ["state", "engine", "iterative", "cancel"])
def test_compiled_semantic_objects_keep_creating_backend(monkeypatch, path):
    session = fixture()
    nr = compile_native_semantic_rules(session.compiled)
    engine = SemanticSearchEngine(session.compiled, nr, board_values=Material.values,
        hand_values=Material.values, tt_megabytes=1, ordering_cache_enabled=False)
    pos = pack_semantic_search_position(session.compiled, nr, session)
    action = session.legal_actions()[0]
    code = pack_semantic_action(nr, session.state.position, action)
    before = sem.snapshot(nr, pos)
    monkeypatch.setattr(native, "_MODULE", WrongDefault())
    if path == "state":
        again = pack_semantic_search_position(session.compiled, nr, session)
        assert sem.snapshot(nr, again) == before
        assert sem.public_action(nr, code) == action
        assert pack_semantic_action(nr, session.state.position, action) == code
        assert code in sem.guarded_actions(nr, pos)
        assert sem.make_unmake_roundtrip(nr, pos, code)["restored"]
    elif path == "iterative":
        result = sem.semantic_iterative_search(nr, pos, 2,
            board_values=Material.values, hand_values=Material.values,
            max_time_seconds=5, root_window_pruning=True)
        assert result["completed_depth"] == 2
        assert sem.public_action(nr, result["best_action"]) in session.legal_actions()
    else:
        token = CancellationToken() if path == "cancel" else None
        if token is not None:
            token.cancel()
        result = engine.search(session, SearchLimits(max_depth=2, max_time_seconds=5,
            quiescence_max_depth=1), token, root_window_pruning=True)
        if token is not None:
            assert result.termination_reason == "cancelled"
        else:
            assert result.completed_depth == 2
            assert result.action in session.legal_actions()
        engine.clear_tt()
        assert engine.tt_info()["occupied_entries"] == 0
    assert sem.snapshot(nr, pos) == before


def test_provider_builds_with_rules_owner_after_default_changes(monkeypatch):
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.core.semantic_executor import semantic_engine_for
    session = fixture()
    nr = compile_native_semantic_rules(session.compiled)
    monkeypatch.setattr(native, "_MODULE", WrongDefault())
    provider = NativeSemanticLegalityProvider(session.compiled,
        semantic_engine_for(session.compiled), nr, strict=True)
    pairs = provider(session.state.position, session.state.ply_count)
    assert {action for action, binding in pairs} == set(session.legal_actions())


def test_new_engine_uses_existing_rules_owner_after_default_changes(monkeypatch):
    session = fixture()
    nr = compile_native_semantic_rules(session.compiled)
    monkeypatch.setattr(native, "_MODULE", WrongDefault())
    engine = SemanticSearchEngine(session.compiled, nr, board_values=Material.values,
        hand_values=Material.values, tt_megabytes=0, ordering_cache_enabled=False)
    assert engine.search(session, SearchLimits(max_depth=2,
        max_time_seconds=5, quiescence_max_depth=0)).completed_depth == 2


@pytest.mark.parametrize("missing", ["qsearch", "rootwindow"])
def test_capability_checks_follow_bound_owner_not_default(monkeypatch, missing):
    session = fixture()
    module = native._module()
    class OlderOwner:
        SEMANTIC_QSEARCH_VERSION = 0 if missing == "qsearch" else 1
        def __getattr__(self, name):
            return getattr(module, name)
        def native_capabilities(self):
            caps = dict(module.native_capabilities())
            if missing == "rootwindow":
                caps["semantic_exact_root_windows"] = False
            return caps
    owner = OlderOwner()
    import generic_chess.native.compiler as compiler
    monkeypatch.setattr(compiler, "_module", lambda: owner)
    nr = compiler.compile_native_semantic_rules(session.compiled)
    assert nr.backend_module is owner
    engine = SemanticSearchEngine(session.compiled, nr, board_values=Material.values,
        hand_values=Material.values, tt_megabytes=0, ordering_cache_enabled=False)
    error = ValueError if missing == "qsearch" else compiler.NativeUnsupportedRuleError
    with pytest.raises(error, match="qsearch requires|inexact tied bound"):
        engine.search(session, SearchLimits(max_depth=2,
            quiescence_max_depth=1 if missing == "qsearch" else 0),
            root_window_pruning=missing == "rootwindow")


def test_compile_metadata_uses_same_captured_backend(monkeypatch):
    import generic_chess.native.compiler as compiler
    session = fixture()
    expected = native._module()
    build = compiler.build_semantic_compile_payload
    def replace_default_after_capture(semantic):
        payload = build(semantic)
        monkeypatch.setattr(native, "_MODULE", WrongDefault())
        return payload
    monkeypatch.setattr(compiler, "build_semantic_compile_payload", replace_default_after_capture)
    nr = compiler.compile_native_semantic_rules(session.compiled)
    assert nr.backend_module is expected
    pos = pack_semantic_search_position(session.compiled, nr, session)
    assert sem.snapshot(nr, pos)["ply"] == 0

@pytest.mark.parametrize("payload", ["older_missing", "coercible", "invalid"])
def test_result_diagnostic_arrays_keep_conversion_contract(monkeypatch, payload):
    """Faster projection retains older-owner defaults and integer errors."""
    from dataclasses import fields
    from generic_chess.native.semantic_engine import SemanticIterativeSearchResult
    import generic_chess.native.compiler as compiler

    session = fixture()
    module = native._module()
    keys = tuple(
        field.name for field in fields(SemanticIterativeSearchResult)
        if field.name.endswith("_by_ply")
        or field.name == "ordering_skipped_by_remaining_depth"
    )
    assert len(keys) == 12

    class DiagnosticOwner:
        def __getattr__(self, name):
            return getattr(module, name)

        def semantic_engine_search(self, *args):
            raw = dict(module.semantic_engine_search(*args))
            for key in keys:
                if payload == "older_missing":
                    raw.pop(key, None)
                elif payload == "coercible":
                    raw[key] = iter(("2", 3.9, False))
            if payload == "invalid":
                raw[keys[0]] = ("not-an-integer",)
            return raw

    monkeypatch.setattr(compiler, "_module", lambda: DiagnosticOwner())
    rules = compiler.compile_native_semantic_rules(session.compiled)
    engine = SemanticSearchEngine(session.compiled, rules,
        board_values=Material.values, hand_values=Material.values,
        tt_megabytes=0, ordering_cache_enabled=False)
    before = (session.state, session.to_record(), session._search_witnesses)
    limits = SearchLimits(max_depth=1, max_time_seconds=5, quiescence_max_depth=0)
    if payload == "invalid":
        with pytest.raises(ValueError, match="invalid literal"):
            engine.search(session, limits)
    else:
        result = engine.search(session, limits)
        expected = () if payload == "older_missing" else (2, 3, 0)
        assert all(getattr(result, key) == expected for key in keys)
        assert all(type(value) is int for key in keys for value in getattr(result, key))
    assert before == (session.state, session.to_record(), session._search_witnesses)
