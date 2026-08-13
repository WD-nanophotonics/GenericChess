"""H8A audit and opt-in probe for one-push checked-state forwarding.

The production runtime is untouched.  In isolated workers this module traces
``_gave_check`` and the terminal check on each push, then optionally replaces
only the terminal function with an equivalent implementation consuming the
already-computed boolean from the same exact child Position.
"""

from __future__ import annotations

import argparse
import inspect
import json
import multiprocessing as mp
import queue as queue_mod
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from generic_chess.core import search_runtime as sr  # noqa: E402
from generic_chess.core import terminal as terminal_mod  # noqa: E402
from generic_chess.core.semantic_executor import SemanticEngine, semantic_engine_for  # noqa: E402
from generic_chess.core.terminal import TerminalResult, TerminalStatus  # noqa: E402
from scripts.audit_f4_runtime_cost import (  # noqa: E402
    FINGERPRINT,
    corpus_specs,
    make_session,
    run_once,
)


DEFAULT_TIMEOUT = 120.0
SEMANTIC_SPECS = tuple(spec for spec in corpus_specs() if spec["kind"] == "semantic")


class PushTrace:
    def __init__(self):
        self.push_id = 0
        self.active = {}
        self.rows = []
        self.counters = Counter()

    def begin(self, runtime):
        self.push_id += 1
        record = {
            "push_id": self.push_id,
            "runtime_id": id(runtime),
            "gave_check_called": False,
            "gave_check_result": None,
            "gave_check_s": 0.0,
            "terminal_check_called": False,
            "terminal_check_result": None,
            "terminal_check_s": 0.0,
            "has_legal_result": None,
            "terminal_status": None,
            "child_position": None,
            "terminal_position": None,
            "child_side_to_move": None,
            "same_exact_child": False,
            "same_side": False,
            "boolean_equal": False,
        }
        self.active[id(runtime)] = record
        return record

    def finish(self, runtime):
        record = self.active.pop(id(runtime), None)
        if record is None:
            return
        if record["gave_check_called"] and record["terminal_check_called"]:
            self.counters["pushes_with_both_calls"] += 1
            if record["same_exact_child"] and record["same_side"]:
                self.counters["exact_duplicate_pairs"] += 1
                if record["boolean_equal"]:
                    self.counters[
                        "duplicate_true_true" if record["gave_check_result"] else "duplicate_false_false"
                    ] += 1
                else:
                    self.counters["boolean_mismatches"] += 1
        self.rows.append(record)

    @staticmethod
    def _position_summary(position):
        if position is None:
            return None
        return {
            "ruleset_fingerprint": position.ruleset_fingerprint,
            "side_to_move": position.side_to_move,
            "board": [
                None if piece is None else {
                    "owner": piece.owner,
                    "base_type_id": piece.base_type_id,
                    "current_type_id": piece.current_type_id,
                }
                for piece in position.board
            ],
            "hands": [list(hand.counts) for hand in position.hands],
            "aux_state": [[list(key), value] for key, value in position.aux_state],
        }

    def snapshot(self):
        semantic_rows = [row for row in self.rows if row["gave_check_called"]]
        duplicate = self.counters["exact_duplicate_pairs"]
        pushes = len(semantic_rows)
        return {
            "semantic_pushes": pushes,
            "gave_check_calls": sum(row["gave_check_called"] for row in self.rows),
            "terminal_check_calls": sum(row["terminal_check_called"] for row in self.rows),
            "pushes_with_both_calls": self.counters["pushes_with_both_calls"],
            "exact_duplicate_pairs": duplicate,
            "duplicate_pair_rate": duplicate / pushes if pushes else 0.0,
            "duplicate_true_true": self.counters["duplicate_true_true"],
            "duplicate_false_false": self.counters["duplicate_false_false"],
            "boolean_mismatches": self.counters["boolean_mismatches"],
            "terminal_check_avoided_if_known_count": sum(
                row["gave_check_called"] and not row["terminal_check_called"]
                for row in self.rows
            ),
            "terminal_check_required_for_no_legal_count": sum(
                row["terminal_check_called"] and row["has_legal_result"] is False
                for row in self.rows
            ),
            "gave_check_inclusive_s": sum(row["gave_check_s"] for row in self.rows),
            "terminal_check_inclusive_s": sum(row["terminal_check_s"] for row in self.rows),
            "duplicate_second_check_s": sum(row["terminal_check_s"] for row in self.rows),
        }


