"""Freeze task2617's family-cap evaluation before any W/L outcomes exist."""
from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
TASK = ROOT / "results/dev_aux/task2617"
DEFAULT_RUN = TASK / "run-002"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def build_registration(directory: Path) -> dict:
    feasibility_path = TASK / "feasibility.json"
    roots_path = TASK / "prospective-roots.json"
    order_path = TASK / "execution-order.json"
    feasibility = json.loads(feasibility_path.read_text(encoding="utf-8"))
    roots = json.loads(roots_path.read_text(encoding="utf-8"))["roots"]
    order = json.loads(order_path.read_text(encoding="utf-8"))["slots"]
    if feasibility["status"] != "FEASIBILITY_ONLY_NOT_REGISTERED_NOT_STARTED":
        raise RuntimeError("task2617 feasibility status changed")
    if len(roots) != 32 or len(order) != 1024:
        raise ValueError("frozen root/slot count mismatch")
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise FileExistsError("registration destination is not empty")

    caps = {
        str(row["family"]): row["node_cap_both_sides"]
        for row in feasibility["protocol"]["budget_assignments"]
    }
    slots = [[0, seed, family, color, endpoint, "uniform"] for family, seed, color, endpoint in order]
    root_manifest = {
        "status": "FROZEN_BEFORE_OUTCOMES",
        "task": "DEV_AUX2617",
        "prefix_plies": 8,
        "unit": "exact complete ChessEnv record (initial FEN plus ordered UCI history)",
        "roots": roots,
    }
    plan = {
        "task": "DEV_AUX2617",
        "attempt_id": directory.name,
        "supersedes_attempt": {
            "id": "run-001",
            "status": "FAILED_PRE_SEARCH_STARTUP",
            "startup_failure_sha256": sha(TASK / "run-001/startup-failure.json"),
        },
        "status": "REGISTERED_PRE_RUN",
        "question": feasibility["question"],
        "domain": "chess",
        "rules": [0],
        "seeds": [1977, 8173, 27182, 31415],
        "endpoints": ["initial", "TD", "WDL", "TreeStrap"],
        "foes": {"uniform": [1.0, 1.0, 1.0, 1.0, 1.0]},
        "initialization": "frozen task2616 seed-matched initial endpoints; no retraining or selection",
        "caps_by_family": caps,
        "cap_values_nodes_both_sides": [20000, 40000],
        "budget_randomization_seed": 26170001,
        "execution_order_seed": 26170002,
        "ordering_seed_offset": json.loads((ROOT / "results/dev_aux/task2616/eval-plan.json").read_text(encoding="utf-8"))["ordering_seed_offset"],
        "slots": len(slots),
        "slot_order": "exact order in execution-order.json; randomization frozen independently of outcomes",
        "max_paid_nodes": 30720000,
        "expected_all_in_seconds": feasibility["cost_estimate"]["risk_adjusted_all_in_seconds"],
        "evaluation_hard_cap_seconds": 5400,
        "setup_audit_reserve_seconds": 900,
        "hard_cap_plus_reserve_seconds": 6300,
        "unknown": "censored; no UNKNOWN-to-draw or quantity substitution",
        "scope": "finite randomized family-cap contrast; no population or CI claim",
        "feasibility_sha256": sha(feasibility_path),
        "prospective_roots_sha256": sha(roots_path),
        "execution_order_sha256": sha(order_path),
    }
    eval_plan = {
        "task": "DEV_AUX2617",
        "attempt_id": directory.name,
        "status": "REGISTERED_PRE_RUN",
        "domain": "chess",
        "rules": [0],
        "seeds": plan["seeds"],
        "endpoints": plan["endpoints"],
        "foes": plan["foes"],
        "slots": slots,
        "root_manifest_sha256": hashlib.sha256(
            (json.dumps(root_manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        ).hexdigest(),
        "execution_order_sha256": plan["execution_order_sha256"],
        "prefix_plies": 8,
        "depth": 2,
        "q_limit": 2,
        "H": 1024,
        "nodes_per_query": 8192,
        "seconds_per_query": 2.0,
        "cap_seconds": 5400,
        "global_cap_seconds": 5400,
        "ordering_seed_offset": plan["ordering_seed_offset"],
        "cap_values_nodes_both_sides": [20000, 40000],
        "unknown_policy": "censored; actual terminal W/D/L only; endpoint-specific [-1,+1] completion bounds",
        "scope": "finite fixed-policy family-randomized comparison only",
    }

    runtime_names = [
        "results/dev_aux/task2392/reader.py",
        "results/dev_aux/task2492/adapters.py",
        "results/dev_aux/task2504/search.py",
        "results/dev_aux/task2565/train.py",
        "results/dev_aux/task2616/result.json",
        "results/dev_aux/task2616/eval-plan.json",
        "results/dev_aux/task2616/tree-training-result.json",
        "results/dev_aux/task2617/FEASIBILITY.md",
        "results/dev_aux/task2617/analyze.py",
        "results/dev_aux/task2617/evaluate.py",
        "results/dev_aux/task2617/feasibility.json",
        "results/dev_aux/task2617/feasibility.py",
        "results/dev_aux/task2617/prospective-roots.json",
        "results/dev_aux/task2617/execution-order.json",
        "results/dev_aux/task2617/register_run.py",
        "results/dev_aux/task2617/test_task2617.py",
        "results/dev_aux/task2617/RUN-002-AMENDMENT.md",
    ]
    runtime_pins = {name: sha(ROOT / name) for name in runtime_names}
    runner_registration = {
        "task": "DEV_AUX2617",
        "status": "READY_PRE_RUN",
        "python_version": sys.version.split()[0],
        "python_chess_version": version("chess"),
        "runtime_pins": runtime_pins,
    }
    model_binding = {
        "task": "DEV_AUX2617",
        "source_task": "DEV_AUX2616",
        "task2616_result_sha256": sha(ROOT / "results/dev_aux/task2616/result.json"),
        "tree_training_result_sha256": sha(ROOT / "results/dev_aux/task2616/tree-training-result.json"),
        "selection": "reuse the four task2616 endpoints exactly; no retraining or W/L-based model selection",
    }
    paths = {
        "root-manifest.json": root_manifest,
        "plan.json": plan,
        "eval-plan.json": eval_plan,
        "execution-order.json": {"task": "DEV_AUX2617", "seed": 26170002, "slots": order},
        "runner-registration.json": runner_registration,
        "model-binding.json": model_binding,
    }
    # The plans need their own exact hashes before writing the immutable receipt.
    plan_bytes = (json.dumps(plan, indent=2, sort_keys=True) + "\n").encode("utf-8")
    eval_bytes = (json.dumps(eval_plan, indent=2, sort_keys=True) + "\n").encode("utf-8")
    root_bytes = (json.dumps(root_manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    reg = {
        "task": "DEV_AUX2617",
        "attempt_id": directory.name,
        "supersedes_attempt": "run-001",
        "status": "REGISTERED_PRE_RUN",
        "science": "OPEN",
        "plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "eval_plan_sha256": hashlib.sha256(eval_bytes).hexdigest(),
        "root_manifest_sha256": hashlib.sha256(root_bytes).hexdigest(),
        "runner_registration_sha256": sha_payload(runner_registration),
        "model_binding_sha256": sha_payload(model_binding),
        "registered_slots": len(slots),
        "no_training_yet": True,
        "no_evaluation_yet": True,
    }
    for name, value in paths.items():
        write_once(directory / name, value)
    write_once(directory / "registration.json", reg)
    return reg


def sha_payload(value: object) -> str:
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=DEFAULT_RUN)
    args = parser.parse_args()
    reg = build_registration(args.directory.resolve())
    print(json.dumps(reg, indent=2))


if __name__ == "__main__":
    main()
