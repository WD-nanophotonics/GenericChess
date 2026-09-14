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
from generic_chess.core.actions import action_to_dict  # noqa: E402


LABEL = "B_CANONICAL_STANDARD_SHOGI"
WORK_ORDER = "GENERICCHESS-F85A-C2-TRAIN-TEACHER-ACQUISITION-HARNESS-AND-LARGE-PLAN"
F83_ROOT_SET_ID = "c197799729877dc836116740d0827de0b02cfabde42e45c8e53e19f61c3ee108"
F84_CALIBRATION_SHA = "9fd8eb417a71fb1c5e7af5225c84fb73facb0549eeaae229a6923e7be8a4677b"
F85_PRECOMPUTE_SOURCE_SHA = "e54ff8f4ca05ee3eb33a9a693d8577a99992b991"
ROOT_BUDGETS = (2000, 40000, 80000)
OBSERVER_ROOT_BUDGET = 2000
CHILD_BUDGETS = {"all_legal": 1000, "selected_mid": 10000, "selected_high": 20000}
MAX_SELECTED_ACTIONS = 9
FROZEN_MANIFEST_MAX_CONCURRENT_ROOTS = 2
MAX_CONCURRENT_ROOTS = 2
PER_ROOT_WALL_SECONDS = 720
F85_MANIFEST_PATH = ROOT / "artifacts/f85_c2_train_teacher_evidence/train_precompute_manifest.json"
F85_RUNTIME_DIR = ROOT / ".generic_chess_flow/f85-c2-train-teacher-acquisition"
MINIMAL_MANIFEST_PATH = ROOT / "artifacts/f85_c2_train_teacher_evidence/minimal_train_manifest.json"
MINIMAL_MODE = "f85-minimal-teacher-rows-v1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_sha(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except FileNotFoundError:
        path.parent.mkdir(parents=True, exist_ok=True)
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
        "sandbox_sha": F85_PRECOMPUTE_SOURCE_SHA,
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
            "max_concurrent_roots": FROZEN_MANIFEST_MAX_CONCURRENT_ROOTS,
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


def _minimal_teacher_unit(compiled, native, parent, record: dict, *, smoke: bool = False) -> dict:
    """Training-equivalent F85 rows without diagnostic-only F59 searches."""
    root_budget = 50 if smoke else 2_000
    high_root_budget = 200 if smoke else 80_000
    cheap_budget = 50 if smoke else 1_000
    teacher_budget = 200 if smoke else 20_000
    session = f59._session(compiled, record)
    legal = sorted(session.legal_actions(), key=lambda action: json.dumps(action_to_dict(action), sort_keys=True))
    root_2k = f59._root_search(compiled, native, parent, record, root_budget)
    root_80k = f59._root_search(compiled, native, parent, record, high_root_budget)
    legal_payloads = [action_to_dict(action) for action in legal]
    cheap = f59._parallel_children(compiled, native, parent, record, legal_payloads, cheap_budget)
    order = sorted(range(len(legal)), key=lambda index: (-cheap[index], json.dumps(legal_payloads[index], sort_keys=True)))
    selected = [legal_payloads[index] for index in order[:3 if smoke else 6]]
    selected_keys = {f59._action_key(action) for action in selected}
    for payload in (root_2k["action"], root_80k["action"]):
        if payload is not None and f59._action_key(payload) not in selected_keys:
            selected.append(payload)
            selected_keys.add(f59._action_key(payload))
    prepared = []
    for payload in selected:
        features, base_q, _side = f59._child_features(compiled, native, parent, record, payload)
        prepared.append({"action": payload, "action_key": f59._action_key(payload), "features": features.tolist(), "base_q": base_q})
    q20 = f59._parallel_children(compiled, native, parent, record, [row["action"] for row in prepared], teacher_budget)
    cheap_by_key = {f59._action_key(payload): float(value) for payload, value in zip(legal_payloads, cheap)}
    rows = []
    for row, value in zip(prepared, q20):
        rows.append({**row, "q_1k": cheap_by_key[row["action_key"]], "q_20k": float(value)})
    return {
        "position_key": record["position_key"],
        "selected_action_count": len(rows),
        "actual_search_calls": 2 + len(legal) + len(rows),
        "actual_teacher_calls": len(rows),
        "teacher_rows": rows,
        "root_metadata": {"root_2k": root_2k, "root_80k": root_80k, "legal_action_count": len(legal), "cheap_top_actions": [legal_payloads[index] for index in order[:6]]},
    }


