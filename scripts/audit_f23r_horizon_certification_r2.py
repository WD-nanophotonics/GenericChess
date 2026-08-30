"""Deterministic F23R R2 reconciliation of the saved R1 ladder evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
V10 = TESTS / "fixtures" / "evaluator_v2_corpus_v10.json"
R1 = TESTS / "fixtures" / "f23r_v10_horizon_certification_r1.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import exact_generic_horizon_abstraction_v2 as abstraction


TIERS = {"SMALL": 0, "MEDIUM": 1, "LARGE": 2}
SEMANTIC = {abstraction.MAX_PLY_ABSTRACT_LEAF}
COMPUTATIONAL = {
    abstraction.ABSTRACT_NODE_CAP,
    abstraction.ABSTRACT_TIME_CAP,
    abstraction.ABSTRACT_CYCLE_REFUSAL,
    abstraction.ABSTRACT_NO_SUCCESSORS,
    abstraction.ABSTRACT_WORKER_FAILURE,
    abstraction.OTHER_ABSTRACT_UNRESOLVED,
}


def _action_key(action):
    return json.dumps(action, sort_keys=True, separators=(",", ":"))


def _proof(row, threshold):
    return row.get(threshold, {"status": abstraction.UNRESOLVED, "necessary_unresolved_causes": [abstraction.OTHER_ABSTRACT_UNRESOLVED]})


def _external(attempt):
    result = attempt.get("result", {})
    if result.get("action_values"):
        return None
    causes = result.get("root_unresolved_causes") or []
    if not causes:
        reason = result.get("unresolved_reason")
        causes = [reason] if reason else [abstraction.OTHER_ABSTRACT_UNRESOLVED]
    return {"tier": attempt["tier"], "causes": sorted(set(causes))}


def reconcile_threshold(attempts, action, threshold):
    """Reconcile one action threshold without treating row count as strength."""
    key = _action_key(action)
    completed = []
    exact = []
    semantic = []
    unresolved = []
    later_external_refusals = []
    for attempt in attempts:
        result = attempt.get("result", {})
        row = next((item for item in result.get("action_values", []) if _action_key(item["action"]) == key), None)
        if row is None:
            refusal = _external(attempt)
            if refusal is not None:
                later_external_refusals.append(refusal)
            continue
        completed.append(attempt["tier"])
        proof = _proof(row, threshold)
        causes = frozenset(proof.get("necessary_unresolved_causes", []))
        if proof.get("status") in {abstraction.PROVED_TRUE, abstraction.PROVED_FALSE}:
            exact.append((TIERS[attempt["tier"]], attempt["tier"], proof["status"]))
        elif causes and causes <= SEMANTIC:
            semantic.append((TIERS[attempt["tier"]], attempt["tier"], causes))
        else:
            unresolved.append((TIERS[attempt["tier"]], attempt["tier"], causes or frozenset({abstraction.OTHER_ABSTRACT_UNRESOLVED})))
    exact_status = None
    if exact:
        _, tier, status = max(exact)
        exact_status = status
    semantic_tier = max(semantic, default=(None, None, frozenset()))
    highest = max(completed, key=lambda tier: TIERS[tier], default=None)
    if exact_status is not None:
        reconciled = "EXACT"
        necessary_semantic = set()
        necessary_computational = set()
    elif semantic:
        reconciled = "SEMANTIC_ONLY_UNRESOLVED"
        necessary_semantic = set(semantic_tier[2])
        necessary_computational = set()
    else:
        causes = set().union(*(item[2] for item in unresolved))
        causes.update(cause for refusal in later_external_refusals for cause in refusal["causes"])
        necessary_semantic = causes & SEMANTIC
        necessary_computational = causes & COMPUTATIONAL
        reconciled = "MIXED_SEMANTIC_AND_COMPUTATIONAL_UNRESOLVED" if necessary_semantic and necessary_computational else "SEMANTIC_ONLY_UNRESOLVED" if necessary_semantic else "COMPUTATIONAL_ONLY_UNRESOLVED" if necessary_computational else "RECONSTRUCTION_OR_PROVENANCE_FAILURE"
    return {
        "exact_status": exact_status,
        "highest_completed_tier": highest,
        "semantic_complete_tier": semantic_tier[1],
        "necessary_semantic_causes": sorted(necessary_semantic),
        "necessary_computational_causes": sorted(necessary_computational),
        "later_external_refusals": later_external_refusals,
        "reconciled_status": reconciled,
    }


def _action_reconciliation(certification, base_row):
    attempts = certification["abstraction"]["attempts"]
    actions = { _action_key(row["action"]): row["action"] for row in base_row.get("root_action_values", []) }
    for attempt in attempts:
        for row in attempt.get("result", {}).get("action_values", []):
            actions.setdefault(_action_key(row["action"]), row["action"])
    rows = []
    for key in sorted(actions):
        action = actions[key]
        ge_win = reconcile_threshold(attempts, action, "ge_win")
        ge_draw = reconcile_threshold(attempts, action, "ge_draw")
        if ge_win["exact_status"] == abstraction.PROVED_TRUE:
            value = "WIN"
        elif ge_draw["exact_status"] == abstraction.PROVED_FALSE:
            value = "LOSS"
        elif ge_win["exact_status"] == abstraction.PROVED_FALSE and ge_draw["exact_status"] == abstraction.PROVED_TRUE:
            value = "DRAW"
        else:
            value = None
        semantic = set(ge_win["necessary_semantic_causes"]) | set(ge_draw["necessary_semantic_causes"])
        computational = set(ge_win["necessary_computational_causes"]) | set(ge_draw["necessary_computational_causes"])
        if semantic and computational:
            kind = "MIXED_SEMANTIC_AND_COMPUTATIONAL_UNRESOLVED"
        elif semantic:
            kind = "SEMANTICALLY_HORIZON_UNRESOLVED"
        elif computational:
            kind = "COMPUTATIONALLY_UNRESOLVED"
        else:
            kind = None
        base = next((item for item in base_row.get("root_action_values", []) if item["action"] == action), None)
        rows.append({"action": action, "base_wdl": base.get("value") if base else None, "abstract_wdl": value, "ge_win": ge_win, "ge_draw": ge_draw, "necessary_semantic_causes": sorted(semantic), "necessary_computational_causes": sorted(computational), "unknown_kind": kind, "max_ply_dependency": bool(semantic)})
    return rows


def _signature(rows, optimal):
    return (tuple(sorted((_action_key(row["action"]), row.get("abstract_wdl", row.get("value"))) for row in rows)), tuple(sorted(_action_key(action) for action in optimal)))


def reconcile_root(root_id, r1_cert, v10_row):
    actions = _action_reconciliation(r1_cert, v10_row)
    strong = all(row["abstract_wdl"] is not None for row in actions)
    abstract_optimal = []
    if strong:
        rank = {"LOSS": -1, "DRAW": 0, "WIN": 1}
        root_value = max((row["abstract_wdl"] for row in actions), key=rank.get)
        abstract_optimal = [row["action"] for row in actions if row["abstract_wdl"] == root_value]
    else:
        root_value = None
    same_base = strong and _signature(actions, abstract_optimal) == _signature(v10_row.get("root_action_values", []), v10_row.get("optimal_actions", []))
    secondary = r1_cert["secondary_f23q"]["accepted_class"]
    base_contradiction = strong and not same_base
    material_contradiction = strong and secondary == "MATERIALLY_MAX_PLY_DEPENDENT"
    if base_contradiction:
        final_class = "ABSTRACT_BASE_CONTRADICTION"
    elif material_contradiction:
        final_class = "ABSTRACT_MATERIAL_EVIDENCE_CONTRADICTION"
    elif strong:
        final_class = "MAX_PLY_ABSTRACT_CERTIFIED"
    elif secondary == "HORIZON_STABLE_EXACT":
        final_class = "HORIZON_STABLE_EXACT"
    elif secondary == "MATERIALLY_MAX_PLY_DEPENDENT":
        final_class = "MATERIALLY_MAX_PLY_DEPENDENT"
    else:
        final_class = "HORIZON_SENSITIVITY_UNKNOWN"
    unknown_actions = [row for row in actions if row["abstract_wdl"] is None]
    kinds = Counter(row["unknown_kind"] for row in unknown_actions if row["unknown_kind"])
    root_semantic = any(kind == "SEMANTICALLY_HORIZON_UNRESOLVED" for kind in kinds)
    root_computational = any(kind == "COMPUTATIONALLY_UNRESOLVED" for kind in kinds)
    root_mixed = any(kind == "MIXED_SEMANTIC_AND_COMPUTATIONAL_UNRESOLVED" for kind in kinds)
    root_unknown_kind = "MIXED_SEMANTIC_AND_COMPUTATIONAL_UNRESOLVED" if root_mixed or (root_semantic and root_computational) else "SEMANTICALLY_HORIZON_UNRESOLVED" if root_semantic else "COMPUTATIONALLY_UNRESOLVED" if root_computational else "RECONSTRUCTION_OR_PROVENANCE_FAILURE" if unknown_actions else None
    return {
        "classification": final_class,
        "development": v10_row["planned_split"] == "DEVELOPMENT",
        "material_evidence_class": secondary,
        "abstract": {"strong": strong, "root_value": root_value, "optimal_actions": abstract_optimal, "action_reconciliation": actions, "unknown_kinds": dict(sorted(kinds.items())), "root_unknown_kind": root_unknown_kind},
        "abstract_base_contradiction": base_contradiction,
        "abstract_material_evidence_contradiction": material_contradiction,
        "secondary_f23q": r1_cert["secondary_f23q"],
    }


def audit() -> dict:
    v10 = json.loads(V10.read_text(encoding="utf-8"))
    r1 = json.loads(R1.read_text(encoding="utf-8"))
    v10_rows = {row["id"]: row for row in v10["effective_preference_representatives"]}
    certifications = {root_id: reconcile_root(root_id, cert, v10_rows[root_id]) for root_id, cert in r1["certifications"].items()}
    development = [item for item in certifications.values() if item["development"]]
    holdout = [item for item in certifications.values() if not item["development"]]
    classes = Counter(item["classification"] for item in certifications.values())
    by_split = {name: dict(sorted(Counter(item["classification"] for item in subset).items())) for name, subset in (("DEVELOPMENT", development), ("HOLDOUT", holdout))}
    unknown_by_split = {name: dict(sorted(Counter(item["abstract"]["root_unknown_kind"] for item in subset if item["classification"] == "HORIZON_SENSITIVITY_UNKNOWN").items())) for name, subset in (("DEVELOPMENT", development), ("HOLDOUT", holdout))}
    family_matrix = {}
    for root_id, item in certifications.items():
        family = v10_rows[root_id]["construction_family"]
        split = v10_rows[root_id]["planned_split"]
        family_matrix.setdefault(family, {}).setdefault(split, Counter())[item["classification"]] += 1
    family_matrix = {family: {split: dict(sorted(counts.items())) for split, counts in sorted(splits.items())} for family, splits in sorted(family_matrix.items())}
    frozen_items = {key: value for key, value in v10["advancement_gate"]["items"].items() if key != "non_max_ply_minimum"}
    contradictions = any(item["abstract_base_contradiction"] or item["abstract_material_evidence_contradiction"] for item in certifications.values())
    dev_quality = sum(item["classification"] in {"MAX_PLY_ABSTRACT_CERTIFIED", "HORIZON_STABLE_EXACT"} for item in development)
    gate_items = {"frozen_non_horizon_gates": all(frozen_items.values()), "abstract_base_contradictions": not any(item["abstract_base_contradiction"] for item in certifications.values()), "abstract_material_evidence_contradictions": not any(item["abstract_material_evidence_contradiction"] for item in certifications.values()), "development_horizon_quality_minimum": dev_quality >= 16, "effective_count": len(certifications) == 42, "development": len(development) == 32, "holdout": len(holdout) == 10}
    semantic_dev = unknown_by_split["DEVELOPMENT"].get("SEMANTICALLY_HORIZON_UNRESOLVED", 0) + unknown_by_split["DEVELOPMENT"].get("MIXED_SEMANTIC_AND_COMPUTATIONAL_UNRESOLVED", 0)
    computational_dev = unknown_by_split["DEVELOPMENT"].get("COMPUTATIONALLY_UNRESOLVED", 0) + unknown_by_split["DEVELOPMENT"].get("MIXED_SEMANTIC_AND_COMPUTATIONAL_UNRESOLVED", 0)
    boundary = "F23S_HORIZON_REFERENCE_CERTIFICATION_FOUNDATION_R2" if contradictions else "F23S_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE_R4" if all(gate_items.values()) else "F23S_NATURAL_TERMINAL_REFERENCE_CORPUS_R9" if semantic_dev >= computational_dev else "F23S_HORIZON_REFERENCE_CERTIFICATION_FOUNDATION_R2"
    unknown_total = Counter(item["abstract"]["root_unknown_kind"] for item in certifications.values() if item["classification"] == "HORIZON_SENSITIVITY_UNKNOWN")
    return {"schema_version": 3, "source_v10_fixture_sha256": hashlib.sha256(V10.read_bytes()).hexdigest(), "source_r1_fixture_sha256": hashlib.sha256(R1.read_bytes()).hexdigest(), "source_effective_count": len(certifications), "certifications": certifications, "final_class_by_split": by_split, "unknown_provenance_by_split": unknown_by_split, "family_matrix": family_matrix, "frozen_non_horizon_gate_items": frozen_items, "summary": {"max_ply_abstract_certified": classes["MAX_PLY_ABSTRACT_CERTIFIED"], "horizon_stable_exact": classes["HORIZON_STABLE_EXACT"], "materially_dependent": classes["MATERIALLY_MAX_PLY_DEPENDENT"], "horizon_unknown": classes["HORIZON_SENSITIVITY_UNKNOWN"], "abstract_base_contradictions": classes["ABSTRACT_BASE_CONTRADICTION"], "abstract_material_evidence_contradictions": classes["ABSTRACT_MATERIAL_EVIDENCE_CONTRADICTION"], "development_horizon_quality": dev_quality, "development_material": sum(item["classification"] == "MATERIALLY_MAX_PLY_DEPENDENT" for item in development), "holdout_material": sum(item["classification"] == "MATERIALLY_MAX_PLY_DEPENDENT" for item in holdout), "unknown_provenance_total": dict(sorted(unknown_total.items()))}, "gate": {"passes": all(gate_items.values()), "items": gate_items}, "selected_next_boundary": boundary, "production_changed": False, "v10_rewritten": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", **result["summary"], "final_class_by_split": result["final_class_by_split"], "unknown_provenance_by_split": result["unknown_provenance_by_split"], "gate": result["gate"]["passes"], "selected": result["selected_next_boundary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
