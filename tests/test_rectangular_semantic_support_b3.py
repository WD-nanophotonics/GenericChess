import hashlib
import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from enum import Enum
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.core.coordinates import BoardShape
from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import (
    _build_semantic_support,
    _compile_geometry_carrier,
    compile_ruleset,
    compile_semantic_ruleset,
)
from generic_chess.rules.ir import CompiledSemanticSupport
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


def _normalize(value):
    if is_dataclass(value):
        selected_fields = fields(value)
        if isinstance(value, CompiledSemanticSupport):
            selected_fields = tuple(
                field for field in selected_fields
                if field.name not in ("board_width", "board_height")
            )
        return {
            field.name: _normalize(getattr(value, field.name))
            for field in selected_fields
        }
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_normalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        rows = [_normalize(item) for item in value]
        return sorted(
            rows,
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(type(value).__name__)


def _support_hash(support):
    serialized = json.dumps(
        _normalize(support), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


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


@pytest.mark.parametrize(
    "builder,expected_hash",
    (
        (
            build_western_chess_ruleset,
            "195b09f35794613e499ca6312e186b1c5d65ba17fd29be951b922f9e90fb11b5",
        ),
        (
            build_standard_shogi_ruleset,
            "e0016d0abf414cd69be618066c932317a7feefcf033bc310424bcb7c33c6b30a",
        ),
    ),
)
def test_square_semantic_support_identity_matches_prechange_hash(builder, expected_hash):
    support = compile_semantic_ruleset(builder()).support
    assert support.board_size is not None
    assert support.board_width is None and support.board_height is None
    assert support.board_shape == BoardShape(support.board_size, support.board_size)
    assert support.board_area == support.board_size * support.board_size
    assert _support_hash(support) == expected_hash


def test_carrier_must_match_ruleset_and_public_rectangular_execution_stays_closed():
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
    with pytest.raises(RuleValidationError, match="RECTANGULAR_EXECUTION_NOT_IN_A_STAGE"):
        compile_semantic_ruleset(rectangular_semantic_rules)
