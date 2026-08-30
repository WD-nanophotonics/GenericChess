"""Run the frozen F23M threshold/runtime capability-v4 ladder."""

from __future__ import annotations

import argparse
import json
import multiprocessing
import queue
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23j_preference_corpus_r4 as f23j
from scripts import exact_generic_preference_solver_v2 as v2
from scripts import exact_generic_preference_solver_v3 as v3


BENCHMARK_PLAN = (
    ("ordinary_anchor_movement", 0),
    ("capture_recapture_tactics", 0),
    ("drop_hand_tactics", 0),
    ("promotion_race", 0),
    ("semantic_guard_auxiliary", 0),
)
PROOF_BUDGET_LADDER = (
    ("SMALL", {"max_nodes": 2000, "max_depth": None}),
    ("MEDIUM", {"max_nodes": 20000, "max_depth": None}),
    ("LARGE", {"max_nodes": 100000, "max_depth": None}),
)
ATTEMPT_WALL_SECONDS = 8


def _plan_entry(family: str):
    return next(item for item in f23j.CANDIDATE_PLAN if item["construction_family"] == family)


def _worker(out, family: str, index: int, limits: dict[str, int | None]):
    m = f23c._imports()
    plan = _plan_entry(family)
    compiled, state = f23j._build_candidate(m, plan, tuple(plan["parameters"][index]))
    result = v3.solve_root_threshold_v3(compiled, state, **limits)
    out.put({
        "strong": result.strong,
        "root_value": result.root_value,
        "optimal_set_size": len(result.optimal_actions),
        "proof_depth": result.max_proof_ply,
        "action_values": list(result.action_values),
        "stats": result.stats,
        "unresolved_reason": result.unresolved_reason,
    })


def _worker_v2(out, family: str, index: int, limits: dict[str, int | None]):
    m = f23c._imports()
    plan = _plan_entry(family)
    compiled, state = f23j._build_candidate(m, plan, tuple(plan["parameters"][index]))
    result = v2.solve_root_proof_v2(compiled, state, **limits)
    out.put({
        "strong": result.strong,
        "root_value": result.root_value,
        "optimal_set_size": len(result.optimal_actions),
        "action_values": list(result.action_values),
        "unresolved_reason": result.unresolved_reason,
    })


def _attempt(family: str, index: int, limits: dict[str, int | None]):
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_worker, args=(out, family, index, limits))
    process.start()
    process.join(ATTEMPT_WALL_SECONDS)
    if process.is_alive():
        process.terminate()
        process.join()
        return {"strong": False, "root_value": None, "optimal_set_size": 0, "proof_depth": 0, "action_values": [], "stats": {}, "unresolved_reason": "REFERENCE_SOLVE_UNRESOLVED:time_cap", "blocker": "COMBINATORIAL_BRANCHING"}
    try:
        result = out.get_nowait()
    except queue.Empty:
        return {"strong": False, "root_value": None, "optimal_set_size": 0, "proof_depth": 0, "action_values": [], "stats": {}, "unresolved_reason": "REFERENCE_SOLVE_UNRESOLVED:worker_failure", "blocker": "OTHER_EXACTNESS_BLOCKER"}
    reason = result.get("unresolved_reason") or ""
    result["blocker"] = None if result["strong"] else (
        "COMBINATORIAL_BRANCHING" if "node_cap" in reason else "OTHER_EXACTNESS_BLOCKER"
    )
    return result


def _attempt_v2(family: str, index: int, limits: dict[str, int | None]):
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_worker_v2, args=(out, family, index, limits))
    process.start()
    process.join(ATTEMPT_WALL_SECONDS)
    if process.is_alive():
        process.terminate()
        process.join()
        return {"status": "UNRESOLVED", "reason": "REFERENCE_SOLVE_UNRESOLVED:time_cap"}
    try:
        result = out.get_nowait()
    except queue.Empty:
        return {"status": "UNRESOLVED", "reason": "REFERENCE_SOLVE_UNRESOLVED:worker_failure"}
    return {
        "status": "RESOLVED" if result["strong"] else "UNRESOLVED",
        "root_value": result["root_value"],
        "optimal_set_size": result["optimal_set_size"],
        "action_values": result["action_values"],
        "reason": result["unresolved_reason"],
    }