def _record_check(trace, runtime, position, result, elapsed, phase):
    record = trace.active.get(id(runtime))
    if record is None:
        return
    if phase == "gave":
        record["gave_check_called"] = True
        record["gave_check_result"] = bool(result)
        record["gave_check_s"] += elapsed
        record["child_position"] = position
        record["child_side_to_move"] = position.side_to_move
    elif phase == "terminal":
        record["terminal_check_called"] = True
        record["terminal_check_result"] = bool(result)
        record["terminal_check_s"] += elapsed
        record["terminal_position"] = position
        record["same_exact_child"] = record["child_position"] == position
        record["same_side"] = record["child_side_to_move"] == position.side_to_move
        record["boolean_equal"] = record["gave_check_result"] == record["terminal_check_result"]


def _install(trace, candidate, force_recompute=False):
    original_push_impl = sr.SearchPathRuntime._push_impl
    original_gave_check = sr.SearchPathRuntime._gave_check
    original_terminal = sr.terminal_from_search_runtime
    original_engine_in_check = SemanticEngine.in_check
    current = {"runtime": None, "phase": None}

    def push_impl(runtime, action, checkpoint=None):
        record = trace.begin(runtime)
        try:
            return original_push_impl(runtime, action, checkpoint)
        finally:
            trace.finish(runtime)

    def gave_check(runtime, position, checkpoint=None):
        current["runtime"] = runtime
        current["phase"] = "gave"
        started = time.perf_counter()
        try:
            return original_gave_check(runtime, position, checkpoint)
        finally:
            current["phase"] = None
            # The engine wrapper records the exact result; elapsed is filled
            # from the outer call below when the result is available.
            record = trace.active.get(id(runtime))
            if record is not None:
                record["gave_check_s"] = max(record["gave_check_s"], time.perf_counter() - started)

    def engine_in_check(engine, position, side, checkpoint=None):
        runtime = current["runtime"]
        current_phase = current["phase"]
        started = time.perf_counter()
        result = original_engine_in_check(engine, position, side, checkpoint=checkpoint)
        elapsed = time.perf_counter() - started
        caller = inspect.currentframe().f_back.f_code.co_name
        direct_gave = current_phase == "gave" and caller == "_gave_check"
        direct_terminal = (
            current_phase == "terminal"
            and caller == "terminal_from_search_runtime"
        )
        if runtime is not None and (direct_gave or direct_terminal):
            _record_check(trace, runtime, position, result, elapsed, current_phase)
        return result

    def terminal_known(runtime, checkpoint=None, *, known_checked=None):
        record = trace.active.get(id(runtime))
        if not candidate:
            current["runtime"] = runtime
            current["phase"] = "terminal"
            try:
                return original_terminal(
                    runtime,
                    checkpoint,
                    known_checked=None if force_recompute else known_checked,
                )
            finally:
                current["phase"] = None
        if record is None or not record["gave_check_called"]:
            current["runtime"] = runtime
            current["phase"] = "terminal"
            try:
                return original_terminal(
                    runtime,
                    checkpoint,
                    known_checked=None if force_recompute else known_checked,
                )
            finally:
                current["phase"] = None
        # This is the narrow candidate: terminal logic is unchanged except
        # the exact boolean already computed for this exact child is supplied.
        current["runtime"] = runtime
        current["phase"] = "known_terminal"
        try:
            return terminal_from_runtime_known(
                runtime,
                checkpoint,
                bool(record["gave_check_result"])
                if known_checked is None else bool(known_checked),
            )
        finally:
            current["phase"] = None

    # The wrapper uses this registry only for the duration of one worker.
    def registered_push(runtime, action, checkpoint=None):
        current["runtime"] = runtime
        try:
            return push_impl(runtime, action, checkpoint)
        finally:
            current["runtime"] = None

    def terminal_from_runtime_known(runtime, checkpoint, known_checked):
        position = runtime.position
        compiled = runtime.compiled
        engine = semantic_engine_for(compiled)
        if engine is None:
            return original_terminal(runtime, checkpoint)
        has_legal = engine.has_legal_action(position, checkpoint=checkpoint)
        checked = known_checked
        if not has_legal:
            if checked:
                return TerminalResult(TerminalStatus.CHECKMATE, 1 - position.side_to_move)
            return TerminalResult(TerminalStatus.STALEMATE)
        if getattr(compiled, "repetition_policy", "draw") == "continuous_check_loss":
            perpetual = terminal_mod._runtime_perpetual_check_result(runtime)
            if perpetual is not None:
                return perpetual
        limit = getattr(compiled, "repetition_limit", compiled.support.repetition_limit if hasattr(compiled, "support") else 4)
        if runtime.occurrence_count() >= limit:
            return TerminalResult(TerminalStatus.REPETITION)
        max_ply = getattr(compiled, "max_ply", compiled.support.max_ply if hasattr(compiled, "support") else 512)
        if runtime.ply_count >= max_ply:
            return TerminalResult(TerminalStatus.MAX_PLY)
        return TerminalResult(TerminalStatus.ONGOING)

    sr.SearchPathRuntime._push_impl = registered_push
    sr.SearchPathRuntime._gave_check = gave_check
    sr.terminal_from_search_runtime = terminal_known
    SemanticEngine.in_check = engine_in_check
    return original_push_impl, original_gave_check, original_terminal, original_engine_in_check


