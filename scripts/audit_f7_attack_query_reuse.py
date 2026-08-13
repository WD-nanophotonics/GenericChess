"""H7A audit and opt-in probe for exact semantic attack-query reuse.

This file never changes the production semantic executor.  Formal workers
temporarily wrap ``SemanticEngine.is_square_attacked`` and ``in_check`` in a
spawned process.  Query identity uses exact immutable ``Position`` equality
plus ruleset fingerprint, square, and attacking owner; no digest is used as
an authority.
"""

from __future__ import annotations

import argparse
import inspect
import json
import multiprocessing as mp
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from generic_chess.core import semantic_executor as se  # noqa: E402
from generic_chess.core.semantic_executor import SemanticEngine  # noqa: E402
from scripts.audit_f4_runtime_cost import (  # noqa: E402
    FINGERPRINT,
    corpus_specs,
    make_session,
    run_once,
)


DEFAULT_TIMEOUT = 120.0
SEMANTIC_PREFIXES = tuple(
    spec for spec in corpus_specs() if spec["kind"] == "semantic"
)


def exact_query_key(position, square: int, by_owner: int):
    """Authoritative audit key; Position equality covers all observable fields."""
    return (position.ruleset_fingerprint, position, int(square), int(by_owner))


def position_digest(position):
    """Non-authoritative bucket digest for reporting only."""
    return hash(position)


def classify_callsite():
    names = {frame.function for frame in inspect.stack(context=0)[1:]}
    if "_gave_check" in names:
        return "RUNTIME_GAVE_CHECK"
    if "_violates_postconditions" in names:
        return "S4_OPPONENT_CHECKED"
    if "_exists_s3_reply" in names:
        return "S4_REPLY_PROBE"
    if "_trial_child_if_s3_legal" in names:
        return "S3_INVARIANT"
    return "OTHER"


