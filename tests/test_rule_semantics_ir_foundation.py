"""Phase 1.9B-1: production semantic IR foundation tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import (
    build_geometry_metadata,
    compile_ruleset,
    compile_semantic_ir,
    compile_semantic_ruleset,
)
from generic_chess.rules.ir import (
    COMPILED_SEMANTIC_IR_VERSION,
    MAX_PROBE_STRATUM,
)
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleAuxState,
    RuleInvariant,
    RulePathConstraint,
    RulePostcondition,
    RuleSemanticAction,
    RuleSet,
    RuleSlotGuard,
    RuleStateGuard,
    ruleset_from_dict,
    ruleset_to_dict,
)


ROOT = Path(__file__).resolve().parent.parent


def _semantic_ruleset(piece_types, actions, n=8):
    """Valid RuleSet: two anchors, all-false drop masks for non-anchors."""
    rows = []
    for rank in range(n):
        row = []
        for file in range(n):
            if (rank, file) == (0, 0):
                row.append(Piece(0, "K", "K"))
            elif (rank, file) == (n - 1, n - 1):
                row.append(Piece(1, "K", "K"))
            else:
                row.append(None)
        rows.append(tuple(row))
    drop_allowed = {}
    for pt in piece_types:
        if not pt.is_anchor:
            drop_allowed[pt.type_id] = ((False,) * (n * n), (False,) * (n * n))
    return RuleSet(
        board_size=n,
        piece_types=piece_types,
        initial_position=tuple(rows),
        drop_allowed=drop_allowed,
        semantic_actions=actions,
    )


def _ray_type(tid, atoms):
    return PieceType(tid, tid, atoms)


def _king():
    return PieceType(
        "K",
        "K",
        tuple(
            LeapAtom((df, dr))
            for df in (-1, 0, 1)
            for dr in (-1, 0, 1)
            if df or dr
        ),
        is_anchor=True,
    )


def _own_anchor():
    return (RuleInvariant("own_anchor_safe"),)


def _cannon_ruleset():
    cannon = _ray_type(
        "C",
        (RayAtom((1, 0)), RayAtom((-1, 0)), RayAtom((0, 1)), RayAtom((0, -1))),
    )
    quiet = RuleSemanticAction(
        name="cannon_quiet",
        type_ids=("C",),
        geometry=("ray",),
        target_relation="empty",
        path_constraints=(RulePathConstraint("path_clear"),),
        effects=(RuleActionEffect("move"),),
        invariants=_own_anchor(),
    )
    capture = RuleSemanticAction(
        name="cannon_capture",
        type_ids=("C",),
        geometry=("ray",),
        target_relation="enemy",
        path_constraints=(RulePathConstraint("path_count_eq", count=1),),
        effects=(RuleActionEffect("remove", "target"), RuleActionEffect("move")),
        invariants=_own_anchor(),
    )
    return _semantic_ruleset((_king(), cannon), (quiet, capture))


def _castling_ruleset():
    king = _king()
    right = RuleAuxState(name="king_right", kind="right", lifetime="persistent")
    castle = RuleSemanticAction(
        name="king_side_shift",
        type_ids=("K",),
        geometry=("leap",),
        target_relation="empty",
        path_constraints=(RulePathConstraint("path_clear"),),
        slot_guards=(RuleSlotGuard("king_right", "eq", 1),),
        aux_state=(right,),
        effects=(
            RuleActionEffect("move"),
            RuleActionEffect("move", "partner_square"),
            RuleActionEffect("clear_right", slot_name="king_right"),
        ),
        invariants=(RuleInvariant("squares_not_attacked", ("SOURCE", "TARGET")),),
    )
    return _semantic_ruleset((king,), (castle,))


def _en_passant_ruleset():
    pawn = _ray_type("P", (RayAtom((0, 1)),))
    token = RuleAuxState(name="ep_token", kind="token_square", lifetime="expire_next_turn")
    creation = RuleSemanticAction(
        name="double_step_creates_token",
        type_ids=("P",),
        geometry=("ray",),
        target_relation="empty",
        path_constraints=(RulePathConstraint("path_clear"),),
        aux_state=(token,),
        effects=(RuleActionEffect("move"), RuleActionEffect("set_token", slot_name="ep_token")),
        invariants=_own_anchor(),
    )
    capture = RuleSemanticAction(
        name="token_adjacent_capture_removes_off_target",
        type_ids=("P",),
        geometry=("leap",),
        target_relation="enemy",
        slot_guards=(RuleSlotGuard("ep_token", "eq", 0),),
        aux_state=(token,),
        effects=(
            RuleActionEffect("move"),
            RuleActionEffect("remove", "token"),
            RuleActionEffect("clear_token", slot_name="ep_token"),
        ),
        invariants=_own_anchor(),
    )
    return _semantic_ruleset((_king(), pawn), (creation, capture))


def _nifu_ruleset():
    pawn = _ray_type("P", (RayAtom((0, 1)),))
    guard = RuleStateGuard(
        aggregation="count",
        owner="self",
        type_mode="base",
        promoted="no",
        location="board",
        spatial="same_file",
        spatial_ref="TARGET",
        comparison="eq",
        value=0,
    )
    action = RuleSemanticAction(
        name="drop_file_occupancy_guard",
        type_ids=("P",),
        geometry=("drop",),
        target_relation="empty",
        state_guards=(guard,),
        effects=(RuleActionEffect("remove_from_hand"), RuleActionEffect("place")),
        invariants=_own_anchor(),
    )
    return _semantic_ruleset((_king(), pawn), (action,))


def _uchifuzume_ruleset():
    pawn = _ray_type("P", (RayAtom((0, 1)),))
    action = RuleSemanticAction(
        name="drop_no_legal_reply_forbidden",
        type_ids=("P",),
        geometry=("drop",),
        target_relation="empty",
        effects=(RuleActionEffect("remove_from_hand"), RuleActionEffect("place")),
        invariants=_own_anchor(),
        postconditions=(
            RulePostcondition("opponent_checked"),
            RulePostcondition("no_legal_reply", max_stratum="S3"),
        ),
    )
    return _semantic_ruleset((_king(), pawn), (action,))


def _weird_rulesets():
    ray = _ray_type(
        "R",
        (RayAtom((1, 0)), RayAtom((-1, 0)), RayAtom((0, 1)), RayAtom((0, -1))),
    )
    weird_ray = RuleSemanticAction(
        name="ray_quiet_zero_capture_two_screens",
        type_ids=("R",),
        geometry=("ray",),
        target_relation="enemy",
        path_constraints=(RulePathConstraint("path_count_eq", count=2),),
        effects=(RuleActionEffect("remove", "target"), RuleActionEffect("move")),
        invariants=_own_anchor(),
    )
    zone_drop = RuleSemanticAction(
        name="drop_zone_capacity_guard",
        type_ids=("R",),
        geometry=("drop",),
        target_relation="empty",
        state_guards=(
            RuleStateGuard(
                aggregation="count",
                owner="self",
                type_mode="current",
                promoted="any",
                location="board",
                spatial="zone",
                spatial_ref="TARGET",
                comparison="lt",
                value=3,
            ),
        ),
        effects=(RuleActionEffect("remove_from_hand"), RuleActionEffect("place")),
        invariants=_own_anchor(),
    )
    token = RuleAuxState(name="temp_right", kind="right", lifetime="expire_next_turn")
    temp_right = RuleSemanticAction(
        name="promotion_grants_one_turn_right",
        type_ids=("R",),
        geometry=("leap",),
        target_relation="any",
        aux_state=(token,),
        effects=(
            RuleActionEffect("set_current_type"),
            RuleActionEffect("set_token", slot_name="temp_right"),
            RuleActionEffect("move"),
        ),
        invariants=_own_anchor(),
    )
    compound = RuleSemanticAction(
        name="move_and_shift_adjacent_friendly",
        type_ids=("R",),
        geometry=("leap",),
        target_relation="empty",
        effects=(RuleActionEffect("move"), RuleActionEffect("shift", "partner_square")),
        invariants=_own_anchor(),
    )
    restricted = RuleSemanticAction(
        name="action_class_no_immediate_mate",
        type_ids=("R",),
        geometry=("ray",),
        target_relation="enemy",
        effects=(RuleActionEffect("remove", "target"), RuleActionEffect("move")),
        invariants=_own_anchor(),
        postconditions=(
            RulePostcondition("opponent_checked"),
            RulePostcondition("no_legal_reply", max_stratum="S3"),
        ),
    )
    return (
        _semantic_ruleset((_king(), ray), (weird_ray,)),
        _semantic_ruleset((_king(), ray), (zone_drop,)),
        _semantic_ruleset((_king(), ray), (temp_right,)),
        _semantic_ruleset((_king(), ray), (compound,)),
        _semantic_ruleset((_king(), ray), (restricted,)),
    )


STRESS_GROUPS = {
    "cannon": _cannon_ruleset,
    "castling": _castling_ruleset,
    "en_passant": _en_passant_ruleset,
    "nifu": _nifu_ruleset,
    "uchifuzume": _uchifuzume_ruleset,
}


def _legacy_corpus():
    from generic_chess.ai.benchmark.audit_suite import (
        build_compiled,
        standard_ruleset_specs,
    )
    from generic_chess.learning.shogi_rules import build_shogi_ruleset
    from native_test_helpers import generated_compiled

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    return [
        build_compiled(specs["gen_classic_like_4_101"]),
        build_compiled(specs["gen_free_random_4_102"]),  # R2
        compile_ruleset(build_shogi_ruleset()),
        generated_compiled(size=6, seed=11),
    ]


def test_legacy_fingerprints_stable():
    from generic_chess.ai.benchmark.audit_suite import (
        build_compiled,
        standard_ruleset_specs,
    )
    from generic_chess.learning.shogi_rules import build_shogi_ruleset

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    r2 = build_compiled(specs["gen_free_random_4_102"])
    assert r2.ruleset_fingerprint == (
        "2c56e08b702cf400a65306519f6fe252574be4d1273717c05d03210316399883"
    )
    shogi = compile_ruleset(build_shogi_ruleset())
    assert shogi.ruleset_fingerprint == (
        "3d0407b1c088ece2c96fe0de2e50cc8ca2a9bf048aafe5fe3e2b816e94357b4d"
    )


def test_legacy_serialization_has_no_new_keys():
    from generic_chess.ai.benchmark.audit_suite import (
        build_compiled,
        standard_ruleset_specs,
    )

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    spec = specs["gen_classic_like_4_101"]
    compiled = build_compiled(spec)
    ruleset = ruleset_from_dict(ruleset_to_dict(compiled_rule_to_ruleset(compiled)))
    data = ruleset_to_dict(ruleset)
    assert "semantic_actions" not in data
    assert set(data) == {
        "schema_version",
        "board_size",
        "piece_types",
        "initial_position",
        "drop_allowed",
        "promotion_allowed",
        "promotion_forced",
        "repetition_limit",
        "max_ply",
        "stalemate_result",
        "metadata",
    }


def compiled_rule_to_ruleset(compiled):
    from generic_chess.rules.schema import RuleSet

    n = compiled.board_size
    board = compiled.initial_position.board
    rows = tuple(tuple(board[r * n : (r + 1) * n]) for r in range(n))
    return RuleSet(
        board_size=compiled.board_size,
        piece_types=compiled.piece_types,
        initial_position=rows,
        drop_allowed=compiled.drop_allowed,
        promotion_allowed=compiled.promotion_allowed,
        promotion_forced=compiled.promotion_forced,
        repetition_limit=compiled.repetition_limit,
        max_ply=compiled.max_ply,
        stalemate_result=compiled.stalemate_result,
    )


def test_semantic_actions_serialization_roundtrip():
    ruleset = _cannon_ruleset()
    data = ruleset_to_dict(ruleset)
    assert "semantic_actions" in data
    restored = ruleset_from_dict(data)
    assert ruleset_to_dict(restored) == data


def test_legacy_lowering_equivalence():
    for compiled in _legacy_corpus():
        ir = compile_semantic_ir(compiled)
        assert ir.ir_version == COMPILED_SEMANTIC_IR_VERSION
        assert ir.capabilities.legacy_core_executable is True
        assert ir.capabilities.native_executable is True
        # Geometry metadata equals the compiled legacy tables.
        n = compiled.board_size
        for tid in compiled.types_by_id:
            for owner in ("0", "1"):
                for idx in range(n * n):
                    expected_leaps = [
                        [sq.rank * n + sq.file for sq in targets]
                        for targets in compiled.leap_targets[tid][int(owner)][idx]
                    ]
                    expected_rays = [
                        [sq.rank * n + sq.file for sq in path]
                        for path in compiled.ray_paths[tid][int(owner)][idx]
                    ]
                    assert ir.geometry_metadata["types"][tid]["leap_targets"][owner][idx] == expected_leaps
                    assert ir.geometry_metadata["types"][tid]["ray_paths"][owner][idx] == expected_rays
        # Effect shapes and invariants per pattern family.
        names = {p.name: p for p in ir.patterns}
        for name, pattern in names.items():
            if name.endswith("_drop"):
                assert [e.kind for e in pattern.effects] == ["remove_from_hand", "place"]
            elif name.endswith("_quiet"):
                assert [e.kind for e in pattern.effects] == ["move"]
                assert pattern.target.kind == "target_empty"
            elif name.endswith("_capture"):
                assert [e.kind for e in pattern.effects] == ["remove", "move"]
                assert pattern.target.kind == "target_enemy"
            assert any(i.kind == "own_anchor_safe" for i in pattern.invariants)


def test_compiler_determinism():
    for compiled in _legacy_corpus():
        first = compile_semantic_ir(compiled)
        for _ in range(20):
            again = compile_semantic_ir(compiled)
            assert again.serialized() == first.serialized()
            assert again.fingerprint() == first.fingerprint()
    sem = compile_semantic_ruleset(_cannon_ruleset())
    first = sem.ir.serialized()
    for _ in range(20):
        assert compile_semantic_ruleset(_cannon_ruleset()).ir.serialized() == first


def test_stress_rules_compile():
    for name, builder in STRESS_GROUPS.items():
        sem = compile_semantic_ruleset(builder())
        assert sem.ir.patterns, name
        assert sem.ir.capabilities.legacy_core_executable is False
        assert sem.ir.capabilities.native_executable is False
        assert sem.ir.capabilities.new_ir_core_executable is False


def test_stress_structure_per_group():
    cannon = compile_semantic_ruleset(_cannon_ruleset()).ir
    quiet, capture = cannon.patterns
    assert [p.kind for p in quiet.path] == ["path_clear"]
    assert [p.kind for p in capture.path] == ["path_count_eq"]
    assert capture.path[0].count == 1
    assert quiet.target.kind == "target_empty"
    assert capture.target.kind == "target_enemy"

    castle = compile_semantic_ruleset(_castling_ruleset()).ir
    assert castle.aux_slots[0].kind == "right"
    assert castle.aux_slots[0].lifetime == "persistent"
    assert castle.patterns[0].slot_guards[0].slot_id == 0
    assert any(i.kind == "squares_not_attacked" for i in castle.patterns[0].invariants)
    assert [e.kind for e in castle.patterns[0].effects] == ["move", "move", "clear_right"]

    ep = compile_semantic_ruleset(_en_passant_ruleset()).ir
    assert ep.aux_slots[0].kind == "token_square"
    assert ep.aux_slots[0].lifetime == "expire_next_turn"
    creation, capture = ep.patterns
    assert [e.kind for e in creation.effects] == ["move", "set_token"]
    assert [e.kind for e in capture.effects] == ["move", "remove", "clear_token"]
    assert capture.effects[1].square_ref == "token"

    nifu = compile_semantic_ruleset(_nifu_ruleset()).ir
    guard = nifu.patterns[0].guards[0]
    assert guard.aggregation == "count"
    assert guard.selector.owner == "self"
    assert guard.selector.type_mode == "base"
    assert guard.selector.promoted == "no"
    assert guard.selector.location == "board"
    assert guard.selector.spatial == "same_file"
    assert guard.selector.spatial_ref == "TARGET"
    assert guard.comparison == "eq" and guard.value == 0

    uchi = compile_semantic_ruleset(_uchifuzume_ruleset()).ir
    pattern = uchi.patterns[0]
    assert [p.kind for p in pattern.postconditions] == ["opponent_checked", "no_legal_reply"]
    assert pattern.postconditions[1].max_stratum == MAX_PROBE_STRATUM
    assert pattern.cost_class == "C4"
    assert pattern.stratum == "S4"


def test_weird_rules_compile():
    for ruleset in _weird_rulesets():
        sem = compile_semantic_ruleset(ruleset)
        assert sem.ir.patterns
        assert sem.ir.capabilities.legacy_core_executable is False


def test_fail_closed_legacy_compile_rejects():
    for builder in STRESS_GROUPS.values():
        with pytest.raises(Exception) as exc:
            compile_ruleset(builder())
        assert "SEMANTIC_ACTIONS_NOT_LEGACY_EXECUTABLE" in str(exc.value)


def test_validation_rejects_bad_semantics():
    from generic_chess.rules.schema import RuleValidationError

    # effect count > 4
    too_many = RuleSemanticAction(
        name="too_many_effects",
        type_ids=("K",),
        geometry=("leap",),
        target_relation="any",
        effects=tuple(RuleActionEffect("move") for _ in range(5)),
    )
    with pytest.raises(RuleValidationError):
        compile_semantic_ruleset(_semantic_ruleset((_king(),), (too_many,)))

    # probe stratum S4 rejected
    bad_probe = RuleSemanticAction(
        name="bad_probe",
        type_ids=("K",),
        geometry=("leap",),
        target_relation="any",
        postconditions=(RulePostcondition("no_legal_reply", max_stratum="S4"),),
    )
    with pytest.raises(RuleValidationError):
        compile_semantic_ruleset(_semantic_ruleset((_king(),), (bad_probe,)))

    # unknown slot reference
    bad_slot = RuleSemanticAction(
        name="bad_slot",
        type_ids=("K",),
        geometry=("leap",),
        target_relation="any",
        effects=(RuleActionEffect("clear_right", slot_name="missing"),),
    )
    with pytest.raises(RuleValidationError):
        compile_semantic_ruleset(_semantic_ruleset((_king(),), (bad_slot,)))

    # squares_not_attacked with too many refs
    too_many_squares = RuleSemanticAction(
        name="bad_invariant",
        type_ids=("K",),
        geometry=("leap",),
        target_relation="any",
        invariants=(
            RuleInvariant(
                "squares_not_attacked",
                ("SOURCE", "TARGET", "FIXED_SQUARE", "AUX_SLOT", "SOURCE"),
            ),
        ),
    )
    with pytest.raises(RuleValidationError):
        compile_semantic_ruleset(_semantic_ruleset((_king(),), (too_many_squares,)))


def test_no_game_specific_production_semantics():
    forbidden = (
        "cannon",
        "castle",
        "castl",
        "en_passant",
        "nifu",
        "uchifuzume",
        "pawn",
        "rook",
        "bishop",
        "shogi",
        "chess",
        "xiangqi",
    )
    from generic_chess.rules import ir as ir_module
    from generic_chess.rules import schema as schema_module

    for module in (ir_module, schema_module):
        for attr in dir(module):
            if not attr.isupper():
                continue
            value = getattr(module, attr)
            if isinstance(value, (tuple, list)):
                for item in value:
                    if isinstance(item, str) and any(t in item.lower() for t in forbidden):
                        raise AssertionError(
                            f"{module.__name__}.{attr} contains forbidden token {item}"
                        )


def test_production_does_not_import_experiments():
    for path in (ROOT / "generic_chess").rglob("*.py"):
        source = path.read_text(encoding="utf-8", errors="ignore")
        assert "rule_ir_design_prototype" not in source


def test_ir_types_frozen_and_deterministic():
    import dataclasses

    from generic_chess.rules.ir import CompiledMovePattern

    assert CompiledMovePattern.__dataclass_params__.frozen is True
    compiled = compile_semantic_ir(_legacy_corpus()[0])
    assert compiled.serialized() == compiled.serialized()
    assert compiled.fingerprint() == compiled.fingerprint()


def test_geometry_payload_size_bounded():
    from generic_chess.ai.benchmark.audit_suite import (
        build_compiled,
        standard_ruleset_specs,
    )
    from generic_chess.learning.shogi_rules import build_shogi_ruleset
    from generic_chess.rules.serialization import serialize_ruleset
    from native_test_helpers import generated_compiled

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    corpus = [
        ("8x8_classic", build_compiled(specs["gen_classic_like_8_301"])),
        ("9x9_shogi", compile_ruleset(build_shogi_ruleset())),
        ("16x16_gen", generated_compiled(size=16, seed=5)),
    ]
    sizes = {}
    for label, compiled in corpus:
        legacy_serialized = len(serialize_ruleset(compiled_rule_to_ruleset(compiled)))
        ir_serialized = len(compile_semantic_ir(compiled).serialized())
        geometry_serialized = len(
            __import__("json").dumps(
                build_geometry_metadata(compiled), sort_keys=True
            )
        )
        sizes[label] = {
            "legacy_serialized_bytes": legacy_serialized,
            "ir_serialized_bytes": ir_serialized,
            "geometry_metadata_bytes": geometry_serialized,
            "ir_over_legacy_ratio": round(ir_serialized / legacy_serialized, 2),
        }
        assert ir_serialized / legacy_serialized < 10.0, (label, sizes[label])
