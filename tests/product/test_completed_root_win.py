"""Only a fully completed winning root child survives a later abort."""
from dataclasses import replace
import pytest
from conftest import make_ruleset, king_type, T
from generic_chess.core.movement import RayAtom
from generic_chess.core.position import Hands, HistoryRecord
from generic_chess.core.identity import position_identity_key
from generic_chess.core.terminal import terminal_result
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta import search
from generic_chess.ai.evaluation.config import MATE_SCORE, MATE_THRESHOLD
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.native import native_available
from scripts.full_q_refresh_comparison import (
    compile_legacy_ruleset_for_semantic_execution, SearchMetadataAdapter, GameSession,
)


def prepared():
    rules = make_ruleset(4, [king_type(), T("R", RayAtom((0, 1)),
        RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))],
        lines=["....", "...R", "....", ".k.K"])
    compiled = compile_legacy_ruleset_for_semantic_execution(rules)
    compiled = SearchMetadataAdapter(ir=compiled.ir,
        _legacy_compiled=compiled._legacy_compiled, support=compiled.support)
    session = GameSession(compiled)
    position = replace(session.state.position, hands=(Hands((("R", 1),)), Hands()))
    key = position_identity_key(position, compiled)
    state = replace(session.state, position=position,
        history=(HistoryRecord(key, -1, "", False),), repetition_counts=((key, 1),))
    session._state = replace(state, terminal_status=terminal_result(state, compiled))
    session._search_history_witnesses = (position,)
    return session


def proves_root_h3(session, action):
    child = apply_action(session.state, action, session.compiled)
    replies = legal_actions(child, session.compiled)
    assert replies
    return all(any(apply_action(after, win, session.compiled).terminal_status.winner == 0
                   for win in legal_actions(after, session.compiled))
               for after in (apply_action(child, a, session.compiled) for a in replies))


@pytest.mark.parametrize("provider_mode", ["Core", "NativeLegal", "NativeAll"])
@pytest.mark.parametrize("nodes,winning", [(98, False), (99, True), (100000, True)])
def test_completed_child_not_incomplete_iteration_is_retained(nodes, winning, provider_mode):
    if provider_mode != "Core" and not native_available():
        pytest.skip("native unavailable")
    session = prepared()
    before = session.state, session.to_record(), session._search_witnesses
    player = AlphaBetaPlayer(session.compiled, use_disk_cache=False,
        use_native_semantic_legality=provider_mode != "Core",
        use_native_semantic_availability=provider_mode == "NativeAll",
        use_native_semantic_check=provider_mode == "NativeAll")
    decision = player.choose_action(session,
        SearchLimits(max_depth=2, max_nodes=nodes, max_time_seconds=5,
                     quiescence_max_depth=2))
    assert before == (session.state, session.to_record(), session._search_witnesses)
    assert decision.runtime_depth_balanced
    assert decision.native_legality_fallbacks == 0
    assert (decision.native_legality_calls > 0) == (provider_mode != "Core")
    if provider_mode == "NativeAll":
        assert player.native_legality_provider.check_metrics["queries"] > 0
        assert player.native_legality_provider.availability_metrics["queries"] > 0
    if nodes == 99:
        assert decision.completed_depth == 1  # Do not claim the whole D2 finished.
        assert decision.result_source == "completed_root_win"
        assert decision.result_ordinary_qdepth == 2
        assert decision.result_check_hard_qdepth == 8
        assert decision.termination_reason == "node_limit"
        assert not decision.root_scan_used_fallback
    elif nodes == 98:
        assert decision.result_source == "main_iteration"
        assert decision.score < MATE_THRESHOLD
    else:
        assert decision.completed_depth == 2
        assert decision.result_source == "main_iteration"
        assert decision.termination_reason == "completed_depth"
    if winning:
        assert decision.score == MATE_SCORE-3
    assert proves_root_h3(session, decision.action) is winning


@pytest.mark.parametrize("native", [False, True])
def test_cancellation_keeps_completed_proof_and_actual_stop_reason(monkeypatch, native):
    if native and not native_available():
        pytest.skip("native unavailable")
    session = prepared()
    token = CancellationToken()
    original = search._Budget.check
    def cancel_after_completed_child(self, stats, *, force=False):
        if stats.nodes + stats.qnodes >= 99:
            token.cancel()
        return original(self, stats, force=force)
    monkeypatch.setattr(search._Budget, "check", cancel_after_completed_child)
    before = session.state, session.to_record(), session._search_witnesses
    decision = AlphaBetaPlayer(session.compiled, use_disk_cache=False,
        use_native_semantic_legality=native).choose_action(session,
        SearchLimits(max_depth=2, max_nodes=None, max_time_seconds=5,
                     quiescence_max_depth=2), cancel_token=token)
    assert decision.termination_reason == "cancelled"
    assert decision.result_source == "completed_root_win"
    assert decision.completed_depth == 1 and decision.score == MATE_SCORE-3
    assert decision.runtime_depth_balanced and proves_root_h3(session, decision.action)
    assert before == (session.state, session.to_record(), session._search_witnesses)


