"""Re-certify frozen V10 roots with MAX_PLY abstracted as unknown."""

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
V10 = TESTS / "fixtures" / "evaluator_v2_corpus_v10.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from scripts import audit_f23q_v9_gate_and_horizon as f23q_audit
from scripts import build_f23q_preference_corpus_r8 as f23q_builder
from scripts import exact_generic_horizon_abstraction as abstraction

LADDER = (("SMALL", {"max_nodes": 2000}), ("MEDIUM", {"max_nodes": 20000}), ("LARGE", {"max_nodes": 100000}))
ATTEMPT_WALL_SECONDS = 8


def _worker(out, compiled, state, limits):
    result = abstraction.solve_root_horizon_abstract(compiled, state, **limits)
    out.put({"strong": result.strong, "root_value": result.root_value, "optimal_actions": list(result.optimal_actions), "action_values": list(result.action_values), "stats": result.stats, "unresolved_reason": result.unresolved_reason, "max_proof_ply": result.max_proof_ply})


def _attempt(compiled, state, limits):
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_worker, args=(out, compiled, state, limits))
    process.start()
    process.join(ATTEMPT_WALL_SECONDS)
    if process.is_alive():
        process.terminate(); process.join()
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "stats": {"unresolved": {"ABSTRACT_TIME_CAP": 1}}, "unresolved_reason": "ABSTRACT_TIME_CAP", "max_proof_ply": 0}
    try:
        return out.get(timeout=1)
    except queue.Empty:
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "stats": {"unresolved": {"ABSTRACT_WORKER_FAILURE": 1}}, "unresolved_reason": "ABSTRACT_WORKER_FAILURE", "max_proof_ply": 0}


def _solve_ladder(compiled, state):
    attempts = []
    for tier, limits in LADDER:
        result = _attempt(compiled, state, limits)
        attempts.append({"tier": tier, "limits": limits, "result": result})
        if result["strong"]:
            return tier, result, attempts
    return None, None, attempts


def _reconstruct(row):
    """Reconstruct V10 without changing the frozen F23Q audit module."""
    if row["version"] == "R8":
        family = {
            "construction_family": row["construction_family"],
            "builder": row["builder"],
            "mechanic_family": row["mechanic_family"],
        }
        return f23q_builder.build_candidate(row["plan_candidate"], family, row["builder"])
    return f23q_audit._reconstruct(row)


def _same_certificate(actual, expected):
    return (tuple((row["action"], row["value"]) for row in actual["action_values"]) == tuple((row["action"], row["value"]) for row in expected["root_action_values"]) and tuple(actual["optimal_actions"]) == tuple(expected["optimal_actions"]))


def certify(row):
    compiled, state = _reconstruct(row)
    tier, result, attempts = _solve_ladder(compiled, state)
    base = {"root_action_values": row.get("root_action_values", []), "optimal_actions": row.get("optimal_actions", [])}
    if result is None:
        unresolved = Counter()
        max_leaves = 0
        for attempt in attempts:
            unresolved.update(attempt["result"].get("stats", {}).get("unresolved", {}))
            max_leaves += attempt["result"].get("stats", {}).get("max_ply_abstract_leaves", 0)
        semantic = max_leaves > 0 or unresolved.get("UNRESOLVED_MAX_PLY", 0) > 0
        return {"classification": "HORIZON_SENSITIVITY_UNKNOWN", "first_resolving_tier": None, "attempts": attempts, "unknown_reason": "SEMANTICALLY_HORIZON_UNRESOLVED" if semantic else "COMPUTATIONALLY_UNRESOLVED", "abstract_base_contradiction": False}
    if not _same_certificate(result, base):
        classification = "ABSTRACT_BASE_CONTRADICTION"
        contradiction = True
    elif row.get("horizon_dependence") == "MATERIALLY_MAX_PLY_DEPENDENT":
        classification = "ABSTRACT_BASE_CONTRADICTION"
        contradiction = True
    else:
        classification = "MAX_PLY_ABSTRACT_CERTIFIED"
        contradiction = False
    return {"classification": classification, "first_resolving_tier": tier, "attempts": attempts, "unknown_reason": None, "abstract_base_contradiction": contradiction}


def audit(path: Path = V10) -> dict:
    corpus = json.loads(path.read_text(encoding="utf-8"))
    rows = corpus["effective_preference_representatives"]
    certifications = {row["id"]: certify(row) for row in rows}
    development = [row for row in rows if row["planned_split"] == "DEVELOPMENT"]
    holdout = [row for row in rows if row["planned_split"] == "HOLDOUT"]
    certified_dev = sum(certifications[row["id"]]["classification"] in {"MAX_PLY_ABSTRACT_CERTIFIED", "HORIZON_STABLE_EXACT"} for row in development)
    mismatches = sum(item["abstract_base_contradiction"] for item in certifications.values())
    classification_by_family = {}
    for family in sorted({row["construction_family"] for row in rows}):
        subset = [row for row in rows if row["construction_family"] == family]
        classification_by_family[family] = dict(sorted(Counter(certifications[row["id"]]["classification"] for row in subset).items()))
    gate = {"abstraction_soundness": mismatches == 0, "abstract_base_contradictions": mismatches == 0, "development_horizon_quality_minimum": certified_dev >= 16, "frozen_effective_set": len(rows) == 42, "development": len(development) == 32, "holdout": len(holdout) == 10}
    semantic_unknown = sum(item["unknown_reason"] == "SEMANTICALLY_HORIZON_UNRESOLVED" for item in certifications.values())
    computational_unknown = sum(item["unknown_reason"] == "COMPUTATIONALLY_UNRESOLVED" for item in certifications.values())
    return {"schema_version": 1, "source_v10_fixture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "source_effective_count": len(rows), "certifications": certifications, "classification_by_family": classification_by_family, "summary": {"development": len(development), "holdout": len(holdout), "development_horizon_quality": certified_dev, "max_ply_abstract_certified": sum(item["classification"] == "MAX_PLY_ABSTRACT_CERTIFIED" for item in certifications.values()), "horizon_stable_exact": sum(item["classification"] == "HORIZON_STABLE_EXACT" for item in certifications.values()), "materially_dependent": sum(item["classification"] == "MATERIALLY_MAX_PLY_DEPENDENT" for item in certifications.values()), "unknown": sum(item["classification"] == "HORIZON_SENSITIVITY_UNKNOWN" for item in certifications.values()), "semantic_unknown": semantic_unknown, "computational_unknown": computational_unknown, "abstract_base_contradictions": mismatches}, "gate": {"passes": all(gate.values()), "items": gate}, "selected_next_boundary": "F23S_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE_R4" if all(gate.values()) else "F23S_NATURAL_TERMINAL_REFERENCE_CORPUS_R9" if semantic_unknown >= computational_unknown else "F23S_HORIZON_REFERENCE_CERTIFICATION_FOUNDATION_R2", "production_changed": False, "v10_rewritten": False}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--input", type=Path, default=V10); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    result = audit(args.input)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", **result["summary"], "gate": result["gate"]["passes"], "selected": result["selected_next_boundary"]}, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
