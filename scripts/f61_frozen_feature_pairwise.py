"""R26 deterministic frozen-feature pairwise residual screen."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import ArenaConfig, run_arena_game_resumable  # noqa: E402
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from scripts import f50_generic_learnable_evaluator as f50  # noqa: E402
from scripts import f54_direct_capacity_and_gradient_geometry_diagnosis as f54  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_gen0_gen1_strength_triage as gen  # noqa: E402
from scripts import f61_strength_first_triage as f61  # noqa: E402


RULESET = "B_CANONICAL_STANDARD_SHOGI"
PARENT_ID = "2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362"
SEED = 59013
WIDTH = 32
REGULARIZATION = 1e-3
STEPS = 600
LR = 0.01
OPENING_SEED = 620700
ARENA_SEED = 620710
OUT = ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "frozen_feature_pairwise.json"


def _arrays(roots, indices):
    selected = [roots[index] for index in indices]
    x = np.vstack([row.features for root in selected for row in root])
    base = np.asarray([row.base_q for root in selected for row in root], dtype=float)
    target = np.asarray([row.q_20k for root in selected for row in root], dtype=float)
    groups = []
    cursor = 0
    for root in selected:
        groups.append(np.arange(cursor, cursor + len(root)))
        cursor += len(root)
    return x, base, target, groups


def _model(features, base, target, groups):
    x = np.asarray(features, dtype=float)
    mean = np.mean(x, axis=0)
    scale = np.where(np.std(x, axis=0) > 1e-9, np.std(x, axis=0), 1.0)
    target_scale = float(np.std(np.asarray(target) - np.asarray(base))) or 1.0
    rng = np.random.default_rng(SEED)
    hidden_weights = rng.normal(0.0, np.sqrt(2.0 / (x.shape[1] + WIDTH)), size=(WIDTH, x.shape[1]))
    hidden_bias = np.zeros(WIDTH)
    hidden = np.tanh(((x - mean) / scale) @ hidden_weights.T + hidden_bias)
    output_weights = np.zeros(WIDTH, dtype=float)
    first = np.zeros_like(output_weights)
    second = np.zeros_like(output_weights)
    targets = np.asarray(target, dtype=float)
    base = np.asarray(base, dtype=float)
    for step in range(1, STEPS + 1):
        prediction = hidden @ output_weights
        grad_prediction = np.zeros(len(x), dtype=float)
        pair_count = 0
        total_prediction = base + prediction * target_scale
        for indices in groups:
            for left in range(len(indices)):
                for right in range(left + 1, len(indices)):
                    i, j = indices[left], indices[right]
                    delta = (targets[i] - targets[j]) / target_scale
                    if abs(delta) < 1e-9:
                        continue
                    sign = 1.0 if delta > 0 else -1.0
                    margin = sign * (total_prediction[i] - total_prediction[j]) / target_scale
                    derivative = -sign / (1.0 + math.exp(min(60.0, max(-60.0, margin))))
                    grad_prediction[i] += derivative
                    grad_prediction[j] -= derivative
                    pair_count += 1
        grad_prediction /= max(pair_count, 1)
        gradient = hidden.T @ grad_prediction + REGULARIZATION * output_weights
        first = 0.9 * first + 0.1 * gradient
        second = 0.999 * second + 0.001 * gradient * gradient
        output_weights -= LR * (first / (1.0 - 0.9 ** step)) / (np.sqrt(second / (1.0 - 0.999 ** step)) + 1e-8)
    return CompactNonlinearResidual(input_mean=tuple(mean.tolist()), input_scale=tuple(scale.tolist()), target_scale=target_scale, hidden_weights=tuple(tuple(row) for row in hidden_weights.tolist()), hidden_bias=tuple(hidden_bias.tolist()), output_weights=tuple(output_weights.tolist()), output_bias=0.0, width=WIDTH, regularization=REGULARIZATION, seed=SEED)


def _zero_model(features, base, target):
    x = np.asarray(features, dtype=float)
    mean = np.mean(x, axis=0)
    scale = np.where(np.std(x, axis=0) > 1e-9, np.std(x, axis=0), 1.0)
    rng = np.random.default_rng(SEED)
    hidden_weights = rng.normal(0.0, np.sqrt(2.0 / (x.shape[1] + WIDTH)), size=(WIDTH, x.shape[1]))
    model = CompactNonlinearResidual(input_mean=tuple(mean.tolist()), input_scale=tuple(scale.tolist()), target_scale=float(np.std(np.asarray(target) - np.asarray(base))) or 1.0, hidden_weights=tuple(tuple(row) for row in hidden_weights.tolist()), hidden_bias=tuple(np.zeros(WIDTH).tolist()), output_weights=tuple(np.zeros(WIDTH).tolist()), output_bias=0.0, width=WIDTH, regularization=REGULARIZATION, seed=SEED)
    if not np.array_equal(model.predict(x), np.zeros(len(x), dtype=float)):
        raise RuntimeError("initial frozen-feature model is not exactly zero")
    if not np.all(np.isfinite(model.predict(x))):
        raise RuntimeError("initial frozen-feature model is non-finite")
    return model


def _metrics(rows, key):
    errors = []
    correct = total = top1 = 0
    regrets = []
    for row in rows:
        target = np.asarray(row["target"], dtype=float)
        prediction = np.asarray(row[key], dtype=float)
        errors.extend((prediction - target).tolist())
        teacher_best = int(np.argmax(target))
        top1 += int(np.argmax(prediction) == teacher_best)
        regrets.append(float(np.max(target) - target[int(np.argmax(prediction))]))
        for i in range(len(target)):
            for j in range(i + 1, len(target)):
                sign = np.sign(target[i] - target[j])
                if sign == 0:
                    continue
                total += 1
                correct += int(sign == np.sign(prediction[i] - prediction[j]))
    return {"mse": float(np.mean(np.square(errors))), "pairwise_ranking_accuracy": correct / total if total else 0.0, "comparable_pairs": total, "mean_root_top_action_q20_regret": float(np.mean(regrets)), "top1_agreement": top1 / len(rows) if rows else 0.0, "root_regrets": regrets}


def _load(compiled, parent):
    records = gen._d0_records(compiled, 620000, count=24, smoke=False)
    roots = []
    for record in records:
        spectrum = gen._load_root_checkpoint(compiled, parent, record, smoke=False)
        if spectrum is None:
            raise RuntimeError(f"missing persisted D0 spectrum for {record['position_key']}")
        roots.append([row for row in spectrum if row.q_20k is not None])
    return records, roots


def _oof(roots):
    rows = []
    folds = []
    for fold in range(4):
        held = list(range(fold * 6, (fold + 1) * 6))
        train = [index for index in range(24) if index not in held]
        x, base, target, groups = _arrays(roots, train)
        _zero_model(x, base, target)
        model = _model(x, base, target, groups)
        for index in held:
            hx, hbase, htarget, _ = _arrays(roots, [index])
            prediction = hbase + model.predict(hx)
            rows.append({"root_index": index, "target": htarget.tolist(), "base_q": hbase.tolist(), "frozen_pairwise_total_q": prediction.tolist()})
        folds.append({"fold": fold, "train_roots": len(train), "heldout_roots": len(held), "heldout_actions": sum(len(roots[index]) for index in held)})
    rows.sort(key=lambda row: row["root_index"])
    return rows, folds


def _nontrivial_witness(compiled, native, parent, child):
    openings = generate_arena_openings(compiled, count=4, seed=OPENING_SEED, min_plies=2, max_plies=6)
    rows = []
    for opening in openings.openings:
        record = {"action_history": [f59.action_to_dict(action) for action in opening.actions]}
        parent_result = f59._root_search(compiled, native, parent, record, 2_000)
        child_result = f59._root_search(compiled, native, child, record, 2_000)
        rows.append({"opening_id": opening.final_position_key, "parent_action_key": parent_result["action_key"], "child_action_key": child_result["action_key"], "changed": parent_result["action_key"] != child_result["action_key"]})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-arena", action="store_true")
    args = parser.parse_args()
    compiled, native, _profile = f50._ruleset(RULESET)
    parent = f54._parent(RULESET)
    if parent.checkpoint_id != PARENT_ID:
        raise RuntimeError("unexpected parent checkpoint")
    records, roots = _load(compiled, parent)
    oof_rows, folds = _oof(roots)
    base_rows = [{"target": row["target"], "base_q": row["base_q"]} for row in oof_rows]
    pairwise_rows = [{"target": row["target"], "frozen_pairwise_total_q": row["frozen_pairwise_total_q"]} for row in oof_rows]
    base_metrics = _metrics(base_rows, "base_q")
    pairwise_metrics = _metrics(pairwise_rows, "frozen_pairwise_total_q")
    gate = pairwise_metrics["pairwise_ranking_accuracy"] >= base_metrics["pairwise_ranking_accuracy"] and pairwise_metrics["mean_root_top_action_q20_regret"] <= base_metrics["mean_root_top_action_q20_regret"] and (pairwise_metrics["pairwise_ranking_accuracy"] > base_metrics["pairwise_ranking_accuracy"] or pairwise_metrics["mean_root_top_action_q20_regret"] < base_metrics["mean_root_top_action_q20_regret"])
    payload = {"schema": "generic-chess-f61-frozen-feature-pairwise-v1", "ruleset": RULESET, "parent_checkpoint_id": parent.checkpoint_id, "training": {"seed": SEED, "roots": 24, "actions": sum(len(root) for root in roots), "width": WIDTH, "hidden_frozen": True, "output_only": True, "objective": "PAIRWISE_RANKING", "steps": STEPS, "learning_rate": LR, "regularization": REGULARIZATION, "persisted_d0_only": True}, "folds": folds, "oof": {"base": base_metrics, "frozen_pairwise": pairwise_metrics, "gate_pass": gate}}
    if not gate:
        payload["decision"] = "STOP_BEFORE_FULL_CANDIDATE_OOF_GATE_FAILED"
    else:
        x, base, target, groups = _arrays(roots, list(range(24)))
        _zero_model(x, base, target)
        model = _model(x, base, target, groups)
        spec = {"candidate_id": "F61_D0_FROZEN_FEATURE_PAIRWISE_SEED_59013", "training_distribution": "D0_RANDOM_REACHABLE", "objective": "PAIRWISE_RANKING", "seed": SEED, "hidden_frozen": True, "output_only": True}
        child, model_payload = f61._candidate_checkpoint(parent, compiled, model, spec)
        payload["candidate"] = {"checkpoint_id": child.checkpoint_id, "model_sha256": f61.stable_sha256(model_payload), "finite_training_predictions": bool(np.all(np.isfinite(model.predict(x))))}
        witness = _nontrivial_witness(compiled, native, parent, child)
        payload["witness_2k"] = {"seed": OPENING_SEED, "rows": witness, "nontrivial": any(row["changed"] for row in witness)}
        payload["decision"] = "STOP_AFTER_TRIVIAL_WITNESS" if not any(row["changed"] for row in witness) else "READY_FOR_ARENA"
        if any(row["changed"] for row in witness) and args.run_arena:
            openings = generate_arena_openings(compiled, count=1, seed=ARENA_SEED, min_plies=2, max_plies=6)
            result = run_arena_game_resumable(compiled, native, parent, child, ArenaConfig(pairs=1, nodes_per_move=2_000, max_depth=12, tt_megabytes=8, opening_seed=ARENA_SEED, opening_count=1, min_plies=2, max_plies=6, workers=1), progress_dir=OUT.parent / "arena-progress-frozen-feature-pairwise" / str(compiled.ruleset_fingerprint) / f"seed-{ARENA_SEED}", openings=openings, stop_on_decision=False)
            if result.status != "COMPLETE" or result.summary is None:
                raise RuntimeError(f"Arena incomplete: {result.status} {result.reason}")
            payload["fresh_arena"] = {"opening_seed": ARENA_SEED, "pair_scores": list(result.summary.pair_scores), "mean_pair_score": result.summary.mean_pair_score, "game_wins": result.summary.game_wins, "game_draws": result.summary.game_draws, "game_losses": result.summary.game_losses}
            payload["decision"] = "ARENA_SCREEN_COMPLETE"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=lambda value: value.item() if isinstance(value, np.generic) else str(value)) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=lambda value: value.item() if isinstance(value, np.generic) else str(value)))


if __name__ == "__main__":
    main()
