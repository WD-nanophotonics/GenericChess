"""H48A: pre-registered learnable-material recovery protocol only."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "h48a_learnable_material_recovery_manifest.json"
BASELINE_SHA = "d4a0d8baf00f95dc9eef315183c59e394ed5928f"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


def test_h48a_manifest_is_canonical_and_prehistory_anchored():
    data = _manifest()
    payload = {key: value for key, value in data.items() if key != "manifest_sha256"}
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert hashlib.sha256(canonical).hexdigest() == data["manifest_sha256"]
    assert data["kind"] == "H48A_LEARNABLE_MATERIAL_RECOVERY_PROTOCOL"
    assert data["protocol_status"] == "PRE_REGISTERED_NO_OBSERVED_RESULTS"
    assert data["baseline"]["sandbox_sha"] == BASELINE_SHA
    assert subprocess.run(
        ["git", "cat-file", "-e", f"{BASELINE_SHA}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
    ).returncode == 0


def test_h48a_contains_no_observed_results_or_experiment_artifacts():
    data = _manifest()
    forbidden = {
        "results",
        "result",
        "observations",
        "measured_values",
        "metrics_observed",
        "winner",
    }
    assert not forbidden.intersection(_keys(data))
    assert data["result_policy"] == {
        "observed_results_in_h48a": False,
        "benchmark_selection_uses_learned_checkpoints": False,
        "human_values_used_by_learner": False,
        "h48b_before_training_if_generated_selection_needed": True,
    }


def test_h48a_freezes_all_three_benchmark_classes_and_pre_learning_selection():
    data = _manifest()
    rulesets = data["benchmark_rulesets"]
    assert [item["id"] for item in rulesets] == [
        "A_CANONICAL_WESTERN_CHESS",
        "B_CANONICAL_STANDARD_SHOGI",
        "C_GENERATED_EVALUATION_SENSITIVE",
    ]
    generated = rulesets[2]
    assert generated["selection_before_learning"] is True
    assert generated["h48b_required_if_screening_is_needed"] is True
    assert "learned" not in generated["selection_rule"]
    assert generated["construction"] == (
        "generator board_size=6, master_seed=20260807, "
        "candidate_seeds=20260807000..20260807031, presets cycling "
        "free_random/bilateral_random/classic_like"
    )


def test_h48a_freezes_layer_ownership_and_trainable_boundary():
    data = _manifest()["architecture_layers"]
    assert set(data) == {
        "L0_rule_semantics",
        "L1_compiled_ruleset_execution",
        "L2_cold_start_evaluation_prior",
        "L3_ruleset_specific_learnable_evaluation",
        "L4_search",
        "L5_learning_meta_controller",
    }
    assert data["L0_rule_semantics"]["learning_may_change"] is False
    assert data["L1_compiled_ruleset_execution"]["learning_may_change"] is False
    assert data["L2_cold_start_evaluation_prior"]["learning_may_change"] is False
    assert data["L4_search"]["learning_may_change"] is False
    assert data["L3_ruleset_specific_learnable_evaluation"]["trainable_parameters"] == [
        "per_current_type_board_material_weight",
        "per_base_type_hand_material_weight_where_applicable",
    ]
    assert "per node" in data["L5_learning_meta_controller"]["contract"]


def test_h48a_freezes_exact_starting_priors_and_learners():
    data = _manifest()
    assert [item["id"] for item in data["starting_priors"]] == [
        "P48-0", "P48-1", "P48-2", "P48-3"
    ]
    definitions = {item["id"]: item["definition"] for item in data["starting_priors"]}
    assert "rule-derived Generation-0" in definitions["P48-0"]
    assert "same positive reference-median" in definitions["P48-1"]
    assert "type-label-invariant" in definitions["P48-2"]
    assert "cyclic permutation" in definitions["P48-3"]
    assert [item["id"] for item in data["learner_variants"]] == ["M48-0", "M48-1"]
    assert data["learner_variants"][0]["contract"].endswith("unchanged")
    assert data["learner_variants"][1]["human_material_target"] is False


def test_h48a_freezes_disjoint_generic_corpora_and_search_budgets():
    data = _manifest()
    corpora = data["corpora"]
    assert corpora["training"]["external_data"] is False
    assert corpora["teacher_holdout"]["external_data"] is False
    assert corpora["teacher_holdout"]["disjoint_from_training"] is True
    assert "fail the run" in corpora["teacher_holdout"]["disjointness_gate"]
    assert corpora["teacher_holdout"]["teacher_nodes"] == 20000
    assert corpora["teacher_holdout"]["student_nodes"] == 2000
    assert corpora["teacher_holdout"]["teacher_checkpoint"] == "fixed P48-0 checkpoint"
    assert data["fixed_compute_budget"]["search_budgets"] == [250, 500, 1000, 2000, 4000]
    assert data["fixed_compute_budget"]["training_generations"] == [0, 1, 2, 3]
    assert corpora["paired_arena"]["pairs"] == 16
    assert corpora["paired_arena"]["color_swap"] is True
    assert corpora["paired_arena"]["fresh_engines"] is True


def test_h48a_freezes_recovery_strength_efficiency_and_classification_gates():
    data = _manifest()
    recovery = data["qualification"]["recovery_threshold"]
    assert recovery["holdout_agreement_fraction_of_p48_0"] == 0.90
    assert recovery["minimum_absolute_improvement_over_disturbed_initial"] == 0.05
    assert recovery["catastrophic_arena_regression"] is False
    assert data["qualification"]["strength_improvement"]["minimum_paired_score"] == 0.5
    assert len(data["classification_mapping"]) == 7
    assert len(data["efficiency_gates"]) == 6
    assert all(data["prohibitions"].values())
    assert data["prohibitions"]["production_learning_integration"] is True
    assert data["prohibitions"]["master_promotion"] is True

