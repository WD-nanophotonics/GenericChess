"""RayAtom semantics: blocking, capture, anchor stop, slopes, finite range."""

from generic_chess.core.actions import BoardMove
from generic_chess.core.attacks import is_square_attacked
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.movegen import legal_actions_from_position

from conftest import king_type, make_compiled, make_position, sq, T


def _moves_from(compiled, pos, from_sq):
    return {
        a.to_square
        for a in legal_actions_from_position(pos, compiled)
        if isinstance(a, BoardMove) and a.from_square == from_sq
    }


def _compiled():
    rook = T(
        "R",
        RayAtom((0, 1)),
        RayAtom((0, -1)),
        RayAtom((1, 0)),
        RayAtom((-1, 0)),
    )
    bishop = T("B", RayAtom((1, 1)), RayAtom((1, -1)), RayAtom((-1, 1)), RayAtom((-1, -1)))
    finite = T("F", RayAtom((1, 0), max_steps=2))
    slope = T("S", RayAtom((2, 1)))
    filler = T("P", LeapAtom((0, 1)))
    return make_compiled(8, [king_type(), rook, bishop, finite, slope, filler])


def test_ray_empty_board_full_path():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "K......k",  # rank 7
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "...R....",  # rank 0
        ],
    )
    reachable = _moves_from(compiled, pos, sq(3, 0))
    assert sq(3, 7) in reachable  # full file upward
    assert sq(0, 0) in reachable  # full rank left
    assert sq(7, 0) in reachable  # full rank right
    assert sq(3, 0) not in reachable


def test_ray_friendly_block_stops():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "K......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "...P....",  # rank 1
            "...R....",  # rank 0
        ],
    )
    to = _moves_from(compiled, pos, sq(3, 0))
    assert sq(3, 1) not in to  # own piece blocks immediately
    assert sq(3, 2) not in to


def test_ray_enemy_capture_stops():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "K......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "...f....",  # rank 1
            "...R....",  # rank 0
        ],
    )
    to = _moves_from(compiled, pos, sq(3, 0))
    assert sq(3, 1) in to  # capture the enemy filler
    assert sq(3, 2) not in to  # stops after the capture


def test_ray_anchor_stops_without_capture():
    compiled = _compiled()
    # P1 anchor at (3,1): the ray stops there and attacks but never captures.
    pos = make_position(
        compiled,
        [
            "K.......",
            "........",
            "........",
            "........",
            "........",
            "........",
            "...k....",  # rank 1
            "...R....",  # rank 0
        ],
    )
    to = _moves_from(compiled, pos, sq(3, 0))
    assert sq(3, 1) not in to  # anchor cannot be captured
    assert is_square_attacked(pos, sq(3, 1), 0, compiled)  # but it is attacked


def test_ray_non_standard_slope():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "K......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "S.......",  # rank 0
        ],
    )
    to = _moves_from(compiled, pos, sq(0, 0))
    assert sq(2, 1) in to
    assert sq(4, 2) in to
    assert sq(6, 3) in to
    assert sq(1, 1) not in to  # (2,1) slope does not touch (1,1)


def test_ray_finite_range():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "K......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "F.......",  # rank 0
        ],
    )
    to = _moves_from(compiled, pos, sq(0, 0))
    assert sq(1, 0) in to
    assert sq(2, 0) in to
    assert sq(3, 0) not in to  # max_steps=2


def test_ray_blocked_by_any_occupant_precisely():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "K......k",
            "........",
            "...f....",  # rank 4
            "........",
            "........",
            "...P....",  # rank 2
            "........",
            "...R....",  # rank 0
        ],
    )
    to = _moves_from(compiled, pos, sq(3, 0))
    assert sq(3, 1) in to
    assert sq(3, 2) not in to  # own piece blocks
    assert sq(3, 3) not in to
    assert sq(3, 4) not in to


def test_bishop_diagonal_path():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "K......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            ".B......",  # rank 0
        ],
    )
    to = _moves_from(compiled, pos, sq(1, 0))
    assert sq(2, 1) in to
    assert sq(7, 6) in to  # (1,1) direction full board
    assert sq(0, 1) in to  # (-1,1) direction
