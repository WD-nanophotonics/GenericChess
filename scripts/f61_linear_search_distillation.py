"""R24 low-dimensional linear search distillation from the persisted D0 roots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import ArenaConfig, run_arena_game_resumable  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from scripts import f50_generic_learnable_evaluator as f50  # noqa: E402
from scripts import f54_direct_capacity_and_gradient_geometry_diagnosis as f54  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_gen0_gen1_strength_triage as gen  # noqa: E402
from scripts import f61_strength_first_triage as f61  # noqa: E402


RULESET = "B_CANONICAL_STANDARD_SHOGI"
PARENT_ID = "2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362"
ROOT_SEED = 620000
ROOT_COUNT = 24
FOLDS = 4
ROOTS_PER_FOLD = 6
RIDGE_ALPHA = 1e-3
WITNESS_SEED = 620700
ARENA_SEED = 620710
OUT = ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "linear_search_distillation.json"


def _weight_vector(parent) -> np.ndarray:
    type_ids = tuple(sorted(parent.board_weights))
    return np.asarray(
        [parent.board_weights[key] for key in type_ids]
        + [parent.hand_weights[key] for key in type_ids]
        + [parent.dynamic_weights.get(name, 0.0) for name in f54.DYNAMIC_FEATURE_NAMES],
        dtype=float,
    )


def _successor_feature(compiled, native, parent, record, action_payload):
    history = [f59.action_from_dict(item) for item in record["action_history"]]
    action = f59.action_from_dict(action_payload)
    successor = f59._record_from_actions(compiled, history + [action])
    if successor is None:
        raise RuntimeError("persisted action did not reconstruct a live successor")
    root_session = f59._session(compiled, record)
    root_side = int(root_session.state.position.side_to_move)
    static = f54._static_row(compiled, native, parent, successor)
    vector = np.asarray(static["vector"], dtype=float)
    if root_side == 1:
        vector = -vector
    return vector, float(np.dot(vector, _weight_vector(parent))), root_side


def _load_roots(compiled, native, parent):
    records = gen._d0_records(compiled, ROOT_SEED, count=ROOT_COUNT, smoke=False)
    roots = []
    total_actions = 0
    for record in records:
        spectrum = gen._load_root_checkpoint(compiled, parent, record, smoke=False)
        if spectrum is None:
            raise RuntimeError(f"missing persisted D0 spectrum for {record['position_key']}")
        rows = [row for row in spectrum if row.q_20k is not None]
        if len(rows) < 2:
            raise RuntimeError("persisted spectrum has fewer than two q20 rows")
        rebuilt = []
        for row in rows:
            vector, base_q, _side = _successor_feature(compiled, native, parent, record, row.action)
            if not np.isclose(base_q, row.base_q, rtol=0.0, atol=1e-9):
                raise RuntimeError("reconstructed F54 base_q disagrees with persisted F59 base_q")
            rebuilt.append({"vector": vector, "base_q": float(row.base_q), "q20": float(row.q_20k), "action": row.action, "action_key": row.action_key})
        roots.append(rebuilt)
        total_actions += len(rebuilt)
    return records, roots, total_actions


def _ridge_fit(features: np.ndarray, residual: np.ndarray) -> np.ndarray:
    gram = features.T @ features + RIDGE_ALPHA * np.eye(features.shape[1])
    return np.linalg.solve(gram, features.T @ residual)


def _metrics(roots, deltas):
    errors = []
    correct = total = 0
    regrets = []
    for root, delta in zip(roots, deltas):
        base = np.asarray([row["base_q"] for row in root], dtype=float)
        target = np.asarray([row["q20"] for row in root], dtype=float)
        prediction = base + np.asarray(delta, dtype=float)
        errors.extend((prediction - target).tolist())
        for left in range(len(root)):
            for right in range(left + 1, len(root)):
                sign = np.sign(target[left] - target[right])
                if sign == 0:
                    continue
                total += 1
                correct += int(sign == np.sign(prediction[left] - prediction[right]))
        regrets.append(float(np.max(target) - target[int(np.argmax(prediction))]))
    return {"mse": float(np.mean(np.square(errors))), "pairwise_ranking_accuracy": correct / total if total else 0.0, "comparable_pairs": total, "mean_root_top_action_q20_regret": float(np.mean(regrets)), "root_regrets": regrets}


def _fit_predict(roots, train_indices, held_indices):
    train_rows = [roots[index] for index in train_indices]
    features = np.vstack([row["vector"] for root in train_rows for row in root])
    residual = np.asarray([row["q20"] - row["base_q"] for root in train_rows for row in root], dtype=float)
    delta = _ridge_fit(features, residual)
    predictions = []
    for index in held_indices:
        predictions.append(np.asarray([float(np.dot(row["vector"], delta)) for row in roots[index]], dtype=float))
    return delta, predictions


def _effective_delta(parent, child) -> np.ndarray:
    type_ids = tuple(sorted(parent.board_weights))
    return np.asarray(
        [child.board_weights[key] - parent.board_weights[key] for key in type_ids]
        + [child.hand_weights[key] - parent.hand_weights[key] for key in type_ids]
        + [child.dynamic_weights.get(name, 0.0) - parent.dynamic_weights.get(name, 0.0) for name in f54.DYNAMIC_FEATURE_NAMES],
        dtype=float,
    )


def _child_from_delta(parent, delta):
    return f54._checkpoint_with_delta(parent, delta, label="F61 R24 linear search distillation", stage="F61-R24-linear-search-distillation")


def _witness(compiled, native, parent, child, cached):
    effective = _effective_delta(parent, child)
    openings = generate_arena_openings(compiled, count=4, seed=WITNESS_SEED, min_plies=2, max_plies=6)
    rows = []
    for opening, cached_row in zip(openings.openings, cached["witness_rows"]):
        record = {"action_history": [f59.action_to_dict(action) for action in opening.actions]}
        actions = cached_row["actions"]
        vectors = np.vstack([_successor_feature(compiled, native, parent, record, action)[0] for action in actions])
        base = np.asarray(cached_row["base_q"], dtype=float)
        target = np.asarray(cached_row["q20"], dtype=float)
        learned = base + vectors @ effective
        rows.append({"opening_id": opening.final_position_key, "base_q": base.tolist(), "linear_total_q": learned.tolist(), "q20": target.tolist()})
    return rows


def _pair_metrics(rows, key):
    roots = [{"base_q": row["base_q"], "q20": row["q20"]} for row in rows]
    deltas = [np.asarray(row[key], dtype=float) - np.asarray(row["base_q"], dtype=float) for row in rows]
    return _metrics(roots, deltas)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-arena", action="store_true")
    args = parser.parse_args()
    compiled, native, _profile = f50._ruleset(RULESET)
    parent = f54._parent(RULESET)
    if parent.checkpoint_id != PARENT_ID:
        raise RuntimeError("unexpected parent checkpoint")
    records, roots, action_count = _load_roots(compiled, native, parent)
    base_deltas = [np.zeros(len(roots[index]), dtype=float) for index in range(ROOT_COUNT)]
    oof_deltas = [None] * ROOT_COUNT
    fold_rows = []
    for fold in range(FOLDS):
        held = list(range(fold * ROOTS_PER_FOLD, (fold + 1) * ROOTS_PER_FOLD))
        train = [index for index in range(ROOT_COUNT) if index not in held]
        delta, predictions = _fit_predict(roots, train, held)
        for index, prediction in zip(held, predictions):
            oof_deltas[index] = prediction
        fold_rows.append({"fold": fold, "train_roots": len(train), "heldout_roots": len(held), "heldout_actions": int(sum(len(roots[index]) for index in held)), "delta_norm": float(np.linalg.norm(delta))})
    base_metrics = _metrics(roots, base_deltas)
    oof_metrics = _metrics(roots, oof_deltas)
    oof_gate = oof_metrics["mse"] < base_metrics["mse"] and oof_metrics["pairwise_ranking_accuracy"] >= base_metrics["pairwise_ranking_accuracy"] and oof_metrics["mean_root_top_action_q20_regret"] <= base_metrics["mean_root_top_action_q20_regret"]
    payload = {"schema": "generic-chess-f61-linear-search-distillation-v1", "ruleset": RULESET, "parent_checkpoint_id": parent.checkpoint_id, "training": {"root_seed": ROOT_SEED, "roots": ROOT_COUNT, "actions": action_count, "ridge_alpha": RIDGE_ALPHA, "features": "F54 board/hand/native-dynamic owner-perspective vector", "persisted_d0_only": True}, "oof": {"folds": fold_rows, "base": base_metrics, "linear_delta": oof_metrics, "gate_pass": oof_gate}}
    if not oof_gate:
        payload["decision"] = "STOP_BEFORE_FULL_CANDIDATE_OOF_GATE_FAILED"
    else:
        features = np.vstack([row["vector"] for root in roots for row in root])
        residual = np.asarray([row["q20"] - row["base_q"] for root in roots for row in root], dtype=float)
        delta = _ridge_fit(features, residual)
        child = _child_from_delta(parent, delta)
        payload["candidate"] = {"checkpoint_id": child.checkpoint_id, "effective_delta_sha256": f61.stable_sha256(_effective_delta(parent, child).tolist()), "raw_delta_norm": float(np.linalg.norm(delta))}
        cached_path = OUT.parent / "pointwise_search_transfer_witness.json"
        cached = json.loads(cached_path.read_text(encoding="utf-8"))
        witness_rows = _witness(compiled, native, parent, child, cached)
        base_witness = _pair_metrics(witness_rows, "base_q")
        linear_witness = _pair_metrics(witness_rows, "linear_total_q")
        witness_gate = linear_witness["mse"] < base_witness["mse"] and linear_witness["pairwise_ranking_accuracy"] >= base_witness["pairwise_ranking_accuracy"] and linear_witness["mean_root_top_action_q20_regret"] <= base_witness["mean_root_top_action_q20_regret"]
        payload["external_witness"] = {"seed": WITNESS_SEED, "base": base_witness, "linear_delta": linear_witness, "gate_pass": witness_gate, "rows": witness_rows}
        payload["decision"] = "STOP_BEFORE_ARENA" if not witness_gate else "READY_FOR_ARENA"
        if witness_gate and args.run_arena:
            openings = generate_arena_openings(compiled, count=1, seed=ARENA_SEED, min_plies=2, max_plies=6)
            result = run_arena_game_resumable(compiled, native, parent, child, ArenaConfig(pairs=1, nodes_per_move=2_000, max_depth=12, tt_megabytes=8, opening_seed=ARENA_SEED, opening_count=1, min_plies=2, max_plies=6, workers=1), progress_dir=OUT.parent / "arena-progress-linear-distillation" / str(compiled.ruleset_fingerprint) / f"seed-{ARENA_SEED}", openings=openings, stop_on_decision=False)
            if result.status != "COMPLETE" or result.summary is None:
                raise RuntimeError(f"Arena incomplete: {result.status} {result.reason}")
            payload["fresh_arena"] = {"opening_seed": ARENA_SEED, "pair_scores": list(result.summary.pair_scores), "mean_pair_score": result.summary.mean_pair_score, "game_wins": result.summary.game_wins, "game_draws": result.summary.game_draws, "game_losses": result.summary.game_losses}
            payload["decision"] = "ARENA_SCREEN_COMPLETE"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=lambda value: value.item() if isinstance(value, np.generic) else str(value)) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=lambda value: value.item() if isinstance(value, np.generic) else str(value)))


if __name__ == "__main__":
    main()
