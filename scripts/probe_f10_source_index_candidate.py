"""Opt-in H10A candidate probe for operation-local source-index reuse."""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import queue as queue_mod
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from generic_chess.core import semantic_executor as se  # noqa: E402
from generic_chess.core.semantic_executor import SemanticEngine  # noqa: E402
from scripts.audit_f4_runtime_cost import corpus_specs, run_once  # noqa: E402


DEFAULT_TIMEOUT = 120.0


def _install():
    original_source = se._sources_by_owner_type
    original_bindings = SemanticEngine.iter_legal_action_bindings
    original_has_legal = SemanticEngine.has_legal_action
    original_exists_reply = SemanticEngine._exists_s3_reply
    original_attacked = SemanticEngine.is_square_attacked
    state = {"stack": []}

    def source_index(position):
        if state["stack"]:
            top = state["stack"][-1]
            if top["kind"] in ("FULL_LEGAL_BINDINGS", "HAS_LEGAL_ACTION", "S3_REPLY_EXISTENCE") and top["position"] == position:
                return top["index"]
        return original_source(position)

    def enter(kind, position):
        row = {"kind": kind, "position": position, "index": original_source(position)}
        state["stack"].append(row)
        return row

    def leave(row):
        if state["stack"] and state["stack"][-1] is row:
            state["stack"].pop()

    def bindings(engine, position, checkpoint=None):
        if state["stack"] and state["stack"][-1]["kind"] == "HAS_LEGAL_ACTION":
            yield from original_bindings(engine, position, checkpoint=checkpoint)
            return
        row = enter("FULL_LEGAL_BINDINGS", position)
        try:
            yield from original_bindings(engine, position, checkpoint=checkpoint)
        finally:
            leave(row)

    def has_legal(engine, position, checkpoint=None):
        row = enter("HAS_LEGAL_ACTION", position)
        try:
            return original_has_legal(engine, position, checkpoint=checkpoint)
        finally:
            leave(row)

    def exists_reply(engine, position, checkpoint=None):
        row = enter("S3_REPLY_EXISTENCE", position)
        try:
            return original_exists_reply(engine, position, checkpoint=checkpoint)
        finally:
            leave(row)

    def attacked(engine, position, square, by_owner, checkpoint=None):
        # Attack queries retain their current one-build-per-query behavior.
        state["stack"].append({"kind": "ATTACK_QUERY", "position": position, "index": None})
        try:
            return original_attacked(engine, position, square, by_owner, checkpoint=checkpoint)
        finally:
            state["stack"].pop()

    se._sources_by_owner_type = source_index
    SemanticEngine.iter_legal_action_bindings = bindings
    SemanticEngine.has_legal_action = has_legal
    SemanticEngine._exists_s3_reply = exists_reply
    SemanticEngine.is_square_attacked = attacked
    return original_source, original_bindings, original_has_legal, original_exists_reply, original_attacked


def _restore(originals):
    original_source, original_bindings, original_has_legal, original_exists_reply, original_attacked = originals
    se._sources_by_owner_type = original_source
    SemanticEngine.iter_legal_action_bindings = original_bindings
    SemanticEngine.has_legal_action = original_has_legal
    SemanticEngine._exists_s3_reply = original_exists_reply
    SemanticEngine.is_square_attacked = original_attacked


def run_search(spec, profile, candidate=True):
    if not candidate:
        result = run_once(spec, profile, "timing")
        result["candidate"] = False
        return result
    originals = _install()
    try:
        result = run_once(spec, profile, "timing")
    finally:
        _restore(originals)
    result["candidate"] = True
    return result


def _worker(payload, out_queue):
    try:
        out_queue.put({"ok": True, "result": run_search(payload["spec"], payload["profile"], payload.get("candidate", True))})
    except BaseException as exc:
        out_queue.put({"ok": False, "error": repr(exc)})


def safe_run(payload, timeout=DEFAULT_TIMEOUT):
    context = mp.get_context("spawn")
    out_queue = context.Queue()
    process = context.Process(target=_worker, args=(payload, out_queue))
    process.start()
    deadline = time.monotonic() + timeout
    message = None
    while message is None and time.monotonic() < deadline:
        try:
            message = out_queue.get(timeout=min(0.5, max(0.01, deadline - time.monotonic())))
        except queue_mod.Empty:
            if not process.is_alive():
                break
    if message is None:
        if process.is_alive():
            process.terminate()
            process.join(5)
            raise RuntimeError(f"RUNTIME_SAFETY_ABORT: {payload['spec']['id']}")
        raise RuntimeError(f"worker failed without result: {payload['spec']['id']}")
    process.join(5)
    if not message["ok"]:
        raise RuntimeError(message["error"])
    return message["result"]


def run_profile(profile, reps=5, candidate=True):
    rows = []
    for spec in corpus_specs():
        safe_run({"spec": spec, "profile": profile, "candidate": candidate})
        for repetition in range(reps):
            row = safe_run({"spec": spec, "profile": profile, "candidate": candidate})
            row["case_id"] = spec["id"]
            row["repetition"] = repetition + 1
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("A", "B"), required=True)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    rows = run_profile(args.profile, args.reps, candidate=not args.baseline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
