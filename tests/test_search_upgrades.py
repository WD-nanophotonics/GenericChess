"""Ablation-flag equivalence and counter tests (PVS/aspiration/root scan/picker/countermove/mate-distance)."""

import pytest
from dataclasses import replace

from generic_chess.ai.alphabeta.ordering import MoveOrderer, StagedMovePicker
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import (
    INF,
    SearchAborted,
    _Budget,
    _Context,
    _aspiration_iteration,
    quiescence,
    reference_minimax,
    run_root_search,
)
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig, MATE_SCORE
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import BoardMove
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.session.session import GameSession

from ai_fixtures import build_4x4_rooks, build_mate
from conftest import make_state, sq
from test_ai_match import _mate_ruleset
from test_ai_search import _optimal_actions


def _evaluator(compiled):
    config = EvaluationConfig()
    return Evaluator(compiled, build_ruleset_profile(compiled, config), config)


def _ctx(compiled, evaluator, tuning=None, limits=None):
    return _Context(
        compiled,
        evaluator,
        TranspositionTable(),
        SearchStatistics(),
        _Budget(limits or SearchLimits(max_depth=4, quiescence_max_depth=0), None),
        tuning or SearchTuning(),
        True,
        True,
        0,
        None,
    )


def _equivalence(compiled, tuning, depth=3):
    # Isolate the search itself: the root scan short-circuits mate positions.
    tuning = replace(tuning, use_root_tactical=False)
    evaluator = _evaluator(compiled)
    state = GameSession(compiled).state
    ref_score, ref_actions = _optimal_actions(compiled, evaluator, depth)
    stats = SearchStatistics()
    action, score, pv, reason = run_root_search(
        state,
        compiled,
        evaluator,
        TranspositionTable(),
        SearchLimits(max_depth=depth, quiescence_max_depth=0),
        None,
        stats,
        use_tt=True,
        use_ordering=True,
        tuning=tuning,
    )
    assert reason in ("completed_depth", "node_limit")
    assert score == ref_score
    assert action in ref_actions
    return stats


def test_pvs_matches_reference_and_counts():
    stats = _equivalence(build_4x4_rooks(), SearchTuning(use_pvs=True), depth=3)
    assert stats.pvs_null_window_searches > 0
    assert stats.pvs_researches >= 0


def test_aspiration_widens_on_fail_and_stays_exact():
    compiled = build_4x4_rooks()
    evaluator = _evaluator(compiled)
    state = GameSession(compiled).state
    ctx = _ctx(compiled, evaluator, SearchTuning(use_aspiration=True))
    # A wildly wrong previous score forces fail-low widening back to exactness.
    result = _aspiration_iteration(state, 3, 10**9, ctx)
    ref_score, _ = _optimal_actions(compiled, evaluator, 3)
    assert result.score == ref_score
    assert ctx.stats.aspiration_fail_low >= 1
    assert ctx.stats.aspiration_researches >= 2


def test_aspiration_equivalence_at_depth_4():
    compiled = build_4x4_rooks()
    stats = _equivalence(compiled, SearchTuning(use_pvs=True, use_aspiration=True), depth=4)
    assert stats.aspiration_researches >= 0


def test_root_scan_finds_immediate_mate():
    compiled = compile_ruleset(_mate_ruleset())
    evaluator = _evaluator(compiled)
    state = GameSession(compiled).state
    stats = SearchStatistics()
    action, score, pv, reason = run_root_search(
        state,
        compiled,
        evaluator,
        TranspositionTable(),
        SearchLimits(max_depth=1, quiescence_max_depth=0),
        None,
        stats,
        use_tt=True,
        use_ordering=True,
        tuning=SearchTuning(use_root_tactical=True),
    )
    assert reason == "root_immediate_win"
    assert score == MATE_SCORE - 1
    matching = [
        (a, c)
        for a, c in legal_successors(state, compiled)
        if a == action
        and c.terminal_status.status.value == "checkmate"
        and c.terminal_status.winner == 0
    ]
    assert matching


def test_root_scan_fallback_is_eval_best_not_canonical_first():
    compiled = build_4x4_rooks()
    evaluator = _evaluator(compiled)
    state = GameSession(compiled).state
    root_count = len(legal_actions(state, compiled))
    # Let the scan finish but abort before depth 1 completes.
    stats = SearchStatistics()
    action, _score, _pv, reason = run_root_search(
        state,
        compiled,
        evaluator,
        TranspositionTable(),
        SearchLimits(max_depth=64, max_nodes=root_count + 1, quiescence_max_depth=0),
        None,
        stats,
        use_tt=True,
        use_ordering=True,
        tuning=SearchTuning(use_root_tactical=True),
    )
    assert reason == "fallback"
    assert stats.root_scan_used_fallback
    expected = None
    best_score = -INF
    for a, child in legal_successors(state, compiled):
        score = -evaluator.evaluate(child)
        if score > best_score:
            best_score = score
            expected = a
    assert action == expected


