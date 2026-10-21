"""Bind the full-pool cap screen to its exact helper and search sources."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2636"
OUTPUT = TASK / "query-cap-fullpool-source-verification-v2.json"


def raw_json(path: Path) -> tuple[bytes, dict]:
    raw = path.read_bytes()
    return raw, json.loads(raw)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> dict:
    if OUTPUT.exists():
        raise FileExistsError(f"write-once output already exists: {OUTPUT}")
    full_raw, full = raw_json(TASK / "query-cap-fullpool-audit.json")
    subset_raw, subset = raw_json(TASK / "query-cap-screen.json")
    plan_raw, plan = raw_json(TASK / "one-init-study-plan.json")
    reference_raw, reference_plan = raw_json(ROOT / "results/dev_aux/task2625/run/plan.json")
    full_script_raw = (TASK / "audit_query_cap_fullpool.py").read_bytes()
    helper_path = TASK / "audit_query_cap_screen.py"
    helper_raw = helper_path.read_bytes()
    alphabeta_path = ROOT / "results/dev_aux/task2492/learning.py"
    alphabeta_raw = alphabeta_path.read_bytes()
    expected_alpha = reference_plan["source_pins"]["results/dev_aux/task2492/learning.py"]

    if full["source_script_sha256"] != sha(full_script_raw):
        raise ValueError("full-pool screen source script hash mismatch")
    if subset["source_script_sha256"] != sha(helper_raw):
        raise ValueError("imported cap-screen helper differs from its source receipt")
    if full["subset_audit_sha256"] != sha(subset_raw):
        raise ValueError("full-pool screen does not bind the prior subset receipt")
    reference = subset["task2621_training_basis"]
    if reference["selected_roots"] != 8 or reference["full_width_nodes_gt_cap"] != 0:
        raise ValueError("task2621 reference screen does not verify zero exceedances across 8 roots")
    if sha(alphabeta_raw) != expected_alpha:
        raise ValueError("AlphaBeta source differs from the frozen task2625 source pin")
    cap = plan["training"]["search"]["nodes_per_query"]
    if plan["training"]["search"]["depth"] != 2 or plan["training"]["search"]["quiescence"] != 0 or cap != 2048:
        raise ValueError("frozen task2636 search budget differs from the audited D2/q0 contract")
    screen = full["screen"]
    if screen["selected_roots"] != 1920 or screen["query_node_cap"] != cap:
        raise ValueError("full-pool screen size or cap does not match the plan")
    if full["execution_state"]["run_v1_exists"] or full["execution_state"]["root_pool_registered"] or full["execution_state"]["learner_or_search_started"]:
        raise ValueError("task2636 run started before full-pool screen verification")

    result = {
        "status": "PASS_FULLPOOL_SCREEN_AND_ALPHA_BETA_SOURCE_BINDING",
        "verification_script_sha256": sha(Path(__file__).read_bytes()),
        "fullpool_audit_sha256": sha(full_raw),
        "subset_audit_sha256": sha(subset_raw),
        "fullpool_script_sha256": sha(full_script_raw),
        "shared_screen_helper_sha256": sha(helper_raw),
        "task2636_plan_sha256": sha(plan_raw),
        "task2625_reference_plan_sha256": sha(reference_raw),
        "task2492_alpha_beta_source_sha256": sha(alphabeta_raw),
        "frozen_search_contract": {"depth": 2, "quiescence": 0, "nodes_per_query": cap},
        "fullpool_exceedance": {
            "roots": screen["selected_roots"],
            "above_cap": screen["full_width_nodes_gt_cap"],
            "fraction": screen["fraction_gt_cap"],
            "reference_roots": reference["selected_roots"],
            "reference_roots_above_cap": reference["full_width_nodes_gt_cap"],
        },
        "execution_state": full["execution_state"],
        "interpretation_limit": full["interpretation_limit"],
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
