"""Focused deterministic contracts for the F42 diagnosis-only audit."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_f42_semantic_capability_prior.py"
EVIDENCE = ROOT / ".generic_chess_flow" / "f42_evidence.json"


@pytest.fixture(scope="module")
def evidence():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_f42_reproduces_accepted_f41_before_diagnosis(evidence):
    assert evidence["status"] == "PASS"
    assert evidence["baseline_sha"] == "fa9a9c334fce331a5059f05a3e261e1fd85fbc7c"
    assert evidence["reproduction"]["accepted_f41_r1_reproduction_matches"] is True
    assert evidence["reproduction"]["standard_shogi"]["positive_control_metrics"]["board_value_cosine_vs_current"] >= 0.95
    assert evidence["reproduction"]["standard_shogi"]["positive_control_metrics"]["spearman_vs_current"] == 1.0


def test_component_ledger_has_complete_absolute_and_share_accounting(evidence):
    for ruleset in ("western_chess", "standard_shogi"):
        rows = evidence["component_ledger"][ruleset]["rows"]
        assert rows
        for row in rows:
            assert set(row["components"]) == {"mobility", "coverage", "reachability", "path_efficiency"}
            assert len(row["density_mobility_curve"]) == 5
            assert row["candidate_source_count"] >= 0
            assert row["candidate_destination_count"] >= 0
            assert abs(sum(item["share_of_raw"] for item in row["components"].values()) - 1.0) <= 1e-12 if row["raw_score_recomputed"] else True
            assert row["pattern_summary"]["ordinary_semantic_pattern_count"] >= 0
            assert row["pattern_summary"]["conditional_semantic_pattern_count"] >= 0
            assert set(row["pattern_summary"]["leap_ray_composition"]) == {"leap", "ray"}


def test_formula_ablations_are_frozen_counterfactuals(evidence):
    ablations = evidence["formula_ablation"]
    assert ablations["variants"] == [
        "full_formula", "mobility_only", "minus_coverage", "minus_reachability",
        "minus_path_efficiency", "graph_global_only", "mobility_plus_coverage",
        "mobility_plus_reachability", "mobility_plus_path_efficiency",
    ]
    assert ablations["existing_weights_unchanged"] is True
    for variant, result in ablations["ledger"].items():
        assert result["counterfactual_only"] is True
        assert set(result["western"]["raw_ratios_by_pawn"]) == {"N", "B", "R", "Q"}
        assert set(result["western"]["normalized_ratios_by_pawn"]) == {"N", "B", "R", "Q"}
        assert set(result["shogi"]) == {"board_value_cosine_vs_current", "spearman_vs_current", "pairwise_ordering_vs_current"}
        assert len(result["western"]["inflation_effect_vs_full_raw"]) == 4


def test_redundancy_and_synthetic_geometry_are_explicit(evidence):
    redundancy = evidence["redundancy"]
    assert set(redundancy["pairwise_pearson"]) == {"mobility", "coverage", "reachability", "path_efficiency"}
    assert len(redundancy["mechanically_coupled_quantities"]) == 3
    synthetic = evidence["synthetic_geometry"]
    assert synthetic["same_analyzer_and_compiler"] is True
    cases = {case["name"]: case for case in synthetic["cases"]}
    assert {"one_step_leap", "multi_square_ray", "short_ray", "long_ray", "single_direction", "multi_direction", "quiet_only", "capture_only", "quiet_and_capture", "directional", "symmetric"} <= set(cases)
    assert cases["long_ray"]["metrics"]["raw_score"] > cases["short_ray"]["metrics"]["raw_score"]
    assert cases["multi_direction"]["metrics"]["raw_score"] > cases["single_direction"]["metrics"]["raw_score"]
    assert cases["quiet_only"]["metrics"]["raw_score"] > cases["capture_only"]["metrics"]["raw_score"]


def test_pawn_suppression_and_shogi_cross_rule_are_quantified(evidence):
    pawn = evidence["pawn_suppression"]
    assert pawn["type"] == "P"
    assert pawn["directional_movement"]["owner_mirror_contract"] is True
    assert pawn["conditional_patterns_excluded_from_ordinary_capability"]["count"] >= 1
    assert pawn["separate_quiet_capture_geometry"]["target_relation_counts"]
    assert pawn["density_endpoint_weighting"]["without_endpoint_factor"] != pawn["density_endpoint_weighting"]["full_density_weighted_mobility"]
    assert pawn["western_gap_attribution"]
    cross = evidence["shogi_cross_rule"]
    assert set(cross["same_mechanisms_present"]) == {"mobility", "coverage", "reachability", "path_efficiency"}
    assert cross["positive_control"]["pass"] is True


def test_single_final_diagnosis_and_boundary_are_mapped(evidence):
    selection = evidence["selection"]
    assert selection["primary_diagnosis"] == "RAY_OR_DIRECTIONAL_SCALING_PRIMARY"
    assert selection["next_boundary"] == "F43_CAPABILITY_GEOMETRY_SCALING_PROTOTYPE"
    assert selection["normalization_assessment"]["classification"] == "NORMALIZATION_NON_PRIMARY"
    predicates = selection["predicate_ledger"]
    assert sum(value["supported"] for value in predicates.values()) == 1
    assert predicates["NORMALIZATION_PRIMARY"]["supported"] is False
    assert predicates["CAPABILITY_COMPONENT_DOUBLE_COUNTING_PRIMARY"]["supported"] is False
    assert predicates["RAY_OR_DIRECTIONAL_SCALING_PRIMARY"]["supported"] is True
    assert selection["quantitative_selection_evidence"]["ray_length_delta"] > 0
    assert selection["quantitative_selection_evidence"]["direction_count_delta"] > 0
    assert "compared across units" in selection["quantitative_selection_evidence"]["selection_rule"]
    assert selection["western_inflation_not_a_loss_function"] is True
    assert evidence["production_changed"] is False
