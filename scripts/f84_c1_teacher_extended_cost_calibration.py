"""F84: bounded extended calibration on the frozen F83 resource roots."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import queue as queue_module
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

from scripts import f50_generic_learnable_evaluator as f50
from scripts import f59_action_spectrum_diagnosis as f59
from scripts import f79_parent_anchored_full_residual_arena4 as f79
from scripts import f83_c1_relative_evidence_roots_and_cost_calibration as f83


LABEL = "B_CANONICAL_STANDARD_SHOGI"
WORK_ORDER = "GENERICCHESS-F84-C1-TEACHER-EXTENDED-COST-CALIBRATION"
C1_ID = f83.C1_ID
C1_MODEL_SHA = f83.C1_MODEL_SHA
F83_ROOT_SET_ID = "c197799729877dc836116740d0827de0b02cfabde42e45c8e53e19f61c3ee108"
ROOT_IDS = (
    "reachable_random-r-00",
    "c1_on_policy-r-00",
    "c1_pv_corridor-r-00",
)
MAX_CONCURRENT_ROOTS = 2
PER_ROOT_WALL_SECONDS = 720
WHOLE_STAGE_HARD_WALL_SECONDS = 1500
ROOT_BUDGETS = (2000, 40000, 80000)
OBSERVER_ROOT_BUDGET = 2000
CHILD_BUDGETS = {"all_legal": 1000, "selected_mid": 10000, "selected_high": 20000}
MAX_SELECTED_ACTIONS = 9
MAX_ROOT_NODE_BUDGETS = {
    "reachable_random": 419000,
    "c1_on_policy": 426000,
    "c1_pv_corridor": 426000,
}
OUTPUT_PATH = ROOT / "artifacts" / "f84_c1_teacher_extended_calibration" / "calibration.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_sha(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _git_sha() -> str:
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT}", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _root_identities(payload: dict) -> list[dict]:
    return [
        {key: root[key] for key in ("root_id", "position_key", "stratum", "role", "replay_actions")}
        for root in payload["roots"]
    ]


def _load_frozen_resource_roots(compiled) -> tuple[dict, list[dict], dict]:
    root_path = ROOT / "artifacts/f83_c1_relative_evidence/root_corpus.json"
    payload = json.loads(root_path.read_text(encoding="utf-8"))
    if _stable_sha(_root_identities(payload)) != F83_ROOT_SET_ID:
        raise RuntimeError("F84 F83 root-set identity mismatch")
    roots = [root for root in payload["roots"] if root["root_id"] in ROOT_IDS]
    if tuple(root["root_id"] for root in roots) != ROOT_IDS:
        raise RuntimeError("F84 resource-root selection mismatch")
    if any(root["role"] != "resource_estimation_only" for root in roots):
        raise RuntimeError("F84 selected root is not resource-only")
    for root in roots:
        session = f83._session(compiled, root["replay_actions"])
        from generic_chess.core.identity import position_identity_key
        if session.result.status.value != "ongoing" or position_identity_key(session.state.position, compiled) != root["position_key"]:
            raise RuntimeError(f"F84 frozen root replay mismatch: {root['root_id']}")
    manifest = json.loads(f83.F62_MANIFEST_PATH.read_text(encoding="utf-8"))
    sealed = f83._load_sealed_position_keys(set(manifest["position_keys"]))
    overlaps = f83._historical_overlap(roots, sealed)
    if any(overlaps.values()):
        raise RuntimeError(f"F84 frozen root overlaps sealed history: {overlaps}")
    return payload, roots, {
        "root_set_identity_sha256": F83_ROOT_SET_ID,
        "root_corpus_path": str(root_path.relative_to(ROOT)).replace("\\", "/"),
        "root_corpus_sha256": _sha(root_path),
        "overlap_counts": overlaps,
    }


def _root_summary(metadata: dict) -> dict:
    return {
        name: {
            "budget": budget,
            "action_key": metadata[name]["action_key"],
            "score": metadata[name]["score"],
            "nodes": metadata[name]["nodes"],
            "completed_depth": metadata[name]["completed_depth"],
        }
        for name, budget in (
            ("root_2k", ROOT_BUDGETS[0]),
            ("root_40k", ROOT_BUDGETS[1]),
            ("root_80k", ROOT_BUDGETS[2]),
            ("observer_2k", OBSERVER_ROOT_BUDGET),
        )
    }


def _calibration_worker(record: dict, result_queue) -> None:
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    try:
        compiled, native, _profile = f50._ruleset(LABEL)
        _parent, champion, _descriptor = f79._load_frozen_candidate(compiled)
        _rows, metadata = f59._spectrum_for_root(compiled, native, champion, champion, record, smoke=False)
        legal = int(metadata["legal_action_count"])
        selected = len(metadata["action_rows"])
        declared_budget = (
            sum(ROOT_BUDGETS) + OBSERVER_ROOT_BUDGET
            + legal * CHILD_BUDGETS["all_legal"]
            + selected * (CHILD_BUDGETS["selected_mid"] + CHILD_BUDGETS["selected_high"])
        )
        result_queue.put({
            "status": "COMPLETE",
            "elapsed_wall_seconds": time.perf_counter() - started_wall,
            "process_cpu_seconds": time.process_time() - started_cpu,
            "legal_action_count": legal,
            "selected_action_count": selected,
            "actual_teacher_calls": 2 * selected,
            "actual_search_calls": 4 + legal + 2 * selected,
            "root_search_summaries": _root_summary(metadata),
            "declared_child_search_budgets": CHILD_BUDGETS,
            "declared_total_search_node_budget": declared_budget,
        })
    except BaseException as exc:  # pragma: no cover - bounded worker failure path
        result_queue.put({
            "status": "HARNESS_MISMATCH",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_wall_seconds": time.perf_counter() - started_wall,
            "process_cpu_seconds": time.process_time() - started_cpu,
        })


def _run_one(root: dict) -> dict:
    context = mp.get_context("spawn")
    result_queue = context.Queue()
    process = context.Process(target=_calibration_worker, args=(root, result_queue))
    started = time.perf_counter()
    process.start()
    process.join(PER_ROOT_WALL_SECONDS)
    elapsed = time.perf_counter() - started
    if process.is_alive():
        process.terminate()
        process.join(5)
        return {
            "status": "TIME_CAP",
            "elapsed_wall_seconds": elapsed,
            "process_cpu_seconds": None,
            "termination_reason": "per_root_wall_cap",
        }
    try:
        result = result_queue.get(timeout=1)
    except queue_module.Empty:
        result = {
            "status": "HARNESS_MISMATCH",
            "error": f"worker exited with code {process.exitcode} without telemetry",
            "elapsed_wall_seconds": elapsed,
            "process_cpu_seconds": None,
        }
    result["elapsed_wall_seconds"] = float(result.get("elapsed_wall_seconds", elapsed))
    return result


def _unknown_fields(result: dict) -> None:
    result.update({
        "selected_action_count": None,
        "actual_teacher_calls": None,
        "actual_search_calls": None,
        "root_search_summaries": None,
        "declared_total_search_node_budget": None,
        "telemetry_unavailable_reason": "probe_process_terminated_at_wall_cap_before_metadata_return",
    })


def _run_stage(roots: list[dict]) -> tuple[list[dict], float]:
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_ROOTS) as pool:
        raw_results = list(pool.map(_run_one, roots))
    elapsed = time.perf_counter() - started
    results = []
    for root, result in zip(roots, raw_results):
        session = f83._session(_compiled_for_metadata, root["replay_actions"])
        row = {
            "root_id": root["root_id"],
            "stratum": root["stratum"],
            "role": root["role"],
            "position_key": root["position_key"],
            "legal_action_count": len(session.legal_actions()),
            **result,
        }
        if row["status"] != "COMPLETE":
            _unknown_fields(row)
        results.append(row)
    return results, elapsed


_compiled_for_metadata = None


def run(envelope_path: Path) -> dict:
    global _compiled_for_metadata
    compiled, _native, _profile = f50._ruleset(LABEL)
    _compiled_for_metadata = compiled
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    envelope_sha = _sha(envelope_path)
    root_payload, roots, root_provenance = _load_frozen_resource_roots(compiled)
    results, elapsed = _run_stage(roots)
    complete = [row for row in results if row["status"] == "COMPLETE"]
    capped = [row for row in results if row["status"] == "TIME_CAP"]
    failed = [row for row in results if row["status"] == "HARNESS_MISMATCH"]
    if failed or elapsed > WHOLE_STAGE_HARD_WALL_SECONDS:
        classification = "HARNESS_MISMATCH"
    elif len(complete) == len(roots):
        classification = "C1_TEACHER_COST_EXTENDED_CALIBRATED"
    elif complete:
        classification = "C1_TEACHER_COST_PARTIALLY_CALIBRATED"
    else:
        classification = "C1_TEACHER_COST_EXTENDED_LOWER_BOUND_ONLY"
    payload = {
        "schema": "generic-chess-f84-c1-teacher-extended-calibration-v1",
        "work_order": WORK_ORDER,
        "sandbox_sha": _git_sha(),
        "ruleset": LABEL,
        "c1_authority": {"checkpoint_id": C1_ID, "model_sha256": C1_MODEL_SHA},
        "f83_authority": root_provenance,
        "teacher_contract": {
            "implementation_paths": ["scripts/f59_action_spectrum_diagnosis.py", "scripts/f62_learned_champion_repeatability.py"],
            "implementation_sha256": {path: _sha(ROOT / path) for path in ("scripts/f59_action_spectrum_diagnosis.py", "scripts/f62_learned_champion_repeatability.py")},
            "f62_stage_sha256": f83.F62_STAGE_SHA,
            "f62_records_sha256": f83.F62_RECORDS_SHA,
            "root_budgets": list(ROOT_BUDGETS),
            "observer_root_budget": OBSERVER_ROOT_BUDGET,
            "teacher_child_budgets": CHILD_BUDGETS,
            "max_depth": 12,
            "tt_megabytes": 8,
            "root_window_pruning": False,
            "candidate_action_construction": "all legal actions sorted canonically; cheap child-Q ordering; top six plus root/observer/high-budget actions",
            "target_q_convention": "child-side search score negated to root-action owner perspective",
        },
        "execution_contract": {
            "root_ids": list(ROOT_IDS),
            "max_concurrent_roots": MAX_CONCURRENT_ROOTS,
            "per_root_wall_cap_seconds": PER_ROOT_WALL_SECONDS,
            "whole_stage_hard_wall_seconds": WHOLE_STAGE_HARD_WALL_SECONDS,
            "no_retry": True,
            "no_persisted_teacher_targets": True,
            "maximum_selected_actions": MAX_SELECTED_ACTIONS,
            "maximum_root_node_budgets": MAX_ROOT_NODE_BUDGETS,
            "effective_workload": {"games": 0, "arena_pairs": 0, "plies": 0},
        },
        "resource_envelope": envelope,
        "resource_envelope_sha256": envelope_sha,
        "results": results,
        "completed_count": len(complete),
        "capped_count": len(capped),
        "failed_count": len(failed),
        "stage_elapsed_wall_seconds": elapsed,
        "stage_hard_wall_exceeded": elapsed > WHOLE_STAGE_HARD_WALL_SECONDS,
        "actual_teacher_calls": sum(row["actual_teacher_calls"] for row in complete) if len(complete) == len(roots) else None,
        "actual_search_calls": sum(row["actual_search_calls"] for row in complete) if len(complete) == len(roots) else None,
        "classification": classification,
    }
    _atomic_json(OUTPUT_PATH, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resource-envelope", required=True, type=Path)
    args = parser.parse_args()
    payload = run(args.resource_envelope)
    print(json.dumps({
        "classification": payload["classification"],
        "completed_count": payload["completed_count"],
        "capped_count": payload["capped_count"],
        "failed_count": payload["failed_count"],
        "output": str(OUTPUT_PATH.relative_to(ROOT)).replace("\\", "/"),
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
