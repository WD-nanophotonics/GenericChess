"""R25 q10/q20 stability filter followed by bounded linear distillation."""

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
from scripts import f61_linear_search_distillation as r24  # noqa: E402
from scripts import f61_strength_first_triage as f61  # noqa: E402


RULESET = "B_CANONICAL_STANDARD_SHOGI"
PARENT_ID = "2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362"
ROOT_SEED = 620000
Q10_NODES = 10_000
WITNESS_SEED = 620700
ARENA_SEED = 620710
OUT = ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "stable_target_linear_distillation.json"


def _trusted_roots(compiled, native, parent, records, roots):
    trusted = []
    details = []
    for index, (record, root) in enumerate(zip(records, roots)):
        actions = [row["action"] for row in root]
        q10 = np.asarray(f59._parallel_children(compiled, native, parent, record, actions, Q10_NODES), dtype=float)
        q20 = np.asarray([row["q20"] for row in root], dtype=float)
        stable = int(np.argmax(q10)) == int(np.argmax(q20))
        mate_actions = [int(f59._is_mate_band_q(value, parent.semantic_native_scale)) for value in q20]
        mate_excluded = any(mate_actions)
        details.append({"root_index": index, "position_key": record["position_key"], "action_count": len(root), "q10_top_action_key": root[int(np.argmax(q10))]["action_key"], "q20_top_action_key": root[int(np.argmax(q20))]["action_key"], "stable_q10_q20": stable, "q20_mate_band_action_count": int(sum(mate_actions)), "q10": q10.tolist()})
        if stable and not mate_excluded:
            trusted.append(index)
    return trusted, details


def _oof(roots, trusted):
    base_roots = [roots[index] for index in trusted]
    predictions = []
    held_roots = []
    deltas = []
    for local_held, global_index in enumerate(trusted):
        train_global = [index for index in trusted if index != global_index]
        delta, held_prediction = r24._fit_predict(roots, train_global, [global_index])
        deltas.append(delta)
        predictions.append(held_prediction[0])
        held_roots.append(global_index)
    base_deltas = [np.zeros(len(root), dtype=float) for root in base_roots]
    return r24._metrics(base_roots, base_deltas), r24._metrics(base_roots, predictions), [{"heldout_root": index, "train_roots": len(trusted) - 1, "delta_norm": float(np.linalg.norm(delta))} for index, delta in zip(held_roots, deltas)]


