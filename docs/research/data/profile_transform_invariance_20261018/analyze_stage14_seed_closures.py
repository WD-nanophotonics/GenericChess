"""Join the stored per-seed rows of Stages 10-12 and name each seed's closure.

Re-reading only: reads three published JSON files, recomputes the global totals
from the per-seed rows, assigns exactly one closure class per seed with the rule
fixed in plan_stage14_seed_closures.json before the run.  No replay, no search,
no evaluator call and no game.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUBLIC = HERE.parents[1] / "docs" / "research" / "data" / "profile_transform_invariance_20261018"

DISJOINT = PUBLIC / "results_zone_promotion_disjointness.json"
CLASSIFY = PUBLIC / "results_zone_promotion_source_classification.json"
CONTACT = PUBLIC / "results_stage12_contact_choice.json"
OUT = HERE / "results_stage14_seed_closures.json"

BUCKETS = (
    "in_zone_contact",
    "zone_geometry_no_source",
    "no_reachable_allowed_destination",
    "dead_promotion_target",
    "pseudo_promotion_filtered_by_legal_safety",
    "would_promote_but_not_to_move",
)

GLOBAL_KEYS = {
    "in_zone_contact": "in_zone_contact",
    "zone_geometry_no_source": "zone_geometry_no_source",
    "no_reachable_allowed_destination": "no_reachable_allowed_destination",
    "dead_promotion_target": "dead_promotion_target",
    "pseudo_promotion_filtered_by_legal_safety": "pseudo_promotion_filtered_by_legal_safety",
    "would_promote_but_not_to_move": "would_promote_but_not_to_move",
}


def closure(row: dict, disjoint: dict, contacts: int) -> tuple[str, str]:
    # The observation count lives in the Stage 10 rows; the bucket counts live in
    # the Stage 11 rows.  The first run of this script read the count from the
    # Stage 11 row, found it absent everywhere and therefore labelled all 14
    # seeds "no_in_zone_observation" - recorded as a defect below, not kept.
    if disjoint.get("in_zone_paid_observations", 0) == 0:
        return "no_in_zone_observation", "the seed pays the in-zone bonus in no scanned position"
    if disjoint.get("zone_disjoint_from_every_promotion_source"):
        return (
            "zone_disjoint_from_every_promotion_source",
            "no square in the seed's zone is a promotion source for that base type, "
            "so a contact is impossible by construction",
        )
    if contacts > 0:
        return "contact_observed", "at least one in-zone contact occurs in this seed"
    if row.get("no_reachable_allowed_destination", 0) > 0:
        return (
            "source_present_but_no_allowed_destination",
            "the paid square is a promotion source for the base type, but no allowed "
            "destination is reachable in any of these positions",
        )
    if row.get("pseudo_promotion_filtered_by_legal_safety", 0) > 0:
        return (
            "source_present_but_legally_filtered",
            "the promotion is pseudo-legal but removed by the legal-safety check",
        )
    return "unexplained", "no stored bucket accounts for the missing contacts"


def main() -> int:
    started = time.perf_counter()
    disjoint = json.loads(DISJOINT.read_text(encoding="utf-8"))
    classify = json.loads(CLASSIFY.read_text(encoding="utf-8"))
    contact = json.loads(CONTACT.read_text(encoding="utf-8"))
    problems: list[str] = []

    d_rows = {r["seed"]: r for r in disjoint["per_seed"]}
    c_rows = {r["seed"]: r for r in classify["per_seed"]}
    k_rows = {r["seed"]: r for r in contact["per_seed"]}

    # Reconciliation 3: the same seeds must carry in-zone observations in both files.
    d_observed = {s for s, r in d_rows.items() if r.get("in_zone_paid_observations", 0) > 0}
    c_observed = set(c_rows)
    if d_observed != c_observed:
        problems.append(
            f"seed sets disagree: only_disjoint={sorted(d_observed - c_observed)} "
            f"only_classification={sorted(c_observed - d_observed)}"
        )

    # Reconciliation 1 and 2: per-seed rows must re-aggregate to the global totals.
    contact_total = 0
    for seed, row in k_rows.items():
        contact_total += sum(v for k, v in row.items() if k != "seed")
    # Stage 12 counts contacts per seed as the sum of its four played classes,
    # except that "in_zone_contact" in Stage 11 is the contact count itself.
    contact_from_classes = 0
    for row in contact["per_seed"]:
        contact_from_classes += sum(
            v
            for k, v in row.items()
            if k
            in (
                "played_move_is_the_promotion_from_the_paid_square",
                "played_move_is_another_move_from_the_paid_square",
                "played_move_is_from_a_different_square",
                "no_played_move_after_this_position",
            )
        )
    if contact_from_classes != contact["summary"]["in_zone_contact"]:
        problems.append(
            f"stage12 per-seed contacts {contact_from_classes} != summary "
            f"{contact['summary']['in_zone_contact']}"
        )
    if contact_from_classes != classify["summary"]["in_zone_contact"]:
        problems.append(
            f"stage12 contacts {contact_from_classes} != stage11 contacts "
            f"{classify['summary']['in_zone_contact']}"
        )

    recomputed = {name: 0 for name in BUCKETS}
    for row in classify["per_seed"]:
        for name in BUCKETS:
            recomputed[name] += row.get(name, 0)
    for name, key in GLOBAL_KEYS.items():
        if recomputed[name] != classify["summary"][key]:
            problems.append(
                f"per-seed {name} sums to {recomputed[name]} but summary says "
                f"{classify['summary'][key]}"
            )

    rows = []
    for seed in sorted(c_rows):
        row = c_rows[seed]
        krow = k_rows.get(seed, {})
        contacts = sum(
            v
            for k, v in krow.items()
            if k
            in (
                "played_move_is_the_promotion_from_the_paid_square",
                "played_move_is_another_move_from_the_paid_square",
                "played_move_is_from_a_different_square",
                "no_played_move_after_this_position",
            )
        )
        name, reason = closure(row, d_rows.get(seed, {}), contacts)
        rows.append(
            {
                "seed": seed,
                "in_zone_paid_observations": d_rows.get(seed, {}).get(
                    "in_zone_paid_observations", 0
                ),
                "contacts": contacts,
                "zone_disjoint_from_every_promotion_source": bool(
                    d_rows.get(seed, {}).get("zone_disjoint_from_every_promotion_source")
                ),
                "zone_squares_that_are_promotion_sources": d_rows.get(seed, {}).get(
                    "zone_squares_that_are_promotion_sources"
                ),
                "zone_squares": d_rows.get(seed, {}).get("zone_squares"),
                "to_move_no_reachable_allowed_destination": row.get(
                    "no_reachable_allowed_destination", 0
                ),
                "to_move_zone_geometry_no_source": row.get("zone_geometry_no_source", 0),
                "to_move_pseudo_promotion_filtered_by_legal_safety": row.get(
                    "pseudo_promotion_filtered_by_legal_safety", 0
                ),
                "would_promote_but_not_to_move": row.get(
                    "would_promote_but_not_to_move", 0
                ),
                "closure": name,
                "closure_reason": reason,
            }
        )

    unexplained = [r["seed"] for r in rows if r["closure"] == "unexplained"]
    decision = (
        "unexplained_zero_contact_seed_remains"
        if unexplained
        else "every_zero_contact_seed_has_a_named_structural_closure"
    )
    by_closure: dict[str, list[int]] = {}
    for r in rows:
        by_closure.setdefault(r["closure"], []).append(r["seed"])

    payload = {
        "role": "DEEPSEEK_AUX",
        "session": "3d8dc073-5fcc-456e-933c-a7b6646296e5",
        "question": "Is every zero-contact seed explained by a named structural closure?",
        "plan": "plan_stage14_seed_closures.json",
        "design": {
            "re_read_only": True,
            "no_replay": True,
            "no_search": True,
            "no_new_games": True,
            "sources": [DISJOINT.name, CLASSIFY.name, CONTACT.name],
            "closure_rule": "fixed in plan_stage14_seed_closures.json before the run",
        },
        "summary": {
            "decision": decision,
            "seeds_with_in_zone_observations": len(rows),
            "seeds_examined": len(d_rows),
            "unexplained_seeds": unexplained,
            "closure_counts": {k: len(v) for k, v in sorted(by_closure.items())},
            "closure_seeds": {k: v for k, v in sorted(by_closure.items())},
            "recomputed_global_buckets": recomputed,
            "wall_seconds": round(time.perf_counter() - started, 3),
        },
        "per_seed": rows,
        "reconciliation": {
            "stage12_per_seed_contact_total": contact_from_classes,
            "stage12_summary_contact_total": contact["summary"]["in_zone_contact"],
            "stage11_summary_contact_total": classify["summary"]["in_zone_contact"],
            "problems": problems,
        },
        "defect_corrections": [
            {
                "defect": "the closure rule read in_zone_paid_observations from the Stage 11 per-seed row",
                "observed": "that key exists only in the Stage 10 rows, so the first run returned closure 'no_in_zone_observation' for all 14 seeds and its decision was not kept",
                "correction": "the count is now read from the Stage 10 row and the bucket counts stay from Stage 11",
                "how_detected": "the first run's closure_counts held a single class covering every seed, which contradicts the stored contacts in the same file",
                "numbers_changed": False,
            }
        ],
        "nonclaims": [
            "a closure class explains why a contact could not occur in that seed; it does not value the zone term",
            "no in-zone-versus-outside rate is produced and the withdrawn 0-vs-53 contrast stays excluded",
            "no strength, playing-quality, utility or causal claim",
            "re-reading three files written by the same scripts is bookkeeping, not independent measurement",
            "board 4, classic_like, the six stored files only",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=1))
    print(f"problems={problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
