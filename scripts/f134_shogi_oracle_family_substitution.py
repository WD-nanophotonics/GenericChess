"""F134: counterfactual oracle-family substitution for frozen F131 action ranking."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import FrozenBasis, _json_sha, _scalar_metrics
    from scripts.f131_shogi_action_conditioned_t1_factorization import _action_ranking, _fit, _predict
    from scripts.f132_shogi_action_residual_causal_decomposition import _build_surface, _family, _write_progress
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import FrozenBasis, _json_sha, _scalar_metrics
    from f131_shogi_action_conditioned_t1_factorization import _action_ranking, _fit, _predict
    from f132_shogi_action_residual_causal_decomposition import _build_surface, _family, _write_progress

from generic_chess.core.transition import apply_action
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


FAMILY = "standard_shogi"
BASELINE = "8d0fcb06d0ee80476c936920f835a40943400e25"
F131_TOP1 = 0.3937007874015748
F131_PAIRWISE = 0.6961452971418344
F131_NREGRET = 0.14638599860007367
F131_T1_RMSE = 2152.230646928496
F133_HAND_TOP1 = 0.39763779527559057
F133_HAND_PAIRWISE = 0.6960334069523595
F133_HAND_NREGRET = 0.13581891875438187
F133_HAND_T1_RMSE = 2113.9505735718635
FAMILIES = ("material_board", "piece_square", "mobility", "king_safety", "hand_inventory", "promotion", "drop_opportunity", "other")


def _weighted_metrics(target: np.ndarray, prediction: np.ndarray, weights: np.ndarray, holdout_std: float) -> dict:
    total = float(np.sum(weights))
    mean_target = float(np.sum(weights * target) / total)
    error = prediction - target
    rmse = float(np.sqrt(np.sum(weights * error * error) / total))
    centered_target = target - mean_target
    centered_prediction = prediction - float(np.sum(weights * prediction) / total)
    denominator = float(np.sqrt(np.sum(weights * centered_target * centered_target) * np.sum(weights * centered_prediction * centered_prediction)))
    pearson = float(np.sum(weights * centered_target * centered_prediction) / denominator) if denominator else 0.0
    r2 = float(1.0 - np.sum(weights * error * error) / np.sum(weights * centered_target * centered_target)) if np.sum(weights * centered_target * centered_target) else 0.0
    target_order = np.argsort(target, kind="mergesort")
    prediction_order = np.argsort(prediction, kind="mergesort")
    target_rank = np.empty(len(target), dtype=np.float64); prediction_rank = np.empty(len(prediction), dtype=np.float64)
    target_rank[target_order] = np.arange(len(target), dtype=np.float64); prediction_rank[prediction_order] = np.arange(len(prediction), dtype=np.float64)
    target_rank -= np.sum(weights * target_rank) / total; prediction_rank -= np.sum(weights * prediction_rank) / total
    rank_denominator = float(np.sqrt(np.sum(weights * target_rank * target_rank) * np.sum(weights * prediction_rank * prediction_rank)))
    return {"weighted_rmse": rmse, "weighted_nrmse": rmse / holdout_std, "r2": r2, "pearson": pearson, "spearman": float(np.sum(weights * target_rank * prediction_rank) / rank_denominator) if rank_denominator else 0.0}


def _predictions(fit: dict, rows: list[dict]) -> np.ndarray:
    return np.concatenate([_predict(fit["matched"], fit["pack"], split) for split in ("train", "dev", "holdout")])


def _groups(rows: list[dict], split: str) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        if row["split"] == split:
            groups.setdefault(row["root_identity"], []).append(index)
    return groups


def _t1_metrics(rows: list[dict], predictions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    groups = _groups(rows, "holdout")
    teacher = np.asarray([max(rows[index]["q"] for index in group) for group in groups.values()], dtype=np.float64)
    predicted = np.asarray([rows[group[0]]["v_star"] + max(predictions[index] for index in group) for group in groups.values()], dtype=np.float64)
    return teacher, predicted


def _report(rows: list[dict], predictions: np.ndarray, holdout_std: float) -> dict:
    action = _action_ranking(rows, predictions, "holdout", holdout_std)
    teacher, predicted = _t1_metrics(rows, predictions)
    t1 = _scalar_metrics(teacher, predicted, holdout_std)
    return {"top1": action["top1_agreement"], "pairwise": action["pairwise_ordering_agreement"], "mean_regret": action["mean_teacher_regret"], "median_regret": action["median_teacher_regret"], "p95_regret": action["p95_teacher_regret"], "normalized_regret": action["mean_normalized_teacher_regret"], "by_teacher_gap_quartile": action["by_teacher_gap_quartile"], "t1_rmse": t1["rmse_oracle_units"], "t1_nrmse": t1["normalized_rmse"], "t1_r2": t1["r2"], "t1_pearson": t1["pearson"], "t1_spearman": t1["spearman"], "t1_max_abs_error": t1["max_abs_error"]}


def _delta_features(rows: list[dict], labels: np.ndarray) -> list[dict]:
    result = []
    for index, row in enumerate(rows):
        copied = dict(row)
        copied["features"] = row["features"]
        result.append(copied)
    return result


def _run(output: Path) -> dict:
    started = time.time()
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    base = FrozenBasis(FAMILY, compiled)
    rows, surface, shard_info = _build_surface(compiled, base, output)
    family_indices = {family: [] for family in FAMILIES}
    for index, name in enumerate(base.names):
        family_indices.setdefault(_family(name), []).append(index)
    contributions = {family: [] for family in FAMILIES}
    named_contributions = {family: [] for family in FAMILIES}
    authoritative_hand = []
    max_error = 0.0
    for row in rows:
        root_phi = base.vector(row["root_state"])
        child = apply_action(row["root_state"], row["action_obj"], compiled)
        delta = -base.vector(child) - root_phi
        max_error = max(max_error, abs(float(delta @ np.asarray(base.weights)) - row["target"]))
        for family in FAMILIES:
            indices = family_indices[family]
            value = float(delta[indices] @ np.asarray([base.weights[index] for index in indices])) if indices else 0.0
            contributions[family].append(value)
            named_contributions[family].append(value)
        root_side = row["root_state"].position.side_to_move
        child_position = child.position
        hand_value = 0.0
        for type_id in base.hand_types:
            weight_index = base.names.index(f"hand_diff:{type_id}")
            hand_value += base.weights[weight_index] * ((child_position.hands[root_side].count(type_id) - row["root_state"].position.hands[root_side].count(type_id)) - (child_position.hands[1 - root_side].count(type_id) - row["root_state"].position.hands[1 - root_side].count(type_id)))
        authoritative_hand.append(float(hand_value))
    contribution_arrays = {family: np.asarray(values, dtype=np.float64) for family, values in contributions.items()}
    named_contribution_arrays = {family: np.asarray(values, dtype=np.float64) for family, values in named_contributions.items()}
    contribution_arrays["hand_inventory"] = np.asarray(authoritative_hand, dtype=np.float64)
    residual_other = np.asarray([row["target"] for row in rows], dtype=np.float64) - sum((contribution_arrays[family] for family in FAMILIES if family not in {"hand_inventory", "other"}), np.zeros(len(rows), dtype=np.float64)) - contribution_arrays["hand_inventory"]
    contribution_arrays["other"] = residual_other
    exact_check = {"max_abs_error": float(max_error), "pass": max_error <= 1e-9, "action_count": len(rows)}
    hashes = {split: {family: _json_sha(contribution_arrays[family][[index for index, row in enumerate(rows) if row["split"] == split]].tolist()) for family in FAMILIES} for split in ("train", "dev", "holdout")}
    named_hashes = {split: {family: _json_sha(named_contribution_arrays[family][[index for index, row in enumerate(rows) if row["split"] == split]].tolist()) for family in FAMILIES} for split in ("train", "dev", "holdout")}
    if not exact_check["pass"]:
        return {"schema": "F134_SHOGI_ORACLE_FAMILY_SUBSTITUTION_V1", "classification": "F134_EXACT_DECOMPOSITION_DECISION_SANITY_FAILURE", "exact_decomposition": exact_check, "runtime_seconds": time.time() - started}

    true = np.asarray([row["target"] for row in rows], dtype=np.float64)
    weights = np.asarray([row["weight"] for row in rows], dtype=np.float64)
    holdout_indices = np.asarray([index for index, row in enumerate(rows) if row["split"] == "holdout"], dtype=int)
    holdout_std = float(np.std(np.asarray([max(rows[item]["q"] for item in group) for group in _groups(rows, "holdout").values()]))) or 1.0
    baseline_fit = _fit(rows, true.tolist())
    baseline_predictions = _predictions(baseline_fit, rows)
    baseline_report = _report(rows, baseline_predictions, holdout_std)

    hand_fit = _fit(rows, (true - contribution_arrays["hand_inventory"]).tolist())
    hand_report = _report(rows, _predictions(hand_fit, rows) + contribution_arrays["hand_inventory"], holdout_std)
    reproduction = {"f131": baseline_report, "hand_exact_control": hand_report, "pass": abs(baseline_report["top1"] - F131_TOP1) <= 1e-10 and abs(baseline_report["pairwise"] - F131_PAIRWISE) <= 1e-10 and abs(baseline_report["normalized_regret"] - F131_NREGRET) <= 1e-10 and abs(baseline_report["t1_rmse"] - F131_T1_RMSE) <= 1e-6 and abs(hand_report["top1"] - F133_HAND_TOP1) <= 1e-10 and abs(hand_report["pairwise"] - F133_HAND_PAIRWISE) <= 1e-10 and abs(hand_report["normalized_regret"] - F133_HAND_NREGRET) <= 1e-10 and abs(hand_report["t1_rmse"] - F133_HAND_T1_RMSE) <= 1e-6}
    _write_progress(output, "frozen-controls", reproduction)
    if not reproduction["pass"]:
        return {"schema": "F134_SHOGI_ORACLE_FAMILY_SUBSTITUTION_V1", "classification": "F134_FROZEN_CONTROL_REPRODUCTION_FAILURE", "reproduction": reproduction, "runtime_seconds": time.time() - started}

    learnability = {}
    for family in FAMILIES:
        fit = _fit(rows, contribution_arrays[family].tolist())
        predictions = _predictions(fit, rows)
        metrics = {}
        holdout_family_std = float(np.std(contribution_arrays[family][holdout_indices])) or 1.0
        for split in ("train", "dev", "holdout"):
            indices = np.asarray([index for index, row in enumerate(rows) if row["split"] == split], dtype=int)
            metrics[split] = _weighted_metrics(contribution_arrays[family][indices], predictions[indices], weights[indices], holdout_family_std)
        values = contribution_arrays[family][holdout_indices]
        mean = float(np.sum(weights[holdout_indices] * values) / np.sum(weights[holdout_indices]))
        learnability[family] = {"metrics": metrics, "holdout_contribution_rms": float(np.sqrt(np.sum(weights[holdout_indices] * values * values) / np.sum(weights[holdout_indices]))), "holdout_contribution_std": float(np.sqrt(np.sum(weights[holdout_indices] * (values - mean) ** 2) / np.sum(weights[holdout_indices]))), "holdout_total_advantage_variance_fraction": float(np.sum(weights[holdout_indices] * values * values) / np.sum(weights[holdout_indices] * true[holdout_indices] * true[holdout_indices]))}

    interventions = {}
    for name, members in [(family, (family,)) for family in FAMILIES] + [("LOCAL", ("material_board", "hand_inventory", "promotion")), ("GLOBAL", ("piece_square", "mobility", "king_safety", "drop_opportunity", "other"))]:
        exact = np.sum([contribution_arrays[family] for family in members], axis=0)
        fit = _fit(rows, (true - exact).tolist())
        report = _report(rows, _predictions(fit, rows) + exact, holdout_std)
        interventions[name] = {"families": list(members), "metrics": report, "delta_top1": report["top1"] - F131_TOP1, "delta_pairwise": report["pairwise"] - F131_PAIRWISE, "relative_regret_reduction": (F131_NREGRET - report["normalized_regret"]) / F131_NREGRET, "t1_rmse_reduction": F131_T1_RMSE - report["t1_rmse"]}

    exact_action = _action_ranking(rows, np.asarray([row["q"] for row in rows], dtype=np.float64), "holdout", holdout_std)
    exact_teacher, exact_predicted = _t1_metrics(rows, true)
    exact_t1 = _scalar_metrics(exact_teacher, exact_predicted, holdout_std)
    exact_sanity = {"top1": exact_action["top1_agreement"], "pairwise": exact_action["pairwise_ordering_agreement"], "regret": exact_action["mean_teacher_regret"], "max_pooled_t1_rmse": exact_t1["rmse_oracle_units"], "pass": exact_action["top1_agreement"] == 1.0 and exact_action["pairwise_ordering_agreement"] == 1.0 and abs(exact_action["mean_teacher_regret"]) <= 1e-9 and exact_t1["rmse_oracle_units"] <= 1e-9}
    if not exact_sanity["pass"]:
        result = {"schema": "F134_SHOGI_ORACLE_FAMILY_SUBSTITUTION_V1", "classification": "F134_EXACT_DECOMPOSITION_DECISION_SANITY_FAILURE", "reproduction": reproduction, "family_contribution_sha256": hashes, "named_f132_family_contribution_sha256": named_hashes, "learnability": learnability, "interventions": interventions, "exact_sanity": exact_sanity, "runtime_seconds": time.time() - started}
        _write_progress(output, "exact-sanity", result)
        return result
    strong = [family for family in FAMILIES if interventions[family]["delta_top1"] >= 0.15 and interventions[family]["relative_regret_reduction"] >= 0.40]
    moderate = [family for family in FAMILIES if family not in strong and (interventions[family]["delta_top1"] >= 0.05 or interventions[family]["relative_regret_reduction"] >= 0.20)]
    sufficient = [family for family in FAMILIES if interventions[family]["metrics"]["top1"] >= 0.90 and interventions[family]["metrics"]["pairwise"] >= 0.95 and interventions[family]["metrics"]["normalized_regret"] <= 0.05]
    local_strong = interventions["LOCAL"]["delta_top1"] >= 0.20 and interventions["LOCAL"]["relative_regret_reduction"] >= 0.50
    global_strong = interventions["GLOBAL"]["delta_top1"] >= 0.20 and interventions["GLOBAL"]["relative_regret_reduction"] >= 0.50
    if sufficient:
        classification = "SINGLE_ORACLE_FAMILY_SUFFICIENT_FOR_ACTION_RECOVERY"
    elif len(strong) == 1 and all(interventions[strong[0]]["delta_top1"] - interventions[family]["delta_top1"] >= 0.05 for family in FAMILIES if family != strong[0]):
        classification = "SINGLE_FAMILY_CAUSAL_BOTTLENECK_SUPPORTED"
    elif local_strong and interventions["LOCAL"]["metrics"]["top1"] - interventions["GLOBAL"]["metrics"]["top1"] >= 0.10:
        classification = "LOCAL_MULTIFAMILY_ACTION_SEMANTICS_BOTTLENECK_SUPPORTED"
    elif global_strong and interventions["GLOBAL"]["metrics"]["top1"] - interventions["LOCAL"]["metrics"]["top1"] >= 0.10:
        classification = "GLOBAL_MULTIFAMILY_STATE_INFORMATION_BOTTLENECK_SUPPORTED"
    elif local_strong or global_strong:
        classification = "DISTRIBUTED_MULTIFAMILY_REPRESENTATION_BOTTLENECK_SUPPORTED"
    else:
        classification = "F131_ACTION_FAILURE_NOT_EXPLAINED_BY_SINGLE_OR_LOCAL_GLOBAL_ORACLE_SUBSTITUTION"
    result = {"schema": "F134_SHOGI_ORACLE_FAMILY_SUBSTITUTION_V1", "baseline": BASELINE, "reproduction": reproduction, "exact_decomposition": exact_check, "family_contribution_sha256": hashes, "named_f132_family_contribution_sha256": named_hashes, "learnability": learnability, "interventions": interventions, "exact_sanity": exact_sanity, "causal_labels": {"strong": strong, "moderate": moderate, "single_family_action_gate_sufficient": sufficient, "local_strong_repair": local_strong, "global_strong_repair": global_strong}, "classification": classification, "runtime_seconds": time.time() - started, "shards": shard_info, "surface": surface}
    _write_progress(output, "final", result)
    return result


def run(output: Path | None = None) -> dict:
    return _run(output or Path(".generic_chess_flow/f134-shogi-result.json"))


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True)
    result = run(parser.parse_args().output)
    print(json.dumps({"classification": result.get("classification"), "runtime_seconds": result.get("runtime_seconds")}, sort_keys=True))


if __name__ == "__main__":
    main()
