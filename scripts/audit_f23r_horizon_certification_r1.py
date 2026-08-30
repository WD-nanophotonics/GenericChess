"""Corrective F23R audit with evidence precedence and proof provenance."""

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
FIRST_PASS = TESTS / "fixtures" / "f23r_v10_horizon_certification.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from scripts import audit_f23q_v9_gate_and_horizon as f23q_audit
from scripts import build_f23q_preference_corpus_r8 as f23q_builder
from scripts import exact_generic_horizon_abstraction_v2 as abstraction


LADDER = (("SMALL", {"max_nodes": 2000}), ("MEDIUM", {"max_nodes": 20000}), ("LARGE", {"max_nodes": 100000}))
ATTEMPT_WALL_SECONDS = 8
SEMANTIC_CAUSES = {abstraction.MAX_PLY_ABSTRACT_LEAF}
COMPUTATIONAL_CAUSES = {
    abstraction.ABSTRACT_NODE_CAP,
    abstraction.ABSTRACT_TIME_CAP,
    abstraction.ABSTRACT_CYCLE_REFUSAL,
    abstraction.ABSTRACT_WORKER_FAILURE,
    abstraction.ABSTRACT_NO_SUCCESSORS,
    abstraction.OTHER_ABSTRACT_UNRESOLVED,
}


def _worker(out, compiled, state, limits):
    result = abstraction.solve_root_horizon_abstract_v2(compiled, state, **limits)
    out.put({
        "strong": result.strong,
        "root_value": result.root_value,
        "optimal_actions": list(result.optimal_actions),
        "action_values": list(result.action_values),
        "stats": result.stats,
        "unresolved_reason": result.unresolved_reason,
        "root_unresolved_causes": sorted(result.root_unresolved_causes),
        "max_proof_ply": result.max_proof_ply,
    })


def _attempt(compiled, state, limits):
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_worker, args=(out, compiled, state, limits))
    process.start()
    process.join(ATTEMPT_WALL_SECONDS)
    if process.is_alive():
        process.terminate()
        process.join()
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "stats": {}, "unresolved_reason": abstraction.ABSTRACT_TIME_CAP, "root_unresolved_causes": [abstraction.ABSTRACT_TIME_CAP], "max_proof_ply": 0}
    try:
        return out.get(timeout=1)
    except queue.Empty:
        return {"strong": False, "root_value": None, "optimal_actions": [], "action_values": [], "stats": {}, "unresolved_reason": abstraction.ABSTRACT_WORKER_FAILURE, "root_unresolved_causes": [abstraction.ABSTRACT_WORKER_FAILURE], "max_proof_ply": 0}


def _reconstruct(row):
    if row["version"] == "R8":
        family = {"construction_family": row["construction_family"], "builder": row["builder"], "mechanic_family": row["mechanic_family"]}
        return f23q_builder.build_candidate(row["plan_candidate"], family, row["builder"])
    return f23q_audit._reconstruct(row)


def _solve_ladder(compiled, state):
    attempts = []
    for tier, limits in LADDER:
        result = _attempt(compiled, state, limits)
        attempts.append({"tier": tier, "limits": limits, "result": result})
        if result["strong"]:
            return tier, result, attempts
    return None, None, attempts


def _signature(action_values, optimal_actions):
    return (tuple((row["action"], row["value"]) for row in action_values), tuple(optimal_actions))


def _exact_evidence(entry):
    if not entry:
        return None
    attempts = entry.get("attempts", [])
    for attempt in attempts:
        result = attempt.get("result", {})
        if result.get("strong"):
            return {
                "first_resolving_tier": entry.get("first_resolving_tier") or attempt.get("tier"),
                "root_value": result.get("root_value"),
                "root_action_values": result.get("action_values", []),
                "optimal_actions": result.get("optimal_actions", []),
            }
    return None