def _restore(originals):
    original_push_impl, original_gave_check, original_terminal, original_engine_in_check = originals
    sr.SearchPathRuntime._push_impl = original_push_impl
    sr.SearchPathRuntime._gave_check = original_gave_check
    sr.terminal_from_search_runtime = original_terminal
    SemanticEngine.in_check = original_engine_in_check


def run_search(spec, profile, candidate=False, force_recompute=False):
    trace = PushTrace()
    originals = _install(trace, candidate, force_recompute)
    try:
        result = run_once(spec, profile, "timing")
    finally:
        _restore(originals)
    result["f8_trace"] = trace.snapshot()
    result["candidate"] = candidate
    return result, trace.rows


def run_search_performance_lite(spec, profile, force_recompute=False):
    """Run timing with no trace wrappers or stack inspection.

    The before mode disables the production forwarding argument so it models
    the exact duplicate-check path.  The after mode uses the current runtime
    unchanged.  This path is reserved for formal performance evidence.
    """
    original_terminal = sr.terminal_from_search_runtime
    if force_recompute:
        def terminal_without_forwarding(runtime, checkpoint=None, *, known_checked=None):
            try:
                return original_terminal(runtime, checkpoint, known_checked=None)
            except TypeError:
                return original_terminal(runtime, checkpoint)

        sr.terminal_from_search_runtime = terminal_without_forwarding
    try:
        result = run_once(spec, profile, "timing")
    finally:
        sr.terminal_from_search_runtime = original_terminal
    result["f8_trace"] = {"formal_performance_trace": False}
    result["candidate"] = False
    return result, []


def _worker(payload, queue):
    try:
        if payload.get("performance_lite", False):
            result, rows = run_search_performance_lite(
                payload["spec"], payload["profile"], payload.get("force_recompute", False)
            )
        else:
            result, rows = run_search(
                payload["spec"],
                payload["profile"],
                payload.get("candidate", False),
                payload.get("force_recompute", False),
            )
        for row in rows:
            row["child_position"] = PushTrace._position_summary(row["child_position"])
            row["terminal_position"] = PushTrace._position_summary(row["terminal_position"])
        queue.put({"ok": True, "result": result, "rows": rows})
    except BaseException as exc:  # pragma: no cover - bounded evidence worker
        queue.put({"ok": False, "error": repr(exc)})


def safe_run(payload, timeout=DEFAULT_TIMEOUT):
    context = mp.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_worker, args=(payload, queue))
    process.start()
    deadline = time.monotonic() + timeout
    message = None
    while message is None and time.monotonic() < deadline:
        try:
            message = queue.get(timeout=min(0.5, max(0.01, deadline - time.monotonic())))
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


def run_profile(profile, candidate=False, reps=5, force_recompute=False, performance_lite=False):
    results = []
    trace_rows = []
    for spec in corpus_specs():
        safe_run({"spec": spec, "profile": profile, "candidate": candidate, "force_recompute": force_recompute, "performance_lite": performance_lite})
        for repetition in range(reps):
            message = safe_run({"spec": spec, "profile": profile, "candidate": candidate, "force_recompute": force_recompute, "performance_lite": performance_lite})
            row = message["result"]
            row["repetition"] = repetition + 1
            results.append(row)
            for trace_row in message["rows"]:
                trace_row["case_id"] = spec["id"]
                trace_row["profile"] = profile
                trace_row["candidate"] = candidate
                trace_row["repetition"] = repetition + 1
                trace_rows.append(trace_row)
    return results, trace_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("A", "B"), required=True)
    parser.add_argument("--candidate", action="store_true")
    parser.add_argument("--force-recompute", action="store_true")
    parser.add_argument("--performance-lite", action="store_true")
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trace-output", type=Path)
    args = parser.parse_args()
    results, traces = run_profile(
        args.profile, args.candidate, args.reps, args.force_recompute, args.performance_lite
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.trace_output:
        args.trace_output.write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in traces) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
