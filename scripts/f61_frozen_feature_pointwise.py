"""R22 frozen-hidden-feature POINTWISE_Q capacity screen."""

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
SEED = 59013
WIDTH = 32
REGULARIZATION = 1e-3
OPENING_SEED = 620700
ARENA_SEED = 620710
OUT = ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "frozen_feature_pointwise.json"


def _load(compiled, parent):
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


def _arrays(roots, indices):
    selected = [roots[i] for i in indices]
    x = np.vstack([row.features for root in selected for row in root])
    base = np.asarray([row.base_q for root in selected for row in root], dtype=float)
    target = np.asarray([row.q_20k for root in selected for row in root], dtype=float)
    return x, base, target


def _frozen_model(features, base, target):
    x = np.asarray(features, dtype=float)
    residual = np.asarray(target, dtype=float) - np.asarray(base, dtype=float)
    mean = np.mean(x, axis=0)
    scale = np.where(np.std(x, axis=0) > 1e-9, np.std(x, axis=0), 1.0)
    target_scale = float(np.std(residual)) or 1.0
    rng = np.random.default_rng(SEED)
    hidden_weights = rng.normal(0.0, np.sqrt(2.0 / (x.shape[1] + WIDTH)), size=(WIDTH, x.shape[1]))
    hidden_bias = np.zeros(WIDTH)
    hidden = np.tanh(((x - mean) / scale) @ hidden_weights.T + hidden_bias)
    design = np.concatenate((hidden, np.ones((len(hidden), 1))), axis=1)
    normalized_target = residual / target_scale
    regularizer = np.diag(np.concatenate((np.full(WIDTH, REGULARIZATION), np.zeros(1))))
    gram = (design.T @ design) / len(design) + regularizer
    rhs = (design.T @ normalized_target) / len(design)
    solution = np.linalg.solve(gram, rhs)
    return CompactNonlinearResidual(
        input_mean=tuple(mean.tolist()), input_scale=tuple(scale.tolist()), target_scale=target_scale,
        hidden_weights=tuple(tuple(row) for row in hidden_weights.tolist()), hidden_bias=tuple(hidden_bias.tolist()),
        output_weights=tuple(solution[:-1].tolist()), output_bias=float(solution[-1]), width=WIDTH,
        regularization=REGULARIZATION, seed=SEED,
    )


def _metrics(rows, key):
    errors = []
    correct = total = 0
    regrets = []
    for row in rows:
        target = np.asarray(row["target"], dtype=float)
        prediction = np.asarray(row[key], dtype=float)
        errors.extend((prediction - target).tolist())
        for i in range(len(target)):
            for j in range(i + 1, len(target)):
                sign = np.sign(target[i] - target[j])
                if sign == 0:
                    continue
                total += 1
                correct += int(sign == np.sign(prediction[i] - prediction[j]))
        regrets.append(float(np.max(target) - target[int(np.argmax(prediction))]))
    return {"mse": float(np.mean(np.square(errors))), "pairwise_ranking_accuracy": correct / total if total else 0.0, "comparable_pairs": total, "mean_root_top_action_teacher_regret": float(np.mean(regrets)), "root_top_action_teacher_regret": regrets}


def _oof(roots):
    rows = []
    fold_rows = []
    for fold in range(4):
        held = list(range(fold * 6, (fold + 1) * 6))
        train = [i for i in range(len(roots)) if i not in held]
        x, base, target = _arrays(roots, train)
        model = _frozen_model(x, base, target)
        for index in held:
            hx, hbase, htarget = _arrays(roots, [index])
            rows.append({"root_index": index, "base": hbase.tolist(), "target": htarget.tolist(), "prediction": (hbase + model.predict(hx)).tolist()})
        fold_rows.append({"fold": fold, "train_roots": len(train), "heldout_roots": len(held), "heldout_actions": sum(len(roots[i]) for i in held)})
    rows.sort(key=lambda row: row["root_index"])
    for row in rows:
        row["base_q"] = row.pop("base")
        row["frozen_total_q"] = row.pop("prediction")
    return rows, fold_rows


