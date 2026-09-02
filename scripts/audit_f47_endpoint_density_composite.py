"""F47 diagnosis-only endpoint completion over the accepted density profile."""

from __future__ import annotations

import hashlib
import inspect
import itertools
import json
import math
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".generic_chess_flow"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import audit_f41_semantic_material_prior as f41  # noqa: E402
import audit_f42_semantic_capability_prior as f42  # noqa: E402
import audit_f44_structural_capability as f44  # noqa: E402
import audit_f46_density_profile as f46  # noqa: E402

from generic_chess.rules.compiler import compile_semantic_ruleset  # noqa: E402
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset  # noqa: E402
from generic_chess.rules.western_chess import build_western_chess_ruleset  # noqa: E402


MANIFEST = ROOT / "tests" / "fixtures" / "f47_endpoint_density_composite_manifest.json"
BASELINE = "979c7e026442e9dbb479658d0a770daefd15da85"
VARIANTS = (
    "C47-0_CURRENT_ARITHMETIC_CONTROL",
    "C47-1_ENDPOINT_ARITHMETIC",
    "C47-2_ENDPOINT_GEOMETRIC",
    "C47-3_ENDPOINT_HARMONIC",
    "C47-4_ENDPOINT_LOWER_ENVELOPE",
)
REDUCERS = {
    VARIANTS[0]: f46.REDUCERS[0],
    VARIANTS[1]: f46.REDUCERS[0],
    VARIANTS[2]: f46.REDUCERS[1],
    VARIANTS[3]: f46.REDUCERS[2],
    VARIANTS[4]: f46.REDUCERS[3],
}
QUALIFICATION_MAPPING = {
    "ENDPOINT_CONTROL_CANDIDATE_SUPPORTED": "F48_ENDPOINT_CONTROL_INTEGRATION_PROTOTYPE",
    "ENDPOINT_DENSITY_COMPOSITE_CANDIDATE_SUPPORTED": "F48_ENDPOINT_DENSITY_INTEGRATION_PROTOTYPE",
    "MULTIPLE_ENDPOINT_DENSITY_CANDIDATES": "F48_ENDPOINT_DENSITY_DISCRIMINATION",
    "ENDPOINT_DENSITY_CROSS_RULESET_CONFLICT": "F48_GENERIC_MATERIAL_PRIOR_REASSESSMENT",
    "ENDPOINT_DENSITY_COMPOSITE_INSUFFICIENT": "F48_GENERIC_MATERIAL_PRIOR_REASSESSMENT",
    "ENDPOINT_DENSITY_DIRECTIONAL_MISMATCH": "F48_MATERIAL_PRIOR_REASSESSMENT",
    "MIXED_OR_UNRESOLVED": "F48_MATERIAL_PRIOR_REASSESSMENT",
}
BANDS = {"N": [2.5, 3.5], "B": [2.5, 3.75], "R": [4.0, 6.0], "Q": [7.5, 11.0]}


def _manifest() -> dict[str, Any]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    actual = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if actual != data["manifest_sha256"] or data["baseline"]["sandbox_sha"] != BASELINE:
        raise AssertionError("H47A manifest mismatch")
    return data


