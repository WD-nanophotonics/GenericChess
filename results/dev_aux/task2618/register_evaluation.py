"""Write-once evaluation gate created only after complete registered training."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path

import chess

from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2618.evaluate_learners import verify_training_result


ROOT = Path(__file__).resolve().parents[3]
RUN_NAMES = ("learner-comparison-v1", "learner-comparison-v2", "learner-comparison-v3")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_once(path: Path, value: dict) -> bytes:
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
    return raw


def register(run_name: str) -> dict:
    if run_name not in RUN_NAMES:
        raise ValueError("unsupported task2618 run name")
    run_dir = ROOT / "results/dev_aux/task2618" / run_name
    plan_raw = (run_dir / "plan.json").read_bytes()
    plan = json.loads(plan_raw)
    registration_raw = (run_dir / "registration.json").read_bytes()
    registration = json.loads(registration_raw)
    if registration.get("status") != "REGISTERED_PRE_TRAINING" or registration.get("search_started") is not False:
        raise ValueError("evaluation requires the original pre-search registration")
    if registration.get("plan_sha256") != sha(plan_raw):
        raise ValueError("registered plan hash mismatch")
    if plan.get("design_revision") != int(run_name.rsplit("-v", 1)[1]):
        raise ValueError("run name and frozen design revision disagree")
    for relative, digest in plan.get("source_sha256", {}).items():
        if sha((ROOT / relative).read_bytes()) != digest:
            raise ValueError(f"registered source changed: {relative}")
    if chess.__version__ != plan.get("python_chess_version"):
        raise ValueError("python-chess runtime differs from registration")

    training_path = run_dir / "training-result.json"
    training_raw = training_path.read_bytes()
    training = json.loads(training_raw)
    arms = verify_training_result(plan, training, sha(plan_raw))
    if len(arms) != len(plan["seeds"]) * len(plan["methods"]):
        raise ValueError("training arm panel is incomplete")

    evaluation_path = run_dir / "evaluation-root-manifest.json"
    evaluation_raw = evaluation_path.read_bytes()
    if sha(evaluation_raw) != registration.get("evaluation_root_manifest_sha256"):
        raise ValueError("registered evaluation roots changed")
    evaluation_manifest = json.loads(evaluation_raw)
    roots = evaluation_manifest.get("roots", [])
    expected_eval = plan["evaluation_root_selection"]
    if (len(roots) != expected_eval["root_count"]
            or plan["evaluation"]["root_count"] != len(roots)):
        raise ValueError("evaluation root panel differs from its frozen count")
    exact_digest = sha(b"\n".join(
        json.dumps(row["record"], sort_keys=True, separators=(",", ":")).encode()
        for row in roots
    ))
    if exact_digest != expected_eval["exact_selected_records_sha256"]:
        raise ValueError("evaluation root records differ from the frozen plan")

    output_names = ("evaluation-started.json", "evaluation-games.jsonl",
                    "evaluation-queries.jsonl", "evaluation-result.json",
                    "analysis.json")
    if any((run_dir / name).exists() for name in output_names):
        raise FileExistsError("evaluation output already exists; refusing rerun or top-up")
    target = run_dir / "evaluation-registration.json"
    if target.exists():
        raise FileExistsError("evaluation registration is write-once")

    stop = SharedDeleteStopReader(ROOT)
    stop()
    session = json.loads((ROOT / ".local_agent/session.json").read_text(encoding="utf-8"))
    role = json.loads((ROOT / ".local_agent/role.json").read_text(encoding="utf-8"))
    if session.get("state") != "active" or session.get("id") != plan.get("session_id"):
        raise ValueError("evaluation registration requires the same active DEV_AUX segment")
    if role.get("role") != "DEV_AUX" or role.get("branch") != "sidemission":
        raise ValueError("evaluation registration must run in DEV_AUX/sidemission")

    value = {
        "status": "REGISTERED_PRE_TRAINING",
        "kind": "BOUND_AFTER_COMPLETE_TRAINING_BEFORE_EVALUATION",
        "registered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "session_id": session["id"],
        "plan_sha256": sha(plan_raw),
        "registration_sha256": sha(registration_raw),
        "training_result_sha256": sha(training_raw),
        "evaluation_root_manifest_sha256": sha(evaluation_raw),
        "training_complete": True,
        "evaluation_search_started": False,
        "evaluated_outcomes_used_for_root_or_parameter_selection": False,
        "source_sha256": plan["source_sha256"],
    }
    raw = write_once(target, value)
    return {
        "status": "PRE_EVALUATION_PREFLIGHT_PASS",
        "evaluation_registration_sha256": sha(raw),
        "plan_sha256": sha(plan_raw),
        "training_result_sha256": sha(training_raw),
        "evaluation_root_count": len(roots),
        "evaluation_search_started": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", choices=RUN_NAMES, required=True)
    args = parser.parse_args()
    print(json.dumps(register(args.run_name), indent=2, sort_keys=True))