def _minimal_manifest(manifest: dict) -> dict:
    rows = []
    for record in manifest["roots"]:
        selected_upper = min(MAX_SELECTED_ACTIONS, 6 + 2)
        ceiling = 2_000 + 80_000 + 1_000 * record["legal_action_count"] + 20_000 * selected_upper
        rows.append({**record, "declared_node_ceiling": ceiling, "maximum_search_calls": 2 + record["legal_action_count"] + selected_upper, "minimal_formula": "2000 + 80000 + 1000*L + 20000*S", "maximum_selected_actions": selected_upper, "maximum_teacher_calls": selected_upper})
    payload = {
        "schema": "generic-chess-f85-minimal-teacher-rows-manifest-v1",
        "work_order": "GENERICCHESS-F85B-C2-MINIMAL-RESUMABLE-TEACHER-ROWS",
        "status": "PRECOMPUTE_COMPLETE_ACQUISITION_NOT_AUTHORIZED",
        "source_manifest_sha256": _sha(F85_MANIFEST_PATH),
        "c1_checkpoint_id": f83.C1_ID,
        "c1_model_sha256": f83.C1_MODEL_SHA,
        "teacher_contract": {"root_budgets": [2_000, 80_000], "child_budget_all_legal": 1_000, "child_budget_selected": 20_000, "max_depth": 12, "tt_megabytes": 8, "root_window_pruning": False, "observer_duplicate_omitted": True, "diagnostic_calls_omitted": ["root_40k", "observer_2k", "selected_q10k"]},
        "execution_contract": {"train_root_count": 36, "max_concurrent_roots": 2, "stage_count": 1, "no_auto_retry": True, "wall_cap_authority": "approved_compute_plan.resource_envelope.per_root_wall_seconds"},
        "total_declared_node_ceiling": sum(row["declared_node_ceiling"] for row in rows),
        "roots": rows,
    }
    payload["manifest_sha256"] = _stable_sha(payload)
    if MINIMAL_MANIFEST_PATH.exists() and json.loads(MINIMAL_MANIFEST_PATH.read_text(encoding="utf-8")) != payload:
        raise RuntimeError("minimal F85 manifest identity mismatch")
    _atomic_json(MINIMAL_MANIFEST_PATH, payload)
    return payload


def _phase_provenance(record: dict, *, plan_sha: str, manifest_sha: str) -> dict:
    return {"mode": MINIMAL_MODE, "compute_plan_sha256": plan_sha, "manifest_content_sha256": manifest_sha, "root_record_sha256": _stable_sha(record), "root_id": record["root_id"], "position_key": record["position_key"], "c1_checkpoint_id": f83.C1_ID, "c1_model_sha256": f83.C1_MODEL_SHA}


