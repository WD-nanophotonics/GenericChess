from dataclasses import replace
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.core.coordinates import BoardShape
from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import (
    _compile_geometry_carrier,
    _lower_compile_only_ray_path_actions,
    compile_ruleset,
    compile_semantic_ruleset,
    lower_legacy_to_ir,
)
from generic_chess.rules.ir import (
    geometry_candidates,
    validate_executable_completeness,
    validate_ir,
)
from generic_chess.rules.schema import RulePathConstraint, RuleReplaceSelector
from generic_chess.rules.validation import RuleValidationError
from rule_semantics_ir_fixtures import cannon_ruleset
from test_xiangqi_static_setup_fixture import (
    MOVEMENT_ATOMS,
    _build_incomplete_static_xiangqi_setup_fixture,
)


def _rectangular_single_capture_ruleset(path_constraint=None):
    base = cannon_ruleset()
    shape = BoardShape(9, 10)
    rows = [[None for _ in range(shape.width)] for _ in range(shape.height)]
    rows[0][0] = Piece(0, "K", "K")
    rows[9][8] = Piece(1, "K", "K")
    mask = (False,) * shape.area
    capture = base.semantic_actions[-1]
    if path_constraint is not None:
        capture = replace(capture, path_constraints=(path_constraint,))
    return replace(
        base,
        board_size=None,
        board_width=shape.width,
        board_height=shape.height,
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"C": (mask, mask)},
        semantic_actions=(capture,),
    )


def test_single_9x10_path_capture_lowers_to_typed_static_ir():
    rules = _rectangular_single_capture_ruleset()
    carrier = _compile_geometry_carrier(rules)
    ir, support = _lower_compile_only_ray_path_actions(carrier, rules)

    assert support.board_shape == BoardShape(9, 10)
    assert support.board_area == 90
    assert support.board_size is None
    semantic = next(pattern for pattern in ir.patterns if pattern.pattern_id.startswith("sem_"))
    assert semantic.name == "cannon_capture"
    assert semantic.target.kind == "target_enemy"
    assert [predicate.kind for predicate in semantic.path] == ["path_count_eq"]
    assert semantic.path[0].count == 1
    assert semantic.path[0].owner_filter == "any"
    assert semantic.effects[0].disposition == "capture_to_hand"
    assert semantic.composition == "replace_legacy"
    assert len(semantic.replaced_pattern_ids) == 4
    assert len(semantic.geometry_ids) == 4

    square_ir = compile_semantic_ruleset(cannon_ruleset()).ir
    square_capture = next(
        pattern for pattern in square_ir.patterns if pattern.name == "cannon_capture"
    )
    assert semantic.effects == square_capture.effects
    assert semantic.invariants == square_capture.invariants
    assert semantic.promotion_mode == square_capture.promotion_mode
    assert semantic.explicit_promotion_type == square_capture.explicit_promotion_type

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
    with pytest.raises(ValueError, match="one quiet and one capture"):
        _lower_compile_only_ray_path_actions(carrier, unsupported)


def test_rectangular_path_clear_is_lowered_from_the_rule_dsl():
    rules = _rectangular_single_capture_ruleset(
        RulePathConstraint("path_clear")
    )
    carrier = _compile_geometry_carrier(rules)
    ir, _ = _lower_compile_only_ray_path_actions(carrier, rules)
    semantic = next(pattern for pattern in ir.patterns if pattern.pattern_id.startswith("sem_"))

    assert len(semantic.path) == 1
    assert semantic.path[0].kind == "path_clear"
    assert semantic.path[0].count is None
    assert semantic.path[0].owner_filter == "any"


def _incomplete_xiangqi_cannon_path_pair():
    base = _build_incomplete_static_xiangqi_setup_fixture()
    quiet, capture = cannon_ruleset().semantic_actions
    quiet = replace(
        quiet,
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("C",),
            action_family="board",
            target_relation="empty",
            geometry_kind="ray",
            replace_all_matching=True,
        ),
    )
    capture = replace(
        capture,
        effects=(
            replace(capture.effects[0], disposition="remove_from_game"),
            capture.effects[1],
        ),
    )
    return replace(base, semantic_actions=(quiet, capture))


