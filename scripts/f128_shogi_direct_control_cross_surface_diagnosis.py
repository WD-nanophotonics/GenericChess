"""F128: attribute the F127 direct-control miss across frozen surfaces."""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import (
        COUNTS,
        FrozenBasis,
        _json_sha,
        _scalar_metrics,
    )
    from scripts.f125_known_oracle_one_ply_search_compression import _prepare_filtered, _sorted_actions
    from scripts.f127_shogi_t1_scalar_compression_expanded_control import eligibility_from_children
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import COUNTS, FrozenBasis, _json_sha, _scalar_metrics
    from f125_known_oracle_one_ply_search_compression import _prepare_filtered, _sorted_actions
    from f127_shogi_t1_scalar_compression_expanded_control import eligibility_from_children

from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


FAMILY = "standard_shogi"
BASELINE = "41277d6001b2f546cf5591f02cb29a108b241647"
CORPUS_SEED = 1220201
ORACLE_HASH = "dda316e263a8f6e5a12678199e87cbedea7e4d40358d3087e8c78ddb3894a316"
CORPUS_HASH = "a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b"
F127_COUNTS = {"train": 2048, "dev": 256, "holdout": 256}
F124_REFERENCE_NRMSE = 0.04928567033125049
F127_REFERENCE_NRMSE = 0.05158006312777384
L2 = 1e-6


def _write_progress(output: Path, stage: str, payload: dict) -> None:
    path = output.parent / f"{output.stem}.stage-{stage}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _collect_states(compiled, basis) -> tuple[list[dict], dict]:
    states = []
    identities = []
    seen = set()
    lengths = (8, 24, 64, 128, 192, 256)
    trajectory = 0
    while len(identities) < sum(COUNTS.values()):
        rng = random.Random(CORPUS_SEED + trajectory * 7919)
        state = initial_state(compiled)
        for _ in range(lengths[trajectory % len(lengths)]):
            actions = _sorted_actions(state, compiled)
            if not actions:
                break
            state = apply_action(state, actions[rng.randrange(len(actions))], compiled)
            key = str(position_identity_key(state.position, compiled))
            if key in seen or state.terminal_status.status is not TerminalStatus.ONGOING:
                continue
            seen.add(key)
            ordinal = len(identities)
            identities.append(key)
            split = "train" if ordinal < COUNTS["train"] else ("dev" if ordinal < COUNTS["train"] + COUNTS["dev"] else "holdout")
            states.append({"identity": key, "ordinal": ordinal, "split": split, "trajectory": trajectory, "ply": state.ply_count, "side_to_move": state.position.side_to_move, "state": state})
            if len(identities) >= sum(COUNTS.values()):
                break
        trajectory += 1
        if trajectory > 2000:
            raise RuntimeError("F128_CORPUS_GENERATION_EXCEEDED_TRAJECTORY_BOUND")
    identity_sha = _json_sha(identities)
    if identity_sha != CORPUS_HASH:
        raise RuntimeError("F128_FROZEN_CORPUS_IDENTITY_MISMATCH")
    if basis.oracle_weight_sha256 != ORACLE_HASH:
        raise RuntimeError("F128_FROZEN_ORACLE_IDENTITY_MISMATCH")
    return states, {"full_rows": len(identities), "full_identity_sha256": identity_sha, "corpus_seed": CORPUS_SEED, "oracle_weight_sha256": basis.oracle_weight_sha256, "counts": COUNTS}


def _selected_ordinals() -> dict[str, list[int]]:
    result = {}
    offset = 0
    for split in ("train", "dev", "holdout"):
        total = COUNTS[split]
        requested = F127_COUNTS[split]
        result[split] = [offset + math.floor(index * total / requested) for index in range(requested)]
        offset += total
    return result


def _eligibility_map(rows, compiled) -> tuple[list[dict], dict, dict[str, str]]:
    counts = {
        split: {"total": 0, "excluded_terminal_child": 0, "excluded_root_declaration": 0, "excluded_child_declaration": 0, "excluded_any": 0, "retained": 0}
        for split in ("train", "dev", "holdout")
    }
    retained = []
    flags = {}
    for row in rows:
        actions = _sorted_actions(row["state"], compiled)
        children = [(action, apply_action(row["state"], action, compiled)) for action in actions]
        eligibility = eligibility_from_children(row["state"], children, compiled)
        split = row["split"]
        counts[split]["total"] += 1
        counts[split]["excluded_terminal_child"] += int(eligibility["terminal_child"])
        counts[split]["excluded_root_declaration"] += int(eligibility["root_shogi_declaration"])
        counts[split]["excluded_child_declaration"] += int(eligibility["child_shogi_declaration"])
        excluded = bool(eligibility["terminal_child"] or eligibility["root_shogi_declaration"] or eligibility["child_shogi_declaration"])
        counts[split]["excluded_any"] += int(excluded)
        counts[split]["retained"] += int(not excluded)
        flags[row["identity"]] = {**eligibility, "excluded": excluded, "root_legal_action_count": len(actions)}
        if not excluded:
            retained.append({**row, "root_legal_action_count": len(actions)})
    retained_sha = {
        split: _json_sha([row["identity"] for row in retained if row["split"] == split])
        for split in ("train", "dev", "holdout")
    }
    return retained, counts, retained_sha


