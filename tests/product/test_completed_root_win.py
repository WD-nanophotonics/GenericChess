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


def test_benchmark_keeps_interrupted_completed_root_proof_eligible(monkeypatch):
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.benchmark import runner
    from generic_chess.ai.benchmark.profiles import BenchmarkProfile

    session = prepared()
    monkeypatch.setattr(runner, "GameSession", lambda _compiled: session)

    class ProofThenFullBudgetPlayer(AlphaBetaPlayer):
        calls = 0

        def choose_action(self, current, limits, **kwargs):
            self.calls += 1
            effective = (
                SearchLimits(max_depth=2, max_nodes=99, max_time_seconds=5,
                             quiescence_max_depth=2)
                if self.calls == 1
                else SearchLimits(max_depth=4, max_nodes=100_000,
                                  max_time_seconds=5, quiescence_max_depth=2)
            )
            return super().choose_action(current, effective, **kwargs)

    player = ProofThenFullBudgetPlayer(
        session.compiled, use_disk_cache=False, use_native_semantic_legality=False
    )
    profile = BenchmarkProfile("proof-contract", SearchTuning())
    config = runner.RunConfig(
        control=profile, candidate=profile, suite=(), seconds=None,
        nodes=100_000, max_plies=8,
    )

    outcome, events = runner.play_game(
        session.compiled, (), "completed-proof", "completed-proof", 0,
        player, player, config,
    )

    assert events[0].termination_reason == "node_limit"
    assert events[0].completed_depth == 1
    assert not events[0].fallback
    assert not outcome.candidate_fallback and not outcome.control_fallback
    assert outcome.result == "candidate_win"
    summary = runner.summarize([outcome])
    assert summary["fallback_games"] == 0
    assert summary["eligible_games"] == 1


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
@pytest.mark.parametrize("early", [False, True])
def test_completed_root_win_can_end_in_zero_action_declaration(nodes, winning, early):
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
        tuning=SearchTuning(use_root_tactical=False, stop_after_root_win=early))
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
    if nodes == 14 or (early and winning):
        assert decision.result_source == "completed_root_win"
        assert decision.completed_depth == 1
        assert decision.result_ordinary_qdepth == 0
        # The proof returns at13 paid nodes. With cap14, default search
        # reaches the next node and aborts; opt-in never starts that work.
        assert decision.termination_reason == ("root_win_found" if early else "node_limit")
        assert (decision.nodes + decision.qnodes < nodes) is early
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


@pytest.mark.parametrize("provider_mode", ("Core", "NativeAll"))
def test_opt_in_stops_after_first_complete_root_win_without_claiming_full_depth(provider_mode):
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    if provider_mode != "Core" and not native_available():
        pytest.skip("native unavailable")
    session = prepared()
    before = session.state, session.to_record(), session._search_witnesses
    decisions = []
    progress = []
    for early in (False, True):
        player = AlphaBetaPlayer(session.compiled, use_disk_cache=False,
            use_native_semantic_legality=provider_mode != "Core",
            use_native_semantic_availability=provider_mode == "NativeAll",
            use_native_semantic_check=provider_mode == "NativeAll",
            tuning=SearchTuning(stop_after_root_win=early))
        decisions.append(player.choose_action(session,
            SearchLimits(max_depth=2, max_nodes=100000, quiescence_max_depth=2),
            progress_callback=lambda depth, *_: progress.append((early, depth))))
    full, early = decisions
    assert full.completed_depth == 2 and full.termination_reason == "completed_depth"
    assert early.completed_depth == 1 and early.termination_reason == "root_win_found"
    assert early.result_source == "completed_root_win"
    assert early.result_ordinary_qdepth == 2 and early.result_check_hard_qdepth == 8
    assert early.score == full.score == MATE_SCORE - 3
    assert early.nodes + early.qnodes < full.nodes + full.qnodes
    assert proves_root_h3(session, early.action)
    assert (True, 2) not in progress and (True, 1) in progress
    assert early.runtime_depth_balanced and early.native_legality_fallbacks == 0
    assert before == (session.state, session.to_record(), session._search_witnesses)


