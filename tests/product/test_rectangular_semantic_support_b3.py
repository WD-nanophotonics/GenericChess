from dataclasses import fields, replace
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.core.coordinates import BoardShape
from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import (
    _build_semantic_support,
    _compile_geometry_carrier,
    compile_ruleset,
    compile_semantic_ruleset,
)
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.validation import RuleValidationError
from generic_chess.rules.western_chess import build_western_chess_ruleset
from rule_semantics_ir_fixtures import cannon_ruleset
from test_rectangular_board_geometry_a import _fixture


def _rectangular_rules(width, height):
    rules = _fixture()
    rows = [[None] * width for _ in range(height)]
    rows[0][0] = Piece(0, "K", "K")
    rows[height - 1][width - 1] = Piece(1, "K", "K")
    return replace(
        rules,
        board_width=width,
        board_height=height,
        initial_position=tuple(tuple(row) for row in rows),
    )


@pytest.mark.parametrize("width,height", ((9, 10), (10, 9)))
def test_compile_only_support_preserves_rectangular_shape_and_typed_data(width, height):
    rules = _rectangular_rules(width, height)
    carrier = _compile_geometry_carrier(rules)
    support = _build_semantic_support(carrier, ruleset=rules)

    assert support.board_shape == BoardShape(width, height)
    assert support.board_width == width
    assert support.board_height == height
    assert support.board_size is None
    assert support.board_area == 90
    assert len(support.initial_position) == height
    assert all(len(row) == width for row in support.initial_position)
    assert support.initial_position[0][0] == Piece(0, "K", "K")
    assert support.initial_position[-1][-1] == Piece(1, "K", "K")
    assert set(support.type_metadata) == {"K", "P"}
    assert support.type_metadata["K"].is_anchor
    assert len(support.drop_allowed["P"][0]) == 90
    assert len(support.drop_allowed["P"][1]) == 90
    assert len(support.empty_mobility["K"][0]) == 90
    assert len(support.empty_mobility["K"][1]) == 90
    assert len(support.empty_mobility["P"][0]) == 90
    assert len(support.empty_mobility["P"][1]) == 90
    assert not any(
        isinstance(getattr(support, field.name), type(rules))
        for field in fields(support)
    )


@pytest.mark.parametrize("builder", (build_western_chess_ruleset, build_standard_shogi_ruleset))
def test_square_semantic_support_preserves_square_geometry(builder):
    # Same-era full payload hash pins are preserved in the historical snapshot.
    # Current optional action/adjudication fields have changed that payload;
    # this product regression checks the square geometry contract itself.
    support = compile_semantic_ruleset(builder()).support
    assert support.board_size is not None
    assert support.board_width is None and support.board_height is None
    assert support.board_shape == BoardShape(support.board_size, support.board_size)
    assert support.board_area == support.board_size * support.board_size


def test_carrier_must_match_ruleset_and_semantic_public_compile_uses_carrier():
    rules = _rectangular_rules(9, 10)
    carrier = _compile_geometry_carrier(rules)
    mismatched_rules = _rectangular_rules(10, 9)
    with pytest.raises(ValueError, match="does not match"):
        _build_semantic_support(carrier, ruleset=mismatched_rules)

    semantic_rules = cannon_ruleset()
    rows = [[None] * 9 for _ in range(10)]
    rows[0][0] = Piece(0, "K", "K")
    rows[9][8] = Piece(1, "K", "K")
    rectangular_semantic_rules = replace(
        semantic_rules,
        board_size=None,
        board_width=9,
        board_height=10,
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"C": ((False,) * 90, (False,) * 90)},
    )
    with pytest.raises(RuleValidationError, match="RECTANGULAR_EXECUTION_NOT_IN_A_STAGE"):
        compile_ruleset(rectangular_semantic_rules, allow_semantic_actions=True)
    compiled = compile_semantic_ruleset(rectangular_semantic_rules)
    assert compiled.board_shape.width == 9
    assert compiled.board_shape.height == 10
    assert compiled.ir.capabilities.new_ir_core_executable
    assert not compiled.ir.capabilities.legacy_core_executable
    assert not compiled.ir.capabilities.native_executable
