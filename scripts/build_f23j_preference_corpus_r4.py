"""Build the evaluator-blind F23J independent-mechanic preference corpus."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23g_preference_corpus_r2 as f23g
from scripts.exact_generic_preference_solver import decision_subtree_fingerprint, solve_root


V1 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json"
V2 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v2.json"
V3 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v3.json"
V4 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v4.json"
V5 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v5.json"
F23F = ROOT / "tests" / "fixtures" / "evaluator_v2_candidate_spec_f23f.json"

SOLVER_LIMITS = {"max_nodes": 2000, "max_depth": 2}

# This is the complete candidate plan.  It is intentionally data-only and is
# frozen before any candidate is solved or any split is inspected.
CANDIDATE_PLAN = (
    {
        "construction_family": "ordinary_anchor_movement",
        "mechanic_family": "anchor_check_movement",
        "builder": "legacy_anchor_mate",
        "parameters": ((5, True), (5, False), (6, True), (6, False), (7, True), (7, False)),
        "splits": ("DEVELOPMENT", "HOLDOUT", "DEVELOPMENT", "HOLDOUT", "DEVELOPMENT", "DEVELOPMENT"),
        "source_families": ("ordinary-anchor-sibling-demo", "ordinary-anchor-sibling-demo", "ordinary-anchor-6", "ordinary-anchor-6", "ordinary-anchor-7", "ordinary-anchor-7"),
    },
    {
        "construction_family": "capture_recapture_tactics",
        "mechanic_family": "capture_recapture",
        "builder": "legacy_capture_recapture",
        "parameters": ((5, 0), (5, 1), (5, 2), (6, 0), (6, 1), (6, 2)),
        "splits": ("DEVELOPMENT", "DEVELOPMENT", "HOLDOUT", "DEVELOPMENT", "HOLDOUT", "DEVELOPMENT"),
        "source_families": ("capture-ray-5-0", "capture-ray-5-1", "capture-ray-5-2", "capture-ray-6-0", "capture-ray-6-1", "capture-ray-6-2"),
    },
    {
        "construction_family": "drop_hand_tactics",
        "mechanic_family": "drop_hand",
        "builder": "legacy_drop_hand",
        "parameters": ((5, 0, 1), (5, 0, 2), (5, 1, 1), (5, 1, 2), (6, 0, 1), (6, 1, 1)),
        "splits": ("DEVELOPMENT", "HOLDOUT", "DEVELOPMENT", "DEVELOPMENT", "HOLDOUT", "DEVELOPMENT"),
        "source_families": ("drop-ray-5-0-1", "drop-ray-5-0-2", "drop-ray-5-1-1", "drop-ray-5-1-2", "drop-ray-6-0-1", "drop-ray-6-1-1"),
    },
    {
        "construction_family": "promotion_race",
        "mechanic_family": "promotion_choice",
        "builder": "auto_promotion_race",
        "parameters": ((1, 4), (2, 4), (3, 4), (1, 3), (2, 3), (3, 3)),
        "splits": ("DEVELOPMENT", "DEVELOPMENT", "HOLDOUT", "DEVELOPMENT", "HOLDOUT", "DEVELOPMENT"),
        "source_families": ("promotion-race-rank4-1", "promotion-race-rank4-2", "promotion-race-rank4-3", "promotion-race-rank3-1", "promotion-race-rank3-2", "promotion-race-rank3-3"),
    },
    {
        "construction_family": "semantic_guard_auxiliary",
        "mechanic_family": "semantic_guard_aux_state",
        "builder": "semantic_fixture_mix",
        "parameters": (("cannon", 0), ("cannon", 1), ("nifu", 1), ("nifu", 6), ("en_passant", 0), ("en_passant", 1)),
        "splits": ("DEVELOPMENT", "HOLDOUT", "DEVELOPMENT", "DEVELOPMENT", "HOLDOUT", "DEVELOPMENT"),
        "source_families": ("semantic-cannon-0", "semantic-cannon-1", "semantic-nifu-1", "semantic-nifu-6", "semantic-en-passant-0", "semantic-en-passant-1"),
    },
    {
        "construction_family": "auxiliary_reply_chain_control",
        "mechanic_family": "auxiliary_state_chain",
        "builder": "f23g_reply_chain_control",
        "parameters": ((0, False), (1, False), (2, False), (3, False), (4, False), (0, True)),
        "splits": ("DEVELOPMENT", "DEVELOPMENT", "HOLDOUT", "DEVELOPMENT", "HOLDOUT", "DEVELOPMENT"),
        "source_families": ("f23g-control-sibling-demo", "f23g-control-1", "f23g-control-sibling-demo", "f23g-control-3", "f23g-control-4", "f23g-control-capture"),
        "solver_limits": {"max_nodes": 30000, "max_depth": 6},
    },
)


def _rows(n: int, pieces: dict[tuple[int, int], str]) -> list[str]:
    board = [["."] * n for _ in range(n)]
    for (file, rank), piece in pieces.items():
        if board[rank][file] != ".":
            raise ValueError(f"overlap at {(file, rank)}")
        board[rank][file] = piece
    return ["".join(board[rank]) for rank in range(n - 1, -1, -1)]


def _ruleset_for_legacy(m: dict[str, Any], n: int):
    return m["make_compiled"](n, [m["king"](), m["rook"](), m["T"]("D")], repetition_limit=2, max_ply=6)


def _build_candidate(m: dict[str, Any], plan: dict[str, Any], parameter: tuple[Any, ...]):
    builder = plan["builder"]
    if builder == "legacy_anchor_mate":
        n, victim = parameter
        compiled = _ruleset_for_legacy(m, n)
        rows = f23c._mate_rows(n, victim=victim)
        state = m["make_state"](compiled, rows)
    elif builder == "legacy_capture_recapture":
        n, variant = parameter
        compiled = _ruleset_for_legacy(m, n)
        state = m["make_state"](compiled, f23c._capture_recapture_rows(n, variant))
    elif builder == "legacy_drop_hand":
        n, variant, count = parameter
        compiled = _ruleset_for_legacy(m, n)
        state = m["make_state"](compiled, f23c._drop_rows(n, variant), hands=([('R', count)], []))
    elif builder == "auto_promotion_race":
        from generic_chess.core.movement import LeapAtom

        pawn = m["T"]("P", LeapAtom((0, 1)), is_promotable=True, targets=("G", "H"))
        gold = m["T"]("G", LeapAtom((1, 0)), LeapAtom((-1, 0)), LeapAtom((0, 1)), LeapAtom((0, -1)))
        horse = m["T"]("H", LeapAtom((1, 1)), LeapAtom((-1, 1)), LeapAtom((1, -1)), LeapAtom((-1, -1)))
        compiled = m["make_compiled"](6, [m["king"](), pawn, gold, horse], auto_promotion=True, repetition_limit=2, max_ply=6)
        file, rank = parameter
        pieces = {(0, 0): "K", (5, 5): "k", (file, rank): "P", (4, 4): "p"}
        state = m["make_state"](compiled, _rows(6, pieces))
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

            compiled = m["compile_semantic_ruleset"](en_passant_ruleset())
            file = 2 + variant
            pieces = {(0, 0): "K", (7, 7): "k", (file, 1): "P", (file + 1, 3): "p"}
            state = m["make_state"](compiled, _rows(8, pieces))
    elif builder == "f23g_reply_chain_control":
        variant, capture = parameter
        compiled, pieces = f23g._semantic_variant(m, variant, capture=capture)
        state = m["make_state"](compiled, f23g._rows(5, pieces))
    else:
        raise AssertionError(f"unknown frozen builder {builder}")
    return compiled, state


def _plan_digest() -> str:
    encoded = json.dumps(CANDIDATE_PLAN, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _candidate_record(m: dict[str, Any], plan: dict[str, Any], index: int, parameter: tuple[Any, ...]):
    compiled, state = _build_candidate(m, plan, parameter)
    limits = plan.get("solver_limits", SOLVER_LIMITS)
    result = solve_root(compiled, state, **limits)
    base = {
        "id": f"generic-f23j-{plan['builder']}-{index}",
        "construction_family": plan["construction_family"],
        "mechanic_family": plan["mechanic_family"],
        "builder": plan["builder"],
        "parameter": list(parameter),
        "planned_split": plan["splits"][index],
        "source_family_id": plan["source_families"][index],
        "solver": {"kind": "exact_root_wdl", "version": "f23j-exact-generic-preference-solver-v2", **limits},
        "source": f"fixture:f23j-{plan['builder']}",
        "state": f23c.f23b.state_spec(state, m),
        "root_action_count": len(result.action_values),
        "strong": result.strong,
        "root_value": result.root_value,
        "action_values": list(result.action_values),
        "solver_stats": result.stats,
        "unresolved_reason": result.unresolved_reason,
    }
    if not result.strong:
        return base
    optimal_depths = [item["proof_depth"] for item in result.action_values if item["value"] == result.root_value]
    values = sorted({item["value"] for item in result.action_values})
    fingerprint = decision_subtree_fingerprint(compiled, state, **limits)
    base.update({
        "ruleset_id": f"f23j-{plan['builder']}",
        "effective_orbit_id": hashlib.sha256(json.dumps({"ruleset_id": f"f23j-{plan['builder']}", "fingerprint": fingerprint}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20],
        "decision_subtree_fingerprint": fingerprint,
        "preference_authority": {
            "root_value": result.root_value,
            "optimal_root_actions": list(result.optimal_actions),
            "optimal_proof_depths": optimal_depths,
            "proof_depth_class": "MULTIPLY_DEPENDENT" if min(optimal_depths, default=0) >= 3 else ("REPLY_DEPENDENT" if min(optimal_depths, default=0) >= 2 else "IMMEDIATE"),
            "max_ply_dependence": max((item["proof_depth"] for item in result.action_values), default=0) >= limits["max_depth"],
            "root_action_wdl_partition": values,
        },
    })
    return base


def _deduplicate_and_split(records: list[dict[str, Any]]):
    solved = [record for record in records if record["strong"]]
    orbit_groups = defaultdict(list)
    for record in solved:
        orbit_groups[(record["ruleset_id"], record["construction_family"], record["decision_subtree_fingerprint"])].append(record)
    duplicate_ids = []
    representatives = []
    for key, group in sorted(orbit_groups.items()):
        group.sort(key=lambda record: record["id"])
        representatives.append(group[0])
        duplicate_ids.extend(record["id"] for record in group[1:])
    source_groups = defaultdict(list)
    for record in solved:
        source_groups[record["source_family_id"]].append(record)
    source_leakage = []
    for source_id, group in source_groups.items():
        splits = {record["planned_split"] for record in group}
        if len(splits) > 1:
            source_leakage.append(source_id)
    source_leakage = sorted(set(source_leakage))
    behavioral_groups = defaultdict(list)
    for record in representatives:
        behavioral_groups[record["decision_subtree_fingerprint"]].append(record)
    behavioral_leakage = []
    for group in behavioral_groups.values():
        if {record["planned_split"] for record in group} > {"DEVELOPMENT"}:
            behavioral_leakage.extend(record["effective_orbit_id"] for record in group)
    behavioral_leakage = sorted(set(behavioral_leakage))
    excluded = set(behavioral_leakage)
    fit = sorted(record["effective_orbit_id"] for record in representatives if record["planned_split"] == "DEVELOPMENT" and record["source_family_id"] not in source_leakage and record["effective_orbit_id"] not in excluded)
    holdout = sorted(record["effective_orbit_id"] for record in representatives if record["planned_split"] == "HOLDOUT" and record["source_family_id"] not in source_leakage and record["effective_orbit_id"] not in excluded)
    return representatives, {
        "fit_eligible_development_orbit_ids": fit,
        "validation_eligible_holdout_orbit_ids": holdout,
        "excluded_behavioral_leakage_orbit_ids": behavioral_leakage,
        "excluded_source_family_leakage_ids": source_leakage,
        "duplicate_candidate_ids": sorted(duplicate_ids),
    }


def build_corpus() -> dict[str, Any]:
    m = f23c._imports()
    records = []
    for plan in CANDIDATE_PLAN:
        for index, parameter in enumerate(plan["parameters"]):
            records.append(_candidate_record(m, plan, index, parameter))
    representatives, accounting = _deduplicate_and_split(records)
    solved = [record for record in records if record["strong"]]
    eligible = [record for record in representatives if record["effective_orbit_id"] in set(accounting["fit_eligible_development_orbit_ids"])]
    coverage = {
        "planned_candidate_count": len(records),
        "solved_candidate_count": len(solved),
        "unresolved_candidate_count": len(records) - len(solved),
        "physical_solved_count": len(solved),
        "canonical_solved_count": len(representatives),
        "effective_development_count": len(eligible),
        "effective_holdout_count": len(accounting["validation_eligible_holdout_orbit_ids"]),
        "construction_family_distribution": dict(sorted(Counter(record["construction_family"] for record in eligible).items())),
        "mechanic_family_distribution": dict(sorted(Counter(record["mechanic_family"] for record in eligible).items())),
        "source_family_distribution": dict(sorted(Counter(record["source_family_id"] for record in eligible).items())),
        "proof_depth_distribution": dict(sorted(Counter(record["preference_authority"]["proof_depth_class"] for record in eligible).items())),
        "wdl_partition_distribution": dict(sorted((repr(key), value) for key, value in Counter(tuple(record["preference_authority"]["root_action_wdl_partition"]) for record in eligible).items())),
        "max_ply_dependent_count": sum(record["preference_authority"]["max_ply_dependence"] for record in eligible),
        "construction_family_attempt_count": len(CANDIDATE_PLAN),
        "mechanic_family_attempt_count": len({plan["mechanic_family"] for plan in CANDIDATE_PLAN}),
    }
    return {
        "schema_version": 6,
        "corpus_id": "evaluator-v2-corpus-v6",
        "source_f23j_plan_sha256": _plan_digest(),
        "candidate_plan": json.loads(json.dumps(CANDIDATE_PLAN)),
        "solver_contract": {"authority": "exact GenericChess legal successors, transition, terminal, and history/repetition semantics", **SOLVER_LIMITS, "evaluator_blind": True, "cycles": "unresolved"},
        "generic_exact": representatives,
        "effective_orbits": accounting,
        "coverage": coverage,
        "historical_strata": {
            "v1_sha256": hashlib.sha256(V1.read_bytes()).hexdigest(),
            "v2_sha256": hashlib.sha256(V2.read_bytes()).hexdigest(),
            "v3_sha256": hashlib.sha256(V3.read_bytes()).hexdigest(),
            "v4_sha256": hashlib.sha256(V4.read_bytes()).hexdigest(),
            "v5_sha256": hashlib.sha256(V5.read_bytes()).hexdigest(),
            "f23f_spec_sha256": hashlib.sha256(F23F.read_bytes()).hexdigest(),
            "note": "Historical V1-V5 and F23F are preserved separately and never used as V6 fit data.",
        },
        "production_changed": False,
        "evaluator_inspection": False,
        "shogi_opened": False,
        "advancement_gate": {
            "passes": False,
            "requirements": {
                "development_effective_minimum": 20,
                "holdout_effective_minimum": 6,
                "construction_families_minimum": 4,
                "mechanic_families_minimum": 4,
                "source_family_leakage": 0,
                "behavioral_orbit_leakage": 0,
            },
            "reason": "exact solver rejected all existing multi-mechanic fixture candidates except two deduplicated auxiliary-chain control orbits",
        },
        "decision": {
            "selected_next_boundary": "F23K_EXACT_REFERENCE_SOLVER_FOUNDATION",
            "reason": "genuinely independent mechanics are not yet producing enough strong finite preference roots under the current exact reference contract",
        },
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corpus = build_corpus()
    args.output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "planned": corpus["coverage"]["planned_candidate_count"], "solved": corpus["coverage"]["solved_candidate_count"], "unresolved": corpus["coverage"]["unresolved_candidate_count"], "development": corpus["coverage"]["effective_development_count"], "holdout": corpus["coverage"]["effective_holdout_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
