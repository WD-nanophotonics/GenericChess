"""F138: targeted corrected-Shogi coverage repair and A1 rerun."""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import COUNTS, FrozenBasis, _action_ranking, _collect_fresh_roots, _json_sha, _ranking_summary, _scalar_metrics, _search_probe, _sort_actions
    from scripts.f123_reverse_benchmark_identifiability_optimizer_diagnosis import _matched_ridge, _minimum_norm, _predict, _proxy_fit
    from scripts.f127_shogi_t1_scalar_compression_expanded_control import _pcg_tight
    from scripts.f135_corrected_shogi_oracle_schema_rebaseline import CORPUS_SHA, CORPUS_SEED, CorrectedShogiFrozenBasisV2, FAMILY, _collect_states, _materialize
    from scripts.f136_corrected_shogi_coverage_identifiability import _gate
    from scripts.f137_corrected_shogi_nullspace_gauge_decomposition import F137_BASELINE, TYPES, _canonical_gauges, _coverage_table, _gauge_activation, _span_report
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import COUNTS, FrozenBasis, _action_ranking, _collect_fresh_roots, _json_sha, _ranking_summary, _scalar_metrics, _search_probe, _sort_actions
    from f123_reverse_benchmark_identifiability_optimizer_diagnosis import _matched_ridge, _minimum_norm, _predict, _proxy_fit
    from f127_shogi_t1_scalar_compression_expanded_control import _pcg_tight
    from f135_corrected_shogi_oracle_schema_rebaseline import CORPUS_SHA, CORPUS_SEED, CorrectedShogiFrozenBasisV2, FAMILY, _collect_states, _materialize
    from f136_corrected_shogi_coverage_identifiability import _gate
    from f137_corrected_shogi_nullspace_gauge_decomposition import F137_BASELINE, TYPES, _canonical_gauges, _coverage_table, _gauge_activation, _span_report

from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


BASELINE = "50e02a9be7042b4c89a5313740f78a2165831124"
CORRECTED_ORACLE_SHA = "fdd6405ffa3f92de05f401dbd12d00a16191ac10c2ba2383fe5332694c9e7aa6"
FEATURE_NAME_SHA = "6accfab1039a546071a23c885d582a2c10792e5db49f69bfa9556c131d516942"
GENERATOR_SEED = 1380201
ROOT_SEED = 1220221
L2 = 1e-6
TRAJECTORY_LENGTHS = (8, 24, 64, 128, 192, 256)


def _splits(train, dev, holdout):
    return {"train": train, "dev": dev, "holdout": holdout}


def _prepare_augmented(rows: dict[str, list[dict]], basis) -> dict:
    raw = {split: np.asarray([row["features"] for row in value], dtype=np.float64) for split, value in rows.items()}
    oracle = {split: np.asarray([row["oracle"] for row in value], dtype=np.float64) for split, value in rows.items()}
    train_x = raw["train"]; train_y = oracle["train"]
    mean = train_x.mean(axis=0); scale = train_x.std(axis=0); active = scale > 1e-12; safe_scale = np.where(active, scale, 1.0)
    target_mean = float(train_y.mean()); target_std = float(train_y.std()) or 1.0
    normalized = {split: (value - mean) / safe_scale for split, value in raw.items()}
    design = {split: np.column_stack([value[:, active], np.ones(len(value))]) for split, value in normalized.items()}
    target = {split: (value - target_mean) / target_std for split, value in oracle.items()}
    singular_values = np.linalg.svd(design["train"], full_matrices=False, compute_uv=False)
    left, singular_values, vt = np.linalg.svd(design["train"], full_matrices=False)
    rank_tol = np.finfo(float).eps * max(design["train"].shape) * float(singular_values[0]); retained = singular_values > rank_tol
    return {"raw": raw, "oracle": oracle, "feature_count": len(basis.names), "feature_mean": mean, "feature_scale": safe_scale, "active": active, "constant_feature_names": [name for name, keep in zip(basis.names, active) if not keep], "target_mean": target_mean, "target_std": target_std, "normalized": normalized, "design": design, "target": target, "singular_values": singular_values, "left_vectors": left, "vt": vt, "rank_tol": rank_tol, "retained": retained}


def _scalar_summary(model, pack):
    normalizer = float(np.std(pack["oracle"]["holdout"])) or 1.0
    return {split: _scalar_metrics(pack["oracle"][split], _predict(model, pack, split), normalizer) for split in ("train", "dev", "holdout")}


def _target_value(state, target):
    type_id, file, rank = target.split(":")[1:]
    piece = state.position.board[int(rank) * state.position.board_size() + int(file)]
    if piece is None or piece.current_type_id != type_id: return 0.0
    return 1.0 if piece.owner == state.position.side_to_move else -1.0


