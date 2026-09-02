"""H48R2A: executable F48 training/screening protocol closure."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "h48r2a_executable_training_screening_manifest.json"
PARENT_SHA = "7e2f17bdc7ac46aabaa8b1a139c5866f1b0689ab"
EXPECTED_MANIFEST_SHA = "9db3a74f5e942e0c4bd89c99d8e275e1b1ce5273ce39dac5de0679d7e3dcdbb9"
SCREEN_REF = "a695fd6e89fb771952e208e562858710ae1e0b3d"
SCREEN_BLOBS = {
    "generic_chess/learning/leverage.py": "e95d1ee0822b08d05a097f4e5843ebfb3b453b30d7df69f6296d2eac33732bd5",
    "tests/test_learning_leverage.py": "b7d69a238532f5e9b753e7a761f73f076b94c67b6c42b3d7ef3928062d728a52",
    "docs/learning_phase1_7_evaluation_leverage.md": "f26b557fdcc87ccdfd0b11234224c30fdf766ddb6af9cac979906511ef281723",
    "pyproject.toml": "df3301af0099d1b74d5c6cd00dce991adeb1583bc3ed86034d569cb3c27eb195",
}


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


def test_h48r2a_is_canonical_and_preserves_prior_checkpoints():
    data = _manifest()
    payload = {key: value for key, value in data.items() if key != "manifest_sha256"}
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert hashlib.sha256(canonical).hexdigest() == EXPECTED_MANIFEST_SHA
    assert data["manifest_sha256"] == EXPECTED_MANIFEST_SHA
    assert data["parent_h48r1a_sha"] == PARENT_SHA
    assert data["preservation"]["h48a_untouched"] is True
    assert data["preservation"]["h48r1a_untouched"] is True
    assert subprocess.run(
        ["git", "cat-file", "-e", f"{PARENT_SHA}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
    ).returncode == 0


def test_h48r2a_has_no_observed_results_or_execution():
    data = _manifest()
    forbidden = {
        "results",
        "result",
        "observations",
        "observed_values",
        "measured_values",
        "metrics_observed",
        "winner",
    }
    assert not forbidden.intersection(_keys(data))
    policy = data["observation_policy"]
    assert all(value is False for value in policy.values())
    assert all(data["prohibitions"].values())


def test_tdleaf_calibration_and_training_schedule_is_exact():
    schedule = _manifest()["tdleaf_control_schedule"]
    calibration = schedule["calibration"]
    assert schedule["starting_priors"] == ["P48-0", "P48-1", "P48-2", "P48-3"]
    assert (calibration["games"], calibration["seed"], calibration["nodes_per_move"], calibration["max_depth"]) == (16, 4807000, 2000, 12)
    assert calibration["epsilon"] == 0.10
    assert calibration["independent_per_ruleset_and_prior"] is True
    assert "do not use calibration trajectories" in calibration["trajectory_use"]
    assert calibration["target_l2_fraction"] == 0.10
    assert calibration["max_multiplier"] == 200.0
    assert calibration["measured_l2_floor"] == 1e-9
    training = schedule["training"]
    assert training["generations"] == [1, 2, 3]
    assert training["games_per_generation"] == 16
    assert training["seed_formula"] == "4807000 + generation"
    assert "new trajectories" in training["parent"]
    assert "frozen" in training["calibrated_alpha"]
    assert (training["gamma"], training["lambda"], training["updates_per_generation"]) == (1.0, 0.7, 1)
    assert training["checkpoint_training_seed"] == 7


def test_m48_1_initial_and_later_population_templates_are_exact():
    data = _manifest()["m48_1_population"]
    assert data["initial_optimizer_generation"] == 1
    assert data["initial_population_size"] == 8
    assert [(item["id"], item["direction"], item["sign"]) for item in data["initial_members"]] == [
        ("C0", None, None),
        ("C1", "alternating_sign", "+1"),
        ("C2", "alternating_sign", "-1"),
        ("C3", "first_half_positive", "+1"),
        ("C4", "first_half_positive", "-1"),
        ("C5", "board_hand_differential", "+1"),
        ("C6", "board_hand_differential", "-1"),
        ("C7", "seeded_normalized_pseudorandom", "+1"),
    ]
    assert data["mutation_magnitude"] == "0.10 * Euclidean_L2_norm(concatenated_vector(P48-start))"
    later = data["later_population"]
    assert data["later_optimizer_generations"] == [2, 3]
    assert later["elite_survival"] == ["elite_0 unchanged", "elite_1 unchanged"]
    assert [(item["id"], item["parent"], item["direction"], item["sign"]) for item in later["offspring_templates"]] == [
        ("O0", "elite_0", "alternating_sign", "+1"),
        ("O1", "elite_0", "first_half_positive", "-1"),
        ("O2", "elite_0", "board_hand_differential", "+1"),
        ("O3", "elite_1", "alternating_sign", "-1"),
        ("O4", "elite_1", "first_half_positive", "+1"),
        ("O5", "elite_1", "seeded_normalized_pseudorandom", "-1"),
    ]
    assert later["nominal_population_size"] == 8
    assert "keep first occurrence" in later["deduplication"]
    assert later["effective_population"] == "report after deduplication"
    assert later["minimum_valid_unique_candidates"] == 2
    assert later["abort_on_insufficient_unique_candidates"] is True
    assert later["legacy_h48r1a_direction_l2_fraction_of_reference"] == {
        "value": 0.25,
        "status": "unused legacy field; not executable",
    }


def test_p48_3_dependency_and_search_limits_are_explicit():
    data = _manifest()
    p = data["p48_3_dependency_semantics"]
    assert p["canonical_type_order_dependency"] is True
    assert p["game_specific_piece_identity_dependency"] is False
    assert p["game_name_branching"] is False
    limits = data["search_limits"]
    assert {key: limits[key] for key in ("max_depth", "quiescence_max_depth", "quiescence_max_nodes", "student_nodes", "teacher_nodes", "stability_nodes")} == {
        "max_depth": 12,
        "quiescence_max_depth": 0,
        "quiescence_max_nodes": 0,
        "student_nodes": 2000,
        "teacher_nodes": 20000,
        "stability_nodes": 40000,
    }
    assert limits["fresh_engine_per_evaluator_comparison"] is True
    assert limits["tt_sharing_across_checkpoints"] is False
    assert "abort" in limits["failed_search"]


def test_h48b_authority_binds_phase17_blobs_and_all_screening_constants():
    data = _manifest()["h48b_screening_authority"]
    assert data["required"] is True
    assert data["required_before_learning"] is True
    assert data["source_ref"] == SCREEN_REF
    assert {item["path"]: item["blob_sha256"] for item in data["source_blobs"]} == SCREEN_BLOBS
    assert (data["candidate_count"], data["candidate_master_seed"], data["candidate_board_size"]) == (32, 20260807, 6)
    assert data["candidate_seed_formula"] == "candidate_seed = candidate_master_seed * 1000 + index"
    assert data["candidate_presets_cycle"] == ["free_random", "bilateral_random", "classic_like"]
    assert (data["candidate_opening_count"], data["candidate_opening_seed"], data["candidate_corpus_count"], data["candidate_corpus_seed"]) == (4, 314159, 16, 42)
    assert (data["candidate_arena_pairs"], data["candidate_arena_nodes"], data["candidate_arena_max_depth"]) == (2, 800, 12)
    assert (data["candidate_leverage_budget"], data["candidate_tactical_shallow"], data["candidate_tactical_deep"]) == (1000, 500, 4000)
    assert data["leverage_factors"] == [0.75, 1.25]
    eligibility = data["eligibility"]
    assert eligibility == {
        "terminal_rate": "== 1.0",
        "average_plies": "[4,200] inclusive",
        "endless_draw_fraction": "<= 0.5",
        "owner0_win_rate": "<= 0.90",
        "owner1_win_rate": ">= 0.05",
        "tactical_shallow_deep_agreement": "[0.30,0.98] inclusive",
        "evaluation_leverage": ">= 0.10",
        "forced_move_fraction": "<= 0.30",
        "mean_legal_actions": ">= 2.0",
    }
    assert data["learned_checkpoint_input"] is False
    assert len(data["h48b_outputs_required"]) == 5


def test_selector_truth_table_ownership_and_thresholds_are_executable_data():
    data = _manifest()
    selector = data["classification_selector"]
    assert selector["booleans"] == {
        "admissible": "leverage_pass AND teacher_stability_pass",
        "ruleset_recovered": "at_least_two_of_three_disturbed_priors_recover AND none_catastrophic",
        "generic_recovery": "at_least_two_admissible_primary_rulesets satisfy ruleset_recovered",
        "beyond_prior": "p48_0_holdout_agreement_delta >= 0.02 AND arena_mean > 0.5 AND bootstrap_lower_bound > 0.5 AND integrity_gates_pass",
        "generic_beyond_prior": "beyond_prior on at_least_two_admissible_primary_rulesets",
    }
    assert [row["step"] for row in selector["precedence"]] == ["A1", "A2", "A3", "B", "C", "D", "E", "F", "G"]
    assert [row["classification"] for row in selector["precedence"] if row["step"] != "B"] == [
        "MATERIAL_ONLY_LEVERAGE_INSUFFICIENT",
        "SEARCH_ENGINE_LIMITS_LEARNING",
        "MIXED_OR_UNRESOLVED",
        "COLD_START_RECOVERY_SUPPORTED",
        "TDLEAF_MATERIAL_RECOVERY_SUPPORTED",
        "SEARCH_AWARE_MATERIAL_EVOLUTION_SUPPORTED",
        "LEARNING_DIRECTION_FAILURE",
        "MIXED_OR_UNRESOLVED",
    ]
    assert {row["ownership"] for row in data["parameter_ownership"]} == {
        "RULE_INVARIANT",
        "COMPILE_TIME_DERIVED",
        "RULESET_LEARNABLE_EVALUATION",
        "GLOBAL_SEARCH_ALGORITHM",
        "RULESET_SEARCH_PROFILE_CANDIDATE",
    }
    assert data["arena_qualification"]["catastrophic_regression_threshold"] == "paired mean score < 0.25 against corresponding starting checkpoint"
    assert data["recovery_aggregation"]["beyond_prior_improvement"].startswith("P48-0 holdout")


def test_phase17_authority_blobs_match_raw_git_bytes():
    data = _manifest()["h48b_screening_authority"]
    for item in data["source_blobs"]:
        raw = subprocess.run(
            ["git", "cat-file", "blob", f"{SCREEN_REF}:{item['path']}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert hashlib.sha256(raw).hexdigest() == item["blob_sha256"]
