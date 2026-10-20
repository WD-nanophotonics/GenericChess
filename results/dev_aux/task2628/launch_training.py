"""One-shot launcher with durable claim, process-start and exit receipts."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2628/run"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_once(path: Path, value: dict) -> None:
    with path.open("xb") as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
        stream.flush()


def main() -> dict:
    plan_raw = (RUN / "plan.json").read_bytes()
    reg_raw = (RUN / "registration.json").read_bytes()
    plan, reg = json.loads(plan_raw), json.loads(reg_raw)
    if reg.get("state") != "REGISTERED_BEFORE_TRAINING_OR_EVALUATION" or reg.get("training_started") is not False:
        raise ValueError("launcher requires the untouched pre-training registration")
    if reg.get("plan_sha256") != sha(plan_raw):
        raise ValueError("registered plan hash mismatch")
    for relative, digest in reg["source_pins"].items():
        if sha((ROOT / relative).read_bytes()) != digest:
            raise ValueError(f"registered source changed: {relative}")

    names = ("started.json", "queries.jsonl", "episodes.jsonl", "training-result.json",
             "launch-claim.json", "launch-started.json", "launch-exit.json",
             "launcher.stdout", "launcher.stderr")
    if any((RUN / name).exists() for name in names):
        raise FileExistsError("training/launcher output exists; refusing retry or top-up")
    command = [sys.executable, "-m", "results.dev_aux.task2628.train"]
    write_once(RUN / "launch-claim.json", {
        "status": "LAUNCH_CLAIMED_NO_RETRY",
        "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": command, "plan_sha256": sha(plan_raw),
        "registration_sha256": sha(reg_raw),
        "launcher_sha256": sha(Path(__file__).read_bytes()),
        "session_id": reg["session_id"],
    })
    began = time.perf_counter()
    with (RUN / "launcher.stdout").open("xb") as stdout, (RUN / "launcher.stderr").open("xb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        write_once(RUN / "launch-started.json", {
            "status": "PROCESS_STARTED",
            "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "pid": process.pid, "command": command,
            "plan_sha256": sha(plan_raw), "registration_sha256": sha(reg_raw),
            "session_id": reg["session_id"],
        })
        code = process.wait()
    elapsed = time.perf_counter() - began
    result = RUN / "training-result.json"
    receipt = {
        "status": "EXIT_RECORDED", "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "return_code": code, "wall_seconds": elapsed, "plan_sha256": sha(plan_raw),
        "training_result_sha256": sha(result.read_bytes()) if result.is_file() else None,
        "stdout_sha256": sha((RUN / "launcher.stdout").read_bytes()),
        "stderr_sha256": sha((RUN / "launcher.stderr").read_bytes()),
        "process_started_sha256": sha((RUN / "launch-started.json").read_bytes()),
        "session_id": reg["session_id"],
    }
    write_once(RUN / "launch-exit.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return receipt


if __name__ == "__main__":
    result = main()
    raise SystemExit(result["return_code"])
