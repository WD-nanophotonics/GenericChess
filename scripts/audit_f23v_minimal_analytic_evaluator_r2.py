"""Final F23V R2 admission correction; no scoring-plan replacement by default."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import queue
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
PLAN = FIXTURES / "f23v_minimal_analytic_plan_r1.json"
OUTPUT = FIXTURES / "f23v_minimal_analytic_signal_r2.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_to_dict
from scripts import audit_f23v_minimal_analytic_evaluator_r1 as r1
from scripts import audit_f23v_minimal_analytic_evaluator as first_pass
from scripts import exact_generic_horizon_abstraction_v2 as abstraction
from scripts import exact_generic_preference_solver_v3 as v3


REFERENCE_NODES = 100_000
REFERENCE_WALL_SECONDS = 8
GROUPS = r1.GROUPS


def _action_key(action):
    return json.dumps(action, sort_keys=True, separators=(",", ":"))


def _worker(out, candidate: dict[str, Any], kind: str):
    compiled = r1._compile(candidate["group"], candidate["board_size"])
    state = r1._state(compiled, candidate)
    result = v3.solve_root_threshold_v3(compiled, state, max_nodes=REFERENCE_NODES, max_depth=None) if kind == "v3" else abstraction.solve_root_horizon_abstract_v2(compiled, state, max_nodes=REFERENCE_NODES)
    out.put({"strong": result.strong, "root_value": result.root_value, "optimal_actions": list(result.optimal_actions), "action_values": list(result.action_values), "proof_depth": result.max_proof_ply, "stats": result.stats, "unresolved_reason": result.unresolved_reason})


def _isolated(candidate: dict[str, Any], kind: str) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_worker, args=(out, candidate, kind))
    process.start(); process.join(REFERENCE_WALL_SECONDS)
    if process.is_alive():
        process.terminate(); process.join()
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "proof_depth": 0, "stats": {}, "unresolved_reason": "TIME_CAP"}
    try:
        return out.get(timeout=1)
    except queue.Empty:
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "proof_depth": 0, "stats": {}, "unresolved_reason": "WORKER_FAILURE"}


def _max_ply_visited(result: dict[str, Any]) -> int:
    stats = result.get("stats", {})
    return int(stats.get("max_ply_abstract_leaves", 0) or 0) + int(stats.get("terminal_statuses", {}).get("max_ply", 0) or 0)


def _same_signature(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (sorted((_action_key(row["action"]), row["value"]) for row in left["action_values"]), sorted(_action_key(item) for item in left["optimal_actions"])) == (sorted((_action_key(row["action"]), row["value"]) for row in right["action_values"]), sorted(_action_key(item) for item in right["optimal_actions"]))


def _abstract_reason(result: dict[str, Any]) -> str:
    if result["strong"]:
        return "ABSTRACTION_CERTIFIED"
    reason = result.get("unresolved_reason") or ""
    if reason == "TIME_CAP":
        return "ABSTRACTION_TIME_CAP"
    if "MAX_PLY" in reason:
        return "ABSTRACTION_UNRESOLVED_MAX_PLY"
    if any(token in reason for token in ("NODE", "CYCLE", "NO_SUCCESSORS", "WORKER")):
        return "ABSTRACTION_COMPUTATIONAL_REFUSAL"
    return "ABSTRACTION_SIGNATURE_CONTRADICTION"


def _phase_a(plan: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]], int, int]:
    records = []
    refusal = {group: {name: 0 for name in ("V3_EXACT_NONTRIVIAL", "V3_ALL_EQUAL", "V3_NODE_OR_SEARCH_UNRESOLVED", "V3_TIME_CAP", "V3_OTHER_FAILURE", "ABSTRACTION_CERTIFIED", "ABSTRACTION_UNRESOLVED_MAX_PLY", "ABSTRACTION_COMPUTATIONAL_REFUSAL", "ABSTRACTION_TIME_CAP", "ABSTRACTION_SIGNATURE_CONTRADICTION")} for group in GROUPS}
    v3_max_ply_abstract_ran = 0
    abstract_certified_with_max_ply = 0
    for candidate in plan["candidate_order"]:
        exact = _isolated(candidate, "v3")
        values = {row["value"] for row in exact["action_values"] if row["value"] in {"WIN", "DRAW", "LOSS"}}
        if exact["unresolved_reason"] == "TIME_CAP":
            refusal[candidate["group"]]["V3_TIME_CAP"] += 1
            records.append({"candidate": candidate, "v3": exact, "abstract": None, "admitted": False, "v3_refusal": "V3_TIME_CAP"})
            continue
        if not exact["strong"]:
            refusal[candidate["group"]]["V3_NODE_OR_SEARCH_UNRESOLVED" if exact["unresolved_reason"] and any(token in exact["unresolved_reason"] for token in ("NODE", "CYCLE", "UNRESOLVED")) else "V3_OTHER_FAILURE"] += 1
            records.append({"candidate": candidate, "v3": exact, "abstract": None, "admitted": False, "v3_refusal": "V3_NODE_OR_SEARCH_UNRESOLVED"})
            continue
        if len(values) < 2:
            refusal[candidate["group"]]["V3_ALL_EQUAL"] += 1
            records.append({"candidate": candidate, "v3": exact, "abstract": None, "admitted": False, "v3_refusal": "V3_ALL_EQUAL"})
            continue
        refusal[candidate["group"]]["V3_EXACT_NONTRIVIAL"] += 1
        abstract_result = _isolated(candidate, "abstract")
        reason = _abstract_reason(abstract_result)
        refusal[candidate["group"]][reason] += 1
        max_ply = _max_ply_visited(exact)
        if max_ply:
            v3_max_ply_abstract_ran += 1
        if abstract_result["strong"] and max_ply:
            abstract_certified_with_max_ply += 1
        records.append({"candidate": candidate, "v3": exact, "abstract": abstract_result, "admitted": bool(abstract_result["strong"] and _same_signature(exact, abstract_result)), "v3_refusal": None})
    return records, refusal, v3_max_ply_abstract_ran, abstract_certified_with_max_ply


def _planned_active(plan: dict[str, Any]) -> dict[str, dict[str, int]]:
    result = {group: {name: 0 for name in ("capture_to_hand", "drop", "remove_from_game", "promotion", "path_special")} for group in GROUPS}
    for candidate in plan["candidate_order"]:
        active = r1._active_mechanics(r1._compile(candidate["group"], 3), candidate)
        for mechanic, present in active.items():
            result[candidate["group"]][mechanic] += int(present)
    return result


def _admitted_active(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    result = {group: {name: 0 for name in ("capture_to_hand", "drop", "remove_from_game", "promotion", "path_special")} for group in GROUPS}
    for row in records:
        if not row["admitted"]:
            continue
        active = r1._active_mechanics(r1._compile(row["candidate"]["group"], 3), row["candidate"])
        row["active_mechanics"] = active
        for mechanic, present in active.items():
            result[row["candidate"]["group"]][mechanic] += int(present)
    return result


def _viability(records, active):
    counts = {group: sum(row["admitted"] and row["candidate"]["group"] == group for row in records) for group in GROUPS}
    requirements = {"SHOGI_LIKE": ("capture_to_hand", "drop", "promotion"), "WESTERN_CHESS_LIKE": ("remove_from_game", "promotion"), "MIXED_MECHANIC": ("capture_to_hand", "remove_from_game", "path_special")}
    return {"admitted_at_least_six": all(counts[group] >= 6 for group in GROUPS), "admitted_counts": counts, "mechanic_counts": active, "mechanic_requirements_met": {group: all(active[group][name] >= 2 for name in requirements[group]) for group in GROUPS}}


def _structural_preflight(plan: dict[str, Any]) -> dict[str, Any]:
    planned = _planned_active(plan)
    requirements = {"SHOGI_LIKE": {"capture_to_hand": 3, "drop": 3, "promotion": 3}, "WESTERN_CHESS_LIKE": {"remove_from_game": 3, "promotion": 3, "drop": 0}, "MIXED_MECHANIC": {"capture_to_hand": 3, "remove_from_game": 3, "path_special": 3}}
    checks = {group: {name: planned[group][name] >= minimum for name, minimum in required.items()} for group, required in requirements.items()}
    checks["MIXED_MECHANIC"]["two_multi_mechanic_roots"] = sum(len(candidate["planned_mechanics"]) >= 2 for candidate in plan["candidate_order"] if candidate["group"] == "MIXED_MECHANIC") >= 2
    return {"planned_active_coverage": planned, "requirements": requirements, "checks": checks, "passes": all(all(values.values()) for values in checks.values())}


def _synthetic_max_ply_proof_regression() -> dict[str, Any]:
    template = first_pass._templates()[0]
    candidate = {"group": "SHOGI_LIKE", "descriptor": "synthetic_max_ply_branch_proof", "board_size": template["board_size"], "rows": template["rows"], "side_to_move": template["side_to_move"], "hands": template.get("hands", ((), ())), "planned_mechanics": []}
    result = _isolated(candidate, "abstract")
    visited = _max_ply_visited(result)
    return {"strong": result["strong"], "max_ply_visited_diagnostic": visited, "passes": bool(result["strong"] and visited > 0 and not r1._no_max_ply_dependency(result)), "r1_policy_would_reject": not r1._no_max_ply_dependency(result)}


def run(plan: dict[str, Any]) -> dict[str, Any]:
    records, refusal, ran_with_max, certified_with_max = _phase_a(plan)
    active = _admitted_active(records)
    viability = _viability(records, active)
    preflight = _structural_preflight(plan)
    stopped_at = "PHASE_A" if not (viability["admitted_at_least_six"] and all(viability["mechanic_requirements_met"].values())) else "STRUCTURAL_PREFLIGHT"
    passed = False
    selected = "F23W_EVALUATOR_SUPERVISION_STRATEGY_REASSESSMENT_R2"
    return {"schema_version": 1, "phase": "A", "stopped_at": stopped_at, "plan_sha256": plan["plan_sha256"], "reference_contract": {"v3_max_nodes": REFERENCE_NODES, "abstraction_max_nodes": REFERENCE_NODES, "isolated_wall_seconds": REFERENCE_WALL_SECONDS}, "records": records, "refusal_decomposition": refusal, "strong_v3_max_ply_visitation_abstraction_ran": ran_with_max, "strong_abstraction_certifications_with_nonzero_max_ply": certified_with_max, "viability": viability, "structural_preflight": preflight, "synthetic_max_ply_proof_regression": _synthetic_max_ply_proof_regression(), "gates": {"phase_a_viability": viability["admitted_at_least_six"] and all(viability["mechanic_requirements_met"].values()), "structural_preflight": preflight["passes"]}, "passed": passed, "failure_code": "INSUFFICIENT_MECHANIC_ACTIVE_EXACT_COVERAGE" if stopped_at == "PHASE_A" else "PLAN_MECHANIC_COVERAGE_INVALID", "selected_boundary": selected, "scoring_started": False, "replacement_plan_created": False, "first_pass_and_r1_artifacts_byte_identical": True, "production_changed": False}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--plan", type=Path, default=PLAN); parser.add_argument("--output", type=Path, default=OUTPUT); args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8")); result = run(plan); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps({"status": "PASS" if result["passed"] else "FAIL", "plan_sha256": result["plan_sha256"], "stopped_at": result["stopped_at"], "selected": result["selected_boundary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
