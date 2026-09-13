"""R18 fixed POINTWISE_Q screen with fresh F60 D1/D2 training roots.

The learner and search remain fixed; only the 24-root training-state
distribution changes. Twelve roots come from independent self-play
trajectories and twelve from a separate self-play/PV-corridor pool.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.learning.arena import ArenaConfig, run_arena_game_resumable  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f60_disjoint_policy_objective_validation as f60  # noqa: E402
from scripts import f61_gen0_gen1_strength_triage as gen  # noqa: E402
from scripts import f61_strength_first_triage as f61  # noqa: E402


RULESET = "B_CANONICAL_STANDARD_SHOGI"
TRAINING_SEED = 59013
D1_SEED = 620802
D2_SEED = 620803
ARENA_SEED = 620708
FROZEN_OPENING_SEED = 620700
ROOTS_PER_DISTRIBUTION = 12
NODES = 2_000
DEPTH = 12
TT_MB = 8
OUT = ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage" / "pointwise_distribution_screen.json"


def _record_key(record: dict) -> str:
    return str(record["position_key"])


def _opening_keys(compiled) -> set[str]:
    keys: set[str] = set()
    for seed in range(620700, 620708):
        openings = generate_arena_openings(compiled, count=4, seed=seed, min_plies=2, max_plies=6)
        for opening in openings.openings:
            history = []
            for action in opening.actions:
                history.append(action)
                record = f59._record_from_actions(compiled, history)
                if record is not None:
                    keys.add(_record_key(record))
    return keys


def _one_per_group(records: list[dict], forbidden: set[str], count: int, prefix: str) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for record in records:
        groups.setdefault(str(record.get("source_group", "")), []).append(record)
    selected = []
    for group in sorted(groups):
        candidate = next((row for row in groups[group] if _record_key(row) not in forbidden), None)
        if candidate is None:
            continue
        row = dict(candidate)
        row["source_group"] = f"{prefix}_{group}"
        selected.append(row)
        forbidden.add(_record_key(row))
        if len(selected) == count:
            break
    if len(selected) != count:
        raise RuntimeError(f"{prefix} supplied {len(selected)} independent roots, expected {count}")
    return selected


def _d2_pv_roots(compiled, native, parent, records: list[dict], forbidden: set[str], count: int) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for record in records:
        groups.setdefault(str(record.get("source_group", "")), []).append(record)
    selected = []
    for group in sorted(groups):
        base = next((row for row in groups[group] if _record_key(row) not in forbidden), None)
        if base is None:
            continue
        root = f59._root_search(compiled, native, parent, base, f60.F60_PV_NODES)
        history = [f59.action_from_dict(item) for item in base["action_history"]]
        candidate = None
        for payload in root["pv"]:
            trial = f59._record_from_actions(compiled, history + [f59.action_from_dict(payload)])
            if trial is not None and _record_key(trial) not in forbidden:
                candidate = trial
                break
        if candidate is None:
            continue
        row = dict(candidate)
        row["source_group"] = f"D2_PV_{group}"
        selected.append(row)
        forbidden.add(_record_key(row))
        if len(selected) == count:
            break
    if len(selected) != count:
        raise RuntimeError(f"D2 PV pool supplied {len(selected)} independent roots, expected {count}")
    return selected


def _stats(values: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(values)), "max": float(np.max(values)),
        "mean": float(np.mean(values)), "std": float(np.std(values)),
        "rms": float(np.sqrt(np.mean(np.square(values)))),
    }


def _fit(records, compiled, native, parent):
    roots = []
    for index, record in enumerate(records):
        rows = gen._lean_spectrum_for_root(compiled, native, parent, record, smoke=False)
        usable = [row for row in rows if row.q_20k is not None]
        if len(usable) < 2:
            raise RuntimeError(f"root {index} has fewer than two usable q20 actions")
        roots.append(usable)
    features = np.vstack([row.features for root in roots for row in root])
    base = np.asarray([row.base_q for root in roots for row in root], dtype=float)
    target = np.asarray([row.q_20k for root in roots for row in root], dtype=float)
    groups = []
    cursor = 0
    for root in roots:
        groups.append(np.arange(cursor, cursor + len(root)))
        cursor += len(root)
    model = f61._fit_serializable(features, base, target, groups, "POINTWISE_Q", TRAINING_SEED)
    spec = {
        "candidate_id": "F61_D12_POINTWISE_Q_SEED_59013",
        "training_distribution": "D12_D1_D2_MIX",
        "objective": "POINTWISE_Q",
        "seed": TRAINING_SEED,
    }
    child, payload = f61._candidate_checkpoint(parent, compiled, model, spec)
    residual = target - base
    prediction = model.predict(features)
    return child, payload, {
        "training_roots": len(roots), "training_actions": int(len(features)),
        "target_residual": _stats(residual), "learned_residual": _stats(prediction),
        "prediction_to_target_rms_ratio": float(np.sqrt(np.mean(prediction ** 2)) / np.sqrt(np.mean(residual ** 2))),
        "model_sha256": f61.stable_sha256(payload),
    }, roots


def _frozen_search(compiled, native, parent, child):
    rows = []
    openings = generate_arena_openings(compiled, count=4, seed=FROZEN_OPENING_SEED, min_plies=2, max_plies=6)
    for opening in openings.openings:
        record = {"action_history": [f59.action_to_dict(action) for action in opening.actions]}
        session = f59._session(compiled, record)
        results = []
        for checkpoint in (parent, child):
            result = SemanticSearchEngine(compiled, native, checkpoint=checkpoint, tt_megabytes=TT_MB).search(
                session, SearchLimits(max_depth=DEPTH, max_nodes=NODES, quiescence_max_depth=0)
            )
            results.append({"action": None if result.action is None else f59.action_to_dict(result.action), "score": int(result.score)})
        rows.append({"opening_id": opening.final_position_key, "parent": results[0], "child": results[1], "changed": results[0]["action"] != results[1]["action"]})
    return rows


def _arena_payload(summary) -> dict:
    return {
        "pair_count": summary.pair_count, "pair_scores": list(summary.pair_scores),
        "mean_pair_score": summary.mean_pair_score, "child_better_pairs": summary.child_better_pairs,
        "tied_pairs": summary.tied_pairs, "child_worse_pairs": summary.child_worse_pairs,
        "game_wins": summary.game_wins, "game_draws": summary.game_draws, "game_losses": summary.game_losses,
        "bootstrap_low": summary.bootstrap_low, "bootstrap_high": summary.bootstrap_high,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-arena", action="store_true")
    args = parser.parse_args()
    compiled, native, parent, _ = gen._context(RULESET)
    forbidden = {_record_key(row) for row in gen._d0_records(compiled, 620000, count=gen.ROOT_COUNT, smoke=False)}
    forbidden |= _opening_keys(compiled)
    d1_pool, d1_source = f60._fresh_selfplay(compiled, native, parent, D1_SEED, ROOTS_PER_DISTRIBUTION, smoke=False)
    d1 = _one_per_group(d1_pool, forbidden, ROOTS_PER_DISTRIBUTION, "D1")
    d2_pool, d2_source = f60._fresh_selfplay(compiled, native, parent, D2_SEED, ROOTS_PER_DISTRIBUTION, smoke=False)
    d2 = _d2_pv_roots(compiled, native, parent, d2_pool, forbidden, ROOTS_PER_DISTRIBUTION)
    records = d1 + d2
    if len(records) != 24 or len({_record_key(row) for row in records}) != 24:
        raise RuntimeError("D1/D2 root identity is not exactly 24 unique positions")
    child, model_payload, fit_metrics, roots = _fit(records, compiled, native, parent)
    frozen = _frozen_search(compiled, native, parent, child)
    if not any(row["changed"] for row in frozen):
        raise RuntimeError("D1/D2 candidate is behaviorally identical to parent on all frozen openings")
    payload = {
        "schema": "generic-chess-f61-pointwise-distribution-screen-v1",
        "ruleset": RULESET, "training_distribution": "D12_D1_D2_MIX",
        "d1_seed": D1_SEED, "d2_seed": D2_SEED, "arena_seed": ARENA_SEED,
        "parent_checkpoint_id": parent.checkpoint_id, "child_checkpoint_id": child.checkpoint_id,
        "model_sha256": fit_metrics["model_sha256"], "training": fit_metrics,
        "root_counts": {"D1_V2_SELFPLAY": len(d1), "D2_V2_PV_CORRIDOR": len(d2), "total": len(records)},
        "source_ids": {"D1_V2_SELFPLAY": d1_source, "D2_V2_PV_CORRIDOR": d2_source},
        "forbidden_original_d0_count": len(forbidden) - len(_opening_keys(compiled)),
        "frozen_opening_search": {"opening_seed": FROZEN_OPENING_SEED, "nodes": NODES, "max_depth": DEPTH, "tt_megabytes": TT_MB, "rows": frozen},
    }
    if args.run_arena:
        openings = generate_arena_openings(compiled, count=1, seed=ARENA_SEED, min_plies=2, max_plies=6)
        result = run_arena_game_resumable(
            compiled, native, parent, child,
            ArenaConfig(pairs=1, nodes_per_move=NODES, max_depth=DEPTH, tt_megabytes=TT_MB,
                        opening_seed=ARENA_SEED, opening_count=1, min_plies=2, max_plies=6, workers=1),
            progress_dir=OUT.parent / "arena-progress-distribution" / str(compiled.ruleset_fingerprint) / f"seed-{ARENA_SEED}",
            openings=openings, stop_on_decision=False,
        )
        if result.status != "COMPLETE" or result.summary is None:
            raise RuntimeError(f"Arena incomplete: {result.status} {result.reason}")
        payload["fresh_arena"] = {"opening_seed": ARENA_SEED, "nodes": NODES, "max_depth": DEPTH, "tt_megabytes": TT_MB, **_arena_payload(result.summary)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
