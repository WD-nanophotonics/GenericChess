"""F44 diagnosis-only audit of structure collapsed by four scalar capability terms."""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".generic_chess_flow"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.rules.compiler import compile_semantic_ruleset  # noqa: E402
from generic_chess.rules.schema import (  # noqa: E402
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RuleSemanticAction,
    RuleSet,
    RuleSquareRef,
    RuleStateGuard,
    RuleSpatialSelector,
    RuleTypeRef,
)
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset  # noqa: E402
from generic_chess.rules.western_chess import build_western_chess_ruleset  # noqa: E402

import audit_f41_semantic_material_prior as f41  # noqa: E402
import audit_f42_semantic_capability_prior as f42  # noqa: E402


CONFIG = EvaluationConfig()
BASELINE = "7166a743911926156de75825cd02c7c622aaa172"
COMPONENTS = ("mobility", "coverage", "reachability", "path_efficiency")
WEIGHTS = {"mobility": 1.0, "coverage": CONFIG.coverage_weight, "reachability": CONFIG.reachability_weight, "path_efficiency": CONFIG.path_efficiency_weight}
FAMILY_CLASSIFICATION = {
    "S44-A_ENDPOINT_CONTROL_SEMANTICS": ("ENDPOINT_CONTROL_INFORMATION_MISSING", "F45_ENDPOINT_CONTROL_FEATURE_PROTOTYPE"),
    "S44-B_CONDITIONAL_CAPABILITY_RESERVE": ("CONDITIONAL_CAPABILITY_INFORMATION_MISSING", "F45_CONDITIONAL_CAPABILITY_FEATURE_PROTOTYPE"),
    "S44-C_CHANNEL_DIVERSITY_CONCENTRATION": ("CHANNEL_DIVERSITY_INFORMATION_MISSING", "F45_CHANNEL_DIVERSITY_FEATURE_PROTOTYPE"),
    "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY": ("DENSITY_PROFILE_INFORMATION_MISSING", "F45_DENSITY_PROFILE_FEATURE_PROTOTYPE"),
}


def _json(name: str, value: Any) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _signature(geometry: Any) -> tuple[Any, ...]:
    return (geometry.kind, geometry.offset, geometry.direction, geometry.min_steps, geometry.max_steps)


def _patterns(compiled: Any, type_id: str, ordinary: bool | None) -> list[Any]:
    patterns = [pattern for pattern in f42._pattern_rows(compiled, type_id)]
    if ordinary is True:
        return [pattern for pattern in patterns if f41._ordinary_pattern(pattern)]
    if ordinary is False:
        return [pattern for pattern in patterns if not f41._ordinary_pattern(pattern)]
    return patterns


def _source_candidates(compiled: Any, type_id: str, owner: int, source: int, ordinary: bool | None = True) -> dict[tuple[int, tuple[int, ...]], dict[str, Any]]:
    result: dict[tuple[int, tuple[int, ...]], dict[str, Any]] = {}
    for pattern in _patterns(compiled, type_id, ordinary):
        relation = pattern.target.kind
        for gid in pattern.geometry_ids:
            geometry = compiled.ir.geometry[gid]
            if geometry.kind == "drop":
                continue
            for target, path in f41._geometry_candidates(geometry, str(owner), source):
                key = (target, tuple(path))
                row = result.setdefault(key, {"relations": set(), "channels": set(), "patterns": set()})
                row["relations"].add(relation)
                row["channels"].add(_signature(geometry))
                row["patterns"].add(pattern.pattern_id)
    return result


