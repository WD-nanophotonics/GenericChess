"""Phase 1.9B-1.5: executable-completeness hardening tests (IR v2)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.rules.compiler import (
    compile_ruleset,
    compile_semantic_ir,
    compile_semantic_ruleset,
)
from generic_chess.rules.ir import (
    COMPILED_SEMANTIC_IR_VERSION,
    MAX_PROBE_STRATUM,
    CompiledSemanticIR,
    SemanticCapabilities,
    geometry_candidates,
    validate_executable_completeness,
    validate_ir,
)
from generic_chess.rules.schema import (
    RuleAuxState,
    RuleActionEffect,
    RuleGeometrySpec,
    RuleReplaceSelector,
    RuleSemanticAction,
    RuleSquareRef,
    RuleSet,
    ruleset_from_dict,
    ruleset_to_dict,
)

from rule_semantics_ir_fixtures import (
    STRESS_GROUPS,
    cannon_ruleset,
    castling_ruleset,
    en_passant_ruleset,
    nifu_ruleset,
    uchifuzume_ruleset,
    weird_rulesets,
)


ROOT = Path(__file__).resolve().parent.parent


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
        build_compiled(specs["gen_free_random_4_102"]),
        compile_ruleset(build_shogi_ruleset()),
        generated_compiled(size=6, seed=11),
    ]


def _patterns(ir):
    return {p.pattern_id: p for p in ir.patterns}


def _compile(group):
    return compile_semantic_ruleset(STRESS_GROUPS[group]()).ir


# ---------------------------------------------------------------- geometry


def test_exact_geometry_identity_four_rays_distinct():
    ir = _compile("cannon")
    ray_geoms = [g for g in ir.geometry.values() if g.kind == "ray"]
    assert len(ray_geoms) == 4
    assert len({g.geometry_id for g in ray_geoms}) == 4
    directions = {g.direction for g in ray_geoms}
    assert directions == {(1, 0), (-1, 0), (0, 1), (0, -1)}
    for g in ray_geoms:
        assert g.atom_source is not None  # legacy atom identity preserved


def test_castling_exact_two_step_geometry():
    ir = _compile("castling")
    pattern = _patterns(ir)["sem_00_king_side_shift"]
    gid = pattern.geometry_ids[0]
    geo = ir.geometry[gid]
    assert geo.kind == "ray"
    assert geo.direction == (1, 0)
    assert geo.min_steps == 2 and geo.max_steps == 2
    # source e1 = (4, 0); candidate target must be exactly two files away.
    source = 0 * 8 + 4
    candidates = geometry_candidates(geo, "0", source)
    assert len(candidates) == 1
    target, path = candidates[0]
    assert target == 0 * 8 + 6  # g1
    assert path == (0 * 8 + 5,)  # f1 transit


def test_geometry_candidates_exclude_source_and_target():
    ir = compile_semantic_ir(_legacy_corpus()[0])
    for geo in ir.geometry.values():
        if geo.kind == "drop":
            continue
        for owner, per_source in geo.paths.items():
            for source, candidates in per_source.items():
                for target, path in geometry_candidates(geo, owner, source):
                    assert target != source
                    assert source not in path and target not in path


# ---------------------------------------------------------------- pattern ids


def test_pattern_ids_deterministic_and_in_serialization():
    for name, builder in STRESS_GROUPS.items():
        a = compile_semantic_ruleset(builder()).ir
        b = compile_semantic_ruleset(builder()).ir
        assert [p.pattern_id for p in a.patterns] == [p.pattern_id for p in b.patterns]
        assert a.serialized() == b.serialized()
        assert all(p.pattern_id in a.serialized() for p in a.patterns)


# ---------------------------------------------------------------- composition


def test_augment_keeps_legacy_patterns():
    ir = _compile("castling")
    ids = {p.pattern_id for p in ir.patterns}
    assert any(pid.startswith("legacy_") for pid in ids)
    assert "sem_00_king_side_shift" in ids


def test_cannon_replace_removes_plain_capture():
    ir = _compile("cannon")
    for pattern in ir.patterns:
        if pattern.type_ids == ("C",) and pattern.target.kind == "target_enemy":
            assert [pp.kind for pp in pattern.path] == ["path_count_eq"]
    assert not any(
        p.type_ids == ("C",)
        and p.target.kind == "target_enemy"
        and [pp.kind for pp in p.path] == ["path_clear"]
        for p in ir.patterns
    )
    replacement = next(
        p for p in ir.patterns if p.pattern_id == "sem_01_cannon_capture"
    )
    assert replacement.replaced_pattern_ids
    assert len(replacement.replaced_pattern_ids) == 4  # four legacy ray captures


def test_nifu_replace_removes_unrestricted_drop():
    ir = _compile("nifu")
    drop_patterns = [
        p
        for p in ir.patterns
        if p.type_ids == ("P",)
        and any(ir.geometry[g].kind == "drop" for g in p.geometry_ids)
    ]
    assert len(drop_patterns) == 1
    assert drop_patterns[0].guards
    assert drop_patterns[0].replaced_pattern_ids


def test_ep_double_step_single_token_version():
    ir = _compile("en_passant")
    creation = _patterns(ir)["sem_00_double_step_creates_token"]
    assert any(e.kind == "set_token" for e in creation.effects)
    # No legacy two-step ray exists for the pawn (single-step legacy only),
    # and the explicit creation is the only two-step pattern.
    two_step = [
        p
        for p in ir.patterns
        if any(
            ir.geometry[g].kind == "ray"
            and ir.geometry[g].min_steps == 2
            and ir.geometry[g].max_steps == 2
            for g in p.geometry_ids
        )
    ]
    assert len(two_step) == 1
    assert any(e.kind == "set_token" for e in two_step[0].effects)


def test_replace_zero_match_rejected():
    from generic_chess.rules.schema import RuleSet, RuleValidationError

    ruleset = cannon_ruleset()
    bad = RuleSemanticAction(
        name="bad_replace",
        type_ids=("C",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="empty",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("C",), action_family="drop", target_relation="empty"
        ),
        effects=(RuleActionEffect("move"),),
    )
    broken = RuleSet(
        board_size=ruleset.board_size,
        piece_types=ruleset.piece_types,
        initial_position=ruleset.initial_position,
        drop_allowed=ruleset.drop_allowed,
        semantic_actions=(bad,),
    )
    with pytest.raises(RuleValidationError):
        compile_semantic_ruleset(broken)


def test_replace_ambiguous_rejected_unless_all():
    from generic_chess.rules.schema import RuleSet, RuleValidationError

    ruleset = cannon_ruleset()
    ambiguous = RuleSemanticAction(
        name="ambiguous_replace",
        type_ids=("C",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="ray"),
        target_relation="enemy",
        composition="replace_legacy",
        replace_selector=RuleReplaceSelector(
            type_ids=("C",), action_family="board", target_relation="enemy"
        ),
        effects=(RuleActionEffect("remove"), RuleActionEffect("move")),
    )
    broken = RuleSet(
        board_size=ruleset.board_size,
        piece_types=ruleset.piece_types,
        initial_position=ruleset.initial_position,
        drop_allowed=ruleset.drop_allowed,
        semantic_actions=(ambiguous,),
    )
    with pytest.raises(RuleValidationError):
        compile_semantic_ruleset(broken)


# ---------------------------------------------------------------- type binding


def test_nifu_type_binding_explicit():
    ir = _compile("nifu")
    guard = next(p for p in ir.patterns if p.guards).guards[0]
    assert guard.type_ref.kind == "action_base"
    assert guard.compare_field == "base"
    assert guard.owner == "self"
    assert guard.promoted == "no"
    assert guard.location == "board"
    assert guard.spatial.kind == "same_file"
    assert len(guard.spatial.refs) == 1
    assert guard.spatial.refs[0].kind == "target"


def test_invalid_explicit_type_rejected():
    from generic_chess.rules.schema import RuleSet, RuleValidationError, RuleStateGuard, RuleSpatialSelector, RuleTypeRef

    ruleset = nifu_ruleset()
    bad_guard = RuleStateGuard(
        aggregation="count",
        owner="self",
        type_ref=RuleTypeRef(kind="explicit", type_id="NOPE"),
        compare_field="base",
        promoted="no",
        location="board",
        spatial=RuleSpatialSelector(kind="same_file", refs=(RuleSquareRef("target"),)),
        comparison="eq",
        value=0,
    )
    bad_action = RuleSemanticAction(
        name="bad_type",
        type_ids=("P",),
        geometry=RuleGeometrySpec(kind="drop"),
        target_relation="empty",
        state_guards=(bad_guard,),
        effects=(RuleActionEffect("remove_from_hand"), RuleActionEffect("place")),
    )
    broken = RuleSet(
        board_size=ruleset.board_size,
        piece_types=ruleset.piece_types,
        initial_position=ruleset.initial_position,
        drop_allowed=ruleset.drop_allowed,
        semantic_actions=(bad_action,),
    )
    with pytest.raises(RuleValidationError):
        compile_semantic_ruleset(broken)


# ---------------------------------------------------------------- spatial / square refs


def test_zone_selector_has_zone_id():
    ir = compile_semantic_ruleset(weird_rulesets()[1]).ir
    assert ir.zones
    guard = next(p for p in ir.patterns if p.guards).guards[0]
    assert guard.spatial.kind == "zone"
    assert guard.spatial.zone_id in ir.zones


def test_path_between_has_two_refs():
    from generic_chess.rules.schema import (
        RuleSet,
        RuleSpatialSelector,
        RuleStateGuard,
        RuleTypeRef,
    )

    ruleset = nifu_ruleset()
    between = RuleStateGuard(
        aggregation="count",
        owner="any",
        type_ref=RuleTypeRef(kind="any"),
        compare_field="base",
        promoted="any",
        location="board",
        spatial=RuleSpatialSelector(
            kind="path_between",
            refs=(RuleSquareRef("source"), RuleSquareRef("target")),
        ),
        comparison="eq",
        value=0,
    )
    action = RuleSemanticAction(
        name="path_between_guard",
        type_ids=("P",),
        geometry=RuleGeometrySpec(kind="drop"),
        target_relation="empty",
        state_guards=(between,),
        effects=(
            RuleActionEffect(
                "remove_from_hand",
                piece_type_ref=RuleTypeRef(kind="action_base"),
            ),
            RuleActionEffect(
                "place",
                to_ref=RuleSquareRef("target"),
                piece_type_ref=RuleTypeRef(kind="action_base"),
            ),
        ),
    )
    broken = RuleSet(
        board_size=ruleset.board_size,
        piece_types=ruleset.piece_types,
        initial_position=ruleset.initial_position,
        drop_allowed=ruleset.drop_allowed,
        semantic_actions=(action,),
    )
    ir = compile_semantic_ruleset(broken).ir
    compiled_sel = next(p for p in ir.patterns if p.guards).guards[0].spatial
    assert compiled_sel.kind == "path_between"
    assert len(compiled_sel.refs) == 2


def test_placeholder_audit_zero():
    forbidden_placeholder_kinds = {"partner_square", "token", "FIXED_SQUARE"}
    for name, builder in STRESS_GROUPS.items():
        ir = compile_semantic_ruleset(builder()).ir
        for pattern in ir.patterns:
            for effect in pattern.effects:
                for ref in (effect.from_ref, effect.to_ref, effect.square_ref):
                    if ref is not None:
                        assert ref.kind not in forbidden_placeholder_kinds
            for invariant in pattern.invariants:
                for ref in invariant.square_refs:
                    assert ref.kind not in forbidden_placeholder_kinds
    assert "partner_square" not in compile_semantic_ruleset(castling_ruleset()).ir.serialized()
    assert "token" not in {
        r.kind
        for p in compile_semantic_ruleset(en_passant_ruleset()).ir.patterns
        for e in p.effects
        for r in (e.from_ref, e.to_ref, e.square_ref)
        if r is not None
    }


# ---------------------------------------------------------------- aux state


def test_aux_scope_initial_lifetime():
    castle = _compile("castling")
    slot = castle.aux_slots[0]
    assert slot.value_kind == "bool"
    assert slot.scope == "per_owner"
    assert slot.lifetime == "persistent"
    assert slot.initial == 1
    ep = _compile("en_passant")
    ep_slot = ep.aux_slots[0]
    assert ep_slot.value_kind == "square_or_none"
    assert ep_slot.scope == "global"
    assert ep_slot.lifetime == "expire_next_turn"
    assert ep_slot.initial is None


def test_transition_triggers_present():
    ir = _compile("castling")
    events = {(t.event, t.square_ref.kind) for t in ir.triggers}
    assert ("piece_leaves_square", "fixed") in events
    assert ("piece_removed_from_square", "fixed") in events
    assert len(ir.triggers) == 3
    assert all(t.slot_id == 0 for t in ir.triggers)


# ---------------------------------------------------------------- effects


def test_effect_wellformedness_rejects():
    from generic_chess.rules.schema import RuleSet, RuleValidationError

    base = uchifuzume_ruleset()

    def broken(action):
        return RuleSet(
            board_size=base.board_size,
            piece_types=base.piece_types,
            initial_position=base.initial_position,
            drop_allowed=base.drop_allowed,
            semantic_actions=(action,),
        )

    no_type = RuleSemanticAction(
        name="no_type",
        type_ids=("P",),
        geometry=RuleGeometrySpec(kind="drop"),
        target_relation="empty",
        effects=(
            RuleActionEffect("set_current_type", square_ref=RuleSquareRef("target")),
        ),
    )
    with pytest.raises(RuleValidationError):
        compile_semantic_ruleset(broken(no_type))

    no_square = RuleSemanticAction(
        name="no_square",
        type_ids=("P",),
        geometry=RuleGeometrySpec(kind="drop"),
        target_relation="empty",
        effects=(
            RuleActionEffect(
                "remove", square_ref=RuleSquareRef("target"), disposition="capture_to_hand"
            ),
            RuleActionEffect("move"),
        ),
    )
    with pytest.raises(RuleValidationError):
        compile_semantic_ruleset(broken(no_square))

    default_disposition = RuleSemanticAction(
        name="default_disposition",
        type_ids=("P",),
        geometry=RuleGeometrySpec(kind="drop"),
        target_relation="empty",
        effects=(
            RuleActionEffect("remove", square_ref=RuleSquareRef("target")),
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),
        ),
    )
    ir = compile_semantic_ruleset(broken(default_disposition)).ir
    semantic = next(p for p in ir.patterns if p.pattern_id.startswith("sem_"))
    remove_effect = next(e for e in semantic.effects if e.kind == "remove")
    assert remove_effect.disposition == "capture_to_hand"

    set_token_bool = RuleSemanticAction(
        name="token_into_bool",
        type_ids=("P",),
        geometry=RuleGeometrySpec(kind="drop"),
        target_relation="empty",
        aux_state=(
            RuleAuxState(
                name="bool_slot", value_kind="bool", scope="global",
                lifetime="persistent", initial=0,
            ),
        ),
        effects=(
            RuleActionEffect("set_token", slot_name="bool_slot", square_ref=RuleSquareRef("target")),
            RuleActionEffect("remove_from_hand"),
            RuleActionEffect("place"),
        ),
    )
    with pytest.raises(RuleValidationError):
        compile_semantic_ruleset(broken(set_token_bool))


def test_ir_v1_rejected_and_capabilities_fail_closed():
    old = CompiledSemanticIR(ir_version=1, patterns=())
    assert validate_ir(old)
    for name, builder in STRESS_GROUPS.items():
        ir = compile_semantic_ruleset(builder()).ir
        assert ir.ir_version == COMPILED_SEMANTIC_IR_VERSION
        assert ir.capabilities == SemanticCapabilities(
            legacy_core_executable=False,
            new_ir_core_executable=False,
            native_executable=False,
            contains_path_predicate=ir.capabilities.contains_path_predicate,
            contains_state_guard=ir.capabilities.contains_state_guard,
            contains_aux_state=ir.capabilities.contains_aux_state,
            contains_compound_effect=ir.capabilities.contains_compound_effect,
            contains_postcondition=ir.capabilities.contains_postcondition,
            contains_transition_trigger=ir.capabilities.contains_transition_trigger,
        )


def test_semantic_dsl_version_in_serialization():
    data = ruleset_to_dict(cannon_ruleset())
    assert data["semantic_dsl_version"] == 2
    restored = ruleset_from_dict(data)
    assert ruleset_to_dict(restored) == data


# ---------------------------------------------------------------- static closure


def _closure(ir, type_ids):
    return validate_executable_completeness(ir, type_ids)


def test_executable_closure_stress_and_weird():
    for name, builder in STRESS_GROUPS.items():
        ir = compile_semantic_ruleset(builder()).ir
        assert _closure(ir, _legacy_type_ids(builder())) == []
    for ruleset in weird_rulesets():
        ir = compile_semantic_ruleset(ruleset).ir
        assert _closure(ir, _legacy_type_ids(ruleset)) == []


def _legacy_type_ids(ruleset):
    return tuple(sorted(pt.type_id for pt in ruleset.piece_types))


def test_executable_closure_legacy_corpus():
    for compiled in _legacy_corpus():
        ir = compile_semantic_ir(compiled)
        type_ids = tuple(sorted(compiled.types_by_id))
        assert _closure(ir, type_ids) == []
        assert ir.ir_version == COMPILED_SEMANTIC_IR_VERSION


def test_uchifuzume_closure_details():
    ir = _compile("uchifuzume")
    pattern = next(p for p in ir.patterns if p.postconditions)
    assert pattern.composition == "replace_legacy"
    assert pattern.replaced_pattern_ids
    assert [p.kind for p in pattern.postconditions] == [
        "opponent_checked",
        "no_legal_reply",
    ]
    assert pattern.postconditions[1].max_stratum == MAX_PROBE_STRATUM
    assert pattern.cost_class == "C4"
    assert pattern.stratum == "S4"
    assert pattern.effects[0].piece_type_ref is not None


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


def test_legacy_serialization_keys_unchanged():
    compiled = _legacy_corpus()[0]
    from generic_chess.rules.schema import RuleSet

    n = compiled.board_size
    board = compiled.initial_position.board
    rows = tuple(tuple(board[r * n : (r + 1) * n]) for r in range(n))
    ruleset = RuleSet(
        board_size=n,
        piece_types=compiled.piece_types,
        initial_position=rows,
        drop_allowed=compiled.drop_allowed,
        promotion_allowed=compiled.promotion_allowed,
        promotion_forced=compiled.promotion_forced,
        repetition_limit=compiled.repetition_limit,
        max_ply=compiled.max_ply,
        stalemate_result=compiled.stalemate_result,
    )
    data = ruleset_to_dict(ruleset)
    assert "semantic_actions" not in data
    assert "semantic_dsl_version" not in data


def test_payload_growth_v2_bounded():
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
        n = compiled.board_size
        board = compiled.initial_position.board
        rows = tuple(tuple(board[r * n : (r + 1) * n]) for r in range(n))
        ruleset = RuleSet(
            board_size=n,
            piece_types=compiled.piece_types,
            initial_position=rows,
            drop_allowed=compiled.drop_allowed,
            promotion_allowed=compiled.promotion_allowed,
            promotion_forced=compiled.promotion_forced,
            repetition_limit=compiled.repetition_limit,
            max_ply=compiled.max_ply,
            stalemate_result=compiled.stalemate_result,
        )
        legacy_bytes = len(serialize_ruleset(ruleset))
        ir_bytes = len(compile_semantic_ir(compiled).serialized())
        ratio = ir_bytes / legacy_bytes
        sizes[label] = {
            "legacy_bytes": legacy_bytes,
            "ir_bytes": ir_bytes,
            "ratio": round(ratio, 2),
        }
        assert ratio < 12.0, (label, sizes[label])
