"""A completed terminal PV must survive result diagnostics at fixed capacity."""
from dataclasses import replace

import pytest

from generic_chess.ai.limits import SearchLimits
from generic_chess.core.transition import apply_action
from generic_chess.native import SemanticSearchEngine, native_available, semantic
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import _core_pv_leaf_dynamic_features
from generic_chess.session.session import GameSession
from test_native_dynamic_feature_views import reference_features, S4_CASES
from test_native_q_history_deferral import cycle, checked_replay
from phase19c1_native_semantic_fixtures import semantic_corpus
from generic_chess.rules.compiler import compile_semantic_ruleset

pytestmark = pytest.mark.skipif(not native_available(), reason="Native unavailable")


@pytest.mark.parametrize("prefix,depth", ((1022, 2), (1023, 1), (1023, 2)))
@pytest.mark.parametrize("q", (0, 1))
@pytest.mark.parametrize("active", (False, True))
def test_actual_max_ply_pv_retains_result_features(prefix, depth, q, active):
    session = cycle(max_ply=1024, repetition=10000, prefix=prefix)
    nr = compile_native_semantic_rules(session.compiled)
    before = session.state, session._search_witnesses
    engine = SemanticSearchEngine(session.compiled, nr,
        dynamic_values=(2, 3, 5) if active else None,
        localized_control_values=(1, 0, 0, 0, 0, 0, 0, 0, -1) if active else None,
        tt_megabytes=0, ordering_cache_enabled=False)
    result = engine.search(session, SearchLimits(max_depth=depth, max_nodes=4096,
        quiescence_max_depth=q, quiescence_hard_max_depth=4 if q else 0))
    assert result.completed_depth == depth and result.score == 0
    state = session.state
    for action in result.principal_variation:
        state = apply_action(state, action, session.compiled)
    assert state.ply_count == 1024
    assert state.terminal_status.status.value == "max_ply"
    assert len(state.history) == 1025
    # Native's rule-ply trial gate is closed here; physical check pressure
    # remains, but this quiet cycle has neither owner in check.
    assert result.dynamic_features == (0, 0, 0)
    assert result.dynamic_features != ()
    checked_replay(session, nr, result)
    assert (session.state, session._search_witnesses) == before


@pytest.mark.parametrize("name,compiled", semantic_corpus(), ids=lambda x: x if isinstance(x, str) else None)
def test_core_result_feature_definition_matches_native_full_mechanisms(name, compiled):
    session = GameSession(compiled)
    nr = compile_native_semantic_rules(compiled)
    for _ in range(3):
        before = session.state, session._search_witnesses
        packed = pack_semantic_search_position(compiled, nr, session)
        assert _core_pv_leaf_dynamic_features(session, ()) == semantic.dynamic_features(nr, packed)
        actions = session.legal_actions()
        if session.state.terminal_status.is_terminal or not actions:
            break
        action = sorted(actions, key=repr)[0]
        child = apply_action(session.state, action, compiled)
        assert _core_pv_leaf_dynamic_features(session, (action,)) == reference_features(compiled, child.position)
        assert (session.state, session._search_witnesses) == before
        session.submit(action)


@pytest.mark.parametrize("builder,posfn", S4_CASES)
@pytest.mark.parametrize("owner", (0, 1))
def test_core_result_features_keep_s4_owner_contract(builder, posfn, owner):
    # Specification Position, not a claimed reachable long-history session.
    from types import SimpleNamespace
    from generic_chess.core.position import GameState
    from generic_chess.core.terminal import TerminalResult, TerminalStatus
    compiled = compile_semantic_ruleset(builder())
    position = replace(posfn(compiled.support), side_to_move=owner)
    session = SimpleNamespace(compiled=compiled, state=GameState(
        position=position, ply_count=0, repetition_counts=(),
        terminal_status=TerminalResult(TerminalStatus.ONGOING), history=()))
    assert _core_pv_leaf_dynamic_features(session, ()) == reference_features(compiled, position)


