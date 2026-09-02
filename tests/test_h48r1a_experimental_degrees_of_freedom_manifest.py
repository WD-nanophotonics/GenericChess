"""H48R1A: every F48 execution choice is frozen before execution."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "h48r1a_experimental_degrees_of_freedom_manifest.json"
PARENT_SHA = "5446ae832aa518fa5ca544c75131bb08575a4177"
EXPECTED_MANIFEST_SHA = "cfc9db0c0b25433a6b6c77f0adf41a7b0132dc017daf277f2467edab0270b3cf"


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


def test_h48r1a_is_canonical_and_preserves_h48a():
    data = _manifest()
    payload = {key: value for key, value in data.items() if key != "manifest_sha256"}
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert hashlib.sha256(canonical).hexdigest() == data["manifest_sha256"]
    assert data["manifest_sha256"] == EXPECTED_MANIFEST_SHA
    assert data["parent_h48a_sha"] == PARENT_SHA
    assert data["preservation"]["h48a_is_untouched"] is True
    assert subprocess.run(
        ["git", "cat-file", "-e", f"{PARENT_SHA}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
    ).returncode == 0


def test_h48r1a_has_no_observed_results_or_execution_artifacts():
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
    assert data["protocol_status"] == "PRE_REGISTERED_NO_OBSERVED_RESULTS"
    assert data["preservation"]["no_learning_or_screening_before_h48r1a"] is True


def test_p48_1_is_an_exact_generic_board_hand_formula():
    p = _manifest()["prior_formulas"]["P48-1"]
    assert p["type_order_helper"] == "generic_chess.learning.features.non_anchor_type_ids(compiled)"
    assert p["reference"] == "P48-0.reference_median"
    assert p["board_formula"] == "board_t = reference_median for every non-anchor current type t"
    assert p["hand_formula"] == "hand_t = reference_median * EvaluationConfig.hand_weight for every corresponding non-anchor base type t"
    assert p["hand_weight_source"] == "generic_chess.ai.evaluation.config.EvaluationConfig.hand_weight"
    assert p["hand_weight_value"] == 0.9
    assert p["exceptions"] == []
    assert "excluded and zero" in p["anchor_formula"]
    assert "native integer quantization" in p["quantization"]


def test_p48_2_is_type_label_invariant_with_frozen_factors_and_rescaling():
    p = _manifest()["prior_formulas"]["P48-2"]
    assert p["grouping"] == "group non-anchor types by equal P48-0 board value"
    assert p["distinct_value_order"] == "distinct positive P48-0 board values in numeric ascending order"
    assert p["factors_by_value_group_cycle"] == [0.5, 1.5, 0.75, 1.25]
    assert p["factor_assignment"] == "group_index modulo 4"
    assert p["equal_value_group_rule"] == "all types in an equal-value group receive the same factor"
    assert p["channels"] == "multiply corresponding board and hand channels by the same factor"
    assert "non-anchor board median" in p["rescaling"]
    assert p["negative_or_nonfinite_policy"] == "reject candidate before scoring"
    assert p["clipping"] == "none; existing checkpoint validity limit is fail-closed rejection"
    assert p["type_label_dependency"] is False
    assert p["literal_type_id_hash"] is False


def test_p48_3_is_an_exact_cyclic_permutation():
    p = _manifest()["prior_formulas"]["P48-3"]
    assert p["ordering_helper"] == "generic_chess.learning.features.non_anchor_type_ids(compiled)"
    assert p["ordering_definition"] == "lexicographically sorted tuple returned by the helper"
    assert p["permutation"] == "for ordered types (t0,...,t(n-1)), new_weight(t_i) = old_weight(t_(i+1 mod n))"
    assert p["board_channel"] != p["hand_channel"]
    assert p["n_less_than_two"] == "return an exact copy with no permutation"
    assert p["global_scale"] == "preserve P48-0 reference_median"
    assert p["type_label_dependency"] is False


def test_m48_1_freezes_vector_directions_mutations_and_population_schedule():
    data = _manifest()
    vector = data["material_vector"]
    assert vector["coordinate_order"] == "x=(board[t0],...,board[t(n-1)],hand[t0],...,hand[t(n-1)])"
    assert vector["type_order"] == "non_anchor_type_ids(compiled), lexicographically sorted"
    assert vector["dimension"] == "2*n where n is the number of non-anchor types"
    m = data["M48-1"]
    assert set(m["direction_families"]) == {
        "alternating_sign",
        "first_half_positive",
        "board_hand_differential",
        "seeded_normalized_pseudorandom",
    }
    assert m["direction_families"]["alternating_sign"] == "raw d_j = 1 when j is even, -1 when j is odd"
    assert m["direction_families"]["first_half_positive"] == "raw d_j = 1 for j < ceil(D/2), otherwise -1"
    assert m["direction_families"]["board_hand_differential"] == "raw d_j = 1 for board coordinates and -1 for hand coordinates"
    assert "CPython random.Random(Mersenne Twister) seeded 480703" in m["direction_families"]["seeded_normalized_pseudorandom"]
    assert m["direction_l2_fraction_of_reference"] == 0.25
    assert m["mutation_l2_fraction_of_reference"] == 0.10
    assert m["reference_norm"] == "L2 norm of concatenated P48-0 board+hand vector"
    assert m["sign_schedule"] == "sign = +1 when (optimizer_generation + offspring_index) is even, otherwise -1"
    assert m["population_size"] == 8
    assert m["elite_count"] == 2
    assert m["offspring_count"] == 6
    assert m["optimizer_generations"] == 3
    assert "k mod 2" in m["offspring_template"]
    assert "k mod 4" in m["offspring_template"]
    assert "retain the first" in m["duplicate_candidate_policy"]
    assert m["holdout_in_ranking"] is False


def test_search_aware_training_holdout_and_arena_positions_are_exactly_disjoint():
    data = _manifest()
    training = data["search_aware_training_positions"]
    holdout = data["teacher_holdout"]
    arena = data["paired_arena_openings"]
    assert (training["count"], training["seed"], training["min_plies"], training["max_plies"]) == (64, 480700, 2, 6)
    assert (holdout["count"], holdout["seed"], holdout["min_plies"], holdout["max_plies"]) == (64, 480701, 2, 6)
    assert (arena["count"], arena["seed"], arena["min_plies"], arena["max_plies"]) == (16, 480702, 2, 6)
    for corpus in (training, holdout, arena):
        assert corpus["identity_key"] == "generic_chess.core.identity.position_identity_key"
        assert "generate_arena_openings" in corpus["generator"]
        assert corpus["collision_policy"] == "abort before learning on any identity collision"
    assert training["disjoint_from_teacher_holdout"] is True
    assert training["disjoint_from_paired_arena_openings"] is True
    assert holdout["disjoint_from_search_aware_training"] is True
    assert holdout["disjoint_from_paired_arena_openings"] is True
    assert arena["disjoint_from_search_aware_training"] is True
    assert arena["disjoint_from_teacher_holdout"] is True
    assert training["evaluator_used_during_generation"] is False
    assert training["training_target"] == "M48-1 objective positions only; never holdout positions"


def test_prerequisite_thresholds_and_generated_eligibility_are_numeric():
    data = _manifest()
    leverage = data["material_leverage_prerequisite"]
    assert leverage["adequate_threshold"] == 0.05
    assert leverage["student_nodes"] == 2000
    assert leverage["perturbation"] == "each non-anchor type's board and corresponding hand channels jointly multiplied by 0.75 and 1.25; all other channels fixed"
    stability = data["teacher_stability_prerequisite"]
    assert (stability["primary_teacher_nodes"], stability["stability_reference_nodes"]) == (20000, 40000)
    assert stability["minimum_self_agreement"] == 0.85
    assert stability["failed_searches"] == 0
    screen = data["generated_benchmark_eligibility"]
    assert screen["screening_budget_nodes"] == 1000
    assert screen["terminal_rate"] == "== 1.0"
    assert screen["average_plies"] == "[4,200] inclusive"
    assert screen["endless_fraction"] == "<= 0.5"
    assert screen["owner0_win_rate"] == "<= 0.90"
    assert screen["owner1_win_rate"] == ">= 0.05"
    assert screen["evaluation_leverage"] == ">= 0.10 using the frozen 1000-node screening budget"
    assert screen["forced_move_fraction"] == "<= 0.30"
    assert screen["mean_legal_actions"] == ">= 2.0"
    assert screen["learned_checkpoint_input"] is False
    assert screen["h48b_required"] is True
    assert screen["h48b_before_learning"] is True


def test_arena_qualification_ownership_and_aggregation_are_exact():
    data = _manifest()
    arena = data["arena_qualification"]
    assert arena["catastrophic_regression_threshold"] == "paired mean score < 0.25 against corresponding starting checkpoint"
    assert arena["arena_execution_failure"] == "automatically catastrophic and fail closed"
    assert arena["strength_improvement"] == "paired mean score > 0.5 and bootstrap lower bound > 0.5"
    ownership = data["parameter_ownership"]
    assert {item["ownership"] for item in ownership} == {
        "RULE_INVARIANT",
        "COMPILE_TIME_DERIVED",
        "RULESET_LEARNABLE_EVALUATION",
        "RULESET_SEARCH_PROFILE_CANDIDATE",
        "GLOBAL_SEARCH_ALGORITHM",
    }
    assert data["recovery_aggregation"]["per_ruleset"].startswith("learner counts as recovered")
    assert "at least two of the three" in data["recovery_aggregation"]["per_ruleset"]
    assert "at least two primary RuleSets" in data["recovery_aggregation"]["generic_recovery"]
    assert data["recovery_aggregation"]["beyond_prior_improvement"].startswith("P48-0-trained")
    assert ">= 0.02 absolute" in data["recovery_aggregation"]["beyond_prior_improvement"]


def test_classification_precedence_and_prohibitions_are_frozen():
    data = _manifest()
    precedence = data["classification_precedence"]
    assert [row["priority"] for row in precedence] == list(range(1, 9))
    assert precedence[0]["resolution"].startswith("if leverage is limiting")
    assert precedence[3]["resolution"] == "COLD_START_RECOVERY_SUPPORTED"
    assert precedence[4]["resolution"] == "TDLEAF_MATERIAL_RECOVERY_SUPPORTED"
    assert precedence[5]["resolution"] == "SEARCH_AWARE_MATERIAL_EVOLUTION_SUPPORTED"
    assert precedence[6]["resolution"] == "LEARNING_DIRECTION_FAILURE"
    assert precedence[7]["resolution"] == "MIXED_OR_UNRESOLVED"
    assert set(data["classification_mapping"]) == {
        "TDLEAF_MATERIAL_RECOVERY_SUPPORTED",
        "SEARCH_AWARE_MATERIAL_EVOLUTION_SUPPORTED",
        "COLD_START_RECOVERY_SUPPORTED",
        "LEARNING_DIRECTION_FAILURE",
        "MATERIAL_ONLY_LEVERAGE_INSUFFICIENT",
        "SEARCH_ENGINE_LIMITS_LEARNING",
        "MIXED_OR_UNRESOLVED",
    }
    assert all(data["prohibitions"].values())
