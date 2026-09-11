"""F85A: prepare, but do not execute, the 36-root C2 teacher acquisition."""

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
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import f50_generic_learnable_evaluator as f50
from scripts import f59_action_spectrum_diagnosis as f59
from scripts import f79_parent_anchored_full_residual_arena4 as f79
from scripts import f83_c1_relative_evidence_roots_and_cost_calibration as f83


LABEL = "B_CANONICAL_STANDARD_SHOGI"
WORK_ORDER = "GENERICCHESS-F85A-C2-TRAIN-TEACHER-ACQUISITION-HARNESS-AND-LARGE-PLAN"
F83_ROOT_SET_ID = "c197799729877dc836116740d0827de0b02cfabde42e45c8e53e19f61c3ee108"
F84_CALIBRATION_SHA = "9fd8eb417a71fb1c5e7af5225c84fb73facb0549eeaae229a6923e7be8a4677b"
ROOT_BUDGETS = (2000, 40000, 80000)
OBSERVER_ROOT_BUDGET = 2000
CHILD_BUDGETS = {"all_legal": 1000, "selected_mid": 10000, "selected_high": 20000}
MAX_SELECTED_ACTIONS = 9
MAX_CONCURRENT_ROOTS = 2
PER_ROOT_WALL_SECONDS = 720
F85_MANIFEST_PATH = ROOT / "artifacts/f85_c2_train_teacher_evidence/train_precompute_manifest.json"
F85_RUNTIME_DIR = ROOT / ".generic_chess_flow/f85-c2-train-teacher-acquisition"


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


def _load_train_roots(compiled) -> tuple[dict, list[dict], dict]:
    root_path = ROOT / "artifacts/f83_c1_relative_evidence/root_corpus.json"
    payload = json.loads(root_path.read_text(encoding="utf-8"))
    if _stable_sha(_root_identities(payload)) != F83_ROOT_SET_ID:
        raise RuntimeError("F85 F83 root-set identity mismatch")
    roots = [root for root in payload["roots"] if root["role"] == "train"]
    if len(roots) != 36 or any(root["role"] != "train" for root in roots):
        raise RuntimeError("F85 train-root count or role mismatch")
    expected_strata = {"reachable_random": 12, "c1_on_policy": 12, "c1_pv_corridor": 12}
    if {stratum: sum(root["stratum"] == stratum for root in roots) for stratum in expected_strata} != expected_strata:
        raise RuntimeError("F85 train-root stratum counts mismatch")
    for root in roots:
        session = f83._session(compiled, root["replay_actions"])
        from generic_chess.core.identity import position_identity_key
        if session.result.status.value != "ongoing" or position_identity_key(session.state.position, compiled) != root["position_key"]:
            raise RuntimeError(f"F85 train root replay mismatch: {root['root_id']}")
    return payload, roots, {
        "root_set_identity_sha256": F83_ROOT_SET_ID,
        "root_corpus_path": str(root_path.relative_to(ROOT)).replace("\\", "/"),
        "root_corpus_sha256": _sha(root_path),
        "root_count": len(roots),
        "stratum_counts": expected_strata,
    }


def _root_ceiling(legal_action_count: int) -> int:
    return (
        sum(ROOT_BUDGETS) + OBSERVER_ROOT_BUDGET
        + legal_action_count * CHILD_BUDGETS["all_legal"]
        + MAX_SELECTED_ACTIONS * (CHILD_BUDGETS["selected_mid"] + CHILD_BUDGETS["selected_high"])
    )


def precompute_manifest() -> dict:
    compiled, _native, _profile = f50._ruleset(LABEL)
    root_payload, roots, authority = _load_train_roots(compiled)
    f84_path = ROOT / "artifacts/f84_c1_teacher_extended_calibration/calibration.json"
    if _sha(f84_path) != F84_CALIBRATION_SHA:
        raise RuntimeError("F85 F84 calibration artifact identity mismatch")
    records = []
    for root in roots:
        session = f83._session(compiled, root["replay_actions"])
        legal_count = len(session.legal_actions())
        records.append({
            "root_id": root["root_id"],
            "stratum": root["stratum"],
            "role": root["role"],
            "position_key": root["position_key"],
            "ply": root["ply"],
            "legal_action_count": legal_count,
            "maximum_selected_actions": MAX_SELECTED_ACTIONS,
            "maximum_teacher_calls": 2 * MAX_SELECTED_ACTIONS,
            "maximum_search_calls": 4 + legal_count + 2 * MAX_SELECTED_ACTIONS,
            "declared_node_ceiling": _root_ceiling(legal_count),
        })
    manifest = {
        "schema": "generic-chess-f85-train-root-precompute-manifest-v1",
        "work_order": WORK_ORDER,
        "status": "PRECOMPUTE_COMPLETE_ACQUISITION_NOT_AUTHORIZED",
        "sandbox_sha": _git_sha(),
        "ruleset": LABEL,
        "f83_authority": authority,
        "f84_calibration_artifact": {
            "path": str(f84_path.relative_to(ROOT)).replace("\\", "/"),
            "content_sha256": F84_CALIBRATION_SHA,
        },
        "c1_authority": {"checkpoint_id": f83.C1_ID, "model_sha256": f83.C1_MODEL_SHA},
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
            "train_root_count": 36,
            "dev_root_count": 0,
            "resource_root_count": 0,
            "max_concurrent_roots": MAX_CONCURRENT_ROOTS,
            "per_root_wall_cap_seconds": PER_ROOT_WALL_SECONDS,
            "stage_count": 1,
            "no_auto_retry": True,
            "effective_workload": {"games": 0, "arena_pairs": 0, "plies": 0},
            "maximum_selected_actions": MAX_SELECTED_ACTIONS,
        },
        "total_declared_node_ceiling": sum(record["declared_node_ceiling"] for record in records),
        "roots": records,
    }
    manifest["manifest_sha256"] = _stable_sha(manifest)
    if F85_MANIFEST_PATH.exists():
        existing = json.loads(F85_MANIFEST_PATH.read_text(encoding="utf-8"))
        if existing != manifest:
            raise RuntimeError("F85 precompute manifest identity mismatch")
    else:
        _atomic_json(F85_MANIFEST_PATH, manifest)
    return manifest


