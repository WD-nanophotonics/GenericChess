"""R23 trusted F60-style D0 POINTWISE_Q candidate and gated Arena screen."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import ArenaConfig, run_arena_game_resumable  # noqa: E402
from generic_chess.learning.diagnostics import generate_diagnostic_corpus  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from scripts import f50_generic_learnable_evaluator as f50  # noqa: E402
from scripts import f54_direct_capacity_and_gradient_geometry_diagnosis as f54  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f60_disjoint_policy_objective_validation as f60  # noqa: E402
from scripts import f61_strength_first_triage as f61  # noqa: E402


RULESET = "B_CANONICAL_STANDARD_SHOGI"
PARENT_ID = "2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362"
SEED = 59013
ROOT_COUNT = 96
FIT_COUNT = 48
DEV_COUNT = 24
FINAL_COUNT = 24
OPENING_SEED = 620710
OUT = ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "trusted_d0_pointwise.json"


def _d0_sources(compiled):
    seed = f59.SEEDS[RULESET] + 600
    openings = generate_arena_openings(compiled, count=ROOT_COUNT * 2, seed=seed, min_plies=2, max_plies=6)
    corpus = generate_diagnostic_corpus(compiled, openings, count=ROOT_COUNT * 2, seed=seed + 1, min_plies=8, max_plies=40)
    records = []
    for position in corpus.positions:
        row = f59._record_dict(position)
        row["source_group"] = f"D0_OPENING_{position.index}"
        records.append(row)
    parts = f60._partition_by_source_group(records, (FIT_COUNT, DEV_COUNT, FINAL_COUNT))
    flattened = f60._flatten_split_parts(parts)
    if len(flattened) != ROOT_COUNT:
        raise RuntimeError(f"D0 source split produced {len(flattened)} roots, expected {ROOT_COUNT}")
    return compiled, flattened, {"source_sha256": f61.stable_sha256(corpus.to_dict()), "source_seed": seed, "pool_size": len(records), "split_counts": [len(part) for part in parts]}


def _spectra(records):
    workers = 1
    with ProcessPoolExecutor(max_workers=workers, initializer=f59._init_root_worker, initargs=(RULESET, False)) as pool:
        return list(pool.map(f59._spectrum_root_worker, records))


def _summary(records, computed):
    metadata = []
    roots = []
    for index, (rows, meta) in enumerate(computed):
        roots.append(rows)
        metadata.append({"index": index, "position_key": records[index]["position_key"], "root": meta})
    stable = [meta["root"]["spectrum_top_10k_action_key"] == meta["root"]["spectrum_top_20k_action_key"] for meta in metadata]
    ordinary = [index for index, value in enumerate(stable) if value and f59._ordinary_usable(metadata[index]["root"])]
    split_indices = {split: [index for index in ordinary if records[index].get("source_split") == split] for split in ("fit", "development", "final_holdout")}
    return {"roots": roots, "metadata": metadata, "stable_count": sum(stable), "ordinary_count": len(ordinary), "split_indices": split_indices, "stable_rate": sum(stable) / len(records), "root_40k_vs_80k_agreement": float(np.mean([meta["root"]["root_40k"]["action_key"] == meta["root"]["root_80k"]["action_key"] for meta in metadata]))}


def _fit(summary, indices, parent, compiled):
    roots = [summary["roots"][index] for index in indices]
    features = np.vstack([row.features for root in roots for row in root])
    base = np.asarray([row.base_q for root in roots for row in root], dtype=float)
    target = np.asarray([row.q_20k for root in roots for row in root], dtype=float)
    groups = []
    cursor = 0
    for root in roots:
        groups.append(np.arange(cursor, cursor + len(root)))
        cursor += len(root)
    model = f61._fit_serializable(features, base, target, groups, "POINTWISE_Q", SEED)
    return model, {"roots": roots, "features": features, "base": base, "target": target, "actions": int(len(features))}


def _metrics(roots, model):
    predictions = [f59._predict_total_q(root, model) for root in roots]
    return f59._metrics(roots, predictions), predictions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-arena", action="store_true")
    args = parser.parse_args()
    compiled, native, _profile = f50._ruleset(RULESET)
    parent = f54._parent(RULESET)
    if parent.checkpoint_id != PARENT_ID:
        raise RuntimeError("unexpected parent checkpoint")
    _compiled, records, provenance = _d0_sources(compiled)
    computed = _spectra(records)
    summary = _summary(records, computed)
    model, fit_data = _fit(summary, summary["split_indices"]["fit"], parent, compiled)
    dev_roots = [summary["roots"][index] for index in summary["split_indices"]["development"]]
    final_roots = [summary["roots"][index] for index in summary["split_indices"]["final_holdout"]]
    dev_metrics, _ = _metrics(dev_roots, model)
    final_metrics, _ = _metrics(final_roots, model)
    base_dev_metrics = f59._metrics(dev_roots, [np.asarray([row.base_q for row in root], dtype=float) for root in dev_roots])
    base_final_metrics = f59._metrics(final_roots, [np.asarray([row.base_q for row in root], dtype=float) for root in final_roots])
    dev_gate = dev_metrics["mse_secondary"] < base_dev_metrics["mse_secondary"] and dev_metrics["ranking_accuracy"] >= base_dev_metrics["ranking_accuracy"] and dev_metrics["teacher_regret_mean"] <= base_dev_metrics["teacher_regret_mean"]
    final_gate = False
    payload = {"schema": "generic-chess-f61-trusted-d0-pointwise-v1", "ruleset": RULESET, "parent_checkpoint_id": parent.checkpoint_id, "provenance": provenance, "retained": {"fit": {"roots": len(summary["split_indices"]["fit"]), "actions": int(sum(len(summary["roots"][i]) for i in summary["split_indices"]["fit"]))}, "development": {"roots": len(summary["split_indices"]["development"]), "actions": int(sum(len(summary["roots"][i]) for i in summary["split_indices"]["development"]))}, "final_holdout": {"roots": len(summary["split_indices"]["final_holdout"]), "actions": int(sum(len(summary["roots"][i]) for i in summary["split_indices"]["final_holdout"]))}}, "spectrum": {"source_roots": ROOT_COUNT, "stable_count": summary["stable_count"], "ordinary_count": summary["ordinary_count"], "stable_rate": summary["stable_rate"], "root_40k_vs_80k_agreement": summary["root_40k_vs_80k_agreement"]}, "training": {"seed": SEED, "objective": "POINTWISE_Q", "width": 32, "regularization": 1e-3, "steps": 600, "actions": fit_data["actions"]}, "development": {"base": base_dev_metrics, "candidate": dev_metrics, "gate_pass": dev_gate}, "final_holdout": {"base": base_final_metrics}, "decision": "STOP_BEFORE_FINAL" if not dev_gate else "PENDING_FINAL"}
    if dev_gate:
        final_gate = final_metrics["mse_secondary"] < base_final_metrics["mse_secondary"] and final_metrics["ranking_accuracy"] >= base_final_metrics["ranking_accuracy"] and final_metrics["teacher_regret_mean"] <= base_final_metrics["teacher_regret_mean"]
        payload["final_holdout"]["candidate"] = final_metrics
        payload["final_holdout"]["gate_pass"] = final_gate
        payload["decision"] = "STOP_BEFORE_ARENA" if not final_gate else "READY_FOR_ARENA"
    if dev_gate and final_gate:
        spec = {"candidate_id": "F61_TRUSTED_D0_POINTWISE_Q_SEED_59013", "training_distribution": "D0_RANDOM_REACHABLE", "objective": "POINTWISE_Q", "seed": SEED}
        child, model_payload = f61._candidate_checkpoint(parent, compiled, model, spec)
        payload["candidate"] = {"checkpoint_id": child.checkpoint_id, "model_sha256": f61.stable_sha256(model_payload)}
        if args.run_arena:
            openings = generate_arena_openings(compiled, count=1, seed=OPENING_SEED, min_plies=2, max_plies=6)
            result = run_arena_game_resumable(compiled, native, parent, child, ArenaConfig(pairs=1, nodes_per_move=2_000, max_depth=12, tt_megabytes=8, opening_seed=OPENING_SEED, opening_count=1, min_plies=2, max_plies=6, workers=1), progress_dir=OUT.parent / "arena-progress-trusted-d0" / str(compiled.ruleset_fingerprint) / f"seed-{OPENING_SEED}", openings=openings, stop_on_decision=False)
            if result.status != "COMPLETE" or result.summary is None:
                raise RuntimeError(f"Arena incomplete: {result.status} {result.reason}")
            payload["fresh_arena"] = {"opening_seed": OPENING_SEED, "pair_scores": list(result.summary.pair_scores), "mean_pair_score": result.summary.mean_pair_score, "game_wins": result.summary.game_wins, "game_draws": result.summary.game_draws, "game_losses": result.summary.game_losses}
            payload["decision"] = "ARENA_SCREEN_COMPLETE"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=lambda value: value.item() if isinstance(value, np.generic) else str(value)) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=lambda value: value.item() if isinstance(value, np.generic) else str(value)))


if __name__ == "__main__":
    main()
