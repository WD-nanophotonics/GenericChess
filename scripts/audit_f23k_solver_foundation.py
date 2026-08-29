"""Run the frozen F23K exact-solver capability matrix.

The representatives are fixed before reading any solver result.  This module
does not inspect evaluator values and does not write corpus labels.
"""

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

from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23g_preference_corpus_r2 as f23g
from scripts import build_f23j_preference_corpus_r4 as f23j
from scripts import exact_generic_preference_solver as legacy
from scripts import exact_generic_preference_solver_v2 as v2


BENCHMARK_PLAN = (
    ("ordinary_anchor_movement", 0, {"max_nodes": 50, "max_depth": 1}),
    ("capture_recapture_tactics", 0, {"max_nodes": 50, "max_depth": 1}),
    ("drop_hand_tactics", 0, {"max_nodes": 50, "max_depth": 1}),
    ("promotion_race", 0, {"max_nodes": 50, "max_depth": 1}),
    ("semantic_guard_auxiliary", 0, {"max_nodes": 50, "max_depth": 1}),
)
CONTROL = ("auxiliary_reply_chain_control", 0, {"max_nodes": 30000, "max_depth": 6})


def _plan_entry(family: str):
    return next(item for item in f23j.CANDIDATE_PLAN if item["construction_family"] == family)


def _run_one(m, family: str, index: int, limits: dict[str, int]):
    plan = _plan_entry(family)
    parameter = tuple(plan["parameters"][index])
    compiled, state = f23j._build_candidate(m, plan, parameter)
    old = legacy.solve_root(compiled, state, **limits)
    new = v2.solve_root_proof_v2(compiled, state, **limits)
    return {
        "representative_id": f"generic-f23j-{plan['builder']}-{index}",
        "construction_family": family,
        "mechanic_family": plan["mechanic_family"],
        "parameter": list(parameter),
        "limits": limits,
        "historical": {"strong": old.strong, "root_value": old.root_value, "unresolved_reason": old.unresolved_reason},
        "new": {"strong": new.strong, "root_value": new.root_value, "unresolved_reason": new.unresolved_reason, "proof_depth": new.max_proof_ply, "states_expanded": new.stats.get("states_expanded", 0), "legal_successors_generated": new.stats.get("legal_successors_generated", 0), "exact_tt_hits": new.stats.get("exact_tt_hits", 0), "lower_bound_hits": new.stats.get("lower_bound_hits", 0), "upper_bound_hits": new.stats.get("upper_bound_hits", 0), "proof_cutoffs": new.stats.get("proof_cutoffs", 0), "terminal_statuses": new.stats.get("terminal_statuses", {}), "history_key_mode": new.stats.get("history_key_mode", "full_state_and_history")},
        "parity": old.root_value == new.root_value and old.optimal_actions == new.optimal_actions if old.strong and new.strong else old.strong == new.strong and old.unresolved_reason == new.unresolved_reason,
    }


def build_report() -> dict:
    m = f23c._imports()
    rows = [_run_one(m, family, index, limits) for family, index, limits in BENCHMARK_PLAN]
    control_family, control_index, control_limits = CONTROL
    cm = f23c._imports()
    compiled, pieces = f23g._semantic_variant(cm, 0)
    state = cm["make_state"](compiled, f23g._rows(5, pieces))
    old = legacy.solve_root(compiled, state, **control_limits)
    new = v2.solve_root_proof_v2(compiled, state, **control_limits)
    rows.append({"representative_id": "generic-f23j-f23g_reply_chain_control-0", "construction_family": control_family, "mechanic_family": "auxiliary_state_chain", "parameter": [0, False], "limits": control_limits, "historical": {"strong": old.strong, "root_value": old.root_value, "unresolved_reason": old.unresolved_reason}, "new": {"strong": new.strong, "root_value": new.root_value, "unresolved_reason": new.unresolved_reason, "proof_depth": new.max_proof_ply, "states_expanded": new.stats.get("states_expanded", 0), "legal_successors_generated": new.stats.get("legal_successors_generated", 0), "exact_tt_hits": new.stats.get("exact_tt_hits", 0), "lower_bound_hits": new.stats.get("lower_bound_hits", 0), "upper_bound_hits": new.stats.get("upper_bound_hits", 0), "proof_cutoffs": new.stats.get("proof_cutoffs", 0), "terminal_statuses": new.stats.get("terminal_statuses", {}), "history_key_mode": new.stats.get("history_key_mode", "full_state_and_history")}, "parity": old.root_value == new.root_value and old.optimal_actions == new.optimal_actions})
    return {"benchmark_version": "f23k-solver-foundation-v1", "selection_frozen_before_results": True, "evaluator_blind": True, "rows": rows, "legacy_parity": all(row["parity"] for row in rows), "non_control_solved_families": sum(row["new"]["strong"] for row in rows if row["construction_family"] != control_family), "non_control_families": len(BENCHMARK_PLAN), "selected_next_boundary": "F23L_EXACT_REFERENCE_SOLVER_FOUNDATION_R2"}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    report = build_report(); args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "legacy_parity": report["legacy_parity"], "non_control_solved_families": report["non_control_solved_families"], "selected": report["selected_next_boundary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
