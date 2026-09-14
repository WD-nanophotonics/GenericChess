"""R21 root-grouped out-of-fold shrinkage for the fixed POINTWISE_Q child."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.learning.arena import ArenaConfig, run_arena_game_resumable  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_gen0_gen1_strength_triage as gen  # noqa: E402
from scripts import f61_strength_first_triage as f61  # noqa: E402
from scripts import f61_pointwise_search_transfer_witness as r20  # noqa: E402


RULESET = "B_CANONICAL_STANDARD_SHOGI"
PARENT_ID = "2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362"
TRAINING_SEED = 59013
OPENING_SEED = 620700
ARENA_SEED = 620710
FOLDS = 4
ROOTS_PER_FOLD = 6
OUT = ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "pointwise_oof_shrinkage.json"


def _stats(rows: list[dict], prediction_key: str) -> dict:
    errors = []
    correct = total = 0
    root_rows = []
    for row in rows:
        target = np.asarray(row["target"], dtype=float)
        pred = np.asarray(row[prediction_key], dtype=float)
        errors.extend((pred - target).tolist())
        for i in range(len(target)):
            for j in range(i + 1, len(target)):
                sign = np.sign(target[i] - target[j])
                if sign == 0:
                    continue
                total += 1
                correct += int(sign == np.sign(pred[i] - pred[j]))
        teacher = int(np.argmax(target))
        chosen = int(np.argmax(pred))
        root_rows.append({"teacher_regret": float(np.max(target) - target[chosen]), "teacher_best_index": teacher, "chosen_index": chosen})
    return {"mse": float(np.mean(np.square(errors))), "pairwise_ranking_accuracy": correct / total if total else 0.0, "comparable_pairs": total, "root_top_action_teacher_regret": root_rows, "mean_root_top_action_teacher_regret": float(np.mean([r["teacher_regret"] for r in root_rows]))}


def _load_roots(compiled, parent):
    records = gen._d0_records(compiled, 620000, count=gen.ROOT_COUNT, smoke=False)
    roots = []
    for record in records:
        spectrum = gen._load_root_checkpoint(compiled, parent, record, smoke=False)
        if spectrum is None:
            raise RuntimeError(f"missing persisted D0 spectrum for {record['position_key']}")
        usable = [row for row in spectrum if row.q_20k is not None]
        if len(usable) < 2:
            raise RuntimeError("persisted spectrum has fewer than two q20 rows")
        roots.append(usable)
    return records, roots


def _fit(roots, indices, seed=TRAINING_SEED):
    rows = [roots[i] for i in indices]
    features = np.vstack([row.features for root in rows for row in root])
    base = np.asarray([row.base_q for root in rows for row in root], dtype=float)
    target = np.asarray([row.q_20k for root in rows for row in root], dtype=float)
    groups = []
    cursor = 0
    for root in rows:
        groups.append(np.arange(cursor, cursor + len(root)))
        cursor += len(root)
    return f61._fit_serializable(features, base, target, groups, "POINTWISE_Q", seed)


def _oof(roots):
    predictions = [None] * len(roots)
    fold_rows = []
    for fold in range(FOLDS):
        held = list(range(fold * ROOTS_PER_FOLD, (fold + 1) * ROOTS_PER_FOLD))
        train = [i for i in range(len(roots)) if i not in held]
        model = _fit(roots, train)
        held_actions = 0
        for index in held:
            root = roots[index]
            features = np.vstack([row.features for row in root])
            predictions[index] = np.asarray(model.predict(features), dtype=float)
            held_actions += len(root)
        fold_rows.append({"fold": fold, "train_roots": len(train), "heldout_roots": len(held), "heldout_actions": held_actions})
    rows = []
    for index, root in enumerate(roots):
        base = np.asarray([row.base_q for row in root], dtype=float)
        target = np.asarray([row.q_20k for row in root], dtype=float)
        rows.append({"root_index": index, "base": base.tolist(), "target": target.tolist(), "oof_residual": predictions[index].tolist()})
    p = np.asarray([value for row in rows for value in row["oof_residual"]], dtype=float)
    residual = np.asarray([value for row in rows for value in (np.asarray(row["target"]) - np.asarray(row["base"]))], dtype=float)
    denominator = float(np.dot(p, p))
    beta = float(np.dot(p, residual) / denominator) if denominator else float("nan")
    for row in rows:
        row["base_q"] = row.pop("base")
        row["target"] = row["target"]
        row["shrunken"] = (np.asarray(row["base_q"]) + beta * np.asarray(row["oof_residual"])).tolist()
    base_metrics = _stats(rows, "base_q")
    shrunken_metrics = _stats(rows, "shrunken")
    gate = bool(np.isfinite(beta) and beta > 0.0 and shrunken_metrics["mse"] < base_metrics["mse"] and shrunken_metrics["pairwise_ranking_accuracy"] >= base_metrics["pairwise_ranking_accuracy"])
    return rows, {"beta": beta, "folds": fold_rows, "base": base_metrics, "shrunken": shrunken_metrics, "gate_pass": gate}


def _full_scaled_child(compiled, parent, roots, beta):
    features = np.vstack([row.features for root in roots for row in root])
    base = np.asarray([row.base_q for root in roots for row in root], dtype=float)
    target = np.asarray([row.q_20k for root in roots for row in root], dtype=float)
    groups = []
    cursor = 0
    for root in roots:
        groups.append(np.arange(cursor, cursor + len(root)))
        cursor += len(root)
    model = f61._fit_serializable(features, base, target, groups, "POINTWISE_Q", TRAINING_SEED)
    spec = {"candidate_id": "F61_D0_POINTWISE_Q_SEED_59013_OOF_SHRUNK", "training_distribution": "D0_RANDOM_REACHABLE", "objective": "POINTWISE_Q", "seed": TRAINING_SEED, "oof_beta": beta}
    original, payload = f61._candidate_checkpoint(parent, compiled, model, spec)
    residual = CompactNonlinearResidual.from_dict(original.compact_nonlinear)
    scaled = CompactNonlinearResidual(**{**residual.__dict__, "output_weights": tuple(beta * value for value in residual.output_weights), "output_bias": beta * residual.output_bias})
    child, scaled_payload = f61._candidate_checkpoint(parent, compiled, scaled, spec)
    expected = beta * residual.predict(features)
    actual = CompactNonlinearResidual.from_dict(scaled_payload).predict(features)
    error = float(np.max(np.abs(actual - expected)))
    return child, scaled_payload, {"original_checkpoint_id": original.checkpoint_id, "child_checkpoint_id": child.checkpoint_id, "model_sha256": f61.stable_sha256(scaled_payload), "max_prediction_scaling_error": error}


def _witness(compiled, native, parent, child, cached):
    rows = []
    openings = generate_arena_openings(compiled, count=4, seed=OPENING_SEED, min_plies=2, max_plies=6)
    for index, opening in enumerate(openings.openings):
        cached_row = cached["witness_rows"][index]
        record = {"action_history": [f59.action_to_dict(action) for action in opening.actions]}
        actions, searches = r20._action_set(compiled, native, parent, child, record)
        if [f59._action_key(action) for action in actions] != [f59._action_key(action) for action in cached_row["actions"]]:
            raise RuntimeError("R20 witness action-set identity changed")
        features = np.vstack([f59._child_features(compiled, native, parent, record, action)[0] for action in actions])
        base = np.asarray(cached_row["base_q"], dtype=float)
        target = np.asarray(cached_row["q20"], dtype=float)
        residual = CompactNonlinearResidual.from_dict(child.compact_nonlinear)
        learned = base + residual.predict(features)
        teacher = float(np.max(target))
        child_key = searches["child_2k"]["action_key"]
        child_index = next(i for i, action in enumerate(actions) if f59._action_key(action) == child_key)
        rows.append({"opening_id": opening.final_position_key, "base_q": base.tolist(), "learned_total_q": learned.tolist(), "q20": target.tolist(), "parent_2k": searches["parent_2k"], "child_2k": searches["child_2k"], "parent_2k_teacher_regret": float(teacher - target[next(i for i, action in enumerate(actions) if f59._action_key(action) == searches["parent_2k"]["action_key"])]), "child_2k_teacher_regret": float(teacher - target[child_index]), "learned_one_ply_teacher_regret": float(teacher - target[int(np.argmax(learned))])})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-arena", action="store_true")
    args = parser.parse_args()
    compiled, native, parent, _ = gen._context(RULESET)
    if parent.checkpoint_id != PARENT_ID:
        raise RuntimeError("unexpected parent checkpoint")
    records, roots = _load_roots(compiled, parent)
    oof_rows, oof = _oof(roots)
    payload = {"schema": "generic-chess-f61-pointwise-oof-shrinkage-v1", "ruleset": RULESET, "parent_checkpoint_id": parent.checkpoint_id, "training": {"training_seed": TRAINING_SEED, "training_roots": len(roots), "training_actions": sum(len(root) for root in roots), "persisted_d0_only": True}, "folds": oof["folds"], "oof": {key: value for key, value in oof.items() if key != "folds"}}
    if not oof["gate_pass"]:
        payload["decision"] = "STOP_BEFORE_CANDIDATE_OOF_GATE_FAILED"
    else:
        child, scaled_payload, identity = _full_scaled_child(compiled, parent, roots, oof["beta"])
        cached = json.loads((ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "pointwise_search_transfer_witness.json").read_text(encoding="utf-8"))
        witness = _witness(compiled, native, parent, child, cached)
        learned_mse = float(np.mean([(v - t) ** 2 for row in witness for v, t in zip(row["learned_total_q"], row["q20"])]))
        base_mse = float(np.mean([(v - t) ** 2 for row in witness for v, t in zip(row["base_q"], row["q20"])]))
        payload.update({"child": identity, "witness": {"rows": witness, "base_mse": base_mse, "learned_mse": learned_mse}, "decision": "STOP_BEFORE_ARENA"})
        if learned_mse < base_mse and args.run_arena:
            openings = generate_arena_openings(compiled, count=1, seed=ARENA_SEED, min_plies=2, max_plies=6)
            result = run_arena_game_resumable(compiled, native, parent, child, ArenaConfig(pairs=1, nodes_per_move=2_000, max_depth=12, tt_megabytes=8, opening_seed=ARENA_SEED, opening_count=1, min_plies=2, max_plies=6, workers=1), progress_dir=OUT.parent / "arena-progress-oof-shrinkage" / str(compiled.ruleset_fingerprint) / f"seed-{ARENA_SEED}", openings=openings, stop_on_decision=False)
            if result.status != "COMPLETE" or result.summary is None:
                raise RuntimeError(f"Arena incomplete: {result.status} {result.reason}")
            payload["fresh_arena"] = {"opening_seed": ARENA_SEED, "pair_scores": list(result.summary.pair_scores), "mean_pair_score": result.summary.mean_pair_score, "game_wins": result.summary.game_wins, "game_draws": result.summary.game_draws, "game_losses": result.summary.game_losses}
            payload["decision"] = "ARENA_SCREEN_COMPLETE"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