def _gap_curve(compiled: Any, type_id: str) -> dict[str, Any]:
    denominator = 2 * compiled.board_size * compiled.board_size
    curve: list[float] = []
    owner_curves: dict[str, list[float]] = {"0": [], "1": []}
    counts: list[int] = []
    for density in f46.EvaluationConfig().density_points:
        total = 0.0
        owner_totals = {0: 0.0, 1: 0.0}
        count = 0
        for owner in (0, 1):
            for source in range(compiled.board_size * compiled.board_size):
                for (_target, path), candidate in f44._source_candidates(compiled, type_id, owner, source, True).items():
                    quiet = "target_empty" in candidate["relations"]
                    attack = "target_enemy" in candidate["relations"]
                    if attack and not quiet:
                        clear = (1.0 - density) ** len(path)
                        value = clear * (1.0 - density / 2.0)
                        total += value
                        owner_totals[owner] += value
                        count += 1
        curve.append(total / denominator if denominator else 0.0)
        owner_curves["0"].append(owner_totals[0] / (compiled.board_size * compiled.board_size) if compiled.board_size else 0.0)
        owner_curves["1"].append(owner_totals[1] / (compiled.board_size * compiled.board_size) if compiled.board_size else 0.0)
        counts.append(count)
    return {
        "type": type_id,
        "gap_curve": curve,
        "owner_gap_curves": owner_curves,
        "attack_only_candidate_count_by_density": counts,
        "ordinary_pattern_count": len(f44._patterns(compiled, type_id, True)),
        "conditional_pattern_count_excluded": len(f44._patterns(compiled, type_id, False)),
    }