def test_root_scan_off_falls_back_to_canonical_first():
    compiled = build_4x4_rooks()
    evaluator = _evaluator(compiled)
    state = GameSession(compiled).state
    root_count = len(legal_actions(state, compiled))
    stats = SearchStatistics()
    action, _score, _pv, reason = run_root_search(
        state,
        compiled,
        evaluator,
        TranspositionTable(),
        SearchLimits(max_depth=64, max_nodes=root_count + 1, quiescence_max_depth=0),
        None,
        stats,
        use_tt=True,
        use_ordering=True,
        tuning=SearchTuning(use_root_tactical=False),
    )
    assert reason == "fallback"
    assert action == sorted(legal_actions(state, compiled), key=str)[0]


def test_staged_picker_yields_every_action_once():
    compiled = build_4x4_rooks()
    evaluator = _evaluator(compiled)
    state = GameSession(compiled).state
    actions = legal_actions(state, compiled)
    stats = SearchStatistics()
    orderer = MoveOrderer()
    picker = StagedMovePicker(
        state,
        actions,
        evaluator,
        1,
        None,
        None,
        orderer,
        SearchTuning(),
        stats,
    )
    yielded = list(picker)
    assert sorted(yielded, key=str) == sorted(actions, key=str)
    assert stats.move_picker_generated == len(actions)
    assert stats.move_picker_yielded == len(actions)
    assert sum(stats.move_picker_yielded_by_stage.values()) == len(actions)


def test_staged_picker_equivalence():
    _equivalence(build_4x4_rooks(), SearchTuning(use_staged_move_picker=True), depth=3)


def test_countermove_recorded_and_prioritized():
    compiled = build_4x4_rooks()
    evaluator = _evaluator(compiled)
    state = GameSession(compiled).state
    actions = legal_actions(state, compiled)
    prev = BoardMove(sq(0, 1), sq(0, 2))
    counter = actions[3]
    orderer = MoveOrderer()
    orderer.record_countermove(prev, counter)
    stats = SearchStatistics()
    picker = StagedMovePicker(
        state,
        actions,
        evaluator,
        1,
        None,
        prev,
        orderer,
        SearchTuning(use_countermove=True),
        stats,
    )
    yielded = list(picker)
    assert yielded.count(counter) == 1
    assert stats.countermove_hits == 1
    # All actions here are quiet (no captures/promotions), so the countermove
    # must come before every other quiet action in the initial position.
    assert yielded[0] == counter


def test_countermove_equivalence():
    _equivalence(build_4x4_rooks(), SearchTuning(use_countermove=True), depth=3)


def test_mate_distance_pruning_equivalence():
    stats = _equivalence(build_mate(2), SearchTuning(use_mate_distance_pruning=True), depth=2)
    assert stats.mate_pruning_cutoffs >= 0


def test_check_evasion_hard_cap_aborts_iteration():
    compiled = build_4x4_rooks()
    evaluator = _evaluator(compiled)
    state = make_state(compiled, ["R..K", "....", ".r..", "k..."], side_to_move=1)
    ctx = _ctx(
        compiled,
        evaluator,
        SearchTuning(check_evasion_max_depth=0),
        SearchLimits(max_depth=2, quiescence_max_depth=4),
    )
    with pytest.raises(SearchAborted) as exc:
        quiescence(state, -INF, INF, 0, 0, ctx)
    assert "q_evasion_depth" in str(exc.value)
    assert ctx.stats.q_evasion_truncations >= 1


def test_check_evasion_qnode_budget_aborts_iteration():
    compiled = build_4x4_rooks()
    evaluator = _evaluator(compiled)
    state = make_state(compiled, ["R..K", "....", ".r..", "k..."], side_to_move=1)
    ctx = _Context(
        compiled,
        evaluator,
        TranspositionTable(),
        SearchStatistics(),
        _Budget(SearchLimits(max_depth=2, quiescence_max_depth=4), None),
        SearchTuning(),
        True,
        True,
        4,
        qnode_limit=1,
    )
    with pytest.raises(SearchAborted) as exc:
        quiescence(state, -INF, INF, 0, 0, ctx)
    assert "q_budget" in str(exc.value)
    assert ctx.stats.q_budget_truncations >= 1


def test_full_candidate_keeps_mate_ruleset_optimal():
    compiled = build_4x4_rooks()
    _equivalence(
        compiled,
        SearchTuning(use_pvs=True, use_aspiration=True),
        depth=3,
    )
    player = AlphaBetaPlayer(
        compiled,
        use_disk_cache=False,
        tuning=SearchTuning(
            use_pvs=True,
            use_aspiration=True,
            use_staged_move_picker=True,
            use_countermove=True,
            use_mate_distance_pruning=True,
        ),
    )
    decision = player.choose_action(
        GameSession(compiled),
        SearchLimits(max_depth=3, quiescence_max_depth=0),
    )
    evaluator = _evaluator(compiled)
    _ref_score, optimal = _optimal_actions(compiled, evaluator, 3)
    assert decision.action in optimal
