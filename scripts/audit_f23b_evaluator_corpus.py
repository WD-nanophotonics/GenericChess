"""Run the F23A feature probe over F23B DEVELOPMENT cases only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_f23a_evaluator_v2_features as f23a
from scripts import build_f23b_evaluator_corpus as corpus_builder


FIXTURE = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json"
FAMILIES = f23a.FAMILY_NAMES


def _action_from_dict(rows, data, builder_m):
    for action, child in rows:
        if builder_m["action_to_dict"](action) == data:
            return action, child
    raise RuntimeError("DIAGNOSTIC_REFERENCE_ACTION_NOT_LEGAL")


def audit_development() -> dict:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    builder_m = corpus_builder._imports()
    probe_m = f23a._imports()
    cases = corpus_builder._generic_strata(builder_m)
    by_id = {case["id"]: case for case in cases}
    probe_rows = []
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
            probe._legal_pairs(state.position, actor),
            entry["label"]["diagnostic_reference_action"],
            builder_m,
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
        legal_scores = {
            corpus_builder._action_key(action): index + 1
            for index, (_value, _text, action, _child) in enumerate(root_scores)
        }
        reference_ranks = [
            legal_scores.get(tuple(
                ("board", item["from"][0], item["from"][1], item["to"][0], item["to"][1], item.get("promotion_target_id"))
                if item["kind"] == "board" else
                ("drop", item["base_type_id"], item["to"][0], item["to"][1])
            ))
            for item in entry["label"].get("reference_actions", [])
        ]
        probe_rows.append({
            "id": entry["id"],
            "ruleset_id": entry["ruleset_id"],
            "reference_child": probe_m["action_to_dict"](reference_action),
            "current_selected_child": probe_m["action_to_dict"](current_action),
            "reference_ranks": reference_ranks,
            "deltas": deltas,
            "reference_family_seconds": ref_detail["family_seconds"],
        })

    family_summary = {}
    for name in FAMILIES:
        advantages = [row["deltas"][name]["reference_advantage_vs_current"] for row in probe_rows]
        nonzero = [row for row, value in zip(probe_rows, advantages) if value != 0]
        family_summary[name] = {
            "development_positions": len(probe_rows),
            "nonzero_reference_vs_current": len(nonzero),
            "observed_rulesets": sorted({row["ruleset_id"] for row in nonzero}),
            "direction": {
                "positive": sum(value > 0 for value in advantages),
                "zero": sum(value == 0 for value in advantages),
                "negative": sum(value < 0 for value in advantages),
            },
            "normalized_abs_range": [min((abs(value) for value in advantages), default=0.0), max((abs(value) for value in advantages), default=0.0)],
            "median_position_local_seconds": median(row["reference_family_seconds"][name] for row in probe_rows) if probe_rows else 0.0,
        }
    correlations = {}
    for index, left in enumerate(FAMILIES):
        for right in FAMILIES[index + 1:]:
            correlations[f"{left}:{right}"] = f23a._correlation(
                [row["deltas"][left]["reference_advantage_vs_current"] for row in probe_rows],
                [row["deltas"][right]["reference_advantage_vs_current"] for row in probe_rows],
            )
    cross_ruleset_families = [
        name
        for name, summary in family_summary.items()
        if summary["nonzero_reference_vs_current"] > 0
        and len(summary["observed_rulesets"]) > 1
    ]
    selected_boundary = (
        "F23C_RULE_DERIVED_EVALUATOR_V2_PROTOTYPE"
        if len(cross_ruleset_families) >= 5
        else "F23C_EVALUATOR_CORPUS_EXPANSION_R2"
    )
    return {
        "status": "PASS",
        "audit": "F23A_PROBE_OVER_F23B_DEVELOPMENT",
        "fixture": str(FIXTURE.relative_to(ROOT)).replace("\\", "/"),
        "frozen_f22_reproduced": fixture["frozen_legacy_f22"] == corpus_builder.recover_f22_stratum(),
        "development_cases": len(probe_rows),
        "holdout_excluded": fixture["split"]["holdout_count"],
        "rows": probe_rows,
        "family_summary": family_summary,
        "correlations": correlations,
        "reference_rank_summary": {
            "cases_with_exact_reference_ranks": sum(bool(row["reference_ranks"]) for row in probe_rows),
            "all_ranks_present": all(all(rank is not None for rank in row["reference_ranks"]) for row in probe_rows),
        },
        "quality_gate": {
            "cross_ruleset_meaningful_families": cross_ruleset_families,
            "cross_ruleset_meaningful_family_count": len(cross_ruleset_families),
            "prototype_gate_passed": len(cross_ruleset_families) >= 5,
        },
        "selected_next_boundary": selected_boundary,
        "production_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_development()
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "development": report["development_cases"], "frozen_f22_reproduced": report["frozen_f22_reproduced"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
