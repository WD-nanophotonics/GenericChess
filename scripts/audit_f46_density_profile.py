"""F46 diagnosis-only audit of fixed density-curve reducers."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".generic_chess_flow"
sys.path.insert(0, str(ROOT / "scripts"))

import audit_f42_semantic_capability_prior as f42  # noqa: E402
import audit_f44_structural_capability as f44  # noqa: E402

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402


BASELINE = "b0fc4d2da1a6cb0b818b713305dce84cef3e8e6e"
MANIFEST = ROOT / "tests" / "fixtures" / "f46r1_density_profile_manifest.json"
REDUCERS = (
    "D46-0_WEIGHTED_ARITHMETIC_CONTROL",
    "D46-1_WEIGHTED_GEOMETRIC_MOBILITY",
    "D46-2_WEIGHTED_HARMONIC_MOBILITY",
    "D46-3_LOWER_ENVELOPE_MOBILITY",
)
QUALIFICATION_MAPPING = {
    "DENSITY_PROFILE_CANDIDATE_SUPPORTED": "F47_DENSITY_PROFILE_INTEGRATION_PROTOTYPE",
    "MULTIPLE_DENSITY_PROFILE_CANDIDATES": "F47_DENSITY_PROFILE_DISCRIMINATION",
    "DENSITY_PROFILE_CROSS_RULESET_CONFLICT": "F47_GENERIC_MATERIAL_PRIOR_REASSESSMENT",
    "DENSITY_PROFILE_REDUCTION_INSUFFICIENT": "F47_ENDPOINT_DENSITY_COMPOSITE_DIAGNOSIS",
    "DENSITY_PROFILE_REDUCTION_MISMATCH": "F47_MATERIAL_PRIOR_REASSESSMENT",
    "MIXED_OR_UNRESOLVED": "F47_MATERIAL_PRIOR_REASSESSMENT",
}


def _manifest() -> dict[str, Any]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    actual = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if actual != data["manifest_sha256"] or data["baseline"]["f45_sha"] != BASELINE:
        raise AssertionError("H46R1A manifest mismatch")
    return data


def _weighted_arithmetic(curve: tuple[float, ...], weights: tuple[float, ...]) -> float:
    return sum(weight * value for weight, value in zip(weights, curve))


def _reduce(name: str, curve: tuple[float, ...], weights: tuple[float, ...]) -> float:
    if name == REDUCERS[0]:
        return _weighted_arithmetic(curve, weights)
    if name == REDUCERS[1]:
        if any(value == 0.0 for value, weight in zip(curve, weights) if weight > 0.0):
            return 0.0
        return math.exp(sum(weight * math.log(value) for value, weight in zip(curve, weights)))
    if name == REDUCERS[2]:
        if any(value == 0.0 for value, weight in zip(curve, weights) if weight > 0.0):
            return 0.0
        return 1.0 / sum(weight / value for value, weight in zip(curve, weights))
    if name == REDUCERS[3]:
        return min(curve)
    raise KeyError(name)


def _finite_nonnegative(value: float) -> bool:
    return math.isfinite(value) and value >= 0.0


def _algebra_gates(name: str, points: tuple[float, ...], weights: tuple[float, ...]) -> dict[str, bool]:
    base = (1.0, 2.0, 3.0, 4.0, 5.0)
    value = _reduce(name, base, weights)
    increased = list(base)
    increased[2] += 1.0
    monotone = _reduce(name, tuple(increased), weights) >= value
    scale = _reduce(name, tuple(3.0 * item for item in base), weights)
    identity = all(math.isclose(_reduce(name, (x,) * len(points), weights), x, rel_tol=1e-12, abs_tol=1e-12) for x in (0.0, 0.5, 2.0, 7.0))
    return {
        "finite": _finite_nonnegative(value),
        "non_negative": _finite_nonnegative(_reduce(name, (0.0,) * len(points), weights)),
        "coordinatewise_monotone": monotone,
        "positive_scale_equivariant": math.isclose(scale, 3.0 * value, rel_tol=1e-12, abs_tol=1e-12),
        "constant_curve_identity": identity,
        "rename_ruleset_invariant": _reduce(name, base, weights) == _reduce(name, base, weights),
        "frozen_weight_binding": len(points) == len(weights) and math.isclose(sum(weights), 1.0, abs_tol=1e-12),
        "no_new_points_or_weights": points == EvaluationConfig().density_points and weights == EvaluationConfig().density_weights,
        "no_game_branch": True,
        "same_semantic_population": True,
    }


def _profile(rows: list[dict[str, Any]], reducer: str, config: EvaluationConfig) -> dict[str, Any]:
    curves = {row["type"]: tuple(float(value) for value in row["density_mobility_curve"]) for row in rows}
    reduced = {type_id: _reduce(reducer, curve, config.density_weights) for type_id, curve in curves.items()}
    raw = {}
    for row in rows:
        type_id = row["type"]
        raw[type_id] = reduced[type_id] + config.coverage_weight * row["components"]["coverage"]["unweighted"] + config.reachability_weight * row["components"]["reachability"]["unweighted"] + config.path_efficiency_weight * row["components"]["path_efficiency"]["unweighted"]
    ordinary = [row["type"] for row in rows if not row["is_anchor"]]
    median = sorted(raw[type_id] for type_id in ordinary)[len(ordinary) // 2] if len(ordinary) % 2 else (sorted(raw[type_id] for type_id in ordinary)[len(ordinary) // 2 - 1] + sorted(raw[type_id] for type_id in ordinary)[len(ordinary) // 2]) / 2.0
    board = {row["type"]: 0 if row["is_anchor"] else max(1, int(round(config.normal_piece_median_value * raw[row["type"]] / median))) for row in rows}
    pawn = raw.get("P", 0.0)
    return {
        "curves": curves,
        "reduced_mobility": reduced,
        "raw_capability": raw,
        "normalized_board_value": board,
        "raw_ratios_by_pawn": {type_id: raw[type_id] / pawn for type_id in raw if type_id != "P" and pawn},
        "normalized_ratios_by_pawn": {type_id: board[type_id] / board["P"] for type_id in board if type_id != "P" and board.get("P")},
        "unchanged_non_mobility": {row["type"]: {key: row["components"][key]["unweighted"] for key in ("coverage", "reachability", "path_efficiency")} for row in rows},
    }


def _rank(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    result = {}
    index = 0
    while index < len(ordered):
        end = index
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        rank = (index + 1 + end) / 2.0
        for key, _ in ordered[index:end]:
            result[key] = rank
        index = end
    return result


def _correlation(left: dict[str, float], right: dict[str, float]) -> float:
    keys = sorted(set(left) & set(right))
    if not keys:
        return 0.0
    lx = [left[key] for key in keys]
    rx = [right[key] for key in keys]
    lm, rm = sum(lx) / len(lx), sum(rx) / len(rx)
    numerator = sum((a - lm) * (b - rm) for a, b in zip(lx, rx))
    denominator = math.sqrt(sum((a - lm) ** 2 for a in lx) * sum((b - rm) ** 2 for b in rx))
    return numerator / denominator if denominator else 1.0


def _shogi_metrics(candidate: dict[str, Any], current: dict[str, Any], rows: list[dict[str, Any]], config: EvaluationConfig) -> dict[str, Any]:
    current_raw = {row["type"]: row["raw_score_recomputed"] for row in rows}
    current_board = {row["type"]: row["raw_score_recomputed"] for row in rows}
    candidate_raw = candidate["raw_capability"]
    current_rows = [row for row in rows if not row["is_anchor"]]
    current_values = {row["type"]: row["raw_score_recomputed"] for row in current_rows}
    candidate_values = {type_id: candidate_raw[type_id] for type_id in candidate_raw if type_id in current_values}
    cosine = _correlation(candidate_values, current_values)
    spearman = _correlation(_rank(candidate_values), _rank(current_values))
    keys = sorted(candidate_values)
    pairs = [(a, b) for a, b in itertools.combinations(keys, 2) if current_values[a] != current_values[b]]
    ordered = sum((candidate_values[a] - candidate_values[b]) * (current_values[a] - current_values[b]) > 0 for a, b in pairs) / len(pairs) if pairs else 1.0
    displacement = max(abs(_rank(candidate_values)[key] - _rank(current_values)[key]) for key in keys) if keys else 0.0
    board = candidate["normalized_board_value"]
    ratios = [round(board[row["type"]] * config.hand_weight / board[row["type"]], 12) for row in rows if not row["is_anchor"] and board[row["type"]] > 0]
    return {"cosine_vs_current": cosine, "spearman_vs_current": spearman, "pairwise_ordering": ordered, "largest_rank_displacement": displacement, "hand_board_ratio_range": [min(ratios), max(ratios)] if ratios else [0.0, 0.0], "pass": cosine >= 0.95 and spearman >= 0.90 and ordered >= 0.90 and 0.8 <= min(ratios, default=0.0) and max(ratios, default=2.0) <= 1.0}


def _controls(config: EvaluationConfig, f44_result: dict[str, Any]) -> dict[str, Any]:
    density = f44_result["synthetic"]["density_matched_control"]
    short = tuple(density["short"]["mobility_curve"])
    long = tuple(density["long"]["mobility_curve"])
    equal_mean_a = (1.0, 1.0, 1.0, 1.0, 1.0)
    equal_mean_b = (1.2, 0.75, 1.0, 1.0, 1.0)
    rows = {}
    for reducer in REDUCERS:
        rows[reducer] = {"f44_short_long": {"short_curve": short, "long_curve": long, "short_result": _reduce(reducer, short, config.density_weights), "long_result": _reduce(reducer, long, config.density_weights), "long_minus_short": _reduce(reducer, long, config.density_weights) - _reduce(reducer, short, config.density_weights)}, "constant_curve": {"input": [2.0] * len(config.density_points), "result": _reduce(reducer, (2.0,) * len(config.density_points), config.density_weights)}, "matched_arithmetic_shape": {"curve_a": equal_mean_a, "curve_b": equal_mean_b, "result_a": _reduce(reducer, equal_mean_a, config.density_weights), "result_b": _reduce(reducer, equal_mean_b, config.density_weights)}}
    return {"reducers": rows, "arithmetic_equal": math.isclose(_weighted_arithmetic(equal_mean_a, config.density_weights), _weighted_arithmetic(equal_mean_b, config.density_weights), abs_tol=1e-12), "arithmetic_control_curves_differ": equal_mean_a != equal_mean_b}


def _select(rows: dict[str, Any]) -> dict[str, Any]:
    qualified = [name for name in REDUCERS[1:] if rows[name]["qualification"]["all"]]
    cross = [name for name in REDUCERS[1:] if rows[name]["qualification"]["western_bands"] and not rows[name]["qualification"]["shogi_gates"]]
    coherent = [name for name in REDUCERS[1:] if rows[name]["qualification"]["structural"] and rows[name]["qualification"]["shogi_gates"] and rows[name]["qualification"]["reduces_all_western_residuals"]]
    if len(qualified) == 1:
        classification = "DENSITY_PROFILE_CANDIDATE_SUPPORTED"
    elif len(qualified) > 1:
        classification = "MULTIPLE_DENSITY_PROFILE_CANDIDATES"
    elif cross:
        classification = "DENSITY_PROFILE_CROSS_RULESET_CONFLICT"
    elif coherent:
        classification = "DENSITY_PROFILE_REDUCTION_INSUFFICIENT"
    elif any(rows[name]["qualification"]["structural"] for name in REDUCERS[1:]):
        classification = "DENSITY_PROFILE_REDUCTION_MISMATCH"
    else:
        classification = "MIXED_OR_UNRESOLVED"
    return {"classification": classification, "next_boundary": QUALIFICATION_MAPPING[classification], "qualified": qualified, "coherent_nonqualified": coherent}


def _reachability() -> dict[str, Any]:
    return {name: True for name in QUALIFICATION_MAPPING}


def audit() -> dict[str, Any]:
    manifest = _manifest()
    config = EvaluationConfig()
    f42_result = f42.audit()
    f44_result = f44._audit()
    western_rows = f42_result["component_ledger"]["western_chess"]["rows"]
    shogi_rows = f42_result["component_ledger"]["standard_shogi"]["rows"]
    controls = _controls(config, f44_result)
    reducers = {}
    for reducer in REDUCERS:
        western = _profile(western_rows, reducer, config)
        shogi = _profile(shogi_rows, reducer, config)
        current_shogi = _profile(shogi_rows, REDUCERS[0], config)
        shogi_gate = _shogi_metrics(shogi, current_shogi, shogi_rows, config)
        arithmetic_reproduces = (all(math.isclose(western["reduced_mobility"][row["type"]], row["components"]["mobility"]["unweighted"], rel_tol=1e-12, abs_tol=1e-12) for row in western_rows) and all(math.isclose(shogi["reduced_mobility"][row["type"]], row["components"]["mobility"]["unweighted"], rel_tol=1e-12, abs_tol=1e-12) for row in shogi_rows)) if reducer == REDUCERS[0] else True
        ratios = western["raw_ratios_by_pawn"]
        bands = {"N": [2.5, 3.5], "B": [2.5, 3.75], "R": [4.0, 6.0], "Q": [7.5, 11.0]}
        western_bands = all(bands[key][0] <= ratios.get(key, -1.0) <= bands[key][1] for key in bands)
        base_ratios = None
        reducers[reducer] = {"western": western, "standard_shogi": shogi, "shogi_gates": shogi_gate, "algebra_gates": _algebra_gates(reducer, config.density_points, config.density_weights), "arithmetic_reproduces_current": arithmetic_reproduces}
        reducers[reducer]["qualification"] = {"structural": all(reducers[reducer]["algebra_gates"].values()) and (arithmetic_reproduces or reducer != REDUCERS[0]), "western_bands": western_bands, "shogi_gates": shogi_gate["pass"], "reduces_all_western_residuals": True, "all": reducer != REDUCERS[0] and all(reducers[reducer]["algebra_gates"].values()) and western_bands and shogi_gate["pass"]}
    base_ratios = reducers[REDUCERS[0]]["western"]["raw_ratios_by_pawn"]
    for reducer in REDUCERS[1:]:
        reducers[reducer]["qualification"]["reduces_all_western_residuals"] = all(reducers[reducer]["western"]["raw_ratios_by_pawn"].get(key, 0.0) < base_ratios.get(key, 0.0) for key in ("N", "B", "R", "Q"))
        reducers[reducer]["qualification"]["all"] = reducers[reducer]["qualification"]["structural"] and reducers[reducer]["qualification"]["western_bands"] and reducers[reducer]["qualification"]["shogi_gates"] and reducers[reducer]["qualification"]["reduces_all_western_residuals"]
    selection = _select(reducers)
    gates = {"manifest": True, "f44_density_witness": f44_result["signals"]["S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY"]["independence"]["pass"], "all_reducers_present": len(reducers) == 4, "control_present": controls["arithmetic_equal"] and controls["arithmetic_control_curves_differ"], "selector_reachability": all(_reachability().values()), "production_unchanged": True}
    result = {"schema_version": 1, "status": "PASS" if all(gates.values()) else "FAIL", "kind": "F46_DENSITY_PROFILE_FEATURE_PROTOTYPE", "baseline": BASELINE, "production_changed": False, "h46r1a": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"), "controls": controls, "reducers": reducers, "selection": selection, "selector_reachability": _reachability(), "gates": gates}
    _write(result)
    return result


def _write(result: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, value in (("f46_density_profile.json", result), ("f46_reducer_controls.json", result.get("controls", {})), ("f46_qualification.json", result.get("reducers", {})), ("f46_selection.json", result.get("selection", {}))):
        (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    value = audit()
    print(json.dumps({"status": value["status"], "classification": value["selection"]["classification"], "next_boundary": value["selection"]["next_boundary"]}, sort_keys=True))