@pytest.mark.parametrize("reason", ("cancelled", "time_limit"))
def test_opt_in_checks_actual_control_after_completed_proof(monkeypatch, reason):
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    session = prepared()
    token = CancellationToken()
    clock = [0.0]
    original_context = search._Context

    class InterruptAtProof(original_context):
        __slots__ = ()
        def __setattr__(self, name, value):
            super().__setattr__(name, value)
            if name == "root_completed_win" and value is not None:
                if reason == "cancelled":
                    token.cancel()
                else:
                    clock[0] = 2.0

    monkeypatch.setattr(search, "_Context", InterruptAtProof)
    monkeypatch.setattr(search.time, "perf_counter", lambda: clock[0])
    before = session.state, session.to_record(), session._search_witnesses
    decision = AlphaBetaPlayer(session.compiled, use_disk_cache=False,
        use_native_semantic_legality=False,
        tuning=SearchTuning(stop_after_root_win=True)).choose_action(session,
            SearchLimits(max_depth=2, max_time_seconds=1, quiescence_max_depth=2),
            cancel_token=token)
    assert decision.termination_reason == reason
    assert decision.result_source == "completed_root_win" and decision.completed_depth == 1
    assert decision.score == MATE_SCORE - 3 and proves_root_h3(session, decision.action)
    assert decision.runtime_depth_balanced
    assert before == (session.state, session.to_record(), session._search_witnesses)


def test_opt_in_warm_exact_win_does_not_start_an_unneeded_deeper_iteration():
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    session = prepared()
    player = AlphaBetaPlayer(session.compiled, use_disk_cache=False,
        use_native_semantic_legality=False)
    completed = player.choose_action(session, SearchLimits(max_depth=2,
        max_nodes=100000, quiescence_max_depth=2))
    assert completed.completed_depth == 2 and completed.score == MATE_SCORE - 3
    player._tuning = replace(player._tuning, stop_after_root_win=True)
    before = session.state, session.to_record(), session._search_witnesses
    early = player.choose_action(session, SearchLimits(max_depth=8,
        max_nodes=100000, quiescence_max_depth=2))
    assert early.tt_hits > 0 and early.completed_depth == 1
    assert early.termination_reason == "root_win_found" and early.result_source == "main_iteration"
    assert early.score == completed.score and proves_root_h3(session, early.action)
    assert early.runtime_depth_balanced
    assert before == (session.state, session.to_record(), session._search_witnesses)


@pytest.mark.parametrize("reason", ("cancelled", "time_limit"))
def test_opt_in_warm_win_checks_controls_after_progress_callback(monkeypatch, reason):
    session = prepared()
    player = AlphaBetaPlayer(session.compiled, use_disk_cache=False,
        use_native_semantic_legality=False)
    warm = player.choose_action(session, SearchLimits(max_depth=2,
        max_nodes=100000, quiescence_max_depth=2))
    assert warm.completed_depth == 2 and warm.score == MATE_SCORE - 3
    player._tuning = replace(player._tuning, stop_after_root_win=True)
    token = CancellationToken()
    clock = [0.0]
    monkeypatch.setattr(search.time, "perf_counter", lambda: clock[0])
    def interrupt(depth, *_):
        assert depth == 1
        if reason == "cancelled":
            token.cancel()
        else:
            clock[0] = 2.0
    before = session.state, session.to_record(), session._search_witnesses
    result = player.choose_action(session, SearchLimits(max_depth=8,
        max_time_seconds=1, quiescence_max_depth=2), cancel_token=token,
        progress_callback=interrupt)
    assert result.termination_reason == reason
    assert result.result_source == "main_iteration" and result.completed_depth == 1
    assert result.score == MATE_SCORE - 3 and proves_root_h3(session, result.action)
    assert result.runtime_depth_balanced
    assert before == (session.state, session.to_record(), session._search_witnesses)


@pytest.mark.parametrize("sign", (-1, 1))
def test_opt_in_does_not_confuse_oversized_static_scores_with_a_root_win(sign):
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.evaluation.config import MAX_STATIC_EVAL
    session = prepared()
    class Oversized:
        def evaluate(self, state):
            return sign * MATE_SCORE * 100
    before = session.state, session.to_record(), session._search_witnesses
    result = AlphaBetaPlayer(session.compiled, evaluator_override=Oversized(),
        use_disk_cache=False, use_native_semantic_legality=False,
        use_ordering=False,  # This mock supplies leaf values only.
        tuning=SearchTuning(stop_after_root_win=True)).choose_action(session,
            SearchLimits(max_depth=2, max_nodes=100000, quiescence_max_depth=0))
    assert abs(result.score) <= MAX_STATIC_EVAL
    assert result.termination_reason == "completed_depth" and result.completed_depth == 2
    assert result.result_source == "main_iteration" and result.runtime_depth_balanced
    assert before == (session.state, session.to_record(), session._search_witnesses)
