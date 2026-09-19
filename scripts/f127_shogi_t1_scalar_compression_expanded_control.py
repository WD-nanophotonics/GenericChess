"""F127: expanded Standard-Shogi direct control and staged T1 compression."""

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
    )
    from scripts.f123_reverse_benchmark_identifiability_optimizer_diagnosis import (
        _predict,
        _scalar_summary,
    )
    from scripts.f124_reverse_benchmark_stable_convex_solver import _normal_system
    from scripts.f125_known_oracle_one_ply_search_compression import _prepare_filtered, _sorted_actions
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import COUNTS, FrozenBasis, _json_sha
    from f123_reverse_benchmark_identifiability_optimizer_diagnosis import _predict, _scalar_summary
    from f124_reverse_benchmark_stable_convex_solver import _normal_system
    from f125_known_oracle_one_ply_search_compression import _prepare_filtered, _sorted_actions

from generic_chess.core.declarations import available_declarations
from generic_chess.core.identity import position_identity_key
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.core.movegen import legal_actions
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


FAMILY = "standard_shogi"
BASELINE = "3ddc285af219ed2a3bb7c3bb3f4309be0c21d86b"
CORPUS_SEED = 1220201
ORACLE_HASH = "dda316e263a8f6e5a12678199e87cbedea7e4d40358d3087e8c78ddb3894a316"
CORPUS_HASH = "a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b"
SELECTED_COUNTS = {"train": 2048, "dev": 256, "holdout": 256}
L2 = 1e-6
PCG_TOLERANCE = 1e-12
PCG_MAX_ITERATION_MULTIPLIER = 8


def _selected_ordinals() -> dict[str, list[int]]:
    result = {}
    offset = 0
    for split in ("train", "dev", "holdout"):
        original_count = COUNTS[split]
        requested = SELECTED_COUNTS[split]
        result[split] = [offset + math.floor(index * original_count / requested) for index in range(requested)]
        offset += original_count
    return result


def _write_progress(output: Path, stage: str, payload: dict) -> str:
    path = output.parent / f"{output.stem}.stage-{stage}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(path)


def _collect_selected_corpus(compiled, basis) -> tuple[list[dict], dict]:
    ordinals = _selected_ordinals()
    selected = {ordinal for values in ordinals.values() for ordinal in values}
    selected_rows = []
    identities = []
    seen = set()
    trajectory_lengths = (8, 24, 64, 128, 192, 256)
    trajectory = 0
    while len(identities) < sum(COUNTS.values()):
        rng = random.Random(CORPUS_SEED + trajectory * 7919)
        state = initial_state(compiled)
        length = trajectory_lengths[trajectory % len(trajectory_lengths)]
        for _ in range(length):
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
            if ordinal in selected:
                # Eligibility is intentionally staged before any basis.vector or
                # basis.oracle call. The state is all the next stage needs.
                selected_rows.append({
                    "identity": key,
                    "ordinal": ordinal,
                    "trajectory": trajectory,
                    "ply": state.ply_count,
                    "side_to_move": state.position.side_to_move,
                    "state": state,
                })
            if len(identities) >= sum(COUNTS.values()):
                break
        trajectory += 1
        if trajectory > 2000:
            raise RuntimeError("F127_CORPUS_GENERATION_EXCEEDED_TRAJECTORY_BOUND")

    if len(identities) != sum(COUNTS.values()):
        raise RuntimeError("F127_FULL_CORPUS_LENGTH_MISMATCH")
    identity_sha = _json_sha(identities)
    if identity_sha != CORPUS_HASH:
        raise RuntimeError("F127_FROZEN_CORPUS_IDENTITY_MISMATCH")
    if basis.oracle_weight_sha256 != ORACLE_HASH:
        raise RuntimeError("F127_FROZEN_ORACLE_IDENTITY_MISMATCH")

    split_by_ordinal = {
        ordinal: split
        for split, values in ordinals.items()
        for ordinal in values
    }
    selected_rows.sort(key=lambda row: row["ordinal"])
    for row in selected_rows:
        row["split"] = split_by_ordinal[row["ordinal"]]
    selected_identity_sha = {
        split: _json_sha([row["identity"] for row in selected_rows if row["split"] == split])
        for split in ("train", "dev", "holdout")
    }
    selection = {
        "method": "floor(j * original_split_count / selected_split_count)",
        "original_counts": COUNTS,
        "selected_counts": SELECTED_COUNTS,
        "selected_original_ordinals": ordinals,
        "selected_identity_sha256": selected_identity_sha,
        "full_corpus_rows": len(identities),
        "full_corpus_identity_sha256": identity_sha,
        "corpus_seed": CORPUS_SEED,
        "oracle_weight_sha256": basis.oracle_weight_sha256,
    }
    return selected_rows, selection


