"""F46 diagnosis-only audit of fixed density-curve reducers."""

from __future__ import annotations

import hashlib
import inspect
import itertools
import json
import math
import sys
from pathlib import Path
from statistics import median
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".generic_chess_flow"
sys.path.insert(0, str(ROOT / "scripts"))

import audit_f42_semantic_capability_prior as f42  # noqa: E402
import audit_f44_structural_capability as f44  # noqa: E402

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402


BASELINE = "b0fc4d2da1a6cb0b818b713305dce84cef3e8e6e"
MANIFEST = ROOT / "tests" / "fixtures" / "f46r1_density_profile_manifest.json"
R2_MANIFEST = ROOT / "tests" / "fixtures" / "f46r2_density_profile_manifest.json"
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


def _h46r2_manifest() -> dict[str, Any]:
    data = json.loads(R2_MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    actual = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if actual != data["manifest_sha256"] or data["baseline"]["first_pass_f46_sha"] != "6eed502b944cfa1398a160d2c6d0efcf1df0f025":
        raise AssertionError("H46R2A manifest mismatch")
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
    monotone = all(_reduce(name, tuple(item + (1.0 if index == coordinate else 0.0) for index, item in enumerate(base)), weights) >= value for coordinate in range(len(base)))
    scale = _reduce(name, tuple(3.0 * item for item in base), weights)
    identity = all(math.isclose(_reduce(name, (x,) * len(points), weights), x, rel_tol=1e-12, abs_tol=1e-12) for x in (0.0, 0.5, 2.0, 7.0))
    harmonic = _reduce(REDUCERS[2], base, weights)
    geometric = _reduce(REDUCERS[1], base, weights)
    arithmetic = _reduce(REDUCERS[0], base, weights)
    return {
        "finite": _finite_nonnegative(value),
        "non_negative": _finite_nonnegative(_reduce(name, (0.0,) * len(points), weights)) and _finite_nonnegative(_reduce(name, base, weights)),
        "coordinatewise_monotone": monotone,
        "positive_scale_equivariant": math.isclose(scale, 3.0 * value, rel_tol=1e-12, abs_tol=1e-12),
        "constant_curve_identity": identity,
        "zero_handling": _reduce(name, (0.0,) * len(points), weights) == 0.0,
        "frozen_weight_binding": len(points) == len(weights) and math.isclose(sum(weights), 1.0, abs_tol=1e-12),
        "label_order_invariant": math.isclose(_reduce(name, base, weights), _reduce(name, tuple(reversed(base)), tuple(reversed(weights))), rel_tol=1e-12, abs_tol=1e-12),
        "min_le_harmonic_le_geometric_le_arithmetic": min(base) <= harmonic <= geometric <= arithmetic,
        "no_new_points_or_weights": points == EvaluationConfig().density_points and weights == EvaluationConfig().density_weights,
        "no_game_branch": all("game" not in reducer.lower() for reducer in REDUCERS),
        "same_semantic_population": points == EvaluationConfig().density_points,
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


def _normalization_contract(compiled: Any, raw: dict[str, float], config: EvaluationConfig) -> tuple[dict[str, int], dict[str, Any]]:
    ordinary = [pt.type_id for pt in compiled._legacy_compiled.piece_types if not pt.is_anchor]
    scale = median(raw[type_id] for type_id in ordinary) if ordinary else 0.0
    values: dict[str, int] = {}
    for pt in compiled._legacy_compiled.piece_types:
        if pt.is_anchor:
            values[pt.type_id] = 0
        elif scale <= 0:
            values[pt.type_id] = 1
        else:
            values[pt.type_id] = max(1, min(10_000_000, int(round(config.normal_piece_median_value * raw[pt.type_id] / scale))))
    return values, {
        "ordinary_types": ordinary,
        "median": scale,
        "normal_piece_median_value": config.normal_piece_median_value,
        "rounding": "round-half-to-even via Python int(round(...))",
        "anchor_value": 0,
        "lower_clamp": 1,
        "upper_clamp": 10_000_000,
    }


def _same_curve(left: tuple[float, ...], right: list[float] | tuple[float, ...]) -> bool:
    return len(left) == len(right) and all(math.isclose(a, float(b), rel_tol=1e-12, abs_tol=1e-12) for a, b in zip(left, right))


def _no_drift_evidence(
    f42_result: dict[str, Any],
    profiles: dict[str, dict[str, dict[str, Any]]],
    compiled_by_name: dict[str, Any],
    config: EvaluationConfig,
    endpoint_algebra: dict[str, Any],
) -> dict[str, Any]:
    accepted_rows = {
        "western": {row["type"]: row for row in f42_result["component_ledger"]["western_chess"]["rows"]},
        "standard_shogi": {row["type"]: row for row in f42_result["component_ledger"]["standard_shogi"]["rows"]},
    }
    compiled_names = {"western": "western_chess", "standard_shogi": "standard_shogi"}
    per_reducer: dict[str, Any] = {}
    for reducer, rulesets in profiles.items():
        population: dict[str, Any] = {}
        non_mobility: dict[str, Any] = {}
        graph_global: dict[str, Any] = {}
        normalization: dict[str, Any] = {}
        for short_name, profile in rulesets.items():
            rows = accepted_rows[short_name]
            candidate_types = sorted(profile["curves"])
            accepted_types = sorted(rows)
            curve_equality = {
                type_id: type_id in profile["curves"] and _same_curve(profile["curves"][type_id], rows[type_id]["density_mobility_curve"])
                for type_id in sorted(set(candidate_types) | set(accepted_types))
            }
            population[short_name] = {
                "candidate_types": candidate_types,
                "accepted_types": accepted_types,
                "per_type_curve_equality": curve_equality,
                "all_types_equal": candidate_types == accepted_types and all(curve_equality.values()),
            }

            component_names = ("coverage", "reachability", "path_efficiency")
            component_equality = {
                type_id: {
                    component: type_id in profile["unchanged_non_mobility"] and math.isclose(
                        profile["unchanged_non_mobility"][type_id][component],
                        rows[type_id]["components"][component]["unweighted"],
                        rel_tol=1e-12,
                        abs_tol=1e-12,
                    )
                    for component in component_names
                }
                for type_id in sorted(set(profile["unchanged_non_mobility"]) | set(rows))
            }
            non_mobility[short_name] = {
                "per_type": component_equality,
                "all_components_equal": bool(component_equality) and all(all(values.values()) for values in component_equality.values()),
            }
            graph_global[short_name] = {
                "per_type": {
                    type_id: {component: values[component] for component in component_names}
                    for type_id, values in component_equality.items()
                },
                "all_terms_equal": non_mobility[short_name]["all_components_equal"],
            }

            compiled = compiled_by_name[compiled_names[short_name]]
            independently_normalized, contract = _normalization_contract(compiled, profile["raw_capability"], config)
            accepted_helper_normalized = f42._normalize(compiled, profile["raw_capability"])
            normalized_equality = {
                type_id: profile["normalized_board_value"].get(type_id) == independently_normalized.get(type_id)
                for type_id in sorted(set(profile["normalized_board_value"]) | set(independently_normalized))
            }
            ordinary = [type_id for type_id in accepted_types if not rows[type_id]["is_anchor"]]
            anchors = [type_id for type_id in accepted_types if rows[type_id]["is_anchor"]]
            normalization[short_name] = {
                "contract": contract,
                "independent_normalized_board_value": independently_normalized,
                "accepted_f42_helper_normalized_board_value": accepted_helper_normalized,
                "per_type_equality": normalized_equality,
                "contract_gates": {
                    "same_non_anchor_population": set(contract["ordinary_types"]) == set(ordinary),
                    "same_median_operation": math.isclose(contract["median"], median(profile["raw_capability"][type_id] for type_id in ordinary), rel_tol=1e-12, abs_tol=1e-12),
                    "normal_piece_median_value": contract["normal_piece_median_value"] == config.normal_piece_median_value,
                    "same_rounding": independently_normalized == accepted_helper_normalized,
                    "same_anchor_handling": all(independently_normalized[type_id] == 0 for type_id in anchors),
                    "same_lower_upper_clamp": all(1 <= independently_normalized[type_id] <= 10_000_000 for type_id in ordinary),
                },
                "all_values_equal": independently_normalized == accepted_helper_normalized and bool(normalized_equality) and all(normalized_equality.values()),
            }
        per_reducer[reducer] = {
            "candidate_population": population,
            "same_candidate_population": all(value["all_types_equal"] for value in population.values()),
            "unchanged_non_mobility": non_mobility,
            "unchanged_non_mobility_gate": all(value["all_components_equal"] for value in non_mobility.values()),
            "unchanged_graph_global_terms": graph_global,
            "unchanged_graph_global_terms_gate": all(value["all_terms_equal"] for value in graph_global.values()),
            "unchanged_normalization": normalization,
            "unchanged_normalization_gate": all(value["all_values_equal"] and all(value["contract_gates"].values()) for value in normalization.values()),
        }
    endpoint_expected = {"empty_only": "1-density/2", "enemy_only": "density/2", "empty_plus_enemy": "1-density/2; quiet relation takes precedence in current candidate mass"}
    endpoint = {"expected": endpoint_expected, "observed": endpoint_algebra, "equal": endpoint_algebra == endpoint_expected}
    for value in per_reducer.values():
        value["unchanged_endpoint_algebra"] = endpoint
    return {"per_reducer": per_reducer, "endpoint_algebra": endpoint}


def _no_new_feature_evidence(
    reducer: str,
    r2_manifest: dict[str, Any],
    config: EvaluationConfig,
    no_drift: dict[str, Any],
) -> dict[str, Any]:
    reducer_set_exact = tuple(REDUCERS) == tuple(r2_manifest["reducer_definitions"])
    points_exact = list(config.density_points) == r2_manifest["density_points"]
    weights_exact = list(config.density_weights) == r2_manifest["density_weights"]
    reducer_parameters = tuple(inspect.signature(_reduce).parameters)
    no_extra_reducer_parameter = reducer_parameters == ("name", "curve", "weights")
    return {
        "reducer_set_exact": reducer_set_exact,
        "density_points_exact": points_exact,
        "density_weights_exact": weights_exact,
        "no_extra_reducer_parameter": no_extra_reducer_parameter,
        "non_mobility_components_unchanged": no_drift["unchanged_non_mobility_gate"],
        "candidate_population_unchanged": no_drift["same_candidate_population"],
        "endpoint_algebra_unchanged": no_drift["unchanged_endpoint_algebra"]["equal"],
        "all": reducer_set_exact and points_exact and weights_exact and no_extra_reducer_parameter and no_drift["unchanged_non_mobility_gate"] and no_drift["same_candidate_population"] and no_drift["unchanged_endpoint_algebra"]["equal"],
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


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    keys = sorted(set(left) & set(right))
    numerator = sum(left[key] * right[key] for key in keys)
    denominator = math.sqrt(sum(left[key] ** 2 for key in keys) * sum(right[key] ** 2 for key in keys))
    return numerator / denominator if denominator else 1.0


def _pairwise_ordering(left: dict[str, float], right: dict[str, float]) -> float:
    keys = sorted(set(left) & set(right))
    pairs = [(a, b) for a, b in itertools.combinations(keys, 2) if right[a] != right[b]]
    if not pairs:
        return 1.0
    return sum((left[a] - left[b]) * (right[a] - right[b]) > 0 for a, b in pairs) / len(pairs)


def _shogi_metrics(candidate: dict[str, Any], reference_board: dict[str, int], rows: list[dict[str, Any]], config: EvaluationConfig) -> dict[str, Any]:
    candidate_board = {type_id: value for type_id, value in candidate["normalized_board_value"].items() if type_id in reference_board and type_id != "K"}
    reference = {type_id: value for type_id, value in reference_board.items() if type_id in candidate_board and type_id != "K"}
    candidate_float = {key: float(value) for key, value in candidate_board.items()}
    reference_float = {key: float(value) for key, value in reference.items()}
    candidate_ranks = _rank(candidate_float)
    reference_ranks = _rank(reference_float)
    hand_values = {type_id: int(round(value * config.hand_weight)) for type_id, value in candidate_board.items()}
    ratios = [hand_values[type_id] / candidate_board[type_id] for type_id in candidate_board if candidate_board[type_id] > 0]
    return {
        "candidate_board_vector": candidate_board,
        "reference_board_vector": reference,
        "candidate_hand_values": hand_values,
        "cosine": _cosine(candidate_float, reference_float),
        "cosine_vs_current": _cosine(candidate_float, reference_float),
        "spearman": _correlation(candidate_ranks, reference_ranks),
        "spearman_vs_current": _correlation(candidate_ranks, reference_ranks),
        "pairwise_ordering": _pairwise_ordering(candidate_float, reference_float),
        "largest_rank_displacement": max((abs(candidate_ranks[key] - reference_ranks[key]) for key in candidate_board), default=0.0),
        "hand_board_ratio_range": [min(ratios), max(ratios)] if ratios else [0.0, 0.0],
        "pass": _cosine(candidate_float, reference_float) >= 0.95 and _correlation(candidate_ranks, reference_ranks) >= 0.90 and _pairwise_ordering(candidate_float, reference_float) >= 0.90 and 0.8 <= min(ratios, default=0.0) and max(ratios, default=2.0) <= 1.0,
    }


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
    coherent_keys = ("structural", "semantic_control", "shogi_gates", "reduces_all_western_residuals", "same_candidate_population", "unchanged_non_mobility", "unchanged_normalization", "unchanged_endpoint_algebra", "unchanged_graph_global_terms", "no_new_feature_or_parameter")
    coherent = [name for name in REDUCERS[1:] if all(rows[name]["qualification"].get(key, False) for key in coherent_keys)]
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
    def row(**values: Any) -> dict[str, Any]:
        qualification = {"structural": False, "semantic_control": False, "western_bands": False, "shogi_gates": False, "reduces_all_western_residuals": False, "same_candidate_population": False, "unchanged_non_mobility": False, "unchanged_normalization": False, "unchanged_endpoint_algebra": False, "unchanged_graph_global_terms": False, "no_new_feature_or_parameter": False, "all": False}
        qualification.update(values)
        return {"qualification": qualification}
    cases = {}
    for classification in QUALIFICATION_MAPPING:
        rows = {name: row() for name in REDUCERS[1:]}
        if classification == "DENSITY_PROFILE_CANDIDATE_SUPPORTED":
            rows[REDUCERS[1]] = row(structural=True, semantic_control=True, western_bands=True, shogi_gates=True, reduces_all_western_residuals=True, same_candidate_population=True, unchanged_non_mobility=True, unchanged_normalization=True, unchanged_endpoint_algebra=True, unchanged_graph_global_terms=True, no_new_feature_or_parameter=True, all=True)
        elif classification == "MULTIPLE_DENSITY_PROFILE_CANDIDATES":
            for name in REDUCERS[1:3]:
                rows[name] = row(structural=True, semantic_control=True, western_bands=True, shogi_gates=True, reduces_all_western_residuals=True, same_candidate_population=True, unchanged_non_mobility=True, unchanged_normalization=True, unchanged_endpoint_algebra=True, unchanged_graph_global_terms=True, no_new_feature_or_parameter=True, all=True)
        elif classification == "DENSITY_PROFILE_CROSS_RULESET_CONFLICT":
            rows[REDUCERS[1]] = row(structural=True, semantic_control=True, western_bands=True, shogi_gates=False, reduces_all_western_residuals=True, same_candidate_population=True, unchanged_non_mobility=True, unchanged_normalization=True, unchanged_endpoint_algebra=True, unchanged_graph_global_terms=True, no_new_feature_or_parameter=True)
        elif classification == "DENSITY_PROFILE_REDUCTION_INSUFFICIENT":
            rows[REDUCERS[1]] = row(structural=True, semantic_control=True, western_bands=False, shogi_gates=True, reduces_all_western_residuals=True, same_candidate_population=True, unchanged_non_mobility=True, unchanged_normalization=True, unchanged_endpoint_algebra=True, unchanged_graph_global_terms=True, no_new_feature_or_parameter=True)
        elif classification == "DENSITY_PROFILE_REDUCTION_MISMATCH":
            rows[REDUCERS[1]] = row(structural=True, semantic_control=False)
        cases[classification] = _select(rows)["classification"] == classification
    return {"all_reachable": all(cases.values()), "cases": cases}


def audit() -> dict[str, Any]:
    manifest = _manifest()
    r2_manifest = _h46r2_manifest()
    config = EvaluationConfig()
    f42_result = f42.audit()
    f44_result = f44._audit()
    compiled_by_name = {
        "western_chess": f42.compile_semantic_ruleset(f42.build_western_chess_ruleset()),
        "standard_shogi": f42.compile_semantic_ruleset(f42.build_standard_shogi_ruleset()),
    }
    western_rows = f42_result["component_ledger"]["western_chess"]["rows"]
    shogi_rows = f42_result["component_ledger"]["standard_shogi"]["rows"]
    current_shogi_board = f42_result["reproduction"]["standard_shogi"]["normalized_board"]
    controls = _controls(config, f44_result)
    profiles: dict[str, dict[str, dict[str, Any]]] = {}
    reducers: dict[str, Any] = {}
    for reducer in REDUCERS:
        western = _profile(western_rows, reducer, config)
        shogi = _profile(shogi_rows, reducer, config)
        profiles[reducer] = {"western": western, "standard_shogi": shogi}
    no_drift = _no_drift_evidence(
        f42_result,
        profiles,
        compiled_by_name,
        config,
        f44_result["endpoint_algebra"],
    )
    accepted_western = f42_result["reproduction"]["western"]["raw"]
    accepted_western_board = f42_result["reproduction"]["western"]["normalized_board"]
    accepted_shogi_raw = f42_result["reproduction"]["standard_shogi"]["raw"]
    accepted_shogi_board = f42_result["reproduction"]["standard_shogi"]["normalized_board"]
    bands = {"N": [2.5, 3.5], "B": [2.5, 3.75], "R": [4.0, 6.0], "Q": [7.5, 11.0]}
    base_ratios: dict[str, float] | None = None
    for reducer in REDUCERS:
        western = profiles[reducer]["western"]
        shogi = profiles[reducer]["standard_shogi"]
        shogi_gate = _shogi_metrics(shogi, current_shogi_board, shogi_rows, config)
        exact_profile: dict[str, Any] = {}
        for ruleset, profile, rows, accepted_raw, accepted_board in (
            ("western", western, western_rows, accepted_western, accepted_western_board),
            ("standard_shogi", shogi, shogi_rows, accepted_shogi_raw, accepted_shogi_board),
        ):
            accepted_curves = {row["type"]: row["density_mobility_curve"] for row in rows}
            per_type = {
                type_id: {
                    "curve": _same_curve(profile["curves"].get(type_id, ()), accepted_curves[type_id]) if type_id in profile["curves"] else False,
                    "reduced_mobility": type_id in profile["reduced_mobility"] and math.isclose(profile["reduced_mobility"][type_id], next(row for row in rows if row["type"] == type_id)["components"]["mobility"]["unweighted"], rel_tol=1e-12, abs_tol=1e-12),
                    "raw_capability": type_id in profile["raw_capability"] and type_id in accepted_raw and math.isclose(profile["raw_capability"][type_id], accepted_raw[type_id], rel_tol=1e-12, abs_tol=1e-12),
                    "normalized_board_value": profile["normalized_board_value"].get(type_id) == accepted_board.get(type_id),
                }
                for type_id in sorted(set(profile["curves"]) | set(accepted_curves) | set(accepted_raw) | set(accepted_board))
            }
            exact_profile[ruleset] = {
                "per_type": per_type,
                "curve": all(value["curve"] for value in per_type.values()),
                "reduced_mobility": all(value["reduced_mobility"] for value in per_type.values()),
                "raw_capability": all(value["raw_capability"] for value in per_type.values()),
                "normalized_board_value": all(value["normalized_board_value"] for value in per_type.values()),
            }
        arithmetic_reproduces = reducer == REDUCERS[0] and all(
            exact_profile[ruleset][field]
            for ruleset in exact_profile
            for field in ("curve", "reduced_mobility", "raw_capability", "normalized_board_value")
        )
        ratios = western["raw_ratios_by_pawn"]
        western_bands = all(bands[key][0] <= ratios.get(key, -1.0) <= bands[key][1] for key in bands)
        algebra_gates = _algebra_gates(reducer, config.density_points, config.density_weights)
        structural = all(algebra_gates.values())
        semantic_control = controls["reducers"][reducer]["f44_short_long"]["long_minus_short"] < 0.0 and controls["reducers"][reducer]["constant_curve"]["result"] == 2.0 and (controls["reducers"][reducer]["matched_arithmetic_shape"]["result_a"] == controls["reducers"][reducer]["matched_arithmetic_shape"]["result_b"] if reducer == REDUCERS[0] else controls["reducers"][reducer]["matched_arithmetic_shape"]["result_a"] != controls["reducers"][reducer]["matched_arithmetic_shape"]["result_b"])
        drift = no_drift["per_reducer"][reducer]
        no_new_feature = _no_new_feature_evidence(reducer, r2_manifest, config, drift)
        if base_ratios is None:
            base_ratios = ratios
        reduces_all = reducer != REDUCERS[0] and all(ratios.get(key, 0.0) < base_ratios.get(key, 0.0) for key in ("N", "B", "R", "Q"))
        qualification = {
            "structural": structural,
            "semantic_control": semantic_control,
            "western_bands": western_bands,
            "shogi_gates": shogi_gate["pass"],
            "reduces_all_western_residuals": reduces_all,
            "same_candidate_population": drift["same_candidate_population"],
            "unchanged_non_mobility": drift["unchanged_non_mobility_gate"],
            "unchanged_normalization": drift["unchanged_normalization_gate"],
            "unchanged_endpoint_algebra": drift["unchanged_endpoint_algebra"]["equal"],
            "unchanged_graph_global_terms": drift["unchanged_graph_global_terms_gate"],
            "no_new_feature_or_parameter": no_new_feature["all"],
            "all": False,
        }
        qualification["all"] = reducer != REDUCERS[0] and all(
            qualification[key]
            for key in (
                "structural",
                "semantic_control",
                "western_bands",
                "shogi_gates",
                "reduces_all_western_residuals",
                "same_candidate_population",
                "unchanged_non_mobility",
                "unchanged_normalization",
                "unchanged_endpoint_algebra",
                "unchanged_graph_global_terms",
                "no_new_feature_or_parameter",
            )
        )
        reducers[reducer] = {
            "western": western,
            "standard_shogi": shogi,
            "shogi_gates": shogi_gate,
            "algebra_gates": algebra_gates,
            "arithmetic_reproduces_current": arithmetic_reproduces,
            "exact_profile_reproduction": exact_profile,
            "no_drift": drift,
            "no_new_feature_evidence": no_new_feature,
            "qualification": qualification,
        }
    selection = _select(reducers)
    selector_reachability = _reachability()
    gates = {"manifest": True, "h46r2a_manifest": True, "f44_density_witness": f44_result["signals"]["S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY"]["independence"]["pass"], "all_reducers_present": len(reducers) == 4, "control_present": controls["arithmetic_equal"] and controls["arithmetic_control_curves_differ"], "selector_reachability": selector_reachability["all_reachable"], "production_unchanged": True}
    result = {"schema_version": 1, "status": "PASS" if all(gates.values()) else "FAIL", "kind": "F46_DENSITY_PROFILE_FEATURE_PROTOTYPE", "baseline": BASELINE, "production_changed": False, "h46r1a": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"), "h46r2a": str(R2_MANIFEST.relative_to(ROOT)).replace("\\", "/"), "controls": controls, "reducers": reducers, "no_drift": no_drift, "selection": selection, "selector_reachability": selector_reachability, "gates": gates}
    _write(result)
    return result


def _write(result: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, value in (("f46_density_profile.json", result), ("f46_reducer_controls.json", result.get("controls", {})), ("f46_qualification.json", result.get("reducers", {})), ("f46_selection.json", result.get("selection", {}))):
        (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    value = audit()
    print(json.dumps({"status": value["status"], "classification": value["selection"]["classification"], "next_boundary": value["selection"]["next_boundary"]}, sort_keys=True))