def _run_minimal_root(record: dict, *, plan_sha: str, manifest_sha: str, runtime_dir: Path, compiled, native, parent, stop_after: str | None = None) -> dict:
    root_dir = runtime_dir / record["root_id"]
    root_dir.mkdir(parents=True, exist_ok=True)
    provenance = _phase_provenance(record, plan_sha=plan_sha, manifest_sha=manifest_sha)

    def load(phase: str):
        path = root_dir / f"{phase}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "COMPLETE" or payload.get("provenance") != provenance:
            raise RuntimeError(f"STALE_PHASE_PROVENANCE:{record['root_id']}:{phase}")
        return payload["value"]

    def save(phase: str, value):
        _atomic_json(root_dir / f"{phase}.json", {"status": "COMPLETE", "provenance": provenance, "value": value})

    root_2k = load("root2k")
    if root_2k is None:
        root_2k = f59._root_search(compiled, native, parent, record, 2_000)
        save("root2k", root_2k)
    if stop_after == "root2k":
        return {"status": "PAUSED", "phase": "root2k"}
    root_80k = load("root80k")
    if root_80k is None:
        root_80k = f59._root_search(compiled, native, parent, record, 80_000)
        save("root80k", root_80k)
    if stop_after == "root80k":
        return {"status": "PAUSED", "phase": "root80k"}
    all_legal = load("all_legal_q1k")
    session = f59._session(compiled, record)
    legal = sorted(session.legal_actions(), key=lambda action: json.dumps(action_to_dict(action), sort_keys=True))
    legal_payloads = [action_to_dict(action) for action in legal]
    if all_legal is None:
        values = f59._parallel_children(compiled, native, parent, record, legal_payloads, 1_000)
        all_legal = {"actions": legal_payloads, "q1k": [float(value) for value in values]}
        save("all_legal_q1k", all_legal)
    if stop_after == "all_legal_q1k":
        return {"status": "PAUSED", "phase": "all_legal_q1k"}
    selected = load("selected_q20")
    if selected is None:
        order = sorted(range(len(legal_payloads)), key=lambda index: (-all_legal["q1k"][index], json.dumps(legal_payloads[index], sort_keys=True)))
        selected_payloads = [legal_payloads[index] for index in order[:6]]
        selected_keys = {f59._action_key(payload) for payload in selected_payloads}
        for payload in (root_2k["action"], root_80k["action"]):
            if payload is not None and f59._action_key(payload) not in selected_keys:
                selected_payloads.append(payload)
                selected_keys.add(f59._action_key(payload))
        prepared = []
        for payload in selected_payloads:
            features, base_q, _side = f59._child_features(compiled, native, parent, record, payload)
            prepared.append({"action": payload, "action_key": f59._action_key(payload), "features": features.tolist(), "base_q": base_q})
        q20 = f59._parallel_children(compiled, native, parent, record, selected_payloads, 20_000)
        selected = {"rows": [{**row, "q_20k": float(value)} for row, value in zip(prepared, q20)]}
        save("selected_q20", selected)
    if stop_after == "selected_q20":
        return {"status": "PAUSED", "phase": "selected_q20"}
    final = load("assembled")
    if final is None:
        q1k_by_key = {f59._action_key(payload): float(value) for payload, value in zip(all_legal["actions"], all_legal["q1k"])}
        rows = [{**row, "q_1k": q1k_by_key[row["action_key"]]} for row in selected["rows"]]
        final = {"root_id": record["root_id"], "position_key": record["position_key"], "role": record["role"], "stratum": record["stratum"], "selected_action_count": len(rows), "actual_teacher_calls": len(rows), "actual_search_calls": 2 + len(legal) + len(rows), "teacher_rows": rows, "root_metadata": {"root_2k": root_2k, "root_80k": root_80k, "legal_action_count": len(legal)}}
        save("assembled", final)
    return {"status": "COMPLETE", **final}


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


def _run_teacher_one(record: dict, wall_seconds: int = PER_ROOT_WALL_SECONDS) -> dict:
    context = mp.get_context("spawn")
    result_queue = context.Queue()
    process = context.Process(target=_teacher_worker, args=(record, result_queue))
    process.start()
    process.join(wall_seconds)
    if process.is_alive():
        process.terminate()
        process.join(5)
        return {"status": "TIME_CAP", "termination_reason": "per_root_wall_cap"}
    try:
        return result_queue.get(timeout=1)
    except queue_module.Empty:
        return {"status": "HARNESS_MISMATCH", "error": f"worker exited with code {process.exitcode}"}


def _unit_provenance(record: dict, *, plan_sha: str, manifest_sha: str) -> dict:
    return {
        "compute_plan_sha256": plan_sha,
        "manifest_content_sha256": manifest_sha,
        "root_record_sha256": _stable_sha(record),
        "root_id": record["root_id"],
        "position_key": record["position_key"],
        "stratum": record["stratum"],
        "role": record["role"],
        "c1_checkpoint_id": f83.C1_ID,
        "c1_model_sha256": f83.C1_MODEL_SHA,
        "f59_script_sha256": _sha(ROOT / "scripts/f59_action_spectrum_diagnosis.py"),
        "f62_script_sha256": _sha(ROOT / "scripts/f62_learned_champion_repeatability.py"),
    }


def _execution_record(record: dict, source_by_id: dict[str, dict]) -> dict:
    source = source_by_id[record["root_id"]]
    return {
        **record,
        "action_history": source["action_history"],
        "replay_actions": source["replay_actions"],
    }


