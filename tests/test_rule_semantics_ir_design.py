"""Phase 1.9A-2 IR design tests: structural validation of the proposed
Rule Semantic IR prototype (design-only; production must not import it)."""

from pathlib import Path

import pytest

from experiments.rule_ir_design_prototype import (
    AUX_KINDS,
    AUX_LIFETIMES,
    COST_CLASSES,
    FORBIDDEN_EXECUTION_TOKENS,
    IRTemplate,
    MAX_EFFECTS_PER_ACTION,
    STRATA,
    build_all_templates,
    dependency_cycle_rejected,
    serialize_all,
    validate_all,
    validate_template,
)


ROOT = Path(__file__).resolve().parent.parent


def _group(name: str) -> tuple[IRTemplate, ...]:
    return build_all_templates()[name]


def _all_valid() -> dict:
    return validate_all()


def test_all_stress_groups_valid():
    report = _all_valid()
    for group in (
        "screen_ray",
        "king_side_shift",
        "double_step_token",
        "file_occupancy_drop_guard",
        "drop_no_legal_reply",
        "weird_rules",
    ):
        assert report[group]["valid"], (group, report[group])


def test_cannon_mapping_uses_generic_path_predicates():
    quiet, capture = _group("screen_ray")
    assert quiet.path[0].kind == "path_clear"
    assert quiet.target.kind == "target_empty"
    assert capture.path[0].kind == "path_count_eq"
    assert capture.path[0].count == 1
    assert capture.target.kind == "target_enemy"


def test_castling_mapping_has_right_slot_and_transit_invariant():
    castle, _king, _rook = _group("king_side_shift")
    assert castle.aux_slots[0].kind == "right"
    assert castle.aux_slots[0].lifetime == "persistent"
    assert castle.slot_guards[0].slot_id == 0
    assert "squares_not_attacked" in castle.invariants
    kinds = [e.kind for e in castle.effects]
    assert kinds == ["move", "move", "clear_right"]


def test_en_passant_mapping_has_token_and_off_target_remove():
    creation, capture = _group("double_step_token")
    assert creation.aux_slots[0].kind == "token_square"
    assert creation.aux_slots[0].lifetime == "expire_next_turn"
    assert [e.kind for e in creation.effects] == ["move", "set_token"]
    assert capture.slot_guards[0].slot_id == 1
    assert [e.kind for e in capture.effects] == ["move", "remove", "clear_token"]
    assert capture.effects[1].square_ref == "token"  # off-target capture


def test_nifu_mapping_is_generic_state_query():
    (guard,) = _group("file_occupancy_drop_guard")
    query = guard.guards[0]
    assert query.aggregation == "count"
    assert query.owner == "self"
    assert query.type_mode == "base"
    assert query.promoted == "no"
    assert query.location == "board"
    assert query.spatial == "same_file"
    assert query.comparison == "eq"
    assert query.value == 0
    assert guard.stratum == "S1"


def test_uchifuzume_mapping_has_bounded_stratified_probe():
    (drop,) = _group("drop_no_legal_reply")
    assert [p.kind for p in drop.postconditions] == [
        "opponent_checked",
        "no_legal_reply",
    ]
    probe = drop.postconditions[1]
    assert probe.probe_stratum == "S3"  # stratified: nested replies <= S3
    assert drop.cost_class == "C4"
    assert drop.stratum == "S4"


def test_weird_rules_all_valid():
    report = _all_valid()["weird_rules"]
    assert report["valid"]
    assert len(report["templates"]) == 5


def test_no_game_names_in_execution_kinds():
    from experiments.rule_ir_design_prototype import (
        EFFECT_KINDS,
        GEOMETRY_KINDS,
        INVARIANT_KINDS,
        PATH_KINDS,
        POSTCONDITION_KINDS,
        PROBE_KINDS,
        SELECTOR_SPATIAL,
        TARGET_KINDS,
    )

    all_kinds = (
        GEOMETRY_KINDS
        + PATH_KINDS
        + TARGET_KINDS
        + EFFECT_KINDS
        + INVARIANT_KINDS
        + POSTCONDITION_KINDS
        + PROBE_KINDS
        + SELECTOR_SPATIAL
        + AUX_KINDS
    )
    for kind in all_kinds:
        assert kind not in FORBIDDEN_EXECUTION_TOKENS


def test_effect_cardinality_bounded_and_deterministic_serialization():
    for group, templates in build_all_templates().items():
        for template in templates:
            assert len(template.effects) <= MAX_EFFECTS_PER_ACTION
    a = serialize_all()
    b = serialize_all()
    assert a == b


def test_aux_slots_typed_and_unique():
    for group, templates in build_all_templates().items():
        for template in templates:
            ids = [slot.slot_id for slot in template.aux_slots]
            assert len(ids) == len(set(ids))
            for slot in template.aux_slots:
                assert slot.kind in AUX_KINDS
                assert slot.lifetime in AUX_LIFETIMES


def test_dependency_cycle_rejected():
    result = dependency_cycle_rejected()
    assert result["rejected"] is True
    assert result["errors"]


def test_forbidden_recursive_probe_rejected():
    from experiments.rule_ir_design_prototype import Effect, Postcondition

    bad = IRTemplate(
        name="bad_probe_stratum",
        geometry=("drop",),
        effects=(Effect("place"),),
        postconditions=(Postcondition("no_legal_reply", probe_stratum="S4"),),
        cost_class="C4",
        stratum="S4",
    )
    report = validate_template(bad)
    assert report["valid"] is False


def test_cost_class_and_stratum_assigned():
    for group, templates in build_all_templates().items():
        for template in templates:
            assert template.cost_class in COST_CLASSES
            assert template.stratum in STRATA


def test_production_does_not_import_prototype():
    for path in (ROOT / "generic_chess").rglob("*.py"):
        source = path.read_text(encoding="utf-8", errors="ignore")
        assert "rule_ir_design_prototype" not in source
