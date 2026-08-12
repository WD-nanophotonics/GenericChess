"""Measure the separated F3 runtime key-construction costs.

This is a validation-only microbenchmark.  It reports calls and elapsed time
for snapshot discriminators, exact-position token fallback, history-context
append, and effective search-key construction separately.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from ai_fixtures import build_4x4_rooks, build_mate  # noqa: E402
from generic_chess.core.search_runtime import (  # noqa: E402
    RuntimeCountsSnapshot,
    RuntimeHistoryContext,
    SearchPathRuntime,
)
from generic_chess.session.session import GameSession  # noqa: E402


def measure(compiled, label: str, depth: int = 6) -> dict[str, object]:
    module = __import__("generic_chess.core.search_runtime", fromlist=["_identity_token"])
    original_entry = RuntimeCountsSnapshot._entry_digest
    original_token = module._identity_token
    original_sort = module._identity_sort_key
    original_record = RuntimeHistoryContext._record_digest
    original_key = SearchPathRuntime.search_key
    counts = {
        "snapshot_entry_digest_calls": 0,
        "exact_position_token_calls": 0,
        "exact_position_sort_calls": 0,
        "history_context_digest_updates": 0,
        "search_key_calls": 0,
        "search_key_ns": 0,
    }

    def entry(*args):
        counts["snapshot_entry_digest_calls"] += 1
        return original_entry(*args)

    def token(value):
        counts["exact_position_token_calls"] += 1
        return original_token(value)

    def sort(value):
        counts["exact_position_sort_calls"] += 1
        return original_sort(value)

    def record(*args):
        counts["history_context_digest_updates"] += 1
        return original_record(*args)

    def search_key(runtime):
        counts["search_key_calls"] += 1
        started = time.perf_counter_ns()
        try:
            return original_key(runtime)
        finally:
            counts["search_key_ns"] += time.perf_counter_ns() - started

    RuntimeCountsSnapshot._entry_digest = staticmethod(entry)
    module._identity_token = token
    module._identity_sort_key = sort
    RuntimeHistoryContext._record_digest = staticmethod(record)
    SearchPathRuntime.search_key = search_key
    runtime = SearchPathRuntime.from_state(GameSession(compiled).state, compiled)
    for key in counts:
        counts[key] = 0
    started = time.perf_counter_ns()
    children = 0
    try:
        for _ in range(depth):
            actions = runtime.legal_actions()
            if not actions:
                break
            runtime.push(actions[0])
            runtime.search_key()
            children += 1
    finally:
        while runtime.depth:
            runtime.pop()
        RuntimeCountsSnapshot._entry_digest = original_entry
        module._identity_token = original_token
        module._identity_sort_key = original_sort
        RuntimeHistoryContext._record_digest = original_record
        SearchPathRuntime.search_key = original_key
    return {
        "fixture": label,
        "children": children,
        **counts,
        "search_key_us": round(counts["search_key_ns"] / 1000, 3),
        "total_runtime_path_ms": round((time.perf_counter_ns() - started) / 1_000_000, 3),
        "position_repr_bytes": len(repr(runtime.position).encode("utf-8")),
    }


def main() -> int:
    print(json.dumps([
        measure(build_4x4_rooks(), "legacy-4x4-rooks"),
        measure(build_mate(2), "legacy-8x8-mate"),
    ], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
