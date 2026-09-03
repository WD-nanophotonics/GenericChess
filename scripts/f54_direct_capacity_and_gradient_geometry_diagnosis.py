"""F54 direct linear capacity and gradient-geometry diagnosis.

The corpus is generated from Core legal actions only.  Search is used only
after the 32/32 split is frozen, first to build the current-v2 teacher and
then to evaluate diagnostic checkpoints.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from f50_generic_learnable_evaluator import (  # noqa: E402
    WEIGHTS,
    _native_delta,
    _ruleset,
)
from f53_learning_signal_variance_and_target_comparison import (  # noqa: E402
    DIAGNOSTIC_FRACTION,
    _action_key,
    _blocks,
    _block_norm,
)
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.core.actions import action_from_dict, action_to_dict  # noqa: E402
from generic_chess.learning.features import (  # noqa: E402
    DYNAMIC_FEATURE_NAMES,
    linear_value,
    material_features,
    non_anchor_type_ids,
)
from generic_chess.learning.material import LearnableMaterialCheckpoint  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.learning.diagnostics import generate_diagnostic_corpus  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.native.adapter import pack_semantic_search_position  # noqa: E402
from generic_chess.native.semantic import dynamic_features as native_dynamic_features  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402
from generic_chess.rules.compiler import compile_ruleset_for_execution  # noqa: E402
from generic_chess.session.session import GameSession  # noqa: E402


OUT = ROOT / ".generic_chess_flow" / "f54-direct-capacity-and-gradient-geometry"
CORPUS_COUNT = 64
TRAIN_COUNT = 32
VALIDATION_COUNT = 32
OPENING_COUNT = 16
CORPUS_MIN_PLIES = 8
CORPUS_MAX_PLIES = 40
CORPUS_SEEDS = {
    "A_CANONICAL_WESTERN_CHESS": 540100,
    "B_CANONICAL_STANDARD_SHOGI": 540200,
}
TEACHER_BUDGETS = (40000, 80000)
TEACHER_STABILITY_THRESHOLD = 0.85
RIDGE_ALPHA = 1e-3
SEMANTIC_NATIVE_VALUE_LIMIT = 1_000_000


def _parent(label: str):
    compiled, _native, profile = _ruleset(label)
    return LearnableMaterialCheckpoint.from_profile(
        compiled, profile, training_seed=5400000, dynamic_weights=dict(WEIGHTS)
    )


def _session(compiled, record: dict) -> GameSession:
    session = GameSession(compiled)
    for payload in record["action_history"]:
        session.submit(action_from_dict(payload))
    return session


def _record_dict(position) -> dict:
    return {
        "index": position.index,
        "action_history": [action_to_dict(action) for action in position.action_history],
        "position_key": position.position_key,
        "side_to_move": position.side_to_move,
        "ply": position.ply,
    }


def _generate_corpus(label: str, compiled) -> tuple[dict, dict]:
    seed = CORPUS_SEEDS[label]
    openings = generate_arena_openings(
        compiled, count=OPENING_COUNT, seed=seed,
        min_plies=2, max_plies=6,
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


def _feature_names(type_ids: tuple[str, ...]) -> list[str]:
    return (
        [f"board:{type_id}" for type_id in type_ids]
        + [f"hand:{type_id}" for type_id in type_ids]
        + [f"dynamic:{name}" for name in DYNAMIC_FEATURE_NAMES]
    )


def _static_row(compiled, native, parent, record: dict) -> dict:
    session = _session(compiled, record)
    type_ids = tuple(sorted(parent.board_weights))
    material = material_features(session.state.position, type_ids, perspective=0)
    packed = pack_semantic_search_position(compiled, native, session)
    dynamic = native_dynamic_features(native, packed)
    vector = np.asarray(
        list(material.board_counts) + list(material.hand_counts) + list(dynamic),
        dtype=float,
    )
    static_value = linear_value(
        material, parent.board_weights, parent.hand_weights,
        dynamic, parent.dynamic_weights,
    )
    return {
        "vector": vector,
        "static_value": float(static_value),
        "side_to_move": session.state.position.side_to_move,
    }


def _owner0_native_value(native_score: int, side_to_move: int, parent) -> float:
    if side_to_move not in (0, 1):
        raise ValueError("side_to_move must be 0 or 1")
    value = native_score / parent.semantic_native_scale
    return value if side_to_move == 0 else -value


def _search_row(compiled, native, parent, record: dict, nodes: int) -> dict:
    session = _session(compiled, record)
    side_to_move = session.state.position.side_to_move
    result = SemanticSearchEngine(
        compiled, native, checkpoint=parent, tt_megabytes=8
    ).search(session, SearchLimits(max_depth=12, max_nodes=nodes, quiescence_max_depth=0))
    return {
        "action_key": _action_key(None if result.action is None else action_to_dict(result.action)),
        "native_score": int(result.score),
        "owner0_value": _owner0_native_value(result.score, side_to_move, parent),
        "side_to_move": side_to_move,
        "nodes": result.nodes,
    }


def _parallel_search(compiled, native, parent, records: list[dict], nodes: int) -> list[dict]:
    workers = min(8, max(1, os.cpu_count() or 1), len(records) or 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda record: _search_row(compiled, native, parent, record, nodes), records))


def _agreement(left: list[dict], right: list[dict]) -> float:
    return (
        sum(a["action_key"] == b["action_key"] for a, b in zip(left, right)) / len(left)
        if left else 0.0
    )


def _metrics(prediction: np.ndarray, target: np.ndarray) -> dict:
    error = prediction - target
    correlation = None
    if len(prediction) > 1 and np.std(prediction) > 0 and np.std(target) > 0:
        correlation = float(np.corrcoef(prediction, target)[0, 1])
    return {
        "count": int(len(prediction)),
        "mse": float(np.mean(error * error)) if len(error) else None,
        "mae": float(np.mean(np.abs(error))) if len(error) else None,
        "correlation": correlation,
    }


def _ridge_fit(features: np.ndarray, residual: np.ndarray, alpha: float = RIDGE_ALPHA) -> np.ndarray:
    if features.ndim != 2 or residual.ndim != 1 or len(features) != len(residual):
        raise ValueError("ridge inputs have incompatible shapes")
    gram = features.T @ features
    gram += alpha * np.eye(features.shape[1])
    return np.linalg.solve(gram, features.T @ residual)


def _checkpoint_with_delta(parent, delta: np.ndarray, *, label: str, stage: str):
    type_ids = tuple(sorted(parent.board_weights))
    weight_bound = min(
        parent.w_max,
        SEMANTIC_NATIVE_VALUE_LIMIT / parent.semantic_native_scale,
    )

    def bounded(value: float) -> float:
        return max(-weight_bound, min(weight_bound, value))

    board = {
        type_id: bounded(parent.board_weights[type_id] + float(delta[index]))
        for index, type_id in enumerate(type_ids)
    }
    offset = len(type_ids)
    hand = {
        type_id: bounded(parent.hand_weights[type_id] + float(delta[offset + index]))
        for index, type_id in enumerate(type_ids)
    }
    dynamic_offset = offset * 2
    dynamic = {
        name: bounded(parent.dynamic_weights.get(name, 0.0) + float(delta[dynamic_offset + index]))
        for index, name in enumerate(DYNAMIC_FEATURE_NAMES)
    }
    return parent.child_checkpoint(
        board_weights=board, hand_weights=hand, dynamic_weights=dynamic,
        games_seen_delta=0, positions_seen_delta=0, training_updates_delta=1,
        training_config_hash=stable_sha256({"stage": stage, "label": label}),
        training_seed=5400000,
    )


def _scaled_direction_checkpoint(parent, direction: np.ndarray, *, label: str, stage: str):
    base = np.asarray(
        [
            parent.board_weights[key] for key in sorted(parent.board_weights)
        ] + [
            parent.hand_weights[key] for key in sorted(parent.hand_weights)
        ] + [
            parent.dynamic_weights.get(name, 0.0) for name in DYNAMIC_FEATURE_NAMES
        ],
        dtype=float,
    )
    base_norm = float(np.linalg.norm(base))
    direction_norm = float(np.linalg.norm(direction))
    scaled = direction * (DIAGNOSTIC_FRACTION * base_norm / direction_norm) if direction_norm else np.zeros_like(direction)
    return _checkpoint_with_delta(parent, scaled, label=label, stage=stage)


def _compare_decisions(compiled, native, parent, candidate, records, teacher_rows, nodes):
    parent_rows = _parallel_search(compiled, native, parent, records, nodes)
    candidate_rows = _parallel_search(compiled, native, candidate, records, nodes)
    teacher_actions = [row["action_key"] for row in teacher_rows]
    parent_actions = [row["action_key"] for row in parent_rows]
    candidate_actions = [row["action_key"] for row in candidate_rows]
    n = len(records)
    return {
        "positions": n,
        "teacher_best_move_agreement": sum(a == b for a, b in zip(candidate_actions, teacher_actions)) / n if n else 0.0,
        "parent_teacher_best_move_agreement": sum(a == b for a, b in zip(parent_actions, teacher_actions)) / n if n else 0.0,
        "move_flip_rate_vs_parent": sum(a != b for a, b in zip(candidate_actions, parent_actions)) / n if n else 0.0,
        "mean_abs_score_change_vs_parent": sum(abs(a["native_score"] - b["native_score"]) for a, b in zip(parent_rows, candidate_rows)) / n if n else 0.0,
    }


def _prefix_vectors(compiled, native, parent, record: dict) -> list[np.ndarray]:
    session = GameSession(compiled)
    actions = [action_from_dict(payload) for payload in record["action_history"]]
    vectors = []
    for action in [None] + actions:
        if action is not None:
            session.submit(action)
        type_ids = tuple(sorted(parent.board_weights))
        material = material_features(session.state.position, type_ids, perspective=0)
        packed = pack_semantic_search_position(compiled, native, session)
        dynamic = native_dynamic_features(native, packed)
        vectors.append(np.asarray(
            list(material.board_counts) + list(material.hand_counts) + list(dynamic),
            dtype=float,
        ))
    return vectors


def _td_direction(prefixes: list[list[np.ndarray]], parent, feature_scale: np.ndarray | None = None) -> np.ndarray:
    dimension = len(next(iter(prefixes))[0])
    direction = np.zeros(dimension, dtype=float)
    type_ids = tuple(sorted(parent.board_weights))
    parent_weights = np.asarray(
        [parent.board_weights[key] for key in type_ids]
        + [parent.hand_weights[key] for key in type_ids]
        + [parent.dynamic_weights.get(name, 0.0) for name in DYNAMIC_FEATURE_NAMES],
        dtype=float,
    )
    for vectors in prefixes:
        values = [math.tanh(float(np.dot(vector, parent_weights)) / parent.value_scale) for vector in vectors]
        eligibility = np.zeros(dimension, dtype=float)
        for index in range(len(vectors) - 1):
            vector = vectors[index]
            grad_scale = (1.0 - values[index] * values[index]) / parent.value_scale
            if feature_scale is not None:
                eligibility = 0.7 * eligibility + grad_scale * (vector / feature_scale)
            else:
                eligibility = 0.7 * eligibility + grad_scale * vector
            direction += (values[index + 1] - values[index]) * eligibility
    if feature_scale is not None:
        direction = direction / feature_scale
    return direction


def _geometry(prefixes, raw_direction: np.ndarray, feature_names: list[str]) -> dict:
    matrix = np.vstack([vector for sequence in prefixes for vector in sequence])
    mean = np.mean(matrix, axis=0)
    std = np.std(matrix, axis=0)
    rms = np.sqrt(np.mean(matrix * matrix, axis=0))
    safe_rms = np.where(rms > 1e-9, rms, 1.0)
    covariance = np.cov(matrix, rowvar=False, ddof=0).tolist()
    condition = float(np.linalg.cond(matrix - mean)) if matrix.shape[0] > 1 else None
    energy = raw_direction * raw_direction
    total = float(np.sum(energy))
    return {
        "sample_count": int(matrix.shape[0]),
        "feature_names": feature_names,
        "mean": mean.tolist(),
        "std": std.tolist(),
        "rms": rms.tolist(),
        "covariance": covariance,
        "condition_number_centered": condition,
        "raw_gradient_energy": {
            name: float(value) for name, value in zip(feature_names, energy)
        },
        "raw_gradient_energy_fraction": {
            name: float(value / total) if total else 0.0
            for name, value in zip(feature_names, energy)
        },
        "safe_rms": safe_rms.tolist(),
    }


def _block_energy(direction: np.ndarray, dimension: int) -> dict:
    board_end = (dimension - 3) // 2
    parts = {
        "board": direction[:board_end],
        "hand": direction[board_end:2 * board_end],
        "dynamic": direction[2 * board_end:],
    }
    total = float(np.dot(direction, direction))
    return {
        block: {
            "l2_norm": float(np.linalg.norm(values)),
            "squared_energy_fraction": float(np.dot(values, values) / total) if total else 0.0,
        }
        for block, values in parts.items()
    }


def _run_label(label: str, validation_nodes: int) -> dict:
    compiled, native, _profile = _ruleset(label)
    parent = _parent(label)
    corpus_payload, corpus_info = _generate_corpus(label, compiled)
    records = corpus_info["records"]
    train_records = records[:TRAIN_COUNT]
    validation_records = records[TRAIN_COUNT:TRAIN_COUNT + VALIDATION_COUNT]
    static_rows = [_static_row(compiled, native, parent, record) for record in records]
    train_static = static_rows[:TRAIN_COUNT]
    validation_static = static_rows[TRAIN_COUNT:TRAIN_COUNT + VALIDATION_COUNT]

    teacher = {
        str(nodes): _parallel_search(compiled, native, parent, records, nodes)
        for nodes in TEACHER_BUDGETS
    }
    stable = [
        left["action_key"] == right["action_key"]
        for left, right in zip(teacher["40000"], teacher["80000"])
    ]
    stable_train = [index for index in range(TRAIN_COUNT) if stable[index]]
    stable_validation = [index for index in range(VALIDATION_COUNT) if stable[TRAIN_COUNT + index]]
    train_teacher = teacher["80000"][:TRAIN_COUNT]
    validation_teacher = teacher["80000"][TRAIN_COUNT:]
    x_train = np.vstack([row["vector"] for row in train_static])
    x_validation = np.vstack([row["vector"] for row in validation_static])
    y_train = np.asarray([row["owner0_value"] for row in train_teacher], dtype=float)
    y_validation = np.asarray([row["owner0_value"] for row in validation_teacher], dtype=float)
    current_train = np.asarray([row["static_value"] for row in train_static], dtype=float)
    current_validation = np.asarray([row["static_value"] for row in validation_static], dtype=float)

    fit_train_indices = stable_train or list(range(TRAIN_COUNT))
    eval_validation_indices = stable_validation or list(range(VALIDATION_COUNT))
    beta = _ridge_fit(x_train[fit_train_indices], (y_train - current_train)[fit_train_indices])
    direct_child = _checkpoint_with_delta(parent, beta, label=label, stage="F54-direct-ridge")
    direct_applied = np.asarray(
        [
            direct_child.board_weights[key] - parent.board_weights[key]
            for key in sorted(parent.board_weights)
        ] + [
            direct_child.hand_weights[key] - parent.hand_weights[key]
            for key in sorted(parent.hand_weights)
        ] + [
            direct_child.dynamic_weights.get(name, 0.0) - parent.dynamic_weights.get(name, 0.0)
            for name in DYNAMIC_FEATURE_NAMES
        ],
        dtype=float,
    )

    prefixes = [_prefix_vectors(compiled, native, parent, record) for record in train_records]
    feature_names = _feature_names(tuple(sorted(parent.board_weights)))
    raw_td = _td_direction(prefixes, parent)
    prefix_matrix = np.vstack([vector for sequence in prefixes for vector in sequence])
    rms = np.sqrt(np.mean(prefix_matrix * prefix_matrix, axis=0))
    safe_rms = np.where(rms > 1e-9, rms, 1.0)
    normalized_td = _td_direction(prefixes, parent, safe_rms)
    raw_td_child = _scaled_direction_checkpoint(parent, raw_td, label=label, stage="F54-raw-td")
    normalized_td_child = _scaled_direction_checkpoint(parent, normalized_td, label=label, stage="F54-rms-normalized-td")

    stable_validation_records = [validation_records[index] for index in eval_validation_indices]
    stable_validation_teacher = [validation_teacher[index] for index in eval_validation_indices]
    candidates = {
        "raw_td": raw_td_child,
        "rms_normalized_td": normalized_td_child,
        "direct_ridge": direct_child,
    }
    comparisons = {
        name: _compare_decisions(
            compiled, native, parent, candidate,
            stable_validation_records, stable_validation_teacher, validation_nodes,
        )
        for name, candidate in candidates.items()
    }
    native_effective = {
        name: _native_delta(compiled, native, parent, candidate)
        for name, candidate in candidates.items()
    }
    native_counts = {
        name: sum(
            abs(value) > 0
            for block in ("board", "hand", "dynamic")
            for value in delta[block]["delta"]
        )
        for name, delta in native_effective.items()
    }
    direct_train_prediction = current_train + x_train @ beta
    direct_validation_prediction = current_validation + x_validation @ beta
    applied_train_prediction = current_train + x_train @ direct_applied
    applied_validation_prediction = current_validation + x_validation @ direct_applied
    geometry = _geometry(prefixes, raw_td, feature_names)
    geometry["raw_gradient_block_energy"] = _block_energy(raw_td, len(feature_names))
    geometry["normalized_td_block_energy"] = _block_energy(normalized_td, len(feature_names))
    geometry["raw_td_norm"] = float(np.linalg.norm(raw_td))
    geometry["normalized_td_norm"] = float(np.linalg.norm(normalized_td))
    geometry["td_direction_cosine_raw_vs_normalized"] = float(
        np.dot(raw_td, normalized_td) / (np.linalg.norm(raw_td) * np.linalg.norm(normalized_td))
    ) if np.linalg.norm(raw_td) and np.linalg.norm(normalized_td) else None
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
            "stable_rate": sum(stable) / len(stable) if stable else 0.0,
            "stable_train_count": len(stable_train),
            "stable_validation_count": len(stable_validation),
        },
        "ridge": {
            "alpha": RIDGE_ALPHA,
            "fit_count": len(fit_train_indices),
            "coefficients": {name: float(value) for name, value in zip(feature_names, beta)},
            "coefficient_l2": float(np.linalg.norm(beta)),
            "applied_delta_l2": float(np.linalg.norm(direct_applied)),
            "clipped_parameter_count": int(np.count_nonzero(np.abs(direct_applied - beta) > 1e-12)),
            "native_weight_bound": min(parent.w_max, SEMANTIC_NATIVE_VALUE_LIMIT / parent.semantic_native_scale),
            "condition_number": float(np.linalg.cond(x_train[fit_train_indices])) if fit_train_indices else None,
            "training_before": _metrics(current_train[fit_train_indices], y_train[fit_train_indices]),
            "training_after": _metrics(applied_train_prediction[fit_train_indices], y_train[fit_train_indices]),
            "validation_before": _metrics(current_validation[eval_validation_indices], y_validation[eval_validation_indices]),
            "validation_after": _metrics(applied_validation_prediction[eval_validation_indices], y_validation[eval_validation_indices]),
            "oracle_unbounded_training_after": _metrics(direct_train_prediction[fit_train_indices], y_train[fit_train_indices]),
            "oracle_unbounded_validation_after": _metrics(direct_validation_prediction[eval_validation_indices], y_validation[eval_validation_indices]),
            "applied_child_training_after": _metrics(applied_train_prediction[fit_train_indices], y_train[fit_train_indices]),
            "applied_child_validation_after": _metrics(applied_validation_prediction[eval_validation_indices], y_validation[eval_validation_indices]),
        },
        "geometry": geometry,
        "direction_cosines": {
            "raw_td_vs_rms_normalized_td": float(np.dot(raw_td, normalized_td) / (np.linalg.norm(raw_td) * np.linalg.norm(normalized_td))) if np.linalg.norm(raw_td) and np.linalg.norm(normalized_td) else None,
            "raw_td_vs_direct_ridge": float(np.dot(raw_td, beta) / (np.linalg.norm(raw_td) * np.linalg.norm(beta))) if np.linalg.norm(raw_td) and np.linalg.norm(beta) else None,
            "rms_normalized_td_vs_direct_ridge": float(np.dot(normalized_td, beta) / (np.linalg.norm(normalized_td) * np.linalg.norm(beta))) if np.linalg.norm(normalized_td) and np.linalg.norm(beta) else None,
        },
        "native_effective_parameter_count": native_counts,
        "comparisons": comparisons,
        "classification": "PENDING_REVIEW",
    }


def _classify_result(result: dict) -> str:
    direct = result["comparisons"]["direct_ridge"]
    normalized = result["comparisons"]["rms_normalized_td"]
    raw = result["comparisons"]["raw_td"]
    direct_policy_positive = (
        direct["teacher_best_move_agreement"]
        > direct["parent_teacher_best_move_agreement"] + 0.01
        and direct["move_flip_rate_vs_parent"] > 0.0
    )
    direct_value_positive = (
        result["ridge"]["validation_after"]["mse"]
        < result["ridge"]["validation_before"]["mse"]
    )
    normalized_positive = (
        normalized["teacher_best_move_agreement"]
        > normalized["parent_teacher_best_move_agreement"] + 0.01
        and normalized["move_flip_rate_vs_parent"] > 0.0
    )
    learner_positive = (
        max(raw["teacher_best_move_agreement"], normalized["teacher_best_move_agreement"])
        > raw["parent_teacher_best_move_agreement"] + 0.01
    )
    if normalized_positive:
        return "FEATURE_SCALE_NORMALIZATION_SUPPORTED"
    if direct_policy_positive or direct_value_positive:
        return "DIRECT_LINEAR_CAPACITY_SUPPORTED_GRADIENT_GEOMETRY_LIMITING"
    if learner_positive:
        return "POSITIVE_LEARNED_DIRECTION_SIGNAL"
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
        "work_order": "GENERICCHESS-F54-DIRECT-CAPACITY-AND-GRADIENT-GEOMETRY-DIAGNOSIS",
        "corpus_count": CORPUS_COUNT,
        "split": {"train": TRAIN_COUNT, "validation": VALIDATION_COUNT},
        "teacher_budgets": TEACHER_BUDGETS,
        "diagnostic_fraction": DIAGNOSTIC_FRACTION,
        "results": results,
        "classification": classification,
        "classification_by_ruleset": classification_by_ruleset,
        "wall_seconds": time.perf_counter() - started,
    }
    (OUT / "f54_results.json").write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "work_order": payload["work_order"],
        "classification": classification,
        "wall_seconds": payload["wall_seconds"],
        "results": [
            {
                "label": result["label"],
                "corpus_id": result["corpus"]["corpus_id"],
                "teacher_stability": result["teacher_stability"],
                "ridge_validation": result["ridge"]["validation_after"],
                "comparisons": result["comparisons"],
            }
            for result in results
        ],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
