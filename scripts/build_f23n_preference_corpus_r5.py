"""Build the evaluator-blind F23N independent exact preference corpus."""

from __future__ import annotations

import argparse
import copy
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.search_runtime import SearchPathRuntime
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23j_preference_corpus_r4 as f23j
from scripts import exact_generic_preference_solver_v3 as v3


PLAN_VERSION = "f23n-independent-reference-preference-r5"
SOLVER_LIMITS = (
    ("SMALL", {"max_nodes": 2000, "max_depth": None}),
    ("MEDIUM", {"max_nodes": 20000, "max_depth": None}),
    ("LARGE", {"max_nodes": 100000, "max_depth": None}),
)
ATTEMPT_WALL_SECONDS = 8
MAX_CANDIDATES_PER_FAMILY = 8

# This plan is complete before any result, split, or orbit is inspected.
CANDIDATE_PLAN = (
    {
        "construction_family": "ordinary_anchor_movement",
        "mechanic_family": "anchor_check_movement",
        "builder": "legacy_anchor_mate",
        "parameters": ((5, True), (5, False), (6, True), (6, False), (7, True), (7, False), (8, True), (8, False)),
        "source_families": ("ordinary-anchor-5", "ordinary-anchor-5", "ordinary-anchor-6", "ordinary-anchor-6", "ordinary-anchor-7", "ordinary-anchor-7", "ordinary-anchor-8", "ordinary-anchor-8"),
    },
    {
        "construction_family": "capture_recapture_tactics",
        "mechanic_family": "capture_recapture",
        "builder": "legacy_capture_recapture",
        "parameters": ((5, 0), (5, 1), (5, 2), (6, 0), (6, 1), (6, 2), (7, 0), (7, 1)),
        "source_families": ("capture-ray-5-0", "capture-ray-5-1", "capture-ray-5-2", "capture-ray-6-0", "capture-ray-6-1", "capture-ray-6-2", "capture-ray-7-0", "capture-ray-7-1"),
    },
    {
        "construction_family": "drop_hand_tactics",
        "mechanic_family": "drop_hand",
        "builder": "legacy_drop_hand",
        "parameters": ((5, 0, 1), (5, 0, 2), (5, 1, 1), (5, 1, 2), (6, 0, 1), (6, 0, 2), (6, 1, 1), (6, 1, 2)),
        "source_families": ("drop-ray-5-0", "drop-ray-5-0", "drop-ray-5-1", "drop-ray-5-1", "drop-ray-6-0", "drop-ray-6-0", "drop-ray-6-1", "drop-ray-6-1"),
    },
    {
        "construction_family": "promotion_choice",
        "mechanic_family": "promotion_choice",
        "builder": "auto_promotion_race",
        "parameters": ((1, 4), (2, 4), (3, 4), (1, 3), (2, 3), (3, 3), (1, 2), (2, 2)),
        "source_families": ("promotion-race-1-4", "promotion-race-2-4", "promotion-race-3-4", "promotion-race-1-3", "promotion-race-2-3", "promotion-race-3-3", "promotion-race-1-2", "promotion-race-2-2"),
    },
    {
        "construction_family": "semantic_guard_auxiliary",
        "mechanic_family": "semantic_guard_aux_state",
        "builder": "semantic_fixture_mix",
        "parameters": (("cannon", 0), ("cannon", 1), ("nifu", 1), ("nifu", 2), ("nifu", 5), ("nifu", 6), ("en_passant", 0), ("en_passant", 1)),
        "source_families": ("semantic-cannon-0", "semantic-cannon-1", "semantic-nifu-1", "semantic-nifu-2", "semantic-nifu-5", "semantic-nifu-6", "semantic-en-passant-0", "semantic-en-passant-1"),
    },
)


def _rows(n: int, pieces: dict[tuple[int, int], str]) -> list[str]:
    board = [["."] * n for _ in range(n)]
    for (file, rank), piece in pieces.items():
        if board[rank][file] != ".":
            raise ValueError(f"overlap at {(file, rank)}")
        board[rank][file] = piece
    return ["".join(board[rank]) for rank in range(n - 1, -1, -1)]


def _plan_entry(family: str):
    return next(item for item in CANDIDATE_PLAN if item["construction_family"] == family)


