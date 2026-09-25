from dataclasses import replace
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.core.coordinates import BoardShape, Square
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.semantic_executor import (
    SemanticEngine,
    _resolve_square_ref,
    _semantic_public_action,
    semantic_action_for,
)
from generic_chess.rules.compiler import (
    _compile_geometry_carrier,
    _lower_compile_only_ray_path_actions,
    _lower_compile_only_single_source_offset_guard,
    _compile_semantic_ruleset_from_baseline,
    compile_ruleset,
    compile_semantic_ruleset,
    lower_legacy_to_ir,
)
from generic_chess.rules.ir import (
    CompiledSquareRef,
    CompiledSemanticRuleset,
    geometry_candidates,
    validate_executable_completeness,
    validate_ir,
)
from generic_chess.rules.schema import (
    RuleDeclaration,
    RulePathConstraint,
    RuleReplaceSelector,
    RuleSet,
    RuleSpatialSelector,
    RuleStateGuard,
    RuleTypeRef,
)
from generic_chess.rules.validation import RuleValidationError
from rule_semantics_ir_fixtures import cannon_ruleset
from test_action_bound_state_guard import _horse_leg_guard_ruleset
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
    compiled = compile_semantic_ruleset(rules)
    assert compiled.ir.capabilities.new_ir_core_executable
    assert not compiled.ir.capabilities.native_executable


def test_rectangular_compile_only_horse_leg_guard_preserves_owner_relative_ref():
    horse_action = _horse_leg_guard_ruleset().semantic_actions[0]
    shape = BoardShape(9, 10)
    rows = [[None] * shape.width for _ in range(shape.height)]
    rows[0][0] = Piece(0, "G", "G")
    rows[9][8] = Piece(1, "G", "G")
    empty_drop_mask = (False,) * shape.area
    rules = RuleSet(
        board_size=None,
        board_width=shape.width,
        board_height=shape.height,
        piece_types=(
            PieceType("G", "General", (), is_anchor=True),
            PieceType("H", "Horse", (LeapAtom((2, 1)),)),
        ),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"H": (empty_drop_mask, empty_drop_mask)},
        semantic_actions=(horse_action,),
        capture_disposition="remove_from_game",
        metadata={"fixture_status": "incomplete_compile_only_guard_witness"},
    )
    carrier = _compile_geometry_carrier(rules)
    ir, support = _lower_compile_only_single_source_offset_guard(carrier, rules)

    assert support.board_shape == BoardShape(9, 10)
    pattern = next(pattern for pattern in ir.patterns if pattern.name == "horse_leg_step")
    assert len(pattern.geometry_ids) == 1
    geometry = ir.geometry[pattern.geometry_ids[0]]
    assert geometry.atom_source == ("H", 0)
    assert geometry.offset == (2, 1)
    assert len(pattern.guards) == 1
    guard = pattern.guards[0]
    assert guard.aggregation == "count"
    assert guard.owner == "any"
    assert guard.type_ref.kind == "any"
    assert guard.compare_field == "base"
    assert guard.promoted == "any"
    assert guard.location == "board"
    assert guard.comparison == "eq"
    assert guard.value == 0
    assert guard.spatial.kind == "exact"
    reference = guard.spatial.refs[0]
    assert reference.kind == "offset_from_source"
    assert reference.offset == (1, 0)
    assert reference.owner_relative is True

    center_source = 4 * 9 + 3
    assert geometry.paths["0"][center_source] == (5 * 9 + 5,)
    assert geometry.paths["1"][center_source] == (3 * 9 + 1,)
    edge_source = 8 * 9 + 7
    assert geometry.paths["0"][edge_source] == ()
    assert geometry.paths["1"][edge_source] == (7 * 9 + 5,)

    def relative_leg(owner, file, rank):
        df = 1 if owner == 0 else -1
        return rank * 9 + file + df

    assert relative_leg(0, 3, 4) == 4 * 9 + 4
    assert relative_leg(1, 3, 4) == 4 * 9 + 2
    assert relative_leg(0, 7, 8) == 8 * 9 + 8
    assert relative_leg(1, 7, 8) == 8 * 9 + 6

    assert not ir.capabilities.legacy_core_executable
    assert not ir.capabilities.new_ir_core_executable
    assert not ir.capabilities.native_executable
    assert ir.capabilities.contains_state_guard
    with pytest.raises(RuleValidationError, match="RECTANGULAR_EXECUTION_NOT_IN_A_STAGE"):
        compile_ruleset(rules, allow_semantic_actions=True)
    with pytest.raises(RuleValidationError, match="INITIAL_NO_LEGAL_MOVE"):
        compile_semantic_ruleset(rules)

    multiple_leaps = replace(
        rules,
        piece_types=tuple(
            replace(
                piece_type,
                movement_atoms=piece_type.movement_atoms + (LeapAtom((1, 2)),),
            )
            if piece_type.type_id == "H"
            else piece_type
            for piece_type in rules.piece_types
        ),
    )
    multi_carrier = _compile_geometry_carrier(multiple_leaps)
    with pytest.raises(ValueError, match="exactly one legacy leap geometry"):
        _lower_compile_only_single_source_offset_guard(multi_carrier, multiple_leaps)