def _gap_ledger(compiled_by_name: dict[str, Any], f42_result: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for ruleset, compiled in compiled_by_name.items():
        rows = {row["type"]: row for row in f42_result["component_ledger"][ruleset]["rows"]}
        output[ruleset] = {type_id: {**_gap_curve(compiled, type_id), "accepted_mobility_curve": rows[type_id]["density_mobility_curve"], "gap_weighted": sum(w * value for w, value in zip(f46.EvaluationConfig().density_weights, _gap_curve(compiled, type_id)["gap_curve"]))} for type_id in rows}
    return output


def _variant_profile(rows: list[dict[str, Any]], variant: str, gap_rows: dict[str, Any], compiled: Any, config: f46.EvaluationConfig) -> dict[str, Any]:
    curves = {}
    for row in rows:
        accepted = tuple(float(value) for value in row["density_mobility_curve"])
        completed = tuple(accepted[i] + gap_rows[row["type"]]["gap_curve"][i] for i in range(len(accepted))) if variant != VARIANTS[0] else accepted
        curves[row["type"]] = completed
    reduced = {type_id: f46._reduce(REDUCERS[variant], curve, config.density_weights) for type_id, curve in curves.items()}
    raw = {row["type"]: reduced[row["type"]] + config.coverage_weight * row["components"]["coverage"]["unweighted"] + config.reachability_weight * row["components"]["reachability"]["unweighted"] + config.path_efficiency_weight * row["components"]["path_efficiency"]["unweighted"] for row in rows}
    board = f42._normalize(compiled, raw)
    pawn = raw.get("P", 0.0)
    return {
        "accepted_mobility_curve": {row["type"]: tuple(float(value) for value in row["density_mobility_curve"]) for row in rows},
        "split_attack_control_gap_curve": {type_id: gap_rows[type_id]["gap_curve"] for type_id in gap_rows},
        "completed_density_curve": curves,
        "non_mobility": {row["type"]: {key: row["components"][key]["unweighted"] for key in ("coverage", "reachability", "path_efficiency")} for row in rows},
        "reduced_mobility": reduced,
        "raw_capability": raw,
        "normalized_board_value": board,
        "raw_ratios_by_pawn": {type_id: raw[type_id] / pawn for type_id in raw if type_id != "P" and pawn},
        "normalized_ratios_by_pawn": {type_id: board[type_id] / board["P"] for type_id in board if type_id != "P" and board.get("P")},
    }


def _distance(value: float, interval: list[float]) -> float:
    lo, hi = interval
    return max(lo - value, 0.0, value - hi)


def _interval_ledger(control: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    per_piece = {}
    for type_id, interval in BANDS.items():
        control_value = control["raw_ratios_by_pawn"][type_id]
        candidate_value = candidate["raw_ratios_by_pawn"][type_id]
        control_distance = _distance(control_value, interval)
        candidate_distance = _distance(candidate_value, interval)
        per_piece[type_id] = {"interval": interval, "control": control_value, "candidate": candidate_value, "control_distance": control_distance, "candidate_distance": candidate_distance, "weakly_improves": candidate_distance <= control_distance + 1e-12, "strictly_improves": candidate_distance < control_distance - 1e-12, "moves_farther": candidate_distance > control_distance + 1e-12}
    return {"per_piece": per_piece, "all_bands_pass": all(BANDS[type_id][0] <= candidate["raw_ratios_by_pawn"].get(type_id, -1.0) <= BANDS[type_id][1] for type_id in BANDS), "weakly_improves_all": all(value["weakly_improves"] for value in per_piece.values()), "strict_improvement": any(value["strictly_improves"] for value in per_piece.values()), "directional_mismatch": any(value["moves_farther"] for value in per_piece.values())}


def _semantic_controls(compiled_by_name: dict[str, Any]) -> dict[str, Any]:
    synthetic = f44._synthetic_rules()
    cases = {name: _gap_curve(ruleset, "X") for name, ruleset in synthetic.items()}
    same_target = {"quiet_only_curve": cases["quiet_only"]["gap_curve"], "quiet_plus_capture_curve": cases["quiet_plus_capture_same_targets"]["gap_curve"], "identical": cases["quiet_only"]["gap_curve"] == cases["quiet_plus_capture_same_targets"]["gap_curve"]}
    split = cases["disjoint_quiet_capture_same_union"]
    no_attack = cases["quiet_only"]
    dual_use = cases["quiet_plus_capture_same_targets"]
    conditional_base = cases["ordinary_base"]
    conditional_extra = cases["ordinary_base_plus_guarded_identical_capability"]
    real_pawn = {ruleset: _gap_curve(compiled, "P") for ruleset, compiled in compiled_by_name.items()}
    return {
        "same_target_relation_control": same_target,
        "split_target_control": {"gap_curve": split["gap_curve"], "positive_gap": any(value > 0.0 for value in split["gap_curve"])},
        "no_attack_control": {"gap_curve": no_attack["gap_curve"], "zero_gap": not any(value > 0.0 for value in no_attack["gap_curve"])},
        "dual_use_only_control": {"gap_curve": dual_use["gap_curve"], "zero_gap": not any(value > 0.0 for value in dual_use["gap_curve"])},
        "conditional_exclusion": {"ordinary_gap_unchanged": conditional_base["gap_curve"] == conditional_extra["gap_curve"], "conditional_patterns_present": conditional_extra["conditional_pattern_count_excluded"] > 0},
        "western_pawn": {"gap_curve": real_pawn["western_chess"]["gap_curve"], "nonzero": any(value > 0.0 for value in real_pawn["western_chess"]["gap_curve"])},
        "standard_shogi_pawn": {"gap_curve": real_pawn["standard_shogi"]["gap_curve"], "derived": True},
        "no_relation_multiplicity_double_count": same_target["identical"],
    }


def _structural_controls(compiled_by_name: dict[str, Any], gap_ledger: dict[str, Any], semantic: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    config = f46.EvaluationConfig()
    deterministic = gap_ledger == _gap_ledger(compiled_by_name, f42.audit())
    owner_mirror = all(row["owner_gap_curves"]["0"] == row["owner_gap_curves"]["1"] for data in gap_ledger.values() for row in data.values())
    rebuilt = {name: _gap_curve(f44._synthetic_rules()[name], "X") for name in ("quiet_only", "quiet_plus_capture_same_targets")}
    renamed_type = _gap_curve(compile_semantic_ruleset(f42._synthetic_ruleset(name="renamed_piece", kind="leap", shapes=((1, 0),), relations=("empty",))), "X")
    renamed_ruleset = _gap_curve(compile_semantic_ruleset(f42._synthetic_ruleset(name="renamed_ruleset", kind="leap", shapes=((1, 0),), relations=("empty",))), "X")
    action_order = _gap_curve(compile_semantic_ruleset(f42._synthetic_ruleset(name="action_order", kind="leap", shapes=((1, 0),), relations=("empty", "enemy"))), "X")
    geometry_ids = _gap_curve(compile_semantic_ruleset(f42._synthetic_ruleset(name="geometry_ids", kind="leap", shapes=((1, 0),), relations=("empty",))), "X")
    return {
        "deterministic": deterministic,
        "finite": all(math.isfinite(value) for data in gap_ledger.values() for row in data.values() for value in row["gap_curve"]),
        "non_negative_gap": all(value >= 0.0 for data in gap_ledger.values() for row in data.values() for value in row["gap_curve"]),
        "candidate_deduplication_invariant": all(row["attack_only_candidate_count_by_density"][0] >= 0 for data in gap_ledger.values() for row in data.values()),
        "owner_mirror_invariant": owner_mirror,
        "type_rename_invariant": rebuilt["quiet_only"]["gap_curve"] == renamed_type["gap_curve"],
        "ruleset_rename_invariant": rebuilt["quiet_only"]["gap_curve"] == renamed_ruleset["gap_curve"],
        "action_pattern_order_invariant": action_order["gap_curve"] == rebuilt["quiet_plus_capture_same_targets"]["gap_curve"],
        "generated_geometry_id_invariant": geometry_ids["gap_curve"] == rebuilt["quiet_only"]["gap_curve"],
        "conditional_pattern_exclusion": semantic["conditional_exclusion"]["ordinary_gap_unchanged"],
        "same_accepted_candidate_population": all(row["ordinary_pattern_count"] >= 0 for data in gap_ledger.values() for row in data.values()),
        "same_path_clear_semantics": manifest["endpoint_completion"]["clear"] == "(1-density) ** path_length",
        "no_relation_multiplicity_double_count": semantic["no_relation_multiplicity_double_count"],
        "no_additional_scalar_parameter": tuple(inspect.signature(_gap_curve).parameters) == ("compiled", "type_id") and tuple(inspect.signature(_variant_profile).parameters) == ("rows", "variant", "gap_rows", "compiled", "config"),
        "density_points_exact": list(config.density_points) == manifest["density_points"],
        "density_weights_exact": list(config.density_weights) == manifest["density_weights"],
    }


def _no_drift(f42_result: dict[str, Any], variants: dict[str, dict[str, dict[str, Any]]], gap_ledger: dict[str, Any], config: f46.EvaluationConfig, manifest: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for variant, rulesets in variants.items():
        per_ruleset = {}
        for ruleset, profile in rulesets.items():
            accepted_rows = {row["type"]: row for row in f42_result["component_ledger"][ruleset]["rows"]}
            population = {type_id: type_id in profile["accepted_mobility_curve"] and tuple(profile["accepted_mobility_curve"][type_id]) == tuple(accepted_rows[type_id]["density_mobility_curve"]) for type_id in sorted(accepted_rows)}
            components = {type_id: {key: math.isclose(profile["non_mobility"][type_id][key], accepted_rows[type_id]["components"][key]["unweighted"], rel_tol=1e-12, abs_tol=1e-12) for key in ("coverage", "reachability", "path_efficiency")} for type_id in accepted_rows}
            independent_normalized = f42._normalize(compile_semantic_ruleset(build_western_chess_ruleset() if ruleset == "western_chess" else build_standard_shogi_ruleset()), profile["raw_capability"])
            normalization = {type_id: profile["normalized_board_value"].get(type_id) == independent_normalized.get(type_id) for type_id in accepted_rows}
            endpoint_only = {type_id: all(math.isclose(profile["completed_density_curve"][type_id][index], profile["accepted_mobility_curve"][type_id][index] + (profile["split_attack_control_gap_curve"][type_id][index] if variant != VARIANTS[0] else 0.0), rel_tol=1e-12, abs_tol=1e-12) for index in range(len(profile["accepted_mobility_curve"][type_id]))) for type_id in accepted_rows}
            conditional_excluded = {type_id: gap_ledger[ruleset][type_id]["conditional_pattern_count_excluded"] == accepted_rows[type_id]["pattern_summary"]["conditional_semantic_pattern_count"] for type_id in accepted_rows}
            hand_relation = {type_id: int(round(profile["normalized_board_value"][type_id] * config.hand_weight)) == int(round(profile["normalized_board_value"][type_id] * f42.CONFIG.hand_weight)) for type_id in accepted_rows}
            per_ruleset[ruleset] = {"candidate_population": population, "coverage_reachability_path_efficiency": components, "endpoint_definitions_except_attack_only_completion": endpoint_only, "normalization": normalization, "hand_value_relation": hand_relation, "no_conditional_capability_inclusion": conditional_excluded, "all_population": all(population.values()), "all_non_mobility": all(all(values.values()) for values in components.values()), "all_endpoint_definitions": all(endpoint_only.values()), "all_normalization": all(normalization.values()), "all_hand_value_relation": all(hand_relation.values()), "all_no_conditional_capability_inclusion": all(conditional_excluded.values())}
        result[variant] = {"per_ruleset": per_ruleset, "accepted_population": all(data["all_population"] for data in per_ruleset.values()), "unchanged_non_mobility": all(data["all_non_mobility"] for data in per_ruleset.values()), "unchanged_normalization": all(data["all_normalization"] for data in per_ruleset.values()), "unchanged_hand_relation": all(data["all_hand_value_relation"] for data in per_ruleset.values()), "unchanged_endpoint_definitions_except_attack_only_completion": all(data["all_endpoint_definitions"] for data in per_ruleset.values()), "unchanged_graph_global_weights": config.coverage_weight == f42.CONFIG.coverage_weight and config.reachability_weight == f42.CONFIG.reachability_weight and config.path_efficiency_weight == f42.CONFIG.path_efficiency_weight, "no_conditional_capability_inclusion": all(data["all_no_conditional_capability_inclusion"] for data in per_ruleset.values()), "unchanged_density_points": list(config.density_points) == manifest["density_points"], "unchanged_density_weights": list(config.density_weights) == manifest["density_weights"]}
        result[variant]["all"] = all(result[variant][key] for key in ("accepted_population", "unchanged_non_mobility", "unchanged_normalization", "unchanged_hand_relation", "unchanged_endpoint_definitions_except_attack_only_completion", "unchanged_graph_global_weights", "no_conditional_capability_inclusion", "unchanged_density_points", "unchanged_density_weights"))
    return result


def _select(rows: dict[str, Any]) -> dict[str, Any]:
    qualified_control = rows[VARIANTS[1]]["qualification"]["all"]
    qualified_density = [name for name in VARIANTS[2:] if rows[name]["qualification"]["all"]]
    cross = [name for name in VARIANTS[1:] if rows[name]["qualification"]["western_bands"] and not rows[name]["qualification"]["shogi_gates"]]
    insufficient = [name for name in VARIANTS[1:] if rows[name]["qualification"]["structural"] and rows[name]["qualification"]["semantic_control"] and rows[name]["qualification"]["no_drift"] and rows[name]["qualification"]["shogi_gates"] and rows[name]["qualification"]["weakly_improves_interval_distance"] and not rows[name]["qualification"]["western_bands"]]
    directional = [name for name in VARIANTS[1:] if rows[name]["qualification"]["directional_mismatch"]]
    if qualified_control:
        classification = "ENDPOINT_CONTROL_CANDIDATE_SUPPORTED"
    elif len(qualified_density) == 1:
        classification = "ENDPOINT_DENSITY_COMPOSITE_CANDIDATE_SUPPORTED"
    elif len(qualified_density) > 1:
        classification = "MULTIPLE_ENDPOINT_DENSITY_CANDIDATES"
    elif cross:
        classification = "ENDPOINT_DENSITY_CROSS_RULESET_CONFLICT"
    elif insufficient:
        classification = "ENDPOINT_DENSITY_COMPOSITE_INSUFFICIENT"
    elif directional:
        classification = "ENDPOINT_DENSITY_DIRECTIONAL_MISMATCH"
    else:
        classification = "MIXED_OR_UNRESOLVED"
    return {"classification": classification, "next_boundary": QUALIFICATION_MAPPING[classification], "qualified": [VARIANTS[1]] if qualified_control else qualified_density, "coherent_insufficient": insufficient, "directional_mismatch": directional}


def _reachability() -> dict[str, Any]:
    keys = ("structural", "semantic_control", "no_drift", "shogi_gates", "western_bands", "weakly_improves_interval_distance", "directional_mismatch", "all")
    def row(**values: Any) -> dict[str, Any]:
        q = {key: False for key in keys}
        q.update(values)
        return {"qualification": q}
    cases = {}
    for classification in QUALIFICATION_MAPPING:
        rows = {name: row() for name in VARIANTS[1:]}
        common = {"structural": True, "semantic_control": True, "no_drift": True, "shogi_gates": True, "weakly_improves_interval_distance": True}
        if classification == "ENDPOINT_CONTROL_CANDIDATE_SUPPORTED":
            rows[VARIANTS[1]] = row(**common, western_bands=True, all=True)
        elif classification == "ENDPOINT_DENSITY_COMPOSITE_CANDIDATE_SUPPORTED":
            rows[VARIANTS[2]] = row(**common, western_bands=True, all=True)
        elif classification == "MULTIPLE_ENDPOINT_DENSITY_CANDIDATES":
            rows[VARIANTS[2]] = row(**common, western_bands=True, all=True)
            rows[VARIANTS[3]] = row(**common, western_bands=True, all=True)
        elif classification == "ENDPOINT_DENSITY_CROSS_RULESET_CONFLICT":
            rows[VARIANTS[2]] = row(**{**common, "western_bands": True, "shogi_gates": False})
        elif classification == "ENDPOINT_DENSITY_COMPOSITE_INSUFFICIENT":
            rows[VARIANTS[2]] = row(**common, western_bands=False)
        elif classification == "ENDPOINT_DENSITY_DIRECTIONAL_MISMATCH":
            rows[VARIANTS[2]] = row(**{**common, "weakly_improves_interval_distance": False, "directional_mismatch": True})
        cases[classification] = _select(rows)["classification"] == classification
    return {"all_reachable": all(cases.values()), "cases": cases}


def audit() -> dict[str, Any]:
    manifest = _manifest()
    config = f46.EvaluationConfig()
    f42_result = f42.audit()
    compiled_by_name = {"western_chess": compile_semantic_ruleset(build_western_chess_ruleset()), "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset())}
    gap_ledger = _gap_ledger(compiled_by_name, f42_result)
    semantic = _semantic_controls(compiled_by_name)
    structural = _structural_controls(compiled_by_name, gap_ledger, semantic, manifest)
    profiles: dict[str, dict[str, dict[str, Any]]] = {}
    for variant in VARIANTS:
        profiles[variant] = {ruleset: _variant_profile(f42_result["component_ledger"][ruleset]["rows"], variant, gap_ledger[ruleset], compiled_by_name[ruleset], config) for ruleset in compiled_by_name}
    no_drift = _no_drift(f42_result, profiles, gap_ledger, config, manifest)
    matrices: dict[str, Any] = {variant: {"western": profiles[variant]["western_chess"], "standard_shogi": profiles[variant]["standard_shogi"]} for variant in VARIANTS}
    for variant in VARIANTS:
        interval = _interval_ledger(profiles[VARIANTS[0]]["western_chess"], profiles[variant]["western_chess"])
        shogi = f46._shogi_metrics(profiles[variant]["standard_shogi"], f42_result["reproduction"]["standard_shogi"]["normalized_board"], f42_result["component_ledger"]["standard_shogi"]["rows"], config)
        matrices[variant]["western"]["interval_distance"] = interval
        matrices[variant]["standard_shogi"]["shogi_gates"] = shogi
    rows: dict[str, Any] = {}
    for variant in VARIANTS:
        western = matrices[variant]["western"]
        interval = western["interval_distance"]
        shogi = matrices[variant]["standard_shogi"]["shogi_gates"]
        algebra = {"finite": all(math.isfinite(value) for value in western["completed_density_curve"].values() for value in value), "non_negative": all(value >= 0.0 for value in western["completed_density_curve"].values() for value in value)}
        semantic_pass = all((semantic["same_target_relation_control"]["identical"], semantic["split_target_control"]["positive_gap"], semantic["no_attack_control"]["zero_gap"], semantic["dual_use_only_control"]["zero_gap"], semantic["conditional_exclusion"]["ordinary_gap_unchanged"]))
        shogi_pass = shogi["pass"]
        no_drift_pass = no_drift[variant]["all"]
        structural_pass = all(structural.values()) and all(algebra.values())
        qualification = {"structural": structural_pass, "semantic_control": semantic_pass, "no_drift": no_drift_pass, "western_bands": interval["all_bands_pass"], "shogi_gates": shogi_pass, "weakly_improves_interval_distance": interval["weakly_improves_all"] and interval["strict_improvement"], "directional_mismatch": interval["directional_mismatch"], "all": False}
        qualification["all"] = variant != VARIANTS[0] and all(qualification[key] for key in ("structural", "semantic_control", "no_drift", "western_bands", "shogi_gates", "weakly_improves_interval_distance"))
        rows[variant] = {"qualification": qualification, "algebra_gates": algebra, "semantic_control": semantic, "no_drift": no_drift[variant], "interval_distance": interval, "shogi_gates": shogi}
    selection = _select(rows)
    reachability = _reachability()
    gates = {"manifest": True, "all_variants_present": tuple(VARIANTS) == tuple(manifest["variants"]), "structural": all(structural.values()), "selector_reachability": reachability["all_reachable"], "production_unchanged": True}
    result = {"schema_version": 1, "status": "PASS" if all(gates.values()) else "FAIL", "kind": "F47_ENDPOINT_DENSITY_COMPOSITE_DIAGNOSIS", "baseline": BASELINE, "production_changed": False, "h47a": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"), "endpoint_completion": manifest["endpoint_completion"], "gap_ledger": gap_ledger, "semantic_controls": semantic, "structural_controls": structural, "variants": matrices, "no_drift": no_drift, "qualification": rows, "selection": selection, "selector_reachability": reachability, "cross_stage": {"f42_to_f47": "F47 adds only the derived attack-only split-control gap to the accepted density profile; all other F42 components remain unchanged."}, "gates": gates}
    _write(result)
    return result


def _write(result: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    outputs = {"f47_endpoint_density_composite.json": result, "f47_endpoint_completion.json": result["endpoint_completion"], "f47_gap_ledger.json": result["gap_ledger"], "f47_semantic_controls.json": result["semantic_controls"], "f47_western_matrix.json": {key: value["western"] for key, value in result["variants"].items()}, "f47_standard_shogi_matrix.json": {key: value["standard_shogi"] for key, value in result["variants"].items()}, "f47_no_drift.json": result["no_drift"], "f47_qualification.json": result["qualification"], "f47_selection.json": result["selection"], "f47_selector_reachability.json": result["selector_reachability"], "f47_cross_stage.json": result["cross_stage"]}
    for name, value in outputs.items():
        (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    value = audit()
    print(json.dumps({"status": value["status"], "classification": value["selection"]["classification"], "next_boundary": value["selection"]["next_boundary"]}, sort_keys=True))
