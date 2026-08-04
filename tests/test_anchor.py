"""Anchor safety: attacked squares, adjacency, check detection."""

from generic_chess.core.actions import BoardMove
from generic_chess.core.attacks import is_in_check, is_square_attacked, pseudo_attacks
from generic_chess.core.movement import RayAtom
from generic_chess.core.movegen import legal_actions_from_position

from conftest import king_type, make_compiled, make_position, sq, T


def _king_rook_compiled():
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    return make_compiled(8, [king_type(), rook])


def test_king_cannot_move_into_attacked_square():
    compiled = _king_rook_compiled()
    # P1 rook at (0,3) attacks rank 3; P0 king at (4,4) is not in check.
    pos = make_position(
        compiled,
        [
            ".......k",  # rank 7
            "........",  # rank 6
            "........",  # rank 5
            "....K...",  # rank 4
            "r.......",  # rank 3
            "........",  # rank 2
            "........",  # rank 1
            "........",  # rank 0
        ],
    )
    assert not is_in_check(pos, 0, compiled)
    actions = legal_actions_from_position(pos, compiled)
    king_moves = {
        a.to_square for a in actions if isinstance(a, BoardMove) and a.from_square == sq(4, 4)
    }
    assert sq(3, 3) not in king_moves  # attacked by the rook
    assert sq(4, 3) not in king_moves
    assert sq(5, 3) not in king_moves
    assert sq(4, 5) in king_moves
    assert sq(3, 4) in king_moves


def test_king_cannot_move_adjacent_to_enemy_anchor():
    compiled = _king_rook_compiled()
    # P1 king at (5,5); P0 king at (3,3) must not step onto (4,4).
    pos = make_position(
        compiled,
        [
            "........",  # rank 7
            "........",  # rank 6
            ".....k..",  # rank 5
            "........",  # rank 4
            "...K....",  # rank 3
            "........",  # rank 2
            "........",  # rank 1
            "........",  # rank 0
        ],
    )
    actions = legal_actions_from_position(pos, compiled)
    king_moves = {
        a.to_square for a in actions if isinstance(a, BoardMove) and a.from_square == sq(3, 3)
    }
    assert sq(4, 4) not in king_moves  # adjacent to the enemy anchor
    assert sq(3, 4) in king_moves
    assert sq(4, 3) in king_moves


def test_two_anchors_never_adjacent_after_moves():
    compiled = _king_rook_compiled()
    # P0 king at (3,3), P1 king at (4,5): stepping to (4,4) would make them
    # adjacent, so it is illegal.
    pos = make_position(
        compiled,
        [
            "........",  # rank 7
            "........",  # rank 6
            "....k...",  # rank 5
            "........",  # rank 4
            "...K....",  # rank 3
            "........",  # rank 2
            "........",  # rank 1
            "........",  # rank 0
        ],
    )
    actions = legal_actions_from_position(pos, compiled)
    king_moves = {
        a.to_square for a in actions if isinstance(a, BoardMove) and a.from_square == sq(3, 3)
    }
    assert sq(4, 4) not in king_moves


def test_check_detection():
    compiled = _king_rook_compiled()
    pos = make_position(
        compiled,
        [
            ".......k",  # rank 7
            "........",  # rank 6
            "r.......",  # rank 5
            "........",  # rank 4
            "........",  # rank 3
            "........",  # rank 2
            "........",  # rank 1
            "K.......",  # rank 0
        ],
    )
    # Rook at (0,5) checks the king at (0,0) along file 0.
    assert is_in_check(pos, 0, compiled)
    assert not is_in_check(pos, 1, compiled)


def test_pinned_piece_still_attacks():
    compiled = _king_rook_compiled()
    # P0 K at (4,0), P0 R at (4,3) pinned by P1 R at (4,7).
    pos = make_position(
        compiled,
        [
            "....r...",  # rank 7
            "........",  # rank 6
            "........",  # rank 5
            "........",  # rank 4
            "....R...",  # rank 3
            "........",  # rank 2
            "........",  # rank 1
            "....K...",  # rank 0
        ],
    )
    # Pinned rook still produces a pseudo-attack on the enemy rook.
    assert is_square_attacked(pos, sq(4, 7), 0, compiled)
    assert sq(4, 7) in pseudo_attacks(pos, 0, compiled)
    # The pinned rook may not leave the file (would expose the king).
    actions = legal_actions_from_position(pos, compiled)
    rook_moves = {
        a.to_square for a in actions if isinstance(a, BoardMove) and a.from_square == sq(4, 3)
    }
    assert sq(4, 7) in rook_moves  # capture that removes the attacker is fine
    assert sq(4, 4) in rook_moves
    assert sq(3, 3) not in rook_moves  # off the pin line exposes the king
    assert sq(5, 3) not in rook_moves