def _build_candidate(m: dict[str, Any], plan: dict[str, Any], parameter: tuple[Any, ...]):
    builder = plan["builder"]
    if builder == "legacy_anchor_mate":
        n, victim = parameter
        compiled = m["make_compiled"](n, [m["king"](), m["rook"](), m["T"]("D")], repetition_limit=2, max_ply=6)
        state = m["make_state"](compiled, f23c._mate_rows(n, victim=victim))
    elif builder == "legacy_capture_recapture":
        n, variant = parameter
        compiled = m["make_compiled"](n, [m["king"](), m["rook"](), m["T"]("D")], repetition_limit=2, max_ply=6)
        state = m["make_state"](compiled, f23c._capture_recapture_rows(n, variant))
    elif builder == "legacy_drop_hand":
        n, variant, count = parameter
        compiled = m["make_compiled"](n, [m["king"](), m["rook"](), m["T"]("D")], repetition_limit=2, max_ply=6)
        state = m["make_state"](compiled, f23c._drop_rows(n, variant), hands=([('R', count)], []))
    elif builder == "auto_promotion_race":
        from generic_chess.core.movement import LeapAtom

        pawn = m["T"]("P", LeapAtom((0, 1)), is_promotable=True, targets=("G", "H"))
        gold = m["T"]("G", LeapAtom((1, 0)), LeapAtom((-1, 0)), LeapAtom((0, 1)), LeapAtom((0, -1)))
        horse = m["T"]("H", LeapAtom((1, 1)), LeapAtom((-1, 1)), LeapAtom((1, -1)), LeapAtom((-1, -1)))
        compiled = m["make_compiled"](6, [m["king"](), pawn, gold, horse], auto_promotion=True, repetition_limit=2, max_ply=6)
        file, rank = parameter
        state = m["make_state"](compiled, _rows(6, {(0, 0): "K", (5, 5): "k", (file, rank): "P", (4, 4): "p"}))
    elif builder == "semantic_fixture_mix":
        fixture_name, variant = parameter
        if fixture_name == "cannon":
            compiled = m["compile_semantic_ruleset"](m["cannon_ruleset"]())
            state = m["make_state"](compiled, f23c._cannon_rows(variant))
        elif fixture_name == "nifu":
            compiled = m["compile_semantic_ruleset"](m["nifu_ruleset"]())
            state = m["make_state"](compiled, f23c._nifu_rows(variant), hands=([('P', 1)], []))
        else:
            from rule_semantics_ir_fixtures import en_passant_ruleset

            file = 2 + variant
            compiled = m["compile_semantic_ruleset"](en_passant_ruleset())
            state = m["make_state"](compiled, _rows(8, {(0, 0): "K", (7, 7): "k", (file, 1): "P", (file + 1, 3): "p"}))
    else:
        raise AssertionError(f"unknown builder {builder}")
    return compiled, state


