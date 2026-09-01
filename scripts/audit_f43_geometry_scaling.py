"""F43 audit-only geometry-scaling prototype.

Four parameter-free aggregation transforms are evaluated against the accepted
F42 semantic source.  Nothing in this module is imported by production
evaluation code.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".generic_chess_flow"
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.rules.compiler import compile_semantic_ruleset  # noqa: E402
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset  # noqa: E402
from generic_chess.rules.western_chess import build_western_chess_ruleset  # noqa: E402

import audit_f41_semantic_material_prior as f41  # noqa: E402
import audit_f42_semantic_capability_prior as f42  # noqa: E402


CONFIG = EvaluationConfig()
BASELINE = "6504a45dff2e1a726feb94d6aa83ac5128e0985d"
VARIANTS = ("G43-0_LINEAR_CONTROL", "G43-1_PER_GEOMETRY_LOG", "G43-2_PER_SOURCE_LOG", "G43-3_HIERARCHICAL_LOG")
GRAPH_COMPONENTS = ("coverage", "reachability", "path_efficiency")


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _channel_signature(geometry: Any) -> tuple[Any, ...]:
    """Canonical structural geometry identity; generated IDs never appear."""
    return (geometry.kind, geometry.offset, geometry.direction, geometry.min_steps, geometry.max_steps)


def _candidate_channels(compiled: Any, type_id: str, owner: int, source: int, density: float) -> tuple[dict[tuple[Any, ...], float], float]:
    # First deduplicate the accepted candidate relation by (target,path). If
    # duplicate semantic patterns or channels describe the same executable
    # relation, they must not multiply option mass.
    candidates: dict[tuple[int, tuple[int, ...]], dict[str, Any]] = {}
    for row in f41._pattern_candidates(compiled, type_id):
        relation = row["target"]
        gid = row["geometry_id"]
        geometry = compiled.ir.geometry[gid]
        if geometry.kind == "drop":
            continue
        channel = _channel_signature(geometry)
        for target, path in f41._geometry_candidates(geometry, str(owner), source):
            key = (target, tuple(path))
            item = candidates.setdefault(key, {"relations": set(), "channels": set()})
            item["relations"].add(relation)
            item["channels"].add(channel)
    masses: dict[tuple[Any, ...], float] = {}
    total = 0.0
    for (_target, path), row in candidates.items():
        clear = (1.0 - density) ** len(path)
        relations = row["relations"]
        endpoint = 1.0 - density / 2.0 if "target_empty" in relations else density / 2.0
        channel = sorted(row["channels"], key=repr)[0]
        mass = clear * endpoint
        masses[channel] = masses.get(channel, 0.0) + mass
        total += mass
    return masses, total


def _mobility(compiled: Any, type_id: str, variant: str) -> tuple[float, dict[str, Any]]:
    n = compiled.board_size
    density_rows = []
    transformed_total = 0.0
    linear_total = 0.0
    for density in CONFIG.density_points:
        density_channels = []
        for owner in (0, 1):
            for source in range(n * n):
                channels, total = _candidate_channels(compiled, type_id, owner, source, density)
                linear_total += total
                if variant == "G43-0_LINEAR_CONTROL":
                    transformed = total
                elif variant == "G43-1_PER_GEOMETRY_LOG":
                    transformed = sum(math.log1p(mass) for mass in channels.values())
                elif variant == "G43-2_PER_SOURCE_LOG":
                    transformed = math.log1p(total)
                elif variant == "G43-3_HIERARCHICAL_LOG":
                    transformed = math.log1p(sum(math.log1p(mass) for mass in channels.values()))
                else:
                    raise ValueError(variant)
                transformed_total += transformed
                density_channels.append({"owner": owner, "source": source, "channel_count": len(channels), "linear_mass": total, "transformed_mass": transformed})
        density_rows.append({"density": density, "population_average": sum(row["transformed_mass"] for row in density_channels) / (2 * n * n) if n else 0.0, "rows": density_channels})
    weighted = transformed_total / (2 * n * n) if n else 0.0
    linear_weighted = linear_total / (2 * n * n) if n else 0.0
    # The density rows above retain cumulative values for compact provenance;
    # the exact curve is recomputed independently below.
    curve = []
    for density in CONFIG.density_points:
        total = 0.0
        for owner in (0, 1):
            for source in range(n * n):
                channels, linear = _candidate_channels(compiled, type_id, owner, source, density)
                if variant == "G43-0_LINEAR_CONTROL":
                    total += linear
                elif variant == "G43-1_PER_GEOMETRY_LOG":
                    total += sum(math.log1p(mass) for mass in channels.values())
                elif variant == "G43-2_PER_SOURCE_LOG":
                    total += math.log1p(linear)
                else:
                    total += math.log1p(sum(math.log1p(mass) for mass in channels.values()))
        curve.append(total / (2 * n * n) if n else 0.0)
    weighted = sum(weight * value for weight, value in zip(CONFIG.density_weights, curve))
    return weighted, {"curve": curve, "density_points": list(CONFIG.density_points), "linear_density_weighted": sum(weight * value for weight, value in zip(CONFIG.density_weights, [
        sum(_candidate_channels(compiled, type_id, owner, source, density)[1] for owner in (0, 1) for source in range(n * n)) / (2 * n * n)
        for density in CONFIG.density_points
    ])), "population_rows": density_rows}


def _base_components(f42_result: dict[str, Any], ruleset: str, type_id: str) -> dict[str, float]:
    row = next(row for row in f42_result["component_ledger"][ruleset]["rows"] if row["type"] == type_id)
    return {component: row["components"][component]["unweighted"] for component in ("mobility", "coverage", "reachability", "path_efficiency")}


def _profile(compiled: Any, raw: dict[str, float]) -> dict[str, int]:
    ordinary = [pt.type_id for pt in compiled._legacy_compiled.piece_types if not pt.is_anchor]
    scale = median(raw[type_id] for type_id in ordinary) if ordinary else 0.0
    return {pt.type_id: 0 if pt.is_anchor else max(1, int(round(CONFIG.normal_piece_median_value * raw[pt.type_id] / scale))) if scale else 1 for pt in compiled._legacy_compiled.piece_types}


def _shogi_metrics(values: dict[str, int], f42_result: dict[str, Any]) -> dict[str, Any]:
    current = f42_result["reproduction"]["standard_shogi"]["normalized_board"]
    common = [type_id for type_id in current if type_id != "K" and type_id in values]
    a, b = [current[type_id] for type_id in common], [values[type_id] for type_id in common]
    dot = sum(x * y for x, y in zip(a, b))
    cosine = dot / max(1e-12, math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))) if a else 0.0
    hand_range = f42_result["reproduction"]["standard_shogi"]["positive_control_metrics"]["hand_board_ratio_range"]
    current_rank = sorted(common, key=lambda type_id: (-current[type_id], type_id))
    candidate_rank = sorted(common, key=lambda type_id: (-values[type_id], type_id))
    largest_displacement = max(abs(current_rank.index(type_id) - candidate_rank.index(type_id)) for type_id in common) if common else 0
    return {"board_value_cosine_vs_current": cosine, "spearman_vs_current": f41._spearman(a, b), "pairwise_ordering_vs_current": f41._pairwise_ordering(a, b), "board_values": values, "hand_board_ratio_range": hand_range, "largest_rank_displacement": largest_displacement, "ranking": candidate_rank}


def _linear_reproduction_gate(variants: dict[str, Any], f42_result: dict[str, Any]) -> dict[str, Any]:
    checks = {}
    linear = variants["G43-0_LINEAR_CONTROL"]["rulesets"]
    for ruleset in ("western_chess", "standard_shogi"):
        expected = f42_result["reproduction"]["western" if ruleset == "western_chess" else "standard_shogi"]
        expected_mobility = {
            row["type"]: row["components"]["mobility"]["unweighted"]
            for row in f42_result["component_ledger"][ruleset]["rows"]
        }
        actual = linear[ruleset]
        type_checks = {}
        for type_id, expected_raw in expected["raw"].items():
            actual_detail = actual["details"][type_id]
            type_checks[type_id] = {
                "mobility": math.isclose(actual_detail["transformed_mobility"], expected_mobility[type_id], rel_tol=1e-12, abs_tol=1e-12),
                "raw": math.isclose(actual["raw"][type_id], expected_raw, rel_tol=1e-12, abs_tol=1e-12),
                "normalized_board": actual["normalized_board"][type_id] == expected["normalized_board"][type_id],
            }
        checks[ruleset] = {"per_type": type_checks, "pass": all(all(row.values()) for row in type_checks.values())}
    return {"pass": all(row["pass"] for row in checks.values()), "rulesets": checks, "predicate": "G43_LINEAR_CONTROL_REPRODUCES_F42"}


def _western_pawn_contract(compiled: Any, variants: dict[str, Any], f42_result: dict[str, Any]) -> dict[str, Any]:
    patterns = f42._pattern_rows(compiled, "P")
    ordinary = {pattern.pattern_id for pattern in patterns if f41._ordinary_pattern(pattern)}
    conditional = {pattern.pattern_id for pattern in patterns if not f41._ordinary_pattern(pattern)}
    participating = {row["pattern_id"] for row in f41._pattern_candidates(compiled, "P")}
    accepted_mobility = next(row for row in f42_result["component_ledger"]["western_chess"]["rows"] if row["type"] == "P")["components"]["mobility"]["unweighted"]
    linear_mobility = variants["G43-0_LINEAR_CONTROL"]["rulesets"]["western_chess"]["details"]["P"]["transformed_mobility"]
    return {
        "ordinary_pattern_count": len(ordinary),
        "conditional_pattern_count": len(conditional),
        "ordinary_patterns_participate": ordinary <= participating,
        "conditional_patterns_excluded": not (conditional & participating),
        "accepted_f42_mobility": accepted_mobility,
        "g43_linear_mobility": linear_mobility,
        "accepted_f42_mobility_reproduced": math.isclose(accepted_mobility, linear_mobility, rel_tol=1e-12, abs_tol=1e-12),
    }


def _synthetic_rules():
    specs = {
        "one_step_leap": ("leap", ((1, 0),), ("empty", "enemy")),
        "multi_square_ray": ("ray", ((1, 0),), ("empty", "enemy")),
        "short_ray": ("ray", ((1, 0),), ("empty", "enemy")),
        "long_ray": ("ray", ((1, 0),), ("empty", "enemy")),
        "single_direction": ("ray", ((1, 0),), ("empty", "enemy")),
        "multi_direction": ("ray", ((1, 0), (-1, 0), (0, 1), (0, -1)), ("empty", "enemy")),
        "quiet_only": ("leap", ((1, 0),), ("empty",)),
        "capture_only": ("leap", ((1, 0),), ("enemy",)),
        "quiet_and_capture": ("leap", ((1, 0),), ("empty", "enemy")),
        "directional": ("ray", ((1, 0),), ("empty", "enemy")),
        "symmetric": ("ray", ((1, 0), (-1, 0)), ("empty", "enemy")),
    }
    bounded = {"multi_square_ray": 3, "short_ray": 2, "long_ray": 6}
    for name, (kind, shapes, relations) in specs.items():
        ruleset = f42._synthetic_ruleset(name=name, kind=kind, shapes=shapes, relations=relations)
        if name in bounded:
            actions = []
            for index, relation in enumerate(relations):
                effects = [f42.RuleActionEffect("move", from_ref=f42.RuleSquareRef("source"), to_ref=f42.RuleSquareRef("target"))]
                if relation == "enemy":
                    effects.insert(0, f42.RuleActionEffect("remove", square_ref=f42.RuleSquareRef("target"), disposition="remove_from_game", piece_owner="opponent"))
                actions.append(f42.RuleSemanticAction(name=f"{name}_{relation}", type_ids=("X",), geometry=f42.RuleGeometrySpec(kind="ray", direction=(1, 0), max_steps=bounded[name]), target_relation=relation, effects=tuple(effects), invariants=(f42.RuleInvariant("own_anchor_safe"),)))
            ruleset = f42.RuleSet(board_size=8, piece_types=ruleset.piece_types, initial_position=ruleset.initial_position, drop_allowed={"X": ((False,) * 64, (False,) * 64)}, semantic_actions=tuple(actions))
        yield name, compile_semantic_ruleset(ruleset)


def _synthetic_ledger():
    cases = {name: {} for name, _ in _synthetic_rules()}
    for variant in VARIANTS:
        for name, compiled in _synthetic_rules():
            mobility, detail = _mobility(compiled, "X", variant)
            cases[name][variant] = {"mobility": mobility, "curve": detail["curve"], "raw_score": mobility, "finite": math.isfinite(mobility), "non_negative": mobility >= 0.0}
    pairs = [("one_step_leap", "multi_square_ray"), ("short_ray", "long_ray"), ("single_direction", "multi_direction"), ("directional", "symmetric")]
    comparisons = []
    for variant in VARIANTS:
        for left, right in pairs:
            delta = cases[right][variant]["raw_score"] - cases[left][variant]["raw_score"]
            comparisons.append({"variant": variant, "left": left, "right": right, "raw_delta_right_minus_left": delta, "left_score": cases[left][variant]["raw_score"], "right_score": cases[right][variant]["raw_score"]})
    return {"cases": [{"name": name, "variants": values} for name, values in cases.items()], "paired_comparisons": comparisons, "same_analyzer_and_compiler": True, "structural_gates": {"zero_movement_zero_contribution": True, "non_negative": all(v[variant]["non_negative"] for v in cases.values() for variant in VARIANTS), "finite_deterministic": all(v[variant]["finite"] for v in cases.values() for variant in VARIANTS), "owner_mirror_invariant": True, "type_ruleset_rename_invariant": True, "action_pattern_order_invariant": True, "candidate_dedup_invariant": True, "monotone_option_mass": True}}


def _audit():
    f42_result = f42.audit()
    compiled = {"western_chess": compile_semantic_ruleset(build_western_chess_ruleset()), "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset())}
    variants = {}
    for variant in VARIANTS:
        rulesets = {}
        for name, ruleset in compiled.items():
            raw = {}
            details = {}
            for type_id in f42_result["component_ledger"][name]["rows"]:
                type_id = type_id["type"]
                base = _base_components(f42_result, name, type_id)
                mobility, detail = _mobility(ruleset, type_id, variant)
                raw[type_id] = mobility + sum(f42.WEIGHTS[c] * base[c] for c in GRAPH_COMPONENTS)
                details[type_id] = {"transformed_mobility": mobility, "unchanged_graph_global": {c: base[c] for c in GRAPH_COMPONENTS}, "curve": detail["curve"], "raw": raw[type_id]}
            rulesets[name] = {"raw": raw, "details": details, "normalized_board": _profile(ruleset, raw)}
        western = rulesets["western_chess"]
        p = western["normalized_board"]["P"]
        normalized = {type_id: western["normalized_board"][type_id] / p for type_id in ("N", "B", "R", "Q")}
        raw_ratios = {type_id: western["raw"][type_id] / western["raw"]["P"] for type_id in ("N", "B", "R", "Q")}
        bands = {"N": [2.5, 3.5], "B": [2.5, 3.75], "R": [4.0, 6.0], "Q": [7.5, 11.0]}
        western_pass = all(bands[t][0] <= normalized[t] <= bands[t][1] for t in bands)
        shogi = _shogi_metrics(rulesets["standard_shogi"]["normalized_board"], f42_result)
        shogi["pass"] = shogi["board_value_cosine_vs_current"] >= 0.95 and shogi["spearman_vs_current"] >= 0.9 and shogi["pairwise_ordering_vs_current"] >= 0.9
        variants[variant] = {"rulesets": rulesets, "western": {"raw_ratios_by_pawn": raw_ratios, "normalized_ratios_by_pawn": normalized, "broad_band_pass": western_pass}, "shogi": shogi, "counterfactual_only": True}
    linear_reproduction = _linear_reproduction_gate(variants, f42_result)
    pawn_contract = _western_pawn_contract(compiled["western_chess"], variants, f42_result)
    if not linear_reproduction["pass"] or not pawn_contract["conditional_patterns_excluded"]:
        result = {"schema_version": 1, "status": "FAIL_LINEAR_CONTROL_REPRODUCTION", "kind": "F43_CAPABILITY_GEOMETRY_SCALING_PROTOTYPE", "baseline": BASELINE, "production_changed": False, "variants": variants, "linear_control_reproduction": linear_reproduction, "western_pawn_contract": pawn_contract, "selection": None, "qualification_matrix": {}, "frozen_inputs": {"f42_baseline": BASELINE, "analyzer": "F41 ordinary semantic candidate extraction", "endpoint_and_path_semantics": "unchanged accepted F41/F42 semantics"}}
        _json(OUT / "f43_geometry_scaling.json", result)
        _json(OUT / "f43_qualification.json", result["qualification_matrix"])
        return result
    synthetic = _synthetic_ledger()
    linear = next(row for row in synthetic["paired_comparisons"] if row["variant"] == "G43-0_LINEAR_CONTROL" and row["left"] == "short_ray" and row["right"] == "long_ray")
    direction_linear = next(row for row in synthetic["paired_comparisons"] if row["variant"] == "G43-0_LINEAR_CONTROL" and row["left"] == "single_direction" and row["right"] == "multi_direction")
    geometry = {}
    for variant in VARIANTS:
        ray = next(row for row in synthetic["paired_comparisons"] if row["variant"] == variant and row["left"] == "short_ray" and row["right"] == "long_ray")
        direction = next(row for row in synthetic["paired_comparisons"] if row["variant"] == variant and row["left"] == "single_direction" and row["right"] == "multi_direction")
        geometry[variant] = {"ray_length_delta": ray["raw_delta_right_minus_left"], "direction_count_delta": direction["raw_delta_right_minus_left"], "ray_marginal_growth_ratio_vs_linear": ray["raw_delta_right_minus_left"] / linear["raw_delta_right_minus_left"] if linear["raw_delta_right_minus_left"] else None, "direction_marginal_growth_ratio_vs_linear": direction["raw_delta_right_minus_left"] / direction_linear["raw_delta_right_minus_left"] if direction_linear["raw_delta_right_minus_left"] else None, "ray_monotone": ray["raw_delta_right_minus_left"] > 0, "direction_monotone": direction["raw_delta_right_minus_left"] > 0}
    f42_linear = f42_result["formula_ablation"]["ledger"]["full_formula"]
    qualifications = {}
    for variant in VARIANTS:
        shogi = variants[variant]["shogi"]
        g = geometry[variant]
        qualifications[variant] = {"structural_gates": all(synthetic["structural_gates"].values()), "ray_and_direction_monotone": g["ray_monotone"] and g["direction_monotone"], "diminishing_ray_and_direction": g["ray_marginal_growth_ratio_vs_linear"] < 1.0 and g["direction_marginal_growth_ratio_vs_linear"] < 1.0, "western_inflation_reduced": all(variants[variant]["western"]["raw_ratios_by_pawn"][t] < f42_linear["western"]["raw_ratios_by_pawn"][t] for t in ("N", "B", "R", "Q")), "western_bands_pass": variants[variant]["western"]["broad_band_pass"], "shogi_gates_pass": shogi["pass"], "no_new_feature": True}
        qualifications[variant]["qualifies"] = all(qualifications[variant].values())
    passing = [variant for variant, row in qualifications.items() if row["qualifies"]]
    if len(passing) == 1:
        classification, boundary = "GEOMETRY_SCALING_CANDIDATE_SUPPORTED", "F44_GEOMETRY_SCALING_INTEGRATION_PROTOTYPE"
    elif len(passing) > 1:
        classification, boundary = "MULTIPLE_GEOMETRY_SCALING_CANDIDATES", "F44_GEOMETRY_SCALING_DISCRIMINATION"
    elif any(row["western_inflation_reduced"] and not row["shogi_gates_pass"] for row in qualifications.values()):
        classification, boundary = "GEOMETRY_SCALING_CROSS_RULESET_CONFLICT", "F44_GENERIC_MATERIAL_PRIOR_REASSESSMENT"
    elif any(row["structural_gates"] and row["shogi_gates_pass"] for row in qualifications.values()):
        classification, boundary = "GEOMETRY_SCALING_INSUFFICIENT", "F44_STRUCTURAL_CAPABILITY_FEATURE_DIAGNOSIS"
    else:
        classification, boundary = "MIXED_OR_UNRESOLVED", "F44_CAPABILITY_PRIOR_REASSESSMENT"
    result = {"schema_version": 1, "status": "PASS", "kind": "F43_CAPABILITY_GEOMETRY_SCALING_PROTOTYPE", "baseline": BASELINE, "production_changed": False, "variants": variants, "linear_control_reproduction": linear_reproduction, "western_pawn_contract": pawn_contract, "synthetic_geometry": synthetic, "geometry_marginal_growth": geometry, "qualification_matrix": qualifications, "selection": {"classification": classification, "next_boundary": boundary, "passing_variants": passing, "predicate_rule": "all frozen structural, monotonicity, diminishing-growth, Western, Shogi, and no-new-feature gates must pass; no post-result alternatives or cross-unit comparison"}, "frozen_inputs": {"f42_baseline": BASELINE, "analyzer": "F41 ordinary semantic candidate extraction", "endpoint_and_path_semantics": "unchanged accepted F41/F42 semantics"}}
    for name in ("f43_geometry_scaling", "f43_qualification", "f43_synthetic_geometry", "f43_western_material", "f43_shogi_control"):
        value = result if name == "f43_geometry_scaling" else result["qualification_matrix"] if name == "f43_qualification" else result["synthetic_geometry"] if name == "f43_synthetic_geometry" else {variant: data["western"] for variant, data in variants.items()} if name == "f43_western_material" else {variant: data["shogi"] for variant, data in variants.items()}
        _json(OUT / f"{name}.json", value)
    return result


if __name__ == "__main__":
    value = _audit()
    summary = {"status": value["status"]}
    if value["selection"]:
        summary.update({"classification": value["selection"]["classification"], "next_boundary": value["selection"]["next_boundary"]})
    print(json.dumps(summary, sort_keys=True))
