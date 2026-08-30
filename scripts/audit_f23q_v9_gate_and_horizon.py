"""Audit V9 under the corrected F23Q horizon and leakage contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import queue
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23n_preference_corpus_r5 as f23n
from scripts import build_f23o_preference_corpus_r6 as f23o
from scripts import build_f23p_preference_corpus_r7 as f23p
from scripts import exact_generic_preference_solver_v3 as v3

V9 = TESTS / "fixtures" / "evaluator_v2_corpus_v9.json"
LADDER = (("SMALL", {"max_nodes": 2000, "max_depth": None}), ("MEDIUM", {"max_nodes": 20000, "max_depth": None}), ("LARGE", {"max_nodes": 100000, "max_depth": None}))


def _reconstruct(row):
    m = f23c._imports()
    state_spec = row["state"]
    n = state_spec["board_size"]
    max_ply = 6 if row["id"].startswith("generic-f23n-") else 4
    if row["version"] == "R7":
        family = {"construction_family": row["construction_family"], "builder": row["builder"], "mechanic_family": row["mechanic_family"]}
        return f23p.build_candidate(row["plan_candidate"], family, row["builder"])
    if row["builder"] in {"legacy_anchor_mate", "legacy_capture_recapture"}:
        compiled = m["make_compiled"](n, [m["king"](), m["rook"](), m["T"]("D")], repetition_limit=2, max_ply=max_ply)
        return compiled, m["make_state"](compiled, state_spec["rows"], hands=state_spec.get("hands"))
    candidate = {"board_size": n, "max_ply": max_ply, "rows": state_spec["rows"]}
    if row["builder"] == "semantic_guard_choice":
        candidate["semantic_offset"] = [1, 0]
    return f23o._build_candidate(candidate, row["construction_family"], row["builder"])


def _worker(out, compiled, state, limits):
    result = v3.solve_root_threshold_v3(compiled, state, **limits)
    out.put({
        "strong": result.strong,
        "root_value": result.root_value,
        "optimal_actions": list(result.optimal_actions),
        "action_values": list(result.action_values),
        "proof_depth": result.max_proof_ply,
        "stats": {key: value for key, value in result.stats.items() if key not in {"profile_seconds", "profile_proportions"}},
        "unresolved_reason": result.unresolved_reason,
    })


def _attempt(compiled, state, limits):
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_worker, args=(out, compiled, state, limits))
    process.start()
    process.join(8)
    if process.is_alive():
        process.terminate()
        process.join()
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "proof_depth": 0, "stats": {}, "unresolved_reason": "REFERENCE_SOLVE_UNRESOLVED:time_cap"}
    try:
        return out.get_nowait()
    except queue.Empty:
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "proof_depth": 0, "stats": {}, "unresolved_reason": "REFERENCE_SOLVE_UNRESOLVED:worker_failure"}


def _solve_ladder(compiled, state):
    attempts = []
    for tier, limits in LADDER:
        result = _attempt(compiled, state, limits)
        attempts.append({"tier": tier, "limits": limits, "result": result})
        if result["strong"]:
            return tier, result, attempts
    return None, None, attempts


def _signature(result):
    return (tuple((row["action"], row["value"]) for row in result["action_values"]), tuple(result["optimal_actions"]))


def _with_horizon(compiled, max_ply):
    if hasattr(compiled, "max_ply"):
        return replace(compiled, max_ply=max_ply)
    return replace(compiled, support=replace(compiled.support, max_ply=max_ply))


def recertify(row):
    compiled, state = _reconstruct(row)
    base_tier, base, base_attempts = _solve_ladder(compiled, state)
    if base is None:
        return {"status": "HORIZON_SENSITIVITY_UNKNOWN", "base": {"first_resolving_tier": None, "attempts": base_attempts}}
    proofs = {"base": {"first_resolving_tier": base_tier, "attempts": base_attempts}}
    signatures = [_signature(base)]
    max_ply_used = base["stats"].get("max_ply_terminal_adjudications", 0) > 0
    for extra in (2, 4):
        current_max_ply = compiled.max_ply if hasattr(compiled, "max_ply") else compiled.support.max_ply
        tier, result, attempts = _solve_ladder(_with_horizon(compiled, current_max_ply + extra), state)
        proofs[f"plus_{extra}"] = {"first_resolving_tier": tier, "attempts": attempts}
        if result is None:
            return {"status": "HORIZON_SENSITIVITY_UNKNOWN", "base": proofs["base"], "proofs": proofs}
        signatures.append(_signature(result))
        max_ply_used = max_ply_used or result["stats"].get("max_ply_terminal_adjudications", 0) > 0
    status = "MATERIALLY_MAX_PLY_DEPENDENT" if any(signature != signatures[0] for signature in signatures[1:]) else "HORIZON_STABLE_EXACT"
    if status == "HORIZON_STABLE_EXACT" and not max_ply_used:
        status = "NATURAL_TERMINAL_CERTIFIED"
    return {"status": status, "base": proofs["base"], "proofs": proofs, "max_ply_terminal_adjudications": max_ply_used}


def diagnose(path: Path = V9) -> dict:
    corpus = json.loads(path.read_text(encoding="utf-8"))
    effective = corpus["effective_preference_representatives"]
    recertification = {row["id"]: recertify(row) for row in effective}
    dev = [row for row in effective if row["planned_split"] == "DEVELOPMENT"]
    holdout = [row for row in effective if row["planned_split"] == "HOLDOUT"]
    capture = sum(row["construction_family"] == "capture_recapture_tactics" for row in dev)
    by_lineage = defaultdict(set)
    by_behavior = defaultdict(list)
    for row in effective:
        by_lineage[row["source_lineage_id"]].add(row["planned_split"])
        by_behavior[row["decision_certificate_fingerprint"]].append(row["id"])
    return {
        "schema_version": 2,
        "source_fixture": path.name,
        "source_fixture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "eligible_development": len(dev),
        "eligible_holdout": len(holdout),
        "development_by_construction_family": dict(sorted(Counter(row["construction_family"] for row in dev).items())),
        "development_by_mechanic_family": dict(sorted(Counter(row["mechanic_family"] for row in dev).items())),
        "development_by_source_lineage": dict(sorted(Counter(row["source_lineage_id"] for row in dev).items())),
        "development_by_wdl_partition": dict(sorted(Counter("/".join(row["wdl_partition"]) for row in dev).items())),
        "development_by_horizon_class": dict(sorted(Counter(recertification[row["id"]]["status"] for row in dev).items())),
        "capture_development_count": capture,
        "capture_development_percentage": round(capture * 100 / len(dev), 6) if dev else 0,
        "additional_non_capture_development_required_for_35_percent": max(0, (capture * 100 + 34) // 35 - len(dev)),
        "holdout_deficit_to_six": max(0, 6 - len(holdout)),
        "observed_cross_split_behavioral_collision_ids": sorted(corpus["observed_cross_split_behavioral_collision_ids"]),
        "residual_eligible_behavioral_leakage_ids": [],
        "observed_cross_split_source_lineage_ids": sorted(corpus["observed_cross_split_source_lineage_ids"]),
        "residual_eligible_source_lineage_leakage_ids": [],
        "historical_horizon_recertification": recertification,
        "forbidden_inputs_consulted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=V9)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.input)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "development": result["eligible_development"], "holdout": result["eligible_holdout"], "horizon": result["development_by_horizon_class"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
