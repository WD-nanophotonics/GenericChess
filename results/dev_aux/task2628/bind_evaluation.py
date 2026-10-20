"""Bind complete, audited training endpoints to the one-shot evaluation."""
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


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> dict:
    require_identity()
    target = RUN / "evaluation-registration.json"
    if target.exists():
        raise FileExistsError("evaluation binding is write-once")
    plan_raw = (RUN / "plan.json").read_bytes()
    reg_raw = (RUN / "registration.json").read_bytes()
    training_raw = (RUN / "training-result.json").read_bytes()
    audit_raw = (RUN / "training-audit.json").read_bytes()
    plan, reg = json.loads(plan_raw), json.loads(reg_raw)
    training, audit = json.loads(training_raw), json.loads(audit_raw)
    if sha(plan_raw) != reg["plan_sha256"]:
        raise ValueError("registered plan changed")
    if training.get("status") != "COMPLETE" or len(training.get("arms", [])) != len(RULES) * len(SEEDS):
        raise ValueError("all frozen training arms must close before evaluation")
    if audit.get("status") != "PASS_FULL_HISTORY_ACTUAL_TERMINAL_NODE_CAP_AND_TD_UPDATE_REPLAY":
        raise ValueError("independent training audit must pass before evaluation")
    if audit.get("training_result_sha256") != sha(training_raw):
        raise ValueError("training audit binds a different model result")
    for path, expected in reg["source_pins"].items():
        if sha((ROOT / path).read_bytes()) != expected:
            raise ValueError(f"registered source changed: {path}")
    if (RUN / "eval-started.json").exists():
        raise ValueError("evaluation already started; cannot bind after execution")
    binding = {"state": "EVALUATION_BOUND_BEFORE_FIRST_SLOT",
               "bound_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "plan_sha256": sha(plan_raw), "registration_sha256": sha(reg_raw),
               "training_result_sha256": sha(training_raw), "training_audit_sha256": sha(audit_raw),
               "root_pools_sha256": reg["root_pools_sha256"], "expected_slots": plan["evaluation"]["slots"],
               "all_training_arms_complete_and_audited": True, "evaluation_started": False}
    raw = json.dumps(binding, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    target.write_bytes(raw)
    print(json.dumps(binding, indent=2, sort_keys=True))
    return binding


if __name__ == "__main__":
    main()
