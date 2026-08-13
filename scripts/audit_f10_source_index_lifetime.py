"""H10A audit for operation-local semantic source-index lifetime."""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import queue as queue_mod
import time
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from generic_chess.core import semantic_executor as se  # noqa: E402
from generic_chess.core import search_runtime as sr  # noqa: E402
from generic_chess.core.semantic_executor import SemanticEngine  # noqa: E402
from generic_chess.core.terminal import TerminalStatus  # noqa: E402
from scripts.audit_f4_runtime_cost import corpus_specs, run_once  # noqa: E402


DEFAULT_TIMEOUT = 120.0


def _position_summary(position):
    return {
        "ruleset_fingerprint": position.ruleset_fingerprint,
        "side_to_move": position.side_to_move,
        "board": [
            None if p is None else [p.owner, p.base_type_id, p.current_type_id, p.promoted]
            for p in position.board
        ],
        "hands": [list(h.counts) for h in position.hands],
        "aux_state": [[list(k), v] for k, v in position.aux_state],
    }


def _index_signature(index):
    return [
        [
            [key[0], key[1]],
            [[source, piece.owner, piece.base_type_id, piece.current_type_id, piece.promoted] for source, piece in values],
        ]
        for key, values in index.items()
    ]


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Audit:
    def __init__(self):
        self.next_id = 0
        self.stack = []
        self.rows = []

    def begin(self, operation_type, position):
        self.next_id += 1
        summary = _position_summary(position)
        row = {
            "operation_id": self.next_id,
            "operation_type": operation_type,
            "position_summary": summary,
            "position_digest": _digest(summary),
            "source_index_build_calls": 0,
            "source_index_entries": [],
            "source_index_build_time_s": 0.0,
            "source_index_digests": [],
            "exact_index_equivalence": True,
            "patterns_visited": [],
            "board_patterns_visited": 0,
            "drop_patterns_visited": 0,
            "s0_s1_candidates": 0,
            "s3_trials": 0,
            "s3_accepted": 0,
            "legal_actions_yielded": 0,
        }
        self.stack.append(row)
        return row

    def current(self):
        return self.stack[-1] if self.stack else None

    def finish(self, row):
        if row["source_index_digests"]:
            first = row["source_index_digests"][0]
            row["exact_index_equivalence"] = all(x == first for x in row["source_index_digests"])
        row["redundant_same_position_builds"] = max(0, row["source_index_build_calls"] - 1)
        self.rows.append(row)

    def leave(self, row):
        if self.stack and self.stack[-1] is row:
            self.stack.pop()
        self.finish(row)

    def record_build(self, position, index, elapsed):
        row = self.current()
        if row is None:
            row = self.begin("OTHER", position)
            standalone = True
        else:
            standalone = False
        signature = _index_signature(index)
        row["source_index_build_calls"] += 1
        row["source_index_entries"].append(sum(len(v) for v in index.values()))
        row["source_index_build_time_s"] += elapsed
        row["source_index_digests"].append(_digest(signature))
        if standalone:
            self.leave(row)

    def snapshot(self):
        rows = [r for r in self.rows if r["source_index_build_calls"]]
        by_type = {}
        for kind in sorted({r["operation_type"] for r in rows}):
            group = [r for r in rows if r["operation_type"] == kind]
            counts = [r["source_index_build_calls"] for r in group]
            by_type[kind] = {
                "operations": len(group),
                "total_builds": sum(counts),
                "builds_per_operation_median": _quantile(counts, 0.5),
                "builds_per_operation_p90": _quantile(counts, 0.9),
                "builds_per_operation_max": max(counts, default=0),
                "redundant_builds": sum(r["redundant_same_position_builds"] for r in group),
                "build_time_s": sum(r["source_index_build_time_s"] for r in group),
                "exact_equivalence_failures": sum(not r["exact_index_equivalence"] for r in group),
            }
        return {
            "operations_with_source_index": len(rows),
            "total_source_index_builds": sum(r["source_index_build_calls"] for r in rows),
            "redundant_same_position_builds": sum(r["redundant_same_position_builds"] for r in rows),
            "redundant_build_rate": sum(r["redundant_same_position_builds"] for r in rows) / sum(r["source_index_build_calls"] for r in rows) if rows else 0.0,
            "source_index_total_time_s": sum(r["source_index_build_time_s"] for r in rows),
            "exact_equivalence_failures": sum(not r["exact_index_equivalence"] for r in rows),
            "operation_breakdown": by_type,
        }


def _quantile(values, q):
    if not values:
        return 0
    values = sorted(values)
    return values[min(len(values) - 1, int(round((len(values) - 1) * q)))]


