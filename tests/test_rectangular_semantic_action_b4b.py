from dataclasses import replace
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.core.coordinates import BoardShape
from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import (
    _compile_geometry_carrier,
    _lower_compile_only_single_path_capture,
    compile_semantic_ruleset,
)
from generic_chess.rules.ir import (
    geometry_candidates,
    validate_executable_completeness,
    validate_ir,
)
from generic_chess.rules.validation import RuleValidationError
from rule_semantics_ir_fixtures import cannon_ruleset


def _rectangular_single_capture_ruleset():
    base = cannon_ruleset()
    shape = BoardShape(9, 10)
    rows = [[None for _ in range(shape.width)] for _ in range(shape.height)]
    rows[0][0] = Piece(0, "K", "K")
    rows[9][8] = Piece(1, "K", "K")
    mask = (False,) * shape.area
    return replace(
        base,
        board_size=None,
        board_width=shape.width,
        board_height=shape.height,
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"C": (mask, mask)},
        semantic_actions=base.semantic_actions[-1:],
    )


def test_single_9x10_path_capture_lowers_to_typed_static_ir():
    rules = _rectangular_single_capture_ruleset()
    carrier = _compile_geometry_carrier(rules)
    ir, support = _lower_compile_only_single_path_capture(carrier, rules)

    assert support.board_shape == BoardShape(9, 10)
    assert support.board_area == 90
    assert support.board_size is None
    semantic = next(pattern for pattern in ir.patterns if pattern.pattern_id.startswith("sem_"))
    assert semantic.name == "cannon_capture"
    assert semantic.target.kind == "target_enemy"
    assert [predicate.kind for predicate in semantic.path] == ["path_count_eq"]
    assert semantic.path[0].count == 1
    assert semantic.path[0].owner_filter == "any"
    assert semantic.composition == "replace_legacy"
    assert len(semantic.replaced_pattern_ids) == 4
    assert len(semantic.geometry_ids) == 4

    assert all(len(ir.geometry[gid].paths["0"]) == 90 for gid in semantic.geometry_ids)
    horizontal = next(
        ir.geometry[gid]
        for gid in semantic.geometry_ids
        if ir.geometry[gid].atom_source == ("C", 0)
    )
    assert (3, (1, 2)) in geometry_candidates(horizontal, "0", 0)

    assert not ir.capabilities.legacy_core_executable
    assert not ir.capabilities.new_ir_core_executable
    assert not ir.capabilities.native_executable
    errors = validate_ir(ir)
    errors.extend(validate_executable_completeness(ir, tuple(sorted(carrier.types_by_id))))
    assert errors == []


def test_single_path_capture_diagnostic_rejects_other_action_shapes():
    rules = _rectangular_single_capture_ruleset()
    unsupported = replace(rules, semantic_actions=rules.semantic_actions * 2)
    carrier = _compile_geometry_carrier(unsupported)
    with pytest.raises(ValueError, match="exactly one"):
        _lower_compile_only_single_path_capture(carrier, unsupported)


def test_public_semantic_compiler_still_rejects_rectangular_execution():
    with pytest.raises(RuleValidationError, match="RECTANGULAR_EXECUTION_NOT_IN_A_STAGE"):
        compile_semantic_ruleset(_rectangular_single_capture_ruleset())
