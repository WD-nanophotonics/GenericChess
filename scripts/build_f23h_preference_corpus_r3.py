"""Build V5 from a frozen pool of genuinely different deep decision trees."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from scripts import build_f23b_evaluator_corpus as f23b
from scripts import build_f23g_preference_corpus_r2 as f23g
from scripts import audit_f23g_decision_orbits as f23g_audit
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts.exact_generic_preference_solver import decision_subtree_fingerprint, solve_root

V4 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v4.json"
SOLVER_VERSION = "f23h-exact-generic-preference-solver-v3"
PAIRS = (
    ((1, 3), (2, 2)),
    ((0, 3), (1, 4)),
    ((0, 3), (2, 0)),
    ((2, 3), (0, 3)),
    ((2, 3), (0, 4)),
    ((2, 3), (2, 0)),
)


def _identity(ruleset_id: str, state: dict, label_kind: str) -> str:
    payload = {"ruleset_id": ruleset_id, "state": state, "label_kind": label_kind}
    canonical_json = f23c._imports()["canonical_json"]
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _planned_pool(m: dict) -> list[dict]:
    pool = []
    for variant in range(5):
        for sample, (a_square, b_square) in enumerate(PAIRS):
            capture = variant >= 3
            compiled, base = f23g._semantic_variant(m, variant, capture=capture)
            pieces = dict(base)
            del pieces[(1, 3)]
            del pieces[(2, 2)]
            if a_square in pieces or b_square in pieces or a_square == b_square:
                pool.append({"status": "SKIP", "reason": "overlap", "variant": variant, "sample": sample})
                continue
            pieces[a_square] = "A"
            pieces[b_square] = "b"
            rows = f23g._rows(5, pieces)
            state = m["make_state"](compiled, rows)
            pool.append({
                "status": "PLANNED", "variant": variant, "sample": sample,
                "capture": capture, "compiled": compiled, "state_object": state,
                "state": f23b.state_spec(state, m),
                "ruleset_id": f"f23h-{ 'capture' if capture else 'aux' }-geometry-{variant}",
                "mechanic_family": "capture_bad_branch" if capture else "auxiliary_reply_chain",
            })
    return pool


def _solve_pool(m: dict) -> tuple[list[dict], list[dict]]:
    solved, unresolved = [], []
    for index, case in enumerate(_planned_pool(m)):
        if case["status"] != "PLANNED":
            unresolved.append({"pool_index": index, "status": case["status"], "reason": case["reason"]})
            continue
        result = solve_root(case["compiled"], case["state_object"], max_nodes=30000, max_depth=6)
        if not result.strong or any(item["value"] is None for item in result.action_values):
            unresolved.append({"pool_index": index, "status": "UNRESOLVED", "reason": result.unresolved_reason, "stats": result.stats})
            continue
        optimal_depths = [item["proof_depth"] for item in result.action_values if item["value"] == result.root_value]
        if not optimal_depths or min(optimal_depths) < 2 or result.max_proof_ply >= 6:
            unresolved.append({"pool_index": index, "status": "REJECTED", "reason": "immediate_or_max_ply", "max_proof_ply": result.max_proof_ply})
            continue
        case = dict(case)
        case["result"] = result
        case["pool_index"] = index
        case["decision_subtree_fingerprint"] = decision_subtree_fingerprint(case["compiled"], case["state_object"], max_nodes=30000, max_depth=6)
        solved.append(case)
    return solved, unresolved


def _entry(case: dict, orbit_id: str, multiplicity: int) -> dict:
    result = case["result"]
    state = case["state"]
    optimal_depths = [item["proof_depth"] for item in result.action_values if item["value"] == result.root_value]
    proof_class = "MULTIPLY_DEPENDENT" if min(optimal_depths) >= 3 else "REPLY_DEPENDENT"
    identity = _identity(case["ruleset_id"], state, "exact_game_theoretic_optimal_set_deep_v5")
    return {
        "id": f"generic-f23h-{case['variant']}-{case['sample']}",
        "ruleset_id": case["ruleset_id"],
        "family": "exact_game_theoretic_preference_deep_v5",
        "mechanic_family": case["mechanic_family"],
        "label_kind": "exact_game_theoretic_optimal_set_deep_v5",
        "reference_authority": "complete bounded exact GenericChess game-theoretic solver",
        "reference_authority_class": "exact terminal minimax with behavior-only decision fingerprint",
        "source": "fixture:f23h-frozen-real-position-pool",
        "solver": {"kind": "exact_root_wdl", "version": SOLVER_VERSION, "max_nodes": 30000, "max_depth": 6},
        "state": state,
        "state_identity_sha256": identity,
        "decision_subtree_fingerprint": case["decision_subtree_fingerprint"],
        "effective_orbit_id": orbit_id,
        "physical_multiplicity": multiplicity,
        "split": "HOLDOUT" if int(identity[:8], 16) % 4 == 0 else "DEVELOPMENT",
        "supervision_class": "PREFERENCE_STRONG",
        "preference_authority": {
            "root_actor": state["side_to_move"], "root_value": result.root_value,
            "legal_root_action_count": len(result.action_values),
            "optimal_root_actions": list(result.optimal_actions),
            "all_root_action_values": list(result.action_values),
            "optimal_proof_depths": optimal_depths,
            "proof_depth_class": proof_class,
            "max_ply_dependence": result.max_proof_ply >= 6,
            "minimum_distinguishing_ply": min(optimal_depths),
            "terminal_mechanism": "ordinary_terminal_adjudication",
            "states_expanded": result.stats["states_expanded"], "terminal_leaves": result.stats["terminal_leaves"],
            "transposition_hits": result.stats["transposition_hits"], "repetition_adjudications": result.stats["repetition_adjudications"],
            "cycle_edges": result.stats["cycle_edges"], "cap_hits": result.stats["cap_hits"],
            "unresolved": result.stats["unresolved"], "solver_version": SOLVER_VERSION,
        },
        "label": {"reference_actions": list(result.optimal_actions), "diagnostic_reference_action": result.optimal_actions[0]},
    }


def _effective_entries(solved: list[dict]) -> tuple[list[dict], dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for case in solved:
        groups[(case["ruleset_id"], case["decision_subtree_fingerprint"])].append(case)
    split_by_orbit = {}
    for key, cases in groups.items():
        identities = [_identity(c["ruleset_id"], c["state"], "exact_game_theoretic_optimal_set_deep_v5") for c in cases]
        splits = {"HOLDOUT" if int(identity[:8], 16) % 4 == 0 else "DEVELOPMENT" for identity in identities}
        split_by_orbit[key] = splits
    leakage = {key for key, splits in split_by_orbit.items() if len(splits) > 1}
    representatives = []
    orbit_ids = {}
    for key, cases in sorted(groups.items(), key=lambda item: min(c["pool_index"] for c in item[1])):
        orbit_id = hashlib.sha256(f"{key[0]}:{key[1]}".encode()).hexdigest()
        orbit_ids[key] = orbit_id
        representatives.append(_entry(cases[0], orbit_id, len(cases)))
    return representatives, {
        "duplicate_multiplicity_per_orbit": {orbit_ids[key]: len(cases) for key, cases in groups.items()},
        "excluded_cross_split_orbit_ids": sorted(orbit_ids[key] for key in leakage),
        "leakage_count": len(leakage),
    }


def build_corpus() -> dict:
    v4_bytes = V4.read_bytes()
    v4 = json.loads(v4_bytes)
    m = f23c._imports()
    historical_v4_audit = f23g_audit.audit()
    solved, unresolved = _solve_pool(m)
    representatives, orbit_meta = _effective_entries(solved)
    historical_v4_fingerprints = {key.split(":", 1)[1] for key in historical_v4_audit["decision_orbit_ids"]}
    historical_duplicate_ids = sorted({entry["effective_orbit_id"] for entry in representatives if entry["mechanic_family"] == "auxiliary_reply_chain" and entry["decision_subtree_fingerprint"] in historical_v4_fingerprints})
    excluded_ids = set(orbit_meta["excluded_cross_split_orbit_ids"]) | set(historical_duplicate_ids)
    new_entries = [entry for entry in representatives if entry["effective_orbit_id"] not in excluded_ids]
    generic = copy.deepcopy(v4["generic_exact"]) + representatives
    eligible_dev = [e for e in new_entries if e["split"] == "DEVELOPMENT"]
    eligible_holdout = [e for e in new_entries if e["split"] == "HOLDOUT"]
    by_ruleset = Counter(e["ruleset_id"] for e in eligible_dev)
    wdl_diverse = sum(len({row["value"] for row in e["preference_authority"]["all_root_action_values"]}) > 1 for e in eligible_dev)
    multi = sum(e["preference_authority"]["proof_depth_class"] == "MULTIPLY_DEPENDENT" for e in eligible_dev)
    non_max = sum(not e["preference_authority"]["max_ply_dependence"] for e in eligible_dev)
    mechanics = {e["mechanic_family"] for e in eligible_dev}
    gate = len(eligible_dev) >= 16 and len(eligible_holdout) >= 4 and len(by_ruleset) >= 4 and max(by_ruleset.values(), default=0) <= len(eligible_dev) * .35 and multi >= 8 and wdl_diverse * 2 >= len(eligible_dev) and non_max * 2 >= len(eligible_dev) and len(mechanics) >= 2 and not orbit_meta["leakage_count"]
    if not gate:
        raise RuntimeError("F23H_EFFECTIVE_DEEP_GATE_FAILED")
    effective_ids = {e["effective_orbit_id"] for e in new_entries}
    return {
        "schema_version": 5, "corpus_id": "evaluator-v2-corpus-v5",
        "source_v4_fixture": str(V4.relative_to(ROOT)).replace("\\", "/"),
        "source_v4_sha256": hashlib.sha256(v4_bytes).hexdigest(),
        "frozen_legacy_f22": copy.deepcopy(v4["frozen_legacy_f22"]),
        "generic_exact": generic,
        "supervision_classes": {e["id"]: e.get("supervision_class", "STRUCTURAL_ONLY") for e in generic},
        "sampling": {"feature_blind": True, "algorithm": "frozen 30-position pool: five movement geometries x six real A/B placements, with two capture-mechanic groups; solve complete pool before split summary", "candidate_pool_size": 30, "solved_candidate_count": len(solved), "unresolved_candidate_count": len(unresolved), "unresolved_candidates": unresolved, "forbidden_diversity_evidence": ["inert hands", "dead inventory", "renamed types", "irrelevant remote blockers"], "deduplication": "behavior-only decision_subtree_fingerprint within ruleset/mechanic identity"},
        "split": {"algorithm": v4["split"]["algorithm"], "frozen_before_fitting": True, "development_count": sum(e["split"] == "DEVELOPMENT" for e in generic), "holdout_count": sum(e["split"] == "HOLDOUT" for e in generic)},
        "effective_orbits": {"physical_planned_candidates": 30, "solved_candidates": len(solved), "canonical_state_identities": len({e["state_identity_sha256"] for e in representatives}), "effective_decision_orbits": len(representatives), "fit_eligible_development_orbit_ids": sorted(e["effective_orbit_id"] for e in eligible_dev), "validation_eligible_holdout_orbit_ids": sorted(e["effective_orbit_id"] for e in eligible_holdout), "excluded_cross_split_orbit_ids": orbit_meta["excluded_cross_split_orbit_ids"], "historical_v4_duplicate_orbit_ids": historical_duplicate_ids, "excluded_noneligible_orbit_ids": sorted(excluded_ids), **orbit_meta},
        "coverage": {"historical_v4_rows": len(v4["generic_exact"]), "new_effective_rows": len(representatives), "fit_eligible_development": len(eligible_dev), "validation_eligible_holdout": len(eligible_holdout), "ruleset_distribution": dict(by_ruleset), "mechanic_distribution": dict(Counter(e["mechanic_family"] for e in eligible_dev)), "multiply_development": multi, "reply_dependent_development": sum(e["preference_authority"]["proof_depth_class"] == "REPLY_DEPENDENT" for e in eligible_dev), "wdl_partition_diverse_development": wdl_diverse, "non_max_ply_development": non_max, "max_ply_dependent": sum(e["preference_authority"]["max_ply_dependence"] for e in representatives)},
        "corrected_deep_supervision_gate": {"passes": gate, "effective_orbit_unit": True},
        "production_changed": False, "alpha_sho_changed": False,
        "selected_f23i_boundary": "F23I_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE_R3",
    }


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    corpus = build_corpus(); args.output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "planned": corpus["sampling"]["candidate_pool_size"], "solved": corpus["sampling"]["solved_candidate_count"], "effective": corpus["effective_orbits"]["effective_decision_orbits"], "dev": corpus["effective_orbits"]["fit_eligible_development_orbit_ids"].__len__(), "holdout": corpus["effective_orbits"]["validation_eligible_holdout_orbit_ids"].__len__()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
