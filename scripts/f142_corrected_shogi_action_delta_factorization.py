"""F142: exact corrected Shogi transition-delta action factorization."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import _json_sha, _scalar_metrics, _sort_actions
    from scripts.f123_reverse_benchmark_identifiability_optimizer_diagnosis import _predict
    from scripts.f135_corrected_shogi_oracle_schema_rebaseline import CorrectedShogiFrozenBasisV2
    from scripts.f138_corrected_shogi_targeted_gauge_coverage_a1 import _fit_report
    from scripts.f141_corrected_shogi_known_oracle_t1_compression import BASELINE as F141_BASELINE, CORRECTED_ORACLE_SHA, FEATURE_NAME_SHA, SHARD_SCHEMA, _reproduce_f140
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import _json_sha, _scalar_metrics, _sort_actions
    from f123_reverse_benchmark_identifiability_optimizer_diagnosis import _predict
    from f135_corrected_shogi_oracle_schema_rebaseline import CorrectedShogiFrozenBasisV2
    from f138_corrected_shogi_targeted_gauge_coverage_a1 import _fit_report
    from f141_corrected_shogi_known_oracle_t1_compression import BASELINE as F141_BASELINE, CORRECTED_ORACLE_SHA, FEATURE_NAME_SHA, SHARD_SCHEMA, _reproduce_f140

from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


BASELINE = "576a14430b512a15f90e1368f59263ab3334e989"
RAW_WIDTH = 1086
L2 = 1e-6
RESIDUAL_TOLERANCE = 1e-12


def _weighted_pack(rows, target_rows, weights, basis, direct_pack):
    raw = {split: np.asarray(rows[split], dtype=np.float64) for split in rows}
    target_raw = {split: np.asarray(target_rows[split], dtype=np.float64) for split in rows}
    weight = {split: np.asarray(weights[split], dtype=np.float64) for split in rows}
    train_w = weight["train"]; total_w = float(train_w.sum())
    mean = np.sum(raw["train"] * train_w[:, None], axis=0) / total_w
    variance = np.sum(((raw["train"] - mean) ** 2) * train_w[:, None], axis=0) / total_w
    scale = np.sqrt(variance); active = scale > 1e-12; safe_scale = np.where(active, scale, 1.0)
    target_mean = float(np.sum(target_raw["train"] * train_w) / total_w)
    target_variance = float(np.sum(((target_raw["train"] - target_mean) ** 2) * train_w) / total_w)
    target_std = float(np.sqrt(target_variance)) or 1.0
    normalized = {split: (raw[split] - mean) / safe_scale for split in rows}
    design = {split: np.column_stack([normalized[split][:, active], np.ones(len(raw[split]))]) for split in rows}
    target = {split: (target_raw[split] - target_mean) / target_std for split in rows}
    weighted_design = design["train"] * np.sqrt(train_w)[:, None]
    left, singular, vt = np.linalg.svd(weighted_design, full_matrices=False)
    tolerance = np.finfo(float).eps * max(weighted_design.shape) * float(singular[0])
    return {"raw": raw, "oracle": target_raw, "weights": weight, "feature_mean": mean, "feature_scale": safe_scale, "active": active, "target_mean": target_mean, "target_std": target_std, "normalized": normalized, "design": design, "target": target, "weighted_design": weighted_design, "singular_values": singular, "left_vectors": left, "vt": vt, "rank_tol": tolerance, "retained": singular > tolerance, "feature_count": len(basis.names), "constant_feature_names": [name for name, keep in zip(basis.names, active) if not keep], "direct_pack": direct_pack}


def _normal_system(pack):
    design = pack["design"]["train"]; target = pack["target"]["train"]; weights = pack["weights"]["train"]; total = float(weights.sum())
    hessian = (design.T * weights) @ design / total; hessian[:-1, :-1] += L2 * np.eye(hessian.shape[0] - 1)
    rhs = (design.T * weights) @ target / total
    return hessian, rhs


def _objective(model, pack):
    residual = pack["design"]["train"] @ model - pack["target"]["train"]; weights = pack["weights"]["train"]; total = float(weights.sum())
    return float(0.5 * np.sum(weights * residual * residual) / total + 0.5 * L2 * np.sum(model[:-1] * model[:-1]))


def _solve(pack):
    hessian, rhs = _normal_system(pack); diagonal = np.diag(hessian); inverse = 1.0 / diagonal; theta = np.zeros(len(rhs), dtype=np.float64); residual = rhs.copy(); direction = inverse * residual; rz = float(residual @ direction); denominator = max(float(np.linalg.norm(rhs)), 1e-30); relative = float(np.linalg.norm(residual) / denominator); iterations = 0
    for iteration in range(1, 8 * len(rhs) + 1):
        if relative <= RESIDUAL_TOLERANCE: break
        curvature = float(direction @ (hessian @ direction))
        step = rz / curvature; theta += step * direction; residual -= step * (hessian @ direction); iterations = iteration; relative = float(np.linalg.norm(residual) / denominator)
        if relative <= RESIDUAL_TOLERANCE: break
        next_preconditioned = inverse * residual; next_rz = float(residual @ next_preconditioned); direction = next_preconditioned + (next_rz / rz) * direction; rz = next_rz
    matched = np.linalg.solve(hessian, rhs)
    diff = {split: pack["target_std"] * (pack["design"][split] @ (theta - matched)) for split in ("train", "dev", "holdout")}
    holdout_std = float(np.sqrt(np.sum(pack["weights"]["holdout"] * (pack["oracle"]["holdout"] - np.average(pack["oracle"]["holdout"], weights=pack["weights"]["holdout"])) ** 2) / pack["weights"]["holdout"].sum())) or 1.0
    numerical = {"finite_parameters": bool(np.all(np.isfinite(theta))), "relative_residual": relative, "iterations": iterations, "maximum_iterations": 8 * len(rhs), "objective_excess": _objective(theta, pack) - _objective(matched, pack), "prediction_difference_holdout_normalized_rmse": float(np.sqrt(np.average(diff["holdout"] ** 2, weights=pack["weights"]["holdout"])) / holdout_std)}
    numerical["pass"] = bool(numerical["finite_parameters"] and numerical["relative_residual"] <= 1e-10 and numerical["objective_excess"] <= 1e-10 and numerical["prediction_difference_holdout_normalized_rmse"] <= 1e-8)
    return theta, matched, numerical


def _predict_pack(model, pack, split):
    return pack["target_mean"] + pack["target_std"] * (pack["design"][split] @ model)


def _weighted_metrics(y, pred, weights, normalization):
    y = np.asarray(y, dtype=np.float64); pred = np.asarray(pred, dtype=np.float64); weights = np.asarray(weights, dtype=np.float64); total = float(weights.sum()); mean_y = float(np.sum(weights * y) / total); mean_p = float(np.sum(weights * pred) / total); err = pred - y; var_y = float(np.sum(weights * (y - mean_y) ** 2) / total); var_p = float(np.sum(weights * (pred - mean_p) ** 2) / total); covariance = float(np.sum(weights * (y - mean_y) * (pred - mean_p)) / total); rank_y = np.argsort(np.argsort(y, kind="mergesort"), kind="mergesort").astype(float); rank_p = np.argsort(np.argsort(pred, kind="mergesort"), kind="mergesort").astype(float); rank_cov = float(np.sum(weights * (rank_y - np.average(rank_y, weights=weights)) * (rank_p - np.average(rank_p, weights=weights))) / total); rank_var_y = float(np.sum(weights * (rank_y - np.average(rank_y, weights=weights)) ** 2) / total); rank_var_p = float(np.sum(weights * (rank_p - np.average(rank_p, weights=weights)) ** 2) / total)
    return {"rmse_oracle_units": float(np.sqrt(np.sum(weights * err * err) / total)), "normalized_rmse": float(np.sqrt(np.sum(weights * err * err) / total) / normalization), "r2": float(1.0 - np.sum(weights * err * err) / np.sum(weights * (y - mean_y) ** 2)) if var_y else 0.0, "pearson": covariance / np.sqrt(var_y * var_p) if var_y and var_p else 0.0, "spearman": rank_cov / np.sqrt(rank_var_y * rank_var_p) if rank_var_y and rank_var_p else 0.0, "sign_agreement_nonzero": float(np.sum(weights[y != 0] * (np.sign(y[y != 0]) == np.sign(pred[y != 0]))) / np.sum(weights[y != 0])) if np.any(y != 0) else 1.0, "max_abs_error": float(np.max(np.abs(err)))}


def _load_rows(result_path, shard_root, surface, basis, compiled):
    result = json.loads(result_path.read_text(encoding="utf-8")); f141 = result["shards"]
    if result.get("baseline") != F141_BASELINE or f141["schema"] != SHARD_SCHEMA or f141["shard_size"] != 128 or f141["shard_count"] != 37 or f141["total_action_rows"] != 200747 or f141["unique_child_identities"] != 200678 or f141["duplicate_child_reuse_count"] != 69 or abs(result["t1_fit"]["metrics"]["holdout"]["normalized_rmse"] - 1.8302864928571427) > 1e-12:
        raise RuntimeError("F142_F141_REPRODUCTION_FAILURE")
    by_id = {row["identity"]: row for split in surface for row in surface[split]}; rows = {"train": [], "dev": [], "holdout": []}; root_records = {"train": [], "dev": [], "holdout": []}; child_ids = set(); action_count = 0
    for manifest in f141["manifests"]:
        path = Path(manifest["path"])
        if not path.is_absolute(): path = shard_root / path.name
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["sha256"]: raise RuntimeError("F142_F141_SHARD_HASH_MISMATCH")
        shard = json.loads(path.read_text(encoding="utf-8"))
        if shard["schema"] != SHARD_SCHEMA or shard["corrected_oracle_sha"] != CORRECTED_ORACLE_SHA or shard["feature_name_sha"] != FEATURE_NAME_SHA: raise RuntimeError("F142_F141_SHARD_CONTRACT_MISMATCH")
        split = shard["split"]
        for record in shard["roots"]:
            root = by_id.get(record["root_identity"])
            if root is None: raise RuntimeError("F142_ROOT_IDENTITY_MISMATCH")
            actions = {str(action): action for action in _sort_actions(legal_actions(root["state"], compiled))}
            if len(actions) != record["legal_action_count"]: raise RuntimeError("F142_LEGAL_ACTION_COUNT_MISMATCH")
            delta_list = []; target_list = []; action_list = []
            root_features = np.asarray(root["features"], dtype=np.float64); root_value = float(root["oracle"])
            if abs(root_value - record["direct_corrected_value"]) > 1e-9: raise RuntimeError("F142_ROOT_VALUE_MISMATCH")
            for item in record["action_spectrum"]:
                action = actions.get(item["action"])
                if action is None: raise RuntimeError("F142_ACTION_IDENTITY_MISMATCH")
                child = apply_action(root["state"], action, compiled); child_id = str(position_identity_key(child.position, compiled)); child_ids.add(child_id); action_count += 1
                if child_id != item["child_identity"]: raise RuntimeError("F142_CHILD_IDENTITY_MISMATCH")
                child_features = basis.vector(child); q = float(-basis.oracle(child_features))
                if abs(q - float(item["q1"])) > 1e-9: raise RuntimeError("F142_F141_Q_MISMATCH")
                delta = -child_features - root_features; target = q - root_value
                delta_list.append(delta); target_list.append(target); action_list.append({"action": item["action"], "q1": q, "target": target})
            root_records[split].append({"identity": record["root_identity"], "direct_value": root_value, "t1": float(record["exact_t1"]), "gap": float(record["teacher_top2_gap"]), "actions": action_list, "deltas": delta_list, "targets": target_list})
    if action_count != 200747 or len(child_ids) != 200678 or {split: len(root_records[split]) for split in root_records} != {"train": 3109, "dev": 731, "holdout": 750}: raise RuntimeError("F142_F141_REPRODUCTION_FAILURE")
    for split in root_records:
        for record in root_records[split]:
            rows[split].extend(record["deltas"]); record["deltas"] = np.asarray(record["deltas"], dtype=np.float64); record["targets"] = np.asarray(record["targets"], dtype=np.float64)
    return root_records, rows, {"action_rows": action_count, "unique_child_identities": len(child_ids), "duplicate_child_reuse": action_count - len(child_ids)}


def _ranking(records, predictions, holdout_t1_std):
    report = {}
    for split in records:
        top = pair = pairs = top3 = 0; mrr = []; regret = []
        for record, predicted in zip(records[split], predictions[split]):
            exact = np.asarray([item["q1"] for item in record["actions"]]); exact_order = sorted(range(len(exact)), key=lambda i: (-exact[i], record["actions"][i]["action"])); pred_order = sorted(range(len(exact)), key=lambda i: (-predicted[i], record["actions"][i]["action"])); top += int(exact_order[0] == pred_order[0]); top3 += int(exact_order[0] in pred_order[:3]); mrr.append(1.0 / (pred_order.index(exact_order[0]) + 1)); regret.append(float(exact[exact_order[0]] - exact[pred_order[0]]))
            for i in range(len(exact)):
                for j in range(i + 1, len(exact)):
                    pairs += 1; pair += int((exact_order.index(i) < exact_order.index(j)) == (pred_order.index(i) < pred_order.index(j)))
        report[split] = {"roots": len(records[split]), "top1_agreement": top / len(records[split]), "pairwise_ordering_agreement": pair / pairs, "mean_regret": float(np.mean(regret)), "median_regret": float(np.median(regret)), "p95_regret": float(np.percentile(regret, 95)), "mean_regret_normalized": float(np.mean(regret) / holdout_t1_std), "top3_containment": top3 / len(records[split]), "mean_reciprocal_rank": float(np.mean(mrr))}
    return report


def _by_gap(records, predictions):
    output = {}
    for split in ("dev", "holdout"):
        order = np.argsort([record["gap"] for record in records[split]], kind="mergesort"); output[split] = []
        for index, chunk in enumerate(np.array_split(order, 4)):
            rankings = _ranking({split: [records[split][i] for i in chunk]}, {split: [predictions[split][i] for i in chunk]}, 1.0)[split]
            output[split].append({"quartile": index + 1, **rankings})
    return output


def _run(output: Path, result_path: Path, shard_root: Path) -> dict:
    started = time.time(); compiled = compile_semantic_ruleset(build_standard_shogi_ruleset()); basis = CorrectedShogiFrozenBasisV2("standard_shogi", compiled); reproduction = _reproduce_f140(compiled, basis); root_records, delta_rows, cache_report = _load_rows(result_path, shard_root, reproduction["rows"], basis, compiled)
    weights = {split: [1.0 / len(record["actions"]) for record in root_records[split] for _ in record["actions"]] for split in root_records}; targets = {split: [target for record in root_records[split] for target in record["targets"]] for split in root_records}
    for split in delta_rows:
        delta_rows[split] = np.asarray(delta_rows[split], dtype=np.float64)
    target_arrays = {split: np.asarray(targets[split], dtype=np.float64) for split in targets}; pack = _weighted_pack(delta_rows, target_arrays, weights, basis, reproduction["pack"]); theta, matched, numerical = _solve(pack)
    pred_actions = {split: _predict_pack(theta, pack, split) for split in pack["design"]}; t1_std = float(np.std([record["t1"] for record in root_records["holdout"]])) or 1.0; scalar = {split: _weighted_metrics(target_arrays[split], pred_actions[split], pack["weights"][split], t1_std) for split in pack["design"]}
    exact_weights = np.asarray(basis.weights, dtype=np.float64); algebra_errors = []; constant_contrib = {}; delta_predictions = {}
    for split in delta_rows:
        delta_predictions[split] = np.asarray(delta_rows[split]) @ exact_weights; algebra_errors.extend((delta_predictions[split] - target_arrays[split]).tolist()); constant = ~pack["active"]; constant_contrib[split] = np.asarray(delta_rows[split])[:, constant] @ exact_weights[constant]
    algebra = {"maximum_absolute_error": float(np.max(np.abs(algebra_errors))), "rms_error": float(np.sqrt(np.mean(np.asarray(algebra_errors) ** 2))), "failing_rows": int(np.sum(np.abs(algebra_errors) > 1e-9))}
    theta_oracle = np.r_[exact_weights[pack["active"]] * pack["feature_scale"][pack["active"]] / pack["target_std"], 0.0]; projector = pack["vt"][pack["retained"]].T @ pack["vt"][pack["retained"]]; theta_row = projector @ theta_oracle; theta_null = theta_oracle - theta_row; null_contrib = {}; constant_report = {}
    for split in pack["design"]:
        null_contrib[split] = {"rmse_oracle_units": float(np.sqrt(np.average((pack["target_std"] * (pack["design"][split] @ theta_null)) ** 2, weights=pack["weights"][split]))), "normalized_by_holdout_a1_std": float(np.sqrt(np.average((pack["target_std"] * (pack["design"][split] @ theta_null)) ** 2, weights=pack["weights"][split])) / t1_std)}
        constant_report[split] = {"rmse_oracle_units": float(np.sqrt(np.average(constant_contrib[split] ** 2, weights=pack["weights"][split]))), "normalized_by_holdout_a1_std": float(np.sqrt(np.average(constant_contrib[split] ** 2, weights=pack["weights"][split])) / t1_std)}
    primary_identifiable = bool(null_contrib["holdout"]["normalized_by_holdout_a1_std"] <= 1e-8 and constant_report["holdout"]["normalized_by_holdout_a1_std"] <= 1e-8)
    ranking_predictions = {split: [] for split in root_records}; t1_predictions = {split: [] for split in root_records}; learned_base_predictions = {split: [] for split in root_records}; direct_fit = _fit_report(reproduction["pack"]); direct_model = direct_fit["pcg"]
    for split in root_records:
        for record, offset in zip(root_records[split], np.cumsum([0] + [len(item["actions"]) for item in root_records[split][:-1]])):
            values = pred_actions[split][offset:offset + len(record["actions"])]; ranking_predictions[split].append(values); t1_predictions[split].append(record["direct_value"] + float(np.max(values))); learned_base = _predict_pack(direct_model, reproduction["pack"], split)[len(learned_base_predictions[split])] + float(np.max(values)); learned_base_predictions[split].append(learned_base)
    rankings = _ranking(root_records, ranking_predictions, t1_std); ranking_by_gap = _by_gap(root_records, ranking_predictions); exact_t1 = {split: np.asarray([record["t1"] for record in root_records[split]]) for split in root_records}; t1_metrics = {split: _scalar_metrics(exact_t1[split], np.asarray(t1_predictions[split]), t1_std) for split in root_records}; learned_base_metrics = {split: _scalar_metrics(exact_t1[split], np.asarray(learned_base_predictions[split]), t1_std) for split in root_records}; action_gate = bool(rankings["holdout"]["top1_agreement"] >= 0.95 and rankings["holdout"]["pairwise_ordering_agreement"] >= 0.98 and rankings["holdout"]["mean_regret_normalized"] <= 0.01); t1_gate = bool(t1_metrics["holdout"]["normalized_rmse"] <= 0.05 and t1_metrics["holdout"]["r2"] >= 0.99 and t1_metrics["holdout"]["pearson"] >= 0.995); usefulness = bool(t1_metrics["holdout"]["rmse_oracle_units"] < 1544.504502406404)
    projection_distance = float(np.linalg.norm(projector @ (matched - theta_oracle)) / max(np.linalg.norm(theta_row), 1e-30)); prediction_difference = {split: float(np.sqrt(np.average((pack["target_std"] * (pack["design"][split] @ (matched - theta_oracle))) ** 2, weights=pack["weights"][split]))) for split in pack["design"]}; projected_matched = projector @ matched; cosine = float((projected_matched @ theta_row) / max(np.linalg.norm(projected_matched) * np.linalg.norm(theta_row), 1e-30))
    if algebra["failing_rows"]:
        classification = "F142_TRANSITION_DELTA_ORACLE_RECOMPOSITION_FAILURE"
    elif not primary_identifiable:
        classification = "F142_ACTION_DELTA_TRAINING_SURFACE_NONIDENTIFIABLE"
    elif not numerical["pass"]:
        classification = "F142_ACTION_DELTA_SOLVER_NUMERICAL_FAILURE"
    elif not action_gate:
        classification = "CORRECTED_ACTION_DELTA_FACTORIZATION_ACTION_RECOVERY_FAILS"
    elif not t1_gate or not usefulness:
        classification = "CORRECTED_ACTION_DELTA_POLICY_PASSES_T1_CALIBRATION_FAILS"
    else:
        classification = "CORRECTED_ONE_PLY_MAX_ACTION_FACTORIZATION_PASSES"
    result = {"schema": "F142_CORRECTED_SHOGI_ACTION_DELTA_FACTORIZATION_V1", "baseline": BASELINE, "f141_reproduction": {"f141_baseline": F141_BASELINE, "shard_schema": SHARD_SCHEMA, "root_counts": {split: len(root_records[split]) for split in root_records}, "action_rows": cache_report["action_rows"], "unique_child_identities": cache_report["unique_child_identities"], "duplicate_child_reuse": cache_report["duplicate_child_reuse"], "static_t1_compression_holdout_nrmse": 1.8302864928571427, "static_root_baseline_holdout_rmse": 1544.504502406404, "f140_learned_teacher_shadow_top1": 0.984, "f140_learned_teacher_shadow_pairwise": 0.9729629736752038}, "action_representation": {"schema": "CORRECTED_TRANSITION_DELTA_V1", "raw_width": RAW_WIDTH, "weighted_train_target_mean": pack["target_mean"], "weighted_train_target_std": pack["target_std"], "active_width": int(pack["active"].sum()), "constant_width": int((~pack["active"]).sum()), "design_width": int(pack["design"]["train"].shape[1]), "numerical_rank": int(pack["retained"].sum()), "nullity": int(len(pack["singular_values"]) - pack["retained"].sum()), "condition_number": float(pack["singular_values"][pack["retained"]][0] / pack["singular_values"][pack["retained"]][-1]), "effective_ranks": {str(threshold): int(np.sum(pack["singular_values"] > threshold * pack["singular_values"][0])) for threshold in (1e-6, 1e-8, 1e-10)}}, "algebraic_control": algebra, "oracle_null_decomposition": {"theta_action_oracle_norm": float(np.linalg.norm(theta_oracle)), "row_space_projection_norm": float(np.linalg.norm(theta_row)), "null_space_projection_norm": float(np.linalg.norm(theta_null)), "train_dev_holdout_null_contribution": null_contrib, "train_constant_delta_contribution": constant_report, "primary_identifiable": primary_identifiable}, "solver": {"numerical": numerical, "weighted_scalar_metrics": scalar}, "action_ranking": {"metrics": rankings, "by_exact_teacher_gap_quartile": ranking_by_gap, "gate_pass": action_gate}, "max_pooled_t1": {"metrics": t1_metrics, "gate_pass": t1_gate, "relative_rmse_reduction_vs_f141_static": 1.0 - t1_metrics["holdout"]["rmse_oracle_units"] / 2769.269142472943, "relative_rmse_reduction_vs_root_v_baseline": 1.0 - t1_metrics["holdout"]["rmse_oracle_units"] / 1544.504502406404}, "f140_learned_value_base_shadow": {"metrics": learned_base_metrics}, "parameter_recovery": {"row_space_projection_distance": projection_distance, "prediction_rmse_of_difference": prediction_difference, "projected_cosine_similarity": cosine}, "provenance": {"no_malformed_f129_shards": True, "no_new_states": True, "root_equal_action_weights": True, "exact_delta_definition": "-child_features-root_features", "shard_contract_verified": True}, "classification": classification, "runtime_seconds": time.time() - started}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"); return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--f141-result", type=Path, required=True); parser.add_argument("--f141-shard-root", type=Path, required=True); args = parser.parse_args(); result = _run(args.output, args.f141_result, args.f141_shard_root); print(json.dumps({"classification": result["classification"], "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__": main()
