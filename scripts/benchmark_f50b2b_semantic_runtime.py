"""F50B2B reproducible semantic Native runtime throughput benchmark.

Writes only caller-selected output; raw measurements belong outside Git.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import threading
import time
from dataclasses import replace
from pathlib import Path

from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import (
    fixed_depth_search, guarded_actions, make_checked, pack_position,
    position_key, search_runtime_sizes, semantic_iterative_search,
    root_parallel_search,
)
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


def _pack_initial(semantic, native):
    ids = {type_id: index for index, type_id in enumerate(native.type_ids)}
    board = [None if piece is None else [ids[piece.base_type_id], ids[piece.current_type_id], piece.owner, int(piece.promoted)]
             for row in semantic.support.initial_position for piece in row]
    return pack_position(native, {"side": 0, "ply": 0, "board": board,
                                  "hands": [[0] * len(ids), [0] * len(ids)], "aux_state": ()})


def _case_specs():
    from audit_f23v_minimal_analytic_evaluator import _rule_set

    generated = _rule_set("MIXED", 4)
    return (
        ("western", build_western_chess_ruleset()),
        ("shogi_without_declarations", replace(build_standard_shogi_ruleset(), declarations=())),
        ("generated", generated),
    )


def _midgames(native, position, variants=3, plies=18):
    """Build deterministic, distinct legal positions rather than timing only setup."""
    positions = []
    seen = set()
    for variant in range(variants):
        cursor = position
        for ply in range(plies):
            actions = guarded_actions(native, cursor)
            if not actions:
                break
            cursor = make_checked(native, cursor, actions[(variant + ply) % len(actions)])
        key = position_key(native, cursor)
        if key not in seen:
            seen.add(key)
            positions.append(cursor)
    return positions


def _rss_bytes():
    """Read current process RSS without adding a third-party benchmark dependency."""
    if os.name != "nt":
        return None
    import ctypes

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong)
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    ok = psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    return int(counters.WorkingSetSize) if ok else None


def _measure_peak_rss(run):
    baseline = _rss_bytes()
    peak = baseline
    stop = threading.Event()

    def sample():
        nonlocal peak
        while not stop.wait(0.002):
            current = _rss_bytes()
            if current is not None:
                peak = max(peak or 0, current)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    try:
        result = run()
    finally:
        stop.set()
        sampler.join()
    current = _rss_bytes()
    if current is not None:
        peak = max(peak or 0, current)
    return result, {"baseline_rss_bytes": baseline, "peak_rss_bytes": peak,
                    "peak_rss_delta_bytes": None if peak is None or baseline is None else peak - baseline}


def _checked_transition_benchmark(native, positions, repeats, position_bytes):
    work = []
    for position in positions:
        actions = guarded_actions(native, position)
        if actions:
            work.append((position, actions[0]))
    if not work:
        return {"calls": 0, "elapsed_seconds": 0.0, "calls_per_second": 0.0,
                "latency_microseconds": None,
                "approximate_copy_bandwidth_bytes_per_second": 0.0}
    started = time.perf_counter()
    for index in range(repeats):
        position, action = work[index % len(work)]
        make_checked(native, position, action)
    elapsed = time.perf_counter() - started
    rate = repeats / elapsed if elapsed else 0.0
    return {"calls": repeats, "elapsed_seconds": elapsed, "calls_per_second": rate,
            "latency_microseconds": (elapsed * 1_000_000 / repeats) if repeats else 0.0,
            "approximate_copy_bandwidth_bytes_per_second": rate * position_bytes}


def _root_parallel_scaling(native, position, depth, worker_counts):
    reference = semantic_iterative_search(native, position, depth)
    rows = []
    for workers in worker_counts:
        started = time.perf_counter()
        cpu_started = time.process_time()
        result, memory = _measure_peak_rss(
            lambda: root_parallel_search(native, position, depth, workers=workers)
        )
        elapsed = time.perf_counter() - started
        cpu = time.process_time() - cpu_started
        rows.append({"workers": workers, "elapsed_seconds": elapsed,
                     "process_cpu_seconds": cpu,
                     "cpu_utilization_cores": cpu / elapsed if elapsed else 0.0,
                     "memory": memory,
                     "parity": (result["score"], result["best_action"], result["principal_variation"]) ==
                               (reference["score"], reference["best_action"], reference["principal_variation"]),
                     "root_actions": result.get("root_actions", 0)})
    return rows


def _run_many(native, positions, depth, workers, repeats):
    def run(index):
        return semantic_iterative_search(native, positions[index % len(positions)], depth)
    def execute():
        started = time.perf_counter()
        cpu_started = time.process_time()
        if workers == 1:
            rows = [run(index) for index in range(repeats)]
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                rows = list(pool.map(run, range(repeats)))
        return rows, time.perf_counter() - started, time.process_time() - cpu_started
    (rows, elapsed, cpu), memory = _measure_peak_rss(execute)
    nodes = sum(row["nodes"] for row in rows)
    transitions = sum(row["transition_count"] for row in rows)
    legal = sum(row["legal_generation_count"] for row in rows)
    identities_by_position = {}
    for index, row in enumerate(rows):
        identities_by_position.setdefault(index % len(positions), set()).add(
            (row["score"], row["best_action"], row["principal_variation"])
        )
    return {"runs": repeats, "workers": workers, "nodes": nodes, "transitions": transitions,
            "legal_generations": legal, "elapsed_seconds": elapsed, "process_cpu_seconds": cpu,
            "cpu_utilization_cores": cpu / elapsed if elapsed else 0.0,
            "nodes_per_second": nodes / elapsed if elapsed else 0.0,
            "transitions_per_second": transitions / elapsed if elapsed else 0.0,
            "legal_generations_per_second": legal / elapsed if elapsed else 0.0,
            "deterministic": all(len(values) == 1 for values in identities_by_position.values()),
            "memory": memory,
            "identities": [
                {"score": row["score"], "best_action": row["best_action"],
                 "principal_variation": row["principal_variation"]}
                for row in rows
            ]}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--workers", type=int, default=min(16, os.cpu_count() or 1))
    parser.add_argument("--scaling-workers", default="4,8,16",
                        help="comma-separated independent-search worker counts")
    parser.add_argument("--cases", default="western,shogi_without_declarations,generated",
                        help="comma-separated case names to include")
    parser.add_argument("--root-workers", default="1,2,4,8,16",
                        help="comma-separated worker counts for one-position root split")
    parser.add_argument("--midgame-plies", type=int, default=18,
                        help="legal plies used to build each representative midgame")
    parser.add_argument("--repeats", type=int, default=16)
    parser.add_argument("--transition-repeats", type=int, default=20_000)
    args = parser.parse_args(argv)
    scaling_workers = tuple(sorted({int(value) for value in args.scaling_workers.split(",") if int(value) > 1} | {args.workers}))
    selected_cases = frozenset(args.cases.split(","))
    root_workers = tuple(sorted({int(value) for value in args.root_workers.split(",") if int(value) > 0}))
    rows = []
    for name, ruleset in _case_specs():
        if name not in selected_cases:
            continue
        semantic = compile_semantic_ruleset(ruleset)
        native = compile_native_semantic_rules(semantic)
        positions = _midgames(native, _pack_initial(semantic, native), plies=args.midgame_plies)
        fixed_rows = []
        for position in positions:
            fixed_started = time.perf_counter()
            fixed = fixed_depth_search(native, position, args.depth)
            fixed_rows.append({"score": fixed["score"], "best_action": fixed["best_action"], "principal_variation": fixed["principal_variation"], "nodes": fixed["nodes"], "elapsed_seconds": time.perf_counter() - fixed_started})
        serial = _run_many(native, positions, args.depth, 1, args.repeats)
        parallel_scaling = {
            worker_count: _run_many(native, positions, args.depth, worker_count, args.repeats)
            for worker_count in scaling_workers
        }
        parallel = parallel_scaling[args.workers]
        parity = parallel["identities"] == serial["identities"]
        fixed_parity = all(
            (result["best_action"], result["principal_variation"]) ==
            (fixed["best_action"], fixed["principal_variation"])
            for result, fixed in zip(
                parallel["identities"],
                (fixed_rows[index % len(fixed_rows)] for index in range(args.repeats)),
            )
        )
        rows.append({"case": name, "midgame_positions": len(positions), "fixed": fixed_rows,
                     "checked_transition": _checked_transition_benchmark(native, positions, args.transition_repeats, search_runtime_sizes()["position_bytes"]),
                     "root_parallel": _root_parallel_scaling(native, positions[0], args.depth, root_workers),
                     "serial": serial, "parallel": parallel,
                     "parallel_scaling": parallel_scaling, "parity": parity,
                     "fixed_action_pv_parity": fixed_parity,
                     "speedup": parallel["nodes_per_second"] / serial["nodes_per_second"] if serial["nodes_per_second"] else None})
    report = {"schema": "F50B2B-SEMANTIC-RUNTIME-BENCHMARK-V1", "depth": args.depth,
              "workers": args.workers, "scaling_workers": scaling_workers, "selected_cases": sorted(selected_cases), "repeats": args.repeats, "transition_repeats": args.transition_repeats, "logical_cpus": os.cpu_count(),
              "runtime_sizes": search_runtime_sizes(), "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": report["schema"], "depth": args.depth, "workers": args.workers,
        "repeats": args.repeats, "runtime_sizes": report["runtime_sizes"],
        "cases": [{"case": row["case"], "parity": row["parity"], "speedup": row["speedup"],
                   "parallel_nps": row["parallel"]["nodes_per_second"],
                   "parallel_cpu_cores": row["parallel"]["cpu_utilization_cores"],
                   "peak_rss_bytes": row["parallel"]["memory"]["peak_rss_bytes"],
                   "transition_latency_us": row["checked_transition"]["latency_microseconds"],
                   "scaling": {str(workers): {"nps": result["nodes_per_second"],
                                                 "cpu_cores": result["cpu_utilization_cores"]}
                               for workers, result in row["parallel_scaling"].items()}}
                  for row in rows],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