def _materialize(rows, basis) -> list[dict]:
    output = []
    for row in rows:
        features = basis.vector(row["state"])
        output.append({**row, "features": features.tolist(), "oracle": float(basis.oracle(features))})
    return output


def _fit_surface(rows, basis) -> dict:
    labels = [row["oracle"] for row in rows]
    pack = _prepare_filtered(rows, labels, basis)
    design = pack["design"]["train"]
    gram = design.T @ design / len(design)
    gram[:-1, :-1] += L2 * np.eye(gram.shape[1] - 1)
    model = np.linalg.solve(gram, design.T @ pack["target"]["train"] / len(design))
    return {"pack": pack, "model": model, "train_rows": len([row for row in rows if row["split"] == "train"])}


def _predict_rows(fit: dict, rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    pack = fit["pack"]
    raw = np.asarray([row["features"] for row in rows], dtype=np.float64)
    target = np.asarray([row["oracle"] for row in rows], dtype=np.float64)
    normalized = (raw - pack["feature_mean"]) / pack["feature_scale"]
    design = np.column_stack([normalized[:, pack["active"]], np.ones(len(normalized))])
    prediction = pack["target_mean"] + pack["target_std"] * (design @ fit["model"])
    return target, prediction


def _metrics(fit: dict, rows: list[dict]) -> dict:
    target, prediction = _predict_rows(fit, rows)
    return _scalar_metrics(target, prediction, float(np.std(target)) or 1.0)


def _surface_rows(rows, split: str) -> list[dict]:
    return [row for row in rows if row["split"] == split]


def _matrix_report(models: dict[str, dict], holdouts: dict[str, list[dict]]) -> dict:
    return {
        model_name: {
            holdout_name: _metrics(fit, rows)
            for holdout_name, rows in holdouts.items()
        }
        for model_name, fit in models.items()
    }


def _design_report(fit: dict, basis: FrozenBasis) -> dict:
    design = fit["pack"]["design"]["train"]
    singular = np.linalg.svd(design, compute_uv=False)
    tolerance = np.finfo(np.float64).eps * max(design.shape) * float(singular[0])
    retained = singular > tolerance
    spectrum = singular[retained]
    return {
        "retained_train_rows": int(len(design)),
        "active_feature_count": int(fit["pack"]["active"].sum()),
        "numerical_rank": int(retained.sum()),
        "nullity": int(len(singular) - retained.sum()),
        "condition_number_on_retained_spectrum": float(spectrum[0] / spectrum[-1]) if len(spectrum) else None,
        "rank_tolerance": float(tolerance),
        "raw_feature_count": len(basis.names),
    }


def _lost_feature_report(full_fit: dict, subset_fit: dict, subset_holdout: list[dict], basis: FrozenBasis) -> dict:
    full_scale = full_fit["pack"]["feature_scale"]
    subset_scale = subset_fit["pack"]["feature_scale"]
    lost = [index for index, (full, subset) in enumerate(zip(full_scale, subset_scale)) if subset == 1.0 and full > 1e-12]
    raw = np.asarray([row["features"] for row in subset_holdout], dtype=np.float64)
    contributions = raw[:, lost] * np.asarray([basis.weights[index] for index in lost], dtype=np.float64) if lost else np.zeros((len(raw), 0))
    total = contributions.sum(axis=1) if contributions.shape[1] else np.zeros(len(raw))
    return {
        "count": len(lost),
        "features_constant_in_subset_but_variable_in_full": [basis.names[index] for index in lost],
        "oracle_rms_contribution_on_f127_holdout": float(np.sqrt(np.mean(total * total))) if len(total) else 0.0,
        "oracle_max_abs_contribution_on_f127_holdout": float(np.max(np.abs(total))) if len(total) else 0.0,
    }


def _sampling_diagnostic(full_fit: dict, full_holdout: list[dict], actual_holdout: list[dict]) -> dict:
    size = len(full_holdout)
    subset_size = len(actual_holdout)
    values = []
    index_sets = []
    for offset in range(64):
        indices = sorted({(offset + math.floor(index * size / subset_size)) % size for index in range(subset_size)})
        index_sets.append(len(indices))
        values.append(_metrics(full_fit, [full_holdout[index] for index in indices])["normalized_rmse"])
    actual = _metrics(full_fit, actual_holdout)["normalized_rmse"]
    values_array = np.asarray(values, dtype=np.float64)
    return {
        "formula": "sorted unique indices ((offset + floor(j * N / K)) mod N), offset=0..63, j=0..K-1",
        "full_eligible_holdout_size": size,
        "pseudo_subset_size": subset_size,
        "pseudo_subset_cardinalities": sorted(set(index_sets)),
        "mean": float(np.mean(values_array)),
        "standard_deviation": float(np.std(values_array)),
        "min": float(np.min(values_array)),
        "median": float(np.median(values_array)),
        "max": float(np.max(values_array)),
        "p10": float(np.percentile(values_array, 10)),
        "p90": float(np.percentile(values_array, 90)),
        "fraction_above_0.05": float(np.mean(values_array > 0.05)),
        "actual_f127_selected_holdout_nrmse": actual,
        "actual_percentile_position": float(100.0 * np.mean(values_array <= actual)),
    }


def _run(output: Path) -> dict:
    started = time.time()
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    basis = FrozenBasis(FAMILY, compiled)
    states, corpus = _collect_states(compiled, basis)
    retained_states, eligibility_counts, retained_sha = _eligibility_map(states, compiled)
    selected_ordinals = _selected_ordinals()
    selected = {ordinal for values in selected_ordinals.values() for ordinal in values}
    selected_retained_states = [row for row in retained_states if row["ordinal"] in selected]
    selected_identity_sha = {
        split: _json_sha([row["identity"] for row in states if row["ordinal"] in selected_ordinals[split]])
        for split in ("train", "dev", "holdout")
    }
    selected_retained_sha = {
        split: _json_sha([row["identity"] for row in selected_retained_states if row["split"] == split])
        for split in ("train", "dev", "holdout")
    }
    expected_selected_sha = {
        "train": "c16db7cc19375820ca9a9866493922bf7a0d74eff64a8f909b225e9936f205fc",
        "dev": "91929864cab22ba1fc065f9acdc49855751a9761ebd28b9cda76202fe01e6e63",
        "holdout": "0173ba68eed4c779322214b3ef6c819726cb5476703214d00e4d8255a7b580b3",
    }
    if selected_identity_sha != expected_selected_sha:
        raise RuntimeError("F128_F127_SELECTED_IDENTITY_REPRODUCTION_FAILURE")
    _write_progress(output, "corpus-eligibility", {"schema": "F128_STAGE_CORPUS_ELIGIBILITY_V1", "corpus": corpus, "eligibility_counts": eligibility_counts, "retained_identity_sha256": retained_sha, "selected_identity_sha256": selected_identity_sha, "selected_retained_identity_sha256": selected_retained_sha})

    materialized = _materialize(states, basis)
    retained_ids = {row["identity"] for row in retained_states}
    eligible_materialized = [row for row in materialized if row["identity"] in retained_ids]
    selected_ids = {row["identity"] for row in selected_retained_states}
    subset_materialized = [row for row in eligible_materialized if row["identity"] in selected_ids]

    model_a = _fit_surface(materialized, basis)
    model_b = _fit_surface(eligible_materialized, basis)
    model_c = _fit_surface(subset_materialized, basis)
    models = {"ORIGINAL_F122_MODEL": model_a, "FULL_ELIGIBLE_MODEL": model_b, "F127_SUBSET_MODEL": model_c}
    holdouts = {"FULL_ELIGIBLE_HOLDOUT": _surface_rows(eligible_materialized, "holdout"), "F127_SELECTED_ELIGIBLE_HOLDOUT": _surface_rows(subset_materialized, "holdout")}
    matrix = _matrix_report(models, holdouts)
    baseline_metric = _metrics(model_a, _surface_rows(materialized, "holdout"))
    subset_reproduction = _metrics(model_c, holdouts["F127_SELECTED_ELIGIBLE_HOLDOUT"])
    if abs(baseline_metric["normalized_rmse"] - F124_REFERENCE_NRMSE) > 1e-9:
        classification = "F128_F124_BASELINE_REPRODUCTION_FAILURE"
    elif abs(subset_reproduction["normalized_rmse"] - F127_REFERENCE_NRMSE) > 1e-9:
        classification = "F128_F127_CONTROL_REPRODUCTION_FAILURE"
    else:
        full_b = matrix["FULL_ELIGIBLE_MODEL"]["FULL_ELIGIBLE_HOLDOUT"]
        full_c = matrix["FULL_ELIGIBLE_MODEL"]["F127_SELECTED_ELIGIBLE_HOLDOUT"]
        subset_c = matrix["F127_SUBSET_MODEL"]["F127_SELECTED_ELIGIBLE_HOLDOUT"]
        if full_b["normalized_rmse"] > 0.05 and baseline_metric["normalized_rmse"] <= 0.05:
            classification = "F125_ELIGIBILITY_CONDITIONING_SHIFTS_DIRECT_CONTROL_GATE"
        elif full_b["normalized_rmse"] <= 0.05 and full_c["normalized_rmse"] > 0.05:
            classification = "F127_HOLDOUT_SUBSAMPLE_THRESHOLD_SENSITIVITY_SUPPORTED"
        elif full_b["normalized_rmse"] <= 0.05 and full_c["normalized_rmse"] <= 0.05 and subset_c["normalized_rmse"] > full_c["normalized_rmse"]:
            classification = "F127_TRAINING_SUBSET_SUPPORT_INSUFFICIENT"
        else:
            classification = "F127_DIRECT_CONTROL_MARGIN_NOT_YET_ATTRIBUTED"

    full_b = matrix["FULL_ELIGIBLE_MODEL"]["FULL_ELIGIBLE_HOLDOUT"]
    full_c = matrix["FULL_ELIGIBLE_MODEL"]["F127_SELECTED_ELIGIBLE_HOLDOUT"]
    subset_c = matrix["F127_SUBSET_MODEL"]["F127_SELECTED_ELIGIBLE_HOLDOUT"]
    decomposition = {
        "holdout_surface_effect_nrmse": full_c["normalized_rmse"] - full_b["normalized_rmse"],
        "holdout_surface_effect_rmse_oracle_units": full_c["rmse_oracle_units"] - full_b["rmse_oracle_units"],
        "training_subset_effect_nrmse": subset_c["normalized_rmse"] - full_c["normalized_rmse"],
        "training_subset_effect_rmse_oracle_units": subset_c["rmse_oracle_units"] - full_c["rmse_oracle_units"],
    }
    design_diagnostics = {
        "FULL_ELIGIBLE_MODEL": _design_report(model_b, basis),
        "F127_SUBSET_MODEL": _design_report(model_c, basis),
        "lost_feature_support": _lost_feature_report(model_b, model_c, holdouts["F127_SELECTED_ELIGIBLE_HOLDOUT"], basis),
    }
    subset_penalty = "F127_SUBSET_GENERALIZATION_PENALTY_MATERIAL" if abs(decomposition["training_subset_effect_nrmse"]) >= 0.01 else "F127_SUBSET_GENERALIZATION_PENALTY_SMALL"
    result = {
        "schema": "F128_SHOGI_DIRECT_CONTROL_CROSS_SURFACE_DIAGNOSIS_V1",
        "baseline": BASELINE,
        "family": FAMILY,
        "corpus": corpus,
        "eligibility": {"counts_by_split": eligibility_counts, "retained_identity_sha256": retained_sha, "selected_identity_sha256": selected_identity_sha, "selected_retained_identity_sha256": selected_retained_sha},
        "surface_sizes": {"A_full": {split: len(_surface_rows(materialized, split)) for split in ("train", "dev", "holdout")}, "B_full_eligible": {split: len(_surface_rows(eligible_materialized, split)) for split in ("train", "dev", "holdout")}, "C_f127_subset": {split: len(_surface_rows(subset_materialized, split)) for split in ("train", "dev", "holdout")}},
        "surface_a_f124_reproduction": {"metrics": baseline_metric, "expected_normalized_rmse": F124_REFERENCE_NRMSE, "absolute_difference": abs(baseline_metric["normalized_rmse"] - F124_REFERENCE_NRMSE)},
        "surface_c_f127_reproduction": {"metrics": subset_reproduction, "expected_normalized_rmse": F127_REFERENCE_NRMSE, "absolute_difference": abs(subset_reproduction["normalized_rmse"] - F127_REFERENCE_NRMSE)},
        "cross_evaluation_matrix": matrix,
        "decomposition": decomposition,
        "design_matrix_diagnostics": design_diagnostics,
        "holdout_sampling_diagnostic": _sampling_diagnostic(model_b, holdouts["FULL_ELIGIBLE_HOLDOUT"], holdouts["F127_SELECTED_ELIGIBLE_HOLDOUT"]),
        "subset_generalization_penalty": subset_penalty,
        "t1_generated": False,
        "classification": classification,
        "runtime_seconds": time.time() - started,
    }
    _write_progress(output, "cross-surface-diagnostics", result)
    return result


def run(output: Path | None = None) -> dict:
    return _run(output or Path(".generic_chess_flow/f128-shogi-result.json"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": result["classification"], "runtime_seconds": result["runtime_seconds"], "t1_generated": result["t1_generated"]}, sort_keys=True))


if __name__ == "__main__":
    main()
