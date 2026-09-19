"""F126: bounded Standard-Shogi scalar compression screen for one-ply search."""

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
    from scripts.f124_reverse_benchmark_stable_convex_solver import _normal_system, _pcg
    from scripts.f125_known_oracle_one_ply_search_compression import (
        _fit_metrics,
        _sorted_actions,
        _teacher_row,
    )
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import (
        COUNTS,
        FrozenBasis,
        _json_sha,
    )
    from f124_reverse_benchmark_stable_convex_solver import _normal_system, _pcg
    from f125_known_oracle_one_ply_search_compression import (
        _fit_metrics,
        _sorted_actions,
        _teacher_row,
    )

from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


FAMILY = "standard_shogi"
CORPUS_SEED = 1220201
ORACLE_HASH = "dda316e263a8f6e5a12678199e87cbedea7e4d40358d3087e8c78ddb3894a316"
CORPUS_HASH = "a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b"
SELECTED_COUNTS = {"train": 1024, "dev": 256, "holdout": 256}
L2 = 1e-6


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
        for ply in range(length):
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
                features = basis.vector(state)
                selected_rows.append({
                    "identity": key,
                    "ordinal": ordinal,
                    "trajectory": trajectory,
                    "ply": state.ply_count,
                    "side_to_move": state.position.side_to_move,
                    "features": features.tolist(),
                    "direct_oracle": basis.oracle(features),
                    "state": state,
                })
            if len(identities) >= sum(COUNTS.values()):
                break
        trajectory += 1
        if trajectory > 2000:
            raise RuntimeError("F126_CORPUS_GENERATION_EXCEEDED_TRAJECTORY_BOUND")

    if len(identities) != sum(COUNTS.values()):
        raise RuntimeError("F126_FULL_CORPUS_LENGTH_MISMATCH")
    identity_sha = _json_sha(identities)
    if identity_sha != CORPUS_HASH:
        raise RuntimeError("F126_FROZEN_CORPUS_IDENTITY_MISMATCH")
    if basis.oracle_weight_sha256 != ORACLE_HASH:
        raise RuntimeError("F126_FROZEN_ORACLE_IDENTITY_MISMATCH")

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


def _fit_report(fit: dict, target_label: str) -> dict:
    numerical = {
        "finite_pcg_parameters": bool(np.all(np.isfinite(fit["pcg"]))),
        "relative_linear_system_residual": fit["solver"]["relative_linear_system_residual"],
        "objective_excess_vs_matched_ridge": fit["objective_excess"],
        "prediction_difference_vs_matched": fit["prediction_difference_vs_matched"],
    }
    scalar = {}
    for model_name, metrics in fit["scalar_metrics"].items():
        scalar[model_name] = {}
        for split, row in metrics.items():
            if split not in ("train", "dev", "holdout"):
                continue
            scalar[model_name][split] = {
                **row,
                f"rmse_{target_label}_units": row["rmse_oracle_units"],
            }
    return {
        "target": target_label,
        "solver": fit["solver"],
        "numerical": numerical,
        "scalar_metrics": scalar,
        "objective_excess": fit["objective_excess"],
        "prediction_difference_vs_matched": fit["prediction_difference_vs_matched"],
    }


def _direct_gate(fit: dict) -> dict:
    holdout = fit["scalar_metrics"]["PCG"]["holdout"]
    numerical = fit["solver"]["relative_linear_system_residual"] <= 1e-10
    objective = fit["objective_excess"] <= 1e-10
    prediction = fit["prediction_difference_vs_matched"]["holdout"]["normalized_by_holdout_target_std"] <= 1e-8
    scalar = {
        "holdout_normalized_rmse": holdout["normalized_rmse"] <= 0.05,
        "holdout_r2": holdout["r2"] >= 0.99,
        "holdout_pearson": holdout["pearson"] >= 0.995,
    }
    return {
        "relative_residual": numerical,
        "objective_excess": objective,
        "prediction_difference": prediction,
        **scalar,
        "pass": bool(numerical and objective and prediction and all(scalar.values())),
    }


def _representation_gate(fit: dict) -> dict:
    holdout = fit["scalar_metrics"]["matched_ridge"]["holdout"]
    result = {
        "holdout_normalized_rmse": holdout["normalized_rmse"] <= 0.15,
        "holdout_r2": holdout["r2"] >= 0.95,
        "holdout_pearson": holdout["pearson"] >= 0.975,
    }
    result["pass"] = all(result.values())
    return result


def _exclusion_report(rows, basis) -> tuple[list[dict], list[dict], dict]:
    labels = []
    retained = []
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
        label = _teacher_row(row, basis)
        split = row["split"]
        counts[split]["selected"] += 1
        if label["terminal_child"]:
            counts[split]["excluded_terminal_child"] += 1
        if label["root_shogi_declaration"]:
            counts[split]["excluded_root_declaration"] += 1
        if label["child_shogi_declaration"]:
            counts[split]["excluded_immediate_child_declaration"] += 1
        excluded = bool(label["terminal_child"] or label["shogi_declaration"])
        if excluded:
            counts[split]["excluded_any"] += 1
        else:
            counts[split]["retained"] += 1
            retained.append(row)
        labels.append({
            "identity": row["identity"],
            "ordinal": row["ordinal"],
            "split": split,
            "t1": label["t1"],
            "terminal_child": label["terminal_child"],
            "root_shogi_declaration": label["root_shogi_declaration"],
            "child_shogi_declaration": label["child_shogi_declaration"],
            "shogi_declaration": label["shogi_declaration"],
        })
    return retained, labels, counts


