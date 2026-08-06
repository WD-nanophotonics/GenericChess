"""Phase C: lazy successor handles differential testing vs eager path."""

import json

import pytest

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.keys import position_key
from generic_chess.core.lazy_transitions import (
    legal_successor_handles,
    materialize_legal_successor,
)
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession
from generic_chess.core.position import GameState

from ai_fixtures import build_4x4_rooks, build_mate, build_promotion
from conftest import make_state
from test_ai_search import _optimal_actions


def _canonical_set(actions):
    return sorted((json.dumps(action_to_dict(a), sort_keys=True) for a in actions))


def _evaluator(compiled):
    config = EvaluationConfig()
    return Evaluator(compiled, build_ruleset_profile(compiled, config), config)


@pytest.mark.parametrize(
    "compiled_factory",
    [build_4x4_rooks, lambda: build_mate(2), build_promotion],
    ids=["rooks4", "mate", "promotion"],
)
def test_action_sets_equal(compiled_factory):
    compiled = compiled_factory()
    state = GameSession(compiled).state
    eager_actions = [a for a, _ in legal_successors(state, compiled)]
    lazy_actions = [h.action for h in legal_successor_handles(state, compiled)]
    assert _canonical_set(lazy_actions) == _canonical_set(eager_actions)


@pytest.mark.parametrize(
    "compiled_factory",
    [build_4x4_rooks, build_promotion],
    ids=["rooks4", "promotion"],
)
def test_child_states_equal(compiled_factory):
    compiled = compiled_factory()
    state = GameSession(compiled).state
    eager = {a: c for a, c in legal_successors(state, compiled)}
    for handle in legal_successor_handles(state, compiled):
        child, child_key = materialize_legal_successor(state, handle, compiled)
        expected = eager[handle.action]
        assert child.position == expected.position
        assert child.position.side_to_move == expected.position.side_to_move
        assert child.position.hands == expected.position.hands
        assert child.repetition_counts == expected.repetition_counts
        assert child.terminal_status == expected.terminal_status
        assert child.ply_count == expected.ply_count
        assert child_key == position_key(child.position, compiled)
        assert child_key == position_key(expected.position, compiled)


def test_handle_materialization_cached():
    compiled = build_4x4_rooks()
    state = GameSession(compiled).state
    handle = legal_successor_handles(state, compiled)[0]
    first, key1 = materialize_legal_successor(state, handle, compiled)
    second, key2 = materialize_legal_successor(state, handle, compiled)
    assert first is second
    assert key1 == key2


def test_handle_rejected_on_wrong_state():
    compiled = build_4x4_rooks()
    state_a = GameSession(compiled).state
    state_b = GameSession(compiled).state
    handle = legal_successor_handles(state_a, compiled)[0]
    with pytest.raises(IllegalActionError):
        materialize_legal_successor(state_b, handle, compiled)


def test_handle_cannot_be_forged():
    from generic_chess.core.lazy_transitions import LegalSuccessorHandle

    compiled = build_4x4_rooks()
    state = GameSession(compiled).state
    with pytest.raises(TypeError):
        LegalSuccessorHandle(
            legal_successor_handles(state, compiled)[0].action,
            state,
        )
    # Even bypassing __init__ via object.__new__, materialization must refuse.
    forged = object.__new__(LegalSuccessorHandle)
    forged.action = legal_successor_handles(state, compiled)[0].action
    forged._parent = state
    forged._issuer = object()
    forged._child = None
    forged._child_key = None
    with pytest.raises(IllegalActionError):
        materialize_legal_successor(state, forged, compiled)


def _perft(compiled, state, depth):
    if depth <= 0:
        return 1
    total = 0
    for _a, child in legal_successors(state, compiled):
        total += _perft(compiled, child, depth - 1)
    return total


def _perft_lazy(compiled, state, depth):
    if depth <= 0:
        return 1
    total = 0
    for handle in legal_successor_handles(state, compiled):
        child, _key = materialize_legal_successor(state, handle, compiled)
        total += _perft_lazy(compiled, child, depth - 1)
    return total


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_perft_equal(depth):
    compiled = build_4x4_rooks()
    state = GameSession(compiled).state
    assert _perft(compiled, state, depth) == _perft_lazy(compiled, state, depth)
    assert _perft(compiled, state, depth) > 0


