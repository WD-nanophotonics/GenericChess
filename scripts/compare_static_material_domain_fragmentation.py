"""Compare frozen rule-only topology to the pre-existing V2D development residuals."""

from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".generic_chess_flow/static-material-domain-fragmentation-freeze.json"
TOPOLOGY = ROOT / ".generic_chess_flow/static-material-domain-fragmentation-topology.json"
V2D_FREEZE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-freeze.json"
V2D_RAW = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json"
V2D_VALIDATION = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-human-validation.json"
OUTPUT = ROOT / ".generic_chess_flow/static-material-domain-fragmentation-comparison.json"
SCRIPT = ROOT / "scripts/compare_static_material_domain_fragmentation.py"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fraction(text: str) -> Fraction:
    numerator, denominator = text.split("/", 1)
    return Fraction(int(numerator), int(denominator))


def _load_frozen_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    if freeze.get("human_reference_read") is not False or freeze.get("v2d_validation_residuals_read") is not False:
        raise RuntimeError("Topology freeze does not prove pre-reference construction")
    for relative, expected in freeze["sha256"].items():
        path = ROOT / relative
        if not path.is_file() or _sha(path) != expected:
            raise RuntimeError(f"Frozen topology input changed: {relative}")
    if _sha(TOPOLOGY) != freeze["topology_candidate_sha256"]:
        raise RuntimeError("Frozen raw topology candidate changed")
    topology = json.loads(TOPOLOGY.read_text(encoding="utf-8"))
    if not topology.get("coverage_complete"):
        raise RuntimeError("Frozen topology coverage is incomplete")
    if not V2D_FREEZE.is_file() or not V2D_RAW.is_file():
        raise RuntimeError("Frozen V2D baseline inputs are missing")
    v2d_freeze = json.loads(V2D_FREEZE.read_text(encoding="utf-8"))
    for relative, expected in v2d_freeze["sha256"].items():
        path = ROOT / relative
        if not path.is_file() or _sha(path) != expected:
            raise RuntimeError(f"Frozen V2D baseline changed: {relative}")
    return freeze, topology


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2
        for offset in range(i, j):
            ranks[order[offset]] = rank
        i = j
    return ranks


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2 or len(left) != len(right):
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    covariance = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_ss = sum((a - left_mean) ** 2 for a in left)
    right_ss = sum((b - right_mean) ** 2 for b in right)
    if left_ss == 0 or right_ss == 0:
        return None
    return covariance / math.sqrt(left_ss * right_ss)


def _piece_topology(piece: dict[str, Any]) -> dict[str, Any]:
    averaged = piece["owner_averaged"]
    return {
        "outgoing_type_transition_types": piece["outgoing_type_transition_types"],
        "has_outgoing_type_transition": piece["has_outgoing_type_transition"],
        "owner_component_sizes": {owner: row["component_sizes"]
                                   for owner, row in piece["owner_graphs"].items()},
        "owner_component_count": {owner: row["component_count"]
                                   for owner, row in piece["owner_graphs"].items()},
        "owner_largest_component_fraction": {owner: row["largest_component_fraction_exact"]
                                              for owner, row in piece["owner_graphs"].items()},
        "owner_d": {owner: row["same_domain_probability_d_exact"]
                    for owner, row in piece["owner_graphs"].items()},
        "owner_f": {owner: row["fragmentation_f_exact"]
                    for owner, row in piece["owner_graphs"].items()},
        "component_count_mean": averaged["component_count_mean_exact"],
        "largest_component_fraction_mean": averaged["largest_component_fraction_mean_exact"],
        "same_domain_probability_d_mean": averaged["same_domain_probability_d_mean_exact"],
        "fragmentation_f_mean": averaged["fragmentation_f_mean_exact"],
    }