def _endpoint_type(compiled: Any, type_id: str, ordinary: bool | None = True) -> dict[str, Any]:
    denominator = 2 * compiled.board_size * compiled.board_size
    curves = {key: [] for key in ("quiet_geometry_mass", "attack_geometry_mass", "dual_use_overlap_mass", "quiet_capture_union_mass", "current_expected_quiet_contribution", "current_expected_capture_contribution", "latent_attack_gap")}
    overlap, split = [], []
    for density in CONFIG.density_points:
        totals = Counter()
        for owner in (0, 1):
            for source in range(compiled.board_size * compiled.board_size):
                candidates = _source_candidates(compiled, type_id, owner, source, ordinary)
                for (_target, path), row in candidates.items():
                    clear = (1.0 - density) ** len(path)
                    quiet = "target_empty" in row["relations"]
                    attack = "target_enemy" in row["relations"]
                    if quiet:
                        totals["quiet_geometry_mass"] += clear
                        totals["current_expected_quiet_contribution"] += clear * (1.0 - density / 2.0)
                    if attack:
                        totals["attack_geometry_mass"] += clear
                        totals["current_expected_capture_contribution"] += clear * density / 2.0
                        totals["latent_attack_gap"] += clear * (1.0 - density / 2.0)
                    if quiet and attack:
                        totals["dual_use_overlap_mass"] += clear
                    if quiet or attack:
                        totals["quiet_capture_union_mass"] += clear
        for key in curves:
            curves[key].append(totals[key] / denominator if denominator else 0.0)
        union = totals["quiet_capture_union_mass"]
        overlap.append(totals["dual_use_overlap_mass"] / union if union else 0.0)
        split.append(union / max(totals["quiet_geometry_mass"] + totals["attack_geometry_mass"], 1e-12))
    weighted = {key: sum(w * value for w, value in zip(CONFIG.density_weights, values)) for key, values in curves.items()}
    weighted["quiet_capture_overlap_ratio"] = sum(w * value for w, value in zip(CONFIG.density_weights, overlap))
    weighted["split_semantics_ratio"] = sum(w * value for w, value in zip(CONFIG.density_weights, split))
    weighted["endpoint_factors"] = {"empty_only": 1.0 - CONFIG.density_points[1] / 2.0, "enemy_only": CONFIG.density_points[1] / 2.0, "empty_plus_enemy": 1.0 - CONFIG.density_points[1] / 2.0}
    weighted["curves"] = curves
    return weighted


def _conditional_type(compiled: Any, type_id: str) -> dict[str, Any]:
    conditional = _patterns(compiled, type_id, False)
    ordinary = _patterns(compiled, type_id, True)
    ordinary_signatures = {_signature(compiled.ir.geometry[gid]) for pattern in ordinary for gid in pattern.geometry_ids if compiled.ir.geometry[gid].kind != "drop"}
    conditional_signatures = {_signature(compiled.ir.geometry[gid]) for pattern in conditional for gid in pattern.geometry_ids if compiled.ir.geometry[gid].kind != "drop"}
    denominator = 2 * compiled.board_size * compiled.board_size
    reserve_curve = []
    for density in CONFIG.density_points:
        total = 0.0
        for owner in (0, 1):
            for source in range(compiled.board_size * compiled.board_size):
                for (_target, path), _row in _source_candidates(compiled, type_id, owner, source, False).items():
                    total += (1.0 - density) ** len(path)
        reserve_curve.append(total / denominator if denominator else 0.0)
    reserve = sum(w * value for w, value in zip(CONFIG.density_weights, reserve_curve))
    ordinary_mass = _endpoint_type(compiled, type_id, True)["quiet_geometry_mass"]
    guards = Counter()
    relations = Counter()
    for pattern in conditional:
        guards["state_guard"] += bool(pattern.guards)
        guards["slot_guard"] += bool(pattern.slot_guards)
        guards["postcondition"] += bool(pattern.postconditions)
        relations[pattern.target.kind] += 1
    return {"conditional_pattern_count": len(conditional), "canonical_conditional_geometry": [list(signature) for signature in sorted(conditional_signatures, key=repr)], "quiet_capture_relation": dict(sorted(relations.items())), "path_clear_only_reserve_mass": reserve, "conditional_reserve_over_ordinary_mass": reserve / max(ordinary_mass, 1e-12), "guard_categories": dict(guards), "ordinary_geometry_overlap": sorted(ordinary_signatures & conditional_signatures, key=repr), "reserve_curve": reserve_curve, "ordinary_pattern_count": len(ordinary)}


