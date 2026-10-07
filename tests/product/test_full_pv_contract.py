"""Opt-in principal replay preserves complete explanations through TT reuse."""
import pytest

from ai_fixtures import build_4x4_rooks, build_mate
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import reference_minimax
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession


def _replay(compiled, decision, history=()):
    session = GameSession(compiled)
    for record in history:
        session.submit(record.action)
    for action in decision.principal_variation:
        assert action in session.legal_actions()
        session.submit(action)
    assert (len(decision.principal_variation) >= decision.completed_depth
            or session.state.terminal_status.is_terminal)


@pytest.mark.parametrize('pvs', [False, True])
@pytest.mark.parametrize('aspiration', [False, True])
@pytest.mark.parametrize('capacity', [1, 250000])
def test_warm_full_pv_preserves_reference_score_and_legal_depth(pvs, aspiration, capacity):
    compiled = build_4x4_rooks()
    session = GameSession(compiled)
    player = AlphaBetaPlayer(compiled, use_disk_cache=False, tt_max_entries=capacity,
        tuning=SearchTuning(require_full_pv=True, use_root_tactical=False,
                            use_pvs=pvs, use_aspiration=aspiration,
                            aspiration_start_depth=2))
    limits = SearchLimits(max_depth=3, max_nodes=20000, quiescence_max_depth=0)
    score, _ = reference_minimax(session.state, 3, player._evaluator, compiled)
    for _ in range(2):
        decision = player.choose_action(session, limits)
        assert decision.completed_depth == 3
        assert decision.score == score
        assert decision.action == decision.principal_variation[0]
        _replay(compiled, decision)
    if capacity > 1:
        assert decision.tt_hits > 0


def test_default_score_action_cache_contract_is_preserved():
    compiled = build_4x4_rooks()
    player = AlphaBetaPlayer(compiled, use_disk_cache=False,
                             tuning=SearchTuning(use_root_tactical=False))
    session = GameSession(compiled)
    limits = SearchLimits(max_depth=3, quiescence_max_depth=0)
    cold = player.choose_action(session, limits)
    warm = player.choose_action(session, limits)
    assert (warm.score, warm.action) == (cold.score, cold.action)
    assert warm.principal_variation == ()


def test_full_pv_may_end_at_real_terminal_before_target_depth():
    compiled = build_mate(2)
    player = AlphaBetaPlayer(compiled, use_disk_cache=False,
        tuning=SearchTuning(require_full_pv=True, use_root_tactical=False,
                            use_pvs=True, use_mate_distance_pruning=True))
    session = GameSession(compiled)
    limits = SearchLimits(max_depth=3, quiescence_max_depth=0)
    for _ in range(2):
        decision = player.choose_action(session, limits)
        _replay(compiled, decision)


def test_full_pv_reuse_preserves_same_board_different_history_frontiers():
    from test_native_history import _cycle_ruleset, _session_at_ply
    compiled = _cycle_ruleset()
    player = AlphaBetaPlayer(compiled, use_disk_cache=False,
        tuning=SearchTuning(require_full_pv=True, use_root_tactical=False,
                            use_pvs=True, use_aspiration=True,
                            aspiration_start_depth=2))
    limits = SearchLimits(max_depth=4, quiescence_max_depth=0)
    for ply in (3, 11, 3):
        session = _session_at_ply(compiled, ply)
        for _ in range(2):
            decision = player.choose_action(session, limits)
            assert decision.completed_depth == 4
            assert len(decision.principal_variation) == (1 if ply == 11 else 4)
            _replay(compiled, decision, session.history)


def test_warm_full_pv_does_not_override_user_cancellation():
    from generic_chess.ai.cancellation import CancellationToken
    compiled = build_4x4_rooks()
    session = GameSession(compiled)
    player = AlphaBetaPlayer(compiled, use_disk_cache=False,
        tuning=SearchTuning(require_full_pv=True, use_root_tactical=False))
    limits = SearchLimits(max_depth=3, quiescence_max_depth=0)
    player.choose_action(session, limits)
    token = CancellationToken()
    token.cancel()
    cancelled = player.choose_action(session, limits, cancel_token=token)
    assert cancelled.termination_reason == 'cancelled'
    assert cancelled.completed_depth == 0
    assert cancelled.principal_variation == ()
