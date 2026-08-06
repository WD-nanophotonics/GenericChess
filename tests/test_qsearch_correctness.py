"""Phase B: qsearch two-level depth, in-check semantics, noisy classification."""

import pytest

from generic_chess.ai.alphabeta.quiescence import classify_noisy
from generic_chess.ai.alphabeta.search import (
    INF,
    SearchAborted,
    _Budget,
    _Context,
    quiescence,
)
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.movement import RayAtom
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession

from ai_fixtures import build_4x4_rooks
from conftest import T, king_type, make_compiled, make_state


def _evaluator(compiled):
    config = EvaluationConfig()
    return Evaluator(compiled, build_ruleset_profile(compiled, config), config)


def _ctx(compiled, evaluator, limits):
    return _Context(
        compiled,
        evaluator,
        TranspositionTable(),
        SearchStatistics(),
        _Budget(limits, None),
        SearchTuning(),
        True,
        True,
        limits.quiescence_max_depth,
        limits.quiescence_hard_max_depth,
        limits.quiescence_max_nodes,
    )


def _king_rook_6():
    return make_compiled(
        6,
        [
            king_type(),
            T(
                "R",
                RayAtom((0, 1)),
                RayAtom((0, -1)),
                RayAtom((1, 0)),
                RayAtom((-1, 0)),
            ),
        ],
    )


def _check_chain_state(compiled):
    # Black king at (0,0) is in check from the white rook at (0,3).  The black
    # rook at (1,3) can capture it, landing on (0,3) and giving check to the
    # white king at (0,5): a genuine two-ply check chain.
    return make_state(
        compiled,
        ["K.....", "......", "Rr....", "......", "......", "k....."],
        side_to_move=1,
    )


def test_soft_vs_hard_depth_validation():
    with pytest.raises(ValueError, match="quiescence_hard_max_depth"):
        SearchLimits(quiescence_max_depth=6, quiescence_hard_max_depth=4)
    SearchLimits(quiescence_max_depth=4, quiescence_hard_max_depth=8)
    SearchLimits(quiescence_max_depth=4, quiescence_hard_max_depth=4)


def test_in_check_no_stand_pat():
    compiled = build_4x4_rooks()
    evaluator = _evaluator(compiled)
    state = make_state(compiled, ["R..K", "....", ".r..", "k..."], side_to_move=1)
    ctx = _ctx(
        compiled,
        evaluator,
        SearchLimits(quiescence_max_depth=4, quiescence_hard_max_depth=8),
    )
    result = quiescence(state, -INF, INF, 0, 0, ctx)
    stand_pat = evaluator.evaluate(state)
    assert result != stand_pat
    assert ctx.stats.in_check_qnodes >= 1


def test_quiet_evasion_is_searched():
    compiled = build_4x4_rooks()
    evaluator = _evaluator(compiled)
    state = make_state(compiled, ["R..K", "....", ".r..", "k..."], side_to_move=1)
    ctx = _ctx(
        compiled,
        evaluator,
        SearchLimits(quiescence_max_depth=4, quiescence_hard_max_depth=8),
    )
    q = quiescence(state, -INF, INF, 0, 0, ctx)
    child_scores = []
    for action, child in legal_successors(state, compiled):
        # Evasions here are quiet: neither captures nor promotions.
        if isinstance(action, BoardMove):
            occupant = state.position.board[
                4 * action.to_square.rank + action.to_square.file
            ]
            assert action.promotion_target_id is None
            assert occupant is None
        child_ctx = _ctx(
            compiled,
            evaluator,
            SearchLimits(quiescence_max_depth=4, quiescence_hard_max_depth=8),
        )
        child_scores.append(-quiescence(child, -INF, INF, 1, 1, child_ctx))
    assert q == max(child_scores)  # all quiet evasions entered qsearch


def test_check_chain_hard_limit_aborts():
    compiled = _king_rook_6()
    evaluator = _evaluator(compiled)
    state = _check_chain_state(compiled)
    ctx = _ctx(
        compiled,
        evaluator,
        SearchLimits(quiescence_max_depth=1, quiescence_hard_max_depth=1),
    )
    with pytest.raises(SearchAborted) as exc:
        quiescence(state, -INF, INF, 0, 0, ctx)
    assert "qsearch_check_hard_limit" in str(exc.value)
    assert ctx.stats.qsearch_check_hard_limit_aborts >= 1
    assert ctx.stats.in_check_qnodes >= 2  # two in-check plies before abort


def test_non_check_qnode_budget_aborts():
    compiled = build_4x4_rooks()
    evaluator = _evaluator(compiled)
    state = GameSession(compiled).state
    ctx = _Context(
        compiled,
        evaluator,
        TranspositionTable(),
        SearchStatistics(),
        _Budget(SearchLimits(quiescence_max_depth=4, quiescence_hard_max_depth=8), None),
        SearchTuning(),
        True,
        True,
        4,
        8,
        qnode_limit=1,
    )
    with pytest.raises(SearchAborted) as exc:
        quiescence(state, -INF, INF, 0, 0, ctx)
    assert "qsearch_budget" in str(exc.value)
    assert ctx.stats.qsearch_budget_aborts >= 1


def test_checking_drop_is_noisy():
    compiled = build_4x4_rooks()
    stats = SearchStatistics()
    state = make_state(
        compiled,
        ["...k", "....", "....", "K..."],
        side_to_move=0,
        hands=([("R", 1)], ()),
    )
    successors = legal_successors(state, compiled)
    noisy = classify_noisy(state, successors, compiled, stats)
    drops = [a for a in noisy if isinstance(a, DropMove)]
    assert drops  # at least one checking drop
    assert stats.checking_drop_qactions >= 1


def test_nonchecking_drop_excluded():
    compiled = build_4x4_rooks()
    stats = SearchStatistics()
    # Black king at (0,0) is shielded by its own rooks at (1,0) and (0,1),
    # so every legal white rook drop is non-checking.
    state = make_state(
        compiled,
        ["...K", "....", "r...", "kr.."],
        side_to_move=0,
        hands=([("R", 2)], ()),
    )
    successors = legal_successors(state, compiled)
    noisy = classify_noisy(state, successors, compiled, stats)
    assert not any(isinstance(a, DropMove) for a in noisy)
    assert stats.nonchecking_drop_excluded >= 1


def test_checking_move_is_noisy():
    compiled = build_4x4_rooks()
    stats = SearchStatistics()
    # A quiet rook move that gives check must enter qsearch.
    state = make_state(
        compiled,
        ["..k.", "....", "R...", "K..."],
        side_to_move=0,
    )
    successors = legal_successors(state, compiled)
    noisy = classify_noisy(state, successors, compiled, stats)
    assert stats.checking_move_qactions >= 1
    assert any(isinstance(a, BoardMove) for a in noisy)


def test_qsearch_is_deterministic():
    compiled = build_4x4_rooks()
    evaluator = _evaluator(compiled)
    state = make_state(compiled, ["R..K", "....", ".r..", "k..."], side_to_move=1)
    limits = SearchLimits(quiescence_max_depth=4, quiescence_hard_max_depth=8)
    a = quiescence(state, -INF, INF, 0, 0, _ctx(compiled, evaluator, limits))
    b = quiescence(state, -INF, INF, 0, 0, _ctx(compiled, evaluator, limits))
    assert a == b
