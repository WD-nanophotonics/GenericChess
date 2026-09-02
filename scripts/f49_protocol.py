"""Validation-only authority for the pre-registered F49 H49A protocol."""

from __future__ import annotations

import hashlib
import json
import math
import random
import subprocess
from pathlib import Path
from typing import Any

from generic_chess.core.actions import action_to_dict
from generic_chess.learning.serialization import canonical_json, stable_sha256


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "fixtures" / "h49a_learning_signal_architecture_protocol_manifest.json"
H49R1A_MANIFEST_PATH = ROOT / "tests" / "fixtures" / "h49r1a_executable_diagnostic_protocol_manifest.json"
F48_BASELINE_SHA = "4bd25d405af0890668c2940eefc8b68faae1b594"
H49A_MANIFEST_SHA = "e294a27ed1a4ea4c03578321b1beeb61ba233aafe19fcad98e968a016ed14f90"
RULESET_FINGERPRINTS = {
    "A_CANONICAL_WESTERN_CHESS": "7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35",
    "B_CANONICAL_STANDARD_SHOGI": "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635",
    "C_H48B_SELECTED_GENERATED": "9f7e7201a19f8f0ee6c0eacc766c2ac3a6c313e06bbc960d5d6dfb89137db923",
}


def _manifest_sha(manifest: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()


def load_h49a_manifest() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_h49a_manifest(manifest)
    return manifest


def validate_h49a_manifest(manifest: dict[str, Any]) -> None:
    if _manifest_sha(manifest) != manifest.get("manifest_sha256"):
        raise RuntimeError("H49A manifest hash mismatch")
    if manifest.get("baseline_sha") != F48_BASELINE_SHA:
        raise RuntimeError("H49A baseline drift")
    if manifest.get("protocol_status") != "PRE_REGISTERED_NO_OBSERVED_RESULTS":
        raise RuntimeError("H49A is not a no-observations protocol checkpoint")
    if manifest.get("observed_results_present") or manifest.get("measurements_invoked") or manifest.get("learning_invoked"):
        raise RuntimeError("H49A contains observed or executed work")
    if manifest.get("production_diff_required") != "ZERO" or manifest.get("master_promotion") is not False:
        raise RuntimeError("H49A production or promotion scope drift")
    if manifest.get("f49_status") != "DIAGNOSIS_ONLY" or manifest.get("f50_status") != "NOT_STARTED":
        raise RuntimeError("H49A stage status drift")
    if manifest["authority"]["rulesets"] != RULESET_FINGERPRINTS:
        raise RuntimeError("H49A RuleSet fingerprint drift")
    if manifest["authority"]["resolved_seed_triple"] != {"training": 480700, "holdout": 480703, "arena": 480708}:
        raise RuntimeError("H49A H48C seed drift")
    if manifest["control_corpus"]["preserve_results"] is not True:
        raise RuntimeError("H49A does not preserve the F48 control")
    strata = manifest["diagnostic_strata"]
    if set(strata) != {"S49-M", "S49-E"} or any(strata[name]["count"] != 64 for name in strata):
        raise RuntimeError("H49A structural strata drift")
    if any(strata[name]["attempt_cap"] != 100000 for name in strata):
        raise RuntimeError("H49A structural attempt cap drift")
    if manifest["leverage_surfaces"]["L49-0"]["budgets"] != [500, 2000, 8000] or manifest["leverage_surfaces"]["L49-1"]["budgets"] != [500, 2000, 8000]:
        raise RuntimeError("H49A leverage budget surface drift")
    if manifest["teacher_stability_surface"]["adjacent_budget_pairs"] != [[10000, 20000], [20000, 40000], [40000, 80000]]:
        raise RuntimeError("H49A teacher stability surface drift")
    classification = manifest["classification"]
    if classification["precedence"] != list(classification["mapping"]):
        raise RuntimeError("H49A classification precedence is not frozen")
    if manifest["authority"]["f48_r4_erratum"]["fresh_r4_partition_root"] != ".generic_chess_flow/f48-r4-prerequisite-closure-final-v3":
        raise RuntimeError("H49A F48 R4 root erratum drift")
    if len(manifest["authority"]["f48_r4_erratum"]["actual_diff_files"]) != 6:
        raise RuntimeError("H49A F48 R4 diff erratum is incomplete")


def derive_stratum_candidate_seed(stratum_id: str, seed: int, index: int, attempt: int) -> int:
    return int(stable_sha256({"stage": "F49_STRATUM_POSITION", "stratum": stratum_id, "seed": seed, "index": index, "attempt": attempt})[:16], 16)


def canonical_action_order_key(action: Any) -> str:
    return canonical_json(action_to_dict(action))


def material_vector_coordinate_order(type_ids: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    ordered = tuple(type_ids)
    return tuple(f"board[{type_id}]" for type_id in ordered) + tuple(f"hand[{type_id}]" for type_id in ordered)


def raw_direction(name: str, dimension: int) -> list[float]:
    if name == "alternating_sign":
        raw = [1.0 if index % 2 == 0 else -1.0 for index in range(dimension)]
    elif name == "first_half_positive":
        raw = [1.0 if index < math.ceil(dimension / 2) else -1.0 for index in range(dimension)]
    elif name == "board_hand_differential":
        half = dimension // 2
        raw = [1.0] * half + [-1.0] * (dimension - half)
    elif name == "seeded_normalized_pseudorandom":
        rng = random.Random(480703)
        raw = [rng.uniform(-1.0, 1.0) for _ in range(dimension)]
    else:
        raise ValueError(name)
    norm = math.sqrt(sum(value * value for value in raw))
    if norm == 0.0:
        raise RuntimeError("zero F49 direction")
    return [value / norm for value in raw]


def direction_candidates(reference_vector: list[float], direction_name: str) -> list[tuple[int, list[float]]]:
    norm = math.sqrt(sum(value * value for value in reference_vector))
    direction = raw_direction(direction_name, len(reference_vector))
    candidates = []
    for sign in (-1, 1):
        candidate = [value + sign * 0.10 * norm * delta for value, delta in zip(reference_vector, direction)]
        if not all(math.isfinite(value) and value > 0 for value in candidate):
            continue
        candidates.append((sign, candidate))
    return candidates


def rescale_to_reference_median(vector: list[float], board_count: int, reference_median: float) -> list[float]:
    board = vector[:board_count]
    ordered = sorted(board)
    median = ordered[board_count // 2] if board_count % 2 else (ordered[board_count // 2 - 1] + ordered[board_count // 2]) / 2.0
    if not math.isfinite(median) or median <= 0:
        raise RuntimeError("invalid F49 median")
    scale = reference_median / median
    result = [value * scale for value in vector]
    if not all(math.isfinite(value) and value > 0 for value in result):
        raise RuntimeError("invalid F49 rescaled candidate")
    return result


def inventory_event_flags(before: dict[str, Any], after: dict[str, Any]) -> dict[str, bool]:
    board_before = before.get("board", {})
    board_after = after.get("board", {})
    board_total_before = sum(board_before.values())
    board_total_after = sum(board_after.values())
    return {
        "remove_or_capture_effect": board_total_after < board_total_before,
        "type_or_promotion_transformation": board_total_after == board_total_before and board_before != board_after,
        "hand_or_inventory_count_change": before.get("inventory", {}) != after.get("inventory", {}),
    }


def aggregate_leverage_cells(cells: list[dict[str, Any]]) -> dict[str, Any]:
    if any(cell.get("status") != "VALID" or cell.get("failed_searches", 1) != 0 for cell in cells):
        return {"status": "CELL_INVALID_SEARCH_FAILURE", "mean_flip_rate": None, "usable_perturbations": 0}
    usable = [cell for cell in cells if not cell.get("construction_failed", False)]
    if not usable:
        return {"status": "NO_USABLE_PERTURBATIONS", "mean_flip_rate": None, "usable_perturbations": 0}
    return {"status": "VALID", "mean_flip_rate": sum(cell["flip_rate"] for cell in usable) / len(usable), "usable_perturbations": len(usable)}


def teacher_pair_metrics(low_actions: list[Any], high_actions: list[Any], low_scores: list[float], high_scores: list[float]) -> dict[str, Any]:
    if not (len(low_actions) == len(high_actions) == len(low_scores) == len(high_scores)):
        raise RuntimeError("teacher metric vectors have different lengths")
    sign = lambda value: -1 if value < 0 else 1 if value > 0 else 0
    n = len(low_actions)
    return {
        "exact_best_move_agreement": sum(left == right for left, right in zip(low_actions, high_actions)) / n if n else 0.0,
        "score_sign_agreement": sum(sign(left) == sign(right) for left, right in zip(low_scores, high_scores)) / n if n else 0.0,
        "failed_searches": 0,
        "top_action_stability": sum(left == right for left, right in zip(low_actions, high_actions)) / n if n else 0.0,
        "top_k_ranking_available": False,
    }


def _valid_cell(corpus: dict[str, Any], key: str) -> bool:
    cell = corpus.get(key, {})
    return cell.get("status") == "VALID" and cell.get("failed_searches", 1) == 0


def _signal(corpus: dict[str, Any], key: str) -> bool:
    return _valid_cell(corpus, key) and corpus[key].get("mean_flip_rate", -1.0) >= 0.05


def select_f49_classification(observations: dict[str, dict[str, dict[str, Any]]]) -> tuple[str, str, dict[str, bool]]:
    """Apply the frozen H49R1A selector to structured observations."""
    witnesses = {name: [] for name in ("A", "B", "C", "D", "E")}
    for ruleset_id, corpora in observations.items():
        control = corpora["F48_CONTROL"]
        stable = {name for name, value in corpora.items() if _valid_cell(value, "teacher_40_80") and value["teacher_40_80"].get("agreement", -1.0) >= 0.85}
        learner_control = _signal(control, "L49_1_2000")
        single_control = _signal(control, "L49_0_2000")
        if "F48_CONTROL" in stable and not single_control and learner_control:
            witnesses["A"].append(ruleset_id)
        structural = [corpora[name]["L49_1_2000"]["mean_flip_rate"] for name in ("S49-M", "S49-E") if name in stable and _signal(corpora[name], "L49_1_2000")]
        if structural and max(structural) - control["L49_1_2000"].get("mean_flip_rate", 0.0) >= 0.05:
            witnesses["B"].append(ruleset_id)
        if not stable:
            witnesses["C"].append(ruleset_id)
        material = any(name in stable and _signal(corpora[name], "L49_1_2000") for name in corpora)
        nonmaterial = any(name in stable and corpora[name].get("non_material_signal", False) for name in corpora)
        if stable and not material and nonmaterial:
            witnesses["D"].append(ruleset_id)
        if stable and not material and not nonmaterial:
            witnesses["E"].append(ruleset_id)
    if len(witnesses["A"]) >= 2:
        classification = "LEARNER_ALIGNED_SIGNAL_SUPPORTED"
    elif len(witnesses["B"]) >= 2:
        classification = "STRUCTURAL_CORPUS_ARCHITECTURE_LIMITING"
    elif len(witnesses["C"]) >= 2:
        classification = "NATIVE_SEARCH_TEACHER_STABILITY_LIMITING"
    elif len(witnesses["D"]) >= 2:
        classification = "MATERIAL_ONLY_REPRESENTATION_LIMITING"
    elif len(witnesses["E"]) >= 2:
        classification = "EVALUATION_SIGNAL_BROADLY_WEAK"
    else:
        classification = "MIXED_OR_UNRESOLVED"
    mapping = {
        "LEARNER_ALIGNED_SIGNAL_SUPPORTED": "F50_LEARNABLE_MATERIAL_RECOVERY_PROTOCOL_V2",
        "STRUCTURAL_CORPUS_ARCHITECTURE_LIMITING": "F50_STRUCTURAL_CORPUS_RECOVERY_PROTOCOL",
        "NATIVE_SEARCH_TEACHER_STABILITY_LIMITING": "F50_NATIVE_SEARCH_STRENGTH_REASSESSMENT",
        "MATERIAL_ONLY_REPRESENTATION_LIMITING": "F50_GENERIC_LEARNABLE_EVALUATOR_EXPANSION",
        "EVALUATION_SIGNAL_BROADLY_WEAK": "F50_SEARCH_DOMINANCE_AND_EVALUATION_ROLE_DIAGNOSIS",
        "MIXED_OR_UNRESOLVED": "F50_LEARNING_ARCHITECTURE_REASSESSMENT",
    }
    return classification, mapping[classification], {name: bool(value) for name, value in witnesses.items()}


def validate_h49r1a_manifest(manifest: dict[str, Any]) -> None:
    if hashlib.sha256(canonical_json({key: value for key, value in manifest.items() if key != "manifest_sha256"}).encode("utf-8")).hexdigest() != manifest.get("manifest_sha256"):
        raise RuntimeError("H49R1A manifest hash mismatch")
    if manifest.get("parent_h49a_sha") != "93eee26a090c5a83487046b9165356fa1187b44e" or manifest.get("h49a_manifest_sha256") != H49A_MANIFEST_SHA:
        raise RuntimeError("H49R1A parent binding drift")
    if manifest.get("protocol_status") != "PRE_REGISTERED_NO_OBSERVED_RESULTS" or manifest.get("measurements_invoked") or manifest.get("learning_invoked"):
        raise RuntimeError("H49R1A contains observed or executed work")
    if manifest.get("production_diff_required") != "ZERO" or manifest.get("master_promotion") is not False:
        raise RuntimeError("H49R1A production scope drift")
    if manifest.get("h48r1a") != {"commit": "7e2f17bdc7ac46aabaa8b1a139c5866f1b0689ab", "manifest_sha256": "cfc9db0c0b25433a6b6c77f0adf41a7b0132dc017daf277f2467edab0270b3cf"}:
        raise RuntimeError("H49R1A inherited direction authority drift")
    expected_dependencies = manifest.get("raw_git_blob_sha256", {})
    if set(expected_dependencies) != {"generic_chess/ai/evaluation/config.py", "generic_chess/learning/features.py", "generic_chess/learning/openings.py", "generic_chess/core/actions.py", "generic_chess/core/identity.py", "generic_chess/native/compiler.py", "generic_chess/native/engine.py"}:
        raise RuntimeError("H49R1A dependency ledger incomplete")
    for path, expected in expected_dependencies.items():
        actual = hashlib.sha256(subprocess.run(["git", "show", f"{manifest['baseline_sha']}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout).hexdigest()
        if actual != expected:
            raise RuntimeError(f"H49R1A dependency hash drift: {path}")
    if manifest.get("source_openings") != {"generator": "generic_chess.learning.openings.generate_arena_openings", "count": 16, "min_plies": 2, "max_plies": 6, "evaluator_or_search_used": False, "strata": {"S49-M": {"seed": 490100}, "S49-E": {"seed": 490200}}}:
        raise RuntimeError("H49R1A source-opening contract drift")
    if manifest.get("stratum_generation", {}).get("attempt_cap_semantics") != "100000 attempts per output position":
        raise RuntimeError("H49R1A attempt-cap semantics drift")
    if manifest.get("event_predicate", {}).get("piece_values_used") is not False or manifest.get("event_predicate", {}).get("game_name_used") is not False:
        raise RuntimeError("H49R1A event predicate is not evaluator neutral")
    if not manifest.get("material_vector_and_directions", {}).get("candidate", "").startswith("P48-0_vector + sign * 0.10 * ||P48-0_vector||2 * normalized_direction"):
        raise RuntimeError("H49R1A direction candidate formula drift")
    if manifest.get("search_contract") != {"max_depth": 12, "quiescence_max_depth": 0, "quiescence_max_nodes": 0, "tt_megabytes": 8, "fresh_engine_per_search": True, "tt_sharing": False, "accepted_termination_reasons": ["completed", "node_limit", "depth_limit"], "null_action_policy": "failed_search", "failed_search_policy": "CELL_INVALID_SEARCH_FAILURE; retain failed positions in denominator"}:
        raise RuntimeError("H49R1A search contract drift")
    if manifest.get("non_material_control", {}).get("fields") != ["dynamic_mobility_weight", "promotion_potential_weight", "anchor_escape_weight"] or manifest.get("non_material_control", {}).get("factors") != [0.75, 1.25] or manifest.get("non_material_control", {}).get("budget") != 2000 or manifest.get("non_material_control", {}).get("threshold") != 0.05:
        raise RuntimeError("H49R1A non-material control drift")
    if set(manifest.get("selector", {}).get("mapping", {})) != {"A", "B", "C", "D", "E", "otherwise"}:
        raise RuntimeError("H49R1A selector mapping incomplete")


def load_h49r1a_manifest() -> dict[str, Any]:
    manifest = json.loads(H49R1A_MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_h49r1a_manifest(manifest)
    return manifest


if __name__ == "__main__":
    value = load_h49r1a_manifest()
    print(json.dumps({"status": "PASS", "kind": value["kind"], "next_boundary": value["next_authorized_boundary"]}))