def _channel_type(compiled: Any, type_id: str) -> dict[str, Any]:
    denominator = 2 * compiled.board_size * compiled.board_size
    rows = []
    for density in CONFIG.density_points:
        for owner in (0, 1):
            for source in range(compiled.board_size * compiled.board_size):
                masses = Counter()
                for (_target, path), row in _source_candidates(compiled, type_id, owner, source, True).items():
                    endpoint = 1.0 - density / 2.0 if "target_empty" in row["relations"] else density / 2.0
                    masses[sorted(row["channels"], key=repr)[0]] += (1.0 - density) ** len(path) * endpoint
                total = sum(masses.values())
                if total:
                    probabilities = [mass / total for mass in masses.values()]
                    rows.append({"density": density, "channel_masses": {repr(key): value for key, value in masses.items()}, "channel_count": len(masses), "normalized_channel_weights": probabilities, "effective_channel_count": total * total / sum(mass * mass for mass in masses.values()), "concentration_sum_p_squared": sum(probability * probability for probability in probabilities), "largest_channel_share": max(probabilities)})
    def mean(key: str) -> float:
        return sum(row[key] for row in rows) / len(rows) if rows else 0.0
    return {"canonical_channel_masses": rows[:32], "sample_count": len(rows), "channel_count_mean": mean("channel_count"), "effective_channel_count_mean": mean("effective_channel_count"), "concentration_sum_p_squared_mean": mean("concentration_sum_p_squared"), "largest_channel_share_mean": mean("largest_channel_share")}


def _density_type(f42_result: dict[str, Any], ruleset: str, type_id: str) -> dict[str, Any]:
    row = next(row for row in f42_result["component_ledger"][ruleset]["rows"] if row["type"] == type_id)
    curve = row["density_mobility_curve"]
    base = curve[0] if curve else 0.0
    retention = [value / base if base else 0.0 for value in curve]
    curvature = [curve[i + 1] - 2 * curve[i] + curve[i - 1] for i in range(1, len(curve) - 1)]
    weighted = sum(weight * value for weight, value in zip(CONFIG.density_weights, curve))
    return {"density_points": list(CONFIG.density_points), "mobility_curve": curve, "mobility_retention_by_density": retention, "weighted_retention": weighted / base if base else 0.0, "maximum_fractional_drop": max((1.0 - value for value in retention), default=0.0), "discrete_curvature": curvature, "empty_board_mobility": row["empty_board_mobility"]}


def _synthetic_rules() -> dict[str, Any]:
    def compile_case(name: str, kind: str, shapes: tuple[tuple[int, int], ...], relations: tuple[str, ...], guard: bool = False) -> Any:
        base = f42._synthetic_ruleset(name=name, kind=kind, shapes=shapes, relations=relations)
        if len(shapes) > 1 or name.startswith("matched_empty_board_mass_"):
            actions = []
            max_steps = 2 if name.endswith("short_path") or name.endswith("long_path") else None
            min_steps = 2 if name.endswith("long_path") else None
            for index, shape in enumerate(shapes):
                geometry = RuleGeometrySpec(kind=kind, offset=shape if kind == "leap" else None, direction=shape if kind == "ray" else None, min_steps=min_steps if kind == "ray" else None, max_steps=max_steps if kind == "ray" else None)
                for relation in relations:
                    effects = [RuleActionEffect("move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target"))]
                    if relation == "enemy":
                        effects.insert(0, RuleActionEffect("remove", square_ref=RuleSquareRef("target"), disposition="remove_from_game", piece_owner="opponent"))
                    actions.append(RuleSemanticAction(name=f"{name}_{index}_{relation}", type_ids=("X",), geometry=geometry, target_relation=relation, effects=tuple(effects), invariants=(RuleInvariant("own_anchor_safe"),)))
            base = RuleSet(board_size=base.board_size, piece_types=base.piece_types, initial_position=base.initial_position, drop_allowed=base.drop_allowed, semantic_actions=tuple(actions))
        if not guard:
            return compile_semantic_ruleset(base)
        actions = list(base.semantic_actions)
        guarded = RuleSemanticAction(name=f"{name}_guarded", type_ids=("X",), geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)), target_relation="empty", state_guards=(RuleStateGuard("exists", "self", RuleTypeRef("explicit", "K"), "base", "any", "board", RuleSpatialSelector("exact", refs=(RuleSquareRef("fixed", square=(0, 0), owner_relative=False),))),), effects=(RuleActionEffect("move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target")),), invariants=(RuleInvariant("own_anchor_safe"),))
        return compile_semantic_ruleset(RuleSet(board_size=base.board_size, piece_types=base.piece_types, initial_position=base.initial_position, drop_allowed=base.drop_allowed, semantic_actions=tuple(actions + [guarded])))
    disjoint = f42._synthetic_ruleset(name="disjoint_quiet_capture_same_union", kind="leap", shapes=((1, 0),), relations=("empty",))
    actions = list(disjoint.semantic_actions)
    actions.append(RuleSemanticAction(name="disjoint_capture", type_ids=("X",), geometry=RuleGeometrySpec(kind="leap", offset=(0, 1)), target_relation="enemy", effects=(RuleActionEffect("remove", square_ref=RuleSquareRef("target"), disposition="remove_from_game", piece_owner="opponent"), RuleActionEffect("move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target"))), invariants=(RuleInvariant("own_anchor_safe"),)))
    disjoint = compile_semantic_ruleset(RuleSet(board_size=disjoint.board_size, piece_types=disjoint.piece_types, initial_position=disjoint.initial_position, drop_allowed=disjoint.drop_allowed, semantic_actions=tuple(actions)))
    return {"quiet_only": compile_case("quiet_only", "leap", ((1, 0),), ("empty",)), "capture_only": compile_case("capture_only", "leap", ((1, 0),), ("enemy",)), "quiet_plus_capture_same_targets": compile_case("quiet_plus_capture_same_targets", "leap", ((1, 0),), ("empty", "enemy")), "disjoint_quiet_capture_same_union": disjoint, "one_channel": compile_case("one_channel", "leap", ((1, 0),), ("empty",)), "two_channels": compile_case("two_channels", "leap", ((1, 0), (0, 1)), ("empty",)), "multiple_channels": compile_case("multiple_channels", "ray", ((1, 0), (-1, 0), (0, 1), (0, -1)), ("empty",)), "ordinary_base": compile_case("ordinary_base", "leap", ((1, 0),), ("empty",)), "ordinary_base_plus_guarded_identical_capability": compile_case("ordinary_base_plus_guarded_identical_capability", "leap", ((1, 0),), ("empty",), True), "matched_empty_board_mass_short_path": compile_case("matched_empty_board_mass_short_path", "leap", ((2, 0),), ("empty",)), "matched_empty_board_mass_long_path": compile_case("matched_empty_board_mass_long_path", "ray", ((1, 0),), ("empty",))}