class QueryAudit:
    def __init__(self, classify=False):
        self.classify = classify
        self.total = 0
        self.unique = set()
        self.counts = Counter()
        self.positions = Counter()
        self.square_owner = Counter()
        self.positive = 0
        self.negative = 0
        self.in_check_calls = 0
        self.attack_calls = 0
        self.first_cost = 0.0
        self.repeat_cost = 0.0
        self.first_count = 0
        self.repeat_count = 0
        self.callsites = Counter()
        self.callsite_queries = Counter()

    def record_attack(self, position, square, owner, elapsed, result):
        self.attack_calls += 1
        self.total += 1
        key = exact_query_key(position, square, owner)
        first = key not in self.unique
        self.unique.add(key)
        self.counts[key] += 1
        self.positions[(position.ruleset_fingerprint, position)] += 1
        self.square_owner[(square, owner)] += 1
        if result:
            self.positive += 1
        else:
            self.negative += 1
        if first:
            self.first_count += 1
            self.first_cost += elapsed
        else:
            self.repeat_count += 1
            self.repeat_cost += elapsed
        if self.classify:
            category = classify_callsite()
            self.callsites[category] += 1
            self.callsite_queries[(category, first)] += 1

    def snapshot(self):
        duplicate = self.total - len(self.unique)
        multiplicities = sorted(self.counts.values(), reverse=True)
        position_counts = sorted(self.positions.values())
        return {
            "total_attack_queries": self.total,
            "unique_exact_attack_queries": len(self.unique),
            "duplicate_exact_attack_queries": duplicate,
            "duplicate_rate": duplicate / self.total if self.total else 0.0,
            "positive_queries": self.positive,
            "negative_queries": self.negative,
            "unique_positions_queried": len(self.positions),
            "queries_per_position_median": (
                position_counts[(len(position_counts) - 1) // 2]
                if position_counts else 0
            ),
            "queries_per_position_p90": (
                position_counts[min(len(position_counts) - 1, int(len(position_counts) * 0.9))]
                if position_counts else 0
            ),
            "queries_per_position_max": max(position_counts, default=0),
            "same_position_duplicate_count": sum(max(0, n - 1) for n in self.positions.values()),
            "same_square_owner_duplicate_count": sum(max(0, n - 1) for n in self.square_owner.values()),
            "in_check_calls": self.in_check_calls,
            "is_square_attacked_calls": self.attack_calls,
            "first_query_cost_s": self.first_cost,
            "repeat_query_cost_s": self.repeat_cost,
            "first_query_cost_mean_s": self.first_cost / self.first_count if self.first_count else 0.0,
            "repeat_query_cost_mean_s": self.repeat_cost / self.repeat_count if self.repeat_count else 0.0,
            "top_repeated_exact_query_multiplicities": multiplicities[:20],
            "callsite_counts": dict(sorted(self.callsites.items())),
            "callsite_first_vs_repeat": {
                f"{category}:{'first' if first else 'repeat'}": count
                for (category, first), count in sorted(self.callsite_queries.items())
            },
        }


class BoundedExactAttackCache:
    """Test-only bounded exact cache; digest collisions cannot authorize hits."""

    def __init__(self, max_entries=4096):
        self.max_entries = max_entries
        self.entries = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.peak = 0

    def get_or_compute(self, position, square, owner, compute, checkpoint=None):
        if checkpoint is not None:
            checkpoint()
        key = exact_query_key(position, square, owner)
        if key in self.entries:
            self.hits += 1
            value = self.entries.pop(key)
            self.entries[key] = value
            return value
        self.misses += 1
        value = compute()
        self.entries[key] = value
        while len(self.entries) > self.max_entries:
            self.entries.popitem(last=False)
            self.evictions += 1
        self.peak = max(self.peak, len(self.entries))
        return value

    def snapshot(self):
        return {
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "cache_hit_rate": self.hits / (self.hits + self.misses) if self.hits + self.misses else 0.0,
            "cache_entries_peak": self.peak,
            "cache_entries_final": len(self.entries),
            "cache_evictions": self.evictions,
            "cache_max_entries": self.max_entries,
        }


def install_wrappers(audit: QueryAudit, candidate=False, classify=False):
    original_attack = SemanticEngine.is_square_attacked
    original_in_check = SemanticEngine.in_check
    cache = BoundedExactAttackCache() if candidate else None

    def in_check(self, position, side, checkpoint=None):
        audit.in_check_calls += 1
        return original_in_check(self, position, side, checkpoint=checkpoint)

    def attack(self, position, square, by_owner, checkpoint=None):
        started = time.perf_counter()

        def compute():
            return original_attack(self, position, square, by_owner, checkpoint=checkpoint)

        if cache is None:
            result = compute()
        else:
            result = cache.get_or_compute(
                position, square, by_owner, compute, checkpoint=checkpoint
            )
        audit.record_attack(
            position, square, by_owner, time.perf_counter() - started, result
        )
        return result

    SemanticEngine.is_square_attacked = attack
    SemanticEngine.in_check = in_check
    return original_attack, original_in_check, cache


def restore_wrappers(original_attack, original_in_check):
    SemanticEngine.is_square_attacked = original_attack
    SemanticEngine.in_check = original_in_check


def run_search(spec, profile, candidate=False, classify=False, profile_path=None):
    audit = QueryAudit(classify=classify)
    original_attack, original_in_check, cache = install_wrappers(audit, candidate, classify)
    started = time.perf_counter()
    try:
        result = run_once(spec, profile, "timing", profile_path=profile_path)
    finally:
        restore_wrappers(original_attack, original_in_check)
    result["query_reuse"] = audit.snapshot()
    if cache is not None:
        result["memoization"] = cache.snapshot()
    result["candidate"] = candidate
    result["diagnostic_classification"] = classify
    result["wall_s"] = time.perf_counter() - started
    return result


def _worker(payload, queue):
    try:
        if payload["mode"] == "search":
            result = run_search(
                payload["spec"], payload["profile"], payload.get("candidate", False),
                payload.get("classify", False), payload.get("profile_path"),
            )
        else:
            raise ValueError(payload["mode"])
        queue.put({"ok": True, "result": result})
    except BaseException as exc:  # pragma: no cover - bounded worker evidence
        queue.put({"ok": False, "error": repr(exc)})


def safe_run(payload, timeout=DEFAULT_TIMEOUT):
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


def run_profile(profile, candidate=False, reps=5, classify=False):
    rows = []
    for spec in corpus_specs():
        safe_run({"mode": "search", "spec": spec, "profile": profile, "candidate": candidate, "classify": classify})
        for repetition in range(reps):
            row = safe_run({"mode": "search", "spec": spec, "profile": profile, "candidate": candidate, "classify": classify})
            row["repetition"] = repetition + 1
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("A", "B"), required=True)
    parser.add_argument("--candidate", action="store_true")
    parser.add_argument("--classify", action="store_true")
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = run_profile(args.profile, args.candidate, args.reps, args.classify)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
