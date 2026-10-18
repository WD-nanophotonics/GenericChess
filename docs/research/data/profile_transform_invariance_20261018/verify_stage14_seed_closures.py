"""Verify the Stage 14 seed-closure re-read independently.

Re-implements the closure rule from the three stored source files instead of
importing the analysis script, then compares every per-seed row and the decision
with the published result.  Re-reading only: no replay, no search, no evaluator.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUBLIC = HERE.parents[1] / "docs" / "research" / "data" / "profile_transform_invariance_20261018"
RESULT = PUBLIC / "results_stage14_seed_closures.json"
OUT = HERE / "verification_stage14_seed_closures.json"

PLAYED_CLASSES = (
    "played_move_is_the_promotion_from_the_paid_square",
    "played_move_is_another_move_from_the_paid_square",
    "played_move_is_from_a_different_square",
    "no_played_move_after_this_position",
)


def classify_seed(obs: int, disjoint: bool, contacts: int, row: dict) -> str:
    if obs == 0:
        return "no_in_zone_observation"
    if disjoint:
        return "zone_disjoint_from_every_promotion_source"
    if contacts:
        return "contact_observed"
    if row.get("no_reachable_allowed_destination", 0):
        return "source_present_but_no_allowed_destination"
    if row.get("pseudo_promotion_filtered_by_legal_safety", 0):
        return "source_present_but_legally_filtered"
    return "unexplained"


def main() -> int:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    disjoint = json.loads(
        (PUBLIC / "results_zone_promotion_disjointness.json").read_text(encoding="utf-8")
    )
    stage11 = json.loads(
        (PUBLIC / "results_zone_promotion_source_classification.json").read_text(
            encoding="utf-8"
        )
    )
    stage12 = json.loads(
        (PUBLIC / "results_stage12_contact_choice.json").read_text(encoding="utf-8")
    )

    d = {r["seed"]: r for r in disjoint["per_seed"]}
    s11 = {r["seed"]: r for r in stage11["per_seed"]}
    contacts = {
        r["seed"]: sum(r.get(name, 0) for name in PLAYED_CLASSES)
        for r in stage12["per_seed"]
    }

    expected = {
        seed: classify_seed(
            d[seed]["in_zone_paid_observations"],
            bool(d[seed]["zone_disjoint_from_every_promotion_source"]),
            contacts.get(seed, 0),
            s11[seed],
        )
        for seed in s11
    }
    published = {r["seed"]: r["closure"] for r in result["per_seed"]}
    mismatched = {
        seed: [published.get(seed), expected[seed]]
        for seed in expected
        if published.get(seed) != expected[seed]
    }
    extra = sorted(set(published) - set(expected))
    missing = sorted(set(expected) - set(published))

    checks = [
        {
            "check": "closure_per_seed_matches_independent_reimplementation",
            "passed": not mismatched and not extra and not missing,
            "detail": {"mismatched": mismatched, "extra": extra, "missing": missing},
        },
        {
            "check": "contact_totals_agree_across_stages_11_and_12",
            "passed": sum(contacts.values())
            == stage11["summary"]["in_zone_contact"]
            == stage12["summary"]["in_zone_contact"],
            "detail": [
                sum(contacts.values()),
                stage11["summary"]["in_zone_contact"],
                stage12["summary"]["in_zone_contact"],
            ],
        },
        {
            "check": "published_per_seed_contacts_match_stage_12",
            "passed": all(
                r["contacts"] == contacts.get(r["seed"], 0) for r in result["per_seed"]
            ),
            "detail": sum(r["contacts"] for r in result["per_seed"]),
        },
        {
            "check": "published_observations_match_stage_10",
            "passed": all(
                r["in_zone_paid_observations"]
                == d[r["seed"]]["in_zone_paid_observations"]
                for r in result["per_seed"]
            ),
            "detail": sum(r["in_zone_paid_observations"] for r in result["per_seed"]),
        },
        {
            "check": "observation_total_reconciles_with_stage_11",
            "passed": sum(r["in_zone_paid_observations"] for r in result["per_seed"])
            == stage11["summary"]["in_zone_paid_observations"],
            "detail": stage11["summary"]["in_zone_paid_observations"],
        },
        {
            "check": "buckets_reaggregate_to_stage_11_summary",
            "passed": all(
                sum(r.get(b, 0) for r in stage11["per_seed"]) == stage11["summary"][b]
                for b in (
                    "in_zone_contact",
                    "zone_geometry_no_source",
                    "no_reachable_allowed_destination",
                    "dead_promotion_target",
                    "pseudo_promotion_filtered_by_legal_safety",
                    "would_promote_but_not_to_move",
                )
            ),
            "detail": "six buckets",
        },
        {
            "check": "decision_rule_reproduces",
            "passed": (
                result["summary"]["decision"]
                == (
                    "unexplained_zero_contact_seed_remains"
                    if "unexplained" in expected.values()
                    else "every_zero_contact_seed_has_a_named_structural_closure"
                )
            ),
            "detail": result["summary"]["decision"],
        },
        {
            "check": "no_in_zone_versus_outside_rate_is_carried",
            "passed": not any(
                marker in RESULT.read_text(encoding="utf-8")
                for marker in ("outside_zone", "in_zone_rate_outside")
            ),
            "detail": [],
        },
    ]

    payload = {
        "role": "DEEPSEEK_AUX",
        "verifier": "verify_stage14_seed_closures.py",
        "verdict": "all_checks_passed"
        if all(c["passed"] for c in checks)
        else "checks_failed",
        "checks": checks,
        "independent_recomputation": expected,
        "scope": "board 4, classic_like, the six stored Stage-8 files; re-read only",
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    for c in checks:
        print(("PASS " if c["passed"] else "FAIL ") + c["check"])
    print(payload["verdict"])
    return 0 if payload["verdict"] == "all_checks_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
