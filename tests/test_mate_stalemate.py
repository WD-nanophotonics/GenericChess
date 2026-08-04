"""Checkmate, stalemate, and mate-over-repetition priority."""

from generic_chess.core.attacks import is_in_check
from generic_chess.core.keys import position_key
from generic_chess.core.movegen import legal_actions_from_position
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.position import GameState
from generic_chess.core.terminal import TerminalResult, TerminalStatus, terminal_result

from conftest import king_type, make_compiled, make_position, T


def _compiled():
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    return make_compiled(8, [king_type(), rook])


def test_checkmate():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "........",
            "........",
            "r.......",
            "........",
            "........",
            "..k.....",
            "........",
            "K....r..",
        ],
        side_to_move=0,
    )
    assert is_in_check(pos, 0, compiled)
    assert legal_actions_from_position(pos, compiled) == []
    state = GameState(
        position=pos,
        ply_count=10,
        repetition_counts=((position_key(pos, compiled), 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )
    result = terminal_result(state, compiled)
    assert result.status is TerminalStatus.CHECKMATE
    assert result.winner == 1


def test_stalemate():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            ".....r..",
            "K.k.....",
        ],
        side_to_move=0,
    )
    assert not is_in_check(pos, 0, compiled)
    assert legal_actions_from_position(pos, compiled) == []
    state = GameState(
        position=pos,
        ply_count=10,
        repetition_counts=((position_key(pos, compiled), 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )
    result = terminal_result(state, compiled)
    assert result.status is TerminalStatus.STALEMATE
    assert result.winner is None


def test_ongoing():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            ".......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K.......",
        ],
    )
    state = GameState(
        position=pos,
        ply_count=0,
        repetition_counts=((position_key(pos, compiled), 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )
    assert terminal_result(state, compiled).status is TerminalStatus.ONGOING


def test_mate_takes_priority_over_repetition():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "........",
            "........",
            "r.......",
            "........",
            "........",
            "..k.....",
            "........",
            "K....r..",
        ],
        side_to_move=0,
    )
    key = position_key(pos, compiled)
    state = GameState(
        position=pos,
        ply_count=40,
        repetition_counts=((key, 4),),  # would be a repetition draw...
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )
    result = terminal_result(state, compiled)
    assert result.status is TerminalStatus.CHECKMATE  # ...but mate wins
