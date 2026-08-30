"""Build the final deterministic F23T/R10 natural-terminal V12 corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import queue
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
PLAN = TESTS / "fixtures" / "f23t_candidate_plan_r10.json"
V10 = TESTS / "fixtures" / "evaluator_v2_corpus_v10.json"
V11 = TESTS / "fixtures" / "evaluator_v2_corpus_v11.json"
R9_DIAGNOSIS = TESTS / "fixtures" / "f23s_r9_failure_diagnosis.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import PieceType
from generic_chess.core.search_runtime import SearchPathRuntime
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23o_preference_corpus_r6 as f23o
from scripts import exact_generic_horizon_abstraction_v2 as abstraction
from scripts import exact_generic_preference_solver_v3 as v3


LADDER = (("SMALL", 2000), ("MEDIUM", 20000), ("LARGE", 100000))
WALL_SECONDS = 8
FAMILY_CAP = 12
ENUMERATION_SCAN_CAP = 600


def _rows(n, pieces):
    board = [["."] * n for _ in range(n)]
    for (file, rank), piece in pieces.items():
        if board[rank][file] != ".":
            raise ValueError((file, rank))
        board[rank][file] = piece
    return ["".join(row) for row in reversed(board)]


def _split(lineage_id):
    value = int(hashlib.sha256(f"F23N-V7|{lineage_id}".encode()).hexdigest()[:8], 16)
    return "HOLDOUT" if value % 4 == 0 else "DEVELOPMENT"


def _descriptor(family, mechanic, builder, candidate):
    payload = {"family": family, "mechanic": mechanic, "builder": builder, "candidate": {key: value for key, value in candidate.items() if key not in {"id", "source_lineage_id", "source_lineage_key", "planned_split", "structural_prefilter"}}}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _candidate(family, mechanic, builder, payload):
    lineage_key = _descriptor(family, mechanic, builder, payload)
    digest = hashlib.sha256(lineage_key.encode()).hexdigest()
    result = dict(payload)
    result.update({"id": f"f23t-r10-{family}-{digest[:10]}", "source_lineage_key": lineage_key, "source_lineage_id": "r10-" + digest[:16]})
    result["planned_split"] = _split(result["source_lineage_id"])
    return result


def build_candidate(candidate, builder):
    m = f23c._imports(); n = candidate["board_size"]
    if builder in {"ordinary_anchor_terminal", "capture_recapture_terminal", "drop_hand_terminal"}:
        compiled = m["make_compiled"](n, [m["king"](), m["rook"]()], repetition_limit=2, max_ply=candidate["max_ply"])
    elif builder == "promotion_terminal":
        pawn = PieceType("P", "P", (LeapAtom((0, 1)),), is_promotable=True, promotion_target_ids=("G", "H"))
        strong = PieceType("G", "G", (LeapAtom((1, 0)), LeapAtom((-1, 0)), LeapAtom((0, 1)), LeapAtom((0, -1))))
        weak = PieceType("H", "H", ())
        compiled = m["make_compiled"](n, [m["king"](), pawn, strong, weak], auto_promotion=True, repetition_limit=2, max_ply=candidate["max_ply"])
    elif builder == "semantic_guard_terminal":
        compiled = f23o._semantic_compiled(candidate)
    elif builder == "interposition_leaper_terminal":
        compiled = m["make_compiled"](n, [m["king"](), m["rook"](), m["T"]("L", LeapAtom((1, 2)), LeapAtom((2, 1)), LeapAtom((-1, 2)), LeapAtom((-2, 1)))], repetition_limit=2, max_ply=candidate["max_ply"])
    else:
        raise AssertionError(builder)
    raw_hands = candidate.get("hands", [[], []])
    hands = ([tuple(item) for item in raw_hands[0]], [tuple(item) for item in raw_hands[1]])
    return compiled, m["make_state"](compiled, candidate["rows"], side_to_move=candidate.get("side_to_move", 0), hands=hands)


def _structural(candidate, mechanic, builder):
    try:
        compiled, state = build_candidate(candidate, builder)
        runtime = SearchPathRuntime.from_state(state, compiled)
        if runtime.terminal_status.is_terminal:
            return None
        actions = runtime.legal_actions()
        max_branching = 24 if mechanic == "drop_hand" else 20 if mechanic == "semantic_guard_aux_state" else 8
        if len(actions) < 2 or len(actions) > max_branching:
            return None
        public = [action_to_dict(action) for action in actions]
        if mechanic == "capture_recapture":
            n = candidate["board_size"]
            if not any(state.position.board[action.to_square.rank * n + action.to_square.file] is not None and state.position.board[action.to_square.rank * n + action.to_square.file].owner != state.position.side_to_move for action in actions if hasattr(action, "to_square")):
                return None
        elif mechanic == "drop_hand" and not any(item["kind"] == "drop" for item in public):
            return None
        elif mechanic == "promotion_choice" and not any(item.get("promotion_target_id") is not None for item in public):
            return None
        elif mechanic == "semantic_guard_aux_state" and not any(item.get("kind") == "semantic_board" and str(item.get("pattern_id", "")).startswith("sem_") for item in public):
            return None
        elif mechanic == "interposition_leaper" and not any(item.get("from") and candidate["rows"][candidate["board_size"] - 1 - item["from"][1]][item["from"][0]].upper() == "L" for item in public):
            return None
        terminal_scan = []
        for action in actions:
            runtime.push(action)
            try:
                status = runtime.terminal_status.status.value
                if status != "max_ply":
                    terminal_scan.append(status)
            finally:
                runtime.pop()
        return {"legal_root_actions": len(actions), "available_mechanic": mechanic, "short_terminal_statuses": sorted(terminal_scan), "public_root_actions": public}
    except Exception:
        return None


def _enumerate_family(family, mechanic, builder):
    candidates = []
    examined = 0

    def finish():
        unique = {candidate["source_lineage_id"]: candidate for candidate in candidates}
        return [unique[key] for key in sorted(unique)[:FAMILY_CAP]]

    def allow_next():
        nonlocal examined
        examined += 1
        return examined <= ENUMERATION_SCAN_CAP

    n = 3 if family == "ordinary_anchor_terminal" else 4 if family != "semantic_guard_terminal" else 5
    if family == "ordinary_anchor_terminal":
        for k in range(n * n):
            for b in range(n * n):
                for r in range(n * n):
                    if len({k, b, r}) < 3:
                        continue
                    if not allow_next(): return finish()
                    payload = {"board_size": n, "max_ply": 10, "rows": _rows(n, {(k % n, k // n): "K", (b % n, b // n): "k", (r % n, r // n): "R"}), "side_to_move": 0}
                    candidate = _candidate(family, mechanic, builder, payload); scan = _structural(candidate, mechanic, builder)
                    if scan: candidate["structural_prefilter"] = scan; candidates.append(candidate)
    elif family == "capture_recapture_terminal":
        for k in range(16):
            for b in range(16):
                for r in range(16):
                    for enemy in range(16):
                        if len({k, b, r, enemy}) < 4:
                            continue
                        if not allow_next(): return finish()
                        payload = {"board_size": 4, "max_ply": 10, "rows": _rows(4, {(k % 4, k // 4): "K", (b % 4, b // 4): "k", (r % 4, r // 4): "R", (enemy % 4, enemy // 4): "r"}), "side_to_move": 0}
                        candidate = _candidate(family, mechanic, builder, payload); scan = _structural(candidate, mechanic, builder)
                        if scan: candidate["structural_prefilter"] = scan; candidates.append(candidate)
    elif family == "drop_hand_terminal":
        for k in range(16):
            for b in range(16):
                if k == b:
                    continue
                if not allow_next(): return finish()
                payload = {"board_size": 4, "max_ply": 10, "rows": _rows(4, {(k % 4, k // 4): "K", (b % 4, b // 4): "k"}), "hands": [[["R", 1]], []], "side_to_move": 0}
                candidate = _candidate(family, mechanic, builder, payload); scan = _structural(candidate, mechanic, builder)
                if scan: candidate["structural_prefilter"] = scan; candidates.append(candidate)
    elif family == "promotion_terminal":
        for file in range(4):
            for k in range(16):
                for b in range(16):
                    source = file + 8
                    if len({source, k, b}) < 3:
                        continue
                    if not allow_next(): return finish()
                    payload = {"board_size": 4, "max_ply": 10, "rows": _rows(4, {(k % 4, k // 4): "K", (b % 4, b // 4): "k", (file, 2): "P"}), "promotion_from": [file, 2], "promotion_to": [file, 3], "side_to_move": 0}
                    candidate = _candidate(family, mechanic, builder, payload); scan = _structural(candidate, mechanic, builder)
                    if scan: candidate["structural_prefilter"] = scan; candidates.append(candidate)
    elif family == "semantic_guard_terminal":
        for cf in range(1, 4):
            for cr in range(1, 4):
                for k in range(1, 24):
                    for b in range(1, 24):
                        if len({cf + cr * 5, k, b, 3}) < 4:
                            continue
                        if not allow_next(): return finish()
                        payload = {"board_size": 5, "max_ply": 12, "semantic_offset": [1 if (cf + cr) % 2 else -1, 0], "rows": _rows(5, {(0, 0): "K", (4, 4): "k", (cf, cr): "C", (3, 0): "R"}), "side_to_move": 0}
                        candidate = _candidate(family, mechanic, builder, payload); scan = _structural(candidate, mechanic, builder)
                        if scan: candidate["structural_prefilter"] = scan; candidates.append(candidate)
    else:
        for l in range(1, 15):
            for b in range(1, 15):
                for r in range(1, 15):
                    if len({l, b, r, 0, 15}) < 5:
                        continue
                    if not allow_next(): return finish()
                    payload = {"board_size": 4, "max_ply": 10, "rows": _rows(4, {(0, 0): "K", (3, 3): "k", (l % 4, l // 4): "L", (b % 4, b // 4): "R"}), "side_to_move": 0}
                    candidate = _candidate(family, mechanic, builder, payload); scan = _structural(candidate, mechanic, builder)
                    if scan: candidate["structural_prefilter"] = scan; candidates.append(candidate)
    return finish()


def make_plan():
    specs = [("ordinary_anchor_terminal", "anchor_check_movement", "ordinary_anchor_terminal"), ("capture_recapture_terminal", "capture_recapture", "capture_recapture_terminal"), ("drop_hand_terminal", "drop_hand", "drop_hand_terminal"), ("promotion_terminal", "promotion_choice", "promotion_terminal"), ("semantic_guard_terminal", "semantic_guard_aux_state", "semantic_guard_terminal"), ("interposition_leaper_terminal", "interposition_leaper", "interposition_leaper_terminal")]
    families = [{"construction_family": family, "mechanic_family": mechanic, "builder": builder, "candidates": _enumerate_family(family, mechanic, builder)} for family, mechanic, builder in specs]
    body = {"plan_version": "f23t-final-natural-terminal-reference-corpus-r10", "source_v11_sha256": hashlib.sha256(V11.read_bytes()).hexdigest(), "source_r9_diagnosis_sha256": hashlib.sha256(R9_DIAGNOSIS.read_bytes()).hexdigest(), "source_baseline_commit": "4ef94d3782255d4b74e9fe9bbc53edc3542c027b", "enumeration": {"board_sizes": {"ordinary": 3, "other_board": 4, "semantic": 5}, "prefilter_root_actions": {"ordinary/capture/promotion/leaper": [2, 8], "drop_hand": [2, 24], "semantic": [2, 20]}, "enumeration_scan_cap": ENUMERATION_SCAN_CAP, "family_cap": FAMILY_CAP, "canonicalization": "canonical JSON semantic descriptor; display ID excluded from lineage"}, "candidate_count": sum(len(f["candidates"]) for f in families), "candidate_count_per_family": {f["construction_family"]: len(f["candidates"]) for f in families}, "candidate_order": [candidate["id"] for f in families for candidate in f["candidates"]], "split_algorithm": "HOLDOUT iff int(sha256(F23N-V7|source_lineage_id)[:8],16) mod 4 == 0; otherwise DEVELOPMENT", "solver_contract": {"backend": "exact_generic_preference_solver_v3", "ladder": [[name, {"max_nodes": nodes, "max_depth": None, "wall_seconds": WALL_SECONDS}] for name, nodes in LADDER]}, "abstraction_contract": {"backend": "exact_generic_horizon_abstraction_v2", "ladder": [[name, {"max_nodes": nodes, "wall_seconds": WALL_SECONDS}] for name, nodes in LADDER]}, "families": families}
    body["candidate_plan_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return body


def _worker_v3(out, compiled, state, nodes):
    result = v3.solve_root_threshold_v3(compiled, state, max_nodes=nodes, max_depth=None)
    out.put({"strong": result.strong, "root_value": result.root_value, "optimal_actions": list(result.optimal_actions), "action_values": list(result.action_values), "proof_depth": result.max_proof_ply, "stats": {key: value for key, value in result.stats.items() if key not in {"profile_seconds", "profile_proportions"}}, "unresolved_reason": result.unresolved_reason})


def _worker_abstraction(out, compiled, state, nodes):
    result = abstraction.solve_root_horizon_abstract_v2(compiled, state, max_nodes=nodes)
    out.put({"strong": result.strong, "root_value": result.root_value, "optimal_actions": list(result.optimal_actions), "action_values": list(result.action_values), "max_proof_ply": result.max_proof_ply, "stats": result.stats, "unresolved_reason": result.unresolved_reason})


def _isolated(worker, compiled, state, nodes):
    context = multiprocessing.get_context("spawn"); out = context.Queue(); process = context.Process(target=worker, args=(out, compiled, state, nodes)); process.start(); process.join(WALL_SECONDS)
    if process.is_alive():
        process.terminate(); process.join(); return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "stats": {}, "unresolved_reason": "ABSTRACT_TIME_CAP" if worker is _worker_abstraction else "V3_TIME_CAP", "external_refusal": "TIME_CAP"}
    try:
        return out.get(timeout=1)
    except queue.Empty:
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "stats": {}, "unresolved_reason": "ABSTRACT_WORKER_FAILURE" if worker is _worker_abstraction else "V3_WORKER_FAILURE", "external_refusal": "WORKER_FAILURE"}


def _ladder(compiled, state, worker):
    attempts = []
    for tier, nodes in LADDER:
        result = _isolated(worker, compiled, state, nodes); attempts.append({"tier": tier, "limits": {"max_nodes": nodes, "wall_seconds": WALL_SECONDS}, "result": result})
        if result.get("strong"):
            return tier, result, attempts
    return None, None, attempts


def _strict_witness(candidate, result, mechanic):
    if not result or len({row["value"] for row in result["action_values"]}) < 2:
        return None
    m = f23c._imports(); compiled, state = build_candidate(candidate, candidate["builder"]); n = candidate["board_size"]
    runtime = SearchPathRuntime.from_state(state, compiled)
    for row in result["action_values"]:
        action = row["action"]
        if mechanic == "drop_hand" and action.get("kind") == "drop":
            return {"kind": "root_drop", "action": action, "value": row["value"]}
        if mechanic == "promotion_choice" and action.get("promotion_target_id") is not None:
            return {"kind": "root_promotion", "action": action, "value": row["value"]}
        if mechanic == "semantic_guard_aux_state" and action.get("kind") == "semantic_board" and str(action.get("pattern_id", "")).startswith("sem_"):
            return {"kind": "root_custom_semantic", "pattern_id": action.get("pattern_id"), "action": action, "value": row["value"]}
        if mechanic == "interposition_leaper" and action.get("from"):
            file, rank = action["from"]; actor = candidate["rows"][n - 1 - rank][file]
            if actor.upper() == "L":
                return {"kind": "root_designated_leaper", "action": action, "value": row["value"]}
        if mechanic == "capture_recapture" and action.get("to"):
            file, rank = action["to"]; target = state.position.board[rank * n + file]
            if target is not None and target.owner != state.position.side_to_move:
                return {"kind": "root_actual_capture", "action": action, "value": row["value"]}
        if mechanic == "anchor_check_movement" and row["value"] in {"WIN", "LOSS"}:
            return {"kind": "root_anchor_terminal_or_check", "action": action, "value": row["value"]}
    return None


def _signature(rows, optimal):
    return (tuple(sorted((json.dumps(row["action"], sort_keys=True), row["value"]) for row in rows)), tuple(sorted(json.dumps(action, sort_keys=True) for action in optimal)))


def build_corpus(plan):
    records = []
    for family in plan["families"]:
        for candidate in family["candidates"]:
            candidate["builder"] = family["builder"]
            compiled, state = build_candidate(candidate, family["builder"])
            v3_tier, exact, v3_attempts = _ladder(compiled, state, _worker_v3)
            record = {"version": "R10", "id": candidate["id"], "construction_family": family["construction_family"], "mechanic_family": family["mechanic_family"], "builder": family["builder"], "candidate": candidate, "source_lineage_key": candidate["source_lineage_key"], "source_lineage_id": candidate["source_lineage_id"], "planned_split": candidate["planned_split"], "structural_prefilter": candidate["structural_prefilter"], "v3_first_resolving_tier": v3_tier, "v3_attempts": v3_attempts, "v3_exact": exact is not None}
            if exact is None:
                record.update({"status": "V3_UNRESOLVED", "strict_witness_status": "NOT_ATTEMPTED", "eligible": False}); records.append(record); continue
            witness = _strict_witness(candidate, exact, family["mechanic_family"]); preference = len({row["value"] for row in exact["action_values"]}) >= 2
            record.update({"status": "PREFERENCE_STRONG" if preference else "SOLVED_ALL_EQUAL", "preference_bearing": preference, "strict_mechanic_witness": witness, "strict_witness_status": "PASS" if witness else "WITNESS_UNPROVEN", "v3_root_value": exact["root_value"], "v3_root_action_values": exact["action_values"], "v3_optimal_actions": exact["optimal_actions"], "proof_depth": exact["proof_depth"]})
            if not preference or witness is None:
                record.update({"abstraction_status": "NOT_ELIGIBLE", "eligible": False}); records.append(record); continue
            abs_tier, abstract, abs_attempts = _ladder(compiled, state, _worker_abstraction)
            matches = abstract is not None and abstract["strong"] and _signature(abstract["action_values"], abstract["optimal_actions"]) == _signature(exact["action_values"], exact["optimal_actions"])
            record.update({"abstraction_status": "MAX_PLY_ABSTRACT_CERTIFIED" if matches else "ABSTRACTION_REFUSED", "abstraction_first_resolving_tier": abs_tier, "abstraction_attempts": abs_attempts, "abstraction_root_value": abstract["root_value"] if abstract else None, "abstraction_action_values": abstract["action_values"] if abstract else [], "abstraction_optimal_actions": abstract["optimal_actions"] if abstract else [], "abstraction_stats": abstract["stats"] if abstract else {}, "eligible": matches})
            records.append(record)
    return records


def finalize(plan, records):
    v10_ids = {row["id"] for row in json.loads(V10.read_text(encoding="utf-8"))["effective_preference_representatives"]}; v11_ids = {row["id"] for row in json.loads(V11.read_text(encoding="utf-8"))["eligible_preference_representatives"]}
    eligible = [row for row in records if row.get("eligible") and row["id"] not in v10_ids and row["id"] not in v11_ids]
    orbit_groups = {}
    for row in eligible:
        payload = {"ruleset": row["candidate"], "actions": row["v3_root_action_values"], "optimal": row["v3_optimal_actions"], "depth": row["proof_depth"], "witness": row["strict_mechanic_witness"], "terminal": row.get("abstraction_stats", {}).get("terminal_statuses", {})}
        orbit_groups.setdefault(hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), []).append(row)
    collisions = [group for group in orbit_groups.values() if len({row["planned_split"] for row in group}) > 1]; collided = {row["id"] for group in collisions for row in group}
    effective = [group[0] for group in orbit_groups.values() if group[0]["id"] not in collided]
    dev = [row for row in effective if row["planned_split"] == "DEVELOPMENT"]; hold = [row for row in effective if row["planned_split"] == "HOLDOUT"]
    family_counts = Counter(row["construction_family"] for row in dev); lineage_counts = Counter(row["source_lineage_id"] for row in dev)
    core = {mechanic: sum(row["mechanic_family"] == mechanic for row in dev) for mechanic in ("anchor_check_movement", "capture_recapture", "drop_hand", "promotion_choice")}
    gate = {"development_effective_minimum": len(dev) >= 20, "holdout_effective_minimum": len(hold) >= 6, "development_construction_families": len({row["construction_family"] for row in dev}) >= 4, "development_mechanic_families": len({row["mechanic_family"] for row in dev}) >= 4, "holdout_construction_families": len({row["construction_family"] for row in hold}) >= 3, "core_mechanic_minimum": all(core[m] >= 2 for m in core), "development_family_max_35_percent": max(family_counts.values(), default=0) <= len(dev) * .35, "development_source_lineage_max_20_percent": max(lineage_counts.values(), default=0) <= len(dev) * .20, "multiply_dependent_minimum": sum(row["proof_depth"] >= 3 for row in dev) >= 10, "all_preference_roots_wdl_diverse": all(len({item["value"] for item in row["v3_root_action_values"]}) >= 2 for row in effective), "all_abstract_certified": all(row["abstraction_status"] == "MAX_PLY_ABSTRACT_CERTIFIED" for row in effective), "partition_signature_minimum": len({"/".join(sorted({item["value"] for item in row["v3_root_action_values"]})) for row in dev}) >= 2, "zero_residual_behavioral_leakage": not collisions, "zero_residual_source_lineage_leakage": len({row["source_lineage_id"] for row in effective}) == len(effective), "zero_v10_v11_supervision": not any(row["id"] in v10_ids | v11_ids for row in effective), "zero_contradictions": all(row["abstraction_status"] == "MAX_PLY_ABSTRACT_CERTIFIED" for row in effective)}
    full = all(gate.values()); signal = all({**gate, "development_effective_minimum": len(dev) >= 12, "holdout_effective_minimum": len(hold) >= 4, "holdout_construction_families": len({row["construction_family"] for row in hold}) >= 3, "multiply_dependent_minimum": sum(row["proof_depth"] >= 3 for row in dev) >= 6, "core_mechanic_minimum": all(core[m] >= 1 for m in core)}.values())
    selected = "F23U_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE_R4" if full else "F23U_RULE_DERIVED_EVALUATOR_V2_SIGNAL_PROBE_R1" if signal else "F23U_HORIZON_REFERENCE_CERTIFICATION_FOUNDATION_R2" if any(row.get("abstraction_status") == "ABSTRACTION_REFUSED" and not row.get("abstraction_stats", {}).get("max_ply_abstract_leaves") for row in records) and not eligible else "F23U_EVALUATOR_SUPERVISION_STRATEGY_REASSESSMENT"
    return {"schema_version": 12, "corpus_id": "evaluator-v2-corpus-v12", "historical_source_hashes": {"v10": hashlib.sha256(V10.read_bytes()).hexdigest(), "v11": hashlib.sha256(V11.read_bytes()).hexdigest(), "r9_diagnosis": hashlib.sha256(R9_DIAGNOSIS.read_bytes()).hexdigest()}, "candidate_plan": plan, "records": records, "eligible_preference_representatives": effective, "fit_eligible_development_orbit_ids": [row["id"] for row in dev], "validation_eligible_holdout_orbit_ids": [row["id"] for row in hold], "v10_historical_control_ids": sorted(v10_ids), "v11_historical_control_ids": sorted(v11_ids), "diagnostics": {"planned": len(records), "v3_exact": sum(row["v3_exact"] for row in records), "v3_unresolved": sum(not row["v3_exact"] for row in records), "preference_bearing": sum(row.get("preference_bearing", False) for row in records), "all_equal": sum(row.get("status") == "SOLVED_ALL_EQUAL" for row in records), "strict_witness_qualified": sum(row.get("strict_witness_status") == "PASS" for row in records), "abstraction_certified": sum(row.get("abstraction_status") == "MAX_PLY_ABSTRACT_CERTIFIED" for row in records), "abstraction_refused": sum(row.get("abstraction_status") == "ABSTRACTION_REFUSED" for row in records), "observed_cross_split_orbits": len(collisions), "residual_cross_split_orbits": len(collisions), "core_mechanic_effective": core}, "coverage": {"development": len(dev), "holdout": len(hold), "development_by_family": dict(sorted(family_counts.items())), "proof_depth": dict(sorted(Counter("MULTIPLY_DEPENDENT" if row["proof_depth"] >= 3 else "REPLY_DEPENDENT" if row["proof_depth"] >= 2 else "IMMEDIATE" for row in effective).items())), "wdl_partitions": dict(sorted(Counter("/".join(sorted({item["value"] for item in row["v3_root_action_values"]})) for row in effective).items())), "core_mechanic_effective": core}, "advancement_gate": {"passes": full, "items": gate}, "signal_probe_gate": {"passes": signal, "items": {**gate, "development_effective_minimum": len(dev) >= 12, "holdout_effective_minimum": len(hold) >= 4, "holdout_construction_families": len({row["construction_family"] for row in hold}) >= 3, "multiply_dependent_minimum": sum(row["proof_depth"] >= 3 for row in dev) >= 6, "core_mechanic_minimum": all(core[m] >= 1 for m in core)}}, "production_changed": False, "v11_rewritten": False, "selected_next_boundary": selected}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--plan", type=Path, default=PLAN); parser.add_argument("--output", type=Path, default=None); parser.add_argument("--plan-only", action="store_true"); args = parser.parse_args()
    if args.plan_only:
        plan = make_plan(); args.plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(plan["candidate_plan_sha256"]); return
    plan = json.loads(args.plan.read_text(encoding="utf-8")); records = build_corpus(plan); result = finalize(plan, records); output = args.output or (TESTS / "fixtures" / "evaluator_v2_corpus_v12.json"); output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps({"status": "PASS", "planned": len(records), "development": result["coverage"]["development"], "holdout": result["coverage"]["holdout"], "eligible": len(result["eligible_preference_representatives"]), "full_gate": result["advancement_gate"]["passes"], "signal_gate": result["signal_probe_gate"]["passes"], "selected": result["selected_next_boundary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
