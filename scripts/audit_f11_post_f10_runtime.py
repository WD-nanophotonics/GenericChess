"""Post-F10 whole-search attribution for the F11 re-baseline.

This script is opt-in and monkeypatches only the isolated audit worker.  The
production search path is unchanged.  Existing F4 corpus/profile construction
is reused so F11 cannot silently drift from the certified corpus.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts import audit_f4_runtime_cost as f4  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.core import search_runtime as runtime_module  # noqa: E402
from generic_chess.core import semantic_executor as semantic_module  # noqa: E402
from generic_chess.core.search_runtime import SearchPathRuntime  # noqa: E402
from generic_chess.core.semantic_executor import SemanticEngine  # noqa: E402


class Probe:
    def __init__(self):
        self.calls = defaultdict(int)
        self.seconds = defaultdict(float)

    def timed(self, name, fn, *args, **kwargs):
        started = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            self.calls[name] += 1
            self.seconds[name] += time.perf_counter() - started

    def snapshot(self):
        return {
            name: {
                "calls": self.calls[name],
                "inclusive_s": self.seconds[name],
            }
            for name in sorted(set(self.calls) | set(self.seconds))
        }


def install_probe(probe: Probe):
    originals = {
        "iter_candidates": SemanticEngine._iter_candidates,
        "trial": SemanticEngine._trial_child_if_s3_legal,
        "attacked": SemanticEngine.is_square_attacked,
        "in_check": SemanticEngine.in_check,
        "reply": SemanticEngine._exists_s3_reply,
        "transition": SemanticEngine._transition,
        "promotion": SemanticEngine._promotion_choices,
        "path": SemanticEngine._path_holds,
        "guards": SemanticEngine._guards_hold,
        "source_index": semantic_module._sources_by_owner_type,
        "geometry": semantic_module.geometry_candidates,
        "push": SearchPathRuntime.push,
        "pop": SearchPathRuntime.pop,
        "hash_diff": runtime_module._semantic_component_diff_hash,
        "terminal": runtime_module.terminal_from_search_runtime,
        "evaluate": Evaluator.evaluate,
    }

    def iter_candidates(self, *args, **kwargs):
        probe.calls["semantic_patterns_visited"] += 1
        started = time.perf_counter()
        try:
            for item in originals["iter_candidates"](self, *args, **kwargs):
                probe.calls["s0_s1_candidates"] += 1
                yield item
        finally:
            probe.seconds["MOVE_GEN_SEMANTIC"] += time.perf_counter() - started

    def trial(self, *args, **kwargs):
        result = probe.timed("S3_TRIAL_TRANSITION", originals["trial"], self, *args, **kwargs)
        probe.calls["s3_accepted"] += int(result is not None)
        return result

    def attacked(self, *args, **kwargs):
        return probe.timed("ATTACK_CHECK", originals["attacked"], self, *args, **kwargs)

    def in_check(self, *args, **kwargs):
        return probe.timed("IN_CHECK", originals["in_check"], self, *args, **kwargs)

    def reply(self, *args, **kwargs):
        return probe.timed("S3_REPLY_EXISTENCE", originals["reply"], self, *args, **kwargs)

    def transition(self, *args, **kwargs):
        return probe.timed("S3_TRANSITION", originals["transition"], self, *args, **kwargs)

    def promotion(self, *args, **kwargs):
        return probe.timed("PROMOTION_CHOICES", originals["promotion"], self, *args, **kwargs)

    def path(self, *args, **kwargs):
        return probe.timed("PATH_PREDICATE", originals["path"], self, *args, **kwargs)

    def guards(self, *args, **kwargs):
        return probe.timed("GUARDS", originals["guards"], self, *args, **kwargs)

    def source_index(*args, **kwargs):
        return probe.timed("SOURCE_INDEX_BUILD", originals["source_index"], *args, **kwargs)

    def geometry(*args, **kwargs):
        started = time.perf_counter()
        for item in originals["geometry"](*args, **kwargs):
            probe.calls["geometry_candidates"] += 1
            yield item
        probe.seconds["GEOMETRY_CANDIDATES"] += time.perf_counter() - started

    def push(self, *args, **kwargs):
        return probe.timed("RUNTIME_PUSH", originals["push"], self, *args, **kwargs)

    def pop(self, *args, **kwargs):
        return probe.timed("RUNTIME_POP", originals["pop"], self, *args, **kwargs)

    def hash_diff(*args, **kwargs):
        return probe.timed("RUNTIME_HASH_IDENTITY", originals["hash_diff"], *args, **kwargs)

    def terminal(*args, **kwargs):
        return probe.timed("TERMINAL_PROBE", originals["terminal"], *args, **kwargs)

    def evaluate(self, *args, **kwargs):
        return probe.timed("EVALUATION_DIRECT", originals["evaluate"], self, *args, **kwargs)

    SemanticEngine._iter_candidates = iter_candidates
    SemanticEngine._trial_child_if_s3_legal = trial
    SemanticEngine.is_square_attacked = attacked
    SemanticEngine.in_check = in_check
    SemanticEngine._exists_s3_reply = reply
    SemanticEngine._transition = transition
    SemanticEngine._promotion_choices = promotion
    SemanticEngine._path_holds = path
    SemanticEngine._guards_hold = guards
    semantic_module._sources_by_owner_type = source_index
    semantic_module.geometry_candidates = geometry
    SearchPathRuntime.push = push
    SearchPathRuntime.pop = pop
    runtime_module._semantic_component_diff_hash = hash_diff
    runtime_module.terminal_from_search_runtime = terminal
    Evaluator.evaluate = evaluate
    return originals


def run_worker(payload, queue):
    try:
        probe = Probe()
        originals = install_probe(probe)
        try:
            result = f4.run_once(**payload)
        finally:
            SemanticEngine._iter_candidates = originals["iter_candidates"]
            SemanticEngine._trial_child_if_s3_legal = originals["trial"]
            SemanticEngine.is_square_attacked = originals["attacked"]
            SemanticEngine.in_check = originals["in_check"]
            SemanticEngine._exists_s3_reply = originals["reply"]
            SemanticEngine._transition = originals["transition"]
            SemanticEngine._promotion_choices = originals["promotion"]
            SemanticEngine._path_holds = originals["path"]
            SemanticEngine._guards_hold = originals["guards"]
            semantic_module._sources_by_owner_type = originals["source_index"]
            semantic_module.geometry_candidates = originals["geometry"]
            SearchPathRuntime.push = originals["push"]
            SearchPathRuntime.pop = originals["pop"]
            runtime_module._semantic_component_diff_hash = originals["hash_diff"]
            runtime_module.terminal_from_search_runtime = originals["terminal"]
            Evaluator.evaluate = originals["evaluate"]
        result["f11_probe"] = probe.snapshot()
        result["f11_structural_counts"] = dict(probe.calls)
        queue.put({"ok": True, "result": result})
    except BaseException as exc:
        queue.put({"ok": False, "error": repr(exc)})


def safe_run(spec, profile_name, timeout=60.0):
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    proc = ctx.Process(target=run_worker, args=({"spec": spec, "profile_name": profile_name, "recorder_name": "timing"}, queue))
    proc.start()
    proc.join(timeout)
    if proc.is_alive():
        proc.terminate()
        proc.join(5)
        raise RuntimeError(f"RUNTIME_SAFETY_ABORT: {spec['id']}")
    if queue.empty():
        raise RuntimeError(f"worker failed without result: {spec['id']}")
    message = queue.get()
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
    for spec in f4.corpus_specs():
        safe_run(spec, args.profile)
        for rep in range(1, args.reps + 1):
            row = safe_run(spec, args.profile)
            row["repetition"] = rep
            rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    semantic = [row["wall_s"] for row in rows if row["case_id"].startswith("semantic_")]
    print(json.dumps({"profile": args.profile, "rows": len(rows), "semantic_median_s": statistics.median(semantic), "semantic_sum_s": sum(semantic)}, indent=2))


if __name__ == "__main__":
    main()
