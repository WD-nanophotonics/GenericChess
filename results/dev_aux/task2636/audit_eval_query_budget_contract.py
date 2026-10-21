"""Audit the frozen plan's shared training/evaluation query-budget convention."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2636"
OUTPUT = TASK / "evaluation-query-budget-contract-audit.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> dict:
    if OUTPUT.exists():
        raise FileExistsError(f"write-once output already exists: {OUTPUT}")
    plan_path = TASK / "one-init-study-plan.json"
    audit_path = TASK / "partial_evaluation_audit.py"
    tests_path = TASK / "test_partial_evaluation_audit.py"
    fullpool_path = TASK / "query-cap-fullpool-audit.json"
    plan_raw, plan = plan_path.read_bytes(), json.loads(plan_path.read_text(encoding="utf8"))
    audit_raw = audit_path.read_bytes()
    tests_raw = tests_path.read_bytes()
    fullpool_raw = fullpool_path.read_bytes()
    evaluation = plan["evaluation"]
    training_search = plan["training"]["search"]
    audit_source = audit_raw.decode("utf8")
    test_source = " ".join(tests_raw.decode("utf8").split())
    if "plan[\"training\"][\"search\"][\"nodes_per_query\"]" not in audit_source:
        raise ValueError("evaluation replay adapter no longer reads the shared training search cap")
    if ('"requested_nodes": 2048' not in test_source
            or "replay_slot_history(before, slot_record, [query], compiled, weights, foe, cap, 2048)"
            not in test_source):
        raise ValueError("focused evaluation tests no longer bind the expected 2,048 query request")
    if "nodes_per_query" in evaluation or "seconds_per_query" in evaluation:
        raise ValueError("evaluation now declares its own per-query budget; reassess this audit")
    if (training_search["depth"] != evaluation["depth"] or training_search["depth"] != 2
            or training_search["quiescence"] != 0 or training_search["nodes_per_query"] != 2048
            or training_search["seconds_per_query"] != 2.0):
        raise ValueError("current shared search contract differs from the audited values")
    fullpool = json.loads(fullpool_raw)
    if fullpool["screen"]["query_node_cap"] != training_search["nodes_per_query"]:
        raise ValueError("full-pool cap screen does not use the frozen shared query limit")

    result = {
        "status": "PASS_SHARED_SEARCH_CONVENTION_EVAL_FIELDS_IMPLICIT",
        "plan_sha256": sha(plan_raw),
        "evaluation_audit_source_sha256": sha(audit_raw),
        "evaluation_tests_sha256": sha(tests_raw),
        "query_cap_screen_sha256": sha(fullpool_raw),
        "training_search_contract": {
            "depth": training_search["depth"],
            "quiescence": training_search["quiescence"],
            "nodes_per_query": training_search["nodes_per_query"],
            "seconds_per_query": training_search["seconds_per_query"],
        },
        "evaluation_plan_fields": {
            "depth": evaluation["depth"],
            "horizon": evaluation["horizon"],
            "slots": evaluation["slots"],
            "explicit_nodes_per_query": False,
            "explicit_seconds_per_query": False,
        },
        "current_adapter_behavior": "FrozenSlotReplayContext passes training.search.nodes_per_query into evaluation query replay; tests bind requested_nodes=2048.",
        "execution_state": {"run_v1_exists": (TASK / "run-v1").exists(),
                            "root_pool_registered": json.loads((TASK / "one-init-root-pools.json").read_text(encoding="utf8"))["root_pool_registered"],
                            "learner_or_search_started": json.loads((TASK / "one-init-root-pools.json").read_text(encoding="utf8"))["learner_or_search_started"]},
        "decision": "Treat training.search as the shared frozen train/eval query-budget convention. Preserve this in any runner/bundle binder; do not invent a separate evaluation cap. No evaluation search was run.",
    }
    if any(result["execution_state"].values()):
        raise ValueError("task2636 run began during read-only contract audit")
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