def _declaration_present(state, compiled) -> bool:
    return bool(available_declarations(state, compiled))


def eligibility_from_children(state, children, compiled=None) -> dict:
    """Return only cheap eligibility flags for already-created child states."""
    if compiled is None:
        raise TypeError("F127_ELIGIBILITY_REQUIRES_COMPILED_RULESET")
    return {
        "terminal_child": any(child.terminal_status.status is not TerminalStatus.ONGOING for _, child in children),
        "root_shogi_declaration": _declaration_present(state, compiled),
        "child_shogi_declaration": any(_declaration_present(child, compiled) for _, child in children),
    }


def _eligibility_report(rows, compiled) -> tuple[list[dict], list[dict], dict]:
    retained = []
    flags = []
    counts = {
        split: {
            "selected": 0,
            "excluded_terminal_child": 0,
            "excluded_root_declaration": 0,
            "excluded_immediate_child_declaration": 0,
            "excluded_any": 0,
            "retained": 0,
        }
        for split in ("train", "dev", "holdout")
    }
    for row in rows:
        actions = _sorted_actions(row["state"], compiled)
        children = [(action, apply_action(row["state"], action, compiled)) for action in actions]
        eligibility = eligibility_from_children(row["state"], children, compiled)
        split = row["split"]
        counts[split]["selected"] += 1
        if eligibility["terminal_child"]:
            counts[split]["excluded_terminal_child"] += 1
        if eligibility["root_shogi_declaration"]:
            counts[split]["excluded_root_declaration"] += 1
        if eligibility["child_shogi_declaration"]:
            counts[split]["excluded_immediate_child_declaration"] += 1
        excluded = bool(eligibility["terminal_child"] or eligibility["root_shogi_declaration"] or eligibility["child_shogi_declaration"])
        if excluded:
            counts[split]["excluded_any"] += 1
        else:
            counts[split]["retained"] += 1
            retained.append({**row, "root_legal_action_count": len(actions)})
        flags.append({"identity": row["identity"], "ordinal": row["ordinal"], "split": split, **eligibility, "excluded": excluded})
    return retained, flags, counts


def _materialize_direct_rows(rows, basis) -> list[dict]:
    output = []
    for row in rows:
        features = basis.vector(row["state"])
        output.append({**row, "features": features.tolist(), "direct_oracle": float(basis.oracle(features))})
    return output


def _pcg_tight(pack: dict) -> tuple[np.ndarray, dict]:
    hessian, rhs = _normal_system(pack)
    diagonal = np.diag(hessian)
    if not np.all(np.isfinite(diagonal)) or not np.all(diagonal > 0.0):
        raise ValueError("F127_PCG_JACOBI_DIAGONAL_NOT_FINITE_POSITIVE")
    inverse_diagonal = 1.0 / diagonal
    parameter_count = len(rhs)
    theta = np.zeros(parameter_count, dtype=np.float64)
    residual = rhs.copy()
    rhs_norm = float(np.linalg.norm(rhs))
    denominator = max(rhs_norm, 1e-30)
    relative_residual = float(np.linalg.norm(residual) / denominator)
    iterations = 0
    preconditioned = inverse_diagonal * residual
    direction = preconditioned.copy()
    rz = float(residual @ preconditioned)
    maximum_iterations = PCG_MAX_ITERATION_MULTIPLIER * parameter_count
    for iteration in range(1, maximum_iterations + 1):
        if relative_residual <= PCG_TOLERANCE:
            break
        curvature = float(direction @ (hessian @ direction))
        if not np.isfinite(curvature) or curvature <= 0.0:
            raise ValueError("F127_PCG_NON_POSITIVE_CURVATURE")
        step = rz / curvature
        theta += step * direction
        residual -= step * (hessian @ direction)
        iterations = iteration
        relative_residual = float(np.linalg.norm(residual) / denominator)
        if relative_residual <= PCG_TOLERANCE:
            break
        next_preconditioned = inverse_diagonal * residual
        next_rz = float(residual @ next_preconditioned)
        direction = next_preconditioned + (next_rz / rz) * direction
        preconditioned = next_preconditioned
        rz = next_rz
    return theta, {
        "iterations": iterations,
        "maximum_iterations": maximum_iterations,
        "relative_residual": relative_residual,
        "tolerance": PCG_TOLERANCE,
        "diagonal_min": float(np.min(diagonal)),
        "diagonal_max": float(np.max(diagonal)),
    }


