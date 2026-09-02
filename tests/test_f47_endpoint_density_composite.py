"""Focused executable contracts for the F47 endpoint-density diagnosis."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_f47_endpoint_density_composite.py"
EVIDENCE = ROOT / ".generic_chess_flow" / "f47_endpoint_density_composite.json"
sys.path.insert(0, str(ROOT / "scripts"))
import audit_f46_density_profile as f46  # noqa: E402
import audit_f47_endpoint_density_composite as audit  # noqa: E402


@pytest.fixture(scope="module")
def evidence():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_f47_actual_classification_is_evidence_derived(evidence):
    assert evidence["status"] == "PASS"
    assert evidence["selection"] == {
        "classification": "ENDPOINT_DENSITY_COMPOSITE_INSUFFICIENT",
        "next_boundary": "F48_GENERIC_MATERIAL_PRIOR_REASSESSMENT",
        "qualified": [],
        "coherent_insufficient": [audit.VARIANTS[1], audit.VARIANTS[2], audit.VARIANTS[3]],
        "directional_mismatch": [audit.VARIANTS[4]],
    }


def test_same_target_and_split_controls(evidence):
    controls = evidence["semantic_controls"]
    assert controls["same_target_relation_control"]["identical"] is True
    assert controls["split_target_control"]["positive_gap"] is True
    assert controls["no_attack_control"]["zero_gap"] is True
    assert controls["dual_use_only_control"]["zero_gap"] is True
    assert controls["no_relation_multiplicity_double_count"] is True


def test_conditional_exclusion_and_pawn_relevance(evidence):
    controls = evidence["semantic_controls"]
    assert controls["conditional_exclusion"]["conditional_patterns_present"] is True
    assert controls["conditional_exclusion"]["ordinary_gap_unchanged"] is True
    assert controls["western_pawn"]["nonzero"] is True
    assert controls["standard_shogi_pawn"]["derived"] is True


def test_structural_controls_and_invariances(evidence):
    controls = evidence["structural_controls"]
    assert all(controls.values())
    assert controls["candidate_deduplication_invariant"] is True
    assert controls["type_rename_invariant"] is True
    assert controls["ruleset_rename_invariant"] is True
    assert controls["action_pattern_order_invariant"] is True
    assert controls["generated_geometry_id_invariant"] is True
    assert controls["same_path_clear_semantics"] is True
    assert controls["current_control_reproduces_f46_f42"] is True
    assert controls["density_reducers_reproduce_f46_definitions"] is True


def test_f47_records_independent_f44_and_f41_population_bindings(evidence):
    for ruleset in ("western_chess", "standard_shogi"):
        for row in evidence["gap_ledger"][ruleset].values():
            assert row["candidate_population_fingerprint"]
            assert row["accepted_f44_population_equal"] is True
            assert row["accepted_f41_population_equal"] is True


def test_c47_zero_reproduces_f46_f42_values(evidence):
    control = evidence["variants"][audit.VARIANTS[0]]
    prior = f46.audit()
    for ruleset, prior_ruleset in (("western", "western"), ("standard_shogi", "standard_shogi")):
        expected = prior["reducers"][f46.REDUCERS[0]][prior_ruleset]
        assert {key: tuple(value) for key, value in control[ruleset]["completed_density_curve"].items()} == expected["curves"]
        assert control[ruleset]["reduced_mobility"] == pytest.approx(expected["reduced_mobility"])
        assert control[ruleset]["raw_capability"] == pytest.approx(expected["raw_capability"])
        assert control[ruleset]["normalized_board_value"] == expected["normalized_board_value"]


def test_no_drift_is_derived_for_all_variants_and_rulesets(evidence):
    for variant in audit.VARIANTS:
        no_drift = evidence["no_drift"][variant]
        assert no_drift["all"] is True
        assert no_drift["accepted_population"] is True
        assert no_drift["unchanged_non_mobility"] is True
        assert no_drift["unchanged_normalization"] is True
        assert no_drift["unchanged_endpoint_definitions_except_attack_only_completion"] is True
        for ruleset in ("western_chess", "standard_shogi"):
            row = no_drift["per_ruleset"][ruleset]
            assert all(row["candidate_population"].values())
            assert all(all(values.values()) for values in row["coverage_reachability_path_efficiency"].values())
            assert all(row["normalization"].values())
            assert all(row["endpoint_definitions_except_attack_only_completion"].values())
            assert all(row["hand_value_relation"].values())


def test_interval_distance_and_directional_mismatch(evidence):
    western = evidence["variants"]
    for variant in audit.VARIANTS[1:4]:
        distance = western[variant]["western"]["interval_distance"]
        assert distance["weakly_improves_all"] is True
        assert distance["strict_improvement"] is True
        assert distance["directional_mismatch"] is False
    directional = western[audit.VARIANTS[4]]["western"]["interval_distance"]
    assert directional["directional_mismatch"] is True
    assert directional["weakly_improves_all"] is False


def test_complete_shogi_gates(evidence):
    for variant in audit.VARIANTS:
        gates = evidence["variants"][variant]["standard_shogi"]["shogi_gates"]
        assert gates["pass"] is True
        assert gates["cosine"] >= 0.95
        assert gates["spearman"] >= 0.90
        assert gates["pairwise_ordering"] >= 0.90
        assert 0.8 <= gates["hand_board_ratio_range"][0] <= gates["hand_board_ratio_range"][1] <= 1.0


def test_all_seven_selector_paths_are_real_and_reachable(evidence):
    assert evidence["selector_reachability"]["all_reachable"] is True
    assert set(evidence["selector_reachability"]["cases"]) == set(audit.QUALIFICATION_MAPPING)
    assert all(evidence["selector_reachability"]["cases"].values())
    assert evidence["selector_reachability"]["mixed_priority"]["coherent_insufficient_and_directional_mismatch"] is True


def test_h47r1a_is_verified_before_f47_result(evidence):
    assert evidence["h47r1a"] == "tests/fixtures/f47r1_endpoint_density_composite_manifest.json"
    assert evidence["gates"]["h47r1a_manifest"] is True


def test_f47_has_no_production_change(evidence):
    assert evidence["production_changed"] is False
    assert evidence["gates"]["production_unchanged"] is True
