"""Reconcile and replay task2635 rows after the producer's summary error."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from tools.local_agent.environment import require_identity

TASK = ROOT / "results/dev_aux/task2635"
PLAN_PATH = TASK / "plan-v2.json"
PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
RUN = TASK / "run-v2"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> dict:
    require_identity()
    if sha(Path(__file__).with_name("feature_activation_probe.py").read_bytes()) != PLAN["runner_sha256"]:
        raise ValueError("producer source no longer matches the frozen run plan")
    candidate_index_path = ROOT / PLAN["candidate_index"]
    index_raw = candidate_index_path.read_bytes()
    if sha(index_raw) != PLAN["candidate_index_sha256"]:
        raise ValueError("candidate index changed")
    for rel, expected in PLAN["source_sha256"].items():
        if sha((ROOT / rel).read_bytes()) != expected:
            raise ValueError(f"pinned source changed: {rel}")
    candidates = json.loads(index_raw)["rows"]
    compiled = []
    for candidate in candidates:
        raw = (ROOT / candidate["source_file"]).read_bytes()
        if sha(raw) != candidate["ruleset_sha256"]:
            raise ValueError("candidate ruleset hash changed")
        compiled.append(compile_ruleset_for_execution(deserialize_ruleset(raw.decode("utf-8"))))

    rows = [json.loads(line) for line in (RUN / "episodes.jsonl").read_text(encoding="utf-8").splitlines() if line]
    expected_count = PLAN["candidate_count"] * PLAN["trajectories_per_candidate"]
    if len(rows) != expected_count:
        raise ValueError(f"durable episode count {len(rows)} != expected {expected_count}")
    seen = set()
    activations = []
    for row in rows:
        key = (row["candidate_index"], row["replicate"])
        if key in seen:
            raise ValueError(f"duplicate episode key: {key}")
        seen.add(key)
        if row["outcome_read"] is not False or row["ending"] not in {"PLY_CAP_UNKNOWN", "NO_BOARD_ACTION_UNKNOWN"}:
            raise ValueError("outcome boundary or unknown ending violated")
        record = deserialize_game_record(json.dumps(row["full_history_record"]))
        replay = GameSession.replay(compiled[row["candidate_index"]], record)
        if len(record.actions) != row["plies"]:
            raise ValueError("action count and reported plies differ")
        if row["first_nonzero_feature_ply"] is not None:
            activations.append(row["first_nonzero_feature_ply"])

    activations.sort()
    candidate_summary = []
    for candidate_index in range(PLAN["candidate_count"]):
        group = [row for row in rows if row["candidate_index"] == candidate_index]
        group_activations = sorted(row["first_nonzero_feature_ply"] for row in group if row["first_nonzero_feature_ply"] is not None)
        candidate_summary.append({
            "candidate_index": candidate_index,
            "seed": candidates[candidate_index].get("seed"),
            "trajectories": len(group),
            "feature_activated_trajectories": len(group_activations),
            "first_activation_ply_min": min(group_activations) if group_activations else None,
            "first_activation_ply_median_upper": group_activations[len(group_activations) // 2] if group_activations else None,
            "first_activation_ply_max": max(group_activations) if group_activations else None,
            "endings": {ending: sum(row["ending"] == ending for row in group) for ending in ("PLY_CAP_UNKNOWN", "NO_BOARD_ACTION_UNKNOWN")},
        })
    result = {
        "status": "RECONCILED_FROM_DURABLE_ROWS",
        "producer_status": "ERROR_AFTER_EPISODE_LOGS_FLUSHED_BEFORE_RESULT_WRITE",
        "plan_sha256": sha(PLAN_PATH.read_bytes()),
        "producer_sha256": PLAN["runner_sha256"],
        "candidate_index_sha256": sha(index_raw),
        "durable_episode_log_sha256": sha((RUN / "episodes.jsonl").read_bytes()),
        "episodes_expected": expected_count,
        "episodes_reconciled": len(rows),
        "candidate_replicate_keys_unique": len(seen) == expected_count,
        "independent_full_history_replays_passed": len(rows),
        "feature_activated_episodes": len(activations),
        "first_activation_ply_min": min(activations) if activations else None,
        "first_activation_ply_median_upper": activations[len(activations) // 2] if activations else None,
        "first_activation_ply_max": max(activations) if activations else None,
        "ending_counts": {
            ending: sum(row["ending"] == ending for row in rows)
            for ending in ("PLY_CAP_UNKNOWN", "NO_BOARD_ACTION_UNKNOWN")
        },
        "total_recorded_plies": sum(row["plies"] for row in rows),
        "candidate_summaries": candidate_summary,
        "outcome_reads": 0,
        "search_queries": 0,
        "scope": "Read-only reconciliation of already-run, flushed histories. No trajectories were rerun and no WDL, search, learner or strength results were accessed.",
    }
    (RUN / "reconciled-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