def plan_digest() -> str:
    descriptor = {"version": PLAN_VERSION, "plan": CANDIDATE_PLAN, "ladder": SOLVER_LIMITS, "wall_seconds": ATTEMPT_WALL_SECONDS, "split": "HOLDOUT iff sha256(F23N-V7|source_family_id)[:8] mod 4 == 0"}
    return hashlib.sha256(json.dumps(descriptor, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _split_for_source(source_family_id: str) -> str:
    value = int(hashlib.sha256(f"F23N-V7|{source_family_id}".encode()).hexdigest()[:8], 16)
    return "HOLDOUT" if value % 4 == 0 else "DEVELOPMENT"


def _is_capture(position, action, board_size: int) -> bool:
    if not hasattr(action, "to_square") or not hasattr(action, "from_square"):
        return False
    target = position.board[action.to_square.rank * board_size + action.to_square.file]
    return target is not None and target.owner != position.side_to_move


def _mechanic_witness(compiled, state, result, mechanic_family: str) -> dict[str, Any] | None:
    runtime = SearchPathRuntime.from_state(state, compiled)
    action_values = result["action_values"] if isinstance(result, dict) else result.action_values
    ordered = sorted(action_values, key=lambda row: json.dumps(row["action"], sort_keys=True, separators=(",", ":")))
    for row in ordered:
        action = next(candidate for candidate in runtime.legal_actions() if action_to_dict(candidate) == row["action"])
        data = row["action"]
        if mechanic_family == "capture_recapture" and _is_capture(runtime.position, action, compiled.board_size):
            return {"kind": "root_capture", "action": data, "value": row["value"]}
        if mechanic_family == "drop_hand" and data.get("kind") == "drop":
            return {"kind": "root_drop", "action": data, "value": row["value"]}
        if mechanic_family == "promotion_choice" and data.get("promotion_target_id") is not None:
            return {"kind": "root_promotion_choice", "action": data, "value": row["value"]}
        if mechanic_family == "semantic_guard_aux_state" and data.get("kind", "").startswith("semantic_"):
            return {"kind": "root_semantic_action", "action": data, "value": row["value"], "pattern_id": data.get("pattern_id")}
        if mechanic_family == "anchor_check_movement":
            with runtime.pushed(action):
                terminal = runtime.terminal_status.status.value
                if terminal != "ongoing":
                    return {"kind": "root_terminal_witness", "action": data, "value": row["value"], "terminal_status": terminal}
    return None


def _strip_profile(stats: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in stats.items() if key not in {"profile_seconds", "profile_proportions"}}


def _worker(out, family: str, index: int, limits: dict[str, int | None]):
    m = f23c._imports()
    plan = _plan_entry(family)
    compiled, state = _build_candidate(m, plan, tuple(plan["parameters"][index]))
    result = v3.solve_root_threshold_v3(compiled, state, **limits)
    out.put({"strong": result.strong, "root_value": result.root_value, "optimal_actions": list(result.optimal_actions), "action_values": list(result.action_values), "proof_depth": result.max_proof_ply, "stats": _strip_profile(result.stats), "unresolved_reason": result.unresolved_reason})


def _attempt(family: str, index: int, limits: dict[str, int | None]) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_worker, args=(out, family, index, limits))
    process.start()
    process.join(ATTEMPT_WALL_SECONDS)
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


def _candidate_record(m, plan, index, parameter):
    compiled, state = _build_candidate(m, plan, parameter)
    attempts = []
    resolved = None
    for tier, limits in SOLVER_LIMITS:
        result = _attempt(plan["construction_family"], index, limits)
        attempts.append({"tier": tier, "limits": limits, "result": result})
        if result["strong"]:
            resolved = (tier, limits, result)
            break
    source_family_id = plan["source_families"][index]
    record = {
        "id": f"generic-f23n-{plan['builder']}-{index}",
        "construction_family": plan["construction_family"],
        "mechanic_family": plan["mechanic_family"],
        "builder": plan["builder"],
        "parameter": list(parameter),
        "source_family_id": source_family_id,
        "planned_split": _split_for_source(source_family_id),
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "attempts": [{"tier": item["tier"], "limits": item["limits"], "result": {key: value for key, value in item["result"].items() if key != "stats" or value}} for item in attempts],
        "state": f23c.f23b.state_spec(state, m),
        "solver_contract": {"backend": v3.SOLVER_VERSION, "authoritative_horizon": True, "evaluator_blind": True},
    }
    if resolved is None:
        record.update({"status": "UNRESOLVED", "first_resolving_tier": None, "strong": False, "blocker": attempts[-1]["result"]["blocker"]})
        return record
    tier, limits, result = resolved
    values = sorted({row["value"] for row in result["action_values"]})
    witness = _mechanic_witness(compiled, state, result, plan["mechanic_family"])
    if len(values) < 2:
        record.update({"status": "SOLVED_ALL_EQUAL", "first_resolving_tier": tier, "strong": True, "root_value": result["root_value"], "root_action_values": result["action_values"], "optimal_actions": result["optimal_actions"], "proof_depth": result["proof_depth"], "wdl_partition": values, "mechanic_witness": witness, "solver_stats": result["stats"]})
        return record
    if witness is None:
        record.update({"status": "SOLVED_NO_WITNESS", "first_resolving_tier": tier, "strong": True, "root_value": result["root_value"], "root_action_values": result["action_values"], "optimal_actions": result["optimal_actions"], "proof_depth": result["proof_depth"], "wdl_partition": values, "mechanic_witness": None, "solver_stats": result["stats"]})
        return record
    alternate = None
    try:
        alternate_compiled = replace(compiled, max_ply=compiled.max_ply + 2)
        alternate_result = v3.solve_root_threshold_v3(alternate_compiled, state, max_nodes=limits["max_nodes"], max_depth=None)
        if alternate_result.strong:
            left = tuple((row["action"], row["value"]) for row in result["action_values"])
            right = tuple((row["action"], row["value"]) for row in alternate_result.action_values)
            alternate = "materially max-ply-dependent" if left != right else "ordinary terminal/check/capture/promotion/drop determined"
        else:
            alternate = "mixed"
    except Exception:
        alternate = "mixed"
    proof_class = "MULTIPLY_DEPENDENT" if result["proof_depth"] >= 3 else ("REPLY_DEPENDENT" if result["proof_depth"] >= 2 else "IMMEDIATE")
    certificate_payload = {"ruleset": compiled.ruleset_fingerprint, "root_action_values": result["action_values"], "proof_depth": result["proof_depth"], "witness": witness, "terminal": {key: result["stats"].get(key, 0) for key in ("repetition_adjudications", "perpetual_check_adjudications")}}
    fingerprint = hashlib.sha256(json.dumps(certificate_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    record.update({"status": "PREFERENCE_STRONG", "first_resolving_tier": tier, "strong": True, "root_value": result["root_value"], "root_action_values": result["action_values"], "optimal_actions": result["optimal_actions"], "proof_depth": result["proof_depth"], "proof_depth_class": proof_class, "wdl_partition": values, "mechanic_witness": witness, "max_ply_dependence": alternate, "decision_certificate_fingerprint": fingerprint, "solver_stats": result["stats"]})
    return record


def _deduplicate(records):
    preference = [record for record in records if record["status"] == "PREFERENCE_STRONG"]
    groups = defaultdict(list)
    for record in preference:
        groups[(record["construction_family"], record["decision_certificate_fingerprint"])].append(record)
    representatives, duplicate_ids = [], []
    for key, group in sorted(groups.items(), key=lambda item: min(record["id"] for record in item[1])):
        group.sort(key=lambda record: record["id"])
        representatives.append(group[0])
        duplicate_ids.extend(record["id"] for record in group[1:])
    orbit_groups = defaultdict(list)
    for record in representatives:
        orbit_groups[record["decision_certificate_fingerprint"]].append(record)
    leakage = sorted({record["decision_certificate_fingerprint"] for group in orbit_groups.values() if {item["planned_split"] for item in group} == {"DEVELOPMENT", "HOLDOUT"} for record in group})
    source_leakage = sorted({source for source, group in _group_by(representatives, "source_family_id").items() if len({item["planned_split"] for item in group}) > 1})
    excluded = set(leakage)
    eligible = [record for record in representatives if record["decision_certificate_fingerprint"] not in excluded and record["source_family_id"] not in source_leakage]
    return eligible, {"duplicate_candidate_ids": sorted(duplicate_ids), "excluded_behavioral_orbit_ids": leakage, "excluded_source_family_ids": source_leakage, "all_representatives": representatives}


def _group_by(records, key):
    groups = defaultdict(list)
    for record in records:
        groups[record[key]].append(record)
    return groups


def build_corpus() -> dict[str, Any]:
    m = f23c._imports()
    records = []
    for plan in CANDIDATE_PLAN:
        for index, parameter in enumerate(plan["parameters"]):
            records.append(_candidate_record(m, plan, index, tuple(parameter)))
    effective, accounting = _deduplicate(records)
    preference = [record for record in records if record["status"] == "PREFERENCE_STRONG"]
    solved = [record for record in records if record["strong"]]
    all_equal = [record for record in records if record["status"] == "SOLVED_ALL_EQUAL"]
    eligible_dev = [record for record in effective if record["planned_split"] == "DEVELOPMENT"]
    eligible_holdout = [record for record in effective if record["planned_split"] == "HOLDOUT"]
    family_counts = Counter(record["construction_family"] for record in eligible_dev)
    source_counts = Counter(record["source_family_id"] for record in eligible_dev)
    partition_counts = Counter("/".join(record["wdl_partition"]) for record in effective)
    multi = sum(record["proof_depth_class"] == "MULTIPLY_DEPENDENT" for record in eligible_dev)
    non_max = sum(record["max_ply_dependence"] != "materially max-ply-dependent" for record in eligible_dev)
    distinct_mechanics = len({record["mechanic_family"] for record in eligible_dev})
    construction_count = len({record["construction_family"] for record in eligible_dev})
    holdout_construction_count = len({record["construction_family"] for record in eligible_holdout})
    gate_items = {
        "development_effective_minimum": len(eligible_dev) >= 20,
        "holdout_effective_minimum": len(eligible_holdout) >= 6,
        "development_construction_families": construction_count >= 4,
        "development_mechanic_families": distinct_mechanics >= 4,
        "holdout_construction_families": holdout_construction_count >= 3,
        "development_family_max_35_percent": max(family_counts.values(), default=0) <= len(eligible_dev) * 0.35,
        "development_source_family_max_20_percent": max(source_counts.values(), default=0) <= len(eligible_dev) * 0.20,
        "multiply_dependent_minimum": multi >= 10,
        "all_preference_roots_wdl_diverse": all(len(record["wdl_partition"]) >= 2 for record in effective),
        "non_max_ply_minimum": non_max * 2 >= len(eligible_dev),
        "partition_signature_minimum": len(partition_counts) >= 3,
        "zero_behavioral_orbit_leakage": not accounting["excluded_behavioral_orbit_ids"],
        "zero_source_family_leakage": not accounting["excluded_source_family_ids"],
    }
    gate = all(gate_items.values())
    historical = {}
    for name in ("evaluator_v2_corpus_v1.json", "evaluator_v2_corpus_v2.json", "evaluator_v2_corpus_v3.json", "evaluator_v2_corpus_v4.json", "evaluator_v2_corpus_v5.json", "evaluator_v2_corpus_v6.json", "evaluator_v2_candidate_spec_f23f.json", "f23k_solver_capability_v1.json", "f23k_solver_capability_v2.json", "f23l_solver_capability_v3.json", "f23m_solver_capability_v4.json", "f23m_solver_capability_v4r1.json", "f23m_solver_capability_v4r1_full.json"):
        historical[name] = hashlib.sha256((TESTS / "fixtures" / name).read_bytes()).hexdigest()
    return {
        "schema_version": 7,
        "corpus_id": "evaluator-v2-corpus-v7",
        "plan_version": PLAN_VERSION,
        "candidate_plan_sha256": plan_digest(),
        "candidate_plan": json.loads(json.dumps(CANDIDATE_PLAN)),
        "proof_budget_ladder": [[tier, limits] for tier, limits in SOLVER_LIMITS],
        "attempt_wall_seconds": ATTEMPT_WALL_SECONDS,
        "authoritative_horizon": "max_depth=None compiled max_ply",
        "planned_candidate_count": len(records),
        "max_candidates_per_construction_family": MAX_CANDIDATES_PER_FAMILY,
        "records": records,
        "effective_preference_representatives": effective,
        "non_preference_all_equal_records": all_equal,
        "unresolved_records": [record for record in records if record["status"] == "UNRESOLVED"],
        "duplicate_candidate_ids": accounting["duplicate_candidate_ids"],
        "excluded_behavioral_orbit_ids": accounting["excluded_behavioral_orbit_ids"],
        "excluded_source_family_ids": accounting["excluded_source_family_ids"],
        "fit_eligible_development_orbit_ids": sorted(record["decision_certificate_fingerprint"] for record in eligible_dev),
        "validation_eligible_holdout_orbit_ids": sorted(record["decision_certificate_fingerprint"] for record in eligible_holdout),
        "source_family_split": {source: _split_for_source(source) for source in sorted({record["source_family_id"] for record in records})},
        "coverage": {
            "planned": len(records), "solved": len(solved), "preference_strong": len(preference), "all_equal": len(all_equal), "unresolved": len(records) - len(solved),
            "effective_preference_representatives": len(effective), "development": len(eligible_dev), "holdout": len(eligible_holdout),
            "development_construction_families": construction_count, "development_mechanic_families": distinct_mechanics, "holdout_construction_families": holdout_construction_count,
            "proof_depth_classes": dict(sorted(Counter(record.get("proof_depth_class", "ALL_EQUAL") for record in effective).items())), "wdl_partition_signatures": dict(sorted(partition_counts.items())), "multiply_dependent_development": multi, "non_max_ply_development": non_max,
        },
        "historical_fixture_sha256": historical,
        "advancement_gate": {"passes": gate, "items": gate_items},
        "production_changed": False,
        "evaluator_inspection": False,
        "shogi_reference_opened": False,
        "selected_next_boundary": "F23O_REFERENCE_PREFERENCE_CORPUS_R6" if not gate else "F23O_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE_R4",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corpus = build_corpus()
    args.output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "planned": corpus["coverage"]["planned"], "solved": corpus["coverage"]["solved"], "preference": corpus["coverage"]["preference_strong"], "development": corpus["coverage"]["development"], "holdout": corpus["coverage"]["holdout"], "gate": corpus["advancement_gate"]["passes"], "selected": corpus["selected_next_boundary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
