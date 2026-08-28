"""F4 whole-search attribution harness with bounded worker isolation.

The harness is intentionally opt-in and lives outside the product search
path.  Each run is isolated in a spawned worker with a controller timeout so
an expensive semantic case cannot hang the audit process.
"""

from __future__ import annotations

import argparse
import cProfile
import json
import multiprocessing as mp
import os
import pstats
import sys
import time
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from ai_fixtures import build_4x4_rooks  # noqa: E402
from generic_chess.ai.alphabeta.search import run_root_search  # noqa: E402
from generic_chess.ai.alphabeta.statistics import SearchStatistics  # noqa: E402
from generic_chess.ai.alphabeta.transposition import TranspositionTable  # noqa: E402
from generic_chess.ai.alphabeta.tuning import SearchTuning  # noqa: E402
from generic_chess.ai.audit_instrumentation import (  # noqa: E402
    NullAuditRecorder,
)
from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.core.search_runtime import SearchPathRuntime  # noqa: E402
from generic_chess.session.session import GameSession  # noqa: E402


FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
DEFAULT_TIMEOUT = 60.0


class ExclusiveAuditRecorder:
    """Timing recorder with inclusive and stack-subtracted exclusive totals."""

    __slots__ = ("counts", "inclusive", "exclusive", "_stack")

    def __init__(self) -> None:
        self.counts: dict[str, int] = defaultdict(int)
        self.inclusive: dict[str, float] = defaultdict(float)
        self.exclusive: dict[str, float] = defaultdict(float)
        self._stack: list[tuple[str, float, float]] = []

    def count(self, key, amount: int = 1) -> None:
        name = key.name if hasattr(key, "name") else str(key)
        self.counts[name] += amount

    @contextmanager
    def time_block(self, key):
        name = key.name if hasattr(key, "name") else str(key)
        started = time.perf_counter()
        self._stack.append((name, started, 0.0))
        try:
            yield
        finally:
            _name, _started, child_time = self._stack.pop()
            elapsed = time.perf_counter() - started
            self.inclusive[name] += elapsed
            self.exclusive[name] += elapsed - child_time
            if self._stack:
                parent_name, parent_started, parent_child = self._stack[-1]
                self._stack[-1] = (parent_name, parent_started, parent_child + elapsed)

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        keys = set(self.counts) | set(self.inclusive) | set(self.exclusive)
        return {
            name: {
                "calls": self.counts.get(name, 0),
                "inclusive_s": self.inclusive.get(name, 0.0),
                "exclusive_s": self.exclusive.get(name, 0.0),
            }
            for name in sorted(keys)
        }


def corpus_specs() -> list[dict[str, object]]:
    return [
        {"id": "legacy_draw_root", "kind": "legacy", "plies": 0, "seed": 0},
        {
            "id": "continuous_check_prefix",
            "kind": "continuous",
            "prefix": ["a1-a2", "b3-b2", "a2-a1", "b2-b3"],
        },
        {"id": "semantic_prefix_0", "kind": "semantic", "plies": 0, "seed": 0},
        {"id": "semantic_prefix_1", "kind": "semantic", "plies": 1, "seed": 1},
        {"id": "semantic_prefix_2", "kind": "semantic", "plies": 2, "seed": 2},
        {"id": "semantic_prefix_3", "kind": "semantic", "plies": 3, "seed": 3},
    ]


def make_session(spec: dict[str, object]):
    if spec["kind"] == "legacy":
        return GameSession(build_4x4_rooks())
    if spec["kind"] == "continuous":
        from dataclasses import replace

        compiled = replace(build_4x4_rooks(), repetition_policy="continuous_check_loss")
        session = GameSession(compiled)
        for text in spec["prefix"]:
            action = next(action for action in session.legal_actions() if str(action) == text)
            session.submit(action)
        return session
    from generic_chess.learning.round5_corrective_r1 import SearchSemanticCompiled
    from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset
    from generic_chess.rules.compiler import compile_semantic_ruleset

    semantic = compile_semantic_ruleset(build_semantic_shogi_ruleset())
    assert semantic.ruleset_fingerprint == FINGERPRINT
    compiled = SearchSemanticCompiled(
        ir=semantic.ir,
        _legacy_compiled=semantic._legacy_compiled,
        support=semantic.support,
    )
    session = GameSession(compiled)
    for ply in range(int(spec["plies"])):
        actions = sorted(session.legal_actions(), key=str)
        session.submit(actions[(int(spec["seed"]) + 3 * ply) % len(actions)])
    return session


def profile_config(name: str) -> dict[str, object]:
    if name == "A":
        return {
            "name": "A",
            "max_depth": 2,
            "max_nodes": 512,
            "quiescence_max_depth": 0,
            "use_tt": True,
            "use_ordering": False,
            "tuning": SearchTuning(use_root_tactical=False),
        }
    return {
        "name": "B",
        "max_depth": 2,
        "max_nodes": 256,
        "quiescence_max_depth": 4,
        "use_tt": True,
        "use_ordering": True,
        "tuning": SearchTuning(),
    }


def _timed_runtime_methods():
    original_push = SearchPathRuntime.push
    original_pop = SearchPathRuntime.pop
    totals = {"push_s": 0.0, "pop_s": 0.0, "push_calls": 0, "pop_calls": 0}

    def push(runtime, *args, **kwargs):
        started = time.perf_counter()
        try:
            return original_push(runtime, *args, **kwargs)
        finally:
            totals["push_s"] += time.perf_counter() - started
            totals["push_calls"] += 1

    def pop(runtime, *args, **kwargs):
        started = time.perf_counter()
        try:
            return original_pop(runtime, *args, **kwargs)
        finally:
            totals["pop_s"] += time.perf_counter() - started
            totals["pop_calls"] += 1

    SearchPathRuntime.push = push
    SearchPathRuntime.pop = pop
    return original_push, original_pop, totals