def _target_signature(state, targets):
    return {target: _target_value(state, target) for target in targets}


def _dev_witnesses(rows, basis, pack, dev_targets):
    by_name = {name: index for index, name in enumerate(basis.names)}; remaining = set(dev_targets); candidates = [row for row in rows if row["split"] == "dev"]; selected = []
    while remaining:
        ranked = []
        for row in candidates:
            covers = {name for name in remaining if abs(row["features"][by_name[name]] - pack["raw"]["train"][0, by_name[name]]) > 1e-12}
            ranked.append((-len(covers), row["ordinal"], row["identity"], covers))
        _, _, identity, covers = min(ranked)
        if not covers: raise RuntimeError("F138_DEV_WITNESS_TRANSFER_INCOMPLETE")
        row = next(row for row in candidates if row["identity"] == identity); remaining -= covers
        selected.append({"row": row, "identity": row["identity"], "original_ordinal": row["ordinal"], "newly_covered_coordinates": sorted(covers), "cumulative_coverage": len(dev_targets) - len(remaining)})
        candidates = [candidate for candidate in candidates if candidate["identity"] != identity]
    return selected


def _generate_candidates(compiled, targets, train_constants, forbidden):
    target_set = set(targets); covered = set(); candidates = []; seen = set(forbidden); inspected_states = 0; trajectory = 0
    while covered != target_set and trajectory < 20000:
        rng = random.Random(GENERATOR_SEED + 7919 * trajectory); state = initial_state(compiled)
        for ply in range(TRAJECTORY_LENGTHS[trajectory % len(TRAJECTORY_LENGTHS)]):
            actions = _sort_actions(legal_actions(state, compiled))
            if not actions: break
            state = apply_action(state, actions[rng.randrange(len(actions))], compiled)
            if state.terminal_status.status is not TerminalStatus.ONGOING: continue
            identity = str(position_identity_key(state.position, compiled)); inspected_states += 1
            if identity in seen: continue
            values = _target_signature(state, targets); newly = {target for target, value in values.items() if abs(value - train_constants[target]) > 1e-12}
            if not newly: continue
            seen.add(identity); candidates.append({"state": state, "identity": identity, "trajectory": trajectory, "ply": ply + 1, "covers": newly}); covered |= newly
            if covered == target_set: break
        trajectory += 1
    return candidates, {"covered": sorted(covered), "uncovered": sorted(target_set - covered), "trajectory_count": trajectory, "inspected_legal_states": inspected_states}


def _minimize_candidates(candidates, targets):
    remaining = set(targets); chosen = []
    while remaining:
        ranked = sorted(candidates, key=lambda row: (-len(row["covers"] & remaining), row["trajectory"], row["ply"], row["identity"]))
        best = ranked[0]; gain = best["covers"] & remaining
        if not gain: raise RuntimeError("F138_GENERATED_WITNESS_SET_STALLED")
        remaining -= gain; chosen.append({**best, "newly_covered_coordinates": sorted(gain), "cumulative_coverage": len(targets) - len(remaining)})
        candidates = [row for row in candidates if row["identity"] != best["identity"]]
    return chosen


def _materialize_generated(selected, basis):
    output = []
    for item in selected:
        features = basis.vector(item["state"])
        output.append({"identity": item["identity"], "ordinal": None, "split": "generated", "trajectory": item["trajectory"], "ply": item["ply"], "state": item["state"], "features": features.tolist(), "oracle": float(basis.oracle(features)), "newly_covered_coordinates": item["newly_covered_coordinates"], "cumulative_coverage": item["cumulative_coverage"]})
    return output


def _fit_report(pack):
    matched = _matched_ridge(pack); pcg, trace = _pcg_tight(pack)
    design = pack["design"]["train"]; target = pack["target"]["train"]
    objective = lambda candidate: float(0.5 * np.mean((design @ candidate - target) ** 2) + 0.5 * L2 * np.sum(candidate[:-1] * candidate[:-1]))
    numerical = {"finite_parameters": bool(np.all(np.isfinite(pcg))), "relative_residual": trace["relative_residual"], "objective_excess": objective(pcg) - objective(matched), "prediction_difference_holdout_normalized_rmse": float(np.sqrt(np.mean((_predict(pcg, pack, "holdout") - _predict(matched, pack, "holdout")) ** 2)) / (float(np.std(pack["oracle"]["holdout"])) or 1.0))}
    numerical["pass"] = bool(numerical["finite_parameters"] and numerical["relative_residual"] <= 1e-10 and numerical["objective_excess"] <= 1e-10 and numerical["prediction_difference_holdout_normalized_rmse"] <= 1e-8)
    return {"matched": matched, "pcg": pcg, "trace": trace, "numerical": numerical, "scalar": _scalar_summary(pcg, pack), "matched_scalar": _scalar_summary(matched, pack)}


