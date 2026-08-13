"""H9A audit for terminal legal-existence work reused by search legal generation.

This module is diagnostic-only.  It traces the existing terminal probe and the
later runtime legal-action materialization in isolated workers; it does not
change production source or cache semantics.
"""
from __future__ import annotations

import argparse
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

from generic_chess.core import search_runtime as sr  # noqa: E402
from generic_chess.core.semantic_executor import SemanticEngine  # noqa: E402
from generic_chess.core.terminal import TerminalStatus  # noqa: E402
from scripts.audit_f4_runtime_cost import corpus_specs, run_once  # noqa: E402


DEFAULT_TIMEOUT = 120.0


def _status(value):
    return getattr(value, "value", getattr(value, "name", str(value)))


def _action_key(action):
    return {
        "pattern_id": getattr(action, "pattern_id", None),
        "geometry_id": getattr(action, "geometry_id", None),
        "actor_type": getattr(action, "actor_type", None),
        "source": getattr(action, "source", None),
        "target": getattr(action, "target", None),
        "promotion_target": getattr(action, "promotion_target_id", None),
    }


def _binding_key(binding):
    return {
        "pattern_id": getattr(getattr(binding, "pattern", None), "pattern_id", None),
        "geometry_id": getattr(binding, "geometry_id", None),
        "actor_type": getattr(binding, "actor_type", None),
        "source": getattr(binding, "source", None),
        "target": getattr(binding, "target", None),
        "promotion_target": getattr(binding, "promotion_target_id", None),
    }


def _position_summary(position):
    if position is None:
        return None
    return {
        "ruleset_fingerprint": position.ruleset_fingerprint,
        "side_to_move": position.side_to_move,
        "board": [
            None if p is None else {
                "owner": p.owner,
                "base_type_id": p.base_type_id,
                "current_type_id": p.current_type_id,
                "promoted": p.promoted,
            }
            for p in position.board
        ],
        "hands": [list(h.counts) for h in position.hands],
        "aux_state": [[list(k), v] for k, v in position.aux_state],
    }


