"""Constructed semantic controls; not estimates of practical occurrence rates."""
from dataclasses import replace
import pytest

from generic_chess import build_standard_shogi_ruleset, compile_ruleset_for_execution
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.position import GameState, HistoryRecord
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalResult, TerminalStatus, terminal_result, terminal_from_search_runtime
from generic_chess.core.transition import apply_action
from generic_chess.learning.shogi_rules import sfen_to_gc_state, gc_action_to_usi, gc_to_sfen
from generic_chess.session import GameSession


def fresh(position, compiled):
    key = position_identity_key(position, compiled)
    state = GameState(position, 0, ((key, 1),), TerminalResult(TerminalStatus.ONGOING),
                      (HistoryRecord(key, -1, '', False),))
    return replace(state, terminal_status=terminal_result(state, compiled))


def flipped(state, compiled):
    p = state.position
    position = replace(p, board=tuple(None if x is None else replace(x, owner=1-x.owner)
                                     for x in reversed(p.board)),
                       hands=(p.hands[1], p.hands[0]), side_to_move=1-p.side_to_move)
    return fresh(position, compiled)


class Unit:
    def evaluate(self, state):
        p = state.position
        return sum(1 if x.owner == p.side_to_move else -1 for x in p.board if x and x.current_type_id != 'K')
    def type_value(self, tid):
        return int(tid != 'K')
    def capture_order_value(self, moving, captured):
        return 10


@pytest.fixture(scope='module')
def compiled():
    return compile_ruleset_for_execution(build_standard_shogi_ruleset())


@pytest.mark.parametrize('sfen', [
    '8k/9/7+R1/9/9/9/9/9/K8 w G 1',
    '8k/6+R2/9/9/9/9/9/9/K8 w G 1',
])
@pytest.mark.parametrize('flip', [False, True])
def test_noncheck_no_move_loses_in_core_runtime_and_public_search(compiled, sfen, flip):
    state = fresh(sfen_to_gc_state(compiled, sfen).position, compiled)
    if flip:
        state = flipped(state, compiled)
    runtime = SearchPathRuntime.from_state(state, compiled, history_witnesses=(state.position,))
    assert not runtime.in_check(state.position.side_to_move)
    assert not legal_actions(state, compiled)
    assert state.terminal_status.status is TerminalStatus.STALEMATE
    assert state.terminal_status.winner == 1-state.position.side_to_move
    assert terminal_from_search_runtime(runtime) == state.terminal_status
    # The library boolean witnesses zero legal moves, not the winner mapping.
    cshogi = pytest.importorskip('cshogi')
    sfen = gc_to_sfen(state, compiled).rsplit(' ', 1)[0]+' 1'
    board = cshogi.Board(sfen)
    assert not board.is_check()
    assert list(board.legal_moves) == [] and board.is_game_over()
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = (state.position,)
    decision = AlphaBetaPlayer(compiled, evaluator_override=Unit(), use_disk_cache=False,
                               use_native_semantic_legality=False).choose_action(
        session, SearchLimits(max_depth=2, quiescence_max_depth=0))
    assert decision.action is None and decision.choice_kind == 'TERMINAL'
    assert decision.score == -1000000000


def test_parent_winning_terminal_propagates_and_ordinary_start_remains_playable(compiled):
    state = fresh(sfen_to_gc_state(compiled, '8k/9/6R2/9/9/9/9/9/K8 b G 1').position, compiled)
    assert not state.terminal_status.is_terminal
    for move in ('3c2c+', '3c3b+'):
        action = next(a for a in legal_actions(state, compiled) if gc_action_to_usi(a) == move)
        child = apply_action(state, action, compiled)
        assert child.terminal_status.winner == state.position.side_to_move
        assert child.terminal_status.status is TerminalStatus.STALEMATE
    session = GameSession(compiled)
    assert len(session.legal_actions()) == 30
    session._state = state
    session._search_history_witnesses = (state.position,)
    decision = AlphaBetaPlayer(compiled, evaluator_override=Unit(), use_disk_cache=False,
                               use_native_semantic_legality=False).choose_action(
        session, SearchLimits(max_depth=2, max_nodes=10000, max_time_seconds=10,
                             quiescence_max_depth=0, quiescence_hard_max_depth=0))
    assert decision.score == 999999999
    assert decision.action is not None
    assert apply_action(state, decision.action, compiled).terminal_status.winner == state.position.side_to_move
