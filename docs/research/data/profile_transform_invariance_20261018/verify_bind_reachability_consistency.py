"""Check the Stage 8 result file against itself and against Stage 7.

This is an arithmetic and bookkeeping audit of already-stored JSON.  It runs
no replay, no search and no evaluator: it exists so the two claims the report
makes about its own numbers - that the per-game records add up to the summary,
and that the position counts reproduce Stage 7 exactly - can be re-checked
from the stored files alone.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE8 = HERE.parent / "games-leaf-terms-20261018" / "results_bind_reachability_to_decisions.json"
STAGE7 = HERE.parent / "games-leaf-terms-20261018" / "results_stored_games_leaf_terms.json"

SUMMED_FIELDS = (
    "positions",
    "in_zone_at_start",
    "in_zone_during_play",
    "in_zone_with_legal_promotion",
    "promotions_chosen",
    "promotions_from_in_zone",
    "promotions_from_dead_intent",
)

STAGE7_SHARED = (
    "promotable_observations",
    "in_zone_live",
    "half_bonus_dead_branch_intent",
    "neither_branch",
)


def main() -> int:
    stage8 = json.loads(STAGE8.read_text(encoding="utf-8"))
    summary = stage8["summary"]
    per_game = stage8["per_game"]
    stage7 = json.loads(STAGE7.read_text(encoding="utf-8"))["summary"]

    problems: list[str] = []

    # 1. per-game records must add up to the summary fields they decompose.
    for field in SUMMED_FIELDS:
        total = sum(g[field] for g in per_game)
        expected = summary["positions_scanned"] if field == "positions" else summary[field]
        if total != expected:
            problems.append(f"per_game_sum_mismatch {field} summed={total} summary={expected}")

    # 2. Stage 7 position counts must be reproduced exactly.
    for field in STAGE7_SHARED:
        if summary.get(field) != stage7.get(field):
            problems.append(f"stage7_disagreement {field} stage8={summary.get(field)} stage7={stage7.get(field)}")

    # 3. Internal partitions.
    if summary["in_zone_at_start"] + summary["in_zone_during_play"] != summary["in_zone_live"]:
        problems.append("in_zone_split_does_not_reconstruct_in_zone_live")
    if summary["in_zone_with_legal_promotion"] + summary["in_zone_without_legal_promotion"] != summary["in_zone_live"]:
        problems.append("in_zone_contact_split_does_not_reconstruct_in_zone_live")
    if (
        summary["promotable_dead_intent_with_legal_promotion"] + summary["promotable_neither_with_legal_promotion"]
        != summary["promotable_not_in_zone_with_legal_promotion"]
    ):
        problems.append("not_in_zone_contact_split_does_not_reconstruct_total")
    if (
        summary["promotable_dead_intent_with_legal_promotion"]
        + summary["promotable_neither_with_legal_promotion"]
        + summary["in_zone_with_legal_promotion"]
        > summary["legal_promotion_actions"]
    ):
        problems.append("contact_counts_exceed_legal_promotion_actions")
    for prefix in ("moves", "promotions"):
        parts = (
            summary[f"{prefix}_from_in_zone"]
            + summary[f"{prefix}_from_dead_intent"]
            + summary[f"{prefix}_from_neither"]
        )
        whole = summary["moves_classified"] if prefix == "moves" else summary["promotions_chosen"]
        if parts != whole:
            problems.append(f"{prefix}_classes_do_not_sum_to_total parts={parts} total={whole}")

    # 4. Reported rates and the ratio must follow from the raw counts.
    in_rate = summary["in_zone_with_legal_promotion"] / summary["promotable_in_zone_observations"]
    out_rate = summary["promotable_not_in_zone_with_legal_promotion"] / summary["promotable_not_in_zone_observations"]
    if abs(in_rate - summary["in_zone_legal_promotion_rate"]) > 1e-5:
        problems.append(f"in_zone_rate_does_not_match_counts {in_rate}")
    if abs(out_rate - summary["not_in_zone_legal_promotion_rate"]) > 1e-5:
        problems.append(f"not_in_zone_rate_does_not_match_counts {out_rate}")
    if abs(out_rate / in_rate - summary["rate_ratio_not_in_zone_over_in_zone"]) > 5e-3:
        problems.append(f"ratio_does_not_match_rates {out_rate / in_rate}")

    # 5. The two decision strings must follow the pre-registered rules.
    if summary["in_zone_with_legal_promotion"] > 0:
        wanted = "in_zone_full_bonus_has_immediate_promotion_contact"
    else:
        wanted = "in_zone_full_bonus_has_no_immediate_promotion_contact"
    if summary["primary_decision"] != wanted:
        problems.append(f"primary_decision_contradicts_count {summary['primary_decision']}")
    depressed = out_rate / in_rate >= 2.0
    wanted = (
        "in_zone_promotability_is_depressed_relative_to_other_promotable_pieces"
        if depressed
        else "in_zone_promotability_matches_other_promotable_pieces"
    )
    if summary["promotability_contrast"] != wanted:
        problems.append(f"contrast_decision_contradicts_ratio {summary['promotability_contrast']}")
    if summary["problems"]:
        problems.append(f"replay_problems_present {summary['problems']}")
    if summary["games_failed_replay"]:
        problems.append(f"games_failed_replay {summary['games_failed_replay']}")

    print(f"per_game_records={len(per_game)} summed_fields={len(SUMMED_FIELDS)}")
    print(f"stage7_fields_compared={len(STAGE7_SHARED)}")
    print(f"in_zone_rate={in_rate:.5f} not_in_zone_rate={out_rate:.5f} ratio={out_rate / in_rate:.2f}")
    for item in problems:
        print(item)
    print("stored_numbers_are_self_consistent" if not problems else "stored_numbers_are_inconsistent")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
