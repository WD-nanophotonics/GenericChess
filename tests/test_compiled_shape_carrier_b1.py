"""B1 compile-only shape carrier; no rectangular execution is enabled."""

import pytest

from generic_chess.core.coordinates import BoardShape, Square, index_to_square
from generic_chess.core.position import Position
from generic_chess.rules.compiler import _compile_geometry_carrier
from test_rectangular_board_geometry_a import _fixture


def test_b1_compile_only_carrier_preserves_rectangular_position_shape():
    carrier = _compile_geometry_carrier(_fixture())
    position = carrier.initial_position

    assert carrier.board_shape == BoardShape(9, 10)
    assert len(position.board) == carrier.board_shape.area == 90
    assert position.board_shape == BoardShape(9, 10)
    assert index_to_square(89, position.board_shape) == Square(8, 9)
    assert len(carrier.ray_paths["K"][0]) == 90
    assert len(carrier.leap_targets["K"][1]) == 90
    with pytest.raises(ValueError, match="undefined for a rectangular position"):
        position.board_size()
    with pytest.raises(TypeError):
        carrier.ray_paths["K"] = ()


def test_square_position_board_size_and_positional_constructor_unchanged():
    position = Position((None,) * 64, (), 0, "legacy-fingerprint", ())
    assert position.board_width is None
    assert position.board_height is None
    assert position.board_size() == 8
    assert position.board_shape == BoardShape(8, 8)