def _external(compiled, native, parent, child, cached):
    rows = []
    openings = generate_arena_openings(compiled, count=4, seed=OPENING_SEED, min_plies=2, max_plies=6)
    for index, opening in enumerate(openings.openings):
        cached_row = cached["witness_rows"][index]
        record = {"action_history": [f59.action_to_dict(action) for action in opening.actions]}
        actions, _searches = r20._action_set(compiled, native, parent, child, record)
        if [f59._action_key(a) for a in actions] != [f59._action_key(a) for a in cached_row["actions"]]:
            raise RuntimeError("external witness action-set identity changed")
        features = np.vstack([f59._child_features(compiled, native, parent, record, action)[0] for action in actions])
        base = np.asarray(cached_row["base_q"], dtype=float)
        target = np.asarray(cached_row["q20"], dtype=float)
        learned = base + CompactNonlinearResidual.from_dict(child.compact_nonlinear).predict(features)
        rows.append({"root_index": index, "base_q": base.tolist(), "target": target.tolist(), "frozen_total_q": learned.tolist()})
    return {"base": _metrics(rows, "base_q"), "frozen": _metrics(rows, "frozen_total_q"), "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-arena", action="store_true")
    args = parser.parse_args()
    compiled, native, parent, _ = gen._context(RULESET)
    if parent.checkpoint_id != PARENT_ID:
        raise RuntimeError("unexpected parent checkpoint")
    records, roots = _load(compiled, parent)
    oof_rows, folds = _oof(roots)
    base_rows = [{"target": row["target"], "base_q": row["base_q"]} for row in oof_rows]
    frozen_rows = [{"target": row["target"], "frozen_total_q": row["frozen_total_q"]} for row in oof_rows]
    base_metrics = _metrics(base_rows, "base_q")
    frozen_metrics = _metrics(frozen_rows, "frozen_total_q")
    oof_gate = frozen_metrics["mse"] < base_metrics["mse"] and frozen_metrics["pairwise_ranking_accuracy"] >= base_metrics["pairwise_ranking_accuracy"] and frozen_metrics["mean_root_top_action_teacher_regret"] <= base_metrics["mean_root_top_action_teacher_regret"]
    payload = {"schema": "generic-chess-f61-frozen-feature-pointwise-v1", "ruleset": RULESET, "parent_checkpoint_id": parent.checkpoint_id, "training": {"training_seed": SEED, "training_roots": len(roots), "training_actions": sum(len(root) for root in roots), "width": WIDTH, "regularization": REGULARIZATION, "hidden_frozen": True, "persisted_d0_only": True}, "folds": folds, "oof": {"base": base_metrics, "frozen": frozen_metrics, "gate_pass": oof_gate}}
    if not oof_gate:
        payload["decision"] = "STOP_BEFORE_FULL_CANDIDATE_OOF_GATE_FAILED"
    else:
        x, base, target = _arrays(roots, list(range(len(roots))))
        model = _frozen_model(x, base, target)
        spec = {"candidate_id": "F61_D0_POINTWISE_Q_SEED_59013_FROZEN_FEATURE", "training_distribution": "D0_RANDOM_REACHABLE", "objective": "POINTWISE_Q", "seed": SEED, "hidden_frozen": True}
        child, model_payload = f61._candidate_checkpoint(parent, compiled, model, spec)
        cached = json.loads((ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "pointwise_search_transfer_witness.json").read_text(encoding="utf-8"))
        external = _external(compiled, native, parent, child, cached)
        external_gate = external["frozen"]["mse"] < external["base"]["mse"] and external["frozen"]["pairwise_ranking_accuracy"] >= external["base"]["pairwise_ranking_accuracy"] and external["frozen"]["mean_root_top_action_teacher_regret"] <= external["base"]["mean_root_top_action_teacher_regret"]
        payload.update({"child_checkpoint_id": child.checkpoint_id, "model_sha256": f61.stable_sha256(model_payload), "external": {**external, "gate_pass": external_gate}, "decision": "STOP_BEFORE_ARENA" if not external_gate else "READY_FOR_ARENA"})
        if external_gate and args.run_arena:
            openings = generate_arena_openings(compiled, count=1, seed=ARENA_SEED, min_plies=2, max_plies=6)
            result = run_arena_game_resumable(compiled, native, parent, child, ArenaConfig(pairs=1, nodes_per_move=2_000, max_depth=12, tt_megabytes=8, opening_seed=ARENA_SEED, opening_count=1, min_plies=2, max_plies=6, workers=1), progress_dir=OUT.parent / "arena-progress-frozen-feature" / str(compiled.ruleset_fingerprint) / f"seed-{ARENA_SEED}", openings=openings, stop_on_decision=False)
            if result.status != "COMPLETE" or result.summary is None:
                raise RuntimeError(f"Arena incomplete: {result.status} {result.reason}")
            payload["fresh_arena"] = {"opening_seed": ARENA_SEED, "pair_scores": list(result.summary.pair_scores), "mean_pair_score": result.summary.mean_pair_score, "game_wins": result.summary.game_wins, "game_draws": result.summary.game_draws, "game_losses": result.summary.game_losses}
            payload["decision"] = "ARENA_SCREEN_COMPLETE"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
