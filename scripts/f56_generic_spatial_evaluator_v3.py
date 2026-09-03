"""F56 generic spatial evaluator v3 capacity gate.

The v3 residual is additive to the frozen v2 evaluator.  Occupancy has an
explicit owner/current-type/3x3-cell axis, while each owner/type row is
parameterized by eight independent zero-sum coordinates.  Local control is a
nine-cell residual whose total is zero, also represented by eight coordinates.
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

from f50_generic_learnable_evaluator import _native_delta, _ruleset  # noqa: E402
from f54_direct_capacity_and_gradient_geometry_diagnosis import (  # noqa: E402
    _agreement,
    _checkpoint_with_delta,
    _metrics,
    _parent,
    _parallel_search,
    _record_dict,
    _session,
    _static_row,
)
from f55_well_posed_linear_capacity_oracle import (  # noqa: E402
    _conditioning,
    _cv_select_alpha,
    _training_scale,
)
from generic_chess.core.actions import action_from_dict  # noqa: E402
from generic_chess.learning.diagnostics import generate_diagnostic_corpus  # noqa: E402
from generic_chess.learning.features import (  # noqa: E402
    DYNAMIC_FEATURE_NAMES,
    SPATIAL_CELL_COUNT,
    localized_control_features,
    spatial_occupancy_features,
)
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.native.adapter import pack_semantic_search_position  # noqa: E402
from generic_chess.native.semantic import spatial_features as native_spatial_features  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402


OUT = ROOT / ".generic_chess_flow" / "f56-generic-spatial-evaluator-v3"
CORPUS_COUNT = 192
TRAIN_COUNT = 128
VALIDATION_COUNT = 64
OPENING_COUNT = 32
CORPUS_MIN_PLIES = 8
CORPUS_MAX_PLIES = 40
CORPUS_SEEDS = {
    "A_CANONICAL_WESTERN_CHESS": 560101,
    "B_CANONICAL_STANDARD_SHOGI": 560201,
}
TEACHER_BUDGETS = (40000, 80000)
MATE_BAND_NATIVE_THRESHOLD = 90_000_000
CV_FOLDS = 4
VALUE_IMPROVEMENT_THRESHOLD = 0.10
POLICY_IMPROVEMENT_THRESHOLD = 0.01
SPATIAL_NATIVE_LIMIT = 1_000_000


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


def _is_mate_band(row: dict) -> bool:
    return abs(int(row["native_score"])) > MATE_BAND_NATIVE_THRESHOLD


def _v3_features(compiled, native, record: dict, type_ids: tuple[str, ...]) -> tuple[np.ndarray, dict]:
    session = _session(compiled, record)
    packed = pack_semantic_search_position(compiled, native, session)
    native_features = native_spatial_features(native, packed)
    vector = np.asarray(
        list(native_features["occupancy"]) + list(native_features["localized_control"]),
        dtype=float,
    )
    python_occupancy = spatial_occupancy_features(session.state.position, type_ids)
    python_control = localized_control_features(session.state.position, compiled)
    python_vector = np.asarray(
        [value for owner in (0, 1) for type_id in type_ids for value in python_occupancy[f"{owner}:{type_id}"]]
        + list(python_control),
        dtype=float,
    )
    return vector, {"python_vector": python_vector}


def _reduced_vector(vector: np.ndarray, type_count: int) -> np.ndarray:
    rows = vector[:2 * type_count * SPATIAL_CELL_COUNT].reshape(2 * type_count, SPATIAL_CELL_COUNT)
    occupancy = (rows[:, :-1] - rows[:, -1, None]).reshape(-1)
    control = vector[2 * type_count * SPATIAL_CELL_COUNT:]
    return np.concatenate((occupancy, control[:-1] - control[-1]))


def _weights_from_reduced(beta: np.ndarray, type_ids: tuple[str, ...]) -> tuple[dict[str, tuple[float, ...]], tuple[float, ...]]:
    rows = {}
    cursor = 0
    for owner in (0, 1):
        for type_id in type_ids:
            first = beta[cursor:cursor + SPATIAL_CELL_COUNT - 1]
            cursor += SPATIAL_CELL_COUNT - 1
            rows[f"{owner}:{type_id}"] = tuple(first.tolist() + [-float(np.sum(first))])
    first = beta[cursor:cursor + SPATIAL_CELL_COUNT - 1]
    return rows, tuple(first.tolist() + [-float(np.sum(first))])


def _reduced_weights(spatial: dict[str, tuple[float, ...]], control: tuple[float, ...], type_ids: tuple[str, ...]) -> np.ndarray:
    values = []
    for owner in (0, 1):
        for type_id in type_ids:
            values.extend(spatial[f"{owner}:{type_id}"][:-1])
    values.extend(control[:-1])
    return np.asarray(values, dtype=float)


def _spatial_child(parent, beta: np.ndarray, type_ids: tuple[str, ...], label: str):
    # Native validates every fixed-point coordinate, including the derived
    # ninth coordinate.  Clip the eight independent coordinates before
    # reconstructing the zero-sum row, so the derived coordinate cannot be
    # eight times over the native bound.
    independent_q_bound = (SPATIAL_NATIVE_LIMIT - (SPATIAL_CELL_COUNT - 1)) // (SPATIAL_CELL_COUNT - 1)
    bound = min(
        parent.w_max,
        independent_q_bound / parent.semantic_native_scale,
    )
    applied = np.clip(np.asarray(beta, dtype=float), -bound, bound)
    clipped_spatial, clipped_control = _weights_from_reduced(applied, type_ids)
    child = parent.child_checkpoint(
        board_weights=parent.board_weights,
        hand_weights=parent.hand_weights,
        dynamic_weights=parent.dynamic_weights,
        spatial_occupancy_weights=clipped_spatial,
        localized_control_weights=clipped_control,
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=stable_sha256({"stage": "F56-spatial-oracle", "label": label}),
        training_seed=5600000,
    )
    return child, applied, int(np.count_nonzero(np.abs(applied - beta) > 1e-12)), bound


def _policy_metrics(parent_rows: list[dict], child_rows: list[dict], teacher_rows: list[dict], indices: list[int]) -> dict:
    if not indices:
        return {"positions": 0, "move_flip_rate_vs_parent": None,
                "parent_teacher_best_move_agreement": None,
                "child_teacher_best_move_agreement": None}
    parent = [parent_rows[i]["action_key"] for i in indices]
    child = [child_rows[i]["action_key"] for i in indices]
    teacher = [teacher_rows[i]["action_key"] for i in indices]
    count = len(indices)
    return {
        "positions": count,
        "move_flip_rate_vs_parent": sum(a != b for a, b in zip(child, parent)) / count,
        "parent_teacher_best_move_agreement": sum(a == b for a, b in zip(parent, teacher)) / count,
        "child_teacher_best_move_agreement": sum(a == b for a, b in zip(child, teacher)) / count,
    }


def _runtime_cost(compiled, native, parent, child, records: list[dict], nodes: int = 5000) -> dict:
    def run(checkpoint):
        rows = _parallel_search(compiled, native, checkpoint, records, nodes)
        elapsed = sum(row.get("elapsed_seconds", 0.0) for row in rows)
        return {"positions": len(rows), "nodes": sum(row["nodes"] for row in rows), "elapsed_seconds": elapsed}
    # _parallel_search does not retain elapsed time; run direct engines for a
    # small fixed surface so NPS is measured on exactly the same positions.
    def timed(checkpoint):
        values = []
        for record in records:
            session = _session(compiled, record)
            started = time.perf_counter()
            result = SemanticSearchEngine(compiled, native, checkpoint=checkpoint, tt_megabytes=0).search(
                session, __import__("generic_chess.ai.limits", fromlist=["SearchLimits"]).SearchLimits(
                    max_depth=12, max_nodes=nodes, quiescence_max_depth=0
                )
            )
            values.append((result.nodes, time.perf_counter() - started))
        total_nodes = sum(item[0] for item in values)
        elapsed = sum(item[1] for item in values)
        return {"positions": len(values), "nodes": total_nodes, "elapsed_seconds": elapsed,
                "nps": total_nodes / elapsed if elapsed else None}
    return {"v2_parent": timed(parent), "v3_zero_spatial": timed(child)}


def _run_label(label: str, validation_nodes: int) -> dict:
    compiled, native, _profile = _ruleset(label)
    parent = _parent(label)
    corpus_payload, corpus_info = _generate_corpus(label, compiled)
    records = corpus_info["records"]
    train_records = records[:TRAIN_COUNT]
    validation_records = records[TRAIN_COUNT:]
    type_ids = tuple(native.type_ids)
    base_rows = [_static_row(compiled, native, parent, record) for record in records]
    x_v3 = np.vstack([_v3_features(compiled, native, record, type_ids)[0] for record in records])
    x_reduced = np.vstack([_reduced_vector(row, len(type_ids)) for row in x_v3])
    teacher = {str(nodes): _parallel_search(compiled, native, parent, records, nodes) for nodes in TEACHER_BUDGETS}
    stable = [a["action_key"] == b["action_key"] for a, b in zip(teacher["40000"], teacher["80000"])]
    teacher_80k = teacher["80000"]
    train_teacher = teacher_80k[:TRAIN_COUNT]
    validation_teacher = teacher_80k[TRAIN_COUNT:]
    stable_train = [i for i in range(TRAIN_COUNT) if stable[i]]
    stable_validation = [i for i in range(VALIDATION_COUNT) if stable[TRAIN_COUNT + i]]
    ordinary_train = [i for i in stable_train if not _is_mate_band(train_teacher[i])]
    ordinary_validation = [i for i in stable_validation if not _is_mate_band(validation_teacher[i])]
    mate_train = [i for i in range(TRAIN_COUNT) if _is_mate_band(train_teacher[i])]
    mate_validation = [i for i in range(VALIDATION_COUNT) if _is_mate_band(validation_teacher[i])]
    if len(ordinary_train) < CV_FOLDS * 2:
        raise ValueError(f"{label}: too few stable ordinary training positions")
    y_train = np.asarray([row["owner0_value"] for row in train_teacher], dtype=float)
    y_validation = np.asarray([row["owner0_value"] for row in validation_teacher], dtype=float)
    current_train = np.asarray([row["static_value"] for row in base_rows[:TRAIN_COUNT]], dtype=float)
    current_validation = np.asarray([row["static_value"] for row in base_rows[TRAIN_COUNT:]], dtype=float)
    fit_x = x_reduced[ordinary_train]
    fit_residual = (y_train - current_train)[ordinary_train]
    active, scale, std = _training_scale(fit_x)
    fit_scaled = fit_x[:, active] / scale
    validation_scaled = x_reduced[TRAIN_COUNT:, active] / scale
    selected_alpha, cv_scores = _cv_select_alpha(fit_scaled, fit_residual)
    from f55_well_posed_linear_capacity_oracle import _ridge_svd
    theta = _ridge_svd(fit_scaled, fit_residual, selected_alpha)
    beta = np.zeros(x_reduced.shape[1], dtype=float)
    beta[active] = theta / scale
    child, applied, clipped_count, bound = _spatial_child(parent, beta, type_ids, label)
    unbounded_train = current_train + x_reduced[:TRAIN_COUNT] @ beta
    unbounded_validation = current_validation + x_reduced[TRAIN_COUNT:] @ beta
    applied_train = current_train + x_reduced[:TRAIN_COUNT] @ applied
    applied_validation = current_validation + x_reduced[TRAIN_COUNT:] @ applied
    value_bound = MATE_BAND_NATIVE_THRESHOLD / parent.semantic_native_scale
    value = {
        "training_stable_non_mate": {
            "unbounded": _metrics(unbounded_train[ordinary_train], y_train[ordinary_train]),
            "applied_child": _metrics(applied_train[ordinary_train], y_train[ordinary_train]),
        },
        "validation_stable_non_mate": {
            "parent": _metrics(current_validation[ordinary_validation], y_validation[ordinary_validation]),
            "unbounded": _metrics(unbounded_validation[ordinary_validation], y_validation[ordinary_validation]),
            "applied_child": _metrics(applied_validation[ordinary_validation], y_validation[ordinary_validation]),
            "parent_bounded": _metrics(np.tanh(current_validation[ordinary_validation] / value_bound), np.tanh(y_validation[ordinary_validation] / value_bound)),
            "applied_child_bounded": _metrics(np.tanh(applied_validation[ordinary_validation] / value_bound), np.tanh(y_validation[ordinary_validation] / value_bound)),
        },
    }
    parent_rows = _parallel_search(compiled, native, parent, validation_records, validation_nodes)
    child_rows = _parallel_search(compiled, native, child, validation_records, validation_nodes)
    policy = {
        "stable_non_mate": _policy_metrics(parent_rows, child_rows, validation_teacher, ordinary_validation),
        "stable_mate_band": _policy_metrics(parent_rows, child_rows, validation_teacher, mate_validation),
    }
    runtime_child, _unused, _zero_clipped, _zero_bound = _spatial_child(
        parent, np.zeros(x_reduced.shape[1]), type_ids, label + "-zero"
    )
    runtime = _runtime_cost(compiled, native, parent, runtime_child, validation_records[:8])
    parity_max = 0.0
    for index in range(min(8, len(records))):
        native_vector, detail = _v3_features(compiled, native, records[index], type_ids)
        parity_max = max(parity_max, float(np.max(np.abs(native_vector - detail["python_vector"]))))
    return {
        "label": label,
        "parent_checkpoint_id": parent.checkpoint_id,
        "child_checkpoint_id": child.checkpoint_id,
        "corpus": {
            "schema_version": corpus_payload["schema_version"],
            "corpus_id": corpus_info["corpus_id"],
            "source_opening_corpus_id": corpus_info["source_opening_corpus_id"],
            "seed": corpus_payload["seed"],
            "count": len(records),
            "split": {"development": [0, TRAIN_COUNT], "validation": [TRAIN_COUNT, CORPUS_COUNT]},
            "development_position_keys_sha256": stable_sha256([r["position_key"] for r in train_records]),
            "validation_position_keys_sha256": stable_sha256([r["position_key"] for r in validation_records]),
            "evaluator_invoked_for_selection": False,
        },
        "teacher_stability": {
            "40k_vs_80k": _agreement(teacher["40000"], teacher["80000"]),
            "stable_count": sum(stable), "stable_rate": sum(stable) / len(stable),
            "stable_development_count": len(stable_train),
            "stable_validation_count": len(stable_validation),
        },
        "target_partition": {
            "native_static_score_band": [-MATE_BAND_NATIVE_THRESHOLD, MATE_BAND_NATIVE_THRESHOLD],
            "definition": "mate_band iff abs(80k Native score) > static-score band",
            "development_ordinary_non_mate_count": len([i for i in range(TRAIN_COUNT) if not _is_mate_band(train_teacher[i])]),
            "development_mate_band_count": len(mate_train),
            "validation_ordinary_non_mate_count": len([i for i in range(VALIDATION_COUNT) if not _is_mate_band(validation_teacher[i])]),
            "validation_mate_band_count": len(mate_validation),
            "stable_development_ordinary_non_mate_count": len(ordinary_train),
            "stable_validation_ordinary_non_mate_count": len(ordinary_validation),
            "stable_validation_mate_band_count": len(mate_validation),
        },
        "spatial_parameterization": {
            "grid": [3, 3], "owner_axis": [0, 1], "type_count": len(type_ids),
            "occupancy_parameter_count": 2 * len(type_ids) * (SPATIAL_CELL_COUNT - 1),
            "localized_control_parameter_count": SPATIAL_CELL_COUNT - 1,
            "total_parameter_count": int(x_reduced.shape[1]),
            "active_parameter_count": int(np.count_nonzero(active)),
            "frozen_zero_variance_parameter_count": int(np.count_nonzero(~active)),
            "conditioning_before_scaling": _conditioning(fit_x[:, active]),
            "conditioning_after_scaling": _conditioning(fit_scaled),
            "cv_folds": CV_FOLDS, "selected_alpha": selected_alpha,
            "cv_scores": cv_scores,
            "coefficient_l2": float(np.linalg.norm(beta)),
            "applied_delta_l2": float(np.linalg.norm(applied)),
            "native_weight_bound": bound,
            "clipped_parameter_count": clipped_count,
            "python_native_feature_max_abs_delta_first_8": parity_max,
        },
        "value_capacity": value,
        "policy_leverage": policy,
        "runtime_cost": runtime,
        "classification": "PENDING_REVIEW",
    }


def _classify_result(result: dict) -> str:
    metrics = result["value_capacity"]["validation_stable_non_mate"]
    parent_mse = metrics["parent"]["mse"]
    child_mse = metrics["applied_child"]["mse"]
    value_positive = parent_mse and (parent_mse - child_mse) / parent_mse >= VALUE_IMPROVEMENT_THRESHOLD
    policy = result["policy_leverage"]["stable_non_mate"]
    policy_positive = (
        policy["parent_teacher_best_move_agreement"] is not None
        and policy["child_teacher_best_move_agreement"] is not None
        and policy["child_teacher_best_move_agreement"] > policy["parent_teacher_best_move_agreement"] + POLICY_IMPROVEMENT_THRESHOLD
    )
    if value_positive and policy_positive:
        return "GENERIC_SPATIAL_CAPACITY_SUPPORTED"
    if value_positive:
        return "SPATIAL_VALUE_CAPACITY_PRESENT_POLICY_LEVERAGE_LIMITING"
    return "SPATIAL_CAPACITY_NOT_SUPPORTED"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation-nodes", type=int, default=2000)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results = [_run_label(label, args.validation_nodes) for label in CORPUS_SEEDS]
    by_ruleset = {result["label"]: _classify_result(result) for result in results}
    distinct = set(by_ruleset.values())
    classification = next(iter(distinct)) if len(distinct) == 1 else "MIXED_RULESET_OUTCOME"
    for result in results:
        result["classification"] = by_ruleset[result["label"]]
    payload = {
        "work_order": "GENERICCHESS-F56-GENERIC-SPATIAL-EVALUATOR-V3",
        "corpus_count": CORPUS_COUNT, "split": {"development": TRAIN_COUNT, "validation": VALIDATION_COUNT},
        "teacher_budgets": TEACHER_BUDGETS, "classification": classification,
        "classification_by_ruleset": by_ruleset, "results": results,
        "wall_seconds": time.perf_counter() - started,
    }
    (OUT / "f56_results.json").write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "work_order": payload["work_order"], "classification": classification,
        "classification_by_ruleset": by_ruleset, "wall_seconds": payload["wall_seconds"],
        "results": [{"label": r["label"], "corpus_id": r["corpus"]["corpus_id"],
                     "teacher_stability": r["teacher_stability"],
                     "target_partition": r["target_partition"],
                     "value": r["value_capacity"]["validation_stable_non_mate"],
                     "policy": r["policy_leverage"]["stable_non_mate"],
                     "runtime_cost": r["runtime_cost"]} for r in results],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
