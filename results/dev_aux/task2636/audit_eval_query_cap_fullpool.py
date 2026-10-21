"""Screen all frozen task2636 evaluation roots against the shared node cap."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from audit_query_cap_screen import compile_source, load, screen

TASK = ROOT / "results/dev_aux/task2636"
OUTPUT = TASK / "query-cap-evaluation-fullpool-audit.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> dict:
    if OUTPUT.exists():
        raise FileExistsError(f"write-once output already exists: {OUTPUT}")
    plan_raw, plan = load(TASK / "one-init-study-plan.json")
    pool_raw, pool = load(ROOT / plan["source_lineage"]["root_pool"])
    index_raw, index = load(ROOT / plan["source_lineage"]["candidate_index"])
    cap_contract_raw, cap_contract = load(TASK / "evaluation-query-budget-contract-audit-v2.json")
    if sha(pool_raw) != plan["source_lineage"]["root_pool_sha256"]:
        raise ValueError("task2636 root-pool hash mismatch")
    if sha(index_raw) != plan["source_lineage"]["candidate_index_sha256"]:
        raise ValueError("task2636 candidate-index hash mismatch")
    if cap_contract["status"] != "PASS_NODE_LIMIT_SHARED_TIME_LIMIT_UNVERIFIED":
        raise ValueError("the evaluation node-cap contract is not verified")
    if pool["root_pool_registered"] or pool["learner_or_search_started"] or (TASK / "run-v1").exists():
        raise ValueError("evaluation cap screen requires the unregistered frozen study")

    candidates = {str(i): compile_source(ROOT / row["source_file"], row["ruleset_sha256"])
                  for i, row in enumerate(index["rows"])}
    rows = [(str(root["candidate_index"]), root["family"], root["record"])
            for root in pool["evaluation_roots"]]
    if len(rows) != 16 * 16:
        raise ValueError("frozen evaluation root pool is not the planned 16x16")
    for candidate in range(16):
        candidate_roots = [root for root in pool["evaluation_roots"]
                           if root["candidate_index"] == candidate]
        if len(candidate_roots) != 16 or len({root["family"] for root in candidate_roots}) != 16:
            raise ValueError(f"candidate {candidate} evaluation roots are incomplete or duplicated")

    result = {
        "status": "PASS_FROZEN_EVALUATION_ROOT_D2_CAP_BOUND_NO_SEARCH_NO_OUTCOME_READ",
        "audit_script_sha256": sha(Path(__file__).read_bytes()),
        "query_cap_contract_sha256": sha(cap_contract_raw),
        "query_cap_contract_status": cap_contract["status"],
        "plan_sha256": sha(plan_raw),
        "root_pool_sha256": sha(pool_raw),
        "candidate_index_sha256": sha(index_raw),
        "selection": "all 16 frozen evaluation roots in family order for each of the 16 candidates; no outcome-based selection",
        "screen": screen(rows, candidates, plan["training"]["search"]["nodes_per_query"]),
        "execution_state": {"run_v1_exists": (TASK / "run-v1").exists(),
                            "root_pool_registered": pool["root_pool_registered"],
                            "learner_or_search_started": pool["learner_or_search_started"]},
        "interpretation_limit": (
            "No-pruning, no-terminal-shortcut D2 full-width walk-call upper bound only. "
            "This is not an AlphaBeta cap-hit, UNKNOWN-rate or runtime estimate; it counts "
            "one root tree per candidate/family, not both endpoints/colors. The verified "
            "per-query node cap is 2,048; evaluation seconds_per_query remains unverified."
        ),
    }
    if any(result["execution_state"].values()):
        raise ValueError("task2636 execution started during read-only screen")
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
