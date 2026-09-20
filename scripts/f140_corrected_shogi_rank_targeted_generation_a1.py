"""F140: targeted continuation to complete the frozen corrected-Shogi rank."""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import _action_ranking, _collect_fresh_roots, _json_sha, _ranking_summary, _search_probe, _sort_actions, _scalar_metrics
    from scripts.f123_reverse_benchmark_identifiability_optimizer_diagnosis import _minimum_norm, _predict
    from scripts.f135_corrected_shogi_oracle_schema_rebaseline import CORPUS_SHA, CorrectedShogiFrozenBasisV2, FAMILY, _collect_states, _materialize
    from scripts.f136_corrected_shogi_coverage_identifiability import _active_oracle_decomposition, _gate
    from scripts.f137_corrected_shogi_nullspace_gauge_decomposition import _canonical_gauges, _gauge_activation, _span_report
    from scripts.f138_corrected_shogi_targeted_gauge_coverage_a1 import _dev_witnesses, _fit_report, _generate_candidates, _materialize_generated, _minimize_candidates, _prepare_augmented, _proxy_fit, _surface_identity_report, TRAJECTORY_LENGTHS, GENERATOR_SEED
    from scripts.f139_corrected_shogi_rank_complete_a1 import F138_COUNTS, _rank_complete, _row
except ModuleNotFoundError as error:
    if error.name != "scripts": raise
    from f122_reverse_benchmark_known_evaluator_system_identification import _action_ranking, _collect_fresh_roots, _json_sha, _ranking_summary, _search_probe, _sort_actions, _scalar_metrics
    from f123_reverse_benchmark_identifiability_optimizer_diagnosis import _minimum_norm, _predict
    from f135_corrected_shogi_oracle_schema_rebaseline import CORPUS_SHA, CorrectedShogiFrozenBasisV2, FAMILY, _collect_states, _materialize
    from f136_corrected_shogi_coverage_identifiability import _active_oracle_decomposition, _gate
    from f137_corrected_shogi_nullspace_gauge_decomposition import _canonical_gauges, _gauge_activation, _span_report
    from f138_corrected_shogi_targeted_gauge_coverage_a1 import _dev_witnesses, _fit_report, _generate_candidates, _materialize_generated, _minimize_candidates, _prepare_augmented, _proxy_fit, _surface_identity_report, TRAJECTORY_LENGTHS, GENERATOR_SEED
    from f139_corrected_shogi_rank_complete_a1 import F138_COUNTS, _rank_complete, _row

from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


BASELINE = "c0a0bf38dbeaa1d0b196b59fe649c91fd39f2132"
CORRECTED_ORACLE_SHA = "fdd6405ffa3f92de05f401dbd12d00a16191ac10c2ba2383fe5332694c9e7aa6"
FEATURE_NAME_SHA = "6accfab1039a546071a23c885d582a2c10792e5db49f69bfa9556c131d516942"
ROOT_SEED = 1220221


def _continue_rank(compiled, basis, f138_pack, existing_rows, forbidden, start_trajectory=342):
    train_design = np.vstack([f138_pack["design"]["train"], np.asarray(existing_rows)])
    singular = np.linalg.svd(train_design, full_matrices=False, compute_uv=False)
    tolerance = np.finfo(float).eps * max(train_design.shape) * float(singular[0]); left, singular, vt = np.linalg.svd(train_design, full_matrices=False); current_rank = int(np.sum(singular > tolerance)); row_basis = vt[singular > tolerance].T.copy()
    seen = set(forbidden); accepted = []; inspected = 0; admissible = 0; trajectory = start_trajectory
    while current_rank < 761 and trajectory < 20000:
        rng = random.Random(GENERATOR_SEED + 7919 * trajectory); state = initial_state(compiled)
        for ply in range(TRAJECTORY_LENGTHS[trajectory % len(TRAJECTORY_LENGTHS)]):
            actions = _sort_actions(legal_actions(state, compiled))
            if not actions: break
            state = apply_action(state, actions[rng.randrange(len(actions))], compiled)
            if state.terminal_status.status is not TerminalStatus.ONGOING: continue
            inspected += 1; identity = str(position_identity_key(state.position, compiled))
            if identity in seen: continue
            features = basis.vector(state).tolist(); inactive_delta = np.asarray(features)[~f138_pack["active"]] - f138_pack["raw"]["train"][0, ~f138_pack["active"]]
            if np.any(np.abs(inactive_delta) > 1e-12): continue
            admissible += 1; candidate_row = _row(features, f138_pack); residual = candidate_row - row_basis @ (row_basis.T @ candidate_row); residual_norm = float(np.linalg.norm(residual))
            if residual_norm <= tolerance: continue
            seen.add(identity); row_basis = np.column_stack([row_basis, residual / residual_norm]); current_rank += 1; accepted.append({"identity": identity, "trajectory": trajectory, "ply": ply + 1, "state": state, "features": features, "row_space_residual_norm_at_selection": residual_norm, "cumulative_rank": current_rank})
            if current_rank == 761: break
        trajectory += 1
    return accepted, {"start_trajectory": start_trajectory, "trajectories_searched": trajectory - start_trajectory, "final_rank": current_rank, "missing_rank_count": max(0, 761 - current_rank), "legal_ongoing_states_inspected": inspected, "no_new_active_admissible_state_count": admissible, "rank_increasing_state_count": len(accepted), "rank_tolerance": float(tolerance)}