def test_noncapacity_native_feature_failure_is_not_swallowed(monkeypatch):
    session = cycle(prefix=0)
    nr = compile_native_semantic_rules(session.compiled)
    engine = SemanticSearchEngine(session.compiled, nr, tt_megabytes=0)
    def failed(*args):
        raise RuntimeError("observed native feature failure")
    monkeypatch.setattr(semantic, "dynamic_features", failed)
    with pytest.raises(RuntimeError, match="observed native feature failure"):
        engine.search(session, SearchLimits(max_depth=1, max_nodes=128,
            quiescence_max_depth=0, quiescence_hard_max_depth=0))


def test_actual_asymmetric_terminal_leaf_preserves_native_rule_gate():
    from conftest import make_ruleset
    from generic_chess.core.movement import LeapAtom
    from generic_chess.core.pieces import PieceType
    from generic_chess.core.semantic_executor import SemanticEngine
    from generic_chess.core.movegen import legal_actions
    from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution

    anchor = PieceType("K", "Anchor", (), is_anchor=True)
    vertical = (LeapAtom((0, 1)), LeapAtom((0, -1)))
    pieces = [anchor, PieceType("F", "F", vertical), PieceType("G", "G", vertical),
              PieceType("H", "Extra", (LeapAtom((1, 0)), LeapAtom((-1, 0)))),
              PieceType("Z", "Z", ())]
    rules = make_ruleset(4, pieces, ["Z..k", "...g", "F...", "KH.z"],
        max_ply=1024, repetition_limit=10000,
        drop_all={t: (False,) * 16 for t in ("F", "G", "H", "Z")})
    compiled = compile_legacy_ruleset_for_semantic_execution(rules)
    session = GameSession(compiled)
    path = ((0, 1, 0, 2), (3, 2, 3, 1), (0, 2, 0, 1), (3, 1, 3, 2))
    for index in range(1023):
        target = path[index % 4]
        action = next(a for a in session.legal_actions()
            if (a.from_square.file, a.from_square.rank,
                a.to_square.file, a.to_square.rank) == target)
        session.submit(action)
    before = session.state, session._search_witnesses
    nr = compile_native_semantic_rules(compiled)
    engine = SemanticSearchEngine(compiled, nr, tt_megabytes=0)
    limits = SearchLimits(max_depth=1, max_nodes=128,
        quiescence_max_depth=0, quiescence_hard_max_depth=0)
    result = engine.search(session, limits)
    state = apply_action(session.state, result.action, compiled)
    assert state.terminal_status.status.value == "max_ply"
    assert state.ply_count == 1024 and len(state.history) == 1025
    assert not legal_actions(state, compiled)
    raw_counts = tuple(len(SemanticEngine(compiled).legal_actions(
        replace(state.position, side_to_move=owner))) for owner in (0, 1))
    assert raw_counts == (2, 1)
    assert reference_features(compiled, state.position) == (1, 0, 0)
    # A real adjacent-limit control demonstrates that blindly using Position
    # counts would change the existing Native result-feature definition.
    short_compiled = compile_legacy_ruleset_for_semantic_execution(
        replace(rules, max_ply=512))
    short = GameSession(short_compiled)
    for action in session.to_record().actions[:511]:
        short.submit(action)
    short_nr = compile_native_semantic_rules(short_compiled)
    short_result = SemanticSearchEngine(short_compiled, short_nr,
        tt_megabytes=0).search(short, limits)
    assert result.dynamic_features == short_result.dynamic_features == (0, 0, 0)
    assert (session.state, session._search_witnesses) == before

    import generic_chess.native.semantic_engine as module
    original = module._core_pv_leaf_dynamic_features
    def failed(*args):
        raise RuntimeError("Core boundary feature failed")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, "_core_pv_leaf_dynamic_features", failed)
        with pytest.raises(RuntimeError, match="Core boundary feature failed"):
            engine.search(session, limits)
    assert module._core_pv_leaf_dynamic_features is original
    retry = engine.search(session, limits)
    assert retry.action == result.action and retry.dynamic_features == (0, 0, 0)
    assert (session.state, session._search_witnesses) == before