def _fit_metrics_tight(rows, labels, basis) -> dict:
    pack = _prepare_filtered(rows, labels, basis)
    model, solver = _pcg_tight(pack)
    hessian, rhs = _normal_system(pack)
    residual = rhs - hessian @ model
    design = pack["design"]["train"]
    gram = design.T @ design / len(design)
    gram[:-1, :-1] += L2 * np.eye(gram.shape[1] - 1)
    matched = np.linalg.solve(gram, design.T @ pack["target"]["train"] / len(design))
    objective = lambda candidate: float(0.5 * np.mean((design @ candidate - pack["target"]["train"]) ** 2) + 0.5 * L2 * np.sum(candidate[:-1] ** 2))
    model_vs_matched = {
        split: float(np.sqrt(np.mean((_predict(model, pack, split) - _predict(matched, pack, split)) ** 2)))
        for split in ("train", "dev", "holdout")
    }
    holdout_std = float(np.std(pack["oracle"]["holdout"])) or 1.0
    prediction_difference = {
        split: {"rmse_oracle_units": value, "normalized_by_holdout_target_std": value / holdout_std}
        for split, value in model_vs_matched.items()
    }
    return {
        "pack": pack,
        "pcg": model,
        "matched": matched,
        "solver": {**solver, "relative_linear_system_residual": float(np.linalg.norm(residual) / max(np.linalg.norm(rhs), 1e-30))},
        "scalar_metrics": {"PCG": _scalar_summary(model, pack), "matched_ridge": _scalar_summary(matched, pack)},
        "objective_excess": objective(model) - objective(matched),
        "prediction_difference_vs_matched": prediction_difference,
    }


def _fit_report(fit: dict, target_label: str) -> dict:
    scalar = {}
    for model_name, metrics in fit["scalar_metrics"].items():
        scalar[model_name] = {
            split: {**row, f"rmse_{target_label}_units": row["rmse_oracle_units"]}
            for split, row in metrics.items()
            if split in ("train", "dev", "holdout")
        }
    return {
        "target": target_label,
        "solver": fit["solver"],
        "numerical": {
            "finite_pcg_parameters": bool(np.all(np.isfinite(fit["pcg"]))),
            "relative_linear_system_residual": fit["solver"]["relative_linear_system_residual"],
            "objective_excess_vs_matched_ridge": fit["objective_excess"],
            "prediction_difference_vs_matched": fit["prediction_difference_vs_matched"],
        },
        "scalar_metrics": scalar,
        "objective_excess": fit["objective_excess"],
        "prediction_difference_vs_matched": fit["prediction_difference_vs_matched"],
    }


def _numerical_gate(fit: dict) -> dict:
    return {
        "finite_parameters": bool(np.all(np.isfinite(fit["pcg"]))),
        "relative_residual": fit["solver"]["relative_linear_system_residual"] <= 1e-10,
        "objective_excess": fit["objective_excess"] <= 1e-10,
        "prediction_difference": fit["prediction_difference_vs_matched"]["holdout"]["normalized_by_holdout_target_std"] <= 1e-8,
    }


def _scalar_gate(metrics: dict) -> dict:
    holdout = metrics["holdout"]
    result = {
        "holdout_normalized_rmse": holdout["normalized_rmse"] <= 0.05,
        "holdout_r2": holdout["r2"] >= 0.99,
        "holdout_pearson": holdout["pearson"] >= 0.995,
    }
    result["pass"] = all(result.values())
    return result


def _direct_gate(fit: dict) -> dict:
    numerical = _numerical_gate(fit)
    pcg_scalar = _scalar_gate(fit["scalar_metrics"]["PCG"])
    matched_scalar = _scalar_gate(fit["scalar_metrics"]["matched_ridge"])
    return {"numerical": {**numerical, "pass": all(numerical.values())}, "pcg_scalar": pcg_scalar, "matched_ridge_scalar": matched_scalar, "pass": bool(all(numerical.values()) and pcg_scalar["pass"])}