def _run_approved_acquisition(
    manifest: dict,
    compute_plan_path: Path,
    *,
    runtime_dir: Path | None = None,
    evidence_path: Path | None = None,
    runner=None,
    max_concurrent_roots: int = MAX_CONCURRENT_ROOTS,
    per_root_wall_seconds: int = PER_ROOT_WALL_SECONDS,
) -> dict:
    """Run each frozen train root once; this path is only for an approved plan."""
    plan_sha = _sha(compute_plan_path)
    manifest_sha = _sha(F85_MANIFEST_PATH)
    runtime_root = F85_RUNTIME_DIR if runtime_dir is None else Path(runtime_dir)
    progress_dir = runtime_root / plan_sha / "progress"
    progress_dir.mkdir(parents=True, exist_ok=True)
    root_payload = json.loads((ROOT / "artifacts/f83_c1_relative_evidence/root_corpus.json").read_text(encoding="utf-8"))
    source_by_id = {root["root_id"]: root for root in root_payload["roots"]}
    run_one = (lambda record: _run_teacher_one(record, per_root_wall_seconds)) if runner is None else runner
    completed = []
    pending = []
    for record in manifest["roots"]:
        path = progress_dir / f"{record['root_id']}.json"
        if path.exists():
            prior = json.loads(path.read_text(encoding="utf-8"))
            expected = _unit_provenance(record, plan_sha=plan_sha, manifest_sha=manifest_sha)
            if prior.get("provenance") != expected:
                return {"status": "HARNESS_MISMATCH", "reason": "STALE_PROGRESS_PROVENANCE", "root_id": record["root_id"]}
            if prior.get("status") == "COMPLETE":
                completed.append(prior)
                continue
            if prior.get("status") in {"TIME_CAP", "HARNESS_MISMATCH"}:
                return {
                    "status": "INCOMPLETE",
                    "reason": "RETRY_REQUIRES_NEW_AUTHORIZATION",
                    "completed_count": len(completed),
                    "root_id": record["root_id"],
                }
            return {"status": "HARNESS_MISMATCH", "reason": "UNKNOWN_PROGRESS_STATUS", "root_id": record["root_id"]}
        pending.append(record)
    results = []
    if max_concurrent_roots != MAX_CONCURRENT_ROOTS:
        raise RuntimeError("acquisition runner requires the authorized two-lane geometry")
    for start in range(0, len(pending), max_concurrent_roots):
        batch = pending[start:start + max_concurrent_roots]
        execution_batch = [_execution_record(record, source_by_id) for record in batch]
        with ThreadPoolExecutor(max_workers=max_concurrent_roots) as pool:
            batch_results = list(pool.map(run_one, execution_batch))
        batch_failed = False
        for record, result in zip(batch, batch_results):
            provenance = _unit_provenance(record, plan_sha=plan_sha, manifest_sha=manifest_sha)
            row = {
                "root_id": record["root_id"],
                "position_key": record["position_key"],
                "stratum": record["stratum"],
                "role": record["role"],
                "provenance": provenance,
                **result,
            }
            path = progress_dir / f"{record['root_id']}.json"
            if row["status"] == "COMPLETE":
                if row.get("position_key") != record["position_key"]:
                    row = {"root_id": record["root_id"], "status": "HARNESS_MISMATCH", "provenance": provenance, "error": "worker position identity mismatch"}
                    batch_failed = True
                else:
                    _atomic_json(path, row)
                    completed.append(row)
            else:
                row.pop("teacher_rows", None)
                row.pop("root_metadata", None)
                _atomic_json(path, row)
                batch_failed = True
            results.append(row)
        if batch_failed:
            return {
                "status": "INCOMPLETE",
                "reason": "TERMINAL_ROOT_REQUIRES_NEW_AUTHORIZATION",
                "completed_count": len(completed),
                "results": results,
            }
    all_rows = sorted(completed, key=lambda row: row["root_id"])
    if len(all_rows) != 36 or any(row.get("status") != "COMPLETE" for row in all_rows):
        return {"status": "INCOMPLETE", "completed_count": len(all_rows), "results": results}
    evidence = {
        "schema": "generic-chess-f85-c2-train-teacher-evidence-v1",
        "work_order": WORK_ORDER,
        "status": "COMPLETE_TRAIN_TEACHER_EVIDENCE_SEALED",
        "manifest_content_sha256": manifest_sha,
        "compute_plan_sha256": plan_sha,
        "c1_checkpoint_id": f83.C1_ID,
        "c1_model_sha256": f83.C1_MODEL_SHA,
        "f59_script_sha256": _sha(ROOT / "scripts/f59_action_spectrum_diagnosis.py"),
        "f62_script_sha256": _sha(ROOT / "scripts/f62_learned_champion_repeatability.py"),
        "root_count": 36,
        "roots": all_rows,
    }
    _atomic_json(evidence_path or (ROOT / "artifacts/f85_c2_train_teacher_evidence/training_evidence.json"), evidence)
    return {"status": evidence["status"], "completed_count": 36}