def _teacher_unit(compiled, native, parent, observer, record: dict) -> dict:
    """One resumable COMPLETE unit; called only after the approved plan exists."""
    rows, metadata = f59._spectrum_for_root(compiled, native, parent, observer, record, smoke=False)
    selected = len(metadata["action_rows"])
    return {
        "position_key": record["position_key"],
        "selected_action_count": selected,
        "actual_teacher_calls": 2 * selected,
        "actual_search_calls": 4 + metadata["legal_action_count"] + 2 * selected,
        "teacher_rows": metadata["action_rows"],
        "root_metadata": {key: metadata[key] for key in ("root_2k", "root_40k", "root_80k", "observer_2k")},
    }


def _teacher_worker(record: dict, result_queue) -> None:
    started = time.perf_counter()
    try:
        compiled, native, _profile = f50._ruleset(LABEL)
        _parent, champion, _descriptor = f79._load_frozen_candidate(compiled)
        result = _teacher_unit(compiled, native, champion, champion, record)
        result_queue.put({"status": "COMPLETE", "elapsed_wall_seconds": time.perf_counter() - started, **result})
    except BaseException as exc:  # pragma: no cover - bounded worker failure path
        result_queue.put({
            "status": "HARNESS_MISMATCH",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_wall_seconds": time.perf_counter() - started,
        })


def _run_teacher_one(record: dict) -> dict:
    context = mp.get_context("spawn")
    result_queue = context.Queue()
    process = context.Process(target=_teacher_worker, args=(record, result_queue))
    process.start()
    process.join(PER_ROOT_WALL_SECONDS)
    if process.is_alive():
        process.terminate()
        process.join(5)
        return {"status": "TIME_CAP", "termination_reason": "per_root_wall_cap"}
    try:
        return result_queue.get(timeout=1)
    except queue_module.Empty:
        return {"status": "HARNESS_MISMATCH", "error": f"worker exited with code {process.exitcode}"}


def _run_approved_acquisition(manifest: dict, compute_plan_path: Path) -> dict:
    """Run each frozen train root once; this path is only for an approved plan."""
    progress_dir = F85_RUNTIME_DIR / "progress"
    progress_dir.mkdir(parents=True, exist_ok=True)
    completed = []
    pending = []
    for record in manifest["roots"]:
        path = progress_dir / f"{record['root_id']}.json"
        if path.exists():
            prior = json.loads(path.read_text(encoding="utf-8"))
            if prior.get("status") == "COMPLETE" and prior.get("position_key") == record["position_key"]:
                completed.append(prior)
                continue
        pending.append(record)
    results = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_ROOTS) as pool:
        for record, result in zip(pending, pool.map(_run_teacher_one, pending)):
            row = {"root_id": record["root_id"], "position_key": record["position_key"], **result}
            if row["status"] == "COMPLETE":
                row["stratum"] = record["stratum"]
                row["role"] = record["role"]
                path = progress_dir / f"{record['root_id']}.json"
                _atomic_json(path, row)
                completed.append(row)
            results.append(row)
    all_rows = sorted(completed, key=lambda row: row["root_id"])
    if len(all_rows) != 36 or any(row.get("status") != "COMPLETE" for row in all_rows):
        return {"status": "INCOMPLETE", "completed_count": len(all_rows), "results": results}
    evidence = {
        "schema": "generic-chess-f85-c2-train-teacher-evidence-v1",
        "work_order": WORK_ORDER,
        "status": "COMPLETE_TRAIN_TEACHER_EVIDENCE_SEALED",
        "manifest_sha256": _sha(F85_MANIFEST_PATH),
        "compute_plan_sha256": _sha(compute_plan_path),
        "root_count": 36,
        "roots": all_rows,
    }
    _atomic_json(ROOT / "artifacts/f85_c2_train_teacher_evidence/training_evidence.json", evidence)
    return {"status": evidence["status"], "completed_count": 36}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--precompute-only", action="store_true")
    parser.add_argument("--approved-run", action="store_true")
    parser.add_argument("--compute-plan", type=Path)
    args = parser.parse_args()
    if not args.precompute_only and not args.approved_run:
        raise SystemExit("F85 teacher acquisition is withheld until the separately approved large plan is bound")
    manifest = precompute_manifest()
    if args.approved_run:
        if args.compute_plan is None:
            raise SystemExit("--approved-run requires --compute-plan")
        print(json.dumps(_run_approved_acquisition(manifest, args.compute_plan), sort_keys=True), flush=True)
        return
    print(json.dumps({
        "status": manifest["status"],
        "manifest_path": str(F85_MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
        "manifest_sha256": manifest["manifest_sha256"],
        "train_root_count": manifest["execution_contract"]["train_root_count"],
        "total_declared_node_ceiling": manifest["total_declared_node_ceiling"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