def _t1_labels(rows, basis, compiled) -> tuple[list[float], dict]:
    labels = []
    action_counts = []
    child_count = 0
    for row in rows:
        actions = _sorted_actions(row["state"], compiled)
        children = [(action, apply_action(row["state"], action, compiled)) for action in actions]
        eligibility = eligibility_from_children(row["state"], children, compiled)
        if any(eligibility.values()):
            raise RuntimeError("F127_RETAINED_IDENTITY_LOST_ELIGIBILITY")
        child_values = [float(basis.oracle(basis.vector(child))) for _, child in children]
        scores = [-value for value in child_values]
        if not scores:
            raise RuntimeError("F127_RETAINED_STATE_HAS_NO_LEGAL_ACTION")
        best = max(range(len(scores)), key=lambda index: (scores[index], -index))
        labels.append(float(scores[best]))
        action_counts.append(len(actions))
        child_count += len(children)
    values = np.asarray(labels, dtype=np.float64)
    actions = np.asarray(action_counts, dtype=np.float64)
    return labels, {
        "retained_identities": [row["identity"] for row in rows],
        "label_count": len(labels),
        "t1_min": float(np.min(values)),
        "t1_max": float(np.max(values)),
        "t1_mean": float(np.mean(values)),
        "t1_standard_deviation": float(np.std(values)),
        "action_count_mean": float(np.mean(actions)),
        "action_count_median": float(np.median(actions)),
        "action_count_p95": float(np.percentile(actions, 95)),
        "action_count_max": int(np.max(actions)),
        "total_child_states_evaluated": child_count,
    }


def _correlation(left, right) -> float:
    if len(left) < 2 or not np.std(left) or not np.std(right):
        return 0.0
    return float(np.corrcoef(left, right)[0, 1])


def _spearman(left, right) -> float:
    left_order = np.argsort(left, kind="mergesort")
    right_order = np.argsort(right, kind="mergesort")
    left_rank = np.empty(len(left), dtype=np.float64)
    right_rank = np.empty(len(right), dtype=np.float64)
    left_rank[left_order] = np.arange(len(left), dtype=np.float64)
    right_rank[right_order] = np.arange(len(right), dtype=np.float64)
    return _correlation(left_rank, right_rank)


def _scalar_displacement(rows, labels) -> dict:
    holdout_rows = [row for row in rows if row["split"] == "holdout"]
    labels_by_identity = {row["identity"]: label for row, label in zip(rows, labels)}
    holdout_labels = np.asarray([labels_by_identity[row["identity"]] for row in holdout_rows], dtype=np.float64)
    direct = np.asarray([row["direct_oracle"] for row in holdout_rows], dtype=np.float64)
    delta = holdout_labels - direct
    order = np.argsort([row["root_legal_action_count"] for row in holdout_rows], kind="mergesort")
    quartiles = []
    for index, group in enumerate(np.array_split(order, 4), start=1):
        if len(group):
            counts = [holdout_rows[item]["root_legal_action_count"] for item in group]
            quartiles.append({"quartile": index, "min_action_count": int(min(counts)), "max_action_count": int(max(counts)), "count": len(group), "mean_absolute_delta": float(np.mean(np.abs(delta[group])))})
    return {
        "count": int(len(delta)),
        "mean": float(np.mean(delta)),
        "median": float(np.median(delta)),
        "standard_deviation": float(np.std(delta)),
        "mean_absolute_value": float(np.mean(np.abs(delta))),
        "p90_absolute_value": float(np.percentile(np.abs(delta), 90)),
        "p95_absolute_value": float(np.percentile(np.abs(delta), 95)),
        "maximum_absolute_value": float(np.max(np.abs(delta))),
        "fraction_exactly_zero_within_1e-12": float(np.mean(np.abs(delta) <= 1e-12)),
        "pearson_t1_with_v_star": _correlation(holdout_labels, direct),
        "spearman_t1_with_v_star": _spearman(holdout_labels, direct),
        "by_root_legal_action_count_quartile": quartiles,
    }


