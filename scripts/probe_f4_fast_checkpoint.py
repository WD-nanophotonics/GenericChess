"""Probe the one F4 candidate without changing product source.

The candidate is an audit-only monkeypatch: for non-interactive fixed-node
search it performs the same max-node check directly and delegates all
interactive cancellation/deadline behavior to the existing Budget.check.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from audit_f4_runtime_cost import (  # noqa: E402
    corpus_specs,
    run_once,
)
from generic_chess.ai.alphabeta.search import _Context  # noqa: E402
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.ai.alphabeta.search import SearchAborted  # noqa: E402


def _candidate_worker(payload, queue):
    original = _Context.checkpoint

    def fast_checkpoint(context):
        budget = context.budget
        total = context.stats.nodes + context.stats.qnodes
        if budget._max_nodes is not None and total >= budget._max_nodes:
            raise SearchAborted("node_limit")
        if budget._interactive:
            budget.check(context.stats, force=True)

    _Context.checkpoint = fast_checkpoint
    try:
        queue.put({"ok": True, "result": run_once(**payload)})
    except BaseException as exc:
        queue.put({"ok": False, "error": repr(exc)})
    finally:
        _Context.checkpoint = original


def safe_candidate(payload, timeout=60.0):
    context = mp.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_candidate_worker, args=(payload, queue))
    process.start()
    process.join(timeout)
    if process.is_alive():
        process.terminate()
        process.join(5)
        raise RuntimeError(f"RUNTIME_SAFETY_ABORT: {payload['spec']['id']}")
    message = queue.get(timeout=5)
    if not message["ok"]:
        raise RuntimeError(message["error"])
    return message["result"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("A", "B"), required=True)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for spec in corpus_specs():
        safe_candidate({"spec": spec, "profile_name": args.profile, "recorder_name": "timing"})
        for repetition in range(args.reps):
            row = safe_candidate({"spec": spec, "profile_name": args.profile, "recorder_name": "timing"})
            row["repetition"] = repetition + 1
            row["candidate"] = "fast_noninteractive_checkpoint"
            rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
