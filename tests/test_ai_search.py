"""AlphaBeta correctness: minimax equivalence, mates, budgets, TT."""

import pytest

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import _tt_key, reference_minimax
from generic_chess.ai.alphabeta.transposition import (
    BoundType,
    TranspositionTable,
    score_from_tt,
    score_to_tt,
)
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.evaluation.config import EvaluationConfig, MATE_SCORE
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import BoardMove
from generic_chess.core.movegen import legal_actions
from generic_chess.session.session import GameSession

from ai_fixtures import build_4x4_rooks, build_mate, build_promotion


def _player(compiled, **kw):
    return AlphaBetaPlayer(compiled, use_disk_cache=False, tt_max_entries=10_000, **kw)


def _optimal_actions(compiled, evaluator, depth):
    state = GameSession(compiled).state
    best_score, _ = reference_minimax(state, depth, evaluator, compiled)
    optimal = []
    for action in legal_actions(state, compiled):
        child = __import__("generic_chess.core.transition", fromlist=["apply_action"]).apply_action(
            state, action, compiled
        )
        score, _ = reference_minimax(child, depth - 1, evaluator, compiled, ply=1)
        if -score == best_score:
            optimal.append(action)
    return best_score, optimal


def test_minimax_equals_alphabeta_bare():
    compiled = build_4x4_rooks()
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = Evaluator(compiled, profile, config)
    session = GameSession(compiled)
    best_score, optimal = _optimal_actions(compiled, evaluator, depth=2)

    player = _player(compiled, use_tt=False, use_ordering=False)
    decision = player.choose_action(
        session, SearchLimits(max_depth=2, quiescence_max_depth=0)
    )
    assert decision.score == best_score
    assert decision.action in optimal


def test_minimax_equals_alphabeta_tt_and_ordering():
    compiled = build_4x4_rooks()
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = Evaluator(compiled, profile, config)
    session = GameSession(compiled)
    best_score, optimal = _optimal_actions(compiled, evaluator, depth=3)
    player = _player(compiled)
    decision = player.choose_action(
        session, SearchLimits(max_depth=3, quiescence_max_depth=0)
    )
    assert decision.score == best_score
    assert decision.action in optimal


def test_returns_legal_action_and_terminal_none():
    compiled = build_4x4_rooks()
    session = GameSession(compiled)
    player = _player(compiled)
    decision = player.choose_action(session, SearchLimits(max_depth=2))
    assert decision.action in legal_actions(session.state, compiled)

    from generic_chess.core.coordinates import Square

    mate_compiled = build_mate(2)
    mated = GameSession(mate_compiled)
    mated.submit(BoardMove(Square(1, 4), Square(0, 4)))
    terminal_decision = _player(mate_compiled).choose_action(
        mated, SearchLimits(max_depth=2)
    )
    assert terminal_decision.action is None
    assert terminal_decision.termination_reason == "terminal_position"


def test_mate_distance_prefers_faster_win():
    mate1 = build_mate(2)  # mate in 1
    mate2 = build_mate(3)  # mate in 2
    p1 = _player(mate1)
    p2 = _player(mate2)
    d1 = p1.choose_action(GameSession(mate1), SearchLimits(max_depth=3, quiescence_max_depth=0))
    d2 = p2.choose_action(GameSession(mate2), SearchLimits(max_depth=3, quiescence_max_depth=0))
    assert d1.score == MATE_SCORE - 1
    assert d2.score == MATE_SCORE - 3
    assert d1.score > d2.score
    assert p1.choose_action(GameSession(mate1), SearchLimits(max_depth=3, quiescence_max_depth=0)).score == MATE_SCORE - 1


def test_tt_key_distinguishes_history_and_ruleset():
    compiled_a = build_4x4_rooks()
    compiled_b = build_mate(2)
    from generic_chess.core.position import GameState

    s1 = GameSession(compiled_a).state
    s2 = GameState(s1.position, s1.ply_count, (("k1", 1), ("k2", 2)), s1.terminal_status)
    assert _tt_key(s1, compiled_a) != _tt_key(s2, compiled_a)  # repetition differs
    s_b = GameSession(compiled_b).state
    assert _tt_key(s1, compiled_a) != _tt_key(s_b, compiled_b)  # ruleset differs


def test_depth_limit_and_node_limit():
    compiled = build_4x4_rooks()
    player = _player(compiled)
    decision = player.choose_action(
        GameSession(compiled), SearchLimits(max_depth=2, quiescence_max_depth=0)
    )
    assert decision.completed_depth == 2
    assert decision.termination_reason == "completed_depth"

    fresh = _player(compiled)
    limited = fresh.choose_action(
        GameSession(compiled),
        SearchLimits(max_depth=64, max_nodes=500, quiescence_max_depth=0),
    )
    assert limited.nodes <= 500
    assert limited.termination_reason in ("node_limit", "completed_depth")


def test_node_budget_reproducible():
    compiled = build_4x4_rooks()
    limits = SearchLimits(max_depth=64, max_nodes=3000, quiescence_max_depth=0)
    a = _player(compiled).choose_action(GameSession(compiled), limits)
    b = _player(compiled).choose_action(GameSession(compiled), limits)
    assert (a.action, a.score, a.nodes) == (b.action, b.score, b.nodes)


def test_time_limit_and_cancellation():
    compiled = build_4x4_rooks()
    decision = _player(compiled).choose_action(
        GameSession(compiled),
        SearchLimits(max_depth=64, max_time_seconds=0.001, quiescence_max_depth=0),
    )
    assert decision.action in legal_actions(GameSession(compiled).state, compiled)
    assert decision.termination_reason in ("time_limit", "completed_depth", "node_limit")

    token = CancellationToken()
    token.cancel()
    cancelled = _player(compiled).choose_action(
        GameSession(compiled), SearchLimits(max_depth=4, quiescence_max_depth=0), cancel_token=token
    )
    assert cancelled.action in legal_actions(GameSession(compiled).state, compiled)
    assert cancelled.termination_reason == "fallback"


def test_transposition_table_bounds_and_capacity():
    tt = TranspositionTable(max_entries=5)
    tt.new_generation()
    key = ("a", 1, ())
    tt.store(key, depth=2, score=5, bound=BoundType.EXACT, best_action=None)
    entry = tt.probe(key, depth=2)
    assert entry is not None and entry.score == 5
    assert tt.probe(key, depth=3) is None  # shallow entry not reused for deeper requests
    for i in range(10):
        tt.store(("k", i, ()), depth=1, score=i, bound=BoundType.EXACT, best_action=None)
    assert len(tt) <= 5


def test_mate_score_tt_normalization_roundtrip():
    for ply in (0, 3, 7):
        for score in (MATE_SCORE - 1, MATE_SCORE - 5, -(MATE_SCORE - 2)):
            assert score_from_tt(score_to_tt(score, ply), ply) == score


def test_promotion_ruleset_searches():
    compiled = build_promotion()
    player = _player(compiled)
    decision = player.choose_action(
        GameSession(compiled), SearchLimits(max_depth=2, quiescence_max_depth=0)
    )
    assert decision.action in legal_actions(GameSession(compiled).state, compiled)


def test_tiny_time_budget_aborts_before_clock_expiry():
    compiled = build_4x4_rooks()
    player = _player(compiled)
    decision = player.choose_action(
        GameSession(compiled),
        SearchLimits(
            max_depth=10,
            max_time_seconds=0.0001,
            max_nodes=None,
            quiescence_max_depth=0,
        ),
    )
    assert decision.termination_reason == "time_limit"
    assert decision.nodes < 128  # time checked at every 128 nodes
    assert decision.completed_depth == 1
