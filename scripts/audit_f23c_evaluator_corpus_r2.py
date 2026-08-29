"""Audit F23C's V2 generic corpus with the F23A feature probe.

Only DEVELOPMENT is profiled.  HOLDOUT is checked structurally and never
enters feature summaries or boundary selection.
"""

from __future__ import annotations

import json
import math
import sys
from statistics import median
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_f23a_evaluator_v2_features as f23a
from scripts import build_f23b_evaluator_corpus as f23b
from scripts import build_f23c_evaluator_corpus_r2 as corpus_builder

FIXTURE = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v2.json"
FAMILIES = f23a.FAMILY_NAMES


def _action_from_dict(rows, data, builder_m):
    for action, child in rows:
        if builder_m["action_to_dict"](action) == data:
            return action, child
    raise RuntimeError("DIAGNOSTIC_REFERENCE_ACTION_NOT_LEGAL")


def _action_key_from_dict(item):
    if item["kind"] in ("board", "semantic_board"):
        return ("board", item["from"][0], item["from"][1], item["to"][0], item["to"][1], item.get("promotion_target_id"))
    return ("drop", item["base_type_id"], item["to"][0], item["to"][1])


def _case_map(builder_m):
    merged = f23b._imports()
    merged.update(builder_m)
    cases = f23b._generic_strata(merged) + corpus_builder._new_case_specs(merged)
    return {case["id"]: case for case in cases}


def _summary(values, rows, family):
    nonzero = [row for row, value in zip(rows, values) if value != 0]
    positive = sum(value > 0 for value in values)
    negative = sum(value < 0 for value in values)
    return {
        "development_positions": len(rows),
        "nonzero_reference_vs_v1_selected": len(nonzero),
        "observed_rulesets": sorted({row["ruleset_id"] for row in nonzero}),
        "reference_authority_classes": sorted({row["reference_authority_class"] for row in nonzero}),
        "direction": {"positive": positive, "zero": len(values) - positive - negative, "negative": negative},
        "normalized_abs_range": [min((abs(value) for value in values), default=0.0), max((abs(value) for value in values), default=0.0)],
        "median_position_local_seconds": median(row["reference_family_seconds"][family] for row in rows) if rows else 0.0,
    }


