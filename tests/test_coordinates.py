"""Coordinate conversion tests."""

import pytest

from generic_chess.core.coordinates import (
    BoardShape,
    Square,
    absolute_to_relative,
    add_offset,
    index_to_square,
    in_bounds,
    is_forward,
    offset_between,
    relative_to_absolute,
    rotate_offset,
    rotate_square,
    square_to_index,
)


def test_square_basics():
    a = Square(3, 4)
    b = Square(3, 4)
    c = Square(4, 3)
    assert a == b
    assert a != c
    assert hash(a) == hash(b)
    assert str(Square(4, 3)) == "e4"


def test_player0_keeps_relative_offset():
    assert relative_to_absolute((2, 1), 0) == (2, 1)
    assert absolute_to_relative((2, 1), 0) == (2, 1)


def test_player1_rotates_relative_offset():
    assert relative_to_absolute((2, 1), 1) == (-2, -1)
    assert relative_to_absolute((-2, -1), 1) == (2, 1)
    assert absolute_to_relative((2, 1), 1) == (-2, -1)


def test_rotate_round_trip():
    for offset in ((1, 0), (0, 1), (2, -3)):
        assert rotate_offset(rotate_offset(offset)) == offset


def test_rotate_square_180():
    n = 8
    for f in range(n):
        for r in range(n):
            sq = Square(f, r)
            assert rotate_square(sq, n) == Square(n - 1 - f, n - 1 - r)
            assert rotate_square(rotate_square(sq, n), n) == sq


def test_index_round_trip():
    n = 8
    for idx in range(n * n):
        assert square_to_index(index_to_square(idx, n), n) == idx
    assert index_to_square(9, 8) == Square(1, 1)


def test_add_offset_bounds():
    assert add_offset(Square(0, 0), (1, 1), 8) == Square(1, 1)
    assert add_offset(Square(0, 0), (-1, 0), 8) is None
    assert add_offset(Square(7, 7), (0, 1), 8) is None


def test_in_bounds():
    assert in_bounds(Square(0, 0), 8)
    assert not in_bounds(Square(8, 0), 8)
    assert not in_bounds(Square(0, -1), 8)


def test_rectangular_coordinates_and_rotation():
    shape = BoardShape(9, 10)
    assert shape.area == 90
    assert square_to_index(Square(0, 0), shape) == 0
    assert square_to_index(Square(8, 9), shape) == 89
    assert index_to_square(89, shape) == Square(8, 9)
    assert add_offset(Square(0, 0), (8, 9), shape) == Square(8, 9)
    assert add_offset(Square(8, 9), (1, 0), shape) is None
    assert add_offset(Square(8, 9), (0, 1), shape) is None
    assert not in_bounds(Square(9, 9), shape)
    assert not in_bounds(Square(8, 10), shape)
    assert rotate_square(Square(0, 0), shape) == Square(8, 9)
    assert rotate_square(Square(3, 2), shape) == Square(5, 7)
    assert rotate_square(rotate_square(Square(3, 2), shape), shape) == Square(3, 2)
    with pytest.raises(ValueError):
        index_to_square(90, shape)


def test_is_forward_directions():
    # Player 0 advances toward +rank; player 1 toward -rank.
    assert is_forward(Square(0, 2), Square(0, 3), 0)
    assert not is_forward(Square(0, 3), Square(0, 2), 0)
    assert is_forward(Square(0, 3), Square(0, 2), 1)
    assert not is_forward(Square(0, 2), Square(0, 3), 1)
    # Sideways is never forward.
    assert not is_forward(Square(2, 2), Square(3, 2), 0)
    assert not is_forward(Square(2, 2), Square(3, 2), 1)


def test_offset_between():
    assert offset_between(Square(1, 2), Square(4, 6)) == (3, 4)