def test_xiangqi_quiet_and_one_screen_capture_lower_to_distinct_static_ir():
    rules = _incomplete_xiangqi_cannon_path_pair()
    carrier = _compile_geometry_carrier(rules)
    ir, support = _lower_compile_only_ray_path_actions(carrier, rules)

    assert support.board_shape == BoardShape(9, 10)
    assert support.board_area == 90
    assert support.board_size is None
    assert rules.metadata["fixture_status"] == "incomplete_static_fixture"
    assert set(carrier.types_by_id) == set(MOVEMENT_ATOMS)
    assert set(carrier.types_by_id) == {"G", "A", "E", "R", "H", "C", "P"}
    baseline_ir = lower_legacy_to_ir(carrier, ruleset=rules)
    non_anchor_types = {"A", "E", "R", "H", "C", "P"}
    baseline_captures = [
        pattern
        for pattern in baseline_ir.patterns
        if pattern.target.kind == "target_enemy"
        and pattern.type_ids[0] in non_anchor_types
    ]
    assert baseline_captures
    assert all(
        next(effect for effect in pattern.effects if effect.kind == "remove").disposition
        == "remove_from_game"
        for pattern in baseline_captures
    )
    assert not ir.capabilities.legacy_core_executable
    assert not ir.capabilities.new_ir_core_executable
    assert not ir.capabilities.native_executable
    assert ir.capabilities.contains_path_predicate

    quiet, capture = (
        next(pattern for pattern in ir.patterns if pattern.name == name)
        for name in ("cannon_quiet", "cannon_capture")
    )
    assert quiet.target.kind == "target_empty"
    assert [(path.kind, path.count) for path in quiet.path] == [("path_clear", None)]
    assert [effect.kind for effect in quiet.effects] == ["move"]
    assert quiet.effects[0].from_ref.kind == "source"
    assert quiet.effects[0].to_ref.kind == "target"
    assert quiet.composition == "replace_legacy"
    assert len(quiet.replaced_pattern_ids) == 4

    assert capture.target.kind == "target_enemy"
    assert [(path.kind, path.count) for path in capture.path] == [
        ("path_count_eq", 1)
    ]
    assert [effect.kind for effect in capture.effects] == ["remove", "move"]
    assert capture.effects[0].square_ref.kind == "target"
    assert capture.effects[0].piece_owner == "opponent"
    assert capture.effects[0].disposition == "remove_from_game"
    assert capture.effects[1].from_ref.kind == "source"
    assert capture.effects[1].to_ref.kind == "target"
    assert capture.composition == "replace_legacy"
    assert len(capture.replaced_pattern_ids) == 4
    assert not set(quiet.replaced_pattern_ids) & set(capture.replaced_pattern_ids)
    legacy_by_id = {
        pattern.pattern_id: pattern
        for pattern in lower_legacy_to_ir(carrier, ruleset=rules).patterns
    }
    for semantic in (quiet, capture):
        assert semantic.type_ids == ("C",)
        assert len(semantic.geometry_ids) == 4
        assert {
            ir.geometry[gid].atom_source[0] for gid in semantic.geometry_ids
        } == {"C"}
        assert all(
            ir.geometry[gid].kind == "ray" for gid in semantic.geometry_ids
        )
        replaced = [
            legacy_by_id[pattern_id]
            for pattern_id in semantic.replaced_pattern_ids
        ]
        assert len(replaced) == 4
        assert all(
            pattern.type_ids == ("C",)
            and pattern.target.kind == semantic.target.kind
            and all(ir.geometry[gid].kind == "ray" for gid in pattern.geometry_ids)
            for pattern in replaced
        )

    horizontal = next(
        ir.geometry[gid]
        for gid in capture.geometry_ids
        if ir.geometry[gid].atom_source == ("C", 0)
    )
    source = 4 * 9 + 1
    candidates = dict(geometry_candidates(horizontal, "0", source))
    assert candidates[4 * 9 + 3] == (4 * 9 + 2,)
    assert candidates[4 * 9 + 4] == (4 * 9 + 2, 4 * 9 + 3)

    errors = validate_ir(ir)
    errors.extend(validate_executable_completeness(ir, tuple(sorted(carrier.types_by_id))))
    assert errors == []
    with pytest.raises(RuleValidationError, match="RECTANGULAR_EXECUTION_NOT_IN_A_STAGE"):
        compile_ruleset(rules, allow_semantic_actions=True)
    with pytest.raises(RuleValidationError, match="RECTANGULAR_EXECUTION_NOT_IN_A_STAGE"):
        compile_semantic_ruleset(rules)


def test_public_semantic_compiler_still_rejects_rectangular_execution():
    with pytest.raises(RuleValidationError, match="RECTANGULAR_EXECUTION_NOT_IN_A_STAGE"):
        compile_semantic_ruleset(_rectangular_single_capture_ruleset())
