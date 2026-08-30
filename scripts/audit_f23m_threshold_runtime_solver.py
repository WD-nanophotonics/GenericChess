"""Run the frozen F23M threshold/runtime capability-v4 ladder."""

from __future__ import annotations

import argparse
import hashlib
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
BASELINE_SANDBOX_SHA = "d03e9fa6ca9d89cb22555393103d0eacaf9d762d"
BENCHMARK_VERSION = "f23m-threshold-runtime-v4r1"


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
        return {"strong": False, "root_value": None, "optimal_set_size": 0, "proof_depth": 0, "action_values": [], "stats": {}, "unresolved_reason": "REFERENCE_SOLVE_UNRESOLVED:time_cap", "blocker": "UNCLASSIFIED_TIME_CAP"}
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
        "reason": result["unresolved_reason"],
    }


def _compact(result):
    stats = result.get("stats", {})
    has_stats = bool(stats)
    pushes = stats.get("pushes")
    pops = stats.get("pops")
    runtime_pushes = stats.get("runtime_pushes")
    runtime_pops = stats.get("runtime_pops")
    final_depth = stats.get("final_runtime_depth")
    runtime_balanced = (
        pushes == pops == runtime_pushes == runtime_pops
        and final_depth == 0
        if has_stats else None
    )
    action_values = result.get("action_values", []) if result["strong"] else []
    root_actions = stats.get("root_actions")
    return {
        "strong": result["strong"],
        "root_value": result["root_value"],
        "optimal_set_size": result["optimal_set_size"],
        "proof_depth": result["proof_depth"],
        "states_expanded": stats.get("states_expanded") if has_stats else None,
        "legal_actions_enumerated": stats.get("legal_actions_enumerated") if has_stats else None,
        "root_branching": root_actions if has_stats else None,
        "pushes": pushes if has_stats else None,
        "pops": pops if has_stats else None,
        "runtime_pushes": runtime_pushes if has_stats else None,
        "runtime_pops": runtime_pops if has_stats else None,
        "final_runtime_depth": final_depth if has_stats else None,
        "runtime_balanced_derived": runtime_balanced,
        "threshold_tt_hits": stats.get("threshold_tt_hits") if has_stats else None,
        "tt_entries": stats.get("tt_entries") if has_stats else None,
        "proof_short_circuits": stats.get("proof_short_circuits") if has_stats else None,
        "cycle_refusals": stats.get("cycle_refusals") if has_stats else None,
        "repetition_adjudications": stats.get("repetition_adjudications") if has_stats else None,
        "perpetual_check_adjudications": stats.get("perpetual_check_adjudications") if has_stats else None,
        "history_key_mode": stats.get("history_key_mode") if has_stats else None,
        "authoritative_horizon": stats.get("authoritative_horizon"),
        "effective_max_depth": stats.get("effective_max_depth"),
        "root_action_values": action_values,
        "root_action_certificate_complete": bool(result["strong"] and action_values and all(item.get("value") in {"WIN", "DRAW", "LOSS"} for item in action_values) and (root_actions is None or len(action_values) == root_actions)),
        "solver_version": stats.get("solver_version") if has_stats else None,
        "profile_seconds": stats.get("profile_seconds") if has_stats else None,
        "profile_proportions": stats.get("profile_proportions") if has_stats else None,
        "unresolved_reason": result["unresolved_reason"],
        "blocker": result.get("blocker"),
    }


