"""F141: corrected known-oracle one-ply max compression on the F140 surface."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import (
        _action_ranking,
        _collect_fresh_roots,
        _json_sha,
        _ranking_summary,
        _search_probe,
        _scalar_metrics,
        _sort_actions,
    )
    from scripts.f123_reverse_benchmark_identifiability_optimizer_diagnosis import (
        _matched_ridge,
        _minimum_norm,
        _predict,
        _proxy_fit,
    )
    from scripts.f135_corrected_shogi_oracle_schema_rebaseline import (
        CORPUS_SHA,
        CorrectedShogiFrozenBasisV2,
        FAMILY,
        _collect_states,
        _materialize,
    )
    from scripts.f136_corrected_shogi_coverage_identifiability import _gate
    from scripts.f138_corrected_shogi_targeted_gauge_coverage_a1 import (
        GENERATOR_SEED,
        ROOT_SEED,
        TRAJECTORY_LENGTHS,
        _dev_witnesses,
        _generate_candidates,
        _materialize_generated,
        _minimize_candidates,
        _prepare_augmented,
        _surface_identity_report,
    )
    from scripts.f139_corrected_shogi_rank_complete_a1 import _rank_complete, _row
    from scripts.f140_corrected_shogi_rank_targeted_generation_a1 import (
        CORRECTED_ORACLE_SHA,
        FEATURE_NAME_SHA,
        _assign_oracle,
        _continue_rank,
    )
    from scripts.f138_corrected_shogi_targeted_gauge_coverage_a1 import _fit_report
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import _action_ranking, _collect_fresh_roots, _json_sha, _ranking_summary, _search_probe, _scalar_metrics, _sort_actions
    from f123_reverse_benchmark_identifiability_optimizer_diagnosis import _matched_ridge, _minimum_norm, _predict, _proxy_fit
    from f135_corrected_shogi_oracle_schema_rebaseline import CORPUS_SHA, CorrectedShogiFrozenBasisV2, FAMILY, _collect_states, _materialize
    from f136_corrected_shogi_coverage_identifiability import _gate
    from f138_corrected_shogi_targeted_gauge_coverage_a1 import GENERATOR_SEED, ROOT_SEED, TRAJECTORY_LENGTHS, _dev_witnesses, _generate_candidates, _materialize_generated, _minimize_candidates, _prepare_augmented, _surface_identity_report
    from f139_corrected_shogi_rank_complete_a1 import _rank_complete, _row
    from f140_corrected_shogi_rank_targeted_generation_a1 import CORRECTED_ORACLE_SHA, FEATURE_NAME_SHA, _assign_oracle, _continue_rank
    from f138_corrected_shogi_targeted_gauge_coverage_a1 import _fit_report

from generic_chess.core.declarations import available_declarations
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import apply_action
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


SHARD_SCHEMA = "F141_CORRECTED_T1_LABEL_SHARD_V1"
SHARD_SIZE = 128
T1_GATE_NRMSE = 0.15
T1_GATE_R2 = 0.95
T1_GATE_PEARSON = 0.975
L2 = 1e-6
BASELINE = "b82e088196b01342352b01bbd1c9599d435532cd"


def _reproduce_f140(compiled, basis):
    states = _collect_states(compiled)
    if _json_sha([row["identity"] for row in states]) != CORPUS_SHA:
        raise RuntimeError("F141_FROZEN_CORPUS_IDENTITY_MISMATCH")
    original = _materialize(states, basis)
    original_pack = _prepare_augmented({"train": original[:3000], "dev": original[3000:3750], "holdout": original[3750:]}, basis)
    occupancy_names = [name for name in basis.names if name.startswith("occupancy_diff:")]
    dev_targets = set()
    holdout_targets = set()
    for name in occupancy_names:
        index = basis.names.index(name)
        constant = original_pack["raw"]["train"][0, index]
        dev_var = np.any(np.abs(original_pack["raw"]["dev"][:, index] - constant) > 1e-12)
        holdout_var = np.any(np.abs(original_pack["raw"]["holdout"][:, index] - constant) > 1e-12)
        if not original_pack["active"][index] and dev_var:
            dev_targets.add(name)
        elif not original_pack["active"][index] and holdout_var:
            holdout_targets.add(name)
    dev_selected = _dev_witnesses(original, basis, original_pack, dev_targets)
    forbidden = {row["identity"] for row in states}
    fresh_roots = _collect_fresh_roots(FAMILY, compiled, basis, ROOT_SEED, forbidden, 256)
    forbidden |= {str(position_identity_key(state.position, compiled)) for state in fresh_roots}
    constants = {name: float(original_pack["raw"]["train"][0, basis.names.index(name)]) for name in holdout_targets}
    generated, generation = _generate_candidates(compiled, sorted(holdout_targets), constants, forbidden)
    generated_features = [{**candidate, "features": basis.vector(candidate["state"]).tolist()} for candidate in generated]
    f138_selected = _minimize_candidates(generated_features, sorted(holdout_targets))
    f138_generated_rows = _assign_oracle(_materialize_generated(f138_selected, basis), basis)
    transferred_rows = [entry["row"] for entry in dev_selected]
    transfer_ids = {row["identity"] for row in transferred_rows}
    original_dev_remaining = [row for row in original[3000:3750] if row["identity"] not in transfer_ids]
    f138_rows = {"train": original[:3000] + transferred_rows + f138_generated_rows, "dev": original_dev_remaining, "holdout": original[3750:]}
    f138_pack = _prepare_augmented(f138_rows, basis)
    if not (len(generated) == 6125 and generation["inspected_legal_states"] == 37066 and generation["trajectory_count"] == 342 and len(f138_selected) == 25 and len(f138_rows["train"]) == 3044 and int(f138_pack["active"].sum()) == 773 and f138_pack["design"]["train"].shape[1] == 774 and int(f138_pack["retained"].sum()) == 696 and len(f138_pack["singular_values"]) - int(f138_pack["retained"].sum()) == 78):
        raise RuntimeError("F141_F140_REPRODUCTION_FAILURE")
    active = f138_pack["active"]
    feature_candidates = [candidate for candidate in generated_features if np.all(np.abs(np.asarray(candidate["features"])[~active] - f138_pack["raw"]["train"][0, ~active]) <= 1e-12)]
    existing_selected, capacity = _rank_complete(f138_pack, feature_candidates, 751)
    if len(feature_candidates) != 2096 or capacity["attainable_rank"] != 751 or len(existing_selected) != 55:
        raise RuntimeError("F141_EXISTING_POOL_REPRODUCTION_FAILURE")
    existing_rows = [{key: row[key] for key in ("identity", "trajectory", "ply", "features", "state", "row_space_residual_norm_at_selection", "cumulative_rank")} for row in existing_selected]
    forbidden |= {row["identity"] for row in f138_selected} | {row["identity"] for row in existing_selected}
    continuation, continuation_report = _continue_rank(compiled, basis, f138_pack, [_row(row["features"], f138_pack) for row in existing_rows], forbidden)
    if len(continuation) != 10 or continuation_report["final_rank"] != 761:
        raise RuntimeError("F141_RANK_COMPLETE_REPRODUCTION_FAILURE")
    continuation_rows = _assign_oracle(continuation, basis)
    final_rows = {"train": f138_rows["train"] + _assign_oracle(existing_rows, basis) + continuation_rows, "dev": original_dev_remaining, "holdout": original[3750:]}
    final_surface = _surface_identity_report(final_rows, [row["identity"] for row in original[3750:]])
    final_pack = _prepare_augmented(final_rows, basis)
    if not (len(final_rows["train"]) == 3109 and len(final_rows["dev"]) == 731 and len(final_rows["holdout"]) == 750 and int(final_pack["active"].sum()) == 773 and final_pack["design"]["train"].shape[1] == 774 and int(final_pack["retained"].sum()) == 761 and len(final_pack["singular_values"]) - int(final_pack["retained"].sum()) == 13):
        raise RuntimeError("F141_F140_RANK_GATE_FAILURE")
    return {"rows": final_rows, "pack": final_pack, "surface": final_surface, "fresh_roots": fresh_roots, "f139_reproduction": {"f138_train_count": len(f138_rows["train"]), "f138_active": int(f138_pack["active"].sum()), "f138_design_width": int(f138_pack["design"]["train"].shape[1]), "f138_rank": int(f138_pack["retained"].sum()), "f138_nullity": int(len(f138_pack["singular_values"]) - f138_pack["retained"].sum()), "candidate_count": len(generated), "no_new_active_candidates": len(feature_candidates), "attainable_rank": capacity["attainable_rank"], "attainable_nullity": capacity["attainable_nullity"]}}


def _vector_prediction(model, pack, features):
    vector = np.asarray(features, dtype=np.float64)
    normalized = (vector - pack["feature_mean"]) / pack["feature_scale"]
    return float(pack["target_mean"] + pack["target_std"] * (np.r_[normalized[pack["active"]], 1.0] @ model))


def _prepare_target_pack(rows, labels, direct_pack):
    raw = {split: np.asarray([row["features"] for row in rows[split]], dtype=np.float64) for split in ("train", "dev", "holdout")}
    target_raw = {split: np.asarray(labels[split], dtype=np.float64) for split in ("train", "dev", "holdout")}
    mean = direct_pack["feature_mean"].copy()
    scale = direct_pack["feature_scale"].copy()
    active = direct_pack["active"].copy()
    normalized = {split: (value - mean) / scale for split, value in raw.items()}
    design = {split: np.column_stack([value[:, active], np.ones(len(value))]) for split, value in normalized.items()}
    target_mean = float(target_raw["train"].mean())
    target_std = float(target_raw["train"].std()) or 1.0
    target = {split: (value - target_mean) / target_std for split, value in target_raw.items()}
    left, singular, vt = np.linalg.svd(design["train"], full_matrices=False)
    tolerance = np.finfo(float).eps * max(design["train"].shape) * float(singular[0])
    return {"raw": raw, "oracle": target_raw, "feature_mean": mean, "feature_scale": scale, "active": active, "target_mean": target_mean, "target_std": target_std, "normalized": normalized, "design": design, "target": target, "singular_values": singular, "left_vectors": left, "vt": vt, "rank_tol": tolerance, "retained": singular > tolerance, "constant_feature_names": direct_pack["constant_feature_names"], "feature_count": direct_pack["feature_count"]}


def _declaration_present(state, compiled):
    return bool(available_declarations(state, compiled))


def _build_shards(rows, basis, shard_root):
    if shard_root.exists():
        shutil.rmtree(shard_root)
    shard_root.mkdir(parents=True, exist_ok=True)
    child_cache = {}
    all_records = {split: [] for split in ("train", "dev", "holdout")}
    total_actions = 0
    terminal_children = 0
    root_declarations = 0
    child_declarations = 0
    action_counts = []
    for split in ("train", "dev", "holdout"):
        for row in rows[split]:
            state = row["state"]
            actions = _sort_actions(legal_actions(state, basis.compiled))
            spectrum = []
            root_decl = _declaration_present(state, basis.compiled)
            child_decl = False
            for action in actions:
                child = apply_action(state, action, basis.compiled)
                child_id = str(position_identity_key(child.position, basis.compiled))
                cached = child_cache.get(child_id)
                if cached is None:
                    features = basis.vector(child).tolist()
                    cached = {"features": features, "oracle": float(basis.oracle(np.asarray(features, dtype=np.float64)))}
                    child_cache[child_id] = cached
                if child.terminal_status.status is not TerminalStatus.ONGOING:
                    terminal_children += 1
                child_decl = child_decl or _declaration_present(child, basis.compiled)
                spectrum.append({"action": str(action), "child_identity": child_id, "q1": float(-cached["oracle"])})
            spectrum.sort(key=lambda item: item["action"])
            if root_decl:
                root_declarations += 1
            if child_decl:
                child_declarations += 1
            if not spectrum:
                raise RuntimeError("F141_ONGOING_ROOT_WITHOUT_LEGAL_ACTION")
            best = min(spectrum, key=lambda item: (-item["q1"], item["action"]))
            second = sorted((item["q1"] for item in spectrum), reverse=True)[1] if len(spectrum) > 1 else best["q1"]
            all_records[split].append({"root_identity": row["identity"], "direct_corrected_value": float(row["oracle"]), "legal_action_count": len(spectrum), "action_spectrum": spectrum, "exact_t1": float(best["q1"]), "exact_teacher_action": best["action"], "teacher_top2_gap": float(best["q1"] - second)})
            action_counts.append(len(spectrum))
            total_actions += len(spectrum)
    manifests = []
    for split in ("train", "dev", "holdout"):
        records = all_records[split]
        root_ids = [record["root_identity"] for record in records]
        for index in range(0, len(records), SHARD_SIZE):
            shard_records = records[index:index + SHARD_SIZE]
            path = shard_root / f"{split}-{index // SHARD_SIZE:03d}.json"
            payload = {"schema": SHARD_SCHEMA, "corrected_oracle_sha": CORRECTED_ORACLE_SHA, "feature_name_sha": FEATURE_NAME_SHA, "split": split, "shard_index": index // SHARD_SIZE, "root_identity_sequence": [record["root_identity"] for record in shard_records], "root_identity_sha256": _json_sha([record["root_identity"] for record in shard_records]), "roots": shard_records}
            path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            manifests.append({"path": str(path), "sha256": digest, "split": split, "shard_index": index // SHARD_SIZE, "root_count": len(shard_records), "root_identity_sha256": payload["root_identity_sha256"]})
    return all_records, {"schema": SHARD_SCHEMA, "shard_size": SHARD_SIZE, "shard_count": len(manifests), "manifests": manifests, "total_action_rows": total_actions, "unique_child_identities": len(child_cache), "duplicate_child_reuse_count": total_actions - len(child_cache), "immediate_terminal_child_count": terminal_children, "root_declaration_count": root_declarations, "child_declaration_root_count": child_declarations, "legal_action_count_distribution": {"mean": float(np.mean(action_counts)), "median": float(np.median(action_counts)), "p90": float(np.percentile(action_counts, 90)), "p95": float(np.percentile(action_counts, 95)), "max": int(max(action_counts))}}, child_cache


def _stats(values):
    array = np.asarray(values, dtype=np.float64)
    return {"count": int(len(array)), "mean": float(np.mean(array)), "median": float(np.median(array)), "std": float(np.std(array)), "rms": float(np.sqrt(np.mean(array * array))), "mean_absolute": float(np.mean(np.abs(array))), "p50_absolute": float(np.percentile(np.abs(array), 50)), "p90_absolute": float(np.percentile(np.abs(array), 90)), "p95_absolute": float(np.percentile(np.abs(array), 95)), "max_absolute": float(np.max(np.abs(array))), "zero_fraction_within_1e-12": float(np.mean(np.abs(array) <= 1e-12))}


def _correlations(left, right):
    left = np.asarray(left, dtype=np.float64); right = np.asarray(right, dtype=np.float64)
    metrics = _scalar_metrics(left, right, float(np.std(left)) or 1.0)
    return {"pearson": metrics["pearson"], "spearman": metrics["spearman"]}


def _quartile_report(values, errors, counts=None):
    order = np.argsort(values, kind="mergesort")
    chunks = np.array_split(order, 4)
    result = []
    for index, chunk in enumerate(chunks):
        result.append({"quartile": index + 1, "count": int(len(chunk)), "value_min": int(np.min(np.asarray(values)[chunk])) if counts is not None and len(chunk) else None, "value_max": int(np.max(np.asarray(values)[chunk])) if counts is not None and len(chunk) else None, "mean_absolute_error": float(np.mean(np.abs(np.asarray(errors)[chunk]))) if len(chunk) else 0.0})
    return result


def _run(output: Path, shard_root: Path) -> dict:
    started = time.time()
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    basis = CorrectedShogiFrozenBasisV2(FAMILY, compiled)
    if basis.oracle_weight_sha256 != CORRECTED_ORACLE_SHA or _json_sha(basis.names) != FEATURE_NAME_SHA:
        raise RuntimeError("F141_CORRECTED_SCHEMA_HASH_MISMATCH")
    reproduction = _reproduce_f140(compiled, basis)
    rows = reproduction["rows"]
    direct_pack = reproduction["pack"]
    direct_fit = _fit_report(direct_pack)
    direct_metrics = direct_fit["scalar"]["holdout"]
    roots_for_control = reproduction["fresh_roots"]
    direct_proxy = _proxy_fit(direct_fit["pcg"], direct_pack); direct_proxy["pcg_model"] = direct_proxy.pop("adam_model")
    direct_action = _ranking_summary(_action_ranking(roots_for_control, basis, direct_proxy, "pcg"), float(np.std(direct_pack["oracle"]["holdout"])))
    direct_action["top1_agreement"] = float(direct_action["top1_agreement"])
    direct_action_gate = bool(abs(direct_metrics["rmse_oracle_units"] - 0.371665296350058) <= 1e-9 and abs(direct_metrics["normalized_rmse"] - 0.0002744663771323697) <= 1e-12 and abs(direct_metrics["r2"] - 0.9999999246682079) <= 1e-9 and abs(direct_metrics["pearson"] - 0.9999999633278593) <= 1e-9 and abs(direct_action["top1_agreement"] - 0.97265625) <= 1e-12 and abs(direct_action["pairwise_ordering_agreement"] - 0.988520006832259) <= 1e-9 and abs(direct_action["mean_regret_normalized"] - 0.0024239891704051506) <= 1e-9)
    if not direct_action_gate:
        raise RuntimeError("F141_F140_DIRECT_CONTROL_REPRODUCTION_FAILURE")
    records, shard_report, child_cache = _build_shards(rows, basis, shard_root)
    labels = {split: [entry["exact_t1"] for entry in records[split]] for split in records}
    t1_pack = _prepare_target_pack(rows, labels, direct_pack)
    t1_fit = _fit_report(t1_pack)
    t1_minimum_norm = _minimum_norm(t1_pack)
    t1_predictions = {split: _predict(t1_fit["pcg"], t1_pack, split) for split in records}
    t1_metrics = t1_fit["scalar"]
    static_metrics = {}
    static_predictions = {}
    for split in records:
        static_predictions[split] = np.asarray([entry["direct_corrected_value"] for entry in records[split]], dtype=np.float64)
        static_metrics[split] = _scalar_metrics(np.asarray(labels[split]), static_predictions[split], float(np.std(labels["holdout"])))
    representation_gate = bool(t1_metrics["holdout"]["normalized_rmse"] <= T1_GATE_NRMSE and t1_metrics["holdout"]["r2"] >= T1_GATE_R2 and t1_metrics["holdout"]["pearson"] >= T1_GATE_PEARSON)
    usefulness = {split: float(1.0 - t1_metrics[split]["rmse_oracle_units"] / static_metrics[split]["rmse_oracle_units"]) if static_metrics[split]["rmse_oracle_units"] else 0.0 for split in records}
    usefulness_gate = bool(t1_metrics["holdout"]["rmse_oracle_units"] < static_metrics["holdout"]["rmse_oracle_units"])
    shadow = {}
    direct_model = direct_fit["pcg"]
    for split in records:
        for entry in records[split]:
            exact = [float(item["q1"]) for item in entry["action_spectrum"]]
            learned = [float(-_vector_prediction(direct_model, direct_pack, child_cache[item["child_identity"]]["features"])) for item in entry["action_spectrum"]]
            actions = [item["action"] for item in entry["action_spectrum"]]
            exact_order = sorted(range(len(actions)), key=lambda i: (-exact[i], actions[i]))
            learned_order = sorted(range(len(actions)), key=lambda i: (-learned[i], actions[i]))
            entry["_learned_scores"] = learned; entry["_exact_scores"] = exact; entry["_exact_order"] = exact_order; entry["_learned_order"] = learned_order
    for split in records:
        exact_leaf = []; learned_leaf = []; top_agree = pair_same = pair_total = 0; regrets = []; exact_t1 = []; learned_t1 = []
        for entry in records[split]:
            exact = entry.pop("_exact_scores"); learned = entry.pop("_learned_scores"); exact_order = entry.pop("_exact_order"); learned_order = entry.pop("_learned_order")
            exact_leaf.extend(exact); learned_leaf.extend(learned); exact_t1.append(max(exact)); learned_t1.append(max(learned)); top_agree += int(exact_order[0] == learned_order[0]); regrets.append(float(max(exact) - exact[learned_order[0]]))
            for i in range(len(exact)):
                for j in range(i + 1, len(exact)):
                    pair_total += 1; pair_same += int((exact_order.index(i) < exact_order.index(j)) == (learned_order.index(i) < learned_order.index(j)))
        shadow[split] = {"child_leaf_rmse_exact_vs_f140_learner": float(np.sqrt(np.mean((np.asarray(learned_leaf) - np.asarray(exact_leaf)) ** 2))), "teacher_top1_agreement": top_agree / len(records[split]), "pairwise_action_order_agreement": pair_same / pair_total if pair_total else 1.0, "mean_corrected_oracle_regret_of_learned_teacher": float(np.mean(regrets)), "t1_a1_vs_exact": _scalar_metrics(np.asarray(labels[split]), np.asarray(learned_t1), float(np.std(labels["holdout"]))) }
    shadow_stability = bool(shadow["holdout"]["teacher_top1_agreement"] >= 0.95 and shadow["holdout"]["mean_corrected_oracle_regret_of_learned_teacher"] / (float(np.std(labels["holdout"])) or 1.0) <= 0.01)
    displacement = {}
    for split in records:
        delta = np.asarray(labels[split]) - static_predictions[split]
        displacement[split] = {"delta_t1": _stats(delta), "t1_vs_root_v_correlation": _correlations(labels[split], static_predictions[split])}
    holdout_counts = np.asarray([entry["legal_action_count"] for entry in records["holdout"]])
    holdout_delta = np.asarray(labels["holdout"]) - static_predictions["holdout"]
    holdout_abs_compression = np.abs(t1_predictions["holdout"] - np.asarray(labels["holdout"]))
    displacement["holdout_by_legal_action_count_quartile"] = _quartile_report(holdout_counts, holdout_delta, holdout_counts)
    gap_diag = {}
    for split in ("dev", "holdout"):
        gaps = np.asarray([entry["teacher_top2_gap"] for entry in records[split]], dtype=np.float64)
        gap_diag[split] = {"gap_stats": _stats(gaps), "static_compression_absolute_error_by_gap_quartile": _quartile_report(gaps, np.abs(t1_predictions[split] - np.asarray(labels[split])), gaps)}
    search_fit = _proxy_fit(direct_fit["pcg"], direct_pack); search_fit["pcg_model"] = search_fit.pop("adam_model")
    search = _search_probe(roots_for_control[:64], basis, search_fit, "pcg")
    if not t1_fit["numerical"]["pass"]:
        classification = "F141_CORRECTED_T1_SOLVER_NUMERICAL_FAILURE"
    elif not representation_gate:
        classification = "CORRECTED_STATIC_BASIS_NOT_CLOSED_UNDER_ONE_PLY_MAX"
    elif not usefulness_gate:
        classification = "CORRECTED_T1_STATIC_REPRESENTABLE_BUT_COMPRESSION_NOT_USEFUL"
    else:
        classification = "CORRECTED_KNOWN_ORACLE_T1_STATIC_COMPRESSION_PASSES"
    result = {"schema": "F141_CORRECTED_SHOGI_KNOWN_ORACLE_T1_COMPRESSION_V1", "baseline": BASELINE, "f140_reproduction": {**reproduction["f139_reproduction"], "active_feature_count": int(direct_pack["active"].sum()), "design_width": int(direct_pack["design"]["train"].shape[1]), "rank": int(direct_pack["retained"].sum()), "nullity": int(len(direct_pack["singular_values"]) - direct_pack["retained"].sum()), "direct_control": {"scalar": direct_metrics, "action": direct_action, "gate_pass": direct_action_gate}}, "surface": reproduction["surface"], "shards": shard_report, "t1_fit": {"numerical": t1_fit["numerical"], "metrics": t1_metrics, "minimum_norm_holdout_prediction_difference": float(np.sqrt(np.mean((_predict(t1_fit["pcg"], t1_pack, "holdout") - _predict(t1_minimum_norm, t1_pack, "holdout")) ** 2)) / (float(np.std(labels["holdout"])) or 1.0)), "representation_gate_pass": representation_gate}, "static_root_baseline": {"metrics": static_metrics, "relative_rmse_reduction_vs_static": usefulness, "usefulness_gate_pass": usefulness_gate}, "learned_teacher_shadow": shadow, "f140_learned_teacher_one_ply_stable": shadow_stability, "search_recovery_diagnostic": search, "search_information_displacement": displacement, "teacher_action_gap_diagnostic": gap_diag, "provenance": {"no_malformed_f129_shards_read_or_reused": True, "original_holdout_unchanged": reproduction["surface"]["holdout_byte_and_identity_preserved"], "train_only_feature_normalization": True, "train_only_t1_target_normalization": True, "active_mask_derived_from_f140": True, "terminal_and_declaration_values_diagnostic_only": True, "child_identity_cache_reused": True}, "classification": classification, "runtime_seconds": time.time() - started}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard-root", type=Path, required=True)
    args = parser.parse_args()
    result = _run(args.output, args.shard_root)
    print(json.dumps({"classification": result["classification"], "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