def audit_development() -> dict:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    builder_m = corpus_builder._imports()
    probe_m = f23a._imports()
    by_id = _case_map(builder_m)
    rows = []
    for entry in fixture["generic_exact"]:
        if entry["split"] != "DEVELOPMENT":
            continue
        case = by_id[entry["id"]]
        compiled, state = case["compiled"], case["state_object"]
        probe = f23a.Probe(compiled, probe_m)
        actor = state.position.side_to_move
        root_features, _root_cost, _root_detail = probe.feature_vector(state, actor)
        root_scores = []
        for action, child_position in probe._legal_pairs(state.position, actor):
            child = f23a._child_state(state, child_position, action, probe_m)
            _components, score = f23a.evaluator_components(probe, child, actor)
            root_scores.append((score, json.dumps(probe_m["action_to_dict"](action), sort_keys=True), action, child))
        root_scores.sort(key=lambda row: (-row[0], row[1]))
        if not root_scores:
            raise RuntimeError(f"{entry['id']} has no legal current child")
        _score, _label, current_action, current_state = root_scores[0]
        reference_action, reference_position = _action_from_dict(
            probe._legal_pairs(state.position, actor), entry["label"]["diagnostic_reference_action"], builder_m
        )
        reference_state = f23a._child_state(state, reference_position, reference_action, probe_m)
        reference_features, _ref_cost, ref_detail = probe.feature_vector(reference_state, actor)
        current_features, _current_cost, _current_detail = probe.feature_vector(current_state, actor)
        deltas = {
            name: {
                "reference_delta": reference_features[name] - root_features[name],
                "current_delta": current_features[name] - root_features[name],
                "reference_advantage_vs_current": reference_features[name] - current_features[name],
            }
            for name in FAMILIES
        }
        legal_scores = {f23b._action_key(action): index + 1 for index, (_value, _text, action, _child) in enumerate(root_scores)}
        ranks = [legal_scores.get(_action_key_from_dict(item)) for item in entry["label"].get("reference_actions", [])]
        rows.append({
            "id": entry["id"], "ruleset_id": entry["ruleset_id"],
            "reference_authority_class": entry.get("reference_authority_class", "preserved F22 authority"),
            "event_tags": entry.get("event_tags", []),
            "reference_child": probe_m["action_to_dict"](reference_action),
            "current_selected_child": probe_m["action_to_dict"](current_action),
            "reference_ranks": ranks, "outside_v1_top_3": any(rank is not None and rank > 3 for rank in ranks),
            "deltas": deltas, "reference_family_seconds": ref_detail["family_seconds"],
        })

    family_summary = {}
    for name in FAMILIES:
        family_summary[name] = _summary(
            [row["deltas"][name]["reference_advantage_vs_current"] for row in rows], rows, name
        )
    correlations = {}
    for index, left in enumerate(FAMILIES):
        for right in FAMILIES[index + 1:]:
            correlations[f"{left}:{right}"] = f23a._correlation(
                [row["deltas"][left]["reference_advantage_vs_current"] for row in rows],
                [row["deltas"][right]["reference_advantage_vs_current"] for row in rows],
            )
    cross_ruleset = [
        name for name, summary in family_summary.items()
        if summary["nonzero_reference_vs_v1_selected"] > 0 and len(summary["observed_rulesets"]) > 1
    ]
    coherent = [
        name for name in cross_ruleset
        if not (family_summary[name]["direction"]["positive"] and family_summary[name]["direction"]["negative"])
    ]
    attack_ok = "attack_defense_hanging" in cross_ruleset
    capture_ok = "capture_recapture_pressure" in cross_ruleset
    nonredundant = [
        name for name in cross_ruleset
        if all(abs(value) < 0.95 for key, value in correlations.items() if name in key.split(":"))
    ]
    prototype_gate = (
        len(cross_ruleset) >= 5 and attack_ok and capture_ok and len(nonredundant) >= 2
        and len(coherent) >= 2
    )
    authority_counts = {}
    solver_counts = {}
    for entry in fixture["generic_exact"]:
        authority_counts[entry.get("reference_authority_class", "preserved F22 authority")] = authority_counts.get(entry.get("reference_authority_class", "preserved F22 authority"), 0) + 1
        solver_counts[entry["solver"]["kind"]] = solver_counts.get(entry["solver"]["kind"], 0) + 1
    return {
        "status": "PASS", "audit": "F23A_PROBE_OVER_F23C_DEVELOPMENT",
        "fixture": str(FIXTURE.relative_to(ROOT)).replace("\\", "/"),
        "source_v1_sha256_matches": fixture["source_v1_sha256"] == __import__("hashlib").sha256((ROOT / fixture["source_v1_fixture"]).read_bytes()).hexdigest(),
        "frozen_f22_reproduced": fixture["frozen_legacy_f22"] == f23b.recover_f22_stratum(),
        "development_cases": len(rows), "holdout_excluded": fixture["split"]["holdout_count"],
        "rows": rows, "family_summary": family_summary, "correlations": correlations,
        "exact_solver_statistics": {"reference_authority_classes": authority_counts, "solver_kinds": solver_counts, "all_development_references_present": all(bool(row["reference_ranks"]) or row["id"].startswith("generic-semantic-file-guard") for row in rows)},
        "quality_gate": {
            "cross_ruleset_meaningful_families": cross_ruleset,
            "cross_ruleset_meaningful_family_count": len(cross_ruleset),
            "attack_defense_meaningful": attack_ok, "capture_recapture_meaningful": capture_ok,
            "coherent_signal_families": coherent, "nonredundant_signal_families": nonredundant,
            "prototype_gate_passed": prototype_gate,
        },
        "selected_next_boundary": "F23D_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE" if prototype_gate else "F23D_EVALUATOR_CORPUS_EXPANSION_R3",
        "production_changed": False,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_development()
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "development": report["development_cases"], "holdout": report["holdout_excluded"], "cross_ruleset": report["quality_gate"]["cross_ruleset_meaningful_families"], "selected": report["selected_next_boundary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
