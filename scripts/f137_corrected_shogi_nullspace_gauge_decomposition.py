"""F137: decompose the corrected Shogi active null space into material/PST gauges."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import COUNTS, FrozenBasis, _json_sha, _scalar_metrics
    from scripts.f123_reverse_benchmark_identifiability_optimizer_diagnosis import _matched_ridge, _prepare, _predict
    from scripts.f135_corrected_shogi_oracle_schema_rebaseline import CORPUS_SHA, CORPUS_SEED, CorrectedShogiFrozenBasisV2, FAMILY, _collect_states, _materialize
    from scripts.f136_corrected_shogi_coverage_identifiability import BASELINE, CORRECTED_ORACLE_SHA, FEATURE_NAME_SHA, _active_oracle_decomposition, _corr
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import COUNTS, FrozenBasis, _json_sha, _scalar_metrics
    from f123_reverse_benchmark_identifiability_optimizer_diagnosis import _matched_ridge, _prepare, _predict
    from f135_corrected_shogi_oracle_schema_rebaseline import CORPUS_SHA, CORPUS_SEED, CorrectedShogiFrozenBasisV2, FAMILY, _collect_states, _materialize
    from f136_corrected_shogi_coverage_identifiability import BASELINE, CORRECTED_ORACLE_SHA, FEATURE_NAME_SHA, _active_oracle_decomposition, _corr

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


F137_BASELINE = "08f5eb079f6614c834792356ee4d97c1e0786540"
TYPES = ("P", "L", "N", "S", "G", "B", "R", "TP", "TL", "TN", "TS", "TB", "TR")
EXACT_SPAN_SINE_TOL = 1e-10
EXACT_SPAN_PROJECTOR_TOL = 1e-9


def _split_indices() -> dict[str, slice]:
    return {"train": slice(0, COUNTS["train"]), "dev": slice(COUNTS["train"], COUNTS["train"] + COUNTS["dev"]), "holdout": slice(COUNTS["train"] + COUNTS["dev"], sum(COUNTS.values()))}


def _type_indices(basis, pack, type_id: str) -> tuple[int, list[int], list[int]]:
    material = basis.names.index(f"material_diff:{type_id}")
    occupancy = [index for index, name in enumerate(basis.names) if name.startswith(f"occupancy_diff:{type_id}:")]
    active = [index for index in occupancy if pack["active"][index]]
    omitted = [index for index in occupancy if not pack["active"][index]]
    return material, active, omitted


def _canonical_gauges(basis, pack) -> tuple[np.ndarray, dict]:
    vectors = []; report = {}
    for type_id in TYPES:
        material, active, omitted = _type_indices(basis, pack, type_id)
        vector = np.zeros(pack["design"]["train"].shape[1], dtype=np.float64)
        active_parameter_index = {raw: index for index, raw in enumerate(np.flatnonzero(pack["active"]))}
        vector[active_parameter_index[material]] = pack["feature_scale"][material]
        for raw in active:
            vector[active_parameter_index[raw]] = -pack["feature_scale"][raw]
        vectors.append(vector)
        report[type_id] = {"vector_norm": float(np.linalg.norm(vector)), "active_occupancy_coordinate_count": len(active), "omitted_occupancy_coordinate_count": len(omitted), "training_relation_max_abs": float(np.max(np.abs(pack["design"]["train"] @ vector)))}
    return np.column_stack(vectors), report


def _span_report(gauges: np.ndarray, pack: dict) -> dict:
    gauge_u, gauge_s, _ = np.linalg.svd(gauges, full_matrices=False)
    gauge_rank = int(np.sum(gauge_s > np.finfo(float).eps * max(gauges.shape) * gauge_s[0]))
    gauge_basis = gauge_u[:, :gauge_rank]
    null_basis = pack["vt"][~pack["retained"]].T
    cosines = np.linalg.svd(null_basis.T @ gauge_basis, compute_uv=False)
    gauge_projector = gauge_basis @ gauge_basis.T
    null_projector = null_basis @ null_basis.T
    residual_svd = [float(np.linalg.norm((np.eye(len(null_basis)) - gauge_projector) @ null_basis[:, i])) for i in range(null_basis.shape[1])]
    residual_gauge = [float(np.linalg.norm((np.eye(len(null_basis)) - null_projector) @ gauges[:, i]) / max(np.linalg.norm(gauges[:, i]), 1e-30)) for i in range(gauges.shape[1])]
    projection_residual_singular_values = np.linalg.svd((np.eye(len(null_basis)) - gauge_projector) @ null_basis, compute_uv=False)
    maximum_sine = float(projection_residual_singular_values[0]) if len(projection_residual_singular_values) else 1.0
    return {"rank": gauge_rank, "nonzero_spectrum_condition_number": float(gauge_s[0] / gauge_s[gauge_rank - 1]) if gauge_rank else None, "principal_angle_cosines": cosines.tolist(), "maximum_principal_angle_sine": maximum_sine, "projector_frobenius_difference": float(np.linalg.norm(null_projector - gauge_projector)), "maximum_svd_null_basis_projection_residual": max(residual_svd) if residual_svd else 0.0, "maximum_canonical_gauge_projection_residual": max(residual_gauge) if residual_gauge else 0.0, "exact_span_tolerances": {"maximum_principal_angle_sine": EXACT_SPAN_SINE_TOL, "projector_frobenius_difference": EXACT_SPAN_PROJECTOR_TOL}, "passes": bool(gauge_rank == 13 and maximum_sine <= EXACT_SPAN_SINE_TOL and (max(residual_gauge) if residual_gauge else 1.0) <= EXACT_SPAN_SINE_TOL and np.linalg.norm(null_projector - gauge_projector) <= EXACT_SPAN_PROJECTOR_TOL)}


def _gauge_activation(rows, basis, pack, gauges: np.ndarray) -> tuple[dict, dict[str, np.ndarray]]:
    activation = {}; raw_activation = {}
    for type_index, type_id in enumerate(TYPES):
        material, active, omitted = _type_indices(basis, pack, type_id)
        split_report = {}
        raw_values = {}
        for split, slc in _split_indices().items():
            design_values = pack["design"][split] @ gauges[:, type_index]
            raw = pack["raw"][split][:, omitted] - pack["raw"]["train"][0, omitted]
            raw_value = raw.sum(axis=1) if len(omitted) else np.zeros(len(design_values))
            raw_values[split] = raw_value
            delta = design_values - raw_value
            split_report[split] = {"nonzero_state_count": int(np.count_nonzero(np.abs(design_values) > 1e-12)), "rms": float(np.sqrt(np.mean(design_values * design_values))), "max_abs": float(np.max(np.abs(design_values))), "raw_identity_difference_max_abs": float(np.max(np.abs(delta))), "omitted_occupancy_coordinates_becoming_variable": [basis.names[index] for index in omitted if np.any(np.abs(pack["raw"][split][:, index] - pack["raw"]["train"][0, index]) > 1e-12)]}
        activation[type_id] = {"dev": split_report["dev"], "holdout": split_report["holdout"], "dev_holdout_identity_check_pass": bool(all(split_report[split]["raw_identity_difference_max_abs"] <= 1e-10 for split in ("dev", "holdout")))}
        raw_activation[type_id] = raw_values
    return activation, raw_activation


def _theta_from_basis(basis, pack) -> np.ndarray:
    active_indices = np.flatnonzero(pack["active"]); constant_indices = np.flatnonzero(~pack["active"]); weights = np.asarray(basis.weights)
    theta = np.zeros(pack["design"]["train"].shape[1], dtype=np.float64)
    theta[:-1] = weights[active_indices] * pack["feature_scale"][active_indices] / pack["target_std"]
    constant_at_train = float(np.dot(weights[constant_indices], pack["raw"]["train"][0, constant_indices])) if len(constant_indices) else 0.0
    theta[-1] = (float(np.dot(weights[active_indices], pack["feature_mean"][active_indices])) + constant_at_train - pack["target_mean"]) / pack["target_std"]
    return theta


def _null_gauge_report(pack, basis, gauges, f135_predictions, c_const) -> tuple[dict, np.ndarray, np.ndarray]:
    theta = _theta_from_basis(basis, pack); null_basis = pack["vt"][~pack["retained"]].T; theta_null = null_basis @ (null_basis.T @ theta)
    alpha, _, _, _ = np.linalg.lstsq(gauges, theta_null, rcond=None); reconstruction = gauges @ alpha; error = reconstruction - theta_null
    type_report = {}; gauge_predictions = {}; exact_null_predictions = {}
    normalizer = float(np.std(pack["oracle"]["holdout"])) or 1.0
    for split in ("train", "dev", "holdout"):
        gauge_predictions[split] = pack["target_std"] * pack["design"][split] @ reconstruction
        exact_null_predictions[split] = pack["target_std"] * pack["design"][split] @ theta_null
    for type_index, type_id in enumerate(TYPES):
        values = {}
        for split in ("dev", "holdout"):
            contribution = pack["target_std"] * alpha[type_index] * (pack["design"][split] @ gauges[:, type_index])
            values[split] = {"rms_oracle_units": float(np.sqrt(np.mean(contribution * contribution))), "normalized_rms": float(np.sqrt(np.mean(contribution * contribution)) / normalizer), "mae_oracle_units": float(np.mean(np.abs(contribution))), "max_abs_oracle_units": float(np.max(np.abs(contribution))), "nonzero_state_count": int(np.count_nonzero(np.abs(contribution) > 1e-12))}
        type_report[type_id] = {"alpha": float(alpha[type_index]), "metrics": values}
    per_split = {}
    for split in ("train", "dev", "holdout"):
        difference = gauge_predictions[split] - exact_null_predictions[split]
        per_split[split] = {"rmse_oracle_units": float(np.sqrt(np.mean(difference * difference))), "normalized_rmse": float(np.sqrt(np.mean(difference * difference)) / normalizer), "max_abs_oracle_units": float(np.max(np.abs(difference)))}
    holdout_residual = pack["oracle"]["holdout"] - f135_predictions["holdout"] - c_const["holdout"]
    gauge_residual = gauge_predictions["holdout"]
    return {"theta_oracle_active": theta.tolist(), "theta_null": theta_null.tolist(), "alpha_by_type": {type_id: float(alpha[index]) for index, type_id in enumerate(TYPES)}, "reconstruction_parameter_l2_error": float(np.linalg.norm(error)), "relative_reconstruction_error": float(np.linalg.norm(error) / max(np.linalg.norm(theta_null), 1e-30)), "type_wise_null_error": type_report, "sum_typewise_reconstructs_total": bool(np.max(np.abs(sum((pack["target_std"] * alpha[index] * (pack["design"]["holdout"] @ gauges[:, index]) for index in range(len(TYPES))), np.zeros(len(pack["design"]["holdout"]))) - gauge_residual)) <= 1e-10), "gauge_vs_exact_null_prediction": per_split, "holdout_gauge_error_vs_f135_residual": {"pearson": _corr(gauge_residual, holdout_residual), "rmse_difference": float(np.sqrt(np.mean((gauge_residual - holdout_residual) ** 2))), "fraction_residual_sse_explained": float(1.0 - np.sum((holdout_residual - gauge_residual) ** 2) / np.sum(holdout_residual * holdout_residual))}}, gauge_predictions, exact_null_predictions


def _coverage_table(rows, basis, pack) -> dict:
    entries = []; categories = {"DEV_COVERED": [], "HOLDOUT_ONLY": [], "NEVER_OBSERVED_OUTSIDE_TRAIN": []}
    for name in basis.names:
        if not name.startswith("occupancy_diff:") or pack["active"][basis.names.index(name)]: continue
        index = basis.names.index(name); type_id, file, rank = name.split(":")[1:]; train_value = float(pack["raw"]["train"][0, index]); dev_delta = pack["raw"]["dev"][:, index] - train_value; holdout_delta = pack["raw"]["holdout"][:, index] - train_value
        dev_positions = np.flatnonzero(np.abs(dev_delta) > 1e-12); holdout_positions = np.flatnonzero(np.abs(holdout_delta) > 1e-12)
        category = "DEV_COVERED" if len(dev_positions) else ("HOLDOUT_ONLY" if len(holdout_positions) else "NEVER_OBSERVED_OUTSIDE_TRAIN")
        entry = {"type": type_id, "square": f"{file}:{rank}", "feature_name": name, "oracle_pst_coefficient": float(basis.weights[index]), "training_constant_value": train_value, "varies_in_dev": bool(len(dev_positions)), "varies_in_holdout": bool(len(holdout_positions)), "dev_nonzero_deviation_count": int(len(dev_positions)), "holdout_nonzero_deviation_count": int(len(holdout_positions)), "first_dev_identity": rows[COUNTS["train"] + int(dev_positions[0])]["identity"] if len(dev_positions) else None, "first_holdout_identity": rows[COUNTS["train"] + COUNTS["dev"] + int(holdout_positions[0])]["identity"] if len(holdout_positions) else None}
        entries.append(entry); categories[category].append(entry)
    return {"all_constant_occupancy_features": entries, "categories": categories, "counts": {key: len(value) for key, value in categories.items()}}


def _run(output: Path) -> dict:
    started = time.time(); compiled = compile_semantic_ruleset(build_standard_shogi_ruleset()); basis = CorrectedShogiFrozenBasisV2(FAMILY, compiled); legacy = FrozenBasis(FAMILY, compiled)
    if basis.oracle_weight_sha256 != CORRECTED_ORACLE_SHA or _json_sha(basis.names) != FEATURE_NAME_SHA: raise RuntimeError("F137_CORRECTED_SCHEMA_HASH_MISMATCH")
    states = _collect_states(compiled); rows = _materialize(states, basis)
    if _json_sha([row["identity"] for row in states]) != CORPUS_SHA: raise RuntimeError("F137_FROZEN_CORPUS_IDENTITY_MISMATCH")
    pack = _prepare(rows, basis); matched = _matched_ridge(pack); f135_predictions = {split: _predict(matched, pack, split) for split in ("train", "dev", "holdout")}
    f136_reproduction = {"active_feature_count": int(pack["active"].sum()), "train_constant_count": len(pack["constant_feature_names"]), "design_width_including_intercept": int(pack["design"]["train"].shape[1]), "numerical_rank": int(pack["retained"].sum()), "nullity": int(len(pack["singular_values"]) - pack["retained"].sum())}
    if f136_reproduction != {"active_feature_count": 664, "train_constant_count": 422, "design_width_including_intercept": 665, "numerical_rank": 652, "nullity": 13}: raise RuntimeError("F137_F136_REPRODUCTION_FAILURE")
    c_const = {}
    for split in ("dev", "holdout"):
        c_const[split] = np.zeros(len(pack["raw"][split]))
        for index in np.flatnonzero(~pack["active"]): c_const[split] += basis.weights[index] * (pack["raw"][split][:, index] - pack["raw"]["train"][0, index])
    f136_null, _ = _active_oracle_decomposition(pack, basis, pack["oracle"]["holdout"] - f135_predictions["holdout"] - c_const["holdout"]); theta = np.asarray(f136_null["theta_oracle_active"]); null_basis = pack["vt"][~pack["retained"]].T; theta_null = null_basis @ (null_basis.T @ theta)
    gauges, gauge_definitions = _canonical_gauges(basis, pack); span = _span_report(gauges, pack); activation, raw_activation = _gauge_activation(rows, basis, pack, gauges); null_gauge, gauge_predictions, exact_null_predictions = _null_gauge_report(pack, basis, gauges, f135_predictions, c_const); coverage = _coverage_table(rows, basis, pack)
    # Greedy witness selection uses the actual corrected feature columns and original dev ordinals.
    targets = {entry["feature_name"] for entry in coverage["categories"]["DEV_COVERED"]}; by_name = {name: index for index, name in enumerate(basis.names)}; dev_rows = [row for row in rows if row["split"] == "dev"]; uncovered = set(targets); witnesses = []
    while uncovered:
        ranked = []
        for row in dev_rows:
            covers = {name for name in uncovered if abs(row["features"][by_name[name]] - pack["raw"]["train"][0, by_name[name]]) > 1e-12}
            ranked.append((-len(covers), row["ordinal"], row["identity"], covers))
        _, _, selected_identity, covered = min(ranked)
        if not covered: raise RuntimeError("F137_GREEDY_WITNESS_SET_STALLED")
        selected = next(row for row in dev_rows if row["identity"] == selected_identity); newly = sorted(covered); uncovered -= covered
        witnesses.append({"identity": selected["identity"], "original_ordinal": selected["ordinal"], "coordinates_newly_covered": newly, "cumulative_coverage": len(targets) - len(uncovered)})
        dev_rows = [row for row in dev_rows if row["ordinal"] != selected["ordinal"]]
    coverage["deterministic_dev_witness_set"] = {"target_coordinate_count": len(targets), "witness_state_count": len(witnesses), "coverage_fraction": 1.0 if not targets else (len(targets) - len(uncovered)) / len(targets), "witnesses": witnesses}
    holdout_only = coverage["categories"]["HOLDOUT_ONLY"]
    exact_gauge = bool(span["passes"] and null_gauge["relative_reconstruction_error"] <= 1e-10 and all(null_gauge["gauge_vs_exact_null_prediction"][split]["normalized_rmse"] <= 1e-10 for split in ("train", "dev", "holdout")))
    classification = "CORRECTED_A1_NULLSPACE_EXACTLY_MATERIAL_PST_COVERAGE_GAUGE" if exact_gauge else ("CORRECTED_A1_NULLSPACE_MIXED_GAUGE_AND_OTHER_RELATIONS" if span["rank"] > 0 else "CORRECTED_A1_NULLSPACE_NOT_MATERIAL_PST_GAUGE")
    global_break = {}
    for type_id in TYPES:
        material, active_occupancy, omitted_occupancy = _type_indices(basis, pack, type_id)
        all_occupancy = active_occupancy + omitted_occupancy
        global_break[type_id] = {}
        for split in ("train", "dev", "holdout"):
            raw = pack["raw"][split]
            full_identity = raw[:, material] - raw[:, all_occupancy].sum(axis=1)
            reduced = raw[:, material] - raw[:, active_occupancy].sum(axis=1)
            train_reduced = pack["raw"]["train"][0, material] - pack["raw"]["train"][0, active_occupancy].sum()
            omitted_delta = raw[:, omitted_occupancy].sum(axis=1) - pack["raw"]["train"][0, omitted_occupancy].sum() if omitted_occupancy else np.zeros(len(raw))
            reduced_delta = reduced - train_reduced
            global_break[type_id][split] = {"full_identity_max_abs": float(np.max(np.abs(full_identity))), "reduced_relation_is_constant_or_zero": bool(np.max(np.abs(reduced_delta)) <= 1e-12), "reduced_relation_variation_max_abs": float(np.max(np.abs(reduced_delta))), "omitted_coverage_break_max_abs": float(np.max(np.abs(omitted_delta))), "reduced_variation_matches_omitted_break_max_abs": float(np.max(np.abs(reduced_delta - omitted_delta)))}
    result = {"schema": "F137_CORRECTED_SHOGI_NULLSPACE_GAUGE_DECOMPOSITION_V1", "baseline": F137_BASELINE, "f136_reproduction": f136_reproduction, "schema_hashes": {"corrected_oracle_sha256": basis.oracle_weight_sha256, "feature_name_sha256": _json_sha(basis.names), "corpus_sha256": CORPUS_SHA, "corpus_seed": CORPUS_SEED}, "canonical_material_pst_gauges": {"definitions": gauge_definitions, "span": span}, "out_of_sample_gauge_activation": activation, "oracle_null_decomposition": null_gauge, "type_wise_null_error_ranked_by_holdout_rms": sorted(((type_id, data) for type_id, data in null_gauge["type_wise_null_error"].items()), key=lambda item: item[1]["metrics"]["holdout"]["rms_oracle_units"], reverse=True), "global_identity_vs_corpus_specific_break": global_break, "train_constant_occupancy_coverage_table": coverage, "holdout_only_requirement": {"coordinates": holdout_only, "count": len(holdout_only)}, "gauge_error_vs_f135_residual": null_gauge["holdout_gauge_error_vs_f135_residual"], "secondary_flags": {"DEV_STATES_CAN_COVER_ALL_OBSERVED_GAUGE_BREAKS": not bool(holdout_only), "DEV_WITNESS_COUNT": len(witnesses), "HOLDOUT_ONLY_COORDINATE_COUNT": len(holdout_only)}, "classification": classification, "runtime_seconds": time.time() - started}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"); return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args(); result = _run(args.output); print(json.dumps({"classification": result["classification"], "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__": main()