def test_public_semantic_compiler_uses_shape_carrier_but_legacy_compile_stays_closed():
    compiled = compile_semantic_ruleset(_rectangular_single_capture_ruleset())
    assert compiled.board_shape == BoardShape(9, 10)
    assert compiled.ir.capabilities.new_ir_core_executable
    assert not compiled.ir.capabilities.legacy_core_executable
    assert not compiled.ir.capabilities.native_executable
    with pytest.raises(RuleValidationError, match="RECTANGULAR_EXECUTION_NOT_IN_A_STAGE"):
        compile_ruleset(_rectangular_single_capture_ruleset(), allow_semantic_actions=True)


def test_shared_semantic_lowering_accepts_shape_carrier_without_enabling_execution():
    base = _horse_leg_guard_ruleset()
    shape = BoardShape(9, 10)
    rows = [[None] * shape.width for _ in range(shape.height)]
    rows[0][0] = Piece(0, "K", "K")
    rows[9][8] = Piece(1, "K", "K")
    zone_squares = ((1, 0), (4, 5), (8, 9))
    zone_guard = RuleStateGuard(
        aggregation="count",
        owner="any",
        type_ref=RuleTypeRef(kind="any"),
        compare_field="base",
        promoted="any",
        location="board",
        spatial=RuleSpatialSelector(kind="zone", zone_squares=zone_squares),
        comparison="eq",
        value=0,
    )
    base_action = base.semantic_actions[0]
    action = replace(
        base_action,
        state_guards=base_action.state_guards + (zone_guard,),
    )
    rules = replace(
        base,
        board_size=None,
        board_width=shape.width,
        board_height=shape.height,
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"H": ((False,) * shape.area, (False,) * shape.area)},
        semantic_actions=(action,),
        declarations=(
            RuleDeclaration("rectangular_zone", owner=0, state_guards=(zone_guard,)),
        ),
    )
    carrier = _compile_geometry_carrier(rules)
    compiled = _compile_semantic_ruleset_from_baseline(carrier, rules)

    assert compiled.ruleset_fingerprint == carrier.ruleset_fingerprint
    assert compiled._legacy_compiled is carrier
    assert compiled.support.board_shape == shape
    assert len(compiled.support.initial_position) == shape.height
    assert len(compiled.support.initial_position[-1]) == shape.width
    assert compiled.ir.zones["z0"].squares == (1, 49, 89)
    assert compiled.ir.declarations[0].zones["dzone0"].squares == (1, 49, 89)
    pattern = next(p for p in compiled.ir.patterns if p.name == "horse_leg_step")
    assert len(pattern.guards) == 2
    assert pattern.guards[0].spatial.refs[0].kind == "offset_from_source"
    assert pattern.guards[1].spatial.zone_id == "z0"
    geometry = compiled.ir.geometry[pattern.geometry_ids[0]]
    assert geometry.atom_source == ("H", 0)
    assert geometry.paths["0"][4 * 9 + 3] == (5 * 9 + 5,)
    assert geometry.paths["1"][4 * 9 + 3] == (3 * 9 + 1,)
    assert all(
        not getattr(compiled.ir.capabilities, capability)
        for capability in (
            "legacy_core_executable",
            "new_ir_core_executable",
            "native_executable",
        )
    )
    assert all(
        len(paths) == shape.area
        for geometry in compiled.ir.geometry.values()
        for paths in geometry.paths.values()
    )

    public_compiled = compile_semantic_ruleset(rules)
    assert public_compiled.ir.capabilities.new_ir_core_executable
    assert not public_compiled.ir.capabilities.native_executable
    with pytest.raises(ValueError, match="does not match"):
        _compile_semantic_ruleset_from_baseline(
            carrier, replace(rules, max_ply=rules.max_ply + 1)
        )


def _rectangular_horse_executor_witness():
    base = _horse_leg_guard_ruleset()
    shape = BoardShape(9, 10)
    rows = [[None] * shape.width for _ in range(shape.height)]
    rows[0][0] = Piece(0, "K", "K")
    rows[9][8] = Piece(1, "K", "K")
    rules = replace(
        base,
        board_size=None,
        board_width=shape.width,
        board_height=shape.height,
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={
            "H": ((False,) * shape.area, (False,) * shape.area)
        },
    )
    carrier = _compile_geometry_carrier(rules)
    ir, support = _lower_compile_only_single_source_offset_guard(carrier, rules)
    # Exercise only the already-precompiled Python executor seam. Keep the
    # compiler's rectangular execution capability flags fail-closed.
    semantic = CompiledSemanticRuleset(ir=ir, support=support)
    engine = SemanticEngine.__new__(SemanticEngine)
    engine.semantic = semantic
    engine.ir = ir
    engine.support = support
    engine._patterns = ir.patterns
    return engine


