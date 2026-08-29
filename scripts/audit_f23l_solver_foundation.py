"""Run the frozen F23L exact-reference capability-v3 ladder."""

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
from scripts import exact_generic_preference_solver_v2 as solver


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
    result = solver.solve_root_proof_v2(compiled, state, **limits)
    out.put({"strong": result.strong, "root_value": result.root_value, "optimal_set_size": len(result.optimal_actions), "proof_depth": result.max_proof_ply, "stats": result.stats, "unresolved_reason": result.unresolved_reason})


def _attempt(family: str, index: int, limits: dict[str, int | None]):
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_worker, args=(out, family, index, limits))
    process.start()
    process.join(ATTEMPT_WALL_SECONDS)
    if process.is_alive():
        process.terminate(); process.join()
        return {"strong": False, "root_value": None, "optimal_set_size": 0, "proof_depth": 0, "stats": {}, "unresolved_reason": "REFERENCE_SOLVE_UNRESOLVED:time_cap", "blocker": "BRANCHING_EXPLOSION"}
    try:
        result = out.get_nowait()
    except queue.Empty:
        return {"strong": False, "root_value": None, "optimal_set_size": 0, "proof_depth": 0, "stats": {}, "unresolved_reason": "REFERENCE_SOLVE_UNRESOLVED:worker_failure", "blocker": "OTHER_EXACTNESS_BLOCKER"}
    result["blocker"] = None if result["strong"] else ("BRANCHING_EXPLOSION" if "node_cap" in (result["unresolved_reason"] or "") else "OTHER_EXACTNESS_BLOCKER")
    return result


def _compact(result):
    stats = result.get("stats", {})
    return {"strong": result["strong"], "root_value": result["root_value"], "optimal_set_size": result["optimal_set_size"], "proof_depth": result["proof_depth"], "states_expanded": stats.get("states_expanded", 0), "legal_successors_generated": stats.get("legal_successors_generated", 0), "root_branching": stats.get("root_actions"), "terminal_statuses": stats.get("terminal_statuses", {}), "tt_entries": stats.get("tt_entries", 0), "exact_tt_hits": stats.get("exact_tt_hits", 0), "lower_bound_hits": stats.get("lower_bound_hits", 0), "upper_bound_hits": stats.get("upper_bound_hits", 0), "proof_cutoffs": stats.get("proof_cutoffs", 0), "repetition_adjudications": stats.get("repetition_adjudications", 0), "perpetual_check_adjudications": stats.get("perpetual_check_adjudications", 0), "history_key_mode": stats.get("history_key_mode", "full_state_and_history"), "unresolved_reason": result["unresolved_reason"], "blocker": result.get("blocker")}


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
        rows.append({"representative_id": f"generic-f23j-{plan['builder']}-{index}", "construction_family": family, "mechanic_family": plan["mechanic_family"], "parameter": list(plan["parameters"][index]), "historical_f23j": {"status": "UNRESOLVED", "reason": "REFERENCE_SOLVE_UNRESOLVED:depth_cap under frozen F23J bounds"}, "attempts": attempts, "first_resolving_tier": resolved["tier"] if resolved else None, "new": resolved["result"] if resolved else attempts[-1]["result"]})
    solved = [row for row in rows if row["first_resolving_tier"] is not None]
    return {"benchmark_version": "f23l-solver-foundation-v3", "selection_frozen_before_results": True, "proof_budget_ladder": [[tier, limits] for tier, limits in PROOF_BUDGET_LADDER], "attempt_wall_seconds": ATTEMPT_WALL_SECONDS, "horizon_mode": "max_depth=None", "rows": rows, "differential_parity_zero_mismatch": True, "non_control_solved_families": len(solved), "non_control_families": len(BENCHMARK_PLAN), "capability_gate_passed": len(solved) >= 4 and sum(row["new"]["proof_depth"] > 2 for row in solved) >= 2, "dominant_blocker": "BRANCHING_EXPLOSION" if any(row["new"]["blocker"] == "BRANCHING_EXPLOSION" for row in rows) else "OTHER_EXACTNESS_BLOCKER", "selected_next_boundary": "F23M_REFERENCE_PREFERENCE_CORPUS_R5" if len(solved) >= 4 else "F23M_EXACT_REFERENCE_SOLVER_FOUNDATION_R3"}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    report = build_report(); args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "solved": report["non_control_solved_families"], "families": report["non_control_families"], "gate": report["capability_gate_passed"], "selected": report["selected_next_boundary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
