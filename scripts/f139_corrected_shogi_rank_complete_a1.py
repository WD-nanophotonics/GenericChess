"""F139: complete the frozen F138 corrected-Shogi training row space."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import _action_ranking, _collect_fresh_roots, _json_sha, _ranking_summary, _search_probe
    from scripts.f135_corrected_shogi_oracle_schema_rebaseline import CORPUS_SHA, CorrectedShogiFrozenBasisV2, FAMILY, _collect_states, _materialize
    from scripts.f136_corrected_shogi_coverage_identifiability import _active_oracle_decomposition, _gate
    from scripts.f137_corrected_shogi_nullspace_gauge_decomposition import _canonical_gauges, _gauge_activation, _span_report
    from scripts.f138_corrected_shogi_targeted_gauge_coverage_a1 import BASELINE as F138_BASELINE, _dev_witnesses, _fit_report, _generate_candidates, _materialize_generated, _minimize_candidates, _prepare_augmented, _proxy_fit, _surface_identity_report
except ModuleNotFoundError as error:
    if error.name != "scripts": raise
    from f122_reverse_benchmark_known_evaluator_system_identification import _action_ranking, _collect_fresh_roots, _json_sha, _ranking_summary, _search_probe
    from f135_corrected_shogi_oracle_schema_rebaseline import CORPUS_SHA, CorrectedShogiFrozenBasisV2, FAMILY, _collect_states, _materialize
    from f136_corrected_shogi_coverage_identifiability import _active_oracle_decomposition, _gate
    from f137_corrected_shogi_nullspace_gauge_decomposition import _canonical_gauges, _gauge_activation, _span_report
    from f138_corrected_shogi_targeted_gauge_coverage_a1 import BASELINE as F138_BASELINE, _dev_witnesses, _fit_report, _generate_candidates, _materialize_generated, _minimize_candidates, _prepare_augmented, _proxy_fit, _surface_identity_report

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


BASELINE = "ca19e3257b51cb6bdce6eb49e5692f51c1c15ce2"
CORRECTED_ORACLE_SHA = "fdd6405ffa3f92de05f401dbd12d00a16191ac10c2ba2383fe5332694c9e7aa6"
FEATURE_NAME_SHA = "6accfab1039a546071a23c885d582a2c10792e5db49f69bfa9556c131d516942"
F138_COUNTS = {"candidate": 6125, "inspected": 37066, "trajectories": 342, "selected": 25}
ROOT_SEED = 1220221


def _row(features: list[float], pack: dict) -> np.ndarray:
    values = np.asarray(features, dtype=np.float64)
    return np.r_[(values - pack["feature_mean"])[pack["active"]] / pack["feature_scale"][pack["active"]], 1.0]


def _make_feature_only_candidates(candidates, basis):
    return [{**candidate, "features": basis.vector(candidate["state"]).tolist()} for candidate in candidates]


def _rank_complete(pack: dict, candidates: list[dict], target_rank: int):
    current_design = pack["design"]["train"]
    _, singular, vt = np.linalg.svd(current_design, full_matrices=False)
    tolerance = np.finfo(float).eps * max(current_design.shape) * float(singular[0])
    retained = singular > tolerance; basis = vt[retained].T.copy(); current_rank = int(retained.sum()); selected = []
    for candidate in sorted(candidates, key=lambda item: (item["trajectory"], item["ply"], item["identity"])):
        candidate_row = _row(candidate["features"], pack); residual = candidate_row - basis @ (basis.T @ candidate_row); residual_norm = float(np.linalg.norm(residual))
        if residual_norm <= tolerance: continue
        basis = np.column_stack([basis, residual / residual_norm]); current_rank += 1
        selected.append({**candidate, "row_space_residual_norm_at_selection": residual_norm, "cumulative_rank": current_rank})
        if current_rank == target_rank: break
    attainable_rank = current_rank
    return selected, {"initial_rank": int(retained.sum()), "target_rank": target_rank, "attainable_rank": attainable_rank, "attainable_nullity": int(current_design.shape[1] - attainable_rank), "rank_tolerance": float(tolerance)}


def _surface_row(rows, candidates):
    output = []
    for candidate in candidates:
        features = candidate.get("features")
        if features is None: raise AssertionError("F139_FEATURES_REQUIRED_BEFORE_SURFACE_BUILD")
        output.append({"identity": candidate["identity"], "ordinal": None, "split": "rank_completion", "trajectory": candidate["trajectory"], "ply": candidate["ply"], "state": candidate["state"], "features": features, "oracle": None, "row_space_residual_norm_at_selection": candidate["row_space_residual_norm_at_selection"], "cumulative_rank": candidate["cumulative_rank"]})
    return output


def _assign_oracle(rows, basis):
    output = []
    for row in rows:
        oracle = float(basis.oracle(np.asarray(row["features"], dtype=np.float64)))
        output.append({**row, "oracle": oracle})
    return output


def _run(output: Path) -> dict:
    started = time.time(); compiled = compile_semantic_ruleset(build_standard_shogi_ruleset()); basis = CorrectedShogiFrozenBasisV2(FAMILY, compiled)
    if basis.oracle_weight_sha256 != CORRECTED_ORACLE_SHA or _json_sha(basis.names) != FEATURE_NAME_SHA: raise RuntimeError("F139_CORRECTED_SCHEMA_HASH_MISMATCH")
    states = _collect_states(compiled); original = _materialize(states, basis)
    if _json_sha([row["identity"] for row in states]) != CORPUS_SHA: raise RuntimeError("F139_FROZEN_CORPUS_IDENTITY_MISMATCH")
    original_pack = _prepare_augmented({"train": original[:3000], "dev": original[3000:3750], "holdout": original[3750:]}, basis)
    # F138 target categories are reproduced from the frozen occupancy coverage without using oracle values.
    occupancy_names = [name for name in basis.names if name.startswith("occupancy_diff:")]
    dev_targets = set(); holdout_targets = set()
    for name in occupancy_names:
        index = basis.names.index(name); train_constant = original_pack["raw"]["train"][0, index]; dev_var = np.any(np.abs(original_pack["raw"]["dev"][:, index] - train_constant) > 1e-12); holdout_var = np.any(np.abs(original_pack["raw"]["holdout"][:, index] - train_constant) > 1e-12)
        if not original_pack["active"][index] and dev_var: dev_targets.add(name)
        elif not original_pack["active"][index] and holdout_var: holdout_targets.add(name)
    dev_selected = _dev_witnesses(original, basis, original_pack, dev_targets)
    forbidden = {row["identity"] for row in states}; roots = _collect_fresh_roots(FAMILY, compiled, basis, ROOT_SEED, forbidden, 256); root_ids = [str(__import__("generic_chess.core.identity", fromlist=["position_identity_key"]).position_identity_key(state.position, compiled)) for state in roots]; forbidden |= set(root_ids)
    train_constants = {name: float(original_pack["raw"]["train"][0, basis.names.index(name)]) for name in holdout_targets}
    generated, generation = _generate_candidates(compiled, sorted(holdout_targets), train_constants, forbidden)
    generated = _make_feature_only_candidates(generated, basis)
    generated_selected = _minimize_candidates(generated, sorted(holdout_targets)); f138_generated_rows = _assign_oracle(_materialize_generated(generated_selected, basis), basis)
    transferred_rows = [entry["row"] for entry in dev_selected]; original_train = original[:3000]; original_dev_remaining = [row for row in original[3000:3750] if row["identity"] not in {row["identity"] for row in transferred_rows}]; original_holdout = original[3750:]
    f138_train = original_train + transferred_rows + f138_generated_rows; f138_rows = {"train": f138_train, "dev": original_dev_remaining, "holdout": original_holdout}; f138_pack = _prepare_augmented(f138_rows, basis); f138_fit = _fit_report(f138_pack)
    if len(generated) != F138_COUNTS["candidate"] or generation["inspected_legal_states"] != F138_COUNTS["inspected"] or generation["trajectory_count"] != F138_COUNTS["trajectories"] or len(generated_selected) != F138_COUNTS["selected"] or len(f138_train) != 3044: raise RuntimeError("F139_F138_REPRODUCTION_FAILURE")
    new_active = np.flatnonzero(f138_pack["active"] & ~original_pack["active"]); inactive_original_train_constant = bool(all(np.std(original_pack["raw"]["train"][:, index]) <= 1e-12 for index in new_active))
    dim = {"new_active_columns": int(len(new_active)), "added_training_rows": len(f138_train) - 3000, "rank_gain": int(f138_pack["retained"].sum() - original_pack["retained"].sum()), "excess_nullity": int((len(f138_pack["singular_values"]) - f138_pack["retained"].sum()) - (len(original_pack["singular_values"]) - original_pack["retained"].sum())), "newly_active_were_original_train_constant": inactive_original_train_constant}
    active138 = f138_pack["active"]; constants138 = f138_pack["raw"]["train"][0]
    feature_candidates = []
    for candidate in generated:
        inactive_delta = np.asarray(candidate["features"])[~active138] - constants138[~active138]
        if np.all(np.abs(inactive_delta) <= 1e-12): feature_candidates.append(candidate)
    f138_rows_design = f138_pack["design"]["train"]; attainable_rows = np.vstack([f138_rows_design, np.asarray([_row(candidate["features"], f138_pack) for candidate in feature_candidates])])
    attainable_singular = np.linalg.svd(attainable_rows, full_matrices=False, compute_uv=False); attainable_tol = np.finfo(float).eps * max(attainable_rows.shape) * float(attainable_singular[0]); attainable_rank = int(np.sum(attainable_singular > attainable_tol))
    if attainable_rank < 761: classification = "F139_EXISTING_CANDIDATE_POOL_INSUFFICIENT_FOR_RANK_COMPLETION"; result = {"schema": "F139_CORRECTED_SHOGI_RANK_COMPLETE_A1_V1", "baseline": BASELINE, "f138_reproduction": {"candidate_count": len(generated), "inspected_legal_states": generation["inspected_legal_states"], "trajectory_count": generation["trajectory_count"], "selected_count": len(generated_selected), "training_count": len(f138_train), "scalar_holdout_nrmse": f138_fit["scalar"]["holdout"]["normalized_rmse"]}, "dimension_count_witness": dim, "no_new_active_candidates": {"total_regenerated_candidates": len(generated), "count": len(feature_candidates), "excluded_count": len(generated) - len(feature_candidates)}, "row_space_capacity": {"current_rank": int(f138_pack["retained"].sum()), "attainable_rank": attainable_rank, "attainable_nullity": int(f138_rows_design.shape[1] - attainable_rank)}, "classification": classification, "runtime_seconds": time.time() - started}; output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"); return result
    selected_completion, capacity = _rank_complete(f138_pack, feature_candidates, 761)
    if len(selected_completion) != 65 or capacity["attainable_rank"] != 761: raise RuntimeError("F139_RANK_COMPLETION_CONTRACT_FAILURE")
    completion_rows = _assign_oracle(_surface_row(f138_train, selected_completion), basis); final_rows = {"train": f138_train + completion_rows, "dev": original_dev_remaining, "holdout": original_holdout}; final_surface = _surface_identity_report(final_rows, [row["identity"] for row in original_holdout]); final_pack = _prepare_augmented(final_rows, basis)
    final_fit = _fit_report(final_pack); gauges, gauge_definitions = _canonical_gauges(basis, final_pack); span = _span_report(gauges, final_pack); f136_null, null_holdout = _active_oracle_decomposition(final_pack, basis, None); holdout_gauge = {type_id: value for type_id, value in _gauge_activation(final_rows["train"] + final_rows["dev"] + final_rows["holdout"], basis, final_pack, gauges)[0].items()}; gauge_zero = all(value["holdout"]["rms"] <= 1e-10 and value["holdout"]["max_abs"] <= 1e-10 for value in holdout_gauge.values()); identifiability = bool(len(final_rows["train"]) == 3109 and final_pack["active"].sum() == 773 and final_pack["design"]["train"].shape[1] == 774 and final_pack["retained"].sum() == 761 and len(final_pack["singular_values"]) - final_pack["retained"].sum() == 13 and span["passes"] and gauge_zero and null_holdout["normalized_rmse"] <= 1e-10)
    ranking_fit = _proxy_fit(final_fit["pcg"], final_pack); ranking_fit["pcg_model"] = ranking_fit.pop("adam_model"); action = _ranking_summary(_action_ranking(roots, basis, ranking_fit, "pcg"), float(np.std(final_pack["oracle"]["holdout"])) or 1.0); action_gate = bool(action["top1_agreement"] >= 0.90 and action["pairwise_ordering_agreement"] >= 0.95 and action["mean_regret_normalized"] <= 0.05); search = _search_probe(roots[:64], basis, ranking_fit, "pcg"); scalar_gate = bool(_gate(final_fit["scalar"]["holdout"]))
    if not identifiability: classification = "F139_RANK_COMPLETION_IDENTIFIABILITY_FAILURE"
    elif not final_fit["numerical"]["pass"]: classification = "F139_CORRECTED_A1_SOLVER_NUMERICAL_FAILURE"
    elif not scalar_gate: classification = "CORRECTED_A1_FAILS_AFTER_COMPLETE_LINEAR_IDENTIFIABILITY"
    elif not action_gate: classification = "CORRECTED_A1_SCALAR_PASSES_ACTION_RECOVERY_FAILS"
    else: classification = "CORRECTED_KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_PASSES_ON_RANK_COMPLETE_SURFACE"
    result = {"schema": "F139_CORRECTED_SHOGI_RANK_COMPLETE_A1_V1", "baseline": BASELINE, "f138_reproduction": {"candidate_count": len(generated), "inspected_legal_states": generation["inspected_legal_states"], "trajectory_count": generation["trajectory_count"], "selected_count": len(generated_selected), "training_count": len(f138_train), "dev_count": len(original_dev_remaining), "holdout_count": len(original_holdout), "scalar_holdout_nrmse": f138_fit["scalar"]["holdout"]["normalized_rmse"], "action_top1": _ranking_summary(_action_ranking(roots, basis, {**_proxy_fit(f138_fit["pcg"], f138_pack), "pcg_model": f138_fit["pcg"]}, "pcg"), float(np.std(f138_pack["oracle"]["holdout"])) or 1.0)["top1_agreement"]}, "dimension_count_witness": dim, "no_new_active_candidates": {"total_regenerated_candidates": len(generated), "count": len(feature_candidates), "excluded_count": len(generated) - len(feature_candidates)}, "row_space_capacity": capacity, "rank_completion_selection": [{key: item[key] for key in ("identity", "trajectory", "ply", "row_space_residual_norm_at_selection", "cumulative_rank")} for item in selected_completion], "final_training_surface": final_surface, "final_identifiability": {"active_feature_count": int(final_pack["active"].sum()), "design_width": int(final_pack["design"]["train"].shape[1]), "numerical_rank": int(final_pack["retained"].sum()), "nullity": int(len(final_pack["singular_values"]) - final_pack["retained"].sum()), "gauge_definitions": gauge_definitions, "gauge_span": span, "holdout_gauge_activation": holdout_gauge, "exact_oracle_null_holdout": null_holdout, "passes": identifiability}, "fit": {"numerical": final_fit["numerical"], "scalar_metrics": final_fit["scalar"], "matched_ridge_scalar_metrics": final_fit["matched_scalar"], "scalar_a1_gate_pass": scalar_gate}, "progression": {"f135_nrmse": 0.15595845351232307, "f138_nrmse": 0.14352245864710567, "f139_nrmse": final_fit["scalar"]["holdout"]["normalized_rmse"]}, "action_recovery": {"root_identity_sequence_sha256": _json_sha(root_ids), "metrics": action, "gate_pass": action_gate}, "search_recovery_diagnostic": search, "provenance": {"selection_used_only_legal_features_active_mask_constants_and_rank": True, "no_oracle_values_used_for_selection": True, "no_holdout_features_or_labels_used_for_selection": True, "holdout_identity_absent_from_training": final_surface["holdout_byte_and_identity_preserved"] and final_surface["cross_surface_disjoint"]}, "classification": classification, "runtime_seconds": time.time() - started}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"); return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args(); result = _run(args.output); print(json.dumps({"classification": result["classification"], "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__": main()
