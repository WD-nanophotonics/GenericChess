"""Build the evaluator-blind F23Q V10 reference corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import queue
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
PLAN_PATH = TESTS / "fixtures" / "f23q_candidate_plan_r8.json"
V9_PATH = TESTS / "fixtures" / "evaluator_v2_corpus_v9.json"
DIAGNOSIS_PATH = TESTS / "fixtures" / "f23q_v9_diagnosis.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.movement import RayAtom
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23n_preference_corpus_r5 as f23n
from scripts import build_f23o_preference_corpus_r6 as f23o
from scripts import build_f23p_preference_corpus_r7 as f23p
from scripts import exact_generic_preference_solver_v3 as v3

LADDER = (("SMALL", {"max_nodes": 2000, "max_depth": None}), ("MEDIUM", {"max_nodes": 20000, "max_depth": None}), ("LARGE", {"max_nodes": 100000, "max_depth": None}))
ATTEMPT_WALL_SECONDS = 8


def load_plan():
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def plan_digest(plan=None):
    plan = plan or load_plan()
    body = dict(plan)
    body.pop("candidate_plan_sha256", None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def lineage_id(key):
    return "r8-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def split(lineage):
    value = int(hashlib.sha256(f"F23N-V7|{lineage}".encode()).hexdigest()[:8], 16)
    return "HOLDOUT" if value % 4 == 0 else "DEVELOPMENT"


def build_candidate(candidate, family, builder):
    if builder != "ordinary_anchor_choice":
        return f23p.build_candidate(candidate, family, builder)
    m = f23c._imports()
    compiled = m["make_compiled"](candidate["board_size"], [m["king"](), m["rook"]()], repetition_limit=2, max_ply=candidate["max_ply"])
    return compiled, m["make_state"](compiled, candidate["rows"])


def worker(out, candidate, family, builder, limits):
    compiled, state = build_candidate(candidate, family, builder)
    result = v3.solve_root_threshold_v3(compiled, state, **limits)
    out.put({"strong": result.strong, "root_value": result.root_value, "optimal_actions": list(result.optimal_actions), "action_values": list(result.action_values), "proof_depth": result.max_proof_ply, "stats": {key: value for key, value in result.stats.items() if key not in {"profile_seconds", "profile_proportions"}}, "unresolved_reason": result.unresolved_reason})


def attempt(candidate, family, builder, limits):
    compiled, state = build_candidate(candidate, {"construction_family": family, "builder": builder}, builder)
    return attempt_compiled(compiled, state, limits)


def solve_ladder(candidate, family, builder, compiled=None, state=None):
    attempts = []
    for tier, limits in LADDER:
        result = attempt(candidate, family, builder, limits) if compiled is None else attempt_compiled(compiled, state, limits)
        attempts.append({"tier": tier, "limits": limits, "result": result})
        if result["strong"]:
            return tier, result, attempts
    return None, None, attempts


def solve_direct(compiled, state, limits):
    result = v3.solve_root_threshold_v3(compiled, state, **limits)
    return {"strong": result.strong, "root_value": result.root_value, "optimal_actions": list(result.optimal_actions), "action_values": list(result.action_values), "proof_depth": result.max_proof_ply, "stats": {key: value for key, value in result.stats.items() if key not in {"profile_seconds", "profile_proportions"}}, "unresolved_reason": result.unresolved_reason, "blocker": None if result.strong else "OTHER_EXACTNESS_BLOCKER"}


def attempt_compiled(compiled, state, limits):
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=worker_compiled, args=(out, compiled, state, limits))
    process.start()
    process.join(ATTEMPT_WALL_SECONDS)
    if process.is_alive():
        process.terminate(); process.join()
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "proof_depth": 0, "stats": {}, "unresolved_reason": "REFERENCE_SOLVE_UNRESOLVED:time_cap", "blocker": "UNCLASSIFIED_TIME_CAP"}
    try:
        result = out.get_nowait()
    except queue.Empty:
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "proof_depth": 0, "stats": {}, "unresolved_reason": "REFERENCE_SOLVE_UNRESOLVED:worker_failure", "blocker": "OTHER_EXACTNESS_BLOCKER"}
    reason = result.get("unresolved_reason") or ""
    result["blocker"] = None if result["strong"] else ("COMBINATORIAL_BRANCHING" if "node_cap" in reason else "OTHER_EXACTNESS_BLOCKER")
    return result


def worker_compiled(out, compiled, state, limits):
    result = v3.solve_root_threshold_v3(compiled, state, **limits)
    out.put({"strong": result.strong, "root_value": result.root_value, "optimal_actions": list(result.optimal_actions), "action_values": list(result.action_values), "proof_depth": result.max_proof_ply, "stats": {key: value for key, value in result.stats.items() if key not in {"profile_seconds", "profile_proportions"}}, "unresolved_reason": result.unresolved_reason})


def witness(compiled, state, result, mechanic_family):
    runtime = SearchPathRuntime.from_state(state, compiled)
    for row in sorted(result["action_values"], key=lambda item: json.dumps(item["action"], sort_keys=True, separators=(",", ":"))):
        action = next(candidate for candidate in runtime.legal_actions() if action_to_dict(candidate) == row["action"])
        if mechanic_family == "drop_hand" and row["action"].get("kind") == "drop":
            return {"kind": "root_drop", "action": row["action"], "value": row["value"]}
        if mechanic_family == "promotion_choice" and row["action"].get("promotion_target_id") is not None:
            return {"kind": "root_promotion_choice", "action": row["action"], "value": row["value"]}
        if mechanic_family == "semantic_guard_aux_state" and row["action"].get("kind", "").startswith("semantic_"):
            return {"kind": "root_semantic_action", "action": row["action"], "value": row["value"], "pattern_id": row["action"].get("pattern_id")}
        if mechanic_family == "anchor_check_movement":
            with runtime.pushed(action):
                if runtime.terminal_status.status.value != "ongoing":
                    return {"kind": "root_terminal_witness", "action": row["action"], "value": row["value"], "terminal_status": runtime.terminal_status.status.value}
    return None


def certificate(compiled, result, mechanic_witness):
    payload = {"ruleset": compiled.ruleset_fingerprint, "root_action_values": result["action_values"], "optimal_actions": result["optimal_actions"], "proof_depth": result["proof_depth"], "witness": mechanic_witness, "terminal": {key: result["stats"].get(key, 0) for key in ("repetition_adjudications", "perpetual_check_adjudications", "max_ply_terminal_adjudications")}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def new_record(family, candidate, plan):
    compiled, state = build_candidate(candidate, family, family["builder"])
    tier, result, attempts = solve_ladder(candidate, family["construction_family"], family["builder"])
    record = {"version": "R8", "id": candidate["id"], "construction_family": family["construction_family"], "mechanic_family": family["mechanic_family"], "builder": family["builder"], "source_lineage_key": candidate["source_lineage_key"], "source_lineage_id": lineage_id(candidate["source_lineage_key"]), "planned_split": split(lineage_id(candidate["source_lineage_key"])), "plan_candidate": candidate, "ruleset_fingerprint": compiled.ruleset_fingerprint, "attempts": attempts, "state": f23c.f23b.state_spec(state, f23c._imports()), "solver_contract": {"backend": v3.SOLVER_VERSION, "authoritative_horizon": True, "evaluator_blind": True}}
    if result is None:
        record.update({"status": "UNRESOLVED", "strong": False, "first_resolving_tier": None, "blocker": attempts[-1]["result"]["blocker"]})
        return record
    values = sorted({row["value"] for row in result["action_values"]})
    mechanic = witness(compiled, state, result, family["mechanic_family"])
    status = "SOLVED_ALL_EQUAL" if len(values) < 2 else "SOLVED_NO_WITNESS" if mechanic is None else "PREFERENCE_STRONG"
    record.update({"status": status, "strong": True, "first_resolving_tier": tier, "root_value": result["root_value"], "root_action_values": result["action_values"], "optimal_actions": result["optimal_actions"], "proof_depth": result["proof_depth"], "wdl_partition": values, "mechanic_witness": mechanic, "solver_stats": result["stats"]})
    if status != "PREFERENCE_STRONG":
        return record
    record.update({"proof_depth_class": "MULTIPLY_DEPENDENT" if result["proof_depth"] >= 3 else "REPLY_DEPENDENT" if result["proof_depth"] >= 2 else "IMMEDIATE", "decision_certificate_fingerprint": certificate(compiled, result, mechanic)})
    record["horizon_recertification"] = recertify_compiled(compiled, state, result)
    record["horizon_dependence"] = record["horizon_recertification"]["status"]
    return record


def recertify_compiled(compiled, state, base_result=None):
    if base_result is None:
        _, base_result, base_attempts = solve_ladder({}, "", "", compiled, state)
    else:
        base_attempts = []
    signatures = [_signature(base_result)]
    proof = {"base": {"result": base_result, "attempts": base_attempts}}
    max_ply_used = base_result["stats"].get("max_ply_terminal_adjudications", 0) > 0
    for extra in (2, 4):
        current_max_ply = compiled.max_ply if hasattr(compiled, "max_ply") else compiled.support.max_ply
        tier, result, attempts = solve_ladder({}, "", "", _with_horizon(compiled, current_max_ply + extra), state)
        proof[f"plus_{extra}"] = {"first_resolving_tier": tier, "attempts": attempts}
        if result is None:
            return {"status": "HORIZON_SENSITIVITY_UNKNOWN", "proof": proof}
        signatures.append(_signature(result))
        max_ply_used = max_ply_used or result["stats"].get("max_ply_terminal_adjudications", 0) > 0
    if any(signature != signatures[0] for signature in signatures[1:]):
        status = "MATERIALLY_MAX_PLY_DEPENDENT"
    elif max_ply_used:
        status = "HORIZON_STABLE_EXACT"
    else:
        status = "NATURAL_TERMINAL_CERTIFIED"
    return {"status": status, "proof": proof, "max_ply_terminal_adjudications": max_ply_used}


def _signature(result):
    return (tuple((row["action"], row["value"]) for row in result["action_values"]), tuple(result["optimal_actions"]))


def _with_horizon(compiled, max_ply):
    if hasattr(compiled, "max_ply"):
        return replace(compiled, max_ply=max_ply)
    return replace(compiled, support=replace(compiled.support, max_ply=max_ply))


def historical_overlay(v9):
    if not DIAGNOSIS_PATH.is_file():
        raise RuntimeError("F23Q requires the completed V9 diagnosis before V10 build")
    diagnosis = json.loads(DIAGNOSIS_PATH.read_text(encoding="utf-8"))
    if diagnosis["source_fixture_sha256"] != hashlib.sha256(V9_PATH.read_bytes()).hexdigest():
        raise RuntimeError("V9 diagnosis does not match the frozen V9 fixture")
    return diagnosis["historical_horizon_recertification"]


def combined(records, historical_observed_behavior, historical_observed_source):
    groups = defaultdict(list)
    for row in records:
        if row.get("status") == "PREFERENCE_STRONG":
            groups[row["decision_certificate_fingerprint"]].append(row)
    observed = set(historical_observed_behavior) | {key for key, group in groups.items() if {row["planned_split"] for row in group} == {"DEVELOPMENT", "HOLDOUT"}}
    representatives = [sorted(group, key=lambda row: (row["version"], row["id"]))[0] for group in groups.values()]
    lineages = defaultdict(list)
    for row in representatives:
        lineages[row["source_lineage_id"]].append(row)
    observed_source = set(historical_observed_source) | {key for key, group in lineages.items() if {row["planned_split"] for row in group} == {"DEVELOPMENT", "HOLDOUT"}}
    eligible = [row for row in representatives if row["decision_certificate_fingerprint"] not in observed and row["source_lineage_id"] not in observed_source]
    residual_behavior = sorted(key for key, group in ((key, [row for row in representatives if row["decision_certificate_fingerprint"] == key]) for key in groups) if {row["planned_split"] for row in group} == {"DEVELOPMENT", "HOLDOUT"} and key not in observed)
    residual_source = sorted(key for key, group in lineages.items() if {row["planned_split"] for row in group} == {"DEVELOPMENT", "HOLDOUT"} and key not in observed_source)
    return eligible, sorted(observed), sorted(observed_source), residual_behavior, residual_source


def build_corpus():
    plan = load_plan()
    assert plan["candidate_plan_sha256"] == plan_digest(plan)
    v9 = json.loads(V9_PATH.read_text(encoding="utf-8"))
    new = [new_record(family, candidate, plan) for family in plan["families"] for candidate in family["candidates"]]
    historical = v9["retained_v8_preference_representatives"] + v9["records"]
    effective, observed, observed_source, residual, residual_source = combined(historical + new, v9["observed_cross_split_behavioral_collision_ids"], v9["observed_cross_split_source_lineage_ids"])
    overlay = historical_overlay(v9)
    effective_view = []
    for row in effective:
        view = dict(row)
        if row["id"] in overlay:
            view["horizon_dependence"] = overlay[row["id"]]["status"]
            view["horizon_recertification"] = overlay[row["id"]]
        effective_view.append(view)
    dev = [row for row in effective_view if row["planned_split"] == "DEVELOPMENT"]
    holdout = [row for row in effective_view if row["planned_split"] == "HOLDOUT"]
    families = Counter(row["construction_family"] for row in dev)
    lineages = Counter(row["source_lineage_id"] for row in dev)
    stable = sum(row.get("horizon_dependence") in {"NATURAL_TERMINAL_CERTIFIED", "HORIZON_STABLE_EXACT"} for row in dev)
    items = {"development_effective_minimum": len(dev) >= 20, "holdout_effective_minimum": len(holdout) >= 6, "development_construction_families": len(families) >= 4, "development_mechanic_families": len({row["mechanic_family"] for row in dev}) >= 4, "holdout_construction_families": len({row["construction_family"] for row in holdout}) >= 3, "development_family_max_35_percent": max(families.values(), default=0) <= len(dev) * .35, "development_source_lineage_max_20_percent": max(lineages.values(), default=0) <= len(dev) * .20, "multiply_dependent_minimum": sum(row.get("proof_depth_class") == "MULTIPLY_DEPENDENT" for row in dev) >= 10, "all_preference_roots_wdl_diverse": all(len(row.get("wdl_partition", [])) >= 2 for row in effective_view), "non_max_ply_minimum": stable * 2 >= len(dev), "partition_signature_minimum": len({"/".join(row["wdl_partition"]) for row in dev}) >= 2, "zero_residual_behavioral_leakage": not residual, "zero_residual_source_lineage_leakage": not residual_source}
    next_boundary = "F23R_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE_R4" if all(items.values()) else ("F23R_HORIZON_REFERENCE_CERTIFICATION_FOUNDATION" if stable * 2 < len(dev) else "F23R_REFERENCE_PREFERENCE_CORPUS_R9")
    return {"schema_version": 10, "corpus_id": "evaluator-v2-corpus-v10", "source_v9_fixture_sha256": hashlib.sha256(V9_PATH.read_bytes()).hexdigest(), "candidate_plan_sha256": plan["candidate_plan_sha256"], "candidate_plan": plan, "records": new, "retained_v9_effective_preference_representatives": v9["effective_preference_representatives"], "historical_horizon_recertification": overlay, "effective_preference_representatives": effective_view, "all_equal_diagnostic_ids": sorted(row["id"] for row in historical + new if row.get("status") == "SOLVED_ALL_EQUAL"), "no_witness_diagnostic_ids": sorted(row["id"] for row in historical + new if row.get("status") == "SOLVED_NO_WITNESS"), "unresolved_candidate_ids": sorted(row["id"] for row in new if row.get("status") == "UNRESOLVED"), "observed_cross_split_behavioral_collision_ids": observed, "observed_cross_split_behavioral_collisions": [{"orbit_id": key, "roots": sorted(row["id"] for row in historical + new if row.get("decision_certificate_fingerprint") == key)} for key in observed], "residual_eligible_behavioral_leakage_ids": residual, "observed_cross_split_source_lineage_ids": observed_source, "observed_cross_split_source_lineage_collisions": [{"source_lineage_id": key, "roots": sorted(row["id"] for row in historical + new if row.get("source_lineage_id") == key)} for key in observed_source], "residual_eligible_source_lineage_leakage_ids": residual_source, "fit_eligible_development_orbit_ids": sorted(row["decision_certificate_fingerprint"] for row in dev), "validation_eligible_holdout_orbit_ids": sorted(row["decision_certificate_fingerprint"] for row in holdout), "coverage": {"r8_planned": len(new), "r8_solved": sum(row.get("strong", False) for row in new), "r8_preference": sum(row.get("status") == "PREFERENCE_STRONG" for row in new), "r8_all_equal": sum(row.get("status") == "SOLVED_ALL_EQUAL" for row in new), "r8_no_witness": sum(row.get("status") == "SOLVED_NO_WITNESS" for row in new), "r8_unresolved": sum(row.get("status") == "UNRESOLVED" for row in new), "combined_effective": len(effective_view), "development": len(dev), "holdout": len(holdout), "development_by_construction_family": dict(sorted(families.items())), "development_by_mechanic_family": dict(sorted(Counter(row["mechanic_family"] for row in dev).items())), "holdout_construction_families": len({row["construction_family"] for row in holdout}), "proof_depth_classes": dict(sorted(Counter(row.get("proof_depth_class", "UNRESOLVED") for row in effective_view).items())), "horizon_classes": dict(sorted(Counter(row.get("horizon_dependence", "UNKNOWN") for row in effective_view).items())), "wdl_partition_signatures_development": dict(sorted(Counter("/".join(row["wdl_partition"]) for row in dev).items())), "multiply_dependent_development": sum(row.get("proof_depth_class") == "MULTIPLY_DEPENDENT" for row in dev), "stable_natural_development": stable, "mechanic_witness_coverage": sum(row.get("mechanic_witness") is not None for row in effective_view)}, "advancement_gate": {"passes": all(items.values()), "items": items}, "production_changed": False, "reference_independence": {"forbidden_inputs_consulted": False, "evaluator_inspection": False, "external_reference_opened": False}, "selected_next_boundary": next_boundary}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    corpus = build_corpus()
    args.output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "r8_planned": corpus["coverage"]["r8_planned"], "r8_solved": corpus["coverage"]["r8_solved"], "r8_preference": corpus["coverage"]["r8_preference"], "development": corpus["coverage"]["development"], "holdout": corpus["coverage"]["holdout"], "gate": corpus["advancement_gate"]["passes"], "selected": corpus["selected_next_boundary"]}, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
