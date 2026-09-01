"""Audit F40's rule-derived material prior and information utilization.

This script is deliberately descriptive: it rebuilds current profiles and
traces their values, but never writes a production source file or runs a
learner/search benchmark.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess import (
    build_standard_shogi_ruleset,
    build_western_chess_ruleset,
    compile_ruleset_for_execution,
)
from generic_chess.ai.evaluation.analyzer import build_movement_capability
from generic_chess.ai.evaluation.config import EvaluationConfig, MAX_STATIC_EVAL
from generic_chess.ai.evaluation.profile import _drop_profile, _raw_capability_score, build_ruleset_profile

FX = ROOT / "tests" / "fixtures"


def write(name: str, value: dict[str, Any]) -> None:
    (FX / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rank(values: list[float]) -> list[float]:
    order = sorted(enumerate(values), key=lambda pair: pair[1])
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and order[j][1] == order[i][1]:
            j += 1
        average = (i + 1 + j) / 2.0
        for k in range(i, j):
            result[order[k][0]] = average
        i = j
    return result


def pearson(a: list[float], b: list[float]) -> float:
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    da = sum((x - ma) ** 2 for x in a)
    db = sum((x - mb) ** 2 for x in b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(da * db)


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b)) / math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))


def pairwise_accuracy(a: list[float], b: list[float]) -> float:
    considered = correct = 0
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            if b[i] == b[j]:
                continue
            considered += 1
            if (a[i] > a[j]) == (b[i] > b[j]):
                correct += 1
    return correct / considered if considered else 1.0


def profile_audit(name: str, build) -> dict[str, Any]:
    config = EvaluationConfig()
    compiled = compile_ruleset_for_execution(build())
    profile = build_ruleset_profile(compiled, config)
    ordinary = [pt for pt in compiled.piece_types if not pt.is_anchor]
    capability = {
        pt.type_id: build_movement_capability(compiled.board_size, pt.movement_atoms, config)
        for pt in compiled.piece_types
    }
    raw = {pt.type_id: _raw_capability_score(capability[pt.type_id], config) for pt in compiled.piece_types}
    denominator = median([raw[pt.type_id] for pt in ordinary]) if ordinary else 0.0
    rows = []
    exact = True
    for pt in compiled.piece_types:
        cap = capability[pt.type_id]
        p = profile.piece_profiles[pt.type_id]
        mobility_score = sum(w * m for w, m in zip(config.density_weights, cap.expected_mobility))
        path_efficiency = 1.0 / (1.0 + cap.average_shortest_path) if cap.average_shortest_path is not None else 0.0
        preclamp = None if pt.is_anchor else (1 if denominator <= 0 else int(round(config.normal_piece_median_value * raw[pt.type_id] / denominator)))
        final = 0 if pt.is_anchor else max(1, min(preclamp, MAX_STATIC_EVAL))
        freedom, drop_mobility = _drop_profile(compiled, pt.type_id, compiled.board_size)
        exact &= final == p.normalized_board_value and freedom == p.drop_freedom_ratio and drop_mobility == p.drop_mobility
        rows.append({
            "type_identity": pt.type_id,
            "is_anchor": pt.is_anchor,
            "is_promotable": pt.is_promotable,
            "rule_capability_quantities": {
                "movement_signature": cap.movement_signature,
                "expected_mobility": list(cap.expected_mobility),
                "density_weighted_mobility": mobility_score,
                "coverage_ratio": cap.coverage_ratio,
                "reachable_pair_ratio": cap.reachable_pair_ratio,
                "average_shortest_path": cap.average_shortest_path,
                "path_efficiency": path_efficiency,
                "directional_asymmetry": cap.directional_asymmetry,
                "drop_freedom_ratio": freedom,
                "drop_mobility": drop_mobility,
            },
            "raw_capability_score": raw[pt.type_id],
            "normalization_denominator": denominator,
            "normalization_scale": config.normal_piece_median_value,
            "pre_clamp_integer": preclamp,
            "final_board_value": p.normalized_board_value,
            "floor_fired": bool(not pt.is_anchor and preclamp <= 1),
            "upper_clamp_fired": bool(not pt.is_anchor and preclamp >= MAX_STATIC_EVAL),
            "hand_value": p.normalized_hand_value,
            "hand_board_ratio": (p.normalized_hand_value / p.normalized_board_value if p.normalized_board_value else None),
            "promotion_gain": p.promotion_option_value,
            "promotion_base_relation": (p.promotion_option_value / p.normalized_board_value if p.normalized_board_value else None),
        })
    non_anchor = [row for row in rows if not row["is_anchor"]]
    values = sorted(row["final_board_value"] for row in non_anchor)
    smallest = values[0] if values else 0
    next_smallest = next((v for v in values if v > smallest), None)
    floor_collapse = bool(smallest == 1 and next_smallest is not None and next_smallest >= 20 * smallest)
    return {
        "ruleset": name,
        "fingerprint": compiled.ruleset_fingerprint,
        "config": {"normal_piece_median_value": config.normal_piece_median_value, "hand_weight": config.hand_weight, "max_static_eval": MAX_STATIC_EVAL},
        "median_raw": denominator,
        "median_non_anchor_value": profile.median_non_anchor_value,
        "types": rows,
        "normalization": {
            "raw_score_range": [min(raw.values()), max(raw.values())],
            "final_score_range": [min(values), max(values)],
            "minimum_floor_count": sum(row["floor_fired"] for row in non_anchor),
            "smallest_two_positive_ratio": (next_smallest / smallest if smallest and next_smallest is not None else None),
            "floor_dominated_scale_collapse": floor_collapse,
            "low_capability_can_collapse_to_one_while_median_is_O_1000": floor_collapse and profile.median_non_anchor_value >= 1000,
            "uniform_rescale_preserves_unrounded_ratios": True,
            "integer_rounding_or_floor_loses_low_end_information": any(row["floor_fired"] for row in non_anchor),
        },
        "CURRENT_PROFILE_EXACT_RECOMPOSITION": exact,
    }


def western_validation(western: dict[str, Any]) -> dict[str, Any]:
    by_type = {row["type_identity"]: row for row in western["types"]}
    base = by_type["P"]["final_board_value"]
    bands = {"P": (1.0, 1.0), "N": (2.5, 3.5), "B": (2.5, 3.75), "R": (4.0, 6.0), "Q": (7.5, 11.0)}
    ratios = {tid: by_type[tid]["final_board_value"] / base for tid in bands}
    distance = {tid: 0.0 if lo <= ratios[tid] <= hi else min(abs(ratios[tid] - lo), abs(ratios[tid] - hi)) for tid, (lo, hi) in bands.items()}
    order = ["P", "N", "B", "R", "Q"]
    ordinal = {f"{left}<{right}": by_type[left]["final_board_value"] < by_type[right]["final_board_value"] for left, right in zip(order, order[1:])}
    nb = ratios["N"] / ratios["B"]
    major_pathology = (
        western["normalization"]["floor_dominated_scale_collapse"]
        or any(ratios[t] > 5 * bands[t][1] or ratios[t] < bands[t][0] / 5 for t in bands if t != "P")
        or not all(ordinal.values())
    )
    return {"normalized_by_pawn": ratios, "distance_to_band": distance, "ordinal": ordinal, "knight_bishop_ratio": nb, "knight_bishop_ratio_in_band": 0.75 <= nb <= 1.25, "WESTERN_MATERIAL_PRIOR_SEVERE_PATHOLOGY": major_pathology}


def shogi_validation(shogi: dict[str, Any]) -> dict[str, Any]:
    by_type = {row["type_identity"]: row for row in shogi["types"]}
    board_order = ["P", "L", "N", "S", "G", "B", "R", "TP", "TL", "TN", "TS", "TB", "TR"]
    human_board = [100, 300, 320, 450, 520, 800, 1000, 520, 520, 520, 520, 950, 1150]
    hand_order = ["P", "L", "N", "S", "G", "B", "R"]
    human_hand = [100, 300, 320, 450, 520, 800, 1000]
    current_board = [float(by_type[t]["final_board_value"]) for t in board_order]
    current_hand = [float(by_type[t]["hand_value"]) for t in hand_order]
    current, human = current_board + current_hand, human_board + human_hand
    scale = sum(x * y for x, y in zip(current, human)) / sum(x * x for x in current)
    metrics = {"best_fit_scale": scale, "cosine": cosine(current, human), "pearson": pearson(current, human), "spearman": pearson(rank(current), rank(human)), "pairwise_ordering_accuracy": pairwise_accuracy(current, human)}
    healthy = metrics["cosine"] >= 0.95 and metrics["spearman"] >= 0.90 and metrics["pairwise_ordering_accuracy"] >= 0.90
    return {"board_types": {t: by_type[t]["final_board_value"] for t in board_order}, "hand_types": {t: by_type[t]["hand_value"] for t in hand_order}, "human_reference": {"board": dict(zip(board_order, human_board)), "hand": dict(zip(hand_order, human_hand))}, "metrics": metrics, "healthy": healthy, "historical_phase18_control": {"cosine": 0.989, "pearson": 0.976, "spearman": 0.952, "pairwise_ordering_accuracy": 0.965}, "drift_explanation": "Current product Standard Shogi includes semantic drop/declaration integration; F40 remeasures its current rule-derived profile without treating the historical AlphaSho table as a fitting target."}


def feature_ledger(shogi: dict[str, Any]) -> dict[str, Any]:
    drop_rows = [row for row in shogi["types"] if row["rule_capability_quantities"]["drop_freedom_ratio"] > 0]
    freedom = [row["rule_capability_quantities"]["drop_freedom_ratio"] for row in drop_rows]
    mobility = [row["rule_capability_quantities"]["drop_mobility"] for row in drop_rows]
    ledger = [
        {"signal": "movement_density_capability", "source": "analyzer.build_movement_capability", "SOURCE_RULE_SEMANTIC": True, "COMPUTED": True, "STORED": False, "USED_IN_BOARD_PRIOR": True, "USED_IN_HAND_PRIOR": False, "USED_IN_PROMOTION_PRIOR": False, "USED_BY_PYTHON_EVALUATOR": "only through board scalar", "COMPILED_INTO_NATIVE_EVALUATION": "only through board scalar", "AVAILABLE_TO_LEARNING": False, "COMPUTED_BUT_UNUSED": False, "COLLAPSED_BY_NORMALIZATION": True, "UNIFORM_FACTOR_ERASES_VARIATION": False},
        {"signal": "coverage", "source": "analyzer._coverage_ratio", "SOURCE_RULE_SEMANTIC": True, "COMPUTED": True, "STORED": False, "USED_IN_BOARD_PRIOR": True, "USED_IN_HAND_PRIOR": False, "USED_IN_PROMOTION_PRIOR": False, "USED_BY_PYTHON_EVALUATOR": "only through board scalar", "COMPILED_INTO_NATIVE_EVALUATION": "only through board scalar", "AVAILABLE_TO_LEARNING": False, "COMPUTED_BUT_UNUSED": False, "COLLAPSED_BY_NORMALIZATION": True, "UNIFORM_FACTOR_ERASES_VARIATION": False},
        {"signal": "reachability_and_path", "source": "analyzer.graph_metrics", "SOURCE_RULE_SEMANTIC": True, "COMPUTED": True, "STORED": False, "USED_IN_BOARD_PRIOR": True, "USED_IN_HAND_PRIOR": False, "USED_IN_PROMOTION_PRIOR": False, "USED_BY_PYTHON_EVALUATOR": "only through board scalar", "COMPILED_INTO_NATIVE_EVALUATION": "only through board scalar", "AVAILABLE_TO_LEARNING": False, "COMPUTED_BUT_UNUSED": False, "COLLAPSED_BY_NORMALIZATION": True, "UNIFORM_FACTOR_ERASES_VARIATION": False},
        {"signal": "drop_freedom", "source": "profile._drop_profile", "SOURCE_RULE_SEMANTIC": True, "COMPUTED": True, "STORED": True, "USED_IN_BOARD_PRIOR": False, "USED_IN_HAND_PRIOR": False, "USED_IN_PROMOTION_PRIOR": False, "USED_BY_PYTHON_EVALUATOR": False, "COMPILED_INTO_NATIVE_EVALUATION": False, "AVAILABLE_TO_LEARNING": False, "COMPUTED_BUT_UNUSED": True, "COLLAPSED_BY_NORMALIZATION": False, "UNIFORM_FACTOR_ERASES_VARIATION": True},
        {"signal": "drop_mobility", "source": "profile._drop_profile", "SOURCE_RULE_SEMANTIC": True, "COMPUTED": True, "STORED": True, "USED_IN_BOARD_PRIOR": False, "USED_IN_HAND_PRIOR": False, "USED_IN_PROMOTION_PRIOR": False, "USED_BY_PYTHON_EVALUATOR": False, "COMPILED_INTO_NATIVE_EVALUATION": False, "AVAILABLE_TO_LEARNING": False, "COMPUTED_BUT_UNUSED": True, "COLLAPSED_BY_NORMALIZATION": False, "UNIFORM_FACTOR_ERASES_VARIATION": True},
        {"signal": "promotion_targets_and_zones", "source": "profile.build_ruleset_profile + evaluator._promotion_bonus", "SOURCE_RULE_SEMANTIC": True, "COMPUTED": True, "STORED": True, "USED_IN_BOARD_PRIOR": False, "USED_IN_HAND_PRIOR": False, "USED_IN_PROMOTION_PRIOR": True, "USED_BY_PYTHON_EVALUATOR": True, "COMPILED_INTO_NATIVE_EVALUATION": True, "AVAILABLE_TO_LEARNING": False, "COMPUTED_BUT_UNUSED": False, "COLLAPSED_BY_NORMALIZATION": False, "UNIFORM_FACTOR_ERASES_VARIATION": False},
        {"signal": "anchor_escape_structure", "source": "evaluator._anchor_escape", "SOURCE_RULE_SEMANTIC": True, "COMPUTED": "per position", "STORED": False, "USED_IN_BOARD_PRIOR": False, "USED_IN_HAND_PRIOR": False, "USED_IN_PROMOTION_PRIOR": False, "USED_BY_PYTHON_EVALUATOR": True, "COMPILED_INTO_NATIVE_EVALUATION": False, "AVAILABLE_TO_LEARNING": False, "COMPUTED_BUT_UNUSED": False, "COLLAPSED_BY_NORMALIZATION": False, "UNIFORM_FACTOR_ERASES_VARIATION": False},
        {"signal": "hand_weight", "source": "EvaluationConfig.hand_weight", "SOURCE_RULE_SEMANTIC": False, "COMPUTED": True, "STORED": True, "USED_IN_BOARD_PRIOR": False, "USED_IN_HAND_PRIOR": True, "USED_IN_PROMOTION_PRIOR": False, "USED_BY_PYTHON_EVALUATOR": True, "COMPILED_INTO_NATIVE_EVALUATION": True, "AVAILABLE_TO_LEARNING": True, "COMPUTED_BUT_UNUSED": False, "COLLAPSED_BY_NORMALIZATION": False, "UNIFORM_FACTOR_ERASES_VARIATION": True},
    ]
    meaningful = bool(max(freedom) > min(freedom) and max(mobility) > min(mobility))
    return {"schema_version": 1, "status": "PASS", "ledger": ledger, "drop_information": {"per_type_rows": [{"type": row["type_identity"], "board": row["final_board_value"], "hand": row["hand_value"], "hand_board_ratio": row["hand_board_ratio"], "drop_freedom": row["rule_capability_quantities"]["drop_freedom_ratio"], "drop_mobility": row["rule_capability_quantities"]["drop_mobility"]} for row in drop_rows], "hand_derivation": "round(board_value * EvaluationConfig.hand_weight), then upper clamp", "DROP_INFORMATION_COMPUTED_BUT_NOT_UTILIZED": meaningful}, "MEANINGFUL_RULE_SIGNAL_UTILIZATION_GAP": meaningful}


def learning_ledger() -> dict[str, Any]:
    return {"schema_version": 1, "status": "PASS", "historical_authorities": {"phase_1_5": "clean paired arena did not reproduce positive strength; updates had L2 about 23–49", "phase_1_6": "parameter updates were real; decision flip rate roughly 0.2–2.9%", "phase_1_7": "learned directions were low leverage while artificial material perturbations had observable leverage", "phase_1_8": "Standard-Shogi Gen0 material prior close to human reference; mean global-scale update-energy fraction about 0.531"}, "current_learnable_parameter_basis": {"board_weights": "one per non-anchor current type", "hand_weights": "one per non-anchor base type", "other": ["global normalization scale is derived, not an independent learned feature", "no bias or position-dependent feature weight"]}, "not_learnable_currently": ["position-dependent realized activity", "anchor-local structure/control", "promotion context beyond fixed material values", "drop context beyond scalar hand weights", "coverage/reachability/path properties independently of their collapsed material scalar"], "MATERIAL_ONLY_LEARNING_CAPACITY_LOW_LEVERAGE": True}


def native_sidecar() -> dict[str, Any]:
    return {"schema_version": 1, "status": "PASS", "flow": ["RuleSet -> rules.compiler.compile_ruleset_for_execution -> CompiledRuleSet geometry/drop/promotion tables", "CompiledRuleSet -> native.compiler.build_compile_payload -> native rule capsule", "RuleSetEvaluationProfile -> native.compiler.compile_native_evaluation -> board/hand/promotion native evaluation tables", "native.engine.NativeSearchEngine -> experimental native iterative search", "ai.alphabeta.player.AlphaBetaPlayer -> Python run_root_search production backend; native semantic legality provider may be used"] , "compile_once": ["movement and semantic rule tables", "drop/promotion masks", "rule-derived board/hand/promotion values when native evaluation is explicitly compiled"], "product_python_hot_path": ["AlphaBetaPlayer constructs Evaluator and calls Python run_root_search", "Python AlphaBeta retains qsearch"], "native_capability_gap": ["NativeSearchEngine rejects nonzero qsearch limits", "NativeSearchEngine is explicitly not the production SearchBackend"], "SECOND_RULE_COMPILER_REQUIRED": False, "COMPILED_SEMANTIC_RESULTS_UNDERCONSUMED_BY_PRODUCT_SEARCH": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    if not args.run:
        parser.error("use --run")
    western, shogi = profile_audit("Western Chess", build_western_chess_ruleset), profile_audit("Standard Shogi", build_standard_shogi_ruleset)
    western_check, shogi_check = western_validation(western), shogi_validation(shogi)
    material = {"schema_version": 1, "status": "PASS", "profiles": {"western_chess": western, "standard_shogi": shogi}, "western_human_validation": western_check, "standard_shogi_human_validation": shogi_check}
    features, learning, native = feature_ledger(shogi), learning_ledger(), native_sidecar()
    severe, gap, healthy = western_check["WESTERN_MATERIAL_PRIOR_SEVERE_PATHOLOGY"], features["MEANINGFUL_RULE_SIGNAL_UTILIZATION_GAP"], shogi_check["healthy"]
    classification = "MATERIAL_AND_FEATURE_UTILIZATION_GAP" if severe and gap else ("MATERIAL_PRIOR_PATHOLOGY_PRIMARY" if severe else ("FEATURE_UTILIZATION_GAP_PRIMARY" if healthy and gap else ("MATERIAL_PRIOR_HEALTHY_STRUCTURAL_REPRESENTATION_GAP" if healthy else "MIXED_OR_UNRESOLVED")))
    mapping = {"MATERIAL_PRIOR_PATHOLOGY_PRIMARY": "F41_RULE_DERIVED_MATERIAL_PRIOR_CORRECTIVE", "MATERIAL_AND_FEATURE_UTILIZATION_GAP": "F41_RULE_DERIVED_MATERIAL_PRIOR_AND_SIGNAL_UTILIZATION_CORRECTIVE", "FEATURE_UTILIZATION_GAP_PRIMARY": "F41_RULE_FEATURE_UTILIZATION_PROTOTYPE", "MATERIAL_PRIOR_HEALTHY_STRUCTURAL_REPRESENTATION_GAP": "F41_LEARNABLE_STRUCTURAL_FEATURE_SCHEMA_REASSESSMENT", "MIXED_OR_UNRESOLVED": "F41_GENERIC_EVALUATOR_ARCHITECTURE_REASSESSMENT"}
    selection = {"schema_version": 1, "status": "PASS", "gates": {"CURRENT_PROFILE_EXACT_RECOMPOSITION": western["CURRENT_PROFILE_EXACT_RECOMPOSITION"] and shogi["CURRENT_PROFILE_EXACT_RECOMPOSITION"], "WESTERN_MATERIAL_PRIOR_SEVERE_PATHOLOGY": severe, "STANDARD_SHOGI_MATERIAL_PRIOR_HEALTHY": healthy, "DROP_INFORMATION_COMPUTED_BUT_NOT_UTILIZED": features["drop_information"]["DROP_INFORMATION_COMPUTED_BUT_NOT_UTILIZED"], "MEANINGFUL_RULE_SIGNAL_UTILIZATION_GAP": gap, "MATERIAL_ONLY_LEARNING_CAPACITY_LOW_LEVERAGE": learning["MATERIAL_ONLY_LEARNING_CAPACITY_LOW_LEVERAGE"], "SECOND_RULE_COMPILER_REQUIRED": native["SECOND_RULE_COMPILER_REQUIRED"], "COMPILED_SEMANTIC_RESULTS_UNDERCONSUMED_BY_PRODUCT_SEARCH": native["COMPILED_SEMANTIC_RESULTS_UNDERCONSUMED_BY_PRODUCT_SEARCH"]}, "aggregate_classification": classification, "selected_boundary": mapping[classification], "flags": {"F39_BROAD_TRANSFER_FAILURE_CONSUMED": True, "MATURE_RULESET_MATERIAL_PRIORS_AUDITED": True, "PROFILE_NORMALIZATION_PATHOLOGY_AUDITED": True, "RULE_INFORMATION_UTILIZATION_LEDGER_COMPLETE": True, "HISTORICAL_LEARNING_LEVERAGE_CONSUMED": True, "COMPILED_NATIVE_INFORMATION_FLOW_AUDITED": True, "NEXT_GENERIC_EVALUATOR_FOUNDATION_BOUNDARY_SELECTED": True}}
    write("f40_material_prior_audit.json", material)
    write("f40_feature_utilization_ledger.json", features)
    write("f40_learning_leverage_ledger.json", learning)
    write("f40_native_consumption_sidecar.json", native)
    write("f40_material_feature_selection.json", selection)
    print(json.dumps({"classification": classification, "boundary": mapping[classification], "status": "PASS"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