def _install(audit):
    originals = {
        "source_index": se._sources_by_owner_type,
        "iter_bindings": SemanticEngine.iter_legal_action_bindings,
        "has_legal": SemanticEngine.has_legal_action,
        "exists_reply": SemanticEngine._exists_s3_reply,
        "attacked": SemanticEngine.is_square_attacked,
        "iter_candidates": SemanticEngine._iter_candidates,
        "trial": SemanticEngine._trial_child_if_s3_legal,
    }

    def source_index(position):
        started = time.perf_counter()
        index = originals["source_index"](position)
        audit.record_build(position, index, time.perf_counter() - started)
        return index

    def iter_bindings(engine, position, checkpoint=None):
        existing = audit.current()
        if existing is not None and existing["operation_type"] == "HAS_LEGAL_ACTION":
            for action, binding in originals["iter_bindings"](engine, position, checkpoint=checkpoint):
                existing["legal_actions_yielded"] += 1
                yield action, binding
            return
        row = audit.begin("FULL_LEGAL_BINDINGS", position)
        try:
            for action, binding in originals["iter_bindings"](engine, position, checkpoint=checkpoint):
                row["legal_actions_yielded"] += 1
                yield action, binding
        finally:
            audit.leave(row)

    def has_legal(engine, position, checkpoint=None):
        row = audit.begin("HAS_LEGAL_ACTION", position)
        try:
            return originals["has_legal"](engine, position, checkpoint=checkpoint)
        finally:
            audit.leave(row)

    def exists_reply(engine, position, checkpoint=None):
        row = audit.begin("S3_REPLY_EXISTENCE", position)
        try:
            return originals["exists_reply"](engine, position, checkpoint=checkpoint)
        finally:
            audit.leave(row)

    def attacked(engine, position, square, by_owner, checkpoint=None):
        row = audit.begin("ATTACK_QUERY", position)
        try:
            return originals["attacked"](engine, position, square, by_owner, checkpoint=checkpoint)
        finally:
            audit.leave(row)

    def iter_candidates(engine, pattern, position, checkpoint=None, sources_by_owner_type=None):
        row = audit.current()
        if row is not None:
            row["patterns_visited"].append(pattern.pattern_id)
            is_drop = any(
                engine.ir.geometry[g].kind == "drop"
                for g in pattern.geometry_ids
                if g in engine.ir.geometry
            )
            if is_drop:
                row["drop_patterns_visited"] += 1
            else:
                row["board_patterns_visited"] += 1
        for action, binding in originals["iter_candidates"](
            engine,
            pattern,
            position,
            checkpoint=checkpoint,
            sources_by_owner_type=sources_by_owner_type,
        ):
            if row is not None:
                row["s0_s1_candidates"] += 1
            yield action, binding

    def trial(engine, pattern, position, action, binding, checkpoint=None):
        row = audit.current()
        if row is not None:
            row["s3_trials"] += 1
        result = originals["trial"](engine, pattern, position, action, binding, checkpoint=checkpoint)
        if row is not None and result is not None:
            row["s3_accepted"] += 1
        return result

    se._sources_by_owner_type = source_index
    SemanticEngine.iter_legal_action_bindings = iter_bindings
    SemanticEngine.has_legal_action = has_legal
    SemanticEngine._exists_s3_reply = exists_reply
    SemanticEngine.is_square_attacked = attacked
    SemanticEngine._iter_candidates = iter_candidates
    SemanticEngine._trial_child_if_s3_legal = trial
    return originals


def _restore(originals):
    se._sources_by_owner_type = originals["source_index"]
    SemanticEngine.iter_legal_action_bindings = originals["iter_bindings"]
    SemanticEngine.has_legal_action = originals["has_legal"]
    SemanticEngine._exists_s3_reply = originals["exists_reply"]
    SemanticEngine.is_square_attacked = originals["attacked"]
    SemanticEngine._iter_candidates = originals["iter_candidates"]
    SemanticEngine._trial_child_if_s3_legal = originals["trial"]


def run_search(spec, profile):
    audit = Audit()
    originals = _install(audit)
    try:
        result = run_once(spec, profile, "timing")
    finally:
        _restore(originals)
    result["f10_audit"] = audit.snapshot()
    return result, audit.rows


def _worker(payload, out_queue):
    try:
        result, rows = run_search(payload["spec"], payload["profile"])
        out_queue.put({"ok": True, "result": result, "rows": rows})
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
    return message


def run_profile(profile, reps=5):
    results = []
    traces = []
    for spec in corpus_specs():
        safe_run({"spec": spec, "profile": profile})
        for repetition in range(reps):
            message = safe_run({"spec": spec, "profile": profile})
            result = message["result"]
            result["repetition"] = repetition + 1
            results.append(result)
            if repetition == 0:
                for row in message["rows"]:
                    row["case_id"] = spec["id"]
                    row["profile"] = profile
                    row["repetition"] = repetition + 1
                    traces.append(row)
    return results, traces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("A", "B"), required=True)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trace-output", type=Path)
    args = parser.parse_args()
    results, traces = run_profile(args.profile, args.reps)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.trace_output:
        args.trace_output.write_text("\n".join(json.dumps(row, sort_keys=True) for row in traces) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
