"""F85 diagnostic-only lane scaling probe on the frozen F84 resource roots."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import ctypes
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import queue
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import f50_generic_learnable_evaluator as f50
from scripts import f59_action_spectrum_diagnosis as f59
from scripts import f79_parent_anchored_full_residual_arena4 as f79
from scripts import f83_c1_relative_evidence_roots_and_cost_calibration as f83
from scripts import f84_c1_teacher_extended_cost_calibration as f84


LABEL = f84.LABEL
LANE_COUNTS = (2, 3, 4)
SMOKE = True
PER_ROOT_WALL_SECONDS = 180
WHOLE_PROBE_HARD_WALL_SECONDS = 900
OUTPUT_PATH = ROOT / ".generic_chess_flow/f85-lane-scaling-calibration/raw.json"

_ACTIVE_PIDS: set[int] = set()
_ACTIVE_LOCK = threading.Lock()


def _digest(payload) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _rss_bytes(pid: int) -> int:
    if os.name != "nt":  # pragma: no cover - this diagnostic is Windows-only
        return 0
    process_query_information = 0x0400
    process_vm_read = 0x0010
    handle = ctypes.windll.kernel32.OpenProcess(process_query_information | process_vm_read, False, pid)
    if not handle:
        return 0

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    try:
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(counters), ctypes.sizeof(Counters)
        )
        return int(counters.WorkingSetSize) if ok else 0
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def _memory_sampler(stop: threading.Event, result: dict) -> None:
    peak = 0
    while not stop.is_set():
        with _ACTIVE_LOCK:
            pids = tuple(_ACTIVE_PIDS)
        total = sum(_rss_bytes(pid) for pid in pids)
        peak = max(peak, total)
        stop.wait(0.05)
    result["peak_worker_rss_bytes"] = peak


def _worker(record: dict, result_queue) -> None:
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    try:
        compiled, native, _profile = f50._ruleset(LABEL)
        _parent, champion, _descriptor = f79._load_frozen_candidate(compiled)
        _rows, metadata = f59._spectrum_for_root(
            compiled, native, champion, champion, record, smoke=SMOKE
        )
        result_queue.put({
            "status": "COMPLETE",
            "elapsed_wall_seconds": time.perf_counter() - started_wall,
            "process_cpu_seconds": time.process_time() - started_cpu,
            "legal_action_count": int(metadata["legal_action_count"]),
            "selected_action_count": len(metadata["action_rows"]),
            "result_signature": _digest(metadata["action_rows"]),
        })
    except BaseException as exc:  # pragma: no cover - bounded diagnostic failure path
        result_queue.put({
            "status": "HARNESS_MISMATCH",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_wall_seconds": time.perf_counter() - started_wall,
            "process_cpu_seconds": time.process_time() - started_cpu,
        })


def _run_one(record: dict) -> dict:
    context = mp.get_context("spawn")
    result_queue = context.Queue()
    process = context.Process(target=_worker, args=(record, result_queue))
    started = time.perf_counter()
    process.start()
    with _ACTIVE_LOCK:
        _ACTIVE_PIDS.add(process.pid)
    try:
        process.join(PER_ROOT_WALL_SECONDS)
        elapsed = time.perf_counter() - started
        if process.is_alive():
            process.terminate()
            process.join(5)
            return {
                "status": "TIME_CAP",
                "elapsed_wall_seconds": elapsed,
                "process_cpu_seconds": None,
                "result_signature": None,
            }
        try:
            result = result_queue.get(timeout=1)
        except queue.Empty:
            result = {
                "status": "HARNESS_MISMATCH",
                "error": f"worker exited with code {process.exitcode} without telemetry",
                "elapsed_wall_seconds": elapsed,
                "process_cpu_seconds": None,
            }
        result["elapsed_wall_seconds"] = float(result.get("elapsed_wall_seconds", elapsed))
        return result
    finally:
        with _ACTIVE_LOCK:
            _ACTIVE_PIDS.discard(process.pid)


def _run_lane_count(compiled, roots: list[dict], lanes: int) -> dict:
    started = time.perf_counter()
    memory = {}
    stop = threading.Event()
    sampler = threading.Thread(target=_memory_sampler, args=(stop, memory), daemon=True)
    sampler.start()
    with ThreadPoolExecutor(max_workers=lanes) as pool:
        raw_results = list(pool.map(_run_one, roots))
    stop.set()
    sampler.join()
    rows = [
        {"root_id": root["root_id"], **result}
        for root, result in zip(roots, raw_results)
    ]
    return {
        "lane_count": lanes,
        "status": "COMPLETE" if all(row["status"] == "COMPLETE" for row in rows) else "INCOMPLETE",
        "stage_elapsed_wall_seconds": time.perf_counter() - started,
        "total_process_cpu_seconds": sum(
            row["process_cpu_seconds"] for row in rows if row.get("process_cpu_seconds") is not None
        ),
        "peak_worker_rss_bytes": memory.get("peak_worker_rss_bytes", 0),
        "results": rows,
    }


def run() -> dict:
    started = time.perf_counter()
    compiled, _native, _profile = f50._ruleset(LABEL)
    _payload, roots, provenance = f84._load_frozen_resource_roots(compiled)
    results = [_run_lane_count(compiled, roots, lanes) for lanes in LANE_COUNTS]
    if time.perf_counter() - started > WHOLE_PROBE_HARD_WALL_SECONDS:
        raise RuntimeError("F85 lane scaling probe exceeded its 15-minute hard wall")
    signatures = {
        row["root_id"]: row.get("result_signature")
        for row in results[0]["results"]
    }
    deterministic = all(
        all(row.get("result_signature") == signatures.get(row["root_id"]) for row in result["results"])
        for result in results
    )
    payload = {
        "schema": "generic-chess-f85-lane-scaling-calibration-v1",
        "status": "DIAGNOSTIC_ONLY_NO_TRAINING_EVIDENCE",
        "sandbox_sha": f84._git_sha(),
        "f84_calibration_sha256": f84._sha(f84.OUTPUT_PATH),
        "f83_root_set_identity_sha256": provenance["root_set_identity_sha256"],
        "root_ids": list(f84.ROOT_IDS),
        "smoke_budgets": {"root": [50, 100, 200], "selected_actions": 3},
        "lane_counts": list(LANE_COUNTS),
        "deterministic_result_signatures": deterministic,
        "stage_elapsed_wall_seconds": time.perf_counter() - started,
        "results": results,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True), flush=True)
