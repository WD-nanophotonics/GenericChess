"""Verify the zone/promotion-source disjointness artifact from scratch.

Recomputes the partition independently (ruleset regeneration, no corpus replay)
and compares it with the stored JSON field by field. It also fails if the
artifact has acquired a contact count or contact rate, because the withdrawn
0-vs-53 contrast would then be re-entering as evidence about search behaviour.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import scan_zone_promotion_disjointness as scan  # noqa: E402

FORBIDDEN_SUBSTRINGS = ("contact_rate", "contacts", "in_zone_hit", "not_in_zone_hit")


def walk_keys(node, path=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk_keys(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_keys(value, f"{path}[{index}]")
    else:
        yield path


def main() -> int:
    payload = scan.OUT.read_text(encoding="utf-8")
    import json

    stored = json.loads(payload)
    opportunity = scan.per_seed_opportunity()
    recomputed = {}
    for seed in sorted(opportunity):
        row = scan.geometry(seed)
        row["in_zone_paid_observations"] = opportunity[seed]
        row["can_contribute_an_in_zone_contact"] = not row[
            "zone_disjoint_from_every_promotion_source"
        ]
        recomputed[seed] = row

    mismatches = []
    stored_rows = {row["seed"]: row for row in stored["per_seed"]}
    if set(stored_rows) != set(recomputed):
        mismatches.append(f"seed set differs: {sorted(set(stored_rows) ^ set(recomputed))}")
    for seed, row in recomputed.items():
        if seed in stored_rows and stored_rows[seed] != row:
            mismatches.append(f"seed {seed} row differs")

    disjoint_all = sorted(
        row["seed"]
        for row in recomputed.values()
        if row["zone_disjoint_from_every_promotion_source"]
    )
    if disjoint_all != sorted(stored["seeds_whose_zone_is_disjoint_from_every_promotion_source"]):
        mismatches.append("disjoint seed list differs")
    if stored["disjoint_seed_count"] != len(disjoint_all):
        mismatches.append("disjoint seed count differs")
    disjoint_opportunity = sorted(
        row["seed"]
        for row in recomputed.values()
        if row["in_zone_paid_observations"] > 0
        and row["zone_disjoint_from_every_promotion_source"]
    )
    if disjoint_opportunity != sorted(stored["opportunity_seeds_whose_zone_is_disjoint"]):
        mismatches.append("opportunity disjoint seed list differs")
    if stored["opportunity_disjoint_seed_count"] != len(disjoint_opportunity):
        mismatches.append("opportunity disjoint seed count differs")
    opportunity_count = sum(1 for row in recomputed.values() if row["in_zone_paid_observations"] > 0)
    if stored["seeds_with_an_in_zone_paid_observation"] != opportunity_count:
        mismatches.append("opportunity seed count differs")
    source_sha = scan.sha256(scan.STAGE8)
    if stored["source_sha256"] != source_sha:
        mismatches.append("recorded source sha does not match the published Stage 8 file")
    if not (HERE / stored["plan"]).exists():
        mismatches.append("recorded plan file is missing")

    offending = [
        path
        for path in walk_keys(stored)
        if any(token in path for token in FORBIDDEN_SUBSTRINGS)
        and not path.endswith("can_contribute_an_in_zone_contact")
    ]
    if offending:
        mismatches.append(f"withdrawn contact statistics present: {offending[:5]}")

    if mismatches:
        for item in mismatches:
            print(f"MISMATCH {item}")
        print("zone_disjointness_artifact_not_verified")
        return 1
    print(f"seeds_examined={stored['seeds_examined']}")
    print(f"disjoint_seed_count={stored['disjoint_seed_count']}")
    print(
        "opportunity_disjoint_seed_count="
        f"{stored['opportunity_disjoint_seed_count']} seeds={disjoint_opportunity}"
    )
    print("no_contact_statistic_carried")
    print("zone_disjointness_artifact_verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
