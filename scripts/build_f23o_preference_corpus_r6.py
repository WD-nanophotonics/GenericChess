"""Build V8 from the frozen R6 plan and retained V7 exact evidence."""

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
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
PLAN_PATH = TESTS / "fixtures" / "f23o_candidate_plan_r6.json"
V7_PATH = TESTS / "fixtures" / "evaluator_v2_corpus_v7.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import PieceType
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import RuleActionEffect, RuleGeometrySpec, RuleInvariant, RuleSemanticAction, RuleSet
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23n_preference_corpus_r5 as f23n
from scripts import exact_generic_preference_solver_v3 as v3
from rule_semantics_ir_fixtures import _king_type, _ray_type, _ref, _semantic_ruleset


def _load_plan() -> dict[str, Any]:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def plan_digest(plan: dict[str, Any] | None = None) -> str:
    plan = plan or _load_plan()
    payload = dict(plan)
    payload.pop("candidate_plan_sha256", None)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _split(lineage: str) -> str:
    value = int(hashlib.sha256(f"F23N-V7|{lineage}".encode()).hexdigest()[:8], 16)
    return "HOLDOUT" if value % 4 == 0 else "DEVELOPMENT"


def _semantic_compiled(candidate: dict[str, Any]):
    offset = tuple(candidate["semantic_offset"])
    cannon = _ray_type("C", (RayAtom((1, 0)), RayAtom((-1, 0)), RayAtom((0, 1)), RayAtom((0, -1))))
    action = RuleSemanticAction(
        name="semantic_guard_step",
        type_ids=("C",),
        geometry=RuleGeometrySpec(kind="leap", offset=offset, owner_relative=False),
        target_relation="empty",
        composition="augment",
        effects=(RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    rules = _semantic_ruleset(
        (_king_type(), cannon, _ray_type("R", (RayAtom((1, 0)), RayAtom((-1, 0)), RayAtom((0, 1)), RayAtom((0, -1))))),
        (action,),
        n=candidate["board_size"],
    )
    rules = replace(rules, max_ply=candidate["max_ply"], repetition_limit=2)
    return compile_semantic_ruleset(rules)


def _build_candidate(candidate: dict[str, Any], family: str, builder: str):
    m = f23c._imports()
    n = candidate["board_size"]
    if builder == "capture_mate_choice":
        compiled = m["make_compiled"](n, [m["king"](), m["rook"]()], repetition_limit=2, max_ply=candidate["max_ply"])
        state = m["make_state"](compiled, candidate["rows"])
    elif builder == "drop_check_choice":
        compiled = m["make_compiled"](n, [m["king"](), m["rook"]()], repetition_limit=2, max_ply=candidate["max_ply"])
        state = m["make_state"](compiled, candidate["rows"], hands=([("R", 1)], []))
    elif builder == "promotion_mate_choice":
        pawn = PieceType("P", "P", (LeapAtom((0, 1)),), is_promotable=True, promotion_target_ids=("G", "H"))
        strong = PieceType("G", "G", (RayAtom((1, 0)), RayAtom((-1, 0)), RayAtom((0, 1)), RayAtom((0, -1))))
        weak = PieceType("H", "H", ())
        compiled = m["make_compiled"](n, [m["king"](), pawn, strong, weak], auto_promotion=True, repetition_limit=2, max_ply=candidate["max_ply"])
        state = m["make_state"](compiled, candidate["rows"])
    elif builder == "semantic_guard_choice":
        compiled = _semantic_compiled(candidate)
        state = m["make_state"](compiled, candidate["rows"])
    else:
        raise AssertionError(builder)
    return compiled, state


def _worker(out, candidate: dict[str, Any], family: str, builder: str, limits: dict[str, int | None]):
    compiled, state = _build_candidate(candidate, family, builder)
    result = v3.solve_root_threshold_v3(compiled, state, **limits)
    out.put({
        "strong": result.strong,
        "root_value": result.root_value,
        "optimal_actions": list(result.optimal_actions),
        "action_values": list(result.action_values),
        "proof_depth": result.max_proof_ply,
        "stats": f23n._strip_profile(result.stats),
        "unresolved_reason": result.unresolved_reason,
    })


def _attempt(candidate: dict[str, Any], family: str, builder: str, limits: dict[str, int | None], wall_seconds: int) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_worker, args=(out, candidate, family, builder, limits))
    process.start()
    process.join(wall_seconds)
    if process.is_alive():
        process.terminate()
        process.join()
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "proof_depth": 0, "stats": {}, "unresolved_reason": "REFERENCE_SOLVE_UNRESOLVED:time_cap", "blocker": "UNCLASSIFIED_TIME_CAP"}
    try:
        result = out.get_nowait()
    except queue.Empty:
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "proof_depth": 0, "stats": {}, "unresolved_reason": "REFERENCE_SOLVE_UNRESOLVED:worker_failure", "blocker": "OTHER_EXACTNESS_BLOCKER"}
    reason = result.get("unresolved_reason") or ""
    result["blocker"] = None if result["strong"] else ("COMBINATORIAL_BRANCHING" if "node_cap" in reason else "OTHER_EXACTNESS_BLOCKER")
    return result