class Trace:
    def __init__(self):
        self.next_id = 0
        self.active = {}
        self.rows = []
        self.counters = Counter()

    def begin(self, runtime):
        self.next_id += 1
        row = {
            "push_id": self.next_id,
            "runtime_id": id(runtime),
            "parent_position": _position_summary(runtime.position),
            "child_position": None,
            "child_side_to_move": None,
            "terminal_status": None,
            "terminal_probe_started": False,
            "terminal_probe_calls": 0,
            "terminal_probe_has_legal": None,
            "terminal_probe_s": 0.0,
            "terminal_probe_first_action": None,
            "terminal_generated_action_keys": [],
            "terminal_patterns_visited": [],
            "terminal_type_ids_visited": [],
            "terminal_sources_visited": [],
            "terminal_geometry_ids_visited": [],
            "terminal_geometry_candidates": 0,
            "terminal_s0_s1_candidates": 0,
            "terminal_s3_trials": 0,
            "terminal_s3_accepted": 0,
            "terminal_candidate_keys": [],
            "terminal_trial_keys": [],
            "terminal_trial_times_s": [],
            "full_legal_requested_before_pop": False,
            "full_legal_action_count": None,
            "full_first_action_rank": None,
            "full_patterns_visited": [],
            "full_type_ids_visited": [],
            "full_sources_visited": [],
            "full_geometry_ids_visited": [],
            "full_geometry_candidates": 0,
            "full_s0_s1_candidates": 0,
            "full_s3_trials": 0,
            "full_s3_accepted": 0,
            "full_candidate_keys": [],
            "full_trial_keys": [],
            "full_trial_times_s": [],
            "full_legal_actions": [],
            "full_generated_action_keys": [],
            "full_legal_s": 0.0,
            "popped": False,
            "exception": None,
        }
        self.active.setdefault(id(runtime), []).append(row)
        return row

    def current(self, runtime):
        stack = self.active.get(id(runtime), ())
        return stack[-1] if stack else None

    @staticmethod
    def _phase_keys(row, phase, kind):
        return row[f"{phase}_{kind}_keys"]

    def finish(self, runtime, row, exc=None):
        row["exception"] = repr(exc) if exc else None
        row["popped"] = exc is None
        row["child_position"] = _position_summary(runtime.position) if exc is None else row["child_position"]
        if row["child_position"] is not None:
            row["child_side_to_move"] = row["child_position"]["side_to_move"]
        self._derive(row)
        self.rows.append(row)

    def close_pop(self, runtime):
        stack = self.active.get(id(runtime), [])
        if not stack:
            return
        row = stack.pop()
        if not stack:
            self.active.pop(id(runtime), None)
        row["popped"] = True
        self._derive(row)
        self.rows.append(row)

    def close_failed(self, runtime, row):
        stack = self.active.get(id(runtime), [])
        if stack and stack[-1] is row:
            stack.pop()
        if not stack:
            self.active.pop(id(runtime), None)
        row["popped"] = False
        self._derive(row)
        self.rows.append(row)

    def _derive(self, row):
        a = row["terminal_candidate_keys"]
        b = row["full_candidate_keys"]
        trial_a = row["terminal_trial_keys"]
        trial_b = row["full_trial_keys"]
        lcp = 0
        for x, y in zip(a, b):
            if x != y:
                break
            lcp += 1
        trial_lcp = 0
        for x, y in zip(trial_a, trial_b):
            if x != y:
                break
            trial_lcp += 1
        row["repeated_prefix_candidate_count"] = lcp
        row["repeated_prefix_s3_trial_count"] = trial_lcp
        row["repeated_prefix_terminal_s"] = sum(row["terminal_trial_times_s"][:trial_lcp])
        row["repeated_prefix_full_s"] = sum(row["full_trial_times_s"][:trial_lcp])
        row["repeated_candidate_bindings"] = lcp
        row["reuse_eligible"] = bool(
            row["terminal_status"] == _status(TerminalStatus.ONGOING)
            and row["full_legal_requested_before_pop"]
        )
        if row["terminal_status"] == _status(TerminalStatus.ONGOING):
            row["classification"] = (
                "ONGOING_FULL_LEGAL_LATER"
                if row["full_legal_requested_before_pop"]
                else "ONGOING_NO_FULL_LEGAL_BEFORE_POP"
            )
        elif row["terminal_probe_has_legal"] is False:
            row["classification"] = "TERMINAL_NO_LEGAL"
        else:
            row["classification"] = "TERMINAL_OTHER"

    def snapshot(self):
        rows = [r for r in self.rows if r["child_position"] is not None]
        semantic = rows
        by_class = Counter(r["classification"] for r in semantic)
        eligible = [r for r in semantic if r["reuse_eligible"]]
        return {
            "semantic_pushes": len(semantic),
            "terminal_probe_calls": sum(r["terminal_probe_calls"] for r in semantic),
            "terminal_no_legal": by_class["TERMINAL_NO_LEGAL"],
            "terminal_other": by_class["TERMINAL_OTHER"],
            "ongoing_full_legal_later": by_class["ONGOING_FULL_LEGAL_LATER"],
            "ongoing_no_full_legal_before_pop": by_class["ONGOING_NO_FULL_LEGAL_BEFORE_POP"],
            "reuse_eligible_pushes": len(eligible),
            "reuse_eligible_rate": len(eligible) / len([r for r in semantic if r["terminal_status"] == _status(TerminalStatus.ONGOING)]) if any(r["terminal_status"] == _status(TerminalStatus.ONGOING) for r in semantic) else 0.0,
            "terminal_geometry_candidates": sum(r["terminal_geometry_candidates"] for r in semantic),
            "full_geometry_candidates": sum(r["full_geometry_candidates"] for r in semantic),
            "repeated_prefix_candidate_count": sum(r["repeated_prefix_candidate_count"] for r in eligible),
            "repeated_prefix_s3_trial_count": sum(r["repeated_prefix_s3_trial_count"] for r in eligible),
            "repeated_prefix_terminal_s": sum(r["repeated_prefix_terminal_s"] for r in eligible),
            "repeated_prefix_full_s": sum(r["repeated_prefix_full_s"] for r in eligible),
            "terminal_probe_s": sum(r["terminal_probe_s"] for r in semantic),
            "full_legal_s": sum(r["full_legal_s"] for r in eligible),
            "terminal_s3_trials": sum(r["terminal_s3_trials"] for r in semantic),
            "full_s3_trials": sum(r["full_s3_trials"] for r in eligible),
            "full_legal_actions": sum(r["full_legal_action_count"] or 0 for r in semantic),
            "first_legal_rank_median": _quantile([r["full_first_action_rank"] for r in eligible if r["full_first_action_rank"] is not None], 0.5),
            "first_legal_rank_p90": _quantile([r["full_first_action_rank"] for r in eligible if r["full_first_action_rank"] is not None], 0.9),
            "first_legal_rank_max": max((r["full_first_action_rank"] for r in eligible if r["full_first_action_rank"] is not None), default=None),
        }


