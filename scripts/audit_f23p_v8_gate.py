"""Deterministic gate diagnosis for the frozen V8 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V8 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v8.json"


def diagnose(path: Path = V8) -> dict:
    raw = path.read_bytes()
    corpus = json.loads(raw.decode("utf-8"))
    effective = corpus["effective_preference_representatives"]
    dev = [row for row in effective if row["planned_split"] == "DEVELOPMENT"]
    holdout = [row for row in effective if row["planned_split"] == "HOLDOUT"]
    capture = sum(row["construction_family"] == "capture_recapture_tactics" for row in dev)
    required_non_capture = max(0, (capture * 100 + 34) // 35 - len(dev))
    observed = []
    for fingerprint in corpus["excluded_behavioral_leakage_orbit_ids"]:
        observed.append({"orbit_id": fingerprint, "roots": sorted(row["id"] for row in corpus["retained_v7_preference_representatives"] + corpus["records"] if row.get("decision_certificate_fingerprint") == fingerprint)})
    eligible_by_orbit = {}
    for row in effective:
        eligible_by_orbit.setdefault(row["decision_certificate_fingerprint"], set()).add(row["planned_split"])
    residual_behavior = sorted(fingerprint for fingerprint, splits in eligible_by_orbit.items() if splits == {"DEVELOPMENT", "HOLDOUT"})
    eligible_by_lineage = {}
    for row in effective:
        eligible_by_lineage.setdefault(row["source_lineage_id"], set()).add(row["planned_split"])
    residual_source = sorted(lineage for lineage, splits in eligible_by_lineage.items() if splits == {"DEVELOPMENT", "HOLDOUT"})
    return {
        "schema_version": 1,
        "source_fixture": path.name,
        "source_fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "eligible_development": len(dev),
        "eligible_holdout": len(holdout),
        "development_by_construction_family": dict(sorted(Counter(row["construction_family"] for row in dev).items())),
        "development_by_mechanic_family": dict(sorted(Counter(row["mechanic_family"] for row in dev).items())),
        "development_by_source_lineage": dict(sorted(Counter(row["source_lineage_id"] for row in dev).items())),
        "development_by_wdl_partition": dict(sorted(Counter("/".join(row["wdl_partition"]) for row in dev).items())),
        "development_by_proof_depth": dict(sorted(Counter(row["proof_depth_class"] for row in dev).items())),
        "development_by_horizon_dependence": dict(sorted(Counter(row["max_ply_dependence"] for row in dev).items())),
        "capture_development_count": capture,
        "capture_development_percentage": round(capture * 100 / len(dev), 6) if dev else 0,
        "additional_non_capture_development_required_for_35_percent": required_non_capture,
        "holdout_deficit_to_six": max(0, 6 - len(holdout)),
        "observed_cross_split_behavioral_collision_ids": observed,
        "residual_eligible_behavioral_leakage_ids": residual_behavior,
        "residual_eligible_source_lineage_leakage_ids": residual_source,
        "forbidden_inputs_consulted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=V8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    encoded = json.dumps(diagnose(args.input), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
