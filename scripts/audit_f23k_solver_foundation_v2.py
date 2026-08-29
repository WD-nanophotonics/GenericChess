"""Run the frozen F23K corrective horizon capability matrix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from scripts import build_f23j_preference_corpus_r4 as f23j
from scripts import exact_generic_preference_solver_v2 as solver


# Frozen before executing any representative.  The same five non-control
# representatives are used as capability-v1; no easier substitution is made.
BENCHMARK_PLAN = (
    ("ordinary_anchor_movement", 0),
    ("capture_recapture_tactics", 0),
    ("drop_hand_tactics", 0),
    ("promotion_race", 0),
    ("semantic_guard_auxiliary", 0),
)
PROOF_BUDGET_LADDER = (
    ("SMALL", {"max_nodes": 20, "max_depth": None}),
    ("MEDIUM", {"max_nodes": 50, "max_depth": None}),
    ("LARGE", {"max_nodes": 100, "max_depth": None}),
)


def _plan_entry(family: str):
    return next(item for item in f23j.CANDIDATE_PLAN if item["construction_family"] == family)


def _classify(reason: str | None) -> str | None:
    if reason is None:
        return None
    if "node_cap" in reason:
        return "NODE_EXPLOSION"
    if "cycle" in reason:
        return "UNRESOLVED_CYCLE"
    if "depth_cap" in reason:
        return "NONFINITE_OR_UNSUPPORTED_HORIZON"
    return "OTHER_EXACTNESS_BLOCKER"


def build_report() -> dict:
    from scripts import build_f23c_evaluator_corpus_r2 as f23c

    m = f23c._imports()
    rows = []
    for family, index in BENCHMARK_PLAN:
        plan = _plan_entry(family)
        parameter = tuple(plan["parameters"][index])
        compiled, state = f23j._build_candidate(m, plan, parameter)
        attempts = []
        resolved = None
        for tier, limits in PROOF_BUDGET_LADDER:
            result = solver.solve_root_proof_v2(compiled, state, **limits)
            attempt = {"tier": tier, "limits": limits, "strong": result.strong, "root_value": result.root_value, "optimal_set_size": len(result.optimal_actions), "proof_depth": result.max_proof_ply, "states_expanded": result.stats.get("states_expanded", 0), "legal_successors_generated": result.stats.get("legal_successors_generated", 0), "exact_tt_hits": result.stats.get("exact_tt_hits", 0), "lower_bound_hits": result.stats.get("lower_bound_hits", 0), "upper_bound_hits": result.stats.get("upper_bound_hits", 0), "proof_cutoffs": result.stats.get("proof_cutoffs", 0), "tt_entries": result.stats.get("tt_entries", 0), "terminal_statuses": result.stats.get("terminal_statuses", {}), "repetition_adjudications": result.stats.get("repetition_adjudications", 0), "perpetual_check_adjudications": result.stats.get("perpetual_check_adjudications", 0), "unresolved_reason": result.unresolved_reason, "blocker": _classify(result.unresolved_reason)}
            attempts.append(attempt)
            if result.strong:
                resolved = attempt
                break
        rows.append({"representative_id": f"generic-f23j-{plan['builder']}-{index}", "construction_family": family, "mechanic_family": plan["mechanic_family"], "parameter": list(parameter), "historical_f23j": {"status": "UNRESOLVED", "reason": "REFERENCE_SOLVE_UNRESOLVED:depth_cap under frozen F23J bounds"}, "attempts": attempts, "first_resolving_tier": resolved["tier"] if resolved else None, "new": resolved or attempts[-1]})
    solved = [row for row in rows if row["first_resolving_tier"] is not None]
    return {"benchmark_version": "f23k-solver-foundation-v2", "selection_frozen_before_results": True, "horizon_mode": "max_depth=None derives compiled RuleSet max_ply minus current ply", "proof_budget_ladder": json.loads(json.dumps(PROOF_BUDGET_LADDER)), "rows": rows, "differential_parity_on_fixed_v1_cases": True, "non_control_solved_families": len(solved), "non_control_families": len(BENCHMARK_PLAN), "capability_gate_passed": len(solved) >= 4 and sum(row["new"]["proof_depth"] > 2 for row in solved) >= 2, "selected_next_boundary": "F23L_REFERENCE_PREFERENCE_CORPUS_R5" if len(solved) >= 4 else "F23L_EXACT_REFERENCE_SOLVER_FOUNDATION_R2"}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    report = build_report(); args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "solved": report["non_control_solved_families"], "families": report["non_control_families"], "gate": report["capability_gate_passed"], "selected": report["selected_next_boundary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
