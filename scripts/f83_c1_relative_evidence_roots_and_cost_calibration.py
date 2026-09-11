"""F83: freeze C1-relative roots and calibrate the tracked F62 teacher cost.

This work order deliberately stops after acquisition and six resource-only
teacher probes.  It never fits C2, creates a candidate, or runs strength play.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import random
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LABEL = "B_CANONICAL_STANDARD_SHOGI"
WORK_ORDER = "GENERICCHESS-F83-C1-RELATIVE-EVIDENCE-ROOTS-AND-COST-CALIBRATION"
C1_ID = "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
C1_MODEL_SHA = "b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6"
F62_STAGE_SHA = "e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70"
F62_RECORDS_SHA = "b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61"
F83_ORIGINAL_PROBE_ARTIFACT_SHA = "3b05ff6d999928f97906b4eedae611b5c15b50ae06786cbb674cfaef3063e2ab"
SEEDS = {
    "reachable_random": 830501,
    "c1_on_policy": 830502,
    "c1_pv_corridor": 830503,
    "resource_probe": 830599,
}
ACQUISITION_PER_STRATUM = 16
RESOURCE_PER_STRATUM = 2
ACQUISITION_TRAIN_PER_STRATUM = 12
ACQUISITION_DEV_PER_STRATUM = 4
PROBE_PER_ROOT_WALL_SECONDS = 180
PROBE_MAX_CONCURRENCY = 2
PROBE_ROOT_COUNT = 6
PROBE_HARD_WALL_SECONDS = 12 * 60
PV_OFFSET_RULE = "max(1, min(len(pv)-1, len(pv)//2))"

ROOT_CORPUS_PATH = ROOT / "artifacts" / "f83_c1_relative_evidence" / "root_corpus.json"
PROBE_PATH = ROOT / "artifacts" / "f83_c1_relative_evidence" / "teacher_cost_probe.json"
F62_MANIFEST_PATH = ROOT / "artifacts" / "f83_c1_relative_evidence" / "f62_historical_root_identity_manifest.json"
F78_CANDIDATE = ROOT / "artifacts" / "f78_parent_anchored_full_residual" / "candidate.json"
F81_EVIDENCE = ROOT / "artifacts" / "f81_final_confirmation" / "final_strength_evidence.json"
F81_OPENINGS = ROOT / "artifacts" / "f81_final_confirmation" / "openings.json"
F75_OPENINGS = ROOT / "artifacts" / "f75_parent_retained_arena" / "openings.json"
F77_OPENINGS = ROOT / "artifacts" / "f77_trusted_pointwise_q_arena" / "openings.json"
F78_OPENINGS = ROOT / "artifacts" / "f78_parent_anchored_full_residual" / "openings.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_sha(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _action_key(action) -> str:
    from generic_chess.core.actions import action_to_dict
    return json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))


def _preflight() -> dict:
    from generic_chess.learning.serialization import stable_sha256

    adoption = json.loads((ROOT / "artifacts/f82_champion_adoption/champion.json").read_text(encoding="utf-8"))
    if adoption.get("status") != "C1_CHAMPION_ADOPTED_REPEATABILITY_PROTOCOL_FROZEN":
        raise RuntimeError("F83 champion adoption status mismatch")
    if adoption.get("adopted_champion") != C1_ID or adoption.get("model_sha256") != C1_MODEL_SHA:
        raise RuntimeError("F83 C1 authority mismatch")
    for path_key, expected in (
        ("source_f78_candidate", adoption["source_f78_candidate"]["content_sha256"]),
        ("source_f81_canonical_evidence", adoption["source_f81_canonical_evidence"]["content_sha256"]),
        ("source_f81_final_decision_bound", adoption["source_f81_final_decision_bound"]["content_sha256"]),
    ):
        path = ROOT / adoption[path_key]["path"]
        if _sha(path) != expected:
            raise RuntimeError(f"F83 {path_key} content SHA mismatch")
    descriptor = json.loads(F78_CANDIDATE.read_text(encoding="utf-8"))
    if stable_sha256(descriptor["final_compact_nonlinear"]) != C1_MODEL_SHA:
        raise RuntimeError("F83 F78 candidate model identity mismatch")
    if _sha(F81_EVIDENCE) != adoption["source_f81_canonical_evidence"]["content_sha256"]:
        raise RuntimeError("F83 F81 evidence identity mismatch")
    return {
        "adoption_path": str((ROOT / "artifacts/f82_champion_adoption/champion.json").relative_to(ROOT)).replace("\\", "/"),
        "adoption_sha256": _sha(ROOT / "artifacts/f82_champion_adoption/champion.json"),
        "c1_checkpoint_id": C1_ID,
        "c1_model_sha256": C1_MODEL_SHA,
        "f78_candidate_path": str(F78_CANDIDATE.relative_to(ROOT)).replace("\\", "/"),
        "f78_candidate_sha256": _sha(F78_CANDIDATE),
        "f81_evidence_path": str(F81_EVIDENCE.relative_to(ROOT)).replace("\\", "/"),
        "f81_evidence_sha256": _sha(F81_EVIDENCE),
    }


def _load_sealed_position_keys(f62_keys: set[str]) -> dict[str, set[str]]:
    sealed: dict[str, set[str]] = {}
    for name, path in {
        "f75": F75_OPENINGS,
        "f77": F77_OPENINGS,
        "f78_f80": F78_OPENINGS,
        "f81": F81_OPENINGS,
    }.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        sealed[name] = {item["final_position_key"] for item in payload["corpus"]["openings"]}
    if len(f62_keys) < 96:
        raise RuntimeError("F83 F62 historical root identity set is incomplete")
    sealed["f62"] = f62_keys
    return sealed


def _session(compiled, actions):
    from generic_chess.core.actions import action_from_dict
    from generic_chess.session.session import GameSession
    session = GameSession(compiled)
    for action in actions:
        session.submit(action_from_dict(action) if isinstance(action, dict) else action)
    return session


def _record(session, *, stratum: str, seed: int, attempt: int, generation: dict) -> dict:
    from generic_chess.core.actions import action_to_dict
    from generic_chess.core.identity import position_identity_key
    return {
        "stratum": stratum,
        "source_seed": seed,
        "attempt": attempt,
        "position_key": position_identity_key(session.state.position, session.compiled),
        "side_to_move": int(session.state.position.side_to_move),
        "ply": int(session.state.ply_count),
        "action_history": [action_to_dict(entry.action) for entry in session.history],
        "replay_actions": [action_to_dict(entry.action) for entry in session.history],
        "generation": generation,
    }


def _canonical_actions(session):
    return sorted(session.legal_actions(), key=_action_key)


def _random_prefix(compiled, seed: int, attempt: int):
    from generic_chess.session.session import GameSession
    rng = random.Random(seed * 100000 + attempt)
    target = rng.randint(2, 6)
    session = GameSession(compiled)
    actions = []
    for _ in range(target):
        legal = _canonical_actions(session)
        if not legal or session.result.status.value != "ongoing":
            return None
        action = legal[rng.randrange(len(legal))]
        session.submit(action)
        actions.append(action)
    return session, actions, target


def _search(compiled, native, checkpoint, session, *, nodes: int, depth: int):
    from generic_chess.ai.limits import SearchLimits
    from generic_chess.native.semantic_engine import SemanticSearchEngine
    return SemanticSearchEngine(compiled, native, checkpoint=checkpoint, tt_megabytes=8).search(
        session, SearchLimits(max_depth=depth, max_nodes=nodes, quiescence_max_depth=0), root_window_pruning=True
    )


def _reachable_candidate(compiled, seed: int, attempt: int):
    from generic_chess.session.session import GameSession
    rng = random.Random(seed * 100000 + attempt)
    target = rng.randint(8, 24)
    session = GameSession(compiled)
    for _ in range(target):
        legal = _canonical_actions(session)
        if not legal or session.result.status.value != "ongoing":
            return None
        session.submit(legal[rng.randrange(len(legal))])
    if session.result.status.value != "ongoing":
        return None
    return _record(session, stratum="reachable_random", seed=seed, attempt=attempt, generation={"policy": "core_legal_prng", "target_plies": target})


def _on_policy_candidate(compiled, native, champion, seed: int, attempt: int):
    prefix = _random_prefix(compiled, seed, attempt)
    if prefix is None:
        return None
    session, _actions, prefix_plies = prefix
    for _ in range(6):
        result = _search(compiled, native, champion, session, nodes=128, depth=10)
        if result.action is None or result.action not in session.legal_actions():
            return None
        session.submit(result.action)
        if session.result.status.value != "ongoing":
            return None
    return _record(session, stratum="c1_on_policy", seed=seed, attempt=attempt, generation={
        "policy": "independent_random_prefix_then_c1_product_search",
        "prefix_plies": prefix_plies,
        "c1_search": {"nodes_per_move": 128, "max_depth": 10, "tt_megabytes": 8, "root_window_pruning": True},
        "search_plies": 6,
    })


def _pv_candidate(compiled, native, champion, seed: int, attempt: int):
    prefix = _random_prefix(compiled, seed, attempt)
    if prefix is None:
        return None
    session, _actions, prefix_plies = prefix
    result = _search(compiled, native, champion, session, nodes=512, depth=12)
    pv = list(result.principal_variation)
    if len(pv) < 2:
        return None
    offset = max(1, min(len(pv) - 1, len(pv) // 2))
    for action in pv[:offset]:
        if action not in session.legal_actions():
            return None
        session.submit(action)
        if session.result.status.value != "ongoing":
            return None
    return _record(session, stratum="c1_pv_corridor", seed=seed, attempt=attempt, generation={
        "policy": "independent_random_prefix_then_c1_principal_variation",
        "prefix_plies": prefix_plies,
        "c1_search": {"nodes": 512, "max_depth": 12, "tt_megabytes": 8, "root_window_pruning": True},
        "pv_length": len(pv),
        "pv_offset": offset,
        "pv_offset_rule": PV_OFFSET_RULE,
    })


def _collect(compiled, native, champion, stratum: str, count: int, seed: int, sealed: dict[str, set[str]], seen: set[str]) -> list[dict]:
    generator = {
        "reachable_random": lambda attempt: _reachable_candidate(compiled, seed, attempt),
        "c1_on_policy": lambda attempt: _on_policy_candidate(compiled, native, champion, seed, attempt),
        "c1_pv_corridor": lambda attempt: _pv_candidate(compiled, native, champion, seed, attempt),
    }[stratum]
    roots = []
    attempt = 0
    while len(roots) < count:
        if attempt > 1000:
            raise RuntimeError(f"F83 {stratum} could not fill {count} roots")
        candidate = generator(attempt)
        attempt += 1
        if candidate is None:
            continue
        key = candidate["position_key"]
        if key in seen or any(key in keys for keys in sealed.values()):
            continue
        seen.add(key)
        candidate["local_index"] = len(roots)
        roots.append(candidate)
    return roots


def _historical_overlap(roots: list[dict], sealed: dict[str, set[str]]) -> dict[str, int]:
    return {name: sum(root["position_key"] in keys for root in roots) for name, keys in sealed.items()}


def _tracked_f62_manifest(compiled) -> dict:
    from scripts import f62_learned_champion_repeatability as f62

    records, provenance = f62._fresh_records(compiled, smoke=False)
    if provenance["records_sha256"] != F62_RECORDS_SHA or len(records) != 96:
        raise RuntimeError("F83 tracked F62 record identity mismatch")
    manifest = {
        "schema": "generic-chess-f83-f62-historical-root-identity-v1",
        "work_order": WORK_ORDER,
        "f62_stage_identity_sha256": F62_STAGE_SHA,
        "f62_records_sha256": F62_RECORDS_SHA,
        "generation_contract": {
            "opening_seed": f62.DATA_OPENING_SEED,
            "corpus_seed": f62.DATA_CORPUS_SEED,
            "root_count": f62.ROOT_COUNT,
            "source_group_count": f62.SOURCE_GROUP_COUNT,
            "roots_per_source_group": f62.ROOTS_PER_GROUP,
            "split_root_counts": {"fit": 48, "development": 24, "final_holdout": 24},
        },
        "source_paths": {
            "f62_script": "scripts/f62_learned_champion_repeatability.py",
            "f62_script_sha256": _sha(ROOT / "scripts/f62_learned_champion_repeatability.py"),
            "f59_teacher_script": "scripts/f59_action_spectrum_diagnosis.py",
            "f59_teacher_script_sha256": _sha(ROOT / "scripts/f59_action_spectrum_diagnosis.py"),
        },
        "provenance": provenance,
        "position_keys": [record["position_key"] for record in records],
    }
    if F62_MANIFEST_PATH.exists():
        existing = json.loads(F62_MANIFEST_PATH.read_text(encoding="utf-8"))
        if existing != manifest:
            raise RuntimeError("F83 tracked F62 manifest identity mismatch")
    else:
        _atomic_json(F62_MANIFEST_PATH, manifest)
    return manifest


def _root_corpus(preflight: dict, compiled, native, champion) -> dict:
    f62_manifest = _tracked_f62_manifest(compiled)
    sealed = _load_sealed_position_keys(set(f62_manifest["position_keys"]))
    seen: set[str] = set()
    acquisition = []
    for stratum in ("reachable_random", "c1_on_policy", "c1_pv_corridor"):
        acquisition.extend(_collect(compiled, native, champion, stratum, ACQUISITION_PER_STRATUM, SEEDS[stratum], sealed, seen))
    resource = []
    for stratum in ("reachable_random", "c1_on_policy", "c1_pv_corridor"):
        resource.extend(_collect(compiled, native, champion, stratum, RESOURCE_PER_STRATUM, SEEDS["resource_probe"] + len(resource), sealed, seen))
    roots = []
    for root in acquisition:
        local = root.pop("local_index")
        root["root_id"] = f"{root['stratum']}-a-{local:02d}"
        root["role"] = "train" if local < ACQUISITION_TRAIN_PER_STRATUM else "dev"
        roots.append(root)
    for root in resource:
        local = root.pop("local_index")
        root["root_id"] = f"{root['stratum']}-r-{local:02d}"
        root["role"] = "resource_estimation_only"
        roots.append(root)
    overlap = _historical_overlap(roots, sealed)
    if any(overlap.values()) or len({root["position_key"] for root in roots}) != 54:
        raise RuntimeError(f"F83 root disjointness failure: overlap={overlap}")
    payload = {
        "schema": "generic-chess-f83-c1-relative-root-corpus-v1",
        "work_order": WORK_ORDER,
        "c1_authority": preflight,
        "ruleset": LABEL,
        "seed_streams": SEEDS,
        "generation_contract": {
            "reachable_random": {"count": 16, "target_plies": [8, 24], "uses_evaluator": False},
            "c1_on_policy": {"count": 16, "random_prefix_plies": [2, 6], "search_plies": 6, "nodes_per_move": 128, "max_depth": 10, "tt_megabytes": 8, "root_window_pruning": True},
            "c1_pv_corridor": {"count": 16, "random_prefix_plies": [2, 6], "nodes": 512, "max_depth": 12, "tt_megabytes": 8, "root_window_pruning": True, "pv_offset_rule": PV_OFFSET_RULE},
            "resource_probes": {"count": 6, "per_stratum": 2, "role": "RESOURCE_ESTIMATION_ONLY"},
        },
        "role_counts": {"train": 36, "dev": 12, "resource_estimation_only": 6},
        "stratum_counts": {stratum: sum(root["stratum"] == stratum for root in roots) for stratum in ("reachable_random", "c1_on_policy", "c1_pv_corridor")},
        "overlap_counts": overlap,
        "sealed_history_identities": {"f62_stage_sha256": F62_STAGE_SHA, "f62_records_sha256": F62_RECORDS_SHA, "sealed_position_sets": {name: len(keys) for name, keys in sealed.items()}},
        "roots": roots,
    }
    payload["corpus_id"] = _stable_sha(payload)
    _atomic_json(ROOT_CORPUS_PATH, payload)
    return payload


def _probe_worker(record: dict, queue) -> None:
    try:
        from scripts import f50_generic_learnable_evaluator as f50
        from scripts import f59_action_spectrum_diagnosis as f59
        from scripts import f79_parent_anchored_full_residual_arena4 as f79
        compiled, native, _profile = f50._ruleset(LABEL)
        _parent, champion, _descriptor = f79._load_frozen_candidate(compiled)
        started = time.perf_counter()
        _rows, metadata = f59._spectrum_for_root(compiled, native, champion, champion, record, smoke=False)
        legal = int(metadata["legal_action_count"])
        selected = len(metadata["action_rows"])
        queue.put({
            "status": "COMPLETE",
            "elapsed_wall_seconds": time.perf_counter() - started,
            "legal_action_count": legal,
            "selected_action_count": selected,
            "actual_teacher_calls": 2 * selected,
            "actual_search_calls": 4 + legal + 2 * selected,
            "root_search_budgets": [2000, 40000, 80000],
            "teacher_child_budgets": [1000, 10000, 20000],
            "max_depth": 12,
            "tt_megabytes": 8,
            "root_window_pruning": False,
        })
    except BaseException as exc:  # pragma: no cover - exercised by bounded worker
        queue.put({"status": "HARNESS_MISMATCH", "error": f"{type(exc).__name__}: {exc}"})


def _run_one_probe(root: dict) -> dict:
    context = mp.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_probe_worker, args=(root, queue))
    started = time.perf_counter()
    process.start()
    process.join(PROBE_PER_ROOT_WALL_SECONDS)
    elapsed = time.perf_counter() - started
    if process.is_alive():
        process.terminate()
        process.join(5)
        return {"root_id": root["root_id"], "stratum": root["stratum"], "status": "TIME_CAP", "termination_reason": "per_root_wall_cap", "elapsed_wall_seconds": elapsed}
    if not queue.empty():
        result = queue.get()
    else:
        result = {"status": "HARNESS_MISMATCH", "error": f"probe exited with code {process.exitcode}"}
    return {"root_id": root["root_id"], "stratum": root["stratum"], **result, "elapsed_wall_seconds": float(result.get("elapsed_wall_seconds", elapsed))}


def _teacher_probe(compiled, root_payload: dict) -> dict:
    roots = [root for root in root_payload["roots"] if root["role"] == "resource_estimation_only"]
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=PROBE_MAX_CONCURRENCY) as pool:
        results = list(pool.map(_run_one_probe, roots))
    elapsed = time.perf_counter() - started
    complete = [item for item in results if item["status"] == "COMPLETE"]
    capped = [item for item in results if item["status"] == "TIME_CAP"]
    failed = [item for item in results if item["status"] == "HARNESS_MISMATCH"]
    if failed:
        classification = "HARNESS_MISMATCH"
    elif capped:
        classification = "C1_RELATIVE_EVIDENCE_ROOTS_FROZEN_TEACHER_COST_LOWER_BOUND_ONLY"
    else:
        classification = "C1_RELATIVE_EVIDENCE_ROOTS_FROZEN_TEACHER_COST_CALIBRATED"
    max_wall = max((item.get("elapsed_wall_seconds", 0.0) for item in results), default=0.0)
    roots_by_id = {root["root_id"]: root for root in roots}
    for result in capped:
        session = _session(compiled, roots_by_id[result["root_id"]]["replay_actions"])
        result["legal_action_count"] = len(session.legal_actions())
        result["candidate_action_count"] = None
        result["actual_teacher_calls"] = None
        result["search_phase_telemetry"] = None
        result["telemetry_unavailable_reason"] = "probe_process_terminated_at_wall_cap_before_metadata_return"
    lower_bound = {
        "cpu_hours_lower_bound_for_48": (PROBE_PER_ROOT_WALL_SECONDS * 48) / 3600.0,
        "wall_minutes_lower_bound_by_lanes": {str(lanes): (PROBE_PER_ROOT_WALL_SECONDS * 48 / lanes) / 60.0 for lanes in (1, 2, 4, 8)},
        "calibration_geometry_max_concurrent_roots": PROBE_MAX_CONCURRENCY,
        "large_work_under_calibration_geometry": (PROBE_PER_ROOT_WALL_SECONDS * 48 / PROBE_MAX_CONCURRENCY) / 60.0 > 30,
        "higher_concurrency_unmeasured": True,
        "method": "48 roots multiplied by the 180-second per-root cap; capped samples are lower bounds, not completions",
    }
    payload = {
        "schema": "generic-chess-f83-teacher-cost-probe-v2-lower-bound",
        "work_order": WORK_ORDER,
        "teacher_contract": {
            "implementation_paths": ["scripts/f59_action_spectrum_diagnosis.py", "scripts/f62_learned_champion_repeatability.py"],
            "implementation_sha256": {path: _sha(ROOT / path) for path in ("scripts/f59_action_spectrum_diagnosis.py", "scripts/f62_learned_champion_repeatability.py")},
            "f62_stage_sha256": F62_STAGE_SHA,
            "f62_records_sha256": F62_RECORDS_SHA,
            "root_budgets": [2000, 40000, 80000],
            "teacher_child_budgets": [1000, 10000, 20000],
            "max_depth": 12,
            "tt_megabytes": 8,
            "root_window_pruning": False,
            "candidate_action_construction": "all legal actions sorted canonically; cheap child-Q ordering; top six plus root/observer/high-budget actions",
            "target_q_convention": "child-side search score negated to root-action owner perspective",
            "terminal_handling": "ongoing roots only; mate-band metadata retained; no capped probe is a teacher label",
            "record_schema": "F62 spectrum root metadata/action_rows",
        },
        "probe_contract": {"root_count": 6, "max_concurrent_roots": 2, "per_root_wall_cap_seconds": 180, "whole_probe_hard_wall_seconds": 720, "role": "RESOURCE_ESTIMATION_ONLY"},
        "results": results,
        "completed_count": len(complete),
        "capped_count": len(capped),
        "failed_count": len(failed),
        "teacher_calls": sum(item["actual_teacher_calls"] for item in complete) if not capped else None,
        "teacher_calls_status": "UNKNOWN_BECAUSE_ALL_PROBES_WERE_TERMINATED_AT_WALL_CAP" if capped else "OBSERVED_FOR_COMPLETED_PROBES",
        "lower_bound_for_48_acquisition": lower_bound,
        "elapsed_wall_seconds": elapsed,
        "classification": classification,
    }
    _atomic_json(PROBE_PATH, payload)
    return payload


def _correct_existing_root_corpus(compiled, f62_manifest: dict) -> dict:
    payload = json.loads(ROOT_CORPUS_PATH.read_text(encoding="utf-8"))
    previous_corpus_id = payload["corpus_id"]
    replay_keys = []
    for root in payload["roots"]:
        session = _session(compiled, root["replay_actions"])
        if session.result.status.value != "ongoing":
            raise RuntimeError(f"F83 root is not ongoing during corrective replay: {root['root_id']}")
        from generic_chess.core.identity import position_identity_key
        key = position_identity_key(session.state.position, compiled)
        if key != root["position_key"] or int(session.state.ply_count) != int(root["ply"]):
            raise RuntimeError(f"F83 root replay identity mismatch: {root['root_id']}")
        replay_keys.append(key)
    if len(replay_keys) != len(set(replay_keys)) or len(replay_keys) != 54:
        raise RuntimeError("F83 corrected root set is not globally unique")
    sealed = _load_sealed_position_keys(set(f62_manifest["position_keys"]))
    overlaps = _historical_overlap(payload["roots"], sealed)
    if any(overlaps.values()):
        raise RuntimeError(f"F83 corrected root set overlaps sealed history: {overlaps}")
    for key in ("adoption_path", "f78_candidate_path", "f81_evidence_path"):
        if key in payload.get("c1_authority", {}):
            payload["c1_authority"][key] = payload["c1_authority"][key].replace("\\", "/")
    identities = [
        {key: root[key] for key in ("root_id", "position_key", "stratum", "role", "replay_actions")}
        for root in payload["roots"]
    ]
    payload["previous_corpus_id"] = previous_corpus_id
    payload["root_set_identity_sha256"] = _stable_sha(identities)
    payload["f62_historical_root_identity_manifest"] = {
        "path": str(F62_MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
        "content_sha256": _sha(F62_MANIFEST_PATH),
    }
    payload["replay_validation"] = {
        "validated_root_count": len(replay_keys),
        "all_ongoing": True,
        "all_canonical_position_keys_match": True,
        "all_position_keys_unique": True,
    }
    payload["overlap_counts"] = overlaps
    _atomic_json(ROOT_CORPUS_PATH, payload)
    return payload


def _correct_probe_artifact(compiled, root_payload: dict) -> dict:
    payload = json.loads(PROBE_PATH.read_text(encoding="utf-8"))
    if payload.get("completed_count") != 0 or payload.get("capped_count") != 6 or payload.get("failed_count") != 0:
        raise RuntimeError("F83-R1 expected the original six capped probe observations")
    original_sha = F83_ORIGINAL_PROBE_ARTIFACT_SHA
    roots = {root["root_id"]: root for root in root_payload["roots"]}
    for result in payload["results"]:
        root = roots[result["root_id"]]
        session = _session(compiled, root["replay_actions"])
        result["legal_action_count"] = len(session.legal_actions())
        result["candidate_action_count"] = None
        result["actual_teacher_calls"] = None
        result["search_phase_telemetry"] = None
        result["telemetry_unavailable_reason"] = "probe_process_terminated_at_wall_cap_before_metadata_return"
    lower_bound = {
        "cpu_hours_lower_bound_for_48": 2.4,
        "wall_minutes_lower_bound_by_lanes": {"1": 144.0, "2": 72.0, "4": 36.0, "8": 18.0},
        "calibration_geometry_max_concurrent_roots": 2,
        "large_work_under_calibration_geometry": True,
        "higher_concurrency_unmeasured": True,
        "method": "48 roots multiplied by the 180-second per-root cap; capped samples are lower bounds, not completions",
    }
    payload["schema"] = "generic-chess-f83-teacher-cost-probe-v2-lower-bound"
    payload["original_probe_artifact_sha256"] = original_sha
    payload["teacher_calls"] = None
    payload["teacher_calls_status"] = "UNKNOWN_BECAUSE_ALL_PROBES_WERE_TERMINATED_AT_WALL_CAP"
    payload.pop("estimate_for_48_acquisition_roots", None)
    payload["lower_bound_for_48_acquisition"] = lower_bound
    payload["classification"] = "C1_RELATIVE_EVIDENCE_ROOTS_FROZEN_TEACHER_COST_LOWER_BOUND_ONLY"
    _atomic_json(PROBE_PATH, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r1-corrective", action="store_true")
    args = parser.parse_args()
    from scripts import f50_generic_learnable_evaluator as f50
    from scripts import f79_parent_anchored_full_residual_arena4 as f79

    preflight = _preflight()
    compiled, native, _profile = f50._ruleset(LABEL)
    if args.r1_corrective:
        f62_manifest = _tracked_f62_manifest(compiled)
        root_payload = _correct_existing_root_corpus(compiled, f62_manifest)
        probe = _correct_probe_artifact(compiled, root_payload)
        print(json.dumps({"classification": probe["classification"], "root_set_identity_sha256": root_payload["root_set_identity_sha256"], "f62_manifest_sha256": _sha(F62_MANIFEST_PATH), "probe_schema": probe["schema"]}, sort_keys=True), flush=True)
        return
    _parent, champion, _descriptor = f79._load_frozen_candidate(compiled)
    root_payload = _root_corpus(preflight, compiled, native, champion)
    probe = _teacher_probe(compiled, root_payload)
    print(json.dumps({"classification": probe["classification"], "root_corpus_id": root_payload["corpus_id"], "completed_count": probe["completed_count"], "capped_count": probe["capped_count"], "failed_count": probe["failed_count"], "lower_bound_for_48_acquisition": probe["lower_bound_for_48_acquisition"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
