"""Run the no-search D2 query-cap bound on every frozen training root."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from audit_query_cap_screen import compile_source, load, screen

TASK = ROOT / "results/dev_aux/task2636"
OUTPUT = TASK / "query-cap-fullpool-audit.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> dict:
    if OUTPUT.exists():
        raise FileExistsError(f"write-once output already exists: {OUTPUT}")
    plan_raw, plan = load(TASK / "one-init-study-plan.json")
    pool_raw, pool = load(ROOT / plan["source_lineage"]["root_pool"])
    index_raw, index = load(ROOT / plan["source_lineage"]["candidate_index"])
    if sha(pool_raw) != plan["source_lineage"]["root_pool_sha256"]:
        raise ValueError("task2636 root-pool hash mismatch")
    if sha(index_raw) != plan["source_lineage"]["candidate_index_sha256"]:
        raise ValueError("task2636 candidate-index hash mismatch")
    if pool["root_pool_registered"] or pool["learner_or_search_started"] or (TASK / "run-v1").exists():
        raise ValueError("full-pool screen requires the unregistered frozen study")

    candidates = {str(i): compile_source(ROOT / row["source_file"], row["ruleset_sha256"])
                  for i, row in enumerate(index["rows"])}
    rows = [(str(root["candidate_index"]), root["family"], root["record"])
            for root in pool["training_roots"]]
    if len(rows) != 16 * 120:
        raise ValueError("frozen training root pool is not the planned 16x120")
    for candidate in range(16):
        if sum(1 for row in pool["training_roots"] if row["candidate_index"] == candidate) != 120:
            raise ValueError(f"candidate {candidate} root count mismatch")

    subset_raw, subset = load(TASK / "query-cap-screen.json")
    if (subset["status"] != "PASS_UNPRUNED_D2_QUERY_CAP_SCREEN_NO_SEARCH_NO_OUTCOME_READ"
            or subset["task2636_training_subset"]["selected_roots"] != 128):
        raise ValueError("the prior deterministic subset screen is missing or invalid")
    result = {
        "status": "PASS_FULL_FROZEN_TRAINING_ROOT_D2_CAP_BOUND_NO_SEARCH_NO_OUTCOME_READ",
        "source_script_sha256": sha(Path(__file__).read_bytes()),
        "subset_audit_sha256": sha(subset_raw),
        "plan_sha256": sha(plan_raw),
        "root_pool_sha256": sha(pool_raw),
        "candidate_index_sha256": sha(index_raw),
        "selection": "all 120 frozen training roots in family order for all 16 candidates; no outcome-based selection",
        "screen": screen(rows, candidates, plan["training"]["search"]["nodes_per_query"]),
        "execution_state": {"run_v1_exists": (TASK / "run-v1").exists(),
                            "root_pool_registered": pool["root_pool_registered"],
                            "learner_or_search_started": pool["learner_or_search_started"]},
        "interpretation_limit": (
            "No-pruning, no-terminal-shortcut D2 full-width walk-call upper bound only. "
            "It does not predict AlphaBeta cap hits, UNKNOWN rates or runtime."
        ),
    }
    if any(result["execution_state"].values()):
        raise ValueError("task2636 execution started during read-only screen")
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
