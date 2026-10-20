"""One-shot launcher with durable claim/start/exit receipts."""
from __future__ import annotations

import datetime
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2629/run"
SCRIPT = ROOT / "results/dev_aux/task2629/evaluate.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")
        stream.flush()


def main() -> int:
    from tools.local_agent.environment import require_identity
    require_identity()
    plan_path, reg_path, bind_path = RUN / "plan.json", RUN / "registration.json", RUN / "evaluation-registration.json"
    plan, reg, binding = (json.loads(p.read_text(encoding="utf-8")) for p in (plan_path, reg_path, bind_path))
    if reg.get("state") != "REGISTERED_BEFORE_EVALUATION" or binding.get("state") != "EVALUATION_BOUND_BEFORE_FIRST_SLOT":
        raise ValueError("evaluation is not registered and bound")
    if sha(plan_path) != reg.get("plan_sha256") or binding.get("plan_sha256") != reg.get("plan_sha256"):
        raise ValueError("plan binding mismatch")
    if reg.get("evaluation_started") is not False or binding.get("evaluation_started") is not False:
        raise ValueError("evaluation already has a start claim")
    if plan.get("evaluation", {}).get("H") != 256 or plan.get("evaluation", {}).get("slots") != 256:
        raise ValueError("unexpected frozen evaluation contract")
    for rel, expected in reg["source_pins"].items():
        if sha(ROOT / rel) != expected:
            raise ValueError(f"registered source changed: {rel}")
    if any((RUN / name).exists() for name in ("eval-started.json", "eval-games.jsonl", "eval-queries.jsonl")):
        raise FileExistsError("one-shot evaluation output already exists")

    command = [sys.executable, str(SCRIPT)]
    command_doc = json.dumps(command, ensure_ascii=False, separators=(",", ":")).encode()
    write_once(RUN / "launch-claim.json", {
        "claimed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "plan_sha256": sha(plan_path), "registration_sha256": sha(reg_path),
        "command": command, "command_sha256": hashlib.sha256(command_doc).hexdigest(),
        "evaluate_source_sha256": sha(SCRIPT), "expected_slots": 256,
        "session_id": reg["session_id"], "state": "CLAIMED_BEFORE_PROCESS_START"})
    stdout = (RUN / "launcher.stdout").open("xb")
    stderr = (RUN / "launcher.stderr").open("xb")
    began = time.perf_counter()
    process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
    start = {"started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "pid": process.pid, "plan_sha256": sha(plan_path),
             "registration_sha256": sha(reg_path), "command_sha256": hashlib.sha256(command_doc).hexdigest(),
             "evaluate_source_sha256": sha(SCRIPT), "session_id": reg["session_id"],
             "expected_slots": 256, "state": "PROCESS_STARTED"}
    write_once(RUN / "launch-started.json", start)
    print(json.dumps(start, indent=2), flush=True)
    code = process.wait()
    stdout.close(); stderr.close()
    end = {"ended_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "pid": process.pid, "return_code": code, "wall_seconds": time.perf_counter() - began,
           "stdout_sha256": sha(RUN / "launcher.stdout"),
           "stderr_sha256": sha(RUN / "launcher.stderr"),
           "eval_result_sha256": sha(RUN / "eval-result.json") if (RUN / "eval-result.json").exists() else None,
           "state": "EXIT_RECORDED"}
    write_once(RUN / "launch-exit.json", end)
    print(json.dumps(end, indent=2), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