def _run(output: Path) -> dict:
    started = time.time()
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    basis = FrozenBasis(FAMILY, compiled)
    rows, selection = _collect_selected_corpus(compiled, basis)
    _write_progress(output, "corpus", {"schema": "F127_STAGE_CORPUS_V1", "selection": selection})

    retained, eligibility_flags, exclusions = _eligibility_report(rows, compiled)
    direct_rows = _materialize_direct_rows(retained, basis)
    direct_labels = [row["direct_oracle"] for row in direct_rows]
    direct_fit = _fit_metrics_tight(direct_rows, direct_labels, basis)
    direct_report = {
        "schema": "F127_STAGE_ELIGIBILITY_DIRECT_CONTROL_V1",
        "selection": selection,
        "eligibility_flags": eligibility_flags,
        "exclusions_by_split": exclusions,
        "retained_rows": len(retained),
        "fit": _fit_report(direct_fit, "oracle"),
        "gate": _direct_gate(direct_fit),
    }
    _write_progress(output, "eligibility-direct-control", direct_report)

    result = {
        "schema": "F127_SHOGI_T1_SCALAR_COMPRESSION_EXPANDED_CONTROL_V1",
        "baseline": BASELINE,
        "family": FAMILY,
        "selection": selection,
        "exclusions_by_split": exclusions,
        "retained_rows": len(retained),
        "direct_control": {**direct_report["fit"], "gate": direct_report["gate"]},
        "runtime_seconds": None,
    }
    matched_pass = direct_report["gate"]["matched_ridge_scalar"]["pass"]
    numerical_pass = direct_report["gate"]["numerical"]["pass"]
    if not matched_pass:
        result["classification"] = "F127_EXPANDED_SUBSET_DIRECT_CONTROL_INSUFFICIENT"
        result["runtime_seconds"] = time.time() - started
        return result
    if not numerical_pass:
        result["classification"] = "F127_DIRECT_CONTROL_NUMERICAL_FAILURE"
        result["runtime_seconds"] = time.time() - started
        return result
    if not direct_report["gate"]["pcg_scalar"]["pass"]:
        result["classification"] = "F127_EXPANDED_SUBSET_DIRECT_CONTROL_INSUFFICIENT"
        result["runtime_seconds"] = time.time() - started
        return result

    t1_labels, label_report = _t1_labels(retained, basis, compiled)
    label_stage = {"schema": "F127_STAGE_T1_LABELS_V1", "selection": selection, "exclusions_by_split": exclusions, **label_report}
    _write_progress(output, "t1-labels", label_stage)
    search_fit = _fit_metrics_tight(direct_rows, t1_labels, basis)
    representation = _scalar_gate(search_fit["scalar_metrics"]["matched_ridge"])
    search_numerical = _numerical_gate(search_fit)
    search_report = {
        "schema": "F127_STAGE_SEARCH_TARGET_FIT_V1",
        "selection": selection,
        "exclusions_by_split": exclusions,
        "retained_rows": len(retained),
        "fit": _fit_report(search_fit, "teacher"),
        "numerical_gate": {**search_numerical, "pass": all(search_numerical.values())},
        "representation_gate": representation,
        "scalar_displacement_holdout": _scalar_displacement(direct_rows, t1_labels),
    }
    _write_progress(output, "search-fit", search_report)
    result["search_compressed_v1"] = search_report["fit"]
    result["search_compressed_v1"]["numerical_gate"] = search_report["numerical_gate"]
    result["search_compressed_v1"]["representation_gate"] = representation
    result["search_information_diagnostic"] = {"holdout_scalar_displacement": search_report["scalar_displacement_holdout"]}
    if not representation["pass"]:
        result["classification"] = "SHOGI_HANDCRAFTED_T1_SEARCH_TARGET_COMPRESSION_LIMIT_SUPPORTED"
    elif not search_report["numerical_gate"]["pass"]:
        result["classification"] = "F127_SHOGI_T1_SOLVER_NUMERICAL_FAILURE"
    else:
        result["classification"] = "SHOGI_KNOWN_ORACLE_T1_SCALAR_COMPRESSION_PASSES"
    result["runtime_seconds"] = time.time() - started
    return result


def run(output: Path | None = None) -> dict:
    return _run(output or Path(".generic_chess_flow/f127-shogi-result.json"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": result["classification"], "retained_rows": result["retained_rows"], "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