def _search_both(compiled, tuning_extra, max_depth=3):
    evaluator = _evaluator(compiled)
    state = GameSession(compiled).state
    results = {}
    for lazy in (False, True):
        tuning = SearchTuning(use_root_tactical=False, **{tuning_extra: lazy})
        stats = SearchStatistics()
        action, score, pv, reason = run_root_search(
            state,
            compiled,
            evaluator,
            TranspositionTable(),
            SearchLimits(max_depth=max_depth, quiescence_max_depth=0),
            None,
            stats,
            use_tt=True,
            use_ordering=True,
            tuning=tuning,
        )
        results[lazy] = (action, score, pv, stats)
    return results


def test_search_equality_baseline_rulesets():
    for factory in (build_4x4_rooks, lambda: build_mate(2), build_promotion):
        compiled = factory()
        eager = _search_both(compiled, "use_lazy_successors")[False]
        lazy = _search_both(compiled, "use_lazy_successors")[True]
        assert (eager[0], eager[1], eager[2], eager[3].completed_depth) == (
            lazy[0],
            lazy[1],
            lazy[2],
            lazy[3].completed_depth,
        )


def test_minimax_reference_equality():
    compiled = build_4x4_rooks()
    evaluator = _evaluator(compiled)
    state = GameSession(compiled).state
    ref_score, ref_actions = _optimal_actions(compiled, evaluator, 3)
    for lazy in (False, True):
        action, score, _pv, stats = _search_both(compiled, "use_lazy_successors")[lazy]
        assert score == ref_score
        assert action in ref_actions
        assert stats.completed_depth == 3


def test_history_and_in_check_equality():
    compiled = build_4x4_rooks()
    # Near-repetition context: same position key already seen twice.
    base = GameSession(compiled).state
    key = position_key(base.position, compiled)
    state = GameState(
        base.position,
        base.ply_count,
        ((key, 2),),
        base.terminal_status,
    )
    results = {}
    for lazy in (False, True):
        tuning = SearchTuning(use_root_tactical=False, use_lazy_successors=lazy)
        stats = SearchStatistics()
        action, score, pv, reason = run_root_search(
            state,
            compiled,
            _evaluator(compiled),
            TranspositionTable(),
            SearchLimits(max_depth=3, quiescence_max_depth=0),
            None,
            stats,
            use_tt=True,
            use_ordering=True,
            tuning=tuning,
        )
        results[lazy] = (action, score, pv)
    assert results[False] == results[True]


def test_in_check_search_equality():
    compiled = build_4x4_rooks()
    state = make_state(compiled, ["R..K", "....", ".r..", "k..."], side_to_move=1)
    results = {}
    for lazy in (False, True):
        tuning = SearchTuning(use_root_tactical=False, use_lazy_successors=lazy)
        stats = SearchStatistics()
        action, score, pv, reason = run_root_search(
            state,
            compiled,
            _evaluator(compiled),
            TranspositionTable(),
            SearchLimits(max_depth=3, quiescence_max_depth=2),
            None,
            stats,
            use_tt=True,
            use_ordering=True,
            tuning=tuning,
        )
        results[lazy] = (action, score, pv, stats.completed_depth)
    assert results[False] == results[True]


def test_lazy_stats_sane():
    compiled = build_4x4_rooks()
    _action, _score, _pv, stats = _search_both(compiled, "use_lazy_successors")[True]
    assert stats.successor_handles_created == stats.legal_actions_generated
    assert stats.successors_materialized <= stats.successor_handles_created
    assert stats.successors_searched == stats.successors_materialized
    assert stats.terminal_results_computed == stats.successors_materialized
    assert stats.position_keys_computed >= stats.successors_materialized
    assert stats.position_key_cache_hits >= 1  # root+materialized TT keys cached


def test_lazy_deterministic():
    compiled = build_4x4_rooks()
    a = _search_both(compiled, "use_lazy_successors")[True]
    b = _search_both(compiled, "use_lazy_successors")[True]
    assert (a[0], a[1], a[3].nodes, a[3].qnodes) == (
        b[0],
        b[1],
        b[3].nodes,
        b[3].qnodes,
    )