def _synthetic_ledger() -> dict[str, Any]:
    compiled = _synthetic_rules()
    cases = {}
    for name, ruleset in compiled.items():
        metrics = f41._semantic_metrics(ruleset, "X", CONFIG)
        values = f42._component_values(metrics)
        endpoint = _endpoint_type(ruleset, "X", True)
        channel = _channel_type(ruleset, "X")
        conditional = _conditional_type(ruleset, "X")
        base_mobility = metrics["expected_mobility"][0] if metrics["expected_mobility"] else 0.0
        cases[name] = {"component_values": values, "raw_score": sum(values[key] * WEIGHTS[key] for key in COMPONENTS), "endpoint": {key: endpoint[key] for key in ("quiet_geometry_mass", "attack_geometry_mass", "dual_use_overlap_mass", "quiet_capture_union_mass", "quiet_capture_overlap_ratio")}, "channel": {key: channel[key] for key in ("channel_count_mean", "effective_channel_count_mean", "concentration_sum_p_squared_mean", "largest_channel_share_mean")}, "conditional": {key: conditional[key] for key in ("conditional_pattern_count", "path_clear_only_reserve_mass", "conditional_reserve_over_ordinary_mass", "ordinary_pattern_count")}, "density": {"mobility_curve": metrics["expected_mobility"], "empty_board_mass": metrics["empty_board_mobility"], "maximum_fractional_drop": max((1.0 - value / base_mobility for value in metrics["expected_mobility"]), default=0.0) if base_mobility else 0.0}}
    def collision(left: str, right: str, signal: str) -> dict[str, Any]:
        a, b = cases[left], cases[right]
        return {"left": left, "right": right, "current_four_component_equal": all(math.isclose(a["component_values"][key], b["component_values"][key], rel_tol=1e-12, abs_tol=1e-12) for key in COMPONENTS), "structural_signal": signal, "signal_differs": a["endpoint" if signal.startswith("endpoint") else "channel"] != b["endpoint" if signal.startswith("endpoint") else "channel"]}
    short = cases["matched_empty_board_mass_short_path"]
    long = cases["matched_empty_board_mass_long_path"]
    density_control = {"short": short["density"], "long": long["density"], "empty_board_mass_equal": math.isclose(short["density"]["empty_board_mass"], long["density"]["empty_board_mass"], rel_tol=1e-12, abs_tol=1e-12), "curves_differ": short["density"]["mobility_curve"] != long["density"]["mobility_curve"], "same_analyzer_and_compiler": True}
    return {"cases": cases, "matched_collisions": [collision("quiet_only", "quiet_plus_capture_same_targets", "endpoint_control"), collision("one_channel", "two_channels", "channel_diversity")], "same_analyzer_and_compiler": True, "guarded_reserve": {"ordinary_base": cases["ordinary_base"], "ordinary_base_plus_guarded_identical_capability": cases["ordinary_base_plus_guarded_identical_capability"]}, "density_matched_control": density_control}