def _secondary_evidence(row):
    horizon = row.get("horizon_recertification", {})
    proofs = horizon.get("proofs") or horizon.get("proof") or {}
    exact = {name: _exact_evidence(proofs.get(name)) for name in ("base", "plus_2", "plus_4")}
    base = {"root_value": row.get("root_value"), "root_action_values": row.get("root_action_values", []), "optimal_actions": row.get("optimal_actions", [])}
    if exact["base"] is None and row.get("first_resolving_tier"):
        exact["base"] = {"first_resolving_tier": row["first_resolving_tier"], "root_value": row.get("root_value"), "root_action_values": row.get("root_action_values", []), "optimal_actions": row.get("optimal_actions", [])}
    alternates = []
    for name in ("plus_2", "plus_4"):
        candidate = exact[name]
        if candidate is not None and _signature(candidate["root_action_values"], candidate["optimal_actions"]) != _signature(base["root_action_values"], base["optimal_actions"]):
            base_actions = {json.dumps(item["action"], sort_keys=True): item["value"] for item in base["root_action_values"]}
            alt_actions = {json.dumps(item["action"], sort_keys=True): item["value"] for item in candidate["root_action_values"]}
            changed = sorted(set(base_actions) | set(alt_actions))
            alternates.append({
                "horizon": name,
                "first_resolving_tier": candidate["first_resolving_tier"],
                "changed_actions": [json.loads(key) for key in changed if base_actions.get(key) != alt_actions.get(key)],
                "base_action_values": base["root_action_values"],
                "alternate_action_values": candidate["root_action_values"],
                "base_optimal_actions": base["optimal_actions"],
                "alternate_optimal_actions": candidate["optimal_actions"],
            })
    return {
        "accepted_class": row.get("horizon_dependence", "HORIZON_SENSITIVITY_UNKNOWN"),
        "base": base,
        "exact_resolving_tiers": {name: data["first_resolving_tier"] for name, data in exact.items() if data is not None},
        "alternate_differences": alternates,
    }


def _same_base(result, row):
    return _signature(result.get("action_values", []), result.get("optimal_actions", [])) == _signature(row.get("root_action_values", []), row.get("optimal_actions", []))


def _best_partial_result(attempts):
    candidates = [attempt["result"] for attempt in attempts if attempt["result"].get("action_values")]
    return max(candidates, key=lambda item: len(item.get("action_values", [])), default=attempts[-1]["result"])


def _unknown_kind(causes):
    causes = set(causes)
    semantic = bool(causes & SEMANTIC_CAUSES)
    computational = bool(causes & COMPUTATIONAL_CAUSES)
    if semantic and computational:
        return "MIXED_SEMANTIC_AND_COMPUTATIONAL_UNRESOLVED"
    if semantic:
        return "SEMANTICALLY_HORIZON_UNRESOLVED"
    if computational:
        return "COMPUTATIONALLY_UNRESOLVED"
    return "RECONSTRUCTION_UNRESOLVED"


def certify(row):
    compiled, state = _reconstruct(row)
    tier, result, attempts = _solve_ladder(compiled, state)
    secondary = _secondary_evidence(row)
    partial = result or _best_partial_result(attempts)
    action_values = partial.get("action_values", [])
    for item in action_values:
        base_item = next((base for base in row.get("root_action_values", []) if base["action"] == item["action"]), None)
        item["base_wdl"] = base_item["value"] if base_item else None
    abstract_exact = result is not None and result["strong"]
    base_contradiction = abstract_exact and not _same_base(result, row)
    material_contradiction = abstract_exact and secondary["accepted_class"] == "MATERIALLY_MAX_PLY_DEPENDENT"
    if base_contradiction:
        classification = "ABSTRACT_BASE_CONTRADICTION"
    elif material_contradiction:
        classification = "ABSTRACT_MATERIAL_EVIDENCE_CONTRADICTION"
    elif abstract_exact:
        classification = "MAX_PLY_ABSTRACT_CERTIFIED"
    elif secondary["accepted_class"] == "HORIZON_STABLE_EXACT":
        classification = "HORIZON_STABLE_EXACT"
    elif secondary["accepted_class"] == "MATERIALLY_MAX_PLY_DEPENDENT":
        classification = "MATERIALLY_MAX_PLY_DEPENDENT"
    else:
        classification = "HORIZON_SENSITIVITY_UNKNOWN"
    causes = frozenset(partial.get("root_unresolved_causes", []))
    return {
        "classification": classification,
        "secondary_f23q": secondary,
        "abstraction": {
            "fully_exact": abstract_exact,
            "first_resolving_tier": tier,
            "attempts": attempts,
            "action_values": action_values,
            "root_unresolved_causes": sorted(causes),
            "unknown_kind": _unknown_kind(causes) if classification == "HORIZON_SENSITIVITY_UNKNOWN" else None,
        },
        "abstract_base_contradiction": base_contradiction,
        "abstract_material_evidence_contradiction": material_contradiction,
    }


