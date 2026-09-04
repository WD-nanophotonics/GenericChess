"""F58 corrective Shogi policy, runtime, and conditional arena gate."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from f50_generic_learnable_evaluator import _ruleset  # noqa: E402
from f54_direct_capacity_and_gradient_geometry_diagnosis import (  # noqa: E402
    _action_key, _agreement, _parent, _record_dict, _session,
)
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.core.actions import action_to_dict  # noqa: E402
from generic_chess.learning.nonlinear import semantic_state_features  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.learning.arena import ArenaConfig, run_arena  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.native.adapter import pack_semantic_search_position  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402

from f58_compact_nonlinear_capacity import (  # noqa: E402
    CORPUS_COUNT, DEV_COUNT, MATE_THRESHOLD, OPENING_COUNT, SEEDS,
    TEACHER_BUDGETS, _corpus, _features,
)


OUT = ROOT / ".generic_chess_flow" / "f58-corrective-policy-gate"
MODEL_SOURCE = ROOT / ".generic_chess_flow" / "f58-compact-nonlinear-capacity" / "f58_shogi_baseline_preserved.json"
LABEL = "B_CANONICAL_STANDARD_SHOGI"
POLICY_NODES = 2000


def _teacher_row(compiled, native, checkpoint, record, nodes):
    session = _session(compiled, record)
    started = time.perf_counter()
    result = SemanticSearchEngine(compiled, native, checkpoint=checkpoint, tt_megabytes=8).search(
        session, SearchLimits(max_depth=12, max_nodes=nodes, quiescence_max_depth=0)
    )
    return {
        "action_key": _action_key(None if result.action is None else action_to_dict(result.action)),
        "native_score": int(result.score),
        "side_to_move": int(session.state.position.side_to_move),
        "completed_depth": int(result.completed_depth),
        "nodes": int(result.nodes),
        "elapsed_seconds": time.perf_counter() - started,
    }


def _parallel(compiled, native, checkpoint, records, nodes):
    workers = min(8, max(1, os.cpu_count() or 1), len(records) or 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda r: _teacher_row(compiled, native, checkpoint, r, nodes), records))


def _owner0(row, parent):
    value = row["native_score"] / parent.semantic_native_scale
    return value if row["side_to_move"] == 0 else -value


def _policy_row(compiled, native, checkpoint, record):
    return _teacher_row(compiled, native, checkpoint, record, POLICY_NODES)


def _policy_parallel(compiled, native, checkpoint, records):
    workers = min(8, max(1, os.cpu_count() or 1), len(records) or 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda r: _policy_row(compiled, native, checkpoint, r), records))


def _checkpoint_from_model(compiled, model):
    parent = _parent(LABEL)
    return parent.child_checkpoint(
        board_weights=parent.board_weights,
        hand_weights=parent.hand_weights,
        dynamic_weights=parent.dynamic_weights,
        compact_nonlinear=model,
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=stable_sha256({"stage": "f58-corrective-policy", "label": LABEL}),
        training_seed=58011,
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    compiled, native, _profile = _ruleset(LABEL)
    parent = _parent(LABEL)
    preserved = json.loads(MODEL_SOURCE.read_text(encoding="utf-8"))
    old = next(item for item in preserved["results"] if item["label"] == LABEL)
    model = next(item for item in old["compact_models"] if int(item["seed"]) == 58011)
    child = _checkpoint_from_model(compiled, model)
    payload, info = _corpus(LABEL, compiled)
    records = info["records"]

    teacher_40 = _parallel(compiled, native, parent, records, TEACHER_BUDGETS[0])
    teacher_80 = _parallel(compiled, native, parent, records, TEACHER_BUDGETS[1])
    stable = [a["action_key"] == b["action_key"] for a, b in zip(teacher_40, teacher_80)]
    validation_indices = [DEV_COUNT + i for i in range(CORPUS_COUNT - DEV_COUNT)
                          if stable[DEV_COUNT + i] and abs(teacher_80[DEV_COUNT + i]["native_score"]) <= MATE_THRESHOLD]
    validation_records = [records[i] for i in validation_indices]
    parent_policy = _policy_parallel(compiled, native, parent, validation_records)
    child_policy = _policy_parallel(compiled, native, child, validation_records)
    teacher_policy = [teacher_80[i] for i in validation_indices]
    parent_agreement = _agreement(parent_policy, teacher_policy)
    child_agreement = _agreement(child_policy, teacher_policy)
    flips = sum(a["action_key"] != b["action_key"] for a, b in zip(parent_policy, child_policy))
    displacement = float(np.mean([abs(a["native_score"] - b["native_score"]) / parent.semantic_native_scale
                                  for a, b in zip(parent_policy, child_policy)])) if child_policy else 0.0
    policy = {
        "count": len(validation_records),
        "teacher_80k_agreement_parent": parent_agreement,
        "teacher_80k_agreement_child": child_agreement,
        "agreement_delta": child_agreement - parent_agreement,
        "move_flip_rate": flips / len(validation_records) if validation_records else 0.0,
        "mean_absolute_score_displacement": displacement,
        "parent_avg_completed_depth": float(np.mean([r["completed_depth"] for r in parent_policy])) if parent_policy else 0.0,
        "child_avg_completed_depth": float(np.mean([r["completed_depth"] for r in child_policy])) if child_policy else 0.0,
        "parent_avg_nodes": float(np.mean([r["nodes"] for r in parent_policy])) if parent_policy else 0.0,
        "child_avg_nodes": float(np.mean([r["nodes"] for r in child_policy])) if child_policy else 0.0,
    }
    policy_pass = bool(policy["count"] > 0 and policy["move_flip_rate"] > 0 and child_agreement >= parent_agreement)

    runtime_indices = validation_indices[: min(32, len(validation_indices))]
    runtime_records = [records[i] for i in runtime_indices]
    runtime = {}
    for name, checkpoint in (("v2_parent", parent), ("v4_child", child)):
        rows = _policy_parallel(compiled, native, checkpoint, runtime_records)
        runtime[name] = {
            "count": len(rows),
            "nps": float(sum(r["nodes"] for r in rows) / max(sum(r["elapsed_seconds"] for r in rows), 1e-9)),
            "avg_elapsed_seconds": float(np.mean([r["elapsed_seconds"] for r in rows])) if rows else 0.0,
            "avg_completed_depth": float(np.mean([r["completed_depth"] for r in rows])) if rows else 0.0,
            "avg_nodes": float(np.mean([r["nodes"] for r in rows])) if rows else 0.0,
            "evaluator": "learnable-generic-v2" if name == "v2_parent" else "learnable-generic-v4",
        }
    result = {
        "work_order": "GENERICCHESS-F58-CORRECTIVE-AUX-SEMANTICS-AND-POLICY-GATE",
        "label": LABEL,
        "parent_checkpoint_id": parent.checkpoint_id,
        "child_checkpoint_id": child.checkpoint_id,
        "corpus": {"corpus_id": info["corpus_id"], "source_opening_corpus_id": info["source_opening_corpus_id"],
                   "count": len(records), "position_keys_sha256": stable_sha256([r["position_key"] for r in records])},
        "teacher": {"budgets": TEACHER_BUDGETS, "stable_count": sum(stable), "stable_rate": sum(stable) / len(stable)},
        "policy_gate": policy,
        "policy_pass": policy_pass,
        "runtime": runtime,
        "arena": None,
        "alphasho": "SKIPPED_POLICY_GATE" if not policy_pass else "EVALUATION_ONLY_PENDING_INTERNAL_ARENA",
    }
    if policy_pass:
        openings = generate_arena_openings(compiled, count=8, seed=SEEDS[LABEL], min_plies=2, max_plies=6)
        summary = run_arena(compiled, native, parent, child,
                            ArenaConfig(pairs=8, nodes_per_move=2000, max_depth=12, tt_megabytes=8,
                                        opening_seed=SEEDS[LABEL], opening_count=8, workers=1), openings=openings)
        result["arena"] = {"pairs": summary.pair_count, "mean_pair_score": summary.mean_pair_score,
                            "bootstrap_low": summary.bootstrap_low, "bootstrap_high": summary.bootstrap_high,
                            "better_pairs": summary.child_better_pairs, "tied_pairs": summary.tied_pairs,
                            "worse_pairs": summary.child_worse_pairs}
    (OUT / "f58_corrective_results.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
