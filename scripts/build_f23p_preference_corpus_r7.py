"""Build V9 from the frozen R7 plan with conservative accounting."""

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
PLAN_PATH = TESTS / "fixtures" / "f23p_candidate_plan_r7.json"
V8_PATH = TESTS / "fixtures" / "evaluator_v2_corpus_v8.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import PieceType
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23n_preference_corpus_r5 as f23n
from scripts import build_f23o_preference_corpus_r6 as f23o
from scripts import exact_generic_preference_solver_v3 as v3


def load_plan():
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def plan_digest(plan=None):
    plan = plan or load_plan()
    body = dict(plan)
    body.pop("candidate_plan_sha256", None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def lineage_id(key: str) -> str:
    return "r7-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def split(lineage: str) -> str:
    value = int(hashlib.sha256(f"F23N-V7|{lineage}".encode()).hexdigest()[:8], 16)
    return "HOLDOUT" if value % 4 == 0 else "DEVELOPMENT"


def build_candidate(candidate, family, builder):
    m = f23c._imports()
    n = candidate["board_size"]
    if builder == "promotion_optional_choice":
        pawn = PieceType("P", "P", (LeapAtom((0, 1)),), is_promotable=True, promotion_target_ids=("G", "H"))
        strong = PieceType("G", "G", (RayAtom((1, 0)), RayAtom((-1, 0)), RayAtom((0, 1)), RayAtom((0, -1))))
        weak = PieceType("H", "H", ())
        source = Square(*candidate["promotion_from"])
        target = Square(*candidate["promotion_to"])
        compiled = m["make_compiled"](n, [m["king"](), pawn, strong, weak], promotion={"P": ([(source, target)], [])}, repetition_limit=2, max_ply=candidate["max_ply"])
        return compiled, m["make_state"](compiled, candidate["rows"])
    return f23o._build_candidate(candidate, family, builder)


def worker(out, candidate, family, builder, limits):
    compiled, state = build_candidate(candidate, family, builder)
    result = v3.solve_root_threshold_v3(compiled, state, **limits)
    out.put({"strong": result.strong, "root_value": result.root_value, "optimal_actions": list(result.optimal_actions), "action_values": list(result.action_values), "proof_depth": result.max_proof_ply, "stats": f23n._strip_profile(result.stats), "unresolved_reason": result.unresolved_reason})


def attempt(candidate, family, builder, limits, seconds):
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=worker, args=(out, candidate, family, builder, limits))
    process.start()
    process.join(seconds)
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


