from dataclasses import replace

import pytest

from generic_chess.core.pieces import Piece
from generic_chess.core.position import HistoryRecord
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.core.transition import initial_state
from scripts.audit_exchange_custody import synthetic_state
from scripts.chess_certificate_request import chess_certificate_request


@pytest.fixture(scope='module')
def compiled():
    return compile_ruleset_for_execution(build_western_chess_ruleset())


def root(compiled, *, owner=0, base='R', current='R'):
    board = [None]*64
    board[0] = Piece(0, 'K', 'K'); board[63] = Piece(1, 'K', 'K')
    board[27 if owner == 0 else 35] = Piece(owner, base, current, base != current)
    position = replace(initial_state(compiled).position, board=tuple(board), side_to_move=owner,
                       aux_state=(((0, -1), 0), ((1, -1), 0), ((2, -1), None),
                                  ((3, -1), 0), ((4, -1), 0)))
    return synthetic_state(compiled, position)


def test_independent_diagram_and_owner_mapping_with_explicit_unverified_source(compiled):
    request = chess_certificate_request(root(compiled), compiled)
    assert request['fen'] == '7k/8/8/8/3R4/8/8/K7 w - - 0 1'
    assert request['absolute_ply'] == 0 and request['remaining_horizon'] == 1000
    assert request['max_repetition_count'] == 1 and request['source_verified'] is False
    assert len(request['state_sha256']) == 64
    assert request['local_state']['position']['board'][27]['current_type_id'] == 'R'
    black = chess_certificate_request(root(compiled, owner=1), compiled)
    assert black['fen'] == '7k/8/8/3r4/8/8/8/K7 b - - 0 1'
    assert black['state_sha256'] != request['state_sha256']


def test_external_fen_does_not_merge_local_origin_or_history_binding(compiled):
    native = root(compiled); promoted = root(compiled, base='P')
    a = chess_certificate_request(native, compiled); b = chess_certificate_request(promoted, compiled)
    assert a['fen'] == b['fen'] and a['state_sha256'] != b['state_sha256']
    # Same position/counts but a different history annotation must remain bound.
    changed = replace(native, history=(replace(native.history[0], action_signature='imported annotation'),))
    c = chess_certificate_request(changed, compiled)
    assert c['fen'] == a['fen'] and c['state_sha256'] != a['state_sha256']
    assert chess_certificate_request(native, compiled) == a


def test_missing_rights_defaults_ep_pawns_adjacent_kings_and_history_fail_closed(compiled):
    state = root(compiled)
    for aux in ((), state.position.aux_state+(((3, -1), 0),),
                tuple((k, 1 if k == (3, -1) else v) for k, v in state.position.aux_state),
                tuple((k, (3, 2) if k == (2, -1) else v) for k, v in state.position.aux_state)):
        with pytest.raises(ValueError, match='aux'):
            chess_certificate_request(replace(state, position=replace(state.position, aux_state=aux)), compiled)
    with pytest.raises(ValueError, match='pawn-free'):
        chess_certificate_request(root(compiled, base='P', current='P'), compiled)
    for changed in (replace(state, history=()), replace(state, repetition_counts=()),
                    replace(state, repetition_counts=state.repetition_counts*2),
                    replace(state, history=(HistoryRecord('wrong-key', -1, ''),))):
        with pytest.raises(ValueError, match='history|identity'):
            chess_certificate_request(changed, compiled)
    board = list(state.position.board); board[63] = None; board[1] = Piece(1, 'K', 'K')
    with pytest.raises(ValueError, match='nonadjacent'):
        chess_certificate_request(replace(state, position=replace(state.position, board=tuple(board))), compiled)


def test_stale_terminal_and_previous_mover_check_are_not_accepted(compiled):
    from generic_chess.core.terminal import TerminalResult, TerminalStatus
    state = root(compiled)
    with pytest.raises(ValueError, match='stale cached'):
        chess_certificate_request(replace(state, terminal_status=TerminalResult(TerminalStatus.STALEMATE)), compiled)
    board = list(state.position.board); board[27] = None; board[31] = Piece(0, 'R', 'R')
    # Rh4 attacks Kh8 while White is to move: previous Black move left check.
    with pytest.raises(ValueError, match='previous mover'):
        chess_certificate_request(replace(state, position=replace(state.position, board=tuple(board))), compiled)
