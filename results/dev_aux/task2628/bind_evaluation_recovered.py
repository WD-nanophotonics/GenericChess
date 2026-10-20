"""Plan-derived binding after the pinned binder's pre-write NameError."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.local_agent.environment import require_identity

RUN = ROOT / "results/dev_aux/task2628/run"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_arm_keys(plan: dict) -> set[tuple[int, int]]:
    return {(rule, seed) for rule in plan["domain"]["rules"] for seed in plan["seeds"]}


def bind() -> dict:
    require_identity()
    target = RUN / "evaluation-registration.json"
    if target.exists():
        raise FileExistsError("evaluation binding is write-once")
    plan_path, reg_path = RUN / "plan.json", RUN / "registration.json"
    training_path, audit_path = RUN / "training-result.json", RUN / "training-audit.json"
    recovered_path, recovery_path = RUN / "training-result-recovered.json", RUN / "training-recovery.json"
    result_binding_path = RUN / "training-result-recovery-binding.json"
    failure_path = RUN / "evaluation-binding-failure.json"
    plan_raw, reg_raw, training_raw = plan_path.read_bytes(), reg_path.read_bytes(), training_path.read_bytes()
    plan, reg, training = json.loads(plan_raw), json.loads(reg_raw), json.loads(training_raw)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
    result_binding = json.loads(result_binding_path.read_text(encoding="utf-8"))
    failure = json.loads(failure_path.read_text(encoding="utf-8"))

    if sha(plan_path) != reg["plan_sha256"]:
        raise ValueError("registered plan changed")
    if sha(reg_path) != json.loads((RUN / "started.json").read_text(encoding="utf-8"))["registration_sha256"]:
        raise ValueError("registration differs from start receipt")
    if recovery.get("status") != "PASS_RECONSTRUCTED_ALL_REGISTERED_TRAINING_ARMS_FROM_DURABLE_LOGS":
        raise ValueError("training recovery did not pass")
    if failure.get("status") != "PRESERVED_PREWRITE_BINDER_FAILURE":
        raise ValueError("original binder failure was not preserved")
    if (training.get("recovery") is None or sha(recovered_path) != sha(training_path)
            or result_binding.get("status") != "PASS_RECOVERED_RESULT_BYTES_RECONCILED_AFTER_TEXT_NEWLINE_TRANSLATION"
            or result_binding.get("canonical_sha256") != sha(training_path)
            or result_binding.get("recovered_sha256") != sha(recovered_path)):
        raise ValueError("canonical training result is not the exact recovered summary")
    if (result_binding.get("recovery_report_sha256") != sha(recovery_path)
            or result_binding.get("training_audit_sha256") != sha(audit_path)):
        raise ValueError("result byte-reconciliation receipt binds different recovery/audit evidence")
    if training.get("status") != "COMPLETE":
        raise ValueError("recovered training is not complete")
    expected = expected_arm_keys(plan)
    arm_keys = {(arm["rule"], arm["seed"]) for arm in training.get("arms", [])}
    if arm_keys != expected or len(training["arms"]) != len(expected):
        raise ValueError("training arms differ from plan-derived grid")
    cap = plan["training"]["nodes_per_arm_candidate_plus_foe"]
    if any(arm["status"] != "NODE_CAP" or arm["nodes"] != cap for arm in training["arms"]):
        raise ValueError("all arms must have exact registered node-cap receipts")
    if audit.get("status") != "PASS_FULL_HISTORY_ACTUAL_TERMINAL_NODE_CAP_AND_TD_UPDATE_REPLAY":
        raise ValueError("independent training audit must pass before evaluation")
    if audit.get("training_result_sha256") != sha(training_path):
        raise ValueError("training audit binds a different recovered result")

    for path, expected_hash in reg["source_pins"].items():
        source = ROOT / path
        if not source.is_file() or sha(source) != expected_hash:
            raise ValueError(f"registered source changed: {path}")
    pool_path = ROOT / "results/dev_aux/task2627/rule15-successor-root-pools.json"
    pool_audit_path = ROOT / "results/dev_aux/task2627/rule15-successor-pool-audit.json"
    if sha(pool_path) != reg["root_pools_sha256"] or sha(pool_audit_path) != reg["root_pools_audit_sha256"]:
        raise ValueError("registered roots or root audit changed")
    if reg.get("evaluation_started") is not False:
        raise ValueError("registration already records evaluation as started")
    for name in ("eval-started.json", "eval-result.json", "eval-games.jsonl", "eval-queries.jsonl"):
        if (RUN / name).exists():
            raise FileExistsError(f"evaluation output already exists: {name}")

    binding = {
        "state": "EVALUATION_BOUND_BEFORE_FIRST_SLOT",
        "bound_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "plan_sha256": sha(plan_path), "registration_sha256": sha(reg_path),
        "training_result_sha256": sha(training_path), "training_audit_sha256": sha(audit_path),
        "root_pools_sha256": reg["root_pools_sha256"],
        "expected_slots": plan["evaluation"]["slots"],
        "all_training_arms_complete_and_audited": True, "evaluation_started": False,
        "binding_recovery": "The source-pinned binder raised NameError before writing. This plan-derived binder preserves that failure and binds the exact recovered training summary only after all registered source checks and the full-history audit passed.",
        "original_training_launch_return_code": json.loads((RUN / "launch-exit.json").read_text(encoding="utf-8"))["return_code"],
        "pinned_binder_sha256": sha(ROOT / "results/dev_aux/task2628/bind_evaluation.py"),
    }
    raw = json.dumps(binding, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    with target.open("xb") as stream:
        stream.write(raw)
        stream.flush()
    print(json.dumps(binding, indent=2, sort_keys=True))
    return binding


if __name__ == "__main__":
    bind()
