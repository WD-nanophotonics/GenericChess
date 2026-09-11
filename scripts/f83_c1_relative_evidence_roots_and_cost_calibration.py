"""F83: freeze C1-relative roots and calibrate the tracked F62 teacher cost.

This work order deliberately stops after acquisition and six resource-only
teacher probes.  It never fits C2, creates a candidate, or runs strength play.
"""

from __future__ import annotations

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

OUT = ROOT / ".generic_chess_flow" / "f83-c1-relative-evidence"
ROOT_CORPUS_PATH = ROOT / "artifacts" / "f83_c1_relative_evidence" / "root_corpus.json"
PROBE_PATH = ROOT / "artifacts" / "f83_c1_relative_evidence" / "teacher_cost_probe.json"
F78_CANDIDATE = ROOT / "artifacts" / "f78_parent_anchored_full_residual" / "candidate.json"
F81_EVIDENCE = ROOT / "artifacts" / "f81_final_confirmation" / "final_strength_evidence.json"
F81_OPENINGS = ROOT / "artifacts" / "f81_final_confirmation" / "openings.json"
F75_OPENINGS = ROOT / "artifacts" / "f75_parent_retained_arena" / "openings.json"
F77_OPENINGS = ROOT / "artifacts" / "f77_trusted_pointwise_q_arena" / "openings.json"
F78_OPENINGS = ROOT / "artifacts" / "f78_parent_anchored_full_residual" / "openings.json"
F62_PROGRESS = ROOT / ".generic_chess_flow" / "f62-learned-champion-repeatability" / "progress" / "spectrum"


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
        "adoption_path": str((ROOT / "artifacts/f82_champion_adoption/champion.json").relative_to(ROOT)),
        "adoption_sha256": _sha(ROOT / "artifacts/f82_champion_adoption/champion.json"),
        "c1_checkpoint_id": C1_ID,
        "c1_model_sha256": C1_MODEL_SHA,
        "f78_candidate_path": str(F78_CANDIDATE.relative_to(ROOT)),
        "f78_candidate_sha256": _sha(F78_CANDIDATE),
        "f81_evidence_path": str(F81_EVIDENCE.relative_to(ROOT)),
        "f81_evidence_sha256": _sha(F81_EVIDENCE),
    }


def _load_sealed_position_keys() -> dict[str, set[str]]:
    sealed: dict[str, set[str]] = {}
    for name, path in {
        "f75": F75_OPENINGS,
        "f77": F77_OPENINGS,
        "f78_f80": F78_OPENINGS,
        "f81": F81_OPENINGS,
    }.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        sealed[name] = {item["final_position_key"] for item in payload["corpus"]["openings"]}
    if not F62_PROGRESS.is_dir():
        raise RuntimeError("F83 cannot recover tracked F62 spectrum evidence roots")
    f62_keys = set()
    for path in sorted(F62_PROGRESS.glob("root-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        record = payload.get("identity", {}).get("record", {})
        if record.get("position_key"):
            f62_keys.add(record["position_key"])
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


def _root_corpus(preflight: dict, compiled, native, champion) -> dict:
    sealed = _load_sealed_position_keys()
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


def _teacher_probe(root_payload: dict) -> dict:
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
    max_calls = max((item.get("actual_teacher_calls", 0) for item in complete), default=0)
    estimate = {
        "method": "conservative max observed resource-root cost multiplied by 48 acquisition roots; capped probes are lower bounds",
        "estimated_teacher_calls": max_calls * 48,
        "estimated_wall_minutes_by_lanes": {str(lanes): (max_wall * ((48 + lanes - 1) // lanes)) / 60.0 for lanes in (1, 2, 4)},
        "estimated_cpu_hours_upper_proxy": (max_wall * 48) / 3600.0,
        "sample_max_wall_seconds": max_wall,
        "large_work_thresholds": {"expected_wall_gt_30_minutes": max_wall * 48 / 60 > 30, "expected_cpu_gt_5_hours": max_wall * 48 / 3600 > 5},
    }
    payload = {
        "schema": "generic-chess-f83-teacher-cost-probe-v1",
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
        "estimate_for_48_acquisition_roots": estimate,
        "elapsed_wall_seconds": elapsed,
        "classification": classification,
    }
    _atomic_json(PROBE_PATH, payload)
    return payload


def main() -> None:
    from scripts import f50_generic_learnable_evaluator as f50
    from scripts import f79_parent_anchored_full_residual_arena4 as f79

    preflight = _preflight()
    compiled, native, _profile = f50._ruleset(LABEL)
    _parent, champion, _descriptor = f79._load_frozen_candidate(compiled)
    root_payload = _root_corpus(preflight, compiled, native, champion)
    probe = _teacher_probe(root_payload)
    print(json.dumps({"classification": probe["classification"], "root_corpus_id": root_payload["corpus_id"], "completed_count": probe["completed_count"], "capped_count": probe["capped_count"], "failed_count": probe["failed_count"], "estimated_wall_minutes_by_lanes": probe["estimate_for_48_acquisition_roots"]["estimated_wall_minutes_by_lanes"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
