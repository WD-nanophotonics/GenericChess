"""Read-only full-action audit of one private live-log prefix, not run closure."""
from __future__ import annotations

import datetime
import hashlib
import json
import time
from pathlib import Path

from results.dev_aux.task2618.evaluate_learners import verify_training_result
from results.dev_aux.task2620.audit import verify_query_stream
from tools.local_agent.environment import require_identity

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2620/run-002"
PRIVATE = ROOT / ".local_agent/handoff-20261020/prefix-audit"


def audit_prefix():
    require_identity()
    if PRIVATE.exists():
        raise FileExistsError("prefix capture is write-once")
    PRIVATE.mkdir()
    began = time.perf_counter()
    path = RUN / "evaluation-queries.jsonl"
    limit = path.stat().st_size
    with path.open("rb") as stream:
        raw = stream.read(limit)
    length = raw.rfind(b"\n") + 1
    saved = PRIVATE / "queries.jsonl"
    saved.write_bytes(raw[:length])
    captured = datetime.datetime.now(datetime.timezone.utc).isoformat()
    plan_raw = (RUN / "plan.json").read_bytes()
    plan = json.loads(plan_raw)
    for relative, digest in plan["source_sha256"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("frozen source changed: " + relative)
    training_plan_raw = (ROOT / plan["training_plan_path"]).read_bytes()
    training_raw = (RUN / "training-result.json").read_bytes()
    if hashlib.sha256(training_plan_raw).hexdigest() != plan["training_plan_sha256"]:
        raise ValueError("training plan changed")
    if hashlib.sha256(training_raw).hexdigest() != plan["training_result_sha256"]:
        raise ValueError("training result changed")
    training = json.loads(training_raw)
    arms = verify_training_result(json.loads(training_plan_raw), training,
                                  hashlib.sha256(training_plan_raw).hexdigest())
    roots_raw = (RUN / "evaluation-root-manifest.json").read_bytes()
    if hashlib.sha256(roots_raw).hexdigest() != plan["evaluation_root_manifest_sha256"]:
        raise ValueError("root manifest changed")
    roots = {row["family"]: row["record"] for row in json.loads(roots_raw)["roots"]}
    slots = [tuple(slot) for slot in plan["evaluation"]["ordered_slots"]]
    initials = {arm["seed"]: arm["initial_weights"] for arm in training["arms"]}
    per_slot, queries = verify_query_stream(plan, slots, roots, arms, initials, saved)
    result = dict(status="PREFIX_REPLAY_PASS", captured_at=captured,
                  prefix_bytes=length, inflight_tail_excluded_bytes=len(raw)-length,
                  prefix_sha256=hashlib.sha256(raw[:length]).hexdigest(),
                  source_plan_sha256=hashlib.sha256(plan_raw).hexdigest(),
                  query_rows=queries, slots_touched=len(per_slot),
                  last_slot=max(per_slot) if per_slot else None,
                  nodes=sum(row["nodes"] for row in per_slot.values()),
                  seconds=time.perf_counter()-began, run_complete_claimed=False,
                  final_outcome_or_strength_claimed=False,
                  scope="All captured action histories and actor/weight/node/time contracts; last slot may be incomplete. Final closed-stream audit still required.")
    with (RUN / "prefix-audit.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(audit_prefix(), indent=2, sort_keys=True))
