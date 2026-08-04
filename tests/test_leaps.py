"""LeapAtom semantics."""

from generic_chess.core.actions import BoardMove
from generic_chess.core.attacks import is_square_attacked, pseudo_attacks
from generic_chess.core.movement import LeapAtom
from generic_chess.core.movegen import legal_actions_from_position

from conftest import king_type, make_compiled, make_position, sq, T


def _leap_board(lines):
    leaper = T("L", LeapAtom((2, 0)))
    filler = T("F", LeapAtom((1, 0)))
    compiled = make_compiled(8, [king_type(), leaper, filler])
    pos = make_position(compiled, lines)
    return compiled, pos


_TOP = "K......."  # P0 anchor at (0,7)


def test_leap_ignores_intermediate_pieces():
    # L at (0,0); friendly filler at (1,0) between; enemy filler at (2,0).
    compiled, pos = _leap_board(
        [
            _TOP,  # rank 7
            "........",  # rank 6
            "........",  # rank 5
            "........",  # rank 4
            "........",  # rank 3
            "........",  # rank 2
            "........",  # rank 1
            "LFf....k",  # rank 0
        ]
    )
    actions = legal_actions_from_position(pos, compiled)
    assert BoardMove(sq(0, 0), sq(2, 0)) in actions  # captures past the block
    assert BoardMove(sq(0, 0), sq(1, 0)) not in actions  # own piece
    assert is_square_attacked(pos, sq(2, 0), 0, compiled)


def test_leap_cannot_land_on_own_piece():
    compiled, pos = _leap_board(
        [
            _TOP,
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "L.F....k",
        ]
    )
    actions = legal_actions_from_position(pos, compiled)
    assert BoardMove(sq(0, 0), sq(2, 0)) not in actions


def test_leap_captures_enemy_ordinary():
    compiled, pos = _leap_board(
        [
            _TOP,
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "L.f....k",
        ]
    )
    actions = legal_actions_from_position(pos, compiled)
    assert BoardMove(sq(0, 0), sq(2, 0)) in actions


def test_leap_attacks_but_never_captures_anchor():
    leaper = T("L", LeapAtom((2, 0)))
    compiled = make_compiled(8, [king_type(), leaper])
    # P1 anchor at (2,0) is attacked by the leaper but can never be captured.
    pos = make_position(
        compiled,
        [
            "K.......",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "L.k.....",
        ],
    )
    actions = legal_actions_from_position(pos, compiled)
    assert BoardMove(sq(0, 0), sq(2, 0)) not in actions
    assert is_square_attacked(pos, sq(2, 0), 0, compiled)
    assert sq(2, 0) in pseudo_attacks(pos, 0, compiled)