def compare() -> dict[str, Any]:
    # Integrity preflight is deliberately complete before the validation file is read.
    freeze, topology = _load_frozen_inputs()
    validation = json.loads(V2D_VALIDATION.read_text(encoding="utf-8"))
    v2d_raw = json.loads(V2D_RAW.read_text(encoding="utf-8"))
    if validation.get("kind") != "STATIC_MATERIAL_PRIOR_V2D_POST_FREEZE_HUMAN_VALIDATION":
        raise RuntimeError("Unexpected V2D validation artifact")
    if validation.get("human_metrics_computed") is not True or validation.get("metrics_are_validation_only") is not True:
        raise RuntimeError("V2D validation artifact lacks validation-only attestation")
    for relative, expected in validation["freeze_sha256"].items():
        if _sha(ROOT / relative) != expected:
            raise RuntimeError(f"V2D validation freeze mismatch: {relative}")
    if v2d_raw.get("human_reference_imported") is not False:
        raise RuntimeError("V2D rule-derived raw candidate improperly imports human values")

    chess_types = topology["rulesets"]["western_chess"]["pieces"]
    chess_result = validation["rulesets"]["western_chess"]["v2d"]
    chess_reference = validation["rulesets"]["western_chess"]["human_reference"]
    chess_v2d_values = chess_result["raw_values"]
    chess_residuals = chess_result["metrics_vs_reference"]["piece_residuals_scaled_candidate_minus_reference"]
    chess_scale = chess_result["metrics_vs_reference"]["best_single_global_scale"]
    chess_report = {}
    for type_id, reference in sorted(chess_reference.items()):
        raw_value = chess_v2d_values[type_id]
        scaled_value = raw_value * chess_scale
        residual = scaled_value - reference
        recorded_residual = chess_residuals[type_id]
        if not math.isclose(residual, recorded_residual, rel_tol=1e-11, abs_tol=1e-9):
            raise RuntimeError(f"V2D scaled residual does not reproduce: {type_id}")
        bands = chess_result["ratio_bands"].get(type_id)
        chess_report[type_id] = {
            "v2d_raw_value": raw_value,
            "global_scale": chess_scale,
            "v2d_scaled_value": scaled_value,
            "human_reference": reference,
            "v2d_scaled_residual": residual,
            "v2d_ratio_to_pawn": chess_result["pawn_normalized_ratios"][type_id],
            "frozen_ratio_band": bands["band"] if bands else None,
            "v2d_in_band": bands["pass"] if bands else None,
            **_piece_topology(chess_types[type_id]),
        }

    no_transition = [type_id for type_id in chess_report
                     if not chess_types[type_id]["has_outgoing_type_transition"]]
    if len(no_transition) < 3:
        conditions = {"coverage_complete": False, "largest_positive_residual_has_fragmentation": False,
                      "largest_f_exceeds_other_median": False, "lower_f_in_band_or_underpredicted_exists": False}
        pearson = spearman = None
        largest_positive = None
    else:
        largest_positive = max(no_transition, key=lambda type_id: chess_report[type_id]["v2d_scaled_residual"])
        others_f = [float(_fraction(chess_report[type_id]["fragmentation_f_mean"]))
                    for type_id in no_transition if type_id != largest_positive]
        ordered = sorted(others_f)
        median_other_f = (ordered[(len(ordered) - 1) // 2] + ordered[len(ordered) // 2]) / 2
        largest_f = float(_fraction(chess_report[largest_positive]["fragmentation_f_mean"]))
        lower_comparator = any(
            type_id != largest_positive
            and (chess_report[type_id]["v2d_in_band"] is True
                 or chess_report[type_id]["v2d_scaled_residual"] <= 0)
            and float(_fraction(chess_report[type_id]["fragmentation_f_mean"])) < largest_f
            for type_id in no_transition
        )
        residual_values = [chess_report[type_id]["v2d_scaled_residual"] for type_id in no_transition]
        f_values = [float(_fraction(chess_report[type_id]["fragmentation_f_mean"])) for type_id in no_transition]
        conditions = {
            "coverage_complete": True,
            "no_transition_reference_types": no_transition,
            "largest_positive_residual_type": largest_positive,
            "largest_positive_residual_has_fragmentation": chess_report[largest_positive]["v2d_scaled_residual"] > 0 and largest_f > 0,
            "largest_f_exceeds_other_median": largest_f > median_other_f,
            "median_other_f": median_other_f,
            "largest_f": largest_f,
            "lower_f_in_band_or_underpredicted_exists": lower_comparator,
        }
        pearson = _correlation(f_values, residual_values)
        spearman = _correlation(_ranks(f_values), _ranks(residual_values))

    if not topology.get("coverage_complete") or not conditions["coverage_complete"]:
        classification = "STATIC_MATERIAL_DOMAIN_FRAGMENTATION_HYPOTHESIS_INCONCLUSIVE"
    elif all(conditions[key] for key in ("largest_positive_residual_has_fragmentation",
                                         "largest_f_exceeds_other_median",
                                         "lower_f_in_band_or_underpredicted_exists")):
        classification = "STATIC_MATERIAL_DOMAIN_FRAGMENTATION_HYPOTHESIS_SUPPORTED"
    else:
        classification = "STATIC_MATERIAL_DOMAIN_FRAGMENTATION_HYPOTHESIS_NOT_SUPPORTED"

    shogi_types = topology["rulesets"]["standard_shogi"]["pieces"]
    shogi_validation = validation["rulesets"]["standard_shogi"]
    shogi_metrics = shogi_validation["metrics_by_generation"]["v2d"]
    shogi_values = shogi_validation["raw_values_by_generation"]["v2d"]
    shogi_reference = shogi_validation["human_reference_board"]
    shogi_scale = shogi_metrics["best_single_global_scale"]
    shogi_residuals = shogi_metrics["piece_residuals_scaled_candidate_minus_reference"]
    shogi_report = {}
    for type_id, reference in sorted(shogi_reference.items()):
        piece = shogi_types[type_id]
        raw_value = shogi_values[type_id]
        residual = raw_value * shogi_scale - reference
        if type_id in shogi_residuals and not math.isclose(
                residual, shogi_residuals[type_id], rel_tol=1e-11, abs_tol=1e-9):
            raise RuntimeError(f"Shogi V2D scaled residual does not reproduce: {type_id}")
        shogi_report[type_id] = {
            "v2d_raw_value": raw_value,
            "global_scale": shogi_scale,
            "v2d_scaled_value": raw_value * shogi_scale,
            "human_reference_validation_only": reference,
            "v2d_scaled_residual": residual,
            **_piece_topology(piece),
        }

    return {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_DOMAIN_FRAGMENTATION_POST_FREEZE_DEVELOPMENT_COMPARISON",
        "classification": classification,
        "topology_candidate_sha256": freeze["topology_candidate_sha256"],
        "topology_freeze_sha256": _sha(FREEZE),
        "comparison_script_sha256": _sha(SCRIPT),
        "v2d_validation_sha256": _sha(V2D_VALIDATION),
        "v2d_validation_is_preexisting_validation_only": True,
        "chess": {"global_scale": chess_scale, "types": chess_report,
                  "no_transition_descriptive_conditions": conditions,
                  "pearson_fragmentation_vs_scaled_residual": pearson,
                  "spearman_fragmentation_vs_scaled_residual": spearman},
        "standard_shogi": {"global_scale": shogi_scale, "types": shogi_report,
                           "new_shogi_gate": False},
    }


def main() -> int:
    result = compare()
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "classification": result["classification"],
                      "chess_no_transition_types": result["chess"]["no_transition_descriptive_conditions"].get("no_transition_reference_types"),
                      "largest_positive_residual_type": result["chess"]["no_transition_descriptive_conditions"].get("largest_positive_residual_type"),
                      "three_conditions": {key: value for key, value in result["chess"]["no_transition_descriptive_conditions"].items()
                                           if key in {"largest_positive_residual_has_fragmentation", "largest_f_exceeds_other_median", "lower_f_in_band_or_underpredicted_exists"}},
                      "pearson": result["chess"]["pearson_fragmentation_vs_scaled_residual"],
                      "spearman": result["chess"]["spearman_fragmentation_vs_scaled_residual"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