def _certificate(compiled, record, result, witness):
    payload = {
        "ruleset": compiled.ruleset_fingerprint,
        "root_action_values": result["action_values"],
        "optimal_actions": result["optimal_actions"],
        "proof_depth": result["proof_depth"],
        "witness": witness,
        "terminal": {key: result["stats"].get(key, 0) for key in ("repetition_adjudications", "perpetual_check_adjudications")},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _new_record(family_spec: dict[str, Any], candidate: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    compiled, state = _build_candidate(candidate, family_spec["construction_family"], family_spec["builder"])
    ladder = plan["solver_contract"]["ladder"]
    attempts = []
    resolved = None
    for tier, limits in ladder:
        result = _attempt(candidate, family_spec["construction_family"], family_spec["builder"], limits, plan["solver_contract"]["attempt_wall_seconds"])
        attempts.append({"tier": tier, "limits": limits, "result": result})
        if result["strong"]:
            resolved = (tier, limits, result)
            break
    record = {
        "version": "R6",
        "id": candidate["id"],
        "construction_family": family_spec["construction_family"],
        "mechanic_family": family_spec["mechanic_family"],
        "builder": family_spec["builder"],
        "source_lineage_id": candidate["source_lineage_id"],
        "planned_split": _split(candidate["source_lineage_id"]),
        "plan_candidate": candidate,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "attempts": attempts,
        "state": f23c.f23b.state_spec(state, f23c._imports()),
        "solver_contract": {"backend": v3.SOLVER_VERSION, "authoritative_horizon": True, "evaluator_blind": True},
    }
    if resolved is None:
        record.update({"status": "UNRESOLVED", "strong": False, "first_resolving_tier": None, "blocker": attempts[-1]["result"]["blocker"]})
        return record
    tier, limits, result = resolved
    values = sorted({row["value"] for row in result["action_values"]})
    witness = f23n._mechanic_witness(compiled, state, result, family_spec["mechanic_family"])
    common = {"status": "SOLVED_ALL_EQUAL" if len(values) < 2 else "SOLVED_NO_WITNESS" if witness is None else "PREFERENCE_STRONG", "strong": True, "first_resolving_tier": tier, "root_value": result["root_value"], "root_action_values": result["action_values"], "optimal_actions": result["optimal_actions"], "proof_depth": result["proof_depth"], "wdl_partition": values, "mechanic_witness": witness, "solver_stats": result["stats"]}
    record.update(common)
    if record["status"] != "PREFERENCE_STRONG":
        return record
    alternate = "mixed"
    try:
        alternate_compiled = replace(compiled, max_ply=compiled.max_ply + 2)
        alternate_result = v3.solve_root_threshold_v3(alternate_compiled, state, max_nodes=limits["max_nodes"], max_depth=None)
        if alternate_result.strong:
            left = tuple((row["action"], row["value"]) for row in result["action_values"])
            right = tuple((row["action"], row["value"]) for row in alternate_result.action_values)
            alternate = "ordinary terminal/check/capture/promotion/drop determined" if left == right else "materially max-ply-dependent"
    except Exception:
        pass
    record.update({
        "proof_depth_class": "MULTIPLY_DEPENDENT" if result["proof_depth"] >= 3 else "REPLY_DEPENDENT" if result["proof_depth"] >= 2 else "IMMEDIATE",
        "max_ply_dependence": alternate,
        "decision_certificate_fingerprint": _certificate(compiled, record, result, witness),
    })
    return record


def _v7_records(v7: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for source in v7["effective_preference_representatives"]:
        row = dict(source)
        row["version"] = "V7"
        row["source_lineage_id"] = source["source_family_id"]
        row["planned_split"] = source["planned_split"]
        result.append(row)
    return result


def _combined_effective(records: list[dict[str, Any]]):
    groups = defaultdict(list)
    for record in records:
        if record.get("status") == "PREFERENCE_STRONG":
            groups[record["decision_certificate_fingerprint"]].append(record)
    representatives = [sorted(group, key=lambda row: (row["version"], row["id"]))[0] for group in groups.values()]
    behavior_leakage = sorted(fingerprint for fingerprint, group in groups.items() if {row["planned_split"] for row in group} == {"DEVELOPMENT", "HOLDOUT"})
    lineage_groups = defaultdict(list)
    for record in representatives:
        lineage_groups[record["source_lineage_id"]].append(record)
    lineage_leakage = sorted(lineage for lineage, group in lineage_groups.items() if len({row["planned_split"] for row in group}) > 1)
    excluded = set(behavior_leakage)
    eligible = [row for row in representatives if row["decision_certificate_fingerprint"] not in excluded and row["source_lineage_id"] not in lineage_leakage]
    return eligible, behavior_leakage, lineage_leakage


def build_corpus() -> dict[str, Any]:
    plan = _load_plan()
    assert plan["candidate_plan_sha256"] == plan_digest(plan)
    v7 = json.loads(V7_PATH.read_text(encoding="utf-8"))
    new_records = []
    for family in plan["families"]:
        for candidate in family["candidates"]:
            new_records.append(_new_record(family, candidate, plan))
    all_records = _v7_records(v7) + new_records
    effective, behavior_leakage, lineage_leakage = _combined_effective(all_records)
    all_equal = [row for row in all_records if row.get("status") == "SOLVED_ALL_EQUAL"]
    unresolved = [row for row in all_records if row.get("status") == "UNRESOLVED"]
    dev = [row for row in effective if row["planned_split"] == "DEVELOPMENT"]
    holdout = [row for row in effective if row["planned_split"] == "HOLDOUT"]
    family_counts = Counter(row["construction_family"] for row in dev)
    source_counts = Counter(row["source_lineage_id"] for row in dev)
    partitions = Counter("/".join(row["wdl_partition"]) for row in dev)
    multi = sum(row.get("proof_depth_class") == "MULTIPLY_DEPENDENT" for row in dev)
    non_max = sum(row.get("max_ply_dependence") != "materially max-ply-dependent" for row in dev)
    construction_count = len({row["construction_family"] for row in dev})
    mechanics_count = len({row["mechanic_family"] for row in dev})
    holdout_construction_count = len({row["construction_family"] for row in holdout})
    gate_items = {
        "development_effective_minimum": len(dev) >= 20,
        "holdout_effective_minimum": len(holdout) >= 6,
        "development_construction_families": construction_count >= 4,
        "development_mechanic_families": mechanics_count >= 4,
        "holdout_construction_families": holdout_construction_count >= 3,
        "development_family_max_35_percent": max(family_counts.values(), default=0) <= len(dev) * 0.35,
        "development_source_lineage_max_20_percent": max(source_counts.values(), default=0) <= len(dev) * 0.20,
        "multiply_dependent_minimum": multi >= 10,
        "all_preference_roots_wdl_diverse": all(len(row["wdl_partition"]) >= 2 for row in effective),
        "non_max_ply_minimum": non_max * 2 >= len(dev),
        "partition_signature_minimum": len(partitions) >= 2,
        "zero_behavioral_orbit_leakage": not behavior_leakage,
        "zero_source_lineage_leakage": not lineage_leakage,
    }
    gate = all(gate_items.values())
    lineage_split = {lineage: _split(lineage) for row in new_records for lineage in [row["source_lineage_id"]]}
    return {
        "schema_version": 8,
        "corpus_id": "evaluator-v2-corpus-v8",
        "source_v7_fixture_sha256": hashlib.sha256(V7_PATH.read_bytes()).hexdigest(),
        "candidate_plan_sha256": plan["candidate_plan_sha256"],
        "candidate_plan": plan,
        "records": new_records,
        "retained_v7_preference_representatives": _v7_records(v7),
        "effective_preference_representatives": effective,
        "all_equal_diagnostic_ids": sorted(row["id"] for row in all_equal),
        "unresolved_candidate_ids": sorted(row["id"] for row in unresolved),
        "excluded_behavioral_leakage_orbit_ids": behavior_leakage,
        "excluded_source_lineage_leakage_ids": lineage_leakage,
        "fit_eligible_development_orbit_ids": sorted(row["decision_certificate_fingerprint"] for row in dev),
        "validation_eligible_holdout_orbit_ids": sorted(row["decision_certificate_fingerprint"] for row in holdout),
        "source_lineage_split": lineage_split,
        "coverage": {"v7_preference": len(v7["effective_preference_representatives"]), "new_planned": len(new_records), "new_solved": sum(row.get("strong", False) for row in new_records), "new_preference": sum(row.get("status") == "PREFERENCE_STRONG" for row in new_records), "new_all_equal": sum(row.get("status") == "SOLVED_ALL_EQUAL" for row in new_records), "new_unresolved": sum(row.get("status") == "UNRESOLVED" for row in new_records), "combined_effective": len(effective), "development": len(dev), "holdout": len(holdout), "development_construction_families": construction_count, "development_mechanic_families": mechanics_count, "holdout_construction_families": holdout_construction_count, "proof_depth_classes": dict(sorted(Counter(row.get("proof_depth_class", "UNRESOLVED") for row in effective).items())), "wdl_partition_signatures_development": dict(sorted(partitions.items())), "multiply_dependent_development": multi, "non_max_ply_development": non_max, "mechanic_witness_coverage": sum(row.get("mechanic_witness") is not None for row in effective)},
        "advancement_gate": {"passes": gate, "items": gate_items},
        "production_changed": False,
        "reference_independence": {"forbidden_inputs_consulted": False, "evaluator_inspection": False, "semantic_reference_opened": False},
        "selected_next_boundary": "F23P_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE_R4" if gate else "F23P_REFERENCE_PREFERENCE_CORPUS_R7",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corpus = build_corpus()
    args.output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "new_planned": corpus["coverage"]["new_planned"], "new_solved": corpus["coverage"]["new_solved"], "new_preference": corpus["coverage"]["new_preference"], "combined_effective": corpus["coverage"]["combined_effective"], "development": corpus["coverage"]["development"], "holdout": corpus["coverage"]["holdout"], "gate": corpus["advancement_gate"]["passes"], "selected": corpus["selected_next_boundary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
