"""Retain real non-checkmate winning children before root-scan budget exhaustion."""
from dataclasses import replace
import pytest
from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import (
    _Budget, _Context, SearchAborted, root_tactical_scan,
)
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig, MATE_SCORE
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.identity import position_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.terminal import terminal_result, TerminalStatus
from generic_chess.core.transition import apply_action
from generic_chess.session.session import GameSession
from scripts.chess_development import root_from_fen


def prepared(policy):
    # Reflect the established native-terminal fixture: actual Core order now
    # encounters a stalemate before any checkmate; no filtered/reordered moves.
    original = root_from_fen('k7/2K5/8/1Q6/8/8/8/8 w - - 0 1',
        compile_ruleset_for_execution(build_builtin_ruleset('western_chess')))
    c = compile_ruleset_for_execution(replace(
        build_builtin_ruleset('western_chess'), stalemate_result=policy))
    position = replace(original.position, ruleset_fingerprint=c.ruleset_fingerprint)
    key = position_identity_key(position, c)
    state = replace(original, position=position,
        history=(HistoryRecord(key, -1, '', False),), repetition_counts=((key, 1),))
    state = replace(state, terminal_status=terminal_result(state, c))
    session = GameSession(c)
    session._state = state
    session._search_history_witnesses = (position,)
    actions = session.legal_actions()
    index, action = next((i, a) for i, a in enumerate(actions)
        if apply_action(state, a, c).terminal_status.status is TerminalStatus.STALEMATE)
    assert all(apply_action(state, a, c).terminal_status.winner is None
        for a in actions[:index])
    return session, index, action


@pytest.mark.parametrize('policy', ['draw', 'loss'])
def test_public_root_retains_winning_stalemate_at_budget_boundary(policy):
    session, index, action = prepared(policy)
    before = session.state, session.to_record(), session._search_witnesses
    d = AlphaBetaPlayer(session.compiled, use_disk_cache=False,
        use_native_semantic_legality=False).choose_action(session,
        SearchLimits(max_depth=4, max_nodes=index+1, max_time_seconds=5,
                     quiescence_max_depth=1))
    assert before == (session.state, session.to_record(), session._search_witnesses)
    assert d.root_scan_nodes == index+1
    assert d.runtime_pushes == d.runtime_pops == index+1
    assert d.runtime_depth_balanced is True
    if policy == 'loss':
        assert d.action == action
        child = apply_action(session.state, d.action, session.compiled)
        assert child.terminal_status.status is TerminalStatus.STALEMATE
        assert child.terminal_status.winner == session.state.position.side_to_move
        assert d.score == MATE_SCORE-1
        assert d.principal_variation == (action,)
        assert d.result_source == d.termination_reason == 'root_immediate_win'
        assert not d.root_scan_used_fallback
    else:
        assert d.termination_reason == 'node_limit'
        assert d.result_source == 'root_scan_fallback'
        assert d.root_scan_used_fallback
        assert d.score == 0 and d.principal_variation == ()


@pytest.mark.parametrize('policy', ['draw', 'loss'])
def test_immutable_root_scan_uses_same_authoritative_terminal_winner(policy):
    session, index, action = prepared(policy)
    c, state = session.compiled, session.state
    cfg = EvaluationConfig()
    evaluator = Evaluator(c, build_ruleset_profile(c, cfg), cfg)
    stats = SearchStatistics()
    ctx = _Context(c, evaluator, TranspositionTable(), stats,
        _Budget(SearchLimits(max_nodes=index+1, max_time_seconds=5), None),
        SearchTuning(), False, False, 1, 8, None)
    if policy == 'loss':
        immediate, _ = root_tactical_scan(state, c, evaluator, ctx)
        assert immediate == action
    else:
        with pytest.raises(SearchAborted, match='node_limit'):
            root_tactical_scan(state, c, evaluator, ctx)
    assert stats.root_scan_nodes == index+1
    assert session.state == state


@pytest.mark.parametrize('checker', [0, 1])
def test_root_retains_history_dependent_continuous_check_win(checker):
    from scripts.search_backend_comparison import CoreBoard
    c = compile_ruleset_for_execution(replace(
        build_builtin_ruleset('standard_shogi'), stalemate_result='draw'))
    setup, cycle = ('4k4/3R5/9/9/9/9/9/9/8K b - 1',
                    '6b5b 5a6a 5b6b 6a5a') if checker == 0 else (
                    'k8/9/9/9/9/9/9/5r3/4K4 w - 1',
                    '4h5h 5i4i 5h4h 4i5i')
    core = CoreBoard(dict(game='shogi', setup=setup,
        moves=' '.join((cycle.split()*3)[:-1])), c)
    session = GameSession(c)
    session._state = core.initial
    session._search_history_witnesses = core.witnesses
    before = session.state, session.to_record(), session._search_witnesses
    index, action, child = next((i, a, apply_action(session.state, a, c))
        for i, a in enumerate(session.legal_actions())
        if apply_action(session.state, a, c).terminal_status.winner ==
            session.state.position.side_to_move)
    assert child.terminal_status.status is TerminalStatus.PERPETUAL_CHECK
    assert child.terminal_status.winner == 1-checker
    d = AlphaBetaPlayer(c, use_disk_cache=False,
        use_native_semantic_legality=False).choose_action(session,
        SearchLimits(max_depth=4, max_nodes=index+1, max_time_seconds=5,
                     quiescence_max_depth=1))
    assert d.action == action and d.score == MATE_SCORE-1
    assert d.principal_variation == (action,)
    assert d.result_source == d.termination_reason == 'root_immediate_win'
    assert d.runtime_pushes == d.runtime_pops == index+1
    assert d.runtime_depth_balanced is True
    assert before == (session.state, session.to_record(), session._search_witnesses)
