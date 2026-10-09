"""Public-player bounds must belong to the caller's q semantics."""
import pytest

from ai_fixtures import build_4x4_rooks
from conftest import make_state
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession


def _player(compiled):
    return AlphaBetaPlayer(
        compiled, use_disk_cache=False, use_native_semantic_legality=False,
        tuning=SearchTuning(use_root_tactical=False),
    )


def _limits(q):
    return SearchLimits(max_depth=2, max_nodes=65536,
                        quiescence_max_depth=q,
                        quiescence_hard_max_depth=8 if q else 0)


@pytest.mark.parametrize("order", [(0, 2), (2, 0)])
def test_changed_q_semantics_match_cold_search(order):
    compiled = build_4x4_rooks()
    session = GameSession(compiled)
    state = make_state(compiled, ["....", "R...", "....", "K.k."],
                       hands=([("R", 1)], ()))
    session._state = state
    session._search_history_witnesses = (state.position,)
    cold = _player(compiled).choose_action(session, _limits(order[1]))
    player = _player(compiled)
    first = player.choose_action(session, _limits(order[0]))
    warm = player.choose_action(session, _limits(order[1]))
    assert first.completed_depth == cold.completed_depth == warm.completed_depth == 2
    assert cold.score != first.score  # This fixture distinguishes the q meanings.
    assert warm.score == cold.score
    assert warm.action == cold.action
    assert session.state == state


def test_unchanged_q_keeps_warm_bounds():
    compiled = build_4x4_rooks()
    session = GameSession(compiled)
    player = _player(compiled)
    first = player.choose_action(session, _limits(2))
    warm = player.choose_action(session, _limits(2))
    assert first.completed_depth == warm.completed_depth == 2
    assert first.score == warm.score
    assert warm.nodes + warm.qnodes < first.nodes + first.qnodes


def test_changed_hard_q_depth_preserves_abort():
    compiled = build_4x4_rooks()
    session = GameSession(compiled)
    state = make_state(compiled, ["....", "R...", "....", "K.k."],
                       hands=([("R", 1)], ()))
    session._state = state
    session._search_history_witnesses = (state.position,)
    deep = SearchLimits(max_depth=2, quiescence_max_depth=1,
                        quiescence_hard_max_depth=8)
    shallow = SearchLimits(max_depth=2, quiescence_max_depth=1,
                           quiescence_hard_max_depth=1)
    cold = _player(compiled).choose_action(session, shallow)
    player = _player(compiled)
    first = player.choose_action(session, deep)
    warm = player.choose_action(session, shallow)
    assert first.completed_depth == 2
    assert cold.termination_reason == "qsearch_check_hard_limit"
    assert (warm.score, warm.completed_depth, warm.termination_reason) == (
        cold.score, cold.completed_depth, cold.termination_reason)
