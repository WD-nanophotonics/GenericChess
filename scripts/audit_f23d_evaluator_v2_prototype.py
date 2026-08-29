"""F23D audit-only evaluator-v2 prototype decision.

This module deliberately refuses to fit a correction when the corpus lacks
PREFERENCE_STRONG DEVELOPMENT supervision.  Exact legal-action sets remain
structural evidence and never turn their diagnostic child into a target.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_f23c_evaluator_corpus_r2 as f23c_audit

V1 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json"
V2 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v2.json"

PREFERENCE_STRONG = "PREFERENCE_STRONG"
PREFERENCE_WEAK = "PREFERENCE_WEAK"
STRUCTURAL_ONLY = "STRUCTURAL_ONLY"


def classify_entry(entry: dict) -> str:
    if entry["split"] not in ("DEVELOPMENT", "HOLDOUT"):
        raise ValueError("unknown corpus split")
    # A one-ply mate proves that the action wins immediately, but does not
    # completely order all other nonterminal root actions.
    if entry["label_kind"] == "terminal_mate_in_one":
        return PREFERENCE_WEAK
    return STRUCTURAL_ONLY


def supervision_partition(fixture: dict) -> dict:
    rows = []
    for entry in fixture["generic_exact"]:
        rows.append({
            "id": entry["id"],
            "split": entry["split"],
            "ruleset_id": entry["ruleset_id"],
            "authority": entry.get("reference_authority_class", "preserved F22 authority"),
            "class": classify_entry(entry),
        })
    counts = Counter(row["class"] for row in rows)
    development = [row for row in rows if row["split"] == "DEVELOPMENT"]
    return {
        "counts_all": dict(sorted(counts.items())),
        "development_counts": dict(sorted(Counter(row["class"] for row in development).items())),
        "rows": rows,
        "development_rulesets_by_class": {
            cls: sorted({row["ruleset_id"] for row in development if row["class"] == cls})
            for cls in (PREFERENCE_STRONG, PREFERENCE_WEAK, STRUCTURAL_ONLY)
        },
    }


def _feature_selection(audit: dict) -> dict:
    # This is a deterministic audit ranking, not a fitted coefficient search.
    # It is retained to document what would be eligible if preference labels
    # were added in a later corpus phase.
    summaries = audit["family_summary"]
    correlations = audit["correlations"]
    eligible = [
        name for name in f23c_audit.FAMILIES
        if summaries[name]["nonzero_reference_vs_v1_selected"] > 0
        and len(summaries[name]["observed_rulesets"]) > 1
        and name != "promotion_structure"
    ]
    eligible.sort(key=lambda name: (-summaries[name]["nonzero_reference_vs_v1_selected"], name))
    selected = []
    for name in eligible:
        if all(abs(correlations.get(f"{min(name, other)}:{max(name, other)}", 0.0)) < 0.95 for other in selected):
            selected.append(name)
        if len(selected) == 4:
            break
    return {
        "eligible_by_development_signal": eligible,
        "selected_for_future_prototype_only": selected,
        "excluded": {
            name: (
                "not observed across multiple rulesets"
                if name not in eligible else "not in deterministic top-four nonredundant audit set"
            )
            for name in f23c_audit.FAMILIES if name not in selected
        },
        "selection_is_not_fitting": True,
    }


def _baseline_metrics(audit: dict, partition: dict) -> dict:
    classes = {row["id"]: row["class"] for row in partition["rows"]}
    development = [row for row in audit["rows"] if classes[row["id"]] in (PREFERENCE_STRONG, PREFERENCE_WEAK)]
    weak = [row for row in development if classes[row["id"]] == PREFERENCE_WEAK]
    ranks = [min(rank for rank in row["reference_ranks"] if rank is not None) for row in weak if any(rank is not None for rank in row["reference_ranks"])]
    by_ruleset = {}
    for row in weak:
        valid = [rank for rank in row["reference_ranks"] if rank is not None]
        by_ruleset.setdefault(row["ruleset_id"], []).append(min(valid) if valid else None)
    return {
        "preference_roots_available": len(development),
        "weak_roots": len(weak),
        "strong_roots": sum(classes[row["id"]] == PREFERENCE_STRONG for row in development),
        "v1_exact_reference_top1_hit": sum(rank == 1 for rank in ranks),
        "v1_exact_reference_best_rank_mean": mean(ranks) if ranks else None,
        "v1_exact_reference_best_rank_median": median(ranks) if ranks else None,
        "by_ruleset": by_ruleset,
        "prototype": "not_evaluated_no_preference_strong_supervision",
    }


def audit() -> dict:
    v1_bytes = V1.read_bytes()
    v2_bytes = V2.read_bytes()
    v1 = json.loads(v1_bytes)
    v2 = json.loads(v2_bytes)
    partition = supervision_partition(v2)
    # F23C audit is DEVELOPMENT-only; it structurally excludes HOLDOUT and is
    # the sole source of the feature-selection audit below.
    development_audit = f23c_audit.audit_development()
    feature_selection = _feature_selection(development_audit)
    strong = partition["development_counts"].get(PREFERENCE_STRONG, 0)
    candidate_produced = strong > 0
    return {
        "status": "PASS",
        "phase": "F23D_AUDIT_ONLY_PROTOTYPE_DECISION",
        "v1_sha256": hashlib.sha256(v1_bytes).hexdigest(),
        "v2_sha256": hashlib.sha256(v2_bytes).hexdigest(),
        "frozen_v1_v2_inputs": True,
        "supervision_partition": partition,
        "feature_selection": feature_selection,
        "candidate_produced": candidate_produced,
        "candidate_spec_sha256": None,
        "candidate_spec": None,
        "development_metrics": _baseline_metrics(development_audit, partition),
        "holdout": {
            "opened": False,
            "reason": "No PREFERENCE_STRONG DEVELOPMENT roots; do not manufacture labels or claim prototype validation",
            "structural_case_count": sum(row["split"] == "HOLDOUT" for row in partition["rows"]),
        },
        "shogi_transfer": {"opened": False, "reason": "No frozen candidate was produced"},
        "runtime_cost": {
            "measured_on": "F23C DEVELOPMENT generic probe only",
            "candidate_incremental_cost": None,
            "reason": "No prototype correction was instantiated",
        },
        "decision": {
            "reason": "DEVELOPMENT has zero PREFERENCE_STRONG roots; weak mate-in-one and structural labels cannot justify fitting or arbitrary ordering",
            "selected_next_boundary": "F23E_REFERENCE_PREFERENCE_CORPUS",
        },
        "production_changed": False,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit()
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "strong": report["development_metrics"]["strong_roots"],
        "weak": report["development_metrics"]["weak_roots"],
        "structural": report["supervision_partition"]["development_counts"].get(STRUCTURAL_ONLY, 0),
        "candidate_produced": report["candidate_produced"],
        "selected": report["decision"]["selected_next_boundary"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