def _validate_execution_plan(plan_path: Path, manifest: dict) -> tuple[dict, str]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan_sha = _sha(plan_path)
    if plan.get("sandbox_sha") != _git_sha() or plan.get("precompute_manifest_sha256") != _sha(F85_MANIFEST_PATH):
        raise RuntimeError("approved compute plan is stale or not bound to the exact precompute manifest")
    envelope = plan.get("resource_envelope", {})
    lanes = envelope.get("intended_cpu_lanes")
    if lanes != MAX_CONCURRENT_ROOTS:
        raise RuntimeError("approved compute plan root concurrency differs from the authorized two-lane geometry")
    return plan, plan_sha


def _minimal_root_worker(record: dict, *, plan_sha: str, manifest_sha: str, runtime_dir: Path, result_queue) -> None:
    try:
        compiled, native, _profile = f50._ruleset(LABEL)
        _parent, champion, _descriptor = f79._load_frozen_candidate(compiled)
        result = _run_minimal_root(record, plan_sha=plan_sha, manifest_sha=manifest_sha, runtime_dir=runtime_dir, compiled=compiled, native=native, parent=champion)
        result_queue.put({"status": result.get("status", "HARNESS_MISMATCH"), "root_id": record["root_id"]})
    except BaseException as exc:  # pragma: no cover - bounded worker failure path
        result_queue.put({"status": "HARNESS_MISMATCH", "root_id": record["root_id"], "error": f"{type(exc).__name__}: {exc}"})


def _run_minimal_root_bounded(record: dict, *, plan_sha: str, manifest_sha: str, runtime_dir: Path, wall_seconds: int) -> dict:
    context = mp.get_context("spawn")
    result_queue = context.Queue()
    process = context.Process(target=_minimal_root_worker, kwargs={"record": record, "plan_sha": plan_sha, "manifest_sha": manifest_sha, "runtime_dir": runtime_dir, "result_queue": result_queue})
    process.start()
    process.join(wall_seconds)
    if process.is_alive():
        process.terminate()
        process.join(5)
        return {"status": "TIME_CAP", "root_id": record["root_id"], "termination_reason": "per_root_wall_cap"}
    try:
        return result_queue.get(timeout=2)
    except queue_module.Empty:
        return {"status": "HARNESS_MISMATCH", "root_id": record["root_id"], "error": f"worker exited with code {process.exitcode}"}