def _surface_identity_report(rows, original_holdout):
    surfaces = {split: [row["identity"] for row in value] for split, value in rows.items()}; all_ids = [identity for values in surfaces.values() for identity in values]
    return {"counts": {split: len(values) for split, values in surfaces.items()}, "within_surface_unique": {split: len(values) == len(set(values)) for split, values in surfaces.items()}, "cross_surface_disjoint": len(all_ids) == len(set(all_ids)), "holdout_identity_sha256": _json_sha(surfaces["holdout"]), "original_holdout_identity_sha256": _json_sha(original_holdout), "holdout_byte_and_identity_preserved": surfaces["holdout"] == original_holdout}


def _run(output: Path) -> dict:
    started = time.time(); compiled = compile_semantic_ruleset(build_standard_shogi_ruleset()); basis = CorrectedShogiFrozenBasisV2(FAMILY, compiled)
    if basis.oracle_weight_sha256 != CORRECTED_ORACLE_SHA or _json_sha(basis.names) != FEATURE_NAME_SHA: raise RuntimeError("F138_CORRECTED_SCHEMA_HASH_MISMATCH")
    states = _collect_states(compiled); original = _materialize(states, basis); original_pack = _prepare_augmented({"train": original[:3000], "dev": original[3000:3750], "holdout": original[3750:]}, basis)
    if _json_sha([row["identity"] for row in states]) != CORPUS_SHA: raise RuntimeError("F138_FROZEN_CORPUS_IDENTITY_MISMATCH")
    original_coverage = _coverage_table(original, basis, original_pack); dev_targets = {entry["feature_name"] for entry in original_coverage["categories"]["DEV_COVERED"]}; holdout_targets = {entry["feature_name"] for entry in original_coverage["categories"]["HOLDOUT_ONLY"]}
    if len(dev_targets) != 33 or len(holdout_targets) != 37 or len(original_coverage["categories"]["NEVER_OBSERVED_OUTSIDE_TRAIN"]) != 352: raise RuntimeError("F138_F137_REPRODUCTION_FAILURE")
    dev_selected = _dev_witnesses(original, basis, original_pack, dev_targets)
    if len(dev_selected) != 19: raise RuntimeError("F138_F137_REPRODUCTION_FAILURE")
    forbidden = {row["identity"] for row in states}; roots = _collect_fresh_roots(FAMILY, compiled, basis, ROOT_SEED, forbidden, 256); root_ids = [str(position_identity_key(state.position, compiled)) for state in roots]; forbidden |= set(root_ids)
    train_constants = {target: float(original_pack["raw"]["train"][0, basis.names.index(target)]) for target in holdout_targets}
    generated, generation = _generate_candidates(compiled, sorted(holdout_targets), train_constants, forbidden)
    if generation["uncovered"]: raise RuntimeError("F138_INDEPENDENT_WITNESS_GENERATION_INCOMPLETE")
    generated_selected = _minimize_candidates(generated, sorted(holdout_targets)); generated_rows = _materialize_generated(generated_selected, basis)
    transferred_rows = [entry["row"] for entry in dev_selected]; transferred_ids = {row["identity"] for row in transferred_rows}; generated_ids = {row["identity"] for row in generated_rows}; original_train = original[:3000]; original_dev_remaining = [row for row in original[3000:3750] if row["identity"] not in transferred_ids]; original_holdout = original[3750:]
    augmented_rows = {"train": original_train + transferred_rows + generated_rows, "dev": original_dev_remaining, "holdout": original_holdout}; surface = _surface_identity_report(augmented_rows, [row["identity"] for row in original_holdout])
    if not surface["cross_surface_disjoint"] or not surface["holdout_byte_and_identity_preserved"] or forbidden & generated_ids: raise RuntimeError("F138_CONTROL_NO_HOLDOUT_LEAKAGE_FAILURE")
    pack = _prepare_augmented(augmented_rows, basis); fit = _fit_report(pack); gauges, gauge_definitions = _canonical_gauges(basis, pack); span = _span_report(gauges, pack); activation, _ = _gauge_activation(augmented_rows["train"] + augmented_rows["dev"] + augmented_rows["holdout"], basis, pack, gauges)
    holdout_activation = {type_id: activation[type_id]["holdout"] for type_id in TYPES}; damaging_gauge_zero = all(value["rms"] <= 1e-10 and value["max_abs"] <= 1e-10 for value in holdout_activation.values())
    ranking_fit = _proxy_fit(fit["pcg"], pack); ranking_fit["pcg_model"] = ranking_fit.pop("adam_model"); action_summary = _ranking_summary(_action_ranking(roots, basis, ranking_fit, "pcg"), float(np.std(pack["oracle"]["holdout"])) or 1.0); action_gate = bool(action_summary["top1_agreement"] >= 0.90 and action_summary["pairwise_ordering_agreement"] >= 0.95 and action_summary["mean_regret_normalized"] <= 0.05)
    search = _search_probe(roots[:64], basis, ranking_fit, "pcg")
    scalar_gate = _gate(fit["scalar"]["holdout"])
    if not fit["numerical"]["pass"]: classification = "F138_CORRECTED_A1_SOLVER_NUMERICAL_FAILURE"
    elif int(len(pack["singular_values"]) - pack["retained"].sum()) != 13 or not span["passes"] or not damaging_gauge_zero: classification = "F138_GAUGE_COVERAGE_REPAIR_INCOMPLETE"
    elif not scalar_gate: classification = "CORRECTED_A1_FAILS_AFTER_IDENTIFIABILITY_REPAIR"
    elif not action_gate: classification = "CORRECTED_A1_SCALAR_PASSES_ACTION_RECOVERY_FAILS"
    else: classification = "CORRECTED_KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_PASSES_ON_IDENTIFYING_SURFACE"
    result = {"schema": "F138_CORRECTED_SHOGI_TARGETED_GAUGE_COVERAGE_A1_V1", "baseline": BASELINE, "f137_reproduction": {"dev_covered": len(dev_targets), "holdout_only": len(holdout_targets), "never_observed_outside_train": len(original_coverage["categories"]["NEVER_OBSERVED_OUTSIDE_TRAIN"]), "dev_witness_count": len(dev_selected), "gauge_rank": span["rank"], "classification": "CORRECTED_A1_NULLSPACE_EXACTLY_MATERIAL_PST_COVERAGE_GAUGE"}, "schema_hashes": {"corrected_oracle_sha256": basis.oracle_weight_sha256, "feature_name_sha256": _json_sha(basis.names), "corpus_sha256": CORPUS_SHA, "corpus_seed": CORPUS_SEED}, "dev_witness_transfer": [{key: entry[key] for key in ("identity", "original_ordinal", "newly_covered_coordinates", "cumulative_coverage")} for entry in dev_selected], "independent_holdout_only_generation": {"generator_seed": GENERATOR_SEED, "trajectory_length_cycle": TRAJECTORY_LENGTHS, "target_coordinates": sorted(holdout_targets), "candidate_witness_count": len(generated), "selected_witness_count": len(generated_selected), "selected_witnesses": [{key: entry[key] for key in ("identity", "trajectory", "ply", "newly_covered_coordinates", "cumulative_coverage")} for entry in generated_selected], "generation": generation}, "training_surface": surface, "coverage_contract": {"active_feature_count": int(pack["active"].sum()), "train_constant_count": len(pack["constant_feature_names"]), "design_width": int(pack["design"]["train"].shape[1]), "numerical_rank": int(pack["retained"].sum()), "nullity": int(len(pack["singular_values"]) - pack["retained"].sum()), "gauge_definitions": gauge_definitions, "gauge_span": span, "holdout_gauge_activation": holdout_activation, "damaging_gauge_activation_zero": damaging_gauge_zero}, "fit": {"numerical": fit["numerical"], "scalar_metrics": fit["scalar"], "matched_ridge_scalar_metrics": fit["matched_scalar"], "scalar_a1_gate_pass": scalar_gate}, "f135_improvement": {"f135_holdout_nrmse": 0.15595845351232307, "f135_holdout_rmse": 211.189237270397, "augmented_holdout_nrmse": fit["scalar"]["holdout"]["normalized_rmse"], "augmented_holdout_rmse": fit["scalar"]["holdout"]["rmse_oracle_units"]}, "action_recovery": {"root_seed": ROOT_SEED, "root_count": len(roots), "root_identity_sequence_sha256": _json_sha(root_ids), "generated_witness_excluded_root_identity_intersection": sorted(generated_ids & set(root_ids)), "metrics": action_summary, "gate_pass": action_gate}, "search_recovery_diagnostic": search, "provenance": {"target_selection_used_only_f137_feature_names": True, "generation_used_no_oracle_values": True, "generation_used_no_holdout_states_or_trajectories": True, "generation_forbidden_original_corpus_and_frozen_roots": True, "set_cover_used_only_target_coverage_and_trajectory_tiebreaks": True, "no_original_holdout_identity_entered_training": True}, "classification": classification, "runtime_seconds": time.time() - started}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"); return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args(); result = _run(args.output); print(json.dumps({"classification": result["classification"], "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__": main()