def _assign_oracle(rows, basis):
    return [{**row, "oracle": float(basis.oracle(np.asarray(row["features"], dtype=np.float64)))} for row in rows]


def _run(output: Path) -> dict:
    started = time.time(); compiled = compile_semantic_ruleset(build_standard_shogi_ruleset()); basis = CorrectedShogiFrozenBasisV2(FAMILY, compiled)
    if basis.oracle_weight_sha256 != CORRECTED_ORACLE_SHA or _json_sha(basis.names) != FEATURE_NAME_SHA: raise RuntimeError("F140_CORRECTED_SCHEMA_HASH_MISMATCH")
    states = _collect_states(compiled); original = _materialize(states, basis)
    if _json_sha([row["identity"] for row in states]) != CORPUS_SHA: raise RuntimeError("F140_FROZEN_CORPUS_IDENTITY_MISMATCH")
    original_pack = _prepare_augmented({"train": original[:3000], "dev": original[3000:3750], "holdout": original[3750:]}, basis); occupancy_names = [name for name in basis.names if name.startswith("occupancy_diff:")]; dev_targets = set(); holdout_targets = set()
    for name in occupancy_names:
        index = basis.names.index(name); train_constant = original_pack["raw"]["train"][0, index]; dev_var = np.any(np.abs(original_pack["raw"]["dev"][:, index] - train_constant) > 1e-12); holdout_var = np.any(np.abs(original_pack["raw"]["holdout"][:, index] - train_constant) > 1e-12)
        if not original_pack["active"][index] and dev_var: dev_targets.add(name)
        elif not original_pack["active"][index] and holdout_var: holdout_targets.add(name)
    dev_selected = _dev_witnesses(original, basis, original_pack, dev_targets); forbidden = {row["identity"] for row in states}; roots = _collect_fresh_roots(FAMILY, compiled, basis, ROOT_SEED, forbidden, 256); root_ids = [str(position_identity_key(state.position, compiled)) for state in roots]; forbidden |= set(root_ids); constants = {name: float(original_pack["raw"]["train"][0, basis.names.index(name)]) for name in holdout_targets}; generated, generation = _generate_candidates(compiled, sorted(holdout_targets), constants, forbidden); generated_features = [{**candidate, "features": basis.vector(candidate["state"]).tolist()} for candidate in generated]; f138_selected = _minimize_candidates(generated_features, sorted(holdout_targets)); f138_generated_rows = _assign_oracle(_materialize_generated(f138_selected, basis), basis); transferred_rows = [entry["row"] for entry in dev_selected]; transfer_ids = {row["identity"] for row in transferred_rows}; original_dev_remaining = [row for row in original[3000:3750] if row["identity"] not in transfer_ids]; original_holdout = original[3750:]; f138_rows = {"train": original[:3000] + transferred_rows + f138_generated_rows, "dev": original_dev_remaining, "holdout": original_holdout}; f138_pack = _prepare_augmented(f138_rows, basis)
    if len(generated) != 6125 or generation["inspected_legal_states"] != 37066 or generation["trajectory_count"] != 342 or len(f138_selected) != 25 or len(f138_rows["train"]) != 3044 or int(f138_pack["active"].sum()) != 773 or f138_pack["design"]["train"].shape[1] != 774 or int(f138_pack["retained"].sum()) != 696 or int(len(f138_pack["singular_values"]) - f138_pack["retained"].sum()) != 78: raise RuntimeError("F140_F139_REPRODUCTION_FAILURE")
    active138 = f138_pack["active"]; feature_candidates = [candidate for candidate in generated_features if np.all(np.abs(np.asarray(candidate["features"])[~active138] - f138_pack["raw"]["train"][0, ~active138]) <= 1e-12)]; existing_selected, capacity = _rank_complete(f138_pack, feature_candidates, 751)
    if len(feature_candidates) != 2096 or capacity["attainable_rank"] != 751 or len(existing_selected) != 55: raise RuntimeError("F140_EXISTING_POOL_SELECTION_REPRODUCTION_FAILURE")
    existing_rows = [{"identity": row["identity"], "trajectory": row["trajectory"], "ply": row["ply"], "features": row["features"], "state": row["state"], "row_space_residual_norm_at_selection": row["row_space_residual_norm_at_selection"], "cumulative_rank": row["cumulative_rank"]} for row in existing_selected]
    forbidden |= {row["identity"] for row in f138_selected} | {row["identity"] for row in existing_selected}
    continuation, continuation_report = _continue_rank(compiled, basis, f138_pack, [_row(row["features"], f138_pack) for row in existing_rows], forbidden)
    if len(continuation) != 10 or continuation_report["final_rank"] != 761:
        result = {"schema": "F140_CORRECTED_SHOGI_RANK_TARGETED_GENERATION_A1_V1", "baseline": BASELINE, "f139_reproduction": {"f138_train_count": len(f138_rows["train"]), "f138_active": int(f138_pack["active"].sum()), "f138_design_width": int(f138_pack["design"]["train"].shape[1]), "f138_rank": int(f138_pack["retained"].sum()), "f138_nullity": int(len(f138_pack["singular_values"]) - f138_pack["retained"].sum()), "candidate_count": len(generated), "no_new_active_candidates": len(feature_candidates), "attainable_rank": capacity["attainable_rank"], "attainable_nullity": capacity["attainable_nullity"]}, "existing_pool_selection_count": len(existing_selected), "targeted_generation": continuation_report, "classification": "F140_TARGETED_RANK_GENERATION_INCOMPLETE", "runtime_seconds": time.time() - started}
        output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"); return result
    continuation_rows = _assign_oracle(continuation, basis); final_rows = {"train": f138_rows["train"] + _assign_oracle(existing_rows, basis) + continuation_rows, "dev": original_dev_remaining, "holdout": original_holdout}; final_surface = _surface_identity_report(final_rows, [row["identity"] for row in original_holdout]); final_pack = _prepare_augmented(final_rows, basis); gauges, gauge_definitions = _canonical_gauges(basis, final_pack); span = _span_report(gauges, final_pack); _, null_holdout = _active_oracle_decomposition(final_pack, basis, None); holdout_gauge = _gauge_activation(final_rows["train"] + final_rows["dev"] + final_rows["holdout"], basis, final_pack, gauges)[0]; gauge_zero = all(value["holdout"]["rms"] <= 1e-10 and value["holdout"]["max_abs"] <= 1e-10 for value in holdout_gauge.values()); identifiability = bool(len(final_rows["train"]) == 3109 and final_pack["active"].sum() == 773 and final_pack["design"]["train"].shape[1] == 774 and final_pack["retained"].sum() == 761 and len(final_pack["singular_values"]) - final_pack["retained"].sum() == 13 and span["passes"] and gauge_zero and null_holdout["normalized_rmse"] <= 1e-10)
    fit = _fit_report(final_pack); minnorm = np.zeros_like(fit["pcg"]); # populated below from the exact active SVD control
    minnorm = _minimum_norm(final_pack); normalizer = float(np.std(final_pack["oracle"]["holdout"])) or 1.0; min_predictions = {split: _predict(minnorm, final_pack, split) for split in ("train", "dev", "holdout")}; min_scalar = {split: _scalar_metrics(final_pack["oracle"][split], min_predictions[split], normalizer) for split in ("train", "dev", "holdout")}; ranking_fit = _proxy_fit(fit["pcg"], final_pack); ranking_fit["pcg_model"] = ranking_fit.pop("adam_model"); action = _ranking_summary(_action_ranking(roots, basis, ranking_fit, "pcg"), normalizer); action_gate = bool(action["top1_agreement"] >= 0.90 and action["pairwise_ordering_agreement"] >= 0.95 and action["mean_regret_normalized"] <= 0.05); search = _search_probe(roots[:64], basis, ranking_fit, "pcg"); scalar_gate = _gate(fit["scalar"]["holdout"])
    if not identifiability: classification = "F140_FINAL_IDENTIFIABILITY_FAILURE"
    elif not fit["numerical"]["pass"]: classification = "F140_CORRECTED_A1_SOLVER_NUMERICAL_FAILURE"
    elif not scalar_gate: classification = "CORRECTED_A1_FAILS_AFTER_COMPLETE_LINEAR_IDENTIFIABILITY"
    elif not action_gate: classification = "CORRECTED_A1_SCALAR_PASSES_ACTION_RECOVERY_FAILS"
    else: classification = "CORRECTED_KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_PASSES_ON_RANK_COMPLETE_SURFACE"
    result = {"schema": "F140_CORRECTED_SHOGI_RANK_TARGETED_GENERATION_A1_V1", "baseline": BASELINE, "f139_reproduction": {"f138_train_count": len(f138_rows["train"]), "f138_active": int(f138_pack["active"].sum()), "f138_design_width": int(f138_pack["design"]["train"].shape[1]), "f138_rank": int(f138_pack["retained"].sum()), "f138_nullity": int(len(f138_pack["singular_values"]) - f138_pack["retained"].sum()), "candidate_count": len(generated), "no_new_active_candidates": len(feature_candidates), "attainable_rank": capacity["attainable_rank"], "attainable_nullity": capacity["attainable_nullity"], "dimension_identity": {"target_rank_gain": 65, "existing_pool_rank_gain": 55, "targeted_rank_gain": 10}}, "existing_pool_selection": [{key: row[key] for key in ("identity", "trajectory", "ply", "row_space_residual_norm_at_selection", "cumulative_rank")} for row in existing_selected], "targeted_generation": {**continuation_report, "selected_witnesses": [{key: row[key] for key in ("identity", "trajectory", "ply", "row_space_residual_norm_at_selection", "cumulative_rank")} for row in continuation]}, "final_training_surface": final_surface, "final_identifiability": {"active_feature_count": int(final_pack["active"].sum()), "train_constant_count": len(final_pack["constant_feature_names"]), "design_width": int(final_pack["design"]["train"].shape[1]), "numerical_rank": int(final_pack["retained"].sum()), "nullity": int(len(final_pack["singular_values"]) - final_pack["retained"].sum()), "gauge_definitions": gauge_definitions, "gauge_span": span, "holdout_gauge_activation": holdout_gauge, "exact_oracle_null_holdout": null_holdout, "passes": identifiability}, "fit": {"numerical": fit["numerical"], "scalar_metrics": fit["scalar"], "matched_ridge_scalar_metrics": fit["matched_scalar"], "scalar_a1_gate_pass": scalar_gate}, "active_minimum_norm_control": {"scalar_metrics": min_scalar, "holdout_prediction_difference_vs_matched_rmse": float(np.sqrt(np.mean((min_predictions["holdout"] - _predict(fit["matched"], final_pack, "holdout")) ** 2)))}, "progression": {"f135_nrmse": 0.15595845351232307, "f138_nrmse": 0.14352245864710567, "f140_nrmse": fit["scalar"]["holdout"]["normalized_rmse"]}, "action_recovery": {"root_identity_sequence_sha256": _json_sha(root_ids), "metrics": action, "gate_pass": action_gate}, "search_recovery_diagnostic": search, "provenance": {"selection_used_only_features_mask_constants_normalization_and_rank": True, "no_oracle_before_acceptance": True, "no_holdout_features_or_labels_for_selection": True, "holdout_identity_absent_from_training": final_surface["holdout_byte_and_identity_preserved"] and final_surface["cross_surface_disjoint"]}, "classification": classification, "runtime_seconds": time.time() - started}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"); return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args(); result = _run(args.output); print(json.dumps({"classification": result["classification"], "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__": main()
