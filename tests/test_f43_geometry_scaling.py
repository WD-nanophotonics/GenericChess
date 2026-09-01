"""Focused deterministic contracts for the F43 geometry-scaling prototype."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_f43_geometry_scaling.py"
EVIDENCE = ROOT / ".generic_chess_flow" / "f43_geometry_scaling.json"
VARIANTS = {
    "G43-0_LINEAR_CONTROL",
    "G43-1_PER_GEOMETRY_LOG",
    "G43-2_PER_SOURCE_LOG",
    "G43-3_HIERARCHICAL_LOG",
}


@pytest.fixture(scope="module")
def evidence():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_f43_is_frozen_counterfactual_and_has_exact_transform_set(evidence):
    assert evidence["status"] == "PASS"
    assert evidence["baseline"] == "6504a45dff2e1a726feb94d6aa83ac5128e0985d"
    assert evidence["kind"] == "F43_CAPABILITY_GEOMETRY_SCALING_PROTOTYPE"
    assert evidence["production_changed"] is False
    assert set(evidence["variants"]) == VARIANTS
    assert all(row["counterfactual_only"] for row in evidence["variants"].values())


def test_g43_linear_control_exactly_reproduces_f42(evidence):
    gate = evidence["linear_control_reproduction"]
    assert gate["predicate"] == "G43_LINEAR_CONTROL_REPRODUCES_F42"
    assert gate["pass"] is True
    for ruleset in ("western_chess", "standard_shogi"):
        assert all(all(checks.values()) for checks in gate["rulesets"][ruleset]["per_type"].values())
    western = evidence["variants"]["G43-0_LINEAR_CONTROL"]["rulesets"]["western_chess"]
    assert western["raw"] == {
        "P": pytest.approx(1.06228880393026),
        "N": pytest.approx(4.815702525575447),
        "B": pytest.approx(6.217622245358478),
        "R": pytest.approx(9.08791486310959),
        "Q": pytest.approx(15.163483676173186),
        "K": pytest.approx(5.976541940789473),
    }
    assert western["normalized_board"] == {"P": 171, "N": 775, "B": 1000, "R": 1462, "Q": 2439, "K": 0}


def test_western_pawn_ordinary_population_excludes_conditionals(evidence):
    pawn = evidence["western_pawn_contract"]
    assert pawn["ordinary_pattern_count"] == 3
    assert pawn["conditional_pattern_count"] == 3
    assert pawn["ordinary_patterns_participate"] is True
    assert pawn["conditional_patterns_excluded"] is True
    assert pawn["accepted_f42_mobility"] == pytest.approx(0.9496484375)
    assert pawn["accepted_f42_mobility_reproduced"] is True


def test_structural_and_growth_gates_are_explicit(evidence):
    gates = evidence["synthetic_geometry"]["structural_gates"]
    assert set(gates) == {
        "zero_movement_zero_contribution",
        "non_negative",
        "finite_deterministic",
        "owner_mirror_invariant",
        "type_ruleset_rename_invariant",
        "action_pattern_order_invariant",
        "candidate_dedup_invariant",
        "monotone_option_mass",
    }
    assert all(gates.values())
    cases = {row["name"]: row for row in evidence["synthetic_geometry"]["cases"]}
    assert {
        "one_step_leap", "multi_square_ray", "short_ray", "long_ray",
        "single_direction", "multi_direction", "quiet_only", "capture_only",
        "quiet_and_capture", "directional", "symmetric",
    } <= set(cases)
    growth = evidence["geometry_marginal_growth"]
    assert growth["G43-0_LINEAR_CONTROL"]["ray_marginal_growth_ratio_vs_linear"] == 1.0
    assert growth["G43-0_LINEAR_CONTROL"]["direction_marginal_growth_ratio_vs_linear"] == 1.0
    for variant in VARIANTS - {"G43-0_LINEAR_CONTROL"}:
        assert 0.0 < growth[variant]["ray_marginal_growth_ratio_vs_linear"] < 1.0
        assert 0.0 < growth[variant]["direction_marginal_growth_ratio_vs_linear"] < 1.0


def test_western_and_shogi_metrics_cover_every_variant(evidence):
    for variant in VARIANTS:
        western = evidence["variants"][variant]["western"]
        assert set(western["raw_ratios_by_pawn"]) == {"N", "B", "R", "Q"}
        assert set(western["normalized_ratios_by_pawn"]) == {"N", "B", "R", "Q"}
        assert western["broad_band_pass"] is False
        shogi = evidence["variants"][variant]["shogi"]
        assert shogi["pass"] is True
        assert {"K", "P", "N", "B", "R", "G", "S", "L", "TB", "TL", "TN", "TP", "TR", "TS"} <= set(shogi["board_values"])
        assert len(shogi["hand_board_ratio_range"]) == 2
        assert shogi["hand_board_ratio_range"] == [0.8992673992673993, 0.900355871886121]
        assert shogi["largest_rank_displacement"] >= 0


def test_all_log_variants_reduce_western_inflation_but_none_qualifies(evidence):
    matrix = evidence["qualification_matrix"]
    assert set(matrix) == VARIANTS
    assert all(row["structural_gates"] and row["ray_and_direction_monotone"] for row in matrix.values())
    assert all(row["shogi_gates_pass"] and row["no_new_feature"] for row in matrix.values())
    assert matrix["G43-0_LINEAR_CONTROL"]["diminishing_ray_and_direction"] is False
    assert matrix["G43-0_LINEAR_CONTROL"]["western_inflation_reduced"] is False
    for variant in VARIANTS - {"G43-0_LINEAR_CONTROL"}:
        assert matrix[variant]["diminishing_ray_and_direction"] is True
        assert matrix[variant]["western_inflation_reduced"] is True
    assert all(row["western_bands_pass"] is False and row["qualifies"] is False for row in matrix.values())
    allowed = {
        "GEOMETRY_SCALING_CANDIDATE_SUPPORTED",
        "MULTIPLE_GEOMETRY_SCALING_CANDIDATES",
        "GEOMETRY_SCALING_CROSS_RULESET_CONFLICT",
        "GEOMETRY_SCALING_INSUFFICIENT",
        "MIXED_OR_UNRESOLVED",
    }
    boundaries = {
        "GEOMETRY_SCALING_CANDIDATE_SUPPORTED": "F44_GEOMETRY_SCALING_INTEGRATION_PROTOTYPE",
        "MULTIPLE_GEOMETRY_SCALING_CANDIDATES": "F44_GEOMETRY_SCALING_DISCRIMINATION",
        "GEOMETRY_SCALING_CROSS_RULESET_CONFLICT": "F44_GENERIC_MATERIAL_PRIOR_REASSESSMENT",
        "GEOMETRY_SCALING_INSUFFICIENT": "F44_STRUCTURAL_CAPABILITY_FEATURE_DIAGNOSIS",
        "MIXED_OR_UNRESOLVED": "F44_CAPABILITY_PRIOR_REASSESSMENT",
    }
    assert evidence["selection"]["classification"] in allowed
    assert evidence["selection"]["next_boundary"] == boundaries[evidence["selection"]["classification"]]