@pytest.mark.parametrize(
    "owner,source,target,leg,target_square",
    [
        (0, 4 * 9 + 3, 5 * 9 + 5, 4 * 9 + 4, Square(5, 5)),
        (1, 5 * 9 + 5, 4 * 9 + 3, 5 * 9 + 4, Square(3, 4)),
    ],
)
def test_python_executor_resolves_rectangular_horse_leg_and_trial_shape(
    owner, source, target, leg, target_square
):
    from generic_chess.core.coordinates import index_to_square

    engine = _rectangular_horse_executor_witness()
    assert not engine.ir.capabilities.new_ir_core_executable
    assert not engine.ir.capabilities.legacy_core_executable
    assert not engine.ir.capabilities.native_executable
    position = engine._initial_position()
    board = list(position.board)
    board[source] = Piece(owner, "H", "H")
    position = replace(
        position,
        board=tuple(board),
        side_to_move=owner,
    )

    assert position.board_shape == BoardShape(9, 10)
    actions = tuple(engine.iter_legal_action_bindings(position))
    action, binding = next(
        (action, binding)
        for action, binding in actions
        if action.pattern_id.endswith("horse_leg_step") and action.target == target
    )
    assert index_to_square(action.target, engine.support.board_shape) == target_square
    public_action = _semantic_public_action(engine, action)
    assert public_action.from_square == index_to_square(
        source, engine.support.board_shape
    )
    assert public_action.to_square == target_square
    assert semantic_action_for(engine, position, public_action) == action
    guard_ref = next(
        pattern for pattern in engine._patterns
        if pattern.name == "horse_leg_step"
    ).guards[0].spatial.refs[0]
    assert _resolve_square_ref(
        guard_ref, engine.support, engine.ir.aux_slots,
        position, owner, binding,
    ) == leg

    child = engine._trial_child_if_s3_legal(
        binding.pattern, position, action, binding
    )
    assert child is not None
    assert child.board_shape == BoardShape(9, 10)
    assert len(child.board) == 90
    assert child.side_to_move == 1 - owner
    assert child.board[target] == Piece(owner, "H", "H")
    assert child.board[source] is None

    blocked_board = list(position.board)
    blocked_board[leg] = Piece(1 - owner, "H", "H")
    blocked = replace(position, board=tuple(blocked_board))
    assert not any(
        action.pattern_id.endswith("horse_leg_step") and action.target == target
        for action in engine.legal_actions(blocked)
    )


def test_python_executor_rectangular_offset_ref_is_none_out_of_bounds():
    from types import SimpleNamespace

    engine = _rectangular_horse_executor_witness()
    guard_ref = next(
        pattern for pattern in engine._patterns
        if pattern.name == "horse_leg_step"
    ).guards[0].spatial.refs[0]
    binding = SimpleNamespace(
        source=4 * 9 + 8,
        target=5 * 9 + 8,
        path=(),
    )
    assert _resolve_square_ref(
        guard_ref, engine.support, engine.ir.aux_slots,
        engine._initial_position(), 0, binding,
    ) is None


def test_python_executor_resolves_fixed_refs_with_rectangular_rotation():
    from types import SimpleNamespace

    engine = _rectangular_horse_executor_witness()
    position = engine._initial_position()
    binding = SimpleNamespace(source=0, target=1, path=())
    fixed = CompiledSquareRef(
        kind="fixed", square=(7, 2), owner_relative=True
    )
    assert _resolve_square_ref(
        fixed, engine.support, engine.ir.aux_slots,
        position, 0, binding,
    ) == 2 * 9 + 7
    assert _resolve_square_ref(
        fixed, engine.support, engine.ir.aux_slots,
        position, 1, binding,
    ) == 7 * 9 + 1


def test_semantic_support_reuses_shape_and_source_offset_results():
    from types import SimpleNamespace

    square_semantic = compile_semantic_ruleset(_horse_leg_guard_ruleset())
    square_support = square_semantic.support
    square_pattern = next(
        pattern for pattern in square_semantic.ir.patterns
        if pattern.name == "horse_leg_step"
    )
    square_ref = square_pattern.guards[0].spatial.refs[0]
    square_binding = SimpleNamespace(source=3 * 8 + 3, target=4 * 8 + 5, path=())

    rectangular_engine = _rectangular_horse_executor_witness()
    rectangular_support = rectangular_engine.support
    rectangular_pattern = next(
        pattern for pattern in rectangular_engine.ir.patterns
        if pattern.name == "horse_leg_step"
    )
    rectangular_ref = rectangular_pattern.guards[0].spatial.refs[0]
    rectangular_binding = SimpleNamespace(
        source=4 * 9 + 3, target=5 * 9 + 5, path=()
    )

    assert square_support.board_shape == BoardShape(8, 8)
    assert square_support.board_shape is square_support.board_shape
    assert rectangular_support.board_shape == BoardShape(9, 10)
    assert rectangular_support.board_shape is rectangular_support.board_shape
    assert _resolve_square_ref(
        square_ref, square_support, square_semantic.ir.aux_slots,
        None, 0, square_binding,
    ) == 3 * 8 + 4
    assert _resolve_square_ref(
        rectangular_ref, rectangular_support, rectangular_engine.ir.aux_slots,
        None, 0, rectangular_binding,
    ) == 4 * 9 + 4
