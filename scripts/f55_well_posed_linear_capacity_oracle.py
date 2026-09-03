"""F55 well-posed direct linear-capacity oracle.

This diagnostic keeps the current-v2 evaluator, five-feature representation,
Native semantic search, and corpus generation policy frozen.  It separates
mate-band search targets from ordinary static targets, scales features using
training-only RMS values, removes zero-variance coordinates, and selects a
small ridge alpha grid by deterministic training-only cross-validation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from f50_generic_learnable_evaluator import WEIGHTS, _native_delta, _ruleset  # noqa: E402
from f54_direct_capacity_and_gradient_geometry_diagnosis import (  # noqa: E402
    _agreement,
    _checkpoint_with_delta,
    _feature_names,
    _metrics,
    _parent,
    _parallel_search,
    _record_dict,
    _static_row,
)
from generic_chess.core.actions import action_from_dict  # noqa: E402
from generic_chess.learning.diagnostics import generate_diagnostic_corpus  # noqa: E402
from generic_chess.learning.features import DYNAMIC_FEATURE_NAMES  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.rules.compiler import compile_semantic_ruleset  # noqa: E402


OUT = ROOT / ".generic_chess_flow" / "f55-well-posed-linear-capacity-oracle"
CORPUS_COUNT = 96
TRAIN_COUNT = 64
VALIDATION_COUNT = 32
OPENING_COUNT = 24
CORPUS_MIN_PLIES = 8
CORPUS_MAX_PLIES = 40
CORPUS_SEEDS = {
    "A_CANONICAL_WESTERN_CHESS": 550101,
    "B_CANONICAL_STANDARD_SHOGI": 550201,
}
TEACHER_BUDGETS = (40000, 80000)
TEACHER_STABILITY_THRESHOLD = 0.85
MATE_BAND_NATIVE_THRESHOLD = 90_000_000
CV_FOLDS = 4
ALPHA_GRID = (1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1.0)
ZERO_VARIANCE_TOLERANCE = 1e-12
VALUE_IMPROVEMENT_THRESHOLD = 0.10


def _generate_corpus(label: str, compiled) -> tuple[dict, dict]:
    seed = CORPUS_SEEDS[label]
    openings = generate_arena_openings(
        compiled, count=OPENING_COUNT, seed=seed, min_plies=2, max_plies=6
    )
    corpus = generate_diagnostic_corpus(
        compiled, openings, count=CORPUS_COUNT, seed=seed + 1,
        min_plies=CORPUS_MIN_PLIES, max_plies=CORPUS_MAX_PLIES,
    )
    payload = corpus.to_dict()
    return payload, {
        "corpus_id": corpus.corpus_id,
        "source_opening_corpus_id": openings.corpus_id,
        "records": [_record_dict(position) for position in corpus.positions],
    }


def _ridge_svd(features: np.ndarray, residual: np.ndarray, alpha: float) -> np.ndarray:
    """Solve ridge in normalized coordinates without forming a Gram matrix."""
    if features.ndim != 2 or residual.ndim != 1 or len(features) != len(residual):
        raise ValueError("ridge inputs have incompatible shapes")
    if not features.shape[1]:
        return np.zeros(0, dtype=float)
    u, singular, vt = np.linalg.svd(features, full_matrices=False)
    factors = singular / (singular * singular + alpha)
    return vt.T @ (factors * (u.T @ residual))


def _conditioning(matrix: np.ndarray) -> dict:
    if matrix.ndim != 2 or not matrix.shape[1]:
        return {
            "rows": int(matrix.shape[0]) if matrix.ndim == 2 else 0,
            "columns": 0,
            "rank": 0,
            "singular_value_max": None,
            "singular_value_min_nonzero": None,
            "condition_number": None,
        }
    singular = np.linalg.svd(matrix, compute_uv=False)
    maximum = float(singular[0]) if len(singular) else 0.0
    tolerance = maximum * max(matrix.shape) * np.finfo(float).eps
    nonzero = singular[singular > tolerance]
    rank = int(len(nonzero))
    minimum = float(nonzero[-1]) if len(nonzero) else None
    condition = float(maximum / minimum) if minimum and rank == min(matrix.shape) else None
    return {
        "rows": int(matrix.shape[0]),
        "columns": int(matrix.shape[1]),
        "rank": rank,
        "singular_value_max": maximum if len(singular) else None,
        "singular_value_min_nonzero": minimum,
        "condition_number": condition,
    }


def _training_scale(features: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if features.ndim != 2:
        raise ValueError("features must be a matrix")
    std = np.std(features, axis=0, ddof=0)
    active = std > ZERO_VARIANCE_TOLERANCE
    if not np.any(active):
        raise ValueError("training features have no non-constant coordinates")
    rms = np.sqrt(np.mean(features[:, active] * features[:, active], axis=0))
    scale = np.where(rms > ZERO_VARIANCE_TOLERANCE, rms, 1.0)
    return active, scale, std


def _cv_select_alpha(features: np.ndarray, residual: np.ndarray) -> tuple[float, list[dict]]:
    if len(features) < CV_FOLDS:
        raise ValueError("training set is too small for deterministic CV")
    fold_ids = np.arange(len(features)) % CV_FOLDS
    rows = []
    for alpha in ALPHA_GRID:
        fold_scores = []
        for fold in range(CV_FOLDS):
            train = fold_ids != fold
            validation = fold_ids == fold
            theta = _ridge_svd(features[train], residual[train], alpha)
            error = features[validation] @ theta - residual[validation]
            fold_scores.append(float(np.mean(error * error)))
        rows.append({
            "alpha": alpha,
            "fold_mse": fold_scores,
            "mean_mse": float(np.mean(fold_scores)),
        })
    selected = min(enumerate(rows), key=lambda item: (item[1]["mean_mse"], item[0]))
    return float(selected[1]["alpha"]), rows


def _bounded_metrics(prediction: np.ndarray, target: np.ndarray, bound: float) -> dict:
    scale = max(float(bound), 1.0)
    return _metrics(np.tanh(prediction / scale), np.tanh(target / scale))


def _is_mate_band(row: dict) -> bool:
    return abs(int(row["native_score"])) > MATE_BAND_NATIVE_THRESHOLD


def _policy_metrics(parent_rows: list[dict], child_rows: list[dict], teacher_rows: list[dict], indices: list[int]) -> dict:
    if not indices:
        return {
            "positions": 0,
            "move_flip_rate_vs_parent": None,
            "parent_teacher_best_move_agreement": None,
            "child_teacher_best_move_agreement": None,
        }
    parent_actions = [parent_rows[index]["action_key"] for index in indices]
    child_actions = [child_rows[index]["action_key"] for index in indices]
    teacher_actions = [teacher_rows[index]["action_key"] for index in indices]
    count = len(indices)
    return {
        "positions": count,
        "move_flip_rate_vs_parent": sum(a != b for a, b in zip(child_actions, parent_actions)) / count,
        "parent_teacher_best_move_agreement": sum(a == b for a, b in zip(parent_actions, teacher_actions)) / count,
        "child_teacher_best_move_agreement": sum(a == b for a, b in zip(child_actions, teacher_actions)) / count,
    }


def _run_label(label: str, validation_nodes: int) -> dict:
    compiled, native, _profile = _ruleset(label)
    parent = _parent(label)
    corpus_payload, corpus_info = _generate_corpus(label, compiled)
    records = corpus_info["records"]
    train_records = records[:TRAIN_COUNT]
    validation_records = records[TRAIN_COUNT:]
    static_rows = [_static_row(compiled, native, parent, record) for record in records]
    x_train = np.vstack([row["vector"] for row in static_rows[:TRAIN_COUNT]])
    x_validation = np.vstack([row["vector"] for row in static_rows[TRAIN_COUNT:]])
    current_train = np.asarray([row["static_value"] for row in static_rows[:TRAIN_COUNT]], dtype=float)
    current_validation = np.asarray([row["static_value"] for row in static_rows[TRAIN_COUNT:]], dtype=float)

    teacher = {
        str(nodes): _parallel_search(compiled, native, parent, records, nodes)
        for nodes in TEACHER_BUDGETS
    }
    stable = [
        left["action_key"] == right["action_key"]
        for left, right in zip(teacher["40000"], teacher["80000"])
    ]
    teacher_80k = teacher["80000"]
    train_teacher = teacher_80k[:TRAIN_COUNT]
    validation_teacher = teacher_80k[TRAIN_COUNT:]
    stable_train = [index for index in range(TRAIN_COUNT) if stable[index]]
    stable_validation = [index for index in range(VALIDATION_COUNT) if stable[TRAIN_COUNT + index]]
    ordinary_train = [index for index in stable_train if not _is_mate_band(train_teacher[index])]
    ordinary_validation = [index for index in stable_validation if not _is_mate_band(validation_teacher[index])]
    mate_train = [index for index in range(TRAIN_COUNT) if _is_mate_band(train_teacher[index])]
    mate_validation = [index for index in range(VALIDATION_COUNT) if _is_mate_band(validation_teacher[index])]
    if len(ordinary_train) < CV_FOLDS * 2:
        raise ValueError(f"{label}: too few stable ordinary training positions")

    y_train = np.asarray([row["owner0_value"] for row in train_teacher], dtype=float)
    y_validation = np.asarray([row["owner0_value"] for row in validation_teacher], dtype=float)
    fit_x = x_train[ordinary_train]
    fit_residual = (y_train - current_train)[ordinary_train]
    active, scale, training_std = _training_scale(fit_x)
    fit_x_scaled = fit_x[:, active] / scale
    validation_x_scaled = x_validation[:, active] / scale
    selected_alpha, cv_rows = _cv_select_alpha(fit_x_scaled, fit_residual)
    theta = _ridge_svd(fit_x_scaled, fit_residual, selected_alpha)
    beta = np.zeros(x_train.shape[1], dtype=float)
    beta[active] = theta / scale
    direct_child = _checkpoint_with_delta(parent, beta, label=label, stage="F55-well-posed-cv-ridge")
    direct_applied = np.asarray(
        [direct_child.board_weights[key] - parent.board_weights[key] for key in sorted(parent.board_weights)]
        + [direct_child.hand_weights[key] - parent.hand_weights[key] for key in sorted(parent.hand_weights)]
        + [direct_child.dynamic_weights.get(name, 0.0) - parent.dynamic_weights.get(name, 0.0)
           for name in DYNAMIC_FEATURE_NAMES],
        dtype=float,
    )
    unbounded_train = current_train + x_train @ beta
    unbounded_validation = current_validation + x_validation @ beta
    applied_train = current_train + x_train @ direct_applied
    applied_validation = current_validation + x_validation @ direct_applied
    bound = MATE_BAND_NATIVE_THRESHOLD / parent.semantic_native_scale
    value = {
        "training_stable_non_mate": {
            "unbounded": _metrics(unbounded_train[ordinary_train], y_train[ordinary_train]),
            "applied_child": _metrics(applied_train[ordinary_train], y_train[ordinary_train]),
        },
        "validation_stable_non_mate": {
            "parent": _metrics(current_validation[ordinary_validation], y_validation[ordinary_validation]),
            "unbounded": _metrics(unbounded_validation[ordinary_validation], y_validation[ordinary_validation]),
            "applied_child": _metrics(applied_validation[ordinary_validation], y_validation[ordinary_validation]),
            "parent_bounded": _bounded_metrics(current_validation[ordinary_validation], y_validation[ordinary_validation], bound),
            "applied_child_bounded": _bounded_metrics(applied_validation[ordinary_validation], y_validation[ordinary_validation], bound),
        },
    }

    parent_validation_rows = _parallel_search(compiled, native, parent, validation_records, validation_nodes)
    child_validation_rows = _parallel_search(compiled, native, direct_child, validation_records, validation_nodes)
    policy = {
        "stable_non_mate": _policy_metrics(parent_validation_rows, child_validation_rows, validation_teacher, ordinary_validation),
        "stable_mate_band": _policy_metrics(parent_validation_rows, child_validation_rows, validation_teacher, mate_validation),
    }
    feature_names = _feature_names(tuple(sorted(parent.board_weights)))
    raw_condition = _conditioning(fit_x[:, active])
    scaled_condition = _conditioning(fit_x_scaled)
    native_effective = _native_delta(compiled, native, parent, direct_child)
    native_counts = {
        "effective_nonzero": sum(
            abs(value) > 0
            for block in ("board", "hand", "dynamic")
            for value in native_effective[block]["delta"]
        ),
    }
    return {
        "label": label,
        "parent_checkpoint_id": parent.checkpoint_id,
        "corpus": {
            "schema_version": corpus_payload["schema_version"],
            "corpus_id": corpus_info["corpus_id"],
            "source_opening_corpus_id": corpus_info["source_opening_corpus_id"],
            "seed": corpus_payload["seed"],
            "count": len(records),
            "split": {"train": [0, TRAIN_COUNT], "validation": [TRAIN_COUNT, CORPUS_COUNT]},
            "training_position_keys_sha256": stable_sha256([r["position_key"] for r in train_records]),
            "validation_position_keys_sha256": stable_sha256([r["position_key"] for r in validation_records]),
            "evaluator_invoked_for_selection": False,
        },
        "teacher_stability": {
            "40k_vs_80k": _agreement(teacher["40000"], teacher["80000"]),
            "threshold": TEACHER_STABILITY_THRESHOLD,
            "stable_count": sum(stable),
            "stable_rate": sum(stable) / len(stable),
            "stable_train_count": len(stable_train),
            "stable_validation_count": len(stable_validation),
        },
        "target_partition": {
            "native_static_score_band": [-MATE_BAND_NATIVE_THRESHOLD, MATE_BAND_NATIVE_THRESHOLD],
            "definition": "mate_band iff abs(80k Native score) > static-score band",
            "train_ordinary_non_mate_count": len(ordinary_train),
            "train_mate_band_count": len(mate_train),
            "validation_ordinary_non_mate_count": len([i for i in range(VALIDATION_COUNT) if not _is_mate_band(validation_teacher[i])]),
            "validation_mate_band_count": len(mate_validation),
            "stable_validation_ordinary_non_mate_count": len(ordinary_validation),
            "stable_validation_mate_band_count": len(mate_validation),
        },
        "linear_inverse_problem": {
            "feature_names": feature_names,
            "raw_coordinate_count": int(x_train.shape[1]),
            "active_feature_count": int(np.count_nonzero(active)),
            "frozen_zero_variance_features": [name for name, is_active in zip(feature_names, active) if not is_active],
            "training_rms_scale": {name: float(value) for name, value in zip(np.asarray(feature_names)[active], scale)},
            "training_std_active": {name: float(value) for name, value in zip(np.asarray(feature_names)[active], training_std[active])},
            "conditioning_before_scaling": raw_condition,
            "conditioning_after_scaling": scaled_condition,
            "cv_folds": CV_FOLDS,
            "alpha_grid": list(ALPHA_GRID),
            "selected_alpha": selected_alpha,
            "cv_scores": cv_rows,
            "coefficient_l2": float(np.linalg.norm(beta)),
            "applied_delta_l2": float(np.linalg.norm(direct_applied)),
            "clipped_parameter_count": int(np.count_nonzero(np.abs(direct_applied - beta) > 1e-12)),
            "native_effective_parameter_count": native_counts,
            "native_weight_bound": min(parent.w_max, 1_000_000 / parent.semantic_native_scale),
        },
        "value_capacity": value,
        "policy_leverage": policy,
        "classification": "PENDING_REVIEW",
    }


def _classify_result(result: dict) -> str:
    metrics = result["value_capacity"]["validation_stable_non_mate"]
    parent_mse = metrics["parent"]["mse"]
    child_mse = metrics["applied_child"]["mse"]
    value_positive = (
        parent_mse is not None and child_mse is not None
        and parent_mse > 0
        and (parent_mse - child_mse) / parent_mse >= VALUE_IMPROVEMENT_THRESHOLD
    )
    policy = result["policy_leverage"]["stable_non_mate"]
    parent_agreement = policy["parent_teacher_best_move_agreement"]
    child_agreement = policy["child_teacher_best_move_agreement"]
    policy_positive = (
        parent_agreement is not None and child_agreement is not None
        and child_agreement > parent_agreement + 0.01
        and (policy["move_flip_rate_vs_parent"] or 0.0) > 0.0
    )
    if value_positive and policy_positive:
        return "DIRECT_LINEAR_POLICY_CAPACITY_SUPPORTED"
    if value_positive:
        return "VALUE_CAPACITY_PRESENT_POLICY_LEVERAGE_LIMITING"
    return "LOCAL_LINEAR_EVALUATOR_CAPACITY_LIMITING"


def _classify(results: list[dict]) -> tuple[str, dict[str, str]]:
    by_ruleset = {result["label"]: _classify_result(result) for result in results}
    distinct = set(by_ruleset.values())
    overall = next(iter(distinct)) if len(distinct) == 1 else "MIXED_RULESET_OUTCOME"
    return overall, by_ruleset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation-nodes", type=int, default=2000)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results = [_run_label(label, args.validation_nodes) for label in CORPUS_SEEDS]
    classification, classification_by_ruleset = _classify(results)
    for result in results:
        result["classification"] = classification_by_ruleset[result["label"]]
    payload = {
        "work_order": "GENERICCHESS-F55-WELL-POSED-LINEAR-CAPACITY-ORACLE",
        "corpus_count": CORPUS_COUNT,
        "split": {"train": TRAIN_COUNT, "validation": VALIDATION_COUNT},
        "teacher_budgets": TEACHER_BUDGETS,
        "mate_band_native_threshold": MATE_BAND_NATIVE_THRESHOLD,
        "value_improvement_threshold": VALUE_IMPROVEMENT_THRESHOLD,
        "results": results,
        "classification": classification,
        "classification_by_ruleset": classification_by_ruleset,
        "wall_seconds": time.perf_counter() - started,
    }
    (OUT / "f55_results.json").write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "work_order": payload["work_order"],
        "classification": classification,
        "classification_by_ruleset": classification_by_ruleset,
        "wall_seconds": payload["wall_seconds"],
        "results": [
            {
                "label": result["label"],
                "corpus_id": result["corpus"]["corpus_id"],
                "teacher_stability": result["teacher_stability"],
                "target_partition": result["target_partition"],
                "selected_alpha": result["linear_inverse_problem"]["selected_alpha"],
                "value_capacity": result["value_capacity"]["validation_stable_non_mate"],
                "policy_leverage": result["policy_leverage"]["stable_non_mate"],
            }
            for result in results
        ],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