def _witness(compiled, native, parent, child, cached):
    effective = r24._effective_delta(parent, child)
    openings = generate_arena_openings(compiled, count=4, seed=WITNESS_SEED, min_plies=2, max_plies=6)
    rows = []
    for opening, cached_row in zip(openings.openings, cached["witness_rows"]):
        record = {"action_history": [f59.action_to_dict(action) for action in opening.actions]}
        vectors = np.vstack([r24._successor_feature(compiled, native, parent, record, action)[0] for action in cached_row["actions"]])
        base = np.asarray(cached_row["base_q"], dtype=float)
        target = np.asarray(cached_row["q20"], dtype=float)
        rows.append({"opening_id": opening.final_position_key, "base_q": base.tolist(), "linear_total_q": (base + vectors @ effective).tolist(), "q20": target.tolist()})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-arena", action="store_true")
    args = parser.parse_args()
    compiled, native, _profile = f50._ruleset(RULESET)
    parent = f54._parent(RULESET)
    if parent.checkpoint_id != PARENT_ID:
        raise RuntimeError("unexpected parent checkpoint")
    records, roots, action_count = r24._load_roots(compiled, native, parent)
    trusted, stability = _trusted_roots(compiled, native, parent, records, roots)
    retained = [roots[index] for index in trusted]
    payload = {"schema": "generic-chess-f61-stable-target-linear-distillation-v1", "ruleset": RULESET, "parent_checkpoint_id": parent.checkpoint_id, "source": {"root_seed": ROOT_SEED, "roots": len(roots), "actions": action_count, "q10_nodes": Q10_NODES, "stable_root_count": sum(item["stable_q10_q20"] for item in stability), "q10_q20_top_action_agreement_rate": float(np.mean([item["stable_q10_q20"] for item in stability])), "retained_q20_mate_band_exclusions": int(sum(item["q20_mate_band_action_count"] > 0 for item in stability)), "retained_root_count": len(trusted), "retained_action_count": int(sum(len(root) for root in retained)), "stability": stability}}
    if len(trusted) < 2:
        payload["decision"] = "STOP_BEFORE_OOF_INSUFFICIENT_TRUSTED_ROOTS"
    else:
        base_metrics, oof_metrics, folds = _oof(roots, trusted)
        gate = oof_metrics["mse"] < base_metrics["mse"] and oof_metrics["pairwise_ranking_accuracy"] >= base_metrics["pairwise_ranking_accuracy"] and oof_metrics["mean_root_top_action_q20_regret"] <= base_metrics["mean_root_top_action_q20_regret"]
        payload["oof"] = {"folds": folds, "base": base_metrics, "linear_delta": oof_metrics, "gate_pass": gate}
        if not gate:
            payload["decision"] = "STOP_BEFORE_FULL_CANDIDATE_OOF_GATE_FAILED"
        else:
            features = np.vstack([row["vector"] for root in retained for row in root])
            residual = np.asarray([row["q20"] - row["base_q"] for root in retained for row in root], dtype=float)
            delta = r24._ridge_fit(features, residual)
            child = r24._child_from_delta(parent, delta)
            payload["candidate"] = {"checkpoint_id": child.checkpoint_id, "effective_delta_sha256": f61.stable_sha256(r24._effective_delta(parent, child).tolist()), "raw_delta_norm": float(np.linalg.norm(delta))}
            cached = json.loads((OUT.parent / "pointwise_search_transfer_witness.json").read_text(encoding="utf-8"))
            witness_rows = _witness(compiled, native, parent, child, cached)
            base_witness = r24._pair_metrics(witness_rows, "base_q")
            linear_witness = r24._pair_metrics(witness_rows, "linear_total_q")
            witness_gate = linear_witness["mse"] < base_witness["mse"] and linear_witness["pairwise_ranking_accuracy"] >= base_witness["pairwise_ranking_accuracy"] and linear_witness["mean_root_top_action_q20_regret"] <= base_witness["mean_root_top_action_q20_regret"]
            payload["external_witness"] = {"seed": WITNESS_SEED, "base": base_witness, "linear_delta": linear_witness, "gate_pass": witness_gate, "rows": witness_rows}
            payload["decision"] = "STOP_BEFORE_ARENA" if not witness_gate else "READY_FOR_ARENA"
            if witness_gate and args.run_arena:
                openings = generate_arena_openings(compiled, count=1, seed=ARENA_SEED, min_plies=2, max_plies=6)
                result = run_arena_game_resumable(compiled, native, parent, child, ArenaConfig(pairs=1, nodes_per_move=2_000, max_depth=12, tt_megabytes=8, opening_seed=ARENA_SEED, opening_count=1, min_plies=2, max_plies=6, workers=1), progress_dir=OUT.parent / "arena-progress-stable-target-linear" / str(compiled.ruleset_fingerprint) / f"seed-{ARENA_SEED}", openings=openings, stop_on_decision=False)
                if result.status != "COMPLETE" or result.summary is None:
                    raise RuntimeError(f"Arena incomplete: {result.status} {result.reason}")
                payload["fresh_arena"] = {"opening_seed": ARENA_SEED, "pair_scores": list(result.summary.pair_scores), "mean_pair_score": result.summary.mean_pair_score, "game_wins": result.summary.game_wins, "game_draws": result.summary.game_draws, "game_losses": result.summary.game_losses}
                payload["decision"] = "ARENA_SCREEN_COMPLETE"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=lambda value: value.item() if isinstance(value, np.generic) else str(value)) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=lambda value: value.item() if isinstance(value, np.generic) else str(value)))


if __name__ == "__main__":
    main()
