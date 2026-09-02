"""Focused deterministic contracts for the F45 structural discrimination."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_f45_structural_feature_discrimination.py"
EVIDENCE = ROOT / ".generic_chess_flow" / "f45_structural_feature_discrimination.json"
sys.path.insert(0, str(ROOT / "scripts"))
import audit_f45_structural_feature_discrimination as audit  # noqa: E402


@pytest.fixture(scope="module")
def evidence():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_f45_reproduces_f44_before_discrimination(evidence):
    reproduction = evidence["f44_reproduction"]
    assert reproduction["status"] == "PASS"
    assert all(reproduction["gates"].values())
    assert reproduction["selection"]["materially_supported_families"] == [
        "S44-A_ENDPOINT_CONTROL_SEMANTICS",
        "S44-B_CONDITIONAL_CAPABILITY_RESERVE",
        "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY",
    ]


def test_consumer_paths_and_placement_are_explicit(evidence):
    placements = evidence["placement_ledger"]
    assert placements["exactly_one_placement_per_family"] is True
    assert placements["S44-A_ENDPOINT_CONTROL_SEMANTICS"]["placement"] == "STATIC_MATERIAL_ADMISSIBLE"
    assert placements["S44-B_CONDITIONAL_CAPABILITY_RESERVE"]["placement"] == "DYNAMIC_EVALUATOR_ADMISSIBLE"
    assert placements["S44-C_CHANNEL_DIVERSITY_CONCENTRATION"]["placement"] == "DIAGNOSTIC_ONLY_NOT_ADMISSIBLE"
    assert placements["S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY"]["placement"] == "STATIC_MATERIAL_ADMISSIBLE"
    assert all(row["all_present"] for family in evidence["consumer_placement"].values() for row in family.get("consumer_paths", []))


def test_endpoint_duplication_gate_preserves_unique_split(evidence):
    row = evidence["consumer_placement"]["S44-A_ENDPOINT_CONTROL_SEMANTICS"]
    assert row["equivalent_existing_consumer"] is False
    assert row["complete_pre_search_collision_remains"] is True
    assert "target_empty" in row["unique_information"]
    assert "target_enemy" in row["unique_information"]


def test_conditional_guards_are_dynamic_and_not_static_value(evidence):
    guards = evidence["guard_category_ledger"]
    assert guards["state_and_slot_guards_present"] == {"state_guard": True, "slot_guard": True}
    assert guards["promotion_related_transition"] is False
    row = evidence["placement_ledger"]["S44-B_CONDITIONAL_CAPABILITY_RESERVE"]
    assert row["static_material_admissible"] is False
    assert row["dynamic_evaluator_admissible"] is True
    assert row["facts"]["requires_position_state"] is True
    assert row["facts"]["independent_support"] is True


def test_density_has_no_equivalent_shape_consumer(evidence):
    row = evidence["consumer_placement"]["S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY"]
    assert row["equivalent_existing_consumer"] is False
    assert row["complete_pre_search_collision_remains"] is True
    assert evidence["placement_ledger"]["S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY"]["placement"] == "STATIC_MATERIAL_ADMISSIBLE"
    density = evidence["orientation_probes"]["S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY"]
    assert density["resolves_R1"] is True
    assert density["resolves_R2"] is True


def test_residual_coverage_and_cross_rule_gate(evidence):
    assert evidence["residual_obligations"]["coverage"] == {
        "S44-A_ENDPOINT_CONTROL_SEMANTICS": {"R1": True, "R2": False},
        "S44-B_CONDITIONAL_CAPABILITY_RESERVE": {"R1": True, "R2": False},
        "S44-C_CHANNEL_DIVERSITY_CONCENTRATION": {"R1": False, "R2": False},
        "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY": {"R1": True, "R2": True},
    }
    assert evidence["orientation_probes"]["R3_cross_rule_gate"]["pass"] is True


def test_redundancy_does_not_select_pawn_nonzero_signals_by_correlation(evidence):
    ordered = [row for key, row in evidence["redundancy_subsumption"]["pairwise_ordered"].items() if not key.startswith("partition:")]
    assert len(ordered) == 6
    assert all(row["target_recoverability_from_source"] in {"NOT_RECOVERABLE", "UNRESOLVED"} for row in ordered)
    assert any(row["target_recoverability_from_source"] == "UNRESOLVED" for row in ordered)
    partitions = [row["partition_relation"] for key, row in evidence["redundancy_subsumption"]["pairwise_ordered"].items() if key.startswith("partition:")]
    assert set(partitions) <= {"same_partition", "left_refines_right", "right_refines_left", "incomparable"}
    assert all("same_executable_cause" in row for key, row in evidence["redundancy_subsumption"]["pairwise_ordered"].items() if key.startswith("partition:") )


def test_minimum_subset_and_final_classification(evidence):
    assert evidence["minimum_subset"] == ["S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY"]
    assert evidence["selection"] == {
        "classification": "DENSITY_PROFILE_FEATURE_PRIMARY",
        "conflicting_families": [],
        "minimum_explanatory_subset": ["S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY"],
        "next_boundary": "F46_DENSITY_PROFILE_FEATURE_PROTOTYPE",
        "tie_status": "not_applicable",
    }


def test_selector_reaches_all_eight_frozen_classifications():
    assert audit._reachability_ledger()["all_reachable"] is True


def test_generic_placement_classifier_reaches_all_five_placements():
    base = {"consumer_evidence_sufficient": True, "independent_support": True, "equivalent_existing_consumer": False, "requires_position_state": False, "compile_once_type_information": True}
    assert audit._classify_placement(base) == "STATIC_MATERIAL_ADMISSIBLE"
    dynamic = {**base, "requires_position_state": True, "compile_once_type_information": False}
    assert audit._classify_placement(dynamic) == "DYNAMIC_EVALUATOR_ADMISSIBLE"
    assert audit._classify_placement({**base, "equivalent_existing_consumer": True}) == "ALREADY_EQUIVALENTLY_CONSUMED"
    assert audit._classify_placement({**base, "independent_support": False}) == "DIAGNOSTIC_ONLY_NOT_ADMISSIBLE"
    assert audit._classify_placement({**base, "consumer_evidence_sufficient": False}) == "UNRESOLVED"


def test_minimum_subset_tie_is_unresolved():
    rows = {
        audit.FAMILIES[0]: {"materially_supported": True, "placement": "STATIC_MATERIAL_ADMISSIBLE", "existing_evaluator_duplication": False, "independent_information": True, "cross_rule_consistent": True, "covers_R1": True, "covers_R2": True},
        audit.FAMILIES[3]: {"materially_supported": True, "placement": "STATIC_MATERIAL_ADMISSIBLE", "existing_evaluator_duplication": False, "independent_information": True, "cross_rule_consistent": True, "covers_R1": True, "covers_R2": True},
    }
    selected = audit._select_classification(rows)
    assert selected["classification"] == "STRUCTURAL_FEATURE_DISCRIMINATION_INSUFFICIENT"
    assert selected["tie_status"] == "unresolved_equal_minimum_subsets"


def test_f45_has_no_production_change_and_exactly_one_result(evidence):
    assert evidence["status"] == "PASS"
    assert evidence["production_changed"] is False
    assert sum(evidence["selection"]["classification"] == name for name in audit.CLASSIFICATION_MAPPING) == 1
    assert all(evidence["gates"].values())
