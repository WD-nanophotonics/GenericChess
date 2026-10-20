"""Bounded source-execution verification of saved search receipts.

Choose the first logged receipt per (seed, endpoint, actor, complete) from one
byte-bounded log snapshot. This produces no new evaluation labels and never
writes into the evaluator's files. At most 64 searches x 2 seconds and 8192
nodes, under a separate 180-second whole-verifier stop.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import time
from pathlib import Path

from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2565.train import restore
from tools.local_agent.environment import require_identity

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2620/run-002"
OUTPUT = ROOT / "results/dev_aux/task2620/query-replay"


def write_once(path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def select(raw):
    """Only newline-terminated rows; an in-flight trailing row is excluded."""
    lines = raw.split(b"\n")
    tail = lines.pop()
    chosen = {}
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        row = json.loads(line)
        key = (row["slot"][0], row["endpoint"], row["actor"], row["complete"])
        chosen.setdefault(key, dict(line_number=number, query=row))
    return list(chosen.values()), len(tail)


def replay():
    require_identity()
    if OUTPUT.exists():
        raise FileExistsError("query verifier is one-shot; no replay/top-up")
    plan_raw = (RUN / "plan.json").read_bytes()
    plan = json.loads(plan_raw)
    for name, digest in plan["source_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError("frozen source changed: " + name)
    path = RUN / "evaluation-queries.jsonl"
    size = path.stat().st_size
    with path.open("rb") as stream:
        raw = stream.read(size)
    samples, tail_bytes = select(raw)
    if len(samples) > 64:
        raise ValueError("unexpected seed/endpoint/actor/completion cardinality")
    OUTPUT.mkdir()
    registration = dict(
        status="REGISTERED_PRE_VERIFICATION", at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        rule="First newline-terminated query per seed-index/endpoint/actor/complete flag in the captured byte prefix",
        source_prefix_bytes=len(raw), source_prefix_sha256=hashlib.sha256(raw).hexdigest(),
        excluded_inflight_tail_bytes=tail_bytes, samples=samples,
        plan_sha256=hashlib.sha256(plan_raw).hexdigest(), samples_limit=64,
        hard_seconds=180, estimated_seconds=150,
        purpose="Source-execution verification only; never extra outcome/strength samples")
    write_once(OUTPUT / "registration.json", registration)
    stop = SharedDeleteStopReader(ROOT)
    began = time.perf_counter()

    def cancel():
        stop()
        if time.perf_counter() - began >= 180:
            raise RuntimeError("query verifier reached its180-second whole-run cap")

    checked = []
    for sample in samples:
        cancel()
        q = sample["query"]
        env = restore(0, None, q["record_before"])
        receipt = TrainingSearch(plan["evaluation"]["depth"], quiet=False,
                                 q_limit=plan["evaluation"]["q_limit"]).search(
            env, Model(q["weights"]), nodes=q["effective_nodes"],
            seconds=q["effective_seconds"], seed=q["ordering_seed"], cancel=cancel)
        if env.record() != q["record_before"]:
            raise AssertionError("search mutated its full-history input")
        observed = dict(complete=receipt.complete, nodes=receipt.nodes,
                        action=receipt.action.uci() if receipt.complete else None,
                        value=receipt.value, reason=receipt.reason, seconds=receipt.seconds)
        expected = {key: q[key] for key in ("complete", "nodes", "action", "value")}
        exact = all(observed[key] == value for key, value in expected.items())
        time_sensitive = ((not q["complete"] and q["nodes"] < q["effective_nodes"])
                          or (not receipt.complete and receipt.nodes < q["effective_nodes"]))
        verdict = "MATCH" if exact else "TIME_DEPENDENT_UNRESOLVED" if time_sensitive else "MISMATCH"
        checked.append(dict(source_line=sample["line_number"], slot_index=q["slot_index"],
                            seed_index=q["slot"][0], endpoint=q["endpoint"], actor=q["actor"],
                            expected=expected, reproduced=observed, verdict=verdict))
    result = dict(status="PASS" if all(row["verdict"] == "MATCH" for row in checked)
                  else "FAIL" if any(row["verdict"] == "MISMATCH" for row in checked)
                  else "TIME_DEPENDENT_UNRESOLVED", rows=checked,
                  samples_selected=len(samples), samples_executed=len(checked),
                  matches=sum(row["verdict"] == "MATCH" for row in checked),
                  verifier_paid_nodes=sum(row["reproduced"]["nodes"] for row in checked),
                  seconds=time.perf_counter() - began,
                  evaluation_labels_added=0, no_retry_or_top_up=True,
                  limitation="This bounded first-query sample is not a full independent rerun or population test.")
    write_once(OUTPUT / "result.json", result)
    return result


if __name__ == "__main__":
    result = replay()
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