def _scalar_displacement(retained_rows, labels) -> dict:
    by_identity = {row["identity"]: row for row in labels}
    holdout = [row for row in retained_rows if row["split"] == "holdout"]
    t1 = np.asarray([by_identity[row["identity"]]["t1"] for row in holdout], dtype=np.float64)
    direct = np.asarray([row["direct_oracle"] for row in holdout], dtype=np.float64)
    delta = t1 - direct
    correlation = float(np.corrcoef(t1, direct)[0, 1]) if np.std(t1) and np.std(direct) else 0.0
    return {
        "count": int(len(delta)),
        "mean": float(np.mean(delta)),
        "median": float(np.median(delta)),
        "standard_deviation": float(np.std(delta)),
        "mean_absolute_value": float(np.mean(np.abs(delta))),
        "p90_absolute_value": float(np.percentile(np.abs(delta), 90)),
        "p95_absolute_value": float(np.percentile(np.abs(delta), 95)),
        "fraction_exactly_zero_within_1e-12": float(np.mean(np.abs(delta) <= 1e-12)),
        "correlation_t1_with_v_star": correlation,
    }


def _run(output: Path) -> dict:
    started = time.time()
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    basis = FrozenBasis(FAMILY, compiled)
    rows, selection = _collect_selected_corpus(compiled, basis)
    _write_progress(output, "corpus", {"schema": "F126_STAGE_CORPUS_V1", "selection": selection})

    retained, labels, exclusions = _exclusion_report(rows, basis)
    direct_labels = [row["direct_oracle"] for row in retained]
    direct_fit = _fit_metrics(retained, direct_labels, basis)
    direct_report = {
        "schema": "F126_STAGE_DIRECT_CONTROL_V1",
        "selection": selection,
        "exclusions_by_split": exclusions,
        "retained_rows": len(retained),
        "fit": _fit_report(direct_fit, "oracle"),
        "gate": _direct_gate(direct_fit),
    }
    _write_progress(output, "direct-control", direct_report)

    result = {
        "schema": "F126_SHOGI_T1_SCALAR_COMPRESSION_SCREEN_V1",
        "baseline": "33b78ffde70f2841a034e80e496f13d7806a4a12",
        "family": FAMILY,
        "selection": selection,
        "exclusions_by_split": exclusions,
        "retained_rows": len(retained),
        "direct_control": {**direct_report["fit"], "gate": direct_report["gate"]},
        "runtime_seconds": None,
    }
    if not direct_report["gate"]["pass"]:
        result["classification"] = "F126_SHOGI_SUBSET_DIRECT_CONTROL_INSUFFICIENT"
        result["runtime_seconds"] = time.time() - started
        return result

    t1_by_identity = {row["identity"]: row for row in labels}
    t1_labels = [t1_by_identity[row["identity"]]["t1"] for row in retained]
    _write_progress(output, "t1-labels", {
        "schema": "F126_STAGE_T1_LABELS_V1",
        "selection": selection,
        "exclusions_by_split": exclusions,
        "retained_rows": len(retained),
        "label_count": len(t1_labels),
        "t1_min": float(np.min(t1_labels)),
        "t1_max": float(np.max(t1_labels)),
    })
    search_fit = _fit_metrics(retained, t1_labels, basis)
    representation_gate = _representation_gate(search_fit)
    search_numerical_gate = _direct_gate(search_fit)
    search_report = {
        "schema": "F126_STAGE_SEARCH_TARGET_FIT_V1",
        "selection": selection,
        "exclusions_by_split": exclusions,
        "retained_rows": len(retained),
        "fit": _fit_report(search_fit, "teacher"),
        "numerical_gate": search_numerical_gate,
        "representation_gate": representation_gate,
        "scalar_displacement_holdout": _scalar_displacement(retained, labels),
    }
    _write_progress(output, "search-fit", search_report)
    result["search_compressed_v1"] = search_report["fit"]
    result["search_compressed_v1"]["numerical_gate"] = search_numerical_gate
    result["search_compressed_v1"]["representation_gate"] = representation_gate
    result["search_information_diagnostic"] = {"holdout_scalar_displacement": search_report["scalar_displacement_holdout"]}
    if not representation_gate["pass"]:
        result["classification"] = "SHOGI_HANDCRAFTED_T1_SEARCH_TARGET_COMPRESSION_LIMIT_SUPPORTED"
    elif not search_numerical_gate["pass"]:
        result["classification"] = "F126_SHOGI_T1_SOLVER_NUMERICAL_FAILURE"
    else:
        result["classification"] = "SHOGI_KNOWN_ORACLE_T1_SCALAR_COMPRESSION_PASSES"
    result["runtime_seconds"] = time.time() - started
    return result


def run(output: Path | None = None) -> dict:
    if output is None:
        output = Path(".generic_chess_flow/f126-shogi-result.json")
    return _run(output)


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