def _quantile(values, q):
    if not values:
        return None
    vals = sorted(values)
    idx = min(len(vals) - 1, max(0, int(round((len(vals) - 1) * q))))
    return vals[idx]


def _install(trace):
    originals = {
        "push_impl": sr.SearchPathRuntime._push_impl,
        "pop": sr.SearchPathRuntime.pop,
        "legal_actions": sr.SearchPathRuntime.legal_actions,
        "terminal": sr.terminal_from_search_runtime,
        "has_legal": SemanticEngine.has_legal_action,
        "iter_bindings": SemanticEngine.iter_legal_action_bindings,
        "iter_candidates": SemanticEngine._iter_candidates,
        "trial": SemanticEngine._trial_child_if_s3_legal,
    }
    state = {"runtime": None, "phase": None}

    def push_impl(runtime, action, checkpoint=None):
        row = trace.begin(runtime)
        state["runtime"] = runtime
        try:
            result = originals["push_impl"](runtime, action, checkpoint)
            row["child_position"] = _position_summary(runtime.position)
            row["child_side_to_move"] = runtime.position.side_to_move
            row["terminal_status"] = _status(runtime.terminal_status.status)
            return result
        except BaseException as exc:
            trace.close_failed(runtime, row)
            raise
        finally:
            state["runtime"] = None

    def pop(runtime):
        result = originals["pop"](runtime)
        trace.close_pop(runtime)
        return result

    def legal_actions(runtime, checkpoint=None):
        row = trace.current(runtime)
        active = row is not None and runtime._legal_cache is None and _status(runtime.terminal_status.status) == _status(TerminalStatus.ONGOING)
        previous = state["phase"]
        started = None
        if active:
            row["full_legal_requested_before_pop"] = True
            state["runtime"] = runtime
            state["phase"] = "full"
            started = time.perf_counter()
        try:
            result = originals["legal_actions"](runtime, checkpoint)
            if active:
                row["full_legal_s"] += time.perf_counter() - started
                row["full_legal_action_count"] = len(result)
                row["full_legal_actions"] = [_action_key(a) for a in result]
                if row["terminal_probe_first_action"] is not None:
                    try:
                        row["full_first_action_rank"] = row["full_generated_action_keys"].index(row["terminal_probe_first_action"]) + 1
                    except ValueError:
                        row["full_first_action_rank"] = None
            return result
        finally:
            state["phase"] = previous
            if previous is None:
                state["runtime"] = None

    def terminal(runtime, checkpoint=None):
        previous = state["phase"]
        state["runtime"] = runtime
        state["phase"] = "terminal"
        row = trace.current(runtime)
        if row is not None:
            row["terminal_probe_started"] = True
        try:
            result = originals["terminal"](runtime, checkpoint)
            if row is not None:
                row["terminal_status"] = _status(result.status)
            return result
        finally:
            state["phase"] = previous
            if previous is None:
                state["runtime"] = None

    def has_legal(engine, position, checkpoint=None):
        row = trace.current(state["runtime"]) if state["runtime"] is not None else None
        is_terminal = state["phase"] == "terminal" and row is not None
        if is_terminal:
            row["terminal_probe_calls"] += 1
        started = time.perf_counter()
        result = originals["has_legal"](engine, position, checkpoint=checkpoint)
        if is_terminal:
            row["terminal_probe_has_legal"] = bool(result)
            row["terminal_probe_s"] += time.perf_counter() - started
        return result

    def iter_bindings(engine, position, checkpoint=None):
        row = trace.current(state["runtime"]) if state["runtime"] is not None else None
        phase = state["phase"]
        iterator = originals["iter_bindings"](engine, position, checkpoint=checkpoint)
        for action, binding in iterator:
            if row is not None and phase in ("terminal", "full"):
                key = _action_key(action)
                row[f"{phase}_generated_action_keys"].append(key)
                if phase == "terminal" and row["terminal_probe_first_action"] is None:
                    row["terminal_probe_first_action"] = key
                row[f"{phase}_first_action_seen"] = True
            yield action, binding

    def iter_candidates(engine, pattern, position, checkpoint=None, sources_by_owner_type=None):
        row = trace.current(state["runtime"]) if state["runtime"] is not None else None
        phase = state["phase"]
        if row is not None and phase in ("terminal", "full"):
            row[f"{phase}_patterns_visited"].append(pattern.pattern_id)
            row[f"{phase}_type_ids_visited"].extend(pattern.type_ids)
            row[f"{phase}_geometry_ids_visited"].extend(pattern.geometry_ids)
        for action, binding in originals["iter_candidates"](
            engine,
            pattern,
            position,
            checkpoint=checkpoint,
            sources_by_owner_type=sources_by_owner_type,
        ):
            if row is not None and phase in ("terminal", "full"):
                key = _binding_key(binding)
                row[f"{phase}_candidate_keys"].append(key)
                row[f"{phase}_geometry_candidates"] += 1
                row[f"{phase}_s0_s1_candidates"] += 1
                if binding.source is not None:
                    row[f"{phase}_sources_visited"].append(binding.source)
            yield action, binding

    def trial(engine, pattern, position, action, binding, checkpoint=None):
        row = trace.current(state["runtime"]) if state["runtime"] is not None else None
        phase = state["phase"]
        if row is not None and phase in ("terminal", "full"):
            row[f"{phase}_s3_trials"] += 1
            row[f"{phase}_trial_keys"].append(_binding_key(binding))
        started = time.perf_counter()
        result = originals["trial"](engine, pattern, position, action, binding, checkpoint=checkpoint)
        if row is not None and phase in ("terminal", "full") and result is not None:
            row[f"{phase}_s3_accepted"] += 1
        if row is not None and phase in ("terminal", "full"):
            row[f"{phase}_trial_times_s"].append(time.perf_counter() - started)
        return result

    sr.SearchPathRuntime._push_impl = push_impl
    sr.SearchPathRuntime.pop = pop
    sr.SearchPathRuntime.legal_actions = legal_actions
    sr.terminal_from_search_runtime = terminal
    SemanticEngine.has_legal_action = has_legal
    SemanticEngine.iter_legal_action_bindings = iter_bindings
    SemanticEngine._iter_candidates = iter_candidates
    SemanticEngine._trial_child_if_s3_legal = trial
    return originals


def _restore(originals):
    sr.SearchPathRuntime._push_impl = originals["push_impl"]
    sr.SearchPathRuntime.pop = originals["pop"]
    sr.SearchPathRuntime.legal_actions = originals["legal_actions"]
    sr.terminal_from_search_runtime = originals["terminal"]
    SemanticEngine.has_legal_action = originals["has_legal"]
    SemanticEngine.iter_legal_action_bindings = originals["iter_bindings"]
    SemanticEngine._iter_candidates = originals["iter_candidates"]
    SemanticEngine._trial_child_if_s3_legal = originals["trial"]


def run_search(spec, profile):
    trace = Trace()
    originals = _install(trace)
    try:
        result = run_once(spec, profile, "timing")
    finally:
        _restore(originals)
    result["f9_trace"] = trace.snapshot()
    return result, trace.rows


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
            row = message["result"]
            row["repetition"] = repetition + 1
            results.append(row)
            for trace_row in message["rows"]:
                trace_row["case_id"] = spec["id"]
                trace_row["profile"] = profile
                trace_row["repetition"] = repetition + 1
                traces.append(trace_row)
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
