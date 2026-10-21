"""Bind the frozen task2636 cost projection to its exact historical sources."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2636"
OUTPUT = TASK / "estimate-basis-receipt-verification-v2.json"


def read(path: Path) -> tuple[bytes, dict]:
    raw = path.read_bytes()
    return raw, json.loads(raw)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def close(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(f"{label} differs: {actual} != {expected}")


def main() -> dict:
    if OUTPUT.exists():
        raise FileExistsError(f"write-once output already exists: {OUTPUT}")

    plan_raw, plan = read(TASK / "one-init-study-plan.json")
    pool_raw, pool = read(TASK / "one-init-root-pools.json")
    root_census_raw, root_census = read(TASK / "cost-basis-root-branching-audit.json")
    task2625_raw, task2625 = read(ROOT / "results/dev_aux/task2625/run/plan.json")
    if sha(task2625_raw) != plan["source_lineage"]["task2625_reference_plan_sha256"]:
        raise ValueError("task2625 reference plan differs from the frozen task2636 lineage")
    if root_census["pins"]["task2625_reference_plan_sha256"] != sha(task2625_raw):
        raise ValueError("root census and task2636 plan disagree on the task2625 reference")

    cost_path = ROOT / "results/dev_aux/task2621/cost-feasibility.json"
    cost_raw, cost = read(cost_path)
    expected_cost_sha = task2625["source_pins"]["results/dev_aux/task2621/cost-feasibility.json"]
    if sha(cost_raw) != expected_cost_sha:
        raise ValueError("task2621 cost feasibility differs from the pinned task2625 source")

    train_path = ROOT / cost["training_source"]["path"]
    train_raw, train = read(train_path)
    if sha(train_raw) != cost["training_source"]["sha256"]:
        raise ValueError("task2621 training cost result hash mismatch")
    eval_path = ROOT / cost["evaluation_source"]["path"]
    eval_raw, evaluation = read(eval_path)
    if sha(eval_raw) != cost["evaluation_source"]["sha256"]:
        raise ValueError("task2609 evaluation result hash mismatch")

    train_registration_raw, train_registration = read(
        ROOT / "results/dev_aux/task2621/cost-scan/registration.json")
    train_manifest_path = ROOT / "results/dev_aux/task2621/active-feature-probe/root-manifest.json"
    train_manifest_raw, _ = read(train_manifest_path)
    if sha(train_manifest_raw) != train_registration["root_manifest_sha256"]:
        raise ValueError("task2621 cost-scan roots differ from the registered root manifest")

    eval_plan_path = ROOT / "results/dev_aux/task2609/eval-plan.json"
    eval_plan_raw, eval_plan = read(eval_plan_path)
    eval_registration_raw, eval_registration = read(
        ROOT / "results/dev_aux/task2609/registration.json")
    eval_manifest_path = ROOT / "results/dev_aux/task2609/root-manifest.json"
    eval_manifest_raw, _ = read(eval_manifest_path)
    if (sha(eval_manifest_raw) != eval_plan["root_manifest_sha256"] or
            sha(eval_manifest_raw) != eval_registration["root_manifest_sha256"]):
        raise ValueError("task2609 evaluation roots differ from frozen plan/registration")

    arm_cap = 80_000
    if len(train["arms"]) != 4 or any(arm["counts"]["nodes"] != arm_cap for arm in train["arms"]):
        raise ValueError("task2621 source is not the exact four-arm 80k-node cost scan")
    slowest_seconds = max(arm["seconds"] for arm in train["arms"])
    projected_training = cost["prospective_training_nodes"] / arm_cap * cost["runtime_margin"] * slowest_seconds
    close(projected_training, cost["training_projection_seconds"], "training projection")
    close(projected_training, plan["budget"]["projected_seconds"]["training"], "plan training projection")
    if (evaluation["expected"] != cost["evaluation_source"]["slots"] or
            evaluation["actual"] != cost["evaluation_source"]["slots"]):
        raise ValueError("task2609 evaluation slot count differs from the cost receipt")
    close(evaluation["seconds"], cost["evaluation_projection_seconds"], "evaluation projection")
    close(evaluation["seconds"], plan["budget"]["projected_seconds"]["evaluation"], "plan evaluation projection")
    close(cost["estimate_seconds"], plan["budget"]["projected_seconds"]["all_in"], "all-in projection")

    frozen_train = root_census["task2636_frozen_roots"]["training_all"]
    basis_train = root_census["training_cost_basis_task2621"]["all"]
    frozen_eval = root_census["task2636_frozen_roots"]["evaluation_all"]
    basis_eval = root_census["evaluation_cost_basis_task2609"]["all"]
    if basis_train["roots"] != 8 or basis_eval["roots"] != 64:
        raise ValueError("direct estimate root census has unexpected size")
    if frozen_train["roots"] != 1920 or frozen_eval["roots"] != 256:
        raise ValueError("task2636 frozen root census has unexpected size")

    result = {
        "status": "PASS_ESTIMATE_SOURCE_AND_ROOT_BINDING",
        "source_script_sha256": sha(Path(__file__).read_bytes()),
        "plan_sha256": sha(plan_raw),
        "root_pool_sha256": sha(pool_raw),
        "root_census_sha256": sha(root_census_raw),
        "task2625_plan_sha256": sha(task2625_raw),
        "task2621_cost_feasibility_sha256": sha(cost_raw),
        "task2621_cost_scan_result_sha256": sha(train_raw),
        "task2621_registration_sha256": sha(train_registration_raw),
        "task2621_root_manifest_sha256": sha(train_manifest_raw),
        "task2609_eval_result_sha256": sha(eval_raw),
        "task2609_eval_plan_sha256": sha(eval_plan_raw),
        "task2609_registration_sha256": sha(eval_registration_raw),
        "task2609_root_manifest_sha256": sha(eval_manifest_raw),
        "training_projection_reconstructed_seconds": projected_training,
        "training_slowest_80k_arm_seconds": slowest_seconds,
        "training_formula": "4,000,000 / 80,000 * 1.5 * max(task2621 arm seconds)",
        "evaluation_projection_reconstructed_seconds": evaluation["seconds"],
        "evaluation_basis_slots": evaluation["actual"],
        "root_action_means": {
            "task2636_training": frozen_train["mean"],
            "task2621_training_basis": basis_train["mean"],
            "task2636_to_task2621_ratio": frozen_train["mean"] / basis_train["mean"],
            "task2636_evaluation": frozen_eval["mean"],
            "task2609_evaluation_basis": basis_eval["mean"],
            "task2636_to_task2609_ratio": frozen_eval["mean"] / basis_eval["mean"],
        },
        "execution_state": {
            "run_v1_exists": (TASK / "run-v1").exists(),
            "root_pool_registered": pool["root_pool_registered"],
            "learner_or_search_started": pool["learner_or_search_started"],
        },
        "interpretation_limit": (
            "Verifies the historical projection inputs and fixed-root legal-action contrast. "
            "It does not predict candidate runtime, descendant branching, or search throughput."
        ),
    }
    if any(result["execution_state"].values()):
        raise ValueError("task2636 execution state changed during read-only verification")
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