def cert(compiled, result, witness):
    payload = {"ruleset": compiled.ruleset_fingerprint, "root_action_values": result["action_values"], "optimal_actions": result["optimal_actions"], "proof_depth": result["proof_depth"], "witness": witness, "terminal": {key: result["stats"].get(key, 0) for key in ("repetition_adjudications", "perpetual_check_adjudications")}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def horizon_class(compiled, state, result, limits, witness):
    if witness and witness.get("kind") == "root_terminal_witness":
        return "NATURAL_TERMINAL_CERTIFIED"
    signatures = []
    for extra in (2, 4):
        try:
            alternate = v3.solve_root_threshold_v3(replace(compiled, max_ply=compiled.max_ply + extra), state, max_nodes=limits["max_nodes"], max_depth=None)
            if not alternate.strong:
                return "HORIZON_SENSITIVITY_UNKNOWN"
            signatures.append((tuple((row["action"], row["value"]) for row in alternate.action_values), tuple(alternate.optimal_actions)))
        except Exception:
            return "HORIZON_SENSITIVITY_UNKNOWN"
    base = (tuple((row["action"], row["value"]) for row in result["action_values"]), tuple(result["optimal_actions"]))
    return "HORIZON_STABLE_EXACT" if all(signature == base for signature in signatures) else "MATERIALLY_MAX_PLY_DEPENDENT"


def new_record(family_spec, candidate, plan):
    family, builder = family_spec["construction_family"], family_spec["builder"]
    compiled, state = build_candidate(candidate, family, builder)
    attempts, resolved = [], None
    for tier, limits in plan["solver_contract"]["ladder"]:
        result = attempt(candidate, family, builder, limits, plan["solver_contract"]["attempt_wall_seconds"])
        attempts.append({"tier": tier, "limits": limits, "result": result})
        if result["strong"]:
            resolved = (tier, limits, result); break
    lineage = lineage_id(candidate["source_lineage_key"])
    record = {"version": "R7", "id": candidate["id"], "construction_family": family, "mechanic_family": family_spec["mechanic_family"], "builder": builder, "source_lineage_key": candidate["source_lineage_key"], "source_lineage_id": lineage, "planned_split": split(lineage), "plan_candidate": candidate, "ruleset_fingerprint": compiled.ruleset_fingerprint, "attempts": attempts, "state": f23c.f23b.state_spec(state, f23c._imports()), "solver_contract": {"backend": v3.SOLVER_VERSION, "authoritative_horizon": True, "evaluator_blind": True}}
    if resolved is None:
        record.update({"status": "UNRESOLVED", "strong": False, "first_resolving_tier": None, "blocker": attempts[-1]["result"]["blocker"]}); return record
    tier, limits, result = resolved
    values = sorted({row["value"] for row in result["action_values"]})
    witness = f23n._mechanic_witness(compiled, state, result, family_spec["mechanic_family"])
    status = "SOLVED_ALL_EQUAL" if len(values) < 2 else "SOLVED_NO_WITNESS" if witness is None else "PREFERENCE_STRONG"
    record.update({"status": status, "strong": True, "first_resolving_tier": tier, "root_value": result["root_value"], "root_action_values": result["action_values"], "optimal_actions": result["optimal_actions"], "proof_depth": result["proof_depth"], "wdl_partition": values, "mechanic_witness": witness, "solver_stats": result["stats"]})
    if status != "PREFERENCE_STRONG": return record
    record.update({"horizon_dependence": horizon_class(compiled, state, result, limits, witness), "proof_depth_class": "MULTIPLY_DEPENDENT" if result["proof_depth"] >= 3 else "REPLY_DEPENDENT" if result["proof_depth"] >= 2 else "IMMEDIATE", "decision_certificate_fingerprint": cert(compiled, result, witness)})
    return record


def retained_v8(v8):
    rows = []
    for source in v8["effective_preference_representatives"]:
        row = dict(source); row["version"] = "V8"; row["source_lineage_id"] = source["source_lineage_id"]; row["horizon_dependence"] = "NATURAL_TERMINAL_CERTIFIED" if source.get("max_ply_dependence") == "ordinary terminal/check/capture/promotion/drop determined" else "MATERIALLY_MAX_PLY_DEPENDENT" if source.get("max_ply_dependence") == "materially max-ply-dependent" else "HORIZON_SENSITIVITY_UNKNOWN"; rows.append(row)
    return rows


def combined(records):
    groups = defaultdict(list)
    for row in records:
        if row.get("status") == "PREFERENCE_STRONG": groups[row["decision_certificate_fingerprint"]].append(row)
    observed = sorted(fingerprint for fingerprint, group in groups.items() if {row["planned_split"] for row in group} == {"DEVELOPMENT", "HOLDOUT"})
    representatives = [sorted(group, key=lambda row: (row["version"], row["id"]))[0] for group in groups.values()]
    lineage_groups = defaultdict(list)
    for row in representatives: lineage_groups[row["source_lineage_id"]].append(row)
    observed_lineage = sorted(lineage for lineage, group in lineage_groups.items() if len({row["planned_split"] for row in group}) > 1)
    eligible = [row for row in representatives if row["decision_certificate_fingerprint"] not in set(observed) and row["source_lineage_id"] not in set(observed_lineage)]
    residual_behavior = sorted(fingerprint for fingerprint, group in ((key, [row for row in representatives if row["decision_certificate_fingerprint"] == key]) for key in groups) if {row["planned_split"] for row in group} == {"DEVELOPMENT", "HOLDOUT"} and key not in set(observed))
    return eligible, observed, observed_lineage, residual_behavior


def build_corpus():
    plan, v8 = load_plan(), json.loads(V8_PATH.read_text(encoding="utf-8"))
    assert plan["candidate_plan_sha256"] == plan_digest(plan)
    new = [new_record(family, candidate, plan) for family in plan["families"] for candidate in family["candidates"]]
    all_records = retained_v8(v8) + new
    effective, observed, observed_lineage, residual = combined(all_records)
    dev = [row for row in effective if row["planned_split"] == "DEVELOPMENT"]; holdout = [row for row in effective if row["planned_split"] == "HOLDOUT"]
    family_counts, source_counts = Counter(row["construction_family"] for row in dev), Counter(row["source_lineage_id"] for row in dev)
    stable = sum(row["horizon_dependence"] in {"NATURAL_TERMINAL_CERTIFIED", "HORIZON_STABLE_EXACT"} for row in dev)
    items = {"development_effective_minimum": len(dev) >= 20, "holdout_effective_minimum": len(holdout) >= 6, "development_construction_families": len({row["construction_family"] for row in dev}) >= 4, "development_mechanic_families": len({row["mechanic_family"] for row in dev}) >= 4, "holdout_construction_families": len({row["construction_family"] for row in holdout}) >= 3, "development_family_max_35_percent": max(family_counts.values(), default=0) <= len(dev) * .35, "development_source_lineage_max_20_percent": max(source_counts.values(), default=0) <= len(dev) * .20, "multiply_dependent_minimum": sum(row["proof_depth_class"] == "MULTIPLY_DEPENDENT" for row in dev) >= 10, "all_preference_roots_wdl_diverse": all(len(row["wdl_partition"]) >= 2 for row in effective), "non_max_ply_minimum": stable * 2 >= len(dev), "partition_signature_minimum": len({"/".join(row["wdl_partition"]) for row in dev}) >= 2, "zero_residual_behavioral_leakage": not residual, "zero_residual_source_lineage_leakage": not observed_lineage}
    return {"schema_version": 9, "corpus_id": "evaluator-v2-corpus-v9", "source_v8_fixture_sha256": hashlib.sha256(V8_PATH.read_bytes()).hexdigest(), "candidate_plan_sha256": plan["candidate_plan_sha256"], "candidate_plan": plan, "records": new, "retained_v8_preference_representatives": retained_v8(v8), "effective_preference_representatives": effective, "all_equal_diagnostic_ids": sorted(row["id"] for row in all_records if row.get("status") == "SOLVED_ALL_EQUAL"), "no_witness_diagnostic_ids": sorted(row["id"] for row in all_records if row.get("status") == "SOLVED_NO_WITNESS"), "unresolved_candidate_ids": sorted(row["id"] for row in all_records if row.get("status") == "UNRESOLVED"), "observed_cross_split_behavioral_collision_ids": observed, "residual_eligible_behavioral_leakage_ids": residual, "observed_cross_split_source_lineage_ids": observed_lineage, "residual_eligible_source_lineage_leakage_ids": [], "fit_eligible_development_orbit_ids": sorted(row["decision_certificate_fingerprint"] for row in dev), "validation_eligible_holdout_orbit_ids": sorted(row["decision_certificate_fingerprint"] for row in holdout), "coverage": {"r7_planned": len(new), "r7_solved": sum(row.get("strong", False) for row in new), "r7_preference": sum(row.get("status") == "PREFERENCE_STRONG" for row in new), "r7_all_equal": sum(row.get("status") == "SOLVED_ALL_EQUAL" for row in new), "r7_no_witness": sum(row.get("status") == "SOLVED_NO_WITNESS" for row in new), "r7_unresolved": sum(row.get("status") == "UNRESOLVED" for row in new), "combined_effective": len(effective), "development": len(dev), "holdout": len(holdout), "development_construction_families": len({row["construction_family"] for row in dev}), "development_mechanic_families": len({row["mechanic_family"] for row in dev}), "holdout_construction_families": len({row["construction_family"] for row in holdout}), "proof_depth_classes": dict(sorted(Counter(row["proof_depth_class"] for row in effective).items())), "horizon_dependence_classes": dict(sorted(Counter(row["horizon_dependence"] for row in effective).items())), "wdl_partition_signatures_development": dict(sorted(Counter("/".join(row["wdl_partition"]) for row in dev).items())), "mechanic_witness_coverage": sum(row.get("mechanic_witness") is not None for row in effective), "stable_horizon_development": stable}, "advancement_gate": {"passes": all(items.values()), "items": items}, "production_changed": False, "reference_independence": {"forbidden_inputs_consulted": False, "evaluator_inspection": False, "external_reference_opened": False}, "selected_next_boundary": "F23Q_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE_R4" if all(items.values()) else "F23Q_REFERENCE_PREFERENCE_CORPUS_R8"}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args(); corpus = build_corpus(); args.output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps({"status": "PASS", "r7_planned": corpus["coverage"]["r7_planned"], "r7_solved": corpus["coverage"]["r7_solved"], "r7_preference": corpus["coverage"]["r7_preference"], "combined_effective": corpus["coverage"]["combined_effective"], "development": corpus["coverage"]["development"], "holdout": corpus["coverage"]["holdout"], "gate": corpus["advancement_gate"]["passes"], "selected": corpus["selected_next_boundary"]}, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
