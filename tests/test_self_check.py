"""Self-check: moves/drops that expose the mover's anchor are illegal."""

from generic_chess.core.actions import BoardMove
from generic_chess.core.attacks import pseudo_attacks
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.movegen import legal_actions_from_position

from conftest import king_type, make_compiled, make_position, drop_move, sq, T


def _compiled():
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    filler = T("F", LeapAtom((1, 0)))
    return make_compiled(8, [king_type(), rook, filler])


_PIN = [
    "....r...",  # rank 7
    "........",  # rank 6
    "........",  # rank 5
    "........",  # rank 4
    "....R...",  # rank 3
    "........",  # rank 2
    "........",  # rank 1
    "....K...",  # rank 0
]


def test_pinned_piece_cannot_leave_pin_line():
    compiled = _compiled()
    pos = make_position(compiled, _PIN)
    actions = legal_actions_from_position(pos, compiled)
    rook_moves = {
        a.to_square for a in actions if isinstance(a, BoardMove) and a.from_square == sq(4, 3)
    }
    assert sq(4, 4) in rook_moves
    assert sq(4, 7) in rook_moves
    for target in (sq(3, 3), sq(5, 3), sq(3, 4), sq(5, 4)):
        assert target not in rook_moves


def test_pinned_piece_keeps_pseudo_attack_but_not_legality():
    compiled = _compiled()
    pos = make_position(compiled, _PIN)
    assert sq(4, 7) in pseudo_attacks(pos, 0, compiled)


def test_drop_that_blocks_check_is_legal():
    compiled = _compiled()
    # P0 king in check along file 4; hand holds one filler.
    pos = make_position(
        compiled,
        [
            "....r...",  # rank 7
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "....K...",  # rank 0
        ],
        side_to_move=0,
        hands=([("F", 1)], []),
    )
    actions = legal_actions_from_position(pos, compiled)
    assert drop_move("F", 4, 3) in actions  # blocks the check
    assert drop_move("F", 5, 5) not in actions  # does not resolve the check


def test_drop_leaving_anchor_in_check_is_illegal():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "....r...",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "....K...",
        ],
        side_to_move=0,
        hands=([("F", 1)], []),
    )
    actions = legal_actions_from_position(pos, compiled)
    assert drop_move("F", 4, 1) in actions
    assert drop_move("F", 0, 7) not in actions
