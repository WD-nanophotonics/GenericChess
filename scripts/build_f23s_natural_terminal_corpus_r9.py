"""Build the evaluator-blind F23S natural-terminal R9 corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
PLAN = TESTS / "fixtures" / "f23s_candidate_plan_r9.json"
V10 = TESTS / "fixtures" / "evaluator_v2_corpus_v10.json"
R2 = TESTS / "fixtures" / "f23r_v10_horizon_certification_r2.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import PieceType
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23o_preference_corpus_r6 as f23o
from scripts import exact_generic_horizon_abstraction_v2 as abstraction
from scripts import exact_generic_preference_solver_v3 as v3


LADDER = (("SMALL", 2000), ("MEDIUM", 20000), ("LARGE", 100000))


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


def _plan_candidates():
    families = []
    ordinary = [(1, 0, 6), (0, 5, 6), (1, 0, 4), (0, 5, 1), (2, 0, 6), (0, 7, 4), (3, 4, 12), (4, 11, 3)]
    capture = [(0, 5, 1, 6), (0, 6, 1, 7), (3, 10, 6, 5), (1, 14, 2, 10), (0, 15, 1, 14), (2, 13, 5, 6), (3, 12, 0, 9), (1, 8, 2, 13)]
    drop = [(0, 8), (1, 8), (2, 8), (3, 12), (4, 12), (5, 12), (0, 15), (3, 15)]
    promotion = [(0, 2), (1, 2), (2, 2), (3, 2), (0, 1), (1, 1), (2, 1), (3, 1)]
    semantic = [(1, 1, 1), (2, 1, 1), (3, 1, 1), (1, 2, -1), (2, 2, 1), (3, 2, 1), (0, 1, -1), (4, 1, -1)]
    leaper = [(1, 5, 2), (2, 6, 3), (3, 7, 4), (4, 8, 5), (5, 9, 6), (6, 10, 7), (7, 11, 8), (8, 12, 9)]
    for family, mechanic, builder, values in (
        ("ordinary_anchor_terminal", "anchor_check_movement", "ordinary_anchor_terminal", ordinary),
        ("capture_recapture_terminal", "capture_recapture", "capture_recapture_terminal", capture),
        ("drop_hand_terminal", "drop_hand", "drop_hand_terminal", drop),
        ("promotion_terminal", "promotion_choice", "promotion_terminal", promotion),
        ("semantic_guard_terminal", "semantic_guard_aux_state", "semantic_guard_terminal", semantic),
        ("interposition_leaper_terminal", "interposition_leaper", "interposition_leaper_terminal", leaper),
    ):
        candidates = []
        for index, value in enumerate(values):
            if family == "ordinary_anchor_terminal":
                k, b, r = value
                n = 3 if max(value) < 9 else 4
                pieces = {(k % n, k // n): "K", (b % n, b // n): "k", (r % n, r // n): "R"}
                candidate = {"id": f"f23s-r9-ordinary-{index:02d}", "board_size": n, "max_ply": 3, "rows": _rows(n, pieces), "side_to_move": 0}
            elif family == "capture_recapture_terminal":
                n = 4; k, b, r, enemy = value
                pieces = {(k % n, k // n): "K", (b % n, b // n): "k", (r % n, r // n): "R", (enemy % n, enemy // n): "r"}
                candidate = {"id": f"f23s-r9-capture-{index:02d}", "board_size": n, "max_ply": 4, "rows": _rows(n, pieces), "side_to_move": 0}
            elif family == "drop_hand_terminal":
                n = 4; k, b = value
                pieces = {(k % n, k // n): "K", (b % n, b // n): "k"}
                candidate = {"id": f"f23s-r9-drop-{index:02d}", "board_size": n, "max_ply": 4, "rows": _rows(n, pieces), "hands": [[["R", 1]], []], "side_to_move": 0}
            elif family == "promotion_terminal":
                n = 4; file, rank = value
                pieces = {(0, 0): "K", (3, 3): "k", (file, rank): "P"}
                candidate = {"id": f"f23s-r9-promotion-{index:02d}", "board_size": n, "max_ply": 4, "rows": _rows(n, pieces), "promotion_from": [file, rank], "promotion_to": [file, rank + 1], "side_to_move": 0}
            elif family == "semantic_guard_terminal":
                file, rank, offset = value
                pieces = {(0, 0): "K", (4, 4): "k", (file, rank): "C", (3, 0): "R"}
                candidate = {"id": f"f23s-r9-semantic-{index:02d}", "board_size": 5, "max_ply": 6, "semantic_offset": [offset, 0], "rows": _rows(5, pieces), "side_to_move": 0}
            else:
                n = 4; k, b, l = value
                pieces = {(0, 0): "K", (3, 3): "k", (k % n, k // n): "L", (l % n, l // n): "R"}
                candidate = {"id": f"f23s-r9-leaper-{index:02d}", "board_size": n, "max_ply": 4, "rows": _rows(n, pieces), "side_to_move": 0}
            lineage_key = json.dumps({"family": family, "mechanic": mechanic, "builder": builder, "candidate": candidate}, sort_keys=True, separators=(",", ":"))
            lineage_id = "r9-" + hashlib.sha256(lineage_key.encode()).hexdigest()[:16]
            candidate.update({"source_lineage_key": lineage_key, "source_lineage_id": lineage_id, "planned_split": _split(lineage_id)})
            candidates.append(candidate)
        families.append({"construction_family": family, "mechanic_family": mechanic, "builder": builder, "candidates": candidates})
    return families


def make_plan():
    families = _plan_candidates()
    body = {
        "plan_version": "f23s-natural-terminal-reference-corpus-r9",
        "source_baseline_commit": "f37c12762116b3fe61b163e3124a319f8600d2d3",
        "source_v10_sha256": hashlib.sha256(V10.read_bytes()).hexdigest(),
        "source_f23r_r2_sha256": hashlib.sha256(R2.read_bytes()).hexdigest(),
        "candidate_count": sum(len(f["candidates"]) for f in families),
        "candidate_count_per_family": 8,
        "candidate_order": [c["id"] for f in families for c in f["candidates"]],
        "split_algorithm": "HOLDOUT iff int(sha256(F23N-V7|source_lineage_id)[:8],16) mod 4 == 0; otherwise DEVELOPMENT",
        "solver_contract": {"backend": "exact_generic_preference_solver_v3", "ladder": [[name, {"max_nodes": nodes, "max_depth": None}] for name, nodes in LADDER], "attempt_wall_seconds": 8, "max_depth": None},
        "abstraction_contract": {"backend": "exact_generic_horizon_abstraction_v2", "eligibility": "every root action exact and equal to V3; MAX_PLY is unknown"},
        "families": families,
    }
    body["candidate_plan_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return body


def build_candidate(candidate, family, builder):
    m = f23c._imports(); n = candidate["board_size"]
    if builder == "ordinary_anchor_terminal":
        compiled = m["make_compiled"](n, [m["king"](), m["rook"]()], repetition_limit=2, max_ply=candidate["max_ply"])
    elif builder == "capture_recapture_terminal":
        compiled = m["make_compiled"](n, [m["king"](), m["rook"]()], repetition_limit=2, max_ply=candidate["max_ply"])
    elif builder == "drop_hand_terminal":
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
    hands = candidate.get("hands", [[], []])
    return compiled, m["make_state"](compiled, candidate["rows"], side_to_move=candidate.get("side_to_move", 0), hands=hands)


def _signature(action_values, optimal):
    return (tuple(sorted((json.dumps(row["action"], sort_keys=True), row["value"]) for row in action_values)), tuple(sorted(json.dumps(action, sort_keys=True) for action in optimal)))


def _solve(compiled, state):
    attempts = []
    for tier, nodes in LADDER:
        try:
            result = v3.solve_root_threshold_v3(compiled, state, max_nodes=nodes, max_depth=None)
        except Exception as exc:
            data = {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "proof_depth": 0, "stats": {}, "unresolved_reason": f"RECONSTRUCTION_OR_SOLVER_ERROR:{type(exc).__name__}"}
            attempts.append({"tier": tier, "result": data})
            return None, None, attempts
        data = {"strong": result.strong, "root_value": result.root_value, "optimal_actions": list(result.optimal_actions), "action_values": list(result.action_values), "proof_depth": result.max_proof_ply, "stats": {k: v for k, v in result.stats.items() if k not in {"profile_seconds", "profile_proportions"}}, "unresolved_reason": result.unresolved_reason}
        attempts.append({"tier": tier, "result": data})
        if result.strong:
            return tier, data, attempts
    return None, None, attempts


def _witness(compiled, state, result, mechanic):
    if not result:
        return None
    for row in result["action_values"]:
        action = row["action"]
        if mechanic == "drop_hand" and action.get("kind") == "drop":
            return {"kind": "root_drop", "action": action}
        if mechanic == "promotion_choice" and action.get("promotion_target_id") is not None:
            return {"kind": "root_promotion", "action": action}
        if mechanic == "anchor_check_movement" and row["value"] in {"WIN", "LOSS"}:
            return {"kind": "terminal_anchor_action", "action": action, "value": row["value"]}
        if mechanic in {"capture_recapture", "interposition_leaper", "semantic_guard_aux_state"} and row["value"] in {"WIN", "LOSS"}:
            return {"kind": mechanic + "_terminal_action", "action": action, "value": row["value"]}
    return None


def build_corpus(plan):
    records = []
    for family in plan["families"]:
        for candidate in family["candidates"]:
            compiled, state = build_candidate(candidate, family, family["builder"])
            tier, exact, attempts = _solve(compiled, state)
            record = {"version": "R9", "id": candidate["id"], "construction_family": family["construction_family"], "mechanic_family": family["mechanic_family"], "builder": family["builder"], "source_lineage_key": candidate["source_lineage_key"], "source_lineage_id": candidate["source_lineage_id"], "planned_split": candidate["planned_split"], "candidate": candidate, "ruleset_fingerprint": compiled.ruleset_fingerprint, "v3_attempts": attempts, "v3_first_resolving_tier": tier, "v3_exact": exact is not None, "production_changed": False}
            if exact is None:
                record.update({"status": "V3_UNRESOLVED", "abstraction_status": "NOT_ATTEMPTED", "eligible": False})
                records.append(record); continue
            witness = _witness(compiled, state, exact, family["mechanic_family"])
            preference = len({row["value"] for row in exact["action_values"]}) >= 2
            record.update({"status": "PREFERENCE_STRONG" if preference else "SOLVED_ALL_EQUAL", "mechanic_witness": witness, "v3_root_value": exact["root_value"], "v3_root_action_values": exact["action_values"], "v3_optimal_actions": exact["optimal_actions"], "proof_depth": exact["proof_depth"], "preference_bearing": preference})
            if not preference or witness is None:
                record.update({"abstraction_status": "NOT_ELIGIBLE", "eligible": False})
                records.append(record); continue
            abstract = abstraction.solve_root_horizon_abstract_v2(compiled, state, max_nodes=100000)
            matches = abstract.strong and _signature(abstract.action_values, abstract.optimal_actions) == _signature(exact["action_values"], exact["optimal_actions"])
            record.update({"abstraction_status": "MAX_PLY_ABSTRACT_CERTIFIED" if matches else "ABSTRACTION_REFUSED", "abstraction_root_value": abstract.root_value, "abstraction_action_values": list(abstract.action_values), "abstraction_optimal_actions": list(abstract.optimal_actions), "abstraction_stats": abstract.stats, "eligible": matches})
            records.append(record)
    return records


def finalize(plan, records):
    v10 = json.loads(V10.read_text(encoding="utf-8")); v10_ids = {row["id"] for row in v10["effective_preference_representatives"]}
    eligible = [row for row in records if row["eligible"] and row["id"] not in v10_ids]
    orbit_groups = {}
    for row in eligible:
        payload = {"ruleset": row["ruleset_fingerprint"], "actions": row["v3_root_action_values"], "optimal": row["v3_optimal_actions"], "depth": row["proof_depth"], "witness": row["mechanic_witness"], "terminal": row.get("abstraction_stats", {}).get("terminal_statuses", {})}
        orbit_groups.setdefault(hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), []).append(row)
    observed = [group for group in orbit_groups.values() if len({row["planned_split"] for row in group}) > 1]
    residual = [group for group in observed if group]
    effective = [group[0] for group in orbit_groups.values() if len(group) == 1 and not any(row in group for collision in residual for row in collision)]
    dev = [row for row in effective if row["planned_split"] == "DEVELOPMENT"]; hold = [row for row in effective if row["planned_split"] == "HOLDOUT"]
    family_counts = Counter(row["construction_family"] for row in dev); lineage_counts = Counter(row["source_lineage_id"] for row in dev)
    gate_items = {"development_effective_minimum": len(dev) >= 20, "holdout_effective_minimum": len(hold) >= 6, "development_construction_families": len({row["construction_family"] for row in dev}) >= 4, "development_mechanic_families": len({row["mechanic_family"] for row in dev}) >= 4, "holdout_construction_families": len({row["construction_family"] for row in hold}) >= 3, "development_family_max_35_percent": max(family_counts.values(), default=0) <= len(dev) * .35, "development_source_lineage_max_20_percent": max(lineage_counts.values(), default=0) <= len(dev) * .20, "multiply_dependent_minimum": sum(row["proof_depth"] >= 3 for row in dev) >= 10, "all_preference_roots_wdl_diverse": all(len({item["value"] for item in row["v3_root_action_values"]}) >= 2 for row in effective), "partition_signature_minimum": len({"/".join(sorted({item["value"] for item in row["v3_root_action_values"]})) for row in dev}) >= 2, "zero_residual_behavioral_leakage": not observed, "zero_residual_source_lineage_leakage": len({row["source_lineage_id"] for row in effective}) == len(effective), "zero_v10_supervision": not any(row["id"] in v10_ids for row in effective), "zero_contradictions": all(row["abstraction_status"] == "MAX_PLY_ABSTRACT_CERTIFIED" for row in effective)}
    full_gate = all(gate_items.values())
    signal_items = {key: value for key, value in gate_items.items()}
    signal_items.update({"development_effective_minimum": len(dev) >= 12, "holdout_effective_minimum": len(hold) >= 4, "multiply_dependent_minimum": sum(row["proof_depth"] >= 3 for row in dev) >= 6})
    signal_gate = all(signal_items.values())
    selected = "F23T_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE_R4" if full_gate else "F23T_RULE_DERIVED_EVALUATOR_V2_SIGNAL_PROBE_R1" if signal_gate else "F23T_NATURAL_TERMINAL_REFERENCE_CORPUS_R10"
    return {"schema_version": 11, "corpus_id": "evaluator-v2-corpus-v11", "historical_source_hashes": {"v10": hashlib.sha256(V10.read_bytes()).hexdigest(), "f23r_r2": hashlib.sha256(R2.read_bytes()).hexdigest()}, "candidate_plan": plan, "records": records, "eligible_preference_representatives": effective, "fit_eligible_development_orbit_ids": [row["id"] for row in dev], "validation_eligible_holdout_orbit_ids": [row["id"] for row in hold], "v10_historical_control_ids": sorted(v10_ids), "diagnostics": {"v3_exact": sum(row["v3_exact"] for row in records), "v3_unresolved": sum(not row["v3_exact"] for row in records), "preference_bearing": sum(row.get("preference_bearing", False) for row in records), "witness_qualified": sum(row.get("mechanic_witness") is not None for row in records), "abstraction_certified": sum(row.get("abstraction_status") == "MAX_PLY_ABSTRACT_CERTIFIED" for row in records), "abstraction_refused": sum(row.get("abstraction_status") == "ABSTRACTION_REFUSED" for row in records), "all_equal": sum(row.get("status") == "SOLVED_ALL_EQUAL" for row in records), "observed_leakage_groups": len(observed), "residual_leakage_groups": len(residual), "duplicate_orbit_groups": sum(len(group) > 1 for group in orbit_groups.values())}, "coverage": {"development": len(dev), "holdout": len(hold), "development_by_family": dict(sorted(family_counts.items())), "proof_depth": dict(sorted(Counter("MULTIPLY_DEPENDENT" if row["proof_depth"] >= 3 else "REPLY_DEPENDENT" if row["proof_depth"] >= 2 else "IMMEDIATE" for row in effective).items())), "wdl_partitions": dict(sorted(Counter("/".join(sorted({item["value"] for item in row["v3_root_action_values"]})) for row in effective).items()))}, "advancement_gate": {"passes": full_gate, "items": gate_items}, "signal_probe_gate": {"passes": signal_gate, "items": signal_items}, "production_changed": False, "v10_rewritten": False, "selected_next_boundary": selected}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--plan", type=Path, default=PLAN); parser.add_argument("--output", type=Path, default=None); parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    if args.plan_only:
        plan = make_plan(); args.plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(plan["candidate_plan_sha256"]); return
    plan = json.loads(args.plan.read_text(encoding="utf-8")); records = build_corpus(plan); result = finalize(plan, records); output = args.output or (TESTS / "fixtures" / "evaluator_v2_corpus_v11.json"); output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps({"status": "PASS", "planned": len(records), "development": result["coverage"]["development"], "holdout": result["coverage"]["holdout"], "eligible": len(result["eligible_preference_representatives"]), "full_gate": result["advancement_gate"]["passes"], "signal_gate": result["signal_probe_gate"]["passes"], "selected": result["selected_next_boundary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