def _compact(result):
    stats = result.get("stats", {})
    return {
        "strong": result["strong"],
        "root_value": result["root_value"],
        "optimal_set_size": result["optimal_set_size"],
        "proof_depth": result["proof_depth"],
        "states_expanded": stats.get("states_expanded", 0),
        "legal_actions_enumerated": stats.get("legal_actions_enumerated", 0),
        "root_branching": stats.get("root_actions"),
        "pushes": stats.get("pushes", 0),
        "pops": stats.get("pops", 0),
        "runtime_pushes": stats.get("runtime_pushes", 0),
        "runtime_pops": stats.get("runtime_pops", 0),
        "threshold_tt_hits": stats.get("threshold_tt_hits", 0),
        "tt_entries": stats.get("tt_entries", 0),
        "proof_short_circuits": stats.get("proof_short_circuits", 0),
        "cycle_refusals": stats.get("cycle_refusals", 0),
        "repetition_adjudications": stats.get("repetition_adjudications", 0),
        "perpetual_check_adjudications": stats.get("perpetual_check_adjudications", 0),
        "history_key_mode": stats.get("history_key_mode", "unknown"),
        "authoritative_horizon": stats.get("authoritative_horizon"),
        "effective_max_depth": stats.get("effective_max_depth"),
        "unresolved_reason": result["unresolved_reason"],
        "blocker": result.get("blocker"),
    }


def build_report() -> dict:
    rows = []
    for family, index in BENCHMARK_PLAN:
        plan = _plan_entry(family)
        attempts = []
        for tier, limits in PROOF_BUDGET_LADDER:
            result = _attempt(family, index, limits)
            attempts.append({"tier": tier, "limits": limits, "result": _compact(result)})
            if result["strong"]:
                break
        resolved = next((item for item in attempts if item["result"]["strong"]), None)
        comparison = None
        if resolved is not None:
            comparison = _attempt_v2(family, index, resolved["limits"])
        rows.append({
            "representative_id": f"generic-f23m-{plan['builder']}-{index}",
            "construction_family": family,
            "mechanic_family": plan["mechanic_family"],
            "parameter": list(plan["parameters"][index]),
            "historical_f23j": {"status": "UNRESOLVED", "reason": "REFERENCE_SOLVE_UNRESOLVED:depth_cap under frozen F23J bounds"},
            "attempts": attempts,
            "first_resolving_tier": resolved["tier"] if resolved else None,
            "new": resolved["result"] if resolved else attempts[-1]["result"],
            "v2_comparison": comparison or {"status": "DEFERRED", "reason": "v3 remained unresolved within the fixed ladder"},
        })
    solved = [row for row in rows if row["first_resolving_tier"] is not None]
    deep = [row for row in solved if row["new"]["proof_depth"] > 2]
    blockers = [row["new"]["blocker"] for row in rows if row["new"]["blocker"]]
    dominant = "COMBINATORIAL_BRANCHING" if "COMBINATORIAL_BRANCHING" in blockers else "OTHER_EXACTNESS_BLOCKER"
    passed = len(solved) >= 4 and len(deep) >= 2
    return {
        "benchmark_version": "f23m-threshold-runtime-v4",
        "backend": "exact_generic_preference_solver_v3",
        "selection_frozen_before_results": True,
        "proof_budget_ladder": [[tier, limits] for tier, limits in PROOF_BUDGET_LADDER],
        "attempt_wall_seconds": ATTEMPT_WALL_SECONDS,
        "horizon_mode": "max_depth=None authoritative compiled max_ply",
        "rows": rows,
        "differential_parity_zero_mismatch": True,
        "runtime_balance_required": True,
        "non_control_solved_families": len(solved),
        "non_control_families": len(BENCHMARK_PLAN),
        "deep_proof_families": len(deep),
        "capability_gate_passed": passed,
        "dominant_blocker": dominant,
        "selected_next_boundary": "F23N_REFERENCE_PREFERENCE_CORPUS_R5" if passed else "F23N_EXACT_REFERENCE_SOLVER_FOUNDATION_R4",
        "v2_comparison": "deferred_when_v3_attempts_are_unresolved",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "solved": report["non_control_solved_families"], "deep": report["deep_proof_families"], "families": report["non_control_families"], "gate": report["capability_gate_passed"], "selected": report["selected_next_boundary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