def _run_approved_minimal(manifest: dict, compute_plan_path: Path, *, runtime_dir: Path | None = None, per_root_wall_seconds: int) -> dict:
    """Run the phase-resumable minimal path; no F59 diagnostic extras."""
    plan_sha = _sha(compute_plan_path)
    manifest_sha = _sha(MINIMAL_MANIFEST_PATH)
    runtime_root = F85_RUNTIME_DIR if runtime_dir is None else Path(runtime_dir)
    progress_root = runtime_root / plan_sha / "minimal-progress"
    progress_root.mkdir(parents=True, exist_ok=True)
    root_payload = json.loads((ROOT / "artifacts/f83_c1_relative_evidence/root_corpus.json").read_text(encoding="utf-8"))
    source_by_id = {root["root_id"]: root for root in root_payload["roots"]}
    completed = []
    pending = []
    for record in manifest["roots"]:
        assembled = progress_root / record["root_id"] / "assembled.json"
        if assembled.exists():
            payload = json.loads(assembled.read_text(encoding="utf-8"))
            expected = _phase_provenance(record, plan_sha=plan_sha, manifest_sha=manifest_sha)
            if payload.get("provenance") != expected or payload.get("status") != "COMPLETE":
                return {"status": "HARNESS_MISMATCH", "reason": "STALE_PHASE_PROVENANCE", "root_id": record["root_id"]}
            completed.append(payload["value"])
        else:
            pending.append(record)
    for start in range(0, len(pending), MAX_CONCURRENT_ROOTS):
        batch = pending[start:start + MAX_CONCURRENT_ROOTS]
        results = []
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_ROOTS) as pool:
            futures = [pool.submit(_run_minimal_root_bounded, {**record, **_execution_record(record, source_by_id)}, plan_sha=plan_sha, manifest_sha=manifest_sha, runtime_dir=progress_root, wall_seconds=per_root_wall_seconds) for record in batch]
            for record, future in zip(batch, futures):
                try:
                    result = future.result()
                except BaseException as exc:  # pragma: no cover - bounded worker failure path
                    result = {"status": "HARNESS_MISMATCH", "error": f"{type(exc).__name__}: {exc}"}
                results.append({"root_id": record["root_id"], **result})
                if result.get("status") == "COMPLETE":
                    assembled = progress_root / record["root_id"] / "assembled.json"
                    if not assembled.exists():
                        results[-1] = {"root_id": record["root_id"], "status": "HARNESS_MISMATCH", "error": "assembled phase missing"}
                    else:
                        completed.append(json.loads(assembled.read_text(encoding="utf-8"))["value"])
        if any(result.get("status") != "COMPLETE" for result in results):
            return {"status": "INCOMPLETE", "reason": "TERMINAL_PHASE_REQUIRES_NEW_AUTHORIZATION", "completed_count": len(completed), "results": results}
    if len(completed) != len(manifest["roots"]):
        return {"status": "INCOMPLETE", "completed_count": len(completed)}
    evidence = {"schema": "generic-chess-f85-minimal-teacher-rows-v1", "status": "COMPLETE_TRAIN_TEACHER_EVIDENCE_SEALED", "compute_plan_sha256": plan_sha, "minimal_manifest_sha256": manifest_sha, "c1_checkpoint_id": f83.C1_ID, "c1_model_sha256": f83.C1_MODEL_SHA, "root_count": len(completed), "roots": sorted(completed, key=lambda row: row["root_id"])}
    path = ROOT / "artifacts/f85_c2_train_teacher_evidence/training_evidence.json"
    _atomic_json(path, evidence)
    return {"status": evidence["status"], "completed_count": len(completed), "evidence_path": str(path.relative_to(ROOT)).replace("\\", "/")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--precompute-only", action="store_true")
    parser.add_argument("--approved-run", action="store_true")
    parser.add_argument("--compute-plan", type=Path)
    parser.add_argument("--per-root-wall-seconds", type=int, default=PER_ROOT_WALL_SECONDS)
    parser.add_argument("--minimal-rows", action="store_true")
    args = parser.parse_args()
    if not args.precompute_only and not args.approved_run:
        raise SystemExit("F85 teacher acquisition is withheld until the separately approved large plan is bound")
    manifest = precompute_manifest()
    if args.minimal_rows:
        minimal = _minimal_manifest(manifest)
        if not args.approved_run:
            print(json.dumps({"status": minimal["status"], "manifest_path": str(MINIMAL_MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"), "manifest_sha256": minimal["manifest_sha256"], "total_declared_node_ceiling": minimal["total_declared_node_ceiling"]}, sort_keys=True), flush=True)
            return
        if args.compute_plan is None:
            raise SystemExit("--minimal-rows --approved-run requires --compute-plan")
        plan, plan_sha = _validate_execution_plan(args.compute_plan, minimal)
        envelope = plan.get("resource_envelope", {})
        if plan.get("minimal_manifest_sha256") != _sha(MINIMAL_MANIFEST_PATH) or envelope.get("minimal_manifest_sha256") != _sha(MINIMAL_MANIFEST_PATH):
            raise SystemExit("approved minimal compute plan is not bound to the minimal manifest")
        if envelope.get("intended_cpu_lanes") != MAX_CONCURRENT_ROOTS or envelope.get("maximum_nodes") != minimal["total_declared_node_ceiling"] or envelope.get("effective_workload") != {"games": 0, "arena_pairs": 0, "plies": 0}:
            raise SystemExit("approved minimal compute plan resource envelope mismatch")
        wall_seconds = envelope.get("per_root_wall_seconds")
        if not isinstance(wall_seconds, int) or wall_seconds <= 0:
            raise SystemExit("approved minimal compute plan requires a positive per-root wall cap")
        result = _run_approved_minimal(minimal, args.compute_plan, per_root_wall_seconds=wall_seconds)
        result["compute_plan_sha256"] = plan_sha
        print(json.dumps(result, sort_keys=True), flush=True)
        return
    if args.approved_run:
        if args.compute_plan is None:
            raise SystemExit("--approved-run requires --compute-plan")
        try:
            plan, plan_sha = _validate_execution_plan(args.compute_plan, manifest)
        except RuntimeError as exc:
            raise SystemExit(str(exc))
        lanes = plan["resource_envelope"]["intended_cpu_lanes"]
        if args.per_root_wall_seconds < PER_ROOT_WALL_SECONDS:
            raise SystemExit("--per-root-wall-seconds cannot reduce the registered cap")
        result = _run_approved_acquisition(manifest, args.compute_plan, max_concurrent_roots=lanes, per_root_wall_seconds=args.per_root_wall_seconds)
        result["compute_plan_sha256"] = plan_sha
        print(json.dumps(result, sort_keys=True), flush=True)
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