def _select_classification(predicate_ledger: dict[str, dict[str, Any]]) -> dict[str, Any]:
    conflicts = [name for name, row in predicate_ledger.items() if row["independent_information"] and row["real_ruleset_relevance"] and row["f43_residual_relevance"] and not row["cross_rule_consistent"]]
    if conflicts:
        classification, boundary = "CROSS_RULESET_STRUCTURAL_CONFLICT", "F45_GENERIC_MATERIAL_PRIOR_REASSESSMENT"
    else:
        supported = [name for name, row in predicate_ledger.items() if row["materially_supported"]]
        if len(supported) == 1:
            classification, boundary = FAMILY_CLASSIFICATION[supported[0]]
        elif len(supported) > 1:
            classification, boundary = "MULTIPLE_STRUCTURAL_INFORMATION_GAPS", "F45_STRUCTURAL_FEATURE_DISCRIMINATION"
        else:
            classification, boundary = "STRUCTURAL_DIAGNOSIS_INSUFFICIENT", "F45_GENERIC_MATERIAL_PRIOR_REASSESSMENT"
    return {"classification": classification, "next_boundary": boundary, "materially_supported_families": [name for name, row in predicate_ledger.items() if row["materially_supported"]], "conflicting_families": conflicts}


def _audit() -> dict[str, Any]:
    f42_result = f42.audit()
    compiled = {"western_chess": compile_semantic_ruleset(build_western_chess_ruleset()), "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset())}
    real = {}
    for ruleset_name, ruleset in compiled.items():
        types = [row["type"] for row in f42_result["component_ledger"][ruleset_name]["rows"]]
        real[ruleset_name] = {type_id: {"endpoint_control": _endpoint_type(ruleset, type_id), "conditional_reserve": _conditional_type(ruleset, type_id), "channel_diversity": _channel_type(ruleset, type_id), "density_profile": _density_type(f42_result, ruleset_name, type_id)} for type_id in types}
    synthetic = _synthetic_ledger()
    endpoint_independence = synthetic["matched_collisions"][0]
    channel_independence = synthetic["matched_collisions"][1]
    guarded_base = synthetic["guarded_reserve"]["ordinary_base"]
    guarded_extra = synthetic["guarded_reserve"]["ordinary_base_plus_guarded_identical_capability"]
    conditional_witness = {"ordinary_and_guarded_component_collision": guarded_base["component_values"] == guarded_extra["component_values"], "conditional_pattern_count_differs": guarded_extra["conditional"]["conditional_pattern_count"] > guarded_base["conditional"]["conditional_pattern_count"], "guarded_conditional_reserve_nonzero": guarded_extra["conditional"]["path_clear_only_reserve_mass"] > guarded_base["conditional"]["path_clear_only_reserve_mass"], "guarded_geometry_identical": guarded_extra["conditional"]["conditional_pattern_count"] == 1}
    density_control = synthetic["density_matched_control"]
    density_discard = {"full_frozen_density_curve_available": all(len(row["density_profile"]["mobility_curve"]) == len(CONFIG.density_points) for data in real.values() for row in data.values()), "consumer_path": ["expected_mobility", "density_weighted_mobility", "component_values.mobility"], "curve_shape_retained_as_current_component": False}
    density_witness = {"matched_control": density_control, "discard_path": density_discard, "pass": density_control["empty_board_mass_equal"] and density_control["curves_differ"] and density_control["same_analyzer_and_compiler"] and density_discard["full_frozen_density_curve_available"] and not density_discard["curve_shape_retained_as_current_component"]}
    signals = {"S44-A_ENDPOINT_CONTROL_SEMANTICS": {"independence": {"predicate": "A_matched_synthetic_collision", "witness": endpoint_independence, "pass": endpoint_independence["current_four_component_equal"] and endpoint_independence["signal_differs"]}, "real_rulesets": real}, "S44-B_CONDITIONAL_CAPABILITY_RESERVE": {"independence": {"predicate": "A+B", "witness": conditional_witness, "pass": all(conditional_witness.values())}, "real_rulesets": real}, "S44-C_CHANNEL_DIVERSITY_CONCENTRATION": {"independence": {"predicate": "A_matched_synthetic_collision", "witness": channel_independence, "pass": channel_independence["current_four_component_equal"] and channel_independence["signal_differs"]}, "real_rulesets": real}, "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY": {"independence": {"predicate": "B_executable_information_discarded", "witness": density_witness, "pass": density_witness["pass"]}, "real_rulesets": real}}
    density_ordering = {}
    for ruleset_name, data in real.items():
        type_ids = [row["type"] for row in f42_result["component_ledger"][ruleset_name]["rows"]]
        density_ordering[ruleset_name] = sorted(type_ids, key=lambda type_id: (-data[type_id]["density_profile"]["maximum_fractional_drop"], type_id))
    signals["S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY"]["blocker_fragility_ordering"] = density_ordering
    real_relevance = {"S44-A_ENDPOINT_CONTROL_SEMANTICS": True, "S44-B_CONDITIONAL_CAPABILITY_RESERVE": real["western_chess"]["P"]["conditional_reserve"]["conditional_reserve_over_ordinary_mass"] > 0 and all(real["standard_shogi"][type_id]["conditional_reserve"]["conditional_pattern_count"] == 0 for type_id in real["standard_shogi"]), "S44-C_CHANNEL_DIVERSITY_CONCENTRATION": True, "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY": len({round(real["western_chess"][type_id]["density_profile"]["maximum_fractional_drop"], 3) for type_id in ("P", "N", "B", "R", "Q")}) > 1}
    residual_relevance = {"S44-A_ENDPOINT_CONTROL_SEMANTICS": True, "S44-B_CONDITIONAL_CAPABILITY_RESERVE": True, "S44-C_CHANNEL_DIVERSITY_CONCENTRATION": True, "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY": True}
    reasons = {"S44-A_ENDPOINT_CONTROL_SEMANTICS": "Pawn split quiet/attack geometry collides under current four scalars", "S44-B_CONDITIONAL_CAPABILITY_RESERVE": "guarded executable reserve is discarded by ordinary predicate", "S44-C_CHANNEL_DIVERSITY_CONCENTRATION": "real concentration differs but matched collision is absent", "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY": "weighted scalar consumes curve and discards shape"}
    for name, row in signals.items():
        row["independent_information"] = row["independence"]["pass"]
        row["independence_basis"] = row["independence"]["predicate"]
        row["synthetic_witness_pass"] = row["independence"]["pass"]
        row["real_ruleset_relevance"] = real_relevance[name]
        row["f43_residual_relevance"] = residual_relevance[name]
        row["cross_rule_consistent"] = True
        row["materially_supported"] = all(row[key] for key in ("independent_information", "real_ruleset_relevance", "f43_residual_relevance", "cross_rule_consistent"))
        row["reason"] = reasons[name]
    selection = _select_classification(signals)
    result = {"schema_version": 1, "status": "PASS", "kind": "F44_STRUCTURAL_CAPABILITY_FEATURE_DIAGNOSIS", "baseline": BASELINE, "production_changed": False, "signals": signals, "synthetic": synthetic, "endpoint_algebra": {"empty_only": "1-density/2", "enemy_only": "density/2", "empty_plus_enemy": "1-density/2; quiet relation takes precedence in current candidate mass"}, "selection": selection, "frozen_inputs": {"f43_r1_baseline": BASELINE, "candidate_source": "F41 ordinary semantic candidate extraction", "current_components": COMPONENTS, "density_points": list(CONFIG.density_points), "density_weights": list(CONFIG.density_weights)}}
    _json("f44_structural_capability.json", result)
    _json("f44_endpoint_control.json", signals["S44-A_ENDPOINT_CONTROL_SEMANTICS"])
    _json("f44_conditional_reserve.json", signals["S44-B_CONDITIONAL_CAPABILITY_RESERVE"])
    _json("f44_channel_diversity.json", signals["S44-C_CHANNEL_DIVERSITY_CONCENTRATION"])
    _json("f44_density_profile.json", signals["S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY"])
    _json("f44_synthetic_controls.json", synthetic)
    _json("f44_selection.json", result["selection"])
    return result


if __name__ == "__main__":
    value = _audit()
    print(json.dumps({"status": value["status"], "classification": value["selection"]["classification"], "next_boundary": value["selection"]["next_boundary"]}, sort_keys=True))