def test_zero_depth_no_pv_and_unqualified_boundary_features_remain_distinct():
    session = cycle(max_ply=2048, repetition=10000, prefix=1023)
    nr = compile_native_semantic_rules(session.compiled)
    before = session.state, session._search_witnesses
    result = SemanticSearchEngine(session.compiled, nr, tt_megabytes=0).search(
        session, SearchLimits(max_depth=0, max_nodes=128,
            quiescence_max_depth=0, quiescence_hard_max_depth=0))
    assert result.principal_variation == () and result.dynamic_features == ()
    # An actual legal edge, not a claimed Native PV or full-capacity feature.
    action = session.legal_actions()[0]
    with pytest.raises(NotImplementedError, match="result features.*Core evaluation"):
        _core_pv_leaf_dynamic_features(session, (action,))
    assert (session.state, session._search_witnesses) == before


def test_plain_rule_terminal_features_keep_nonzero_check_pressure():
    from test_native_pending_continuation import session_after
    session = session_after(("e2e4", "d7d5", "f1b5"), trigger=None)
    assert session.state.terminal_status.status.value == "max_ply"
    nr = compile_native_semantic_rules(session.compiled)
    packed = pack_semantic_search_position(session.compiled, nr, session)
    assert semantic.dynamic_features(nr, packed) == (0, 0, 10)
    assert _core_pv_leaf_dynamic_features(session, ()) == (0, 0, 10)


def test_actual_pending_record_beyond_capacity_keeps_explicit_core_evaluator():
    from conftest import make_ruleset
    from generic_chess import RuleAutomaticAdjudication
    from generic_chess.core.movement import LeapAtom, RayAtom
    from generic_chess.core.pieces import PieceType
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution

    anchor = PieceType("K", "Anchor", (LeapAtom((1, 0)), LeapAtom((-1, 0))),
                       is_anchor=True)
    rook = PieceType("R", "Checker", (RayAtom((0, 1)),
                     LeapAtom((1, 0)), LeapAtom((-1, 0))))
    rules = replace(make_ruleset(4, [anchor, rook],
        ["..k.", ".R..", "....", "K..."], max_ply=3, repetition_limit=10000),
        automatic_adjudications=(RuleAutomaticAdjudication("opaque", 1),))
    compiled = compile_legacy_ruleset_for_semantic_execution(rules)
    session = GameSession(compiled)
    path = ((1, 2, 2, 2), (2, 3, 1, 3), (2, 2, 1, 2), (1, 3, 2, 3))
    for index in range(1025):
        target = path[index % 4]
        action = next(a for a in session.legal_actions()
            if (a.from_square.file, a.from_square.rank,
                a.to_square.file, a.to_square.rank) == target)
        session.submit(action)
    assert not session.state.terminal_status.is_terminal
    assert len(session.state.history) == 1026
    assert all(event.gave_check for event in session.state.history[1::2])
    before = session.state, session._search_witnesses
    nr = compile_native_semantic_rules(compiled)
    limits = SearchLimits(max_depth=1, max_nodes=4096,
        quiescence_max_depth=0, quiescence_hard_max_depth=0)
    with pytest.raises(NotImplementedError, match="history capacity.*Core"):
        SemanticSearchEngine(compiled, nr, tt_megabytes=0).search(session, limits)

    class ExactCallback:
        calls = 0
        def evaluate(self, state):
            self.calls += 1
            # The evaluator receives a readonly RuntimeSearchState, whose
            # public contract intentionally omits history. Inspect the actual
            # backing runtime here as a regression diagnostic only.
            assert len(state._runtime.history) == state.ply_count + 1
            assert state.ply_count >= 1025
            return reference_features(compiled, state.position)[0]
        def capture_order_value(self, mover, occupant):
            return 0
    callback = ExactCallback()
    player = AlphaBetaPlayer(compiled, evaluator_override=callback,
        use_tt=False, use_ordering=False, use_disk_cache=False,
        use_native_semantic_legality=False,
        tuning=SearchTuning(use_root_tactical=False))
    decision = player.choose_action(session, limits)
    assert decision.completed_depth == 1
    assert decision.action in session.legal_actions()
    assert callback.calls > 0
    assert player.native_legality_provider is None
    assert (session.state, session._search_witnesses) == before