def audit(path: Path = V10) -> dict:
    corpus = json.loads(path.read_text(encoding="utf-8"))
    rows = corpus["effective_preference_representatives"]
    first_pass = json.loads(FIRST_PASS.read_text(encoding="utf-8"))
    certifications = {row["id"]: certify(row) for row in rows}
    development = [row for row in rows if row["planned_split"] == "DEVELOPMENT"]
    holdout = [row for row in rows if row["planned_split"] == "HOLDOUT"]
    classes = Counter(item["classification"] for item in certifications.values())
    quality = classes["MAX_PLY_ABSTRACT_CERTIFIED"] + classes["HORIZON_STABLE_EXACT"]
    contradictions = sum(item["abstract_base_contradiction"] or item["abstract_material_evidence_contradiction"] for item in certifications.values())
    family_matrix = {}
    for family in sorted({row["construction_family"] for row in rows}):
        family_matrix[family] = {}
        for split in ("DEVELOPMENT", "HOLDOUT"):
            family_matrix[family][split] = dict(sorted(Counter(certifications[row["id"]]["classification"] for row in rows if row["construction_family"] == family and row["planned_split"] == split).items()))
    unknown_kinds = Counter(item["abstraction"]["unknown_kind"] for item in certifications.values() if item["classification"] == "HORIZON_SENSITIVITY_UNKNOWN")
    gate_items = {
        "abstract_base_contradictions": not any(item["abstract_base_contradiction"] for item in certifications.values()),
        "abstract_material_evidence_contradictions": not any(item["abstract_material_evidence_contradiction"] for item in certifications.values()),
        "development_horizon_quality_minimum": quality >= 16,
        "frozen_effective_set": len(rows) == 42,
        "development": len(development) == 32,
        "holdout": len(holdout) == 10,
    }
    if not all(gate_items.values()):
        if contradictions:
            boundary = "F23S_HORIZON_REFERENCE_CERTIFICATION_FOUNDATION_R2"
        elif unknown_kinds["SEMANTICALLY_HORIZON_UNRESOLVED"] + unknown_kinds["MIXED_SEMANTIC_AND_COMPUTATIONAL_UNRESOLVED"] >= unknown_kinds["COMPUTATIONALLY_UNRESOLVED"]:
            boundary = "F23S_NATURAL_TERMINAL_REFERENCE_CORPUS_R9"
        else:
            boundary = "F23S_HORIZON_REFERENCE_CERTIFICATION_FOUNDATION_R2"
    else:
        boundary = "F23S_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE_R4"
    return {
        "schema_version": 2,
        "source_v10_fixture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "first_pass_f23r_fixture_sha256": hashlib.sha256(FIRST_PASS.read_bytes()).hexdigest(),
        "source_effective_count": len(rows),
        "certifications": certifications,
        "family_matrix": family_matrix,
        "summary": {
            "development": len(development), "holdout": len(holdout),
            "max_ply_abstract_certified": classes["MAX_PLY_ABSTRACT_CERTIFIED"],
            "horizon_stable_exact": classes["HORIZON_STABLE_EXACT"],
            "materially_dependent": classes["MATERIALLY_MAX_PLY_DEPENDENT"],
            "horizon_unknown": classes["HORIZON_SENSITIVITY_UNKNOWN"],
            "abstract_base_contradictions": classes["ABSTRACT_BASE_CONTRADICTION"],
            "abstract_material_evidence_contradictions": classes["ABSTRACT_MATERIAL_EVIDENCE_CONTRADICTION"],
            "development_horizon_quality": quality,
            "unknown_kinds": dict(sorted(unknown_kinds.items())),
            "f23q_secondary_counts": dict(sorted(Counter(row["horizon_dependence"] for row in rows).items())),
        },
        "gate": {"passes": all(gate_items.values()), "items": gate_items},
        "selected_next_boundary": boundary,
        "production_changed": False,
        "v10_rewritten": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=V10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.input)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", **result["summary"], "gate": result["gate"]["passes"], "selected": result["selected_next_boundary"]}, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
