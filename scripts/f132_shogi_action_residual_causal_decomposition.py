"""F132: causal decomposition of the frozen F131 action-ranking residual.

This benchmark performs no new learner selection.  It reconstructs the exact
F131 matched-ridge action model, then only measures residuals and exact
successor-state/oracle contribution relationships.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import FrozenBasis, _json_sha, _scalar_metrics
    from scripts.f128_shogi_direct_control_cross_surface_diagnosis import CORPUS_HASH, _collect_states, _eligibility_map, _selected_ordinals
    from scripts.f129_shogi_known_oracle_t1_scalar_compression import RETAINED_COUNTS, _load_or_generate_shards, _materialize
    from scripts.f131_shogi_action_conditioned_t1_factorization import (
        F129_BASE_HOLDOUT_RMSE,
        F129_STATIC_HOLDOUT_RMSE,
        _action_context,
        _fit,
        _predict,
        action_features,
    )
    from scripts.f130_shogi_rule_derived_structural_t1_augmentation import structural_features
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import FrozenBasis, _json_sha, _scalar_metrics
    from f128_shogi_direct_control_cross_surface_diagnosis import CORPUS_HASH, _collect_states, _eligibility_map, _selected_ordinals
    from f129_shogi_known_oracle_t1_scalar_compression import RETAINED_COUNTS, _load_or_generate_shards, _materialize
    from f131_shogi_action_conditioned_t1_factorization import F129_BASE_HOLDOUT_RMSE, F129_STATIC_HOLDOUT_RMSE, _action_context, _fit, _predict, action_features
    from f130_shogi_rule_derived_structural_t1_augmentation import structural_features

from generic_chess.core.actions import action_is_board, action_is_drop, action_promotion_target_id, action_source_square, action_target_square
from generic_chess.core.identity import position_identity_key
from generic_chess.core.semantic_executor import semantic_engine_for, semantic_public_actions
from generic_chess.core.transition import apply_action
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


FAMILY = "standard_shogi"
BASELINE = "e361228eeb8dcbbc54d0ea6d850059b2e3113d62"
F131_TOP1 = 0.3937007874015748
F131_PAIRWISE = 0.6961452971418344
F131_NREGRET = 0.14638599860007367
F131_POOLED_RMSE = 2152.230646928496
ORACLE_HASH = "dda316e263a8f6e5a12678199e87cbedea7e4d40358d3087e8c78ddb3894a316"


def _write_progress(output: Path, stage: str, payload: dict) -> None:
    path = output.parent / f"{output.stem}.stage-{stage}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _family(name: str) -> str:
    if name.startswith("material_diff:"):
        return "material_board"
    if name.startswith("occupancy_diff:"):
        return "piece_square"
    if name == "mobility_diff":
        return "mobility"
    if name in {"king_escape_diff", "king_zone_pressure_diff", "current_check_diff"}:
        return "king_safety"
    if name.startswith("hand_diff:"):
        return "hand_inventory"
    if name == "promotion_potential_diff":
        return "promotion"
    if name.startswith("legal_drop_count_diff:") or name == "mean_legal_drop_mobility_diff":
        return "drop_opportunity"
    return "other"


def _rank(values: list[float], reference: list[float]) -> tuple[int, float, float]:
    order = sorted(range(len(values)), key=lambda index: (-values[index], index))
    ref_order = sorted(range(len(reference)), key=lambda index: (-reference[index], index))
    positions = {index: rank for rank, index in enumerate(order)}
    ref_positions = {index: rank for rank, index in enumerate(ref_order)}
    total = len(values) * (len(values) - 1) // 2
    pairs = sum((positions[left] < positions[right]) == (ref_positions[left] < ref_positions[right]) for left in range(len(values)) for right in range(left + 1, len(values)))
    return int(order[0] == ref_order[0]), pairs / total if total else 1.0, float(reference[ref_order[0]] - reference[order[0]])


def _corr(left: np.ndarray, right: np.ndarray, weights: np.ndarray | None = None) -> float:
    if len(left) < 2:
        return 0.0
    w = np.ones(len(left), dtype=np.float64) if weights is None else weights
    lm = np.sum(w * left) / np.sum(w)
    rm = np.sum(w * right) / np.sum(w)
    denom = float(np.sqrt(np.sum(w * (left - lm) ** 2) * np.sum(w * (right - rm) ** 2)))
    return float(np.sum(w * (left - lm) * (right - rm)) / denom) if denom else 0.0


def _spearman(left: np.ndarray, right: np.ndarray, weights: np.ndarray) -> float:
    return _corr(np.argsort(np.argsort(left, kind="mergesort"), kind="mergesort").astype(float), np.argsort(np.argsort(right, kind="mergesort"), kind="mergesort").astype(float), weights)


def _summary(predicted: np.ndarray, target: np.ndarray, weights: np.ndarray) -> dict:
    residual = predicted - target
    return {"rmse": float(np.sqrt(np.sum(weights * residual * residual) / np.sum(weights))), "mae": float(np.sum(weights * np.abs(residual)) / np.sum(weights)), "bias": float(np.sum(weights * residual) / np.sum(weights)), "standard_deviation": float(np.sqrt(np.sum(weights * (residual - np.sum(weights * residual) / np.sum(weights)) ** 2) / np.sum(weights))), "pearson_predicted_vs_true": _corr(predicted, target, weights), "spearman_predicted_vs_true": _spearman(predicted, target, weights)}


def _family_diagnostics(contributions: dict[str, np.ndarray], residual: np.ndarray, weights: np.ndarray) -> dict:
    result = {}
    for name, values in contributions.items():
        slope_denom = float(np.sum(weights * values * values))
        slope = float(np.sum(weights * values * residual) / slope_denom) if slope_denom else 0.0
        base_sse = float(np.sum(weights * (residual - np.sum(weights * residual) / np.sum(weights)) ** 2))
        fitted = slope * values
        new_sse = float(np.sum(weights * (residual - fitted - np.sum(weights * (residual - fitted)) / np.sum(weights)) ** 2))
        result[name] = {"contribution_rms": float(np.sqrt(np.sum(weights * values * values) / np.sum(weights))), "contribution_standard_deviation": float(np.sqrt(np.sum(weights * (values - np.sum(weights * values) / np.sum(weights)) ** 2) / np.sum(weights))), "pearson_residual": _corr(residual, values, weights), "spearman_residual": _spearman(residual, values, weights), "univariate_slope": slope, "incremental_r2": float((base_sse - new_sse) / base_sse) if base_sse else 0.0}
    return result


def _regime_report(rows: list[dict], indices: list[int], residual: np.ndarray, true: np.ndarray) -> dict:
    selected = [rows[index] for index in indices]
    values = residual[indices]
    targets = true[indices]
    return {"action_count": len(indices), "true_advantage_mean": float(np.mean(targets)) if len(targets) else 0.0, "true_advantage_standard_deviation": float(np.std(targets)) if len(targets) else 0.0, "residual_rmse": float(np.sqrt(np.mean(values * values))) if len(values) else 0.0, "residual_mae": float(np.mean(np.abs(values))) if len(values) else 0.0, "residual_bias": float(np.mean(values)) if len(values) else 0.0}


def _quartile_bins(values: np.ndarray) -> list[np.ndarray]:
    return [group for group in np.array_split(np.argsort(values, kind="mergesort"), 4)]


def _build_surface(compiled, base, output: Path) -> tuple[list[dict], dict, dict]:
    states, corpus = _collect_states(compiled, base)
    retained_states, eligibility_counts, retained_sha = _eligibility_map(states, compiled)
    selected_ordinals = _selected_ordinals()
    selected = {ordinal for values in selected_ordinals.values() for ordinal in values}
    selected_identity_sha = {split: _json_sha([row["identity"] for row in states if row["ordinal"] in selected_ordinals[split]]) for split in ("train", "dev", "holdout")}
    retained = [row for row in retained_states if row["ordinal"] in selected]
    counts = {split: sum(row["split"] == split for row in retained) for split in ("train", "dev", "holdout")}
    if corpus["full_identity_sha256"] != CORPUS_HASH or base.oracle_weight_sha256 != ORACLE_HASH or retained_sha != {"train": "74f9778dff9a2a5c08a6623d5452cdf2d15971cc20eab0c3e12a9c5d01d0a15b", "dev": "5c9d3acbc6adbd366c8c2b3739fe80b322e67a83e13b3eb1c1153871d70f0448", "holdout": "4238175784283f3338294290bb70b1330930a427a213f1a56223471b44d1d456"} or counts != RETAINED_COUNTS:
        raise RuntimeError("F132_FROZEN_SURFACE_IDENTITY_MISMATCH")
    rows = _materialize(retained, base)
    records, shard_info = _load_or_generate_shards(rows, base, compiled, output.parent / "f129-shogi-result.json")
    record_by_identity = {record["identity"]: record for record in records}
    action_rows = []
    for root in rows:
        record = record_by_identity[root["identity"]]
        scores = {entry["action"]: float(entry["score"]) for entry in record["action_spectrum"]}
        actions = sorted(semantic_public_actions(semantic_engine_for(compiled), root["state"].position), key=str)
        if set(scores) != {str(action) for action in actions}:
            raise RuntimeError("F132_ACTION_SPECTRUM_ACTION_SET_MISMATCH")
        context = _action_context(root["state"], compiled)
        root_features = structural_features(root["state"], compiled)
        for action in actions:
            action_key = str(action)
            action_rows.append({"root_identity": root["identity"], "split": root["split"], "action": action_key, "action_obj": action, "root_state": root["state"], "q": scores[action_key], "v_star": float(root["direct_oracle"]), "target": scores[action_key] - float(root["direct_oracle"]), "weight": 1.0 / len(actions), "features": action_features(root["state"], action, compiled, root_features, context).tolist()})
    return action_rows, {"corpus": corpus, "eligibility_counts": eligibility_counts, "retained_sha": retained_sha, "selected_identity_sha": selected_identity_sha, "counts": counts}, shard_info


def _run(output: Path) -> dict:
    started = time.time()
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    base = FrozenBasis(FAMILY, compiled)
    rows, surface, shard_info = _build_surface(compiled, base, output)
    fit = _fit(rows, [row["target"] for row in rows])
    pack = fit["pack"]
    predictions = np.concatenate([_predict(fit["matched"], pack, split) for split in ("train", "dev", "holdout")])
    true = np.asarray([row["target"] for row in rows], dtype=np.float64)
    holdout_indices = [index for index, row in enumerate(rows) if row["split"] == "holdout"]
    holdout_weights = np.asarray([rows[index]["weight"] for index in holdout_indices], dtype=np.float64)
    holdout_true = true[holdout_indices]
    holdout_pred = predictions[holdout_indices]
    root_groups: dict[str, list[int]] = {}
    for index in holdout_indices:
        root_groups.setdefault(rows[index]["root_identity"], []).append(index)
    root_info = {identity: group for identity, group in root_groups.items()}
    teacher_top1 = []
    pairwise = []
    regrets = []
    top2_gaps = []
    predicted_t1 = {}
    teacher_t1 = {}
    wrong_roots = []
    for identity, group in root_info.items():
        reference = [rows[index]["q"] for index in group]
        predicted = [predictions[index] for index in group]
        top, pair, regret = _rank(predicted, reference)
        teacher_top1.append(top); pairwise.append(pair); regrets.append(regret)
        order = sorted(range(len(reference)), key=lambda j: (-reference[j], j))
        top2_gaps.append(float(reference[order[0]] - reference[order[1]]) if len(order) > 1 else 0.0)
        predicted_t1[identity] = rows[group[0]]["v_star"] + max(predicted)
        teacher_t1[identity] = max(reference)
        if not top:
            wrong_roots.append((identity, group, order[0], int(np.argmax(predicted))))
    holdout_root_ids = list(root_info)
    pooled_rmse = float(np.sqrt(np.mean([(predicted_t1[key] - teacher_t1[key]) ** 2 for key in holdout_root_ids])))
    reproduction = {"top1": float(np.mean(teacher_top1)), "pairwise": float(np.mean(pairwise)), "mean_normalized_teacher_regret": float(np.mean(regrets) / (float(np.std(list(teacher_t1.values()))) or 1.0)), "max_pooled_t1_rmse": pooled_rmse, "pass": abs(float(np.mean(teacher_top1)) - F131_TOP1) <= 1e-10 and abs(float(np.mean(pairwise)) - F131_PAIRWISE) <= 1e-10 and abs(float(np.mean(regrets) / (float(np.std(list(teacher_t1.values()))) or 1.0)) - F131_NREGRET) <= 1e-10 and abs(pooled_rmse - F131_POOLED_RMSE) <= 1e-6}
    _write_progress(output, "f131-reproduction", reproduction)
    if not reproduction["pass"]:
        return {"schema": "F132_SHOGI_ACTION_RESIDUAL_CAUSAL_DECOMPOSITION_V1", "classification": "F132_F131_REPRODUCTION_FAILURE", "reproduction": reproduction, "runtime_seconds": time.time() - started}

    families = {}
    for index, name in enumerate(base.names):
        families.setdefault(_family(name), []).append(index)
    deltas = []
    contribution_rows = []
    for row in rows:
        root_phi = base.vector(row["root_state"])
        child = apply_action(row["root_state"], row["action_obj"], compiled)
        delta = -base.vector(child) - root_phi
        exact = float(delta @ np.asarray(base.weights, dtype=np.float64))
        if abs(exact - row["target"]) > 1e-9:
            return {"schema": "F132_SHOGI_ACTION_RESIDUAL_CAUSAL_DECOMPOSITION_V1", "classification": "F132_ORACLE_ADVANTAGE_RECOMPOSITION_FAILURE", "failed_action": row["action"], "recomposition_error": exact - row["target"], "runtime_seconds": time.time() - started}
        deltas.append(delta.tolist())
        contribution_rows.append({family: float(delta[indices] @ np.asarray([base.weights[index] for index in indices], dtype=np.float64)) for family, indices in families.items()})
    delta_matrix = np.asarray(deltas, dtype=np.float64)
    contributions = {family: np.asarray([row.get(family, 0.0) for row in contribution_rows], dtype=np.float64) for family in families}
    residual = predictions - true
    family_report = _family_diagnostics({family: values[holdout_indices] for family, values in contributions.items()}, residual[holdout_indices], holdout_weights)
    overall = _summary(holdout_pred, holdout_true, holdout_weights)

    regimes = {"quiet_board_move": [], "direct_capture": [], "non_capture_promotion": [], "capture_plus_promotion": [], "drop": [], "leap_geometry": [], "ray_geometry": [], "target_friendly_controlled_before": [], "target_enemy_controlled_before": []}
    for index, row in enumerate(rows):
        if row["split"] != "holdout":
            continue
        action = row["action_obj"]
        is_capture = bool(row["features"][18])
        is_promotion = bool(row["features"][17])
        is_drop = action_is_drop(action)
        is_quiet = not is_capture and not is_promotion and not is_drop
        if is_quiet: regimes["quiet_board_move"].append(index)
        if is_capture and not is_promotion: regimes["direct_capture"].append(index)
        if is_promotion and not is_capture: regimes["non_capture_promotion"].append(index)
        if is_promotion and is_capture: regimes["capture_plus_promotion"].append(index)
        if is_drop: regimes["drop"].append(index)
        if row["features"][13]: regimes["leap_geometry"].append(index)
        if row["features"][14]: regimes["ray_geometry"].append(index)
        if row["features"][29]: regimes["target_friendly_controlled_before"].append(index)
        if row["features"][30]: regimes["target_enemy_controlled_before"].append(index)
    regime_report = {name: _regime_report(rows, indices, residual, true) for name, indices in regimes.items()}
    actor_values = np.asarray([row["features"][21] for row in rows], dtype=np.float64)
    captured_values = np.asarray([row["features"][22] for row in rows], dtype=np.float64)
    enemy_anchor = np.asarray([row["features"][32] for row in rows], dtype=np.float64)
    root_counts = np.asarray([len(root_info.get(row["root_identity"], ())) for row in rows], dtype=np.float64)
    for label, values in (("captured_structural_value_quartile", captured_values), ("actor_structural_value_quartile", actor_values), ("target_enemy_anchor_proximity_quartile", enemy_anchor), ("root_legal_action_count_quartile", root_counts)):
        bins = _quartile_bins(values[holdout_indices])
        regime_report[label] = {str(q + 1): _regime_report(rows, [holdout_indices[i] for i in group], residual, true) for q, group in enumerate(bins)}

    margin_records = []
    for identity, group, teacher_local, predicted_local in wrong_roots:
        teacher_index = group[teacher_local]; predicted_index = group[predicted_local]
        margin_contrib = {family: float(values[teacher_index] - values[predicted_index]) for family, values in contributions.items()}
        margin = float(true[teacher_index] - true[predicted_index])
        teacher_features = rows[teacher_index]["features"]
        teacher_kinds = []
        if teacher_features[18]:
            teacher_kinds.append("capture")
        if teacher_features[17]:
            teacher_kinds.append("promotion")
        if teacher_features[1]:
            teacher_kinds.append("drop")
        if not teacher_kinds:
            teacher_kinds.append("quiet_move")
        margin_records.append({"root_identity": identity, "margin": margin, "contributions": margin_contrib, "teacher_action": rows[teacher_index]["action"], "predicted_action": rows[predicted_index]["action"], "teacher_kinds": teacher_kinds})
    margin_families = list(families)
    wrong_margins = np.asarray([row["margin"] for row in margin_records], dtype=np.float64)
    teacher_vs_predicted = {"wrong_top1_roots": len(margin_records), "margin_mean": float(np.mean(wrong_margins)) if len(wrong_margins) else 0.0, "margin_median": float(np.median(wrong_margins)) if len(wrong_margins) else 0.0, "margin_p95": float(np.percentile(wrong_margins, 95)) if len(wrong_margins) else 0.0, "families": {family: {"mean_signed_margin_contribution": float(np.mean([row["contributions"][family] for row in margin_records])) if margin_records else 0.0, "mean_absolute_margin_contribution": float(np.mean([abs(row["contributions"][family]) for row in margin_records])) if margin_records else 0.0, "largest_positive_fraction": float(np.mean([max(row["contributions"], key=row["contributions"].get) == family for row in margin_records])) if margin_records else 0.0, "over_50_percent_positive_fraction": float(np.mean([row["contributions"][family] > 0.5 * sum(max(0.0, value) for value in row["contributions"].values()) for row in margin_records])) if margin_records else 0.0} for family in margin_families}}
    teacher_vs_predicted["by_teacher_best_kind"] = {}
    for kind in ("capture", "promotion", "drop", "quiet_move"):
        selected = [row for row in margin_records if kind in row["teacher_kinds"]]
        teacher_vs_predicted["by_teacher_best_kind"][kind] = {"count": len(selected), "mean_margin": float(np.mean([row["margin"] for row in selected])) if selected else 0.0}

    gap_values = np.asarray([top2_gaps[index] for index, identity in enumerate(holdout_root_ids)], dtype=np.float64)
    gap_quartiles = {}
    for quartile, group in enumerate(_quartile_bins(gap_values), 1):
        identities = {holdout_root_ids[index] for index in group}
        relevant = [item for item in margin_records if item["root_identity"] in identities]
        dominant = [max(item["contributions"], key=item["contributions"].get) for item in relevant]
        gap_quartiles[str(quartile)] = {"roots": len(identities), "top1_agreement": float(np.mean([teacher_top1[holdout_root_ids.index(identity)] for identity in identities])), "pairwise_agreement": float(np.mean([pairwise[holdout_root_ids.index(identity)] for identity in identities])), "mean_regret": float(np.mean([regrets[holdout_root_ids.index(identity)] for identity in identities])), "mean_teacher_margin_on_failures": float(np.mean([item["margin"] for item in relevant])) if relevant else 0.0, "dominant_missed_contribution_family": {family: dominant.count(family) / len(dominant) for family in margin_families} if dominant else {}}

    train_indices = [index for index, row in enumerate(rows) if row["split"] == "train"]
    delta_mean = np.mean(delta_matrix[train_indices], axis=0)
    delta_scale = np.std(delta_matrix[train_indices], axis=0)
    standardized_delta = (delta_matrix - delta_mean) / np.where(delta_scale > 1e-12, delta_scale, 1.0)
    magnitude = np.linalg.norm(standardized_delta, axis=1)
    holdout_magnitude = magnitude[holdout_indices]
    abs_residual = np.abs(residual[holdout_indices])
    successor_report = {"abs_residual_vs_successor_change_pearson": _corr(abs_residual, holdout_magnitude, holdout_weights), "abs_residual_vs_successor_change_spearman": _spearman(abs_residual, holdout_magnitude, holdout_weights)}
    failed_by_root = {identity: any(item["root_identity"] == identity for item in margin_records) for identity in holdout_root_ids}
    max_magnitude = np.asarray([max(magnitude[index] for index in root_info[identity]) for identity in holdout_root_ids])
    successor_report["root_failure_vs_max_successor_change_pearson"] = _corr(np.asarray([failed_by_root[identity] for identity in holdout_root_ids], dtype=float), max_magnitude)
    successor_report["residual_rmse_by_successor_change_quartile"] = {str(q + 1): float(np.sqrt(np.mean(residual[[holdout_indices[i] for i in group]] ** 2))) for q, group in enumerate(_quartile_bins(holdout_magnitude))}

    local_families = {"material_board", "hand_inventory", "promotion"}
    global_families = {"piece_square", "mobility", "king_safety", "drop_opportunity", "other"}
    local_margins = np.asarray([sum(item["contributions"].get(family, 0.0) for family in local_families) for item in margin_records])
    global_margins = np.asarray([sum(item["contributions"].get(family, 0.0) for family in global_families) for item in margin_records])
    local_global = {"fraction_global_positive_margin_gt_local": float(np.mean(global_margins > local_margins)) if len(margin_records) else 0.0, "fraction_global_at_least_50_percent": float(np.mean(global_margins >= 0.5 * wrong_margins)) if len(margin_records) else 0.0, "mean_absolute_local_margin": float(np.mean(np.abs(local_margins))) if len(margin_records) else 0.0, "mean_absolute_global_margin": float(np.mean(np.abs(global_margins))) if len(margin_records) else 0.0}
    global_fraction = local_global["fraction_global_at_least_50_percent"]
    local_fraction = float(np.mean(local_margins >= 0.5 * wrong_margins)) if len(margin_records) else 0.0
    if global_fraction >= 0.60:
        classification = "F131_MISSING_GLOBAL_SUCCESSOR_STATE_INFORMATION_SUPPORTED"
    elif local_fraction >= 0.60:
        classification = "F131_LOCAL_ACTION_SEMANTICS_STILL_INSUFFICIENT"
    else:
        classification = "F131_RESIDUAL_CAUSE_MIXED"
    secondary_flags = []
    for family in margin_families:
        if teacher_vs_predicted["families"][family]["largest_positive_fraction"] >= 0.35:
            secondary_flags.append(family.upper() + "_RESIDUAL_DOMINANT")
    result = {"schema": "F132_SHOGI_ACTION_RESIDUAL_CAUSAL_DECOMPOSITION_V1", "baseline": BASELINE, "family": FAMILY, "reproduction": reproduction, "oracle_recomposition": {"action_count": len(rows), "family_names": margin_families, "max_abs_error": 0.0}, "overall_residual": overall, "family_diagnostics": family_report, "action_regimes": regime_report, "teacher_best_vs_f131_chosen": teacher_vs_predicted, "teacher_gap_quartiles": gap_quartiles, "successor_change_magnitude": successor_report, "local_vs_global_margin": local_global, "classification": classification, "secondary_flags": secondary_flags, "runtime_seconds": time.time() - started, "shards": shard_info, "surface": surface}
    _write_progress(output, "final", result)
    return result


def run(output: Path | None = None) -> dict:
    return _run(output or Path(".generic_chess_flow/f132-shogi-result.json"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": result["classification"], "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