def run_once(spec: dict[str, object], profile_name: str, recorder_name: str, profile_path: str | None = None):
    session = make_session(spec)
    compiled = session.compiled
    legacy = getattr(compiled, "_legacy_compiled", compiled)
    config = EvaluationConfig()
    evaluator = Evaluator(legacy, build_ruleset_profile(legacy, config), config)
    config_data = profile_config(profile_name)
    recorder = NullAuditRecorder() if recorder_name == "null" else ExclusiveAuditRecorder()
    stats = SearchStatistics()
    original_push, original_pop, runtime_timing = _timed_runtime_methods()
    profiler = cProfile.Profile() if profile_path else None
    started = time.perf_counter()
    try:
        if profiler:
            profiler.enable()
        result = run_root_search(
            session.state,
            compiled,
            evaluator,
            TranspositionTable(),
            SearchLimits(
                max_depth=int(config_data["max_depth"]),
                max_nodes=int(config_data["max_nodes"]),
                quiescence_max_depth=int(config_data["quiescence_max_depth"]),
            ),
            None,
            stats,
            use_tt=bool(config_data["use_tt"]),
            use_ordering=bool(config_data["use_ordering"]),
            tuning=config_data["tuning"],
            _history_witnesses=session._search_witnesses,
            recorder=recorder,
        )
        if profiler:
            profiler.disable()
            profiler.dump_stats(profile_path)
    finally:
        SearchPathRuntime.push = original_push
        SearchPathRuntime.pop = original_pop
    elapsed = time.perf_counter() - started
    audit = recorder.snapshot() if hasattr(recorder, "snapshot") else {}
    return {
        "case_id": spec["id"],
        "profile": profile_name,
        "recorder": recorder_name,
        "wall_s": elapsed,
        "action": str(result[0]) if result[0] is not None else None,
        "score": result[1],
        "pv": [str(action) for action in result[2]],
        "nodes": stats.nodes,
        "qnodes": stats.qnodes,
        "completed_depth": stats.completed_depth,
        "termination_reason": result[3],
        "terminal_status": session.state.terminal_status.status.value,
        "audit": audit,
        "runtime": {
            "push_s": runtime_timing["push_s"],
            "pop_s": runtime_timing["pop_s"],
            "push_calls": runtime_timing["push_calls"],
            "pop_calls": runtime_timing["pop_calls"],
            "runtime_pushes": stats.runtime_pushes,
            "runtime_pops": stats.runtime_pops,
            "search_key_calls": stats.runtime_search_key_calls,
            "snapshot_updates": stats.runtime_snapshot_updates,
            "history_context_updates": stats.runtime_history_context_updates,
        },
        "search": {
            "legal_actions_generated": stats.legal_actions_generated,
            "successors_materialized": stats.successors_materialized,
            "successors_searched": stats.successors_searched,
            "terminal_results_computed": stats.terminal_results_computed,
            "terminal_cache_hits": stats.terminal_cache_hits,
            "position_keys_computed": stats.position_keys_computed,
            "position_key_cache_hits": stats.position_key_cache_hits,
            "tt_probes": stats.tt_probes,
            "tt_hits": stats.tt_hits,
            "tt_cutoffs": stats.tt_cutoffs,
            "tt_stores": stats.tt_stores,
        },
    }


def _worker(payload: dict[str, object], queue) -> None:
    try:
        queue.put({"ok": True, "result": run_once(**payload)})
    except BaseException as exc:  # pragma: no cover - controller evidence
        queue.put({"ok": False, "error": repr(exc)})


def safe_run(payload: dict[str, object], timeout: float = DEFAULT_TIMEOUT) -> dict[str, object]:
    context = mp.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_worker, args=(payload, queue))
    process.start()
    process.join(timeout)
    if process.is_alive():
        process.terminate()
        process.join(5)
        raise RuntimeError(f"RUNTIME_SAFETY_ABORT: {payload['spec']['id']}")
    if queue.empty():
        raise RuntimeError(f"worker failed without result: {payload['spec']['id']}")
    message = queue.get()
    if not message["ok"]:
        raise RuntimeError(message["error"])
    return message["result"]


def run_corpus(profile_name: str, recorder_name: str, reps: int, warmup: bool = True):
    rows = []
    for spec in corpus_specs():
        if warmup:
            safe_run({"spec": spec, "profile_name": profile_name, "recorder_name": recorder_name})
        for repetition in range(reps):
            row = safe_run({"spec": spec, "profile_name": profile_name, "recorder_name": recorder_name})
            row["repetition"] = repetition + 1
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("A", "B"))
    parser.add_argument("--recorder", choices=("null", "timing"), default="timing")
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cprofile", type=Path)
    args = parser.parse_args()
    if args.cprofile:
        spec = next(spec for spec in corpus_specs() if spec["kind"] == "semantic")
        result = safe_run({
            "spec": spec,
            "profile_name": args.profile or "A",
            "recorder_name": args.recorder,
            "profile_path": str(args.cprofile),
        })
    else:
        result = run_corpus(args.profile or "A", args.recorder, args.reps)
    payload = result
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