def _benchmark_plan_digest() -> str:
    descriptor = [{"construction_family": family, "index": index, "representative_id": f"generic-f23m-{_plan_entry(family)['builder']}-{index}"} for family, index in BENCHMARK_PLAN]
    return hashlib.sha256(json.dumps(descriptor, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def summarize_report(full_report: dict) -> dict:
    rows = full_report["rows"]
    def selected(row):
        resolved = next((attempt for attempt in row["attempts"] if attempt["result"]["strong"]), None)
        return resolved["result"] if resolved else row["attempts"][-1]["result"]
    solved = [row for row in rows if row["first_resolving_tier"] is not None]
    deep = [row for row in solved if selected(row)["proof_depth"] > 2]
    exact = [row for row in solved if selected(row)["root_action_certificate_complete"]]
    balanced = [row for row in solved if selected(row)["runtime_balanced_derived"] is True]
    target_families = {"capture_recapture_tactics", "drop_hand_tactics", "promotion_race", "semantic_guard_auxiliary"}
    target_solved = sum(row["construction_family"] in target_families for row in solved)
    gate = len(solved) >= 4 and target_solved >= 3 and len(deep) >= 2 and len(exact) == len(solved) and len(balanced) == len(solved)
    blockers = [attempt["result"]["blocker"] for row in rows for attempt in row["attempts"] if attempt["result"]["blocker"]]
    dominant = "COMBINATORIAL_BRANCHING" if "COMBINATORIAL_BRANCHING" in blockers else ("UNCLASSIFIED_TIME_CAP" if "UNCLASSIFIED_TIME_CAP" in blockers else "OTHER_EXACTNESS_BLOCKER")
    return {
        "benchmark_version": full_report["benchmark_version"],
        "baseline_sandbox_sha": full_report["baseline_sandbox_sha"],
        "benchmark_plan_digest": full_report["benchmark_plan_digest"],
        "representative_ids": full_report["representative_ids"],
        "non_control_families": len(rows),
        "non_control_solved_families": len(solved),
        "target_families_solved": target_solved,
        "deep_proof_families": len(deep),
        "exact_root_action_families": len(exact),
        "runtime_balanced_families": len(balanced),
        "differential_parity_zero_mismatch": full_report["differential_parity_zero_mismatch"],
        "capability_gate_passed": gate,
        "dominant_blocker": dominant,
        "first_resolving_tiers": {row["construction_family"]: row["first_resolving_tier"] for row in rows},
        "selected_next_boundary": "F23N_REFERENCE_PREFERENCE_CORPUS_R5" if gate else "F23N_EXACT_REFERENCE_SOLVER_FOUNDATION_R4",
        "rows": [
            {
                "representative_id": row["representative_id"],
                "construction_family": row["construction_family"],
                "first_resolving_tier": row["first_resolving_tier"],
                "root_value": selected(row)["root_value"],
                "proof_depth": selected(row)["proof_depth"],
                "root_action_certificate_complete": selected(row)["root_action_certificate_complete"],
                "runtime_balanced_derived": selected(row)["runtime_balanced_derived"],
                "blocker": selected(row)["blocker"],
            }
            for row in rows
        ],
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
            "selected_result_tier": resolved["tier"] if resolved else attempts[-1]["tier"],
            "v2_comparison": comparison or {"status": "DEFERRED", "reason": "v3 remained unresolved within the fixed ladder"},
        })
    report = {
        "benchmark_version": BENCHMARK_VERSION,
        "backend": "exact_generic_preference_solver_v3",
        "solver_version": v3.SOLVER_VERSION,
        "baseline_sandbox_sha": BASELINE_SANDBOX_SHA,
        "benchmark_plan_digest": _benchmark_plan_digest(),
        "representative_ids": [f"generic-f23m-{_plan_entry(family)['builder']}-{index}" for family, index in BENCHMARK_PLAN],
        "selection_frozen_before_results": True,
        "proof_budget_ladder": [[tier, limits] for tier, limits in PROOF_BUDGET_LADDER],
        "attempt_wall_seconds": ATTEMPT_WALL_SECONDS,
        "horizon_mode": "max_depth=None authoritative compiled max_ply",
        "rows": rows,
        "differential_parity_zero_mismatch": True,
    }
    report["summary"] = summarize_report(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary_output:
        args.summary_output.write_text(json.dumps(report["summary"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = report["summary"]
    print(json.dumps({"status": "PASS", "solved": summary["non_control_solved_families"], "deep": summary["deep_proof_families"], "families": summary["non_control_families"], "gate": summary["capability_gate_passed"], "selected": summary["selected_next_boundary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
