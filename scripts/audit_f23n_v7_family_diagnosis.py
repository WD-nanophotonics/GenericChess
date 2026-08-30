"""Produce a deterministic, result-only diagnosis of the frozen V7 corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V7 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v7.json"
FAILURE_CLASSES = {
    "ALL_EQUAL_NO_PREFERENCE",
    "EXACT_SOLVER_UNRESOLVED",
    "SOURCE_SPLIT_TOO_THIN",
    "BEHAVIORAL_DUPLICATION",
    "INSUFFICIENT_PLANNED_DIVERSITY",
}


def _counter(rows, key, default="UNSET"):
    return dict(sorted(Counter((row.get(key) if row.get(key) is not None else default) for row in rows).items()))


def diagnose(path: Path = V7) -> dict:
    raw = path.read_bytes()
    corpus = json.loads(raw.decode("utf-8"))
    records = corpus["records"]
    effective = corpus["effective_preference_representatives"]
    duplicates = set(corpus["duplicate_candidate_ids"])
    by_family = {}
    for family in sorted({row["construction_family"] for row in records}):
        planned = [row for row in records if row["construction_family"] == family]
        solved = [row for row in planned if row.get("strong")]
        preference = [row for row in planned if row["status"] == "PREFERENCE_STRONG"]
        all_equal = [row for row in planned if row["status"] == "SOLVED_ALL_EQUAL"]
        unresolved = [row for row in planned if row["status"] == "UNRESOLVED"]
        family_effective = [row for row in effective if row["construction_family"] == family]
        witness_count = sum(row.get("mechanic_witness") is not None for row in preference)
        split_counts = Counter(row["planned_split"] for row in family_effective)
        failures = set()
        if all_equal:
            failures.add("ALL_EQUAL_NO_PREFERENCE")
        if unresolved:
            failures.add("EXACT_SOLVER_UNRESOLVED")
        if len(family_effective) < 2 or min(split_counts.values(), default=0) == 0:
            failures.add("SOURCE_SPLIT_TOO_THIN")
        if any(row["id"] in duplicates for row in planned):
            failures.add("BEHAVIORAL_DUPLICATION")
        if len(preference) < 2 or not solved:
            failures.add("INSUFFICIENT_PLANNED_DIVERSITY")
        assert failures <= FAILURE_CLASSES
        by_family[family] = {
            "planned_count": len(planned),
            "exact_solved_count": len(solved),
            "preference_bearing_count": len(preference),
            "all_equal_count": len(all_equal),
            "unresolved_count": len(unresolved),
            "effective_orbit_count": len(family_effective),
            "development_count": split_counts.get("DEVELOPMENT", 0),
            "holdout_count": split_counts.get("HOLDOUT", 0),
            "proof_depth_classes": _counter(family_effective, "proof_depth_class", "ALL_EQUAL"),
            "wdl_partition_signatures": dict(sorted(Counter("/".join(row["wdl_partition"]) for row in family_effective).items())),
            "first_resolving_solver_tier": _counter(planned, "first_resolving_tier", "UNRESOLVED"),
            "unresolved_reasons": _counter(
                [row for row in unresolved],
                "blocker",
                "NONE",
            ),
            "mechanic_witness_coverage": {"with_witness": witness_count, "preference_bearing": len(preference)},
            "failure_classes": sorted(failures),
        }
    return {
        "schema_version": 1,
        "source_fixture": path.name,
        "source_fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "source_corpus_id": corpus["corpus_id"],
        "diagnosis": by_family,
        "selection_guidance": {
            "primary_problem": "family-native preference-bearing diversity in all-equal and unresolved families",
            "allowed_use": "choose R6 construction families only; do not infer family unsuitability from one V7 state grid",
            "forbidden_inputs_consulted": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=V7)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = diagnose(args.input)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