@pytest.mark.skipif(not native_available(), reason="native unavailable")
def test_operational_provider_failure_preserves_completed_win_and_counts():
    session = prepared()
    before = session.state, session.to_record(), session._search_witnesses
    player = AlphaBetaPlayer(session.compiled, use_disk_cache=False)
    provider = player.native_legality_provider
    assert provider is not None
    attempts = 0

    def fail_on_third(position, ply, checkpoint=None):
        nonlocal attempts
        attempts += 1
        if attempts == 3:
            raise ValueError("controlled provider failure")
        return provider(position, ply, checkpoint)

    player._native_legality_provider = fail_on_third
    decision = player.choose_action(session, SearchLimits(
        max_depth=2, max_nodes=99, max_time_seconds=5, quiescence_max_depth=2))
    assert attempts == 3 and decision.native_legality_calls == 2
    assert decision.native_legality_fallbacks == 1
    assert decision.native_legality_operational_failures == 1
    assert decision.result_source == "completed_root_win"
    assert decision.score == MATE_SCORE - 3 and proves_root_h3(session, decision.action)
    assert decision.completed_depth == 1 and decision.termination_reason == "node_limit"
    assert decision.runtime_depth_balanced
    assert before == (session.state, session.to_record(), session._search_witnesses)


@pytest.mark.parametrize("nodes,winning", [(13, False), (14, True), (10000, True)])
def test_completed_root_win_can_end_in_zero_action_declaration(nodes, winning):
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.schema import (
        RuleDeclaration, RuleDeclarationOutcomeBand, RuleSpatialSelector,
        RuleStateGuard, RuleTypeRef, RuleWeightedMaterialMetric,
    )
    from generic_chess.core.declarations import available_declarations
    from generic_chess.ai.alphabeta.tuning import SearchTuning

    rules = make_ruleset(4, [king_type()], lines=["...k", "....", "....", "K..."])
    declaration = RuleDeclaration(
        declaration_id="zone_claim", owner=0,
        state_guards=(RuleStateGuard(
            aggregation="exists", owner="self", type_ref=RuleTypeRef("explicit", "K"),
            compare_field="current", promoted="any", location="board",
            spatial=RuleSpatialSelector("zone", zone_squares=((1, 0),)), value=1),),
        weighted_metric=RuleWeightedMaterialMetric(weights={"K": 1}),
        outcome_bands=(RuleDeclarationOutcomeBand(1, "WIN"),))
    compiled = compile_ruleset_for_execution(replace(rules, declarations=(declaration,)))
    session = GameSession(compiled)

    class Zero:
        def evaluate(self, state):
            return 0

    before = session.state, session.to_record(), session._search_witnesses
    player = AlphaBetaPlayer(compiled, evaluator_override=Zero(),
        use_ordering=False, use_native_semantic_legality=True,
        tuning=SearchTuning(use_root_tactical=False))
    decision = player.choose_action(session, SearchLimits(
        max_depth=2, max_nodes=nodes, max_time_seconds=5, quiescence_max_depth=0))
    # Unsupported declaration rules stay on Core; request flags are not evidence
    # of actual Native execution.
    assert player.native_legality_provider is None
    assert decision.native_legality_calls == 0
    assert before == (session.state, session.to_record(), session._search_witnesses)
    assert decision.runtime_depth_balanced
    child = apply_action(session.state, decision.action, compiled)
    replies = legal_actions(child, compiled)
    assert replies
    proved = all(any(option.outcome == "WIN" for option in available_declarations(
        apply_action(child, action, compiled), compiled)) for action in replies)
    assert proved is winning
    assert decision.score == (MATE_SCORE - 2 if winning else 0)
    if nodes == 14:
        assert decision.result_source == "completed_root_win"
        assert decision.completed_depth == 1
        assert decision.result_ordinary_qdepth == 0
        assert decision.termination_reason == "node_limit"
        assert not child.terminal_status.is_terminal  # Claim is out of band.
    else:
        assert decision.result_source == "main_iteration"


@pytest.mark.parametrize("warm_children", [False, True])
@pytest.mark.parametrize("improving", [False, True])
@pytest.mark.parametrize("selective", [False, True])
def test_mate_window_equality_is_not_a_new_completed_root_proof(
        warm_children, improving, selective):
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.core.search_runtime import SearchPathRuntime
    from scripts.full_q_refresh_comparison import runtime_state

    session = prepared()
    player = AlphaBetaPlayer(session.compiled, use_disk_cache=False,
                             use_native_semantic_legality=False)
    tuning = SearchTuning(use_pvs=selective, use_mate_distance_pruning=selective)

    def query(tt, alpha, beta):
        stats = SearchStatistics()
        runtime = SearchPathRuntime.from_state(session.state, session.compiled,
            history_witnesses=session._search_witnesses)
        runtime.attach_stats(stats)
        before = runtime_state(runtime)
        root_key = runtime.search_key()
        assert tt.probe(root_key) is None  # No vacuous root TT return.
        ctx = search._Context(session.compiled, player._evaluator, tt, stats,
            search._Budget(SearchLimits(max_nodes=100000, max_time_seconds=5), None),
            tuning, True, True, 2, 8, None, runtime=runtime,
            first_main_iteration_complete=True)
        result = search.negamax(session.state, 2, alpha, beta, 0, ctx)
        runtime.assert_balanced()
        assert runtime_state(runtime) == before
        assert stats.successors_searched > 0  # Root had to enter its child loop.
        return result, ctx, root_key

    real_entries = TranspositionTable()
    exact, _, root_key = query(real_entries, -search.INF, search.INF)
    value = exact.score
    assert value == MATE_SCORE - 3 and proves_root_h3(session, exact.best_action)
    tt = TranspositionTable()
    if warm_children:
        # Retain only entries produced by the actual matching search.
        tt._data = dict(real_entries._data)
        tt._data.pop(root_key)
        assert len(tt) > 0
    alpha = value - 1 if improving else value
    result, ctx, _ = query(tt, alpha, alpha + 1)
    assert result.score >= MATE_THRESHOLD
    assert (ctx.root_completed_win is not None) is improving
    if improving:
        assert proves_root_h3(session, ctx.root_completed_win[0].best_action)
