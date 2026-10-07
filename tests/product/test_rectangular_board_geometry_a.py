"""A-stage geometry-only contract for true rectangular board shapes."""

from generic_chess.core.coordinates import BoardShape, Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import _basic_validation, _build_tables, compile_ruleset
from generic_chess.rules.schema import RuleSet, ruleset_from_dict, ruleset_to_dict
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset
from generic_chess.rules.validation import RuleValidationError
import pytest


def _fixture() -> RuleSet:
    shape = BoardShape(9, 10)
    king = PieceType(
        "K", "Anchor",
        (RayAtom((1, 0)), RayAtom((0, 1)), RayAtom((1, 1)),
         RayAtom((1, 2)), LeapAtom((2, 1))),
        is_anchor=True,
    )
    pawn = PieceType("P", "Token", (LeapAtom((1, 0)),))
    rows = [[None for _ in range(shape.width)] for _ in range(shape.height)]
    rows[0][0] = Piece(0, "K", "K")
    rows[9][8] = Piece(1, "K", "K")
    mask = (False,) * shape.area
    return RuleSet(
        board_size=None,
        board_width=shape.width,
        board_height=shape.height,
        piece_types=(king, pawn),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"P": (mask, mask)},
    )


def test_synthetic_9_by_10_schema_roundtrip_and_structure():
    rules = _fixture()
    assert _basic_validation(rules) == []
    data = ruleset_to_dict(rules)
    assert data["board_width"] == 9 and data["board_height"] == 10
    assert "board_size" not in data
    assert len(data["drop_allowed"]["P"][0]) == 90
    restored = ruleset_from_dict(data)
    assert ruleset_to_dict(restored) == data
    assert serialize_ruleset(deserialize_ruleset(serialize_ruleset(rules))) == serialize_ruleset(rules)

    conflicting = dict(data, board_size=9)
    with pytest.raises(RuleValidationError, match="BOARD_SHAPE_CONFLICT"):
        ruleset_from_dict(conflicting)
    incomplete = dict(data)
    del incomplete["board_height"]
    with pytest.raises(RuleValidationError, match="BOARD_SHAPE_INCOMPLETE"):
        ruleset_from_dict(incomplete)
    with pytest.raises(RuleValidationError, match="RECTANGULAR_EXECUTION_NOT_IN_A_STAGE"):
        compile_ruleset(rules)


def test_synthetic_9_by_10_compiled_geometry():
    shape = BoardShape(9, 10)
    tables = _build_tables(_fixture())
    rays = tables["ray_paths"]["K"][0]
    leaps = tables["leap_targets"]["K"][0]
    owner1_rays = tables["ray_paths"]["K"][1]
    owner1_leaps = tables["leap_targets"]["K"][1]
    mobility = tables["empty_mobility"]["K"][0]
    forward = tables["empty_forward_mobility"]["K"][0]
    idx = lambda f, r: r * shape.width + f

    assert len(rays) == shape.area == 90
    assert len(leaps) == shape.area == 90
    assert len(mobility) == len(forward) == shape.area
    assert len(rays[idx(0, 5)][0]) == 8  # horizontal reaches the file edge
    assert len(rays[idx(4, 0)][1]) == 9  # vertical reaches the rank edge
    assert len(rays[idx(0, 0)][2]) == 8  # diagonal hits file 8 first
    assert len(rays[idx(0, 0)][3]) == 4  # (1,2) diagonal hits rank 9 first
    assert leaps[idx(3, 3)][4] == (Square(5, 4),)
    assert owner1_leaps[idx(3, 3)][4] == (Square(1, 2),)
    assert len(owner1_rays[idx(8, 5)][0]) == 8
    assert len(owner1_rays[idx(4, 9)][1]) == 9
