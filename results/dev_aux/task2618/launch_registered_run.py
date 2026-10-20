"""One-shot launcher that retains the registered training process receipts."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
RUN_NAMES = {"learner-comparison-v1", "learner-comparison-v2"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_once(path: Path, value: dict) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()


def launch(run_name: str) -> dict:
    if run_name not in RUN_NAMES:
        raise ValueError("unsupported task2618 run name")
    run_dir = ROOT / "results/dev_aux/task2618" / run_name
    plan_raw = (run_dir / "plan.json").read_bytes()
    plan = json.loads(plan_raw)
    registration_raw = (run_dir / "registration.json").read_bytes()
    registration = json.loads(registration_raw)
    if registration.get("status") != "REGISTERED_PRE_TRAINING" or registration.get("search_started") is not False:
        raise ValueError("launcher requires a pre-search registration")
    if registration.get("plan_sha256") != sha(plan_raw):
        raise ValueError("registered plan hash mismatch")
    if plan.get("design_revision") != (2 if run_name.endswith("-v2") else 1):
        raise ValueError("run name and frozen design revision disagree")
    for relative, digest in plan.get("source_sha256", {}).items():
        if sha((ROOT / relative).read_bytes()) != digest:
            raise ValueError(f"registered source changed: {relative}")

    run_files = {
        "started": run_dir / "started.json",
        "queries": run_dir / "queries.jsonl",
        "games": run_dir / "games.jsonl",
        "training_result": run_dir / "training-result.json",
        "claim": run_dir / "launch-claim.json",
        "launch_started": run_dir / "launch-started.json",
        "launch_exit": run_dir / "launch-exit.json",
        "stdout": run_dir / "launcher.stdout",
        "stderr": run_dir / "launcher.stderr",
    }
    if any(path.exists() for path in run_files.values()):
        raise FileExistsError("run/launcher output already exists; refusing launch or top-up")

    command = [sys.executable, "-m", "results.dev_aux.task2618.train_learners",
               "--run-name", run_name]
    write_once(run_files["claim"], {
        "status": "LAUNCH_CLAIMED_NO_RETRY",
        "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "run_name": run_name,
        "command": command,
        "plan_sha256": sha(plan_raw),
        "registration_sha256": sha(registration_raw),
        "launcher_sha256": sha(Path(__file__).read_bytes()),
        "session_id": plan.get("session_id"),
    })

    began = time.perf_counter()
    with run_files["stdout"].open("xb") as stdout, run_files["stderr"].open("xb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        write_once(run_files["launch_started"], {
            "status": "PROCESS_STARTED",
            "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "pid": process.pid,
            "command": command,
            "plan_sha256": sha(plan_raw),
            "registration_sha256": sha(registration_raw),
            "session_id": plan.get("session_id"),
        })
        return_code = process.wait()
    elapsed = time.perf_counter() - began
    result_path = run_files["training_result"]
    result_sha = sha(result_path.read_bytes()) if result_path.is_file() else None
    record = {
        "status": "EXIT_RECORDED",
        "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "return_code": return_code,
        "wall_seconds": elapsed,
        "plan_sha256": sha(plan_raw),
        "training_result_sha256": result_sha,
        "stdout_sha256": sha(run_files["stdout"].read_bytes()),
        "stderr_sha256": sha(run_files["stderr"].read_bytes()),
        "process_started_sha256": sha(run_files["launch_started"].read_bytes()),
        "session_id": plan.get("session_id"),
    }
    write_once(run_files["launch_exit"], record)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", choices=sorted(RUN_NAMES), required=True)
    args = parser.parse_args()
    receipt = launch(args.run_name)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    raise SystemExit(receipt["return_code"])
