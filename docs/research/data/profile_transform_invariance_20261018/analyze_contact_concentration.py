"""Decompose the Stage 8 promotion-contact contrast by seed.

DEEPSEEK_AUX, session ``6de032cc-45b4-4938-8700-2abdcae346aa``.  Reads only
``results_bind_reachability_to_decisions.json``; no replay, no search, no new
game.  The pooled 53/2489 against 782/5594 is an aggregate over 182 games from
36 seeds, so this script asks whether the contrast survives when the seed is
treated as the independent unit instead of the position observation.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "results_bind_reachability_to_decisions.json"
OUT = HERE / "results_contact_concentration.json"


def main() -> int:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    summary = payload["summary"]
    per_seed: dict[int, dict[str, int]] = defaultdict(
        lambda: dict(
            games=0,
            in_zone=0,
            in_zone_hit=0,
            not_in_zone=0,
            not_in_zone_hit=0,
            dead_intent=0,
            dead_intent_hit=0,
            neither=0,
            neither_hit=0,
        )
    )
    for game in payload["per_game"]:
        row = per_seed[game["seed"]]
        row["games"] += 1
        row["in_zone"] += game["promotable_in_zone"]
        row["in_zone_hit"] += game["promotable_in_zone_with_promotion"]
        row["dead_intent"] += game["promotable_dead_intent"]
        row["dead_intent_hit"] += game["promotable_dead_intent_with_promotion"]
        row["neither"] += game["promotable_neither"]
        row["neither_hit"] += game["promotable_neither_with_promotion"]
        row["not_in_zone"] += game["promotable_dead_intent"] + game["promotable_neither"]
        row["not_in_zone_hit"] += (
            game["promotable_dead_intent_with_promotion"]
            + game["promotable_neither_with_promotion"]
        )

    # The decomposition must re-aggregate to the published summary exactly.
    totals = dict(
        promotable_in_zone_observations=sum(r["in_zone"] for r in per_seed.values()),
        promotable_in_zone_with_legal_promotion=sum(
            r["in_zone_hit"] for r in per_seed.values()
        ),
        promotable_not_in_zone_observations=sum(
            r["not_in_zone"] for r in per_seed.values()
        ),
        promotable_not_in_zone_with_legal_promotion=sum(
            r["not_in_zone_hit"] for r in per_seed.values()
        ),
        promotable_dead_intent=sum(r["dead_intent"] for r in per_seed.values()),
        promotable_dead_intent_with_legal_promotion=sum(
            r["dead_intent_hit"] for r in per_seed.values()
        ),
        promotable_neither=sum(r["neither"] for r in per_seed.values()),
        promotable_neither_with_legal_promotion=sum(
            r["neither_hit"] for r in per_seed.values()
        ),
        games=sum(r["games"] for r in per_seed.values()),
    )
    checks = {
        "in_zone_observations_match": totals["promotable_in_zone_observations"]
        == summary["promotable_in_zone_observations"],
        "in_zone_hits_match": totals["promotable_in_zone_with_legal_promotion"]
        == summary["promotable_in_zone_with_legal_promotion"],
        "not_in_zone_observations_match": totals["promotable_not_in_zone_observations"]
        == summary["promotable_not_in_zone_observations"],
        "not_in_zone_hits_match": totals[
            "promotable_not_in_zone_with_legal_promotion"
        ]
        == summary["promotable_not_in_zone_with_legal_promotion"],
        "dead_intent_matches": totals["promotable_dead_intent"]
        == summary["half_bonus_dead_branch_intent"],
        "dead_intent_hits_match": totals[
            "promotable_dead_intent_with_legal_promotion"
        ]
        == summary["promotable_dead_intent_with_legal_promotion"],
        "neither_matches": totals["promotable_neither"] == summary["neither_branch"],
        "neither_hits_match": totals[
            "promotable_neither_with_legal_promotion"
        ]
        == summary["promotable_neither_with_legal_promotion"],
        "games_match": totals["games"] == summary["games_scanned"],
    }

    rows = []
    for seed in sorted(per_seed):
        row = per_seed[seed]
        rows.append(
            dict(
                seed=seed,
                games=row["games"],
                in_zone=row["in_zone"],
                in_zone_hit=row["in_zone_hit"],
                not_in_zone=row["not_in_zone"],
                not_in_zone_hit=row["not_in_zone_hit"],
                in_zone_rate=(
                    round(row["in_zone_hit"] / row["in_zone"], 5) if row["in_zone"] else None
                ),
                not_in_zone_rate=(
                    round(row["not_in_zone_hit"] / row["not_in_zone"], 5)
                    if row["not_in_zone"]
                    else None
                ),
            )
        )

    seeds_with_contact = [r for r in rows if r["in_zone_hit"]]
    both_arms = [
        r for r in rows if r["in_zone"] and r["not_in_zone"]
    ]
    favouring = [r for r in both_arms if r["not_in_zone_rate"] > (r["in_zone_rate"] or 0.0)]
    against = [r for r in both_arms if r["not_in_zone_rate"] < (r["in_zone_rate"] or 0.0)]
    tied = [r for r in both_arms if r["not_in_zone_rate"] == (r["in_zone_rate"] or 0.0)]
    contact_counts = sorted((r["in_zone_hit"] for r in rows), reverse=True)
    total_hits = totals["promotable_in_zone_with_legal_promotion"]
    top_share = (
        round(contact_counts[0] / total_hits, 4) if total_hits else None
    )
    top3_share = (
        round(sum(contact_counts[:3]) / total_hits, 4) if total_hits else None
    )

    decision = (
        "contrast_is_seed_spread"
        if len(favouring) > len(against) and len(seeds_with_contact) >= len(rows) / 2
        else "contrast_is_seed_concentrated"
    )

    # Concentration inside the seeds that do produce contact: a single game can
    # repeat the same standing piece over many plies, so the per-game counts say
    # whether "34 of 53" is 34 independent choices or one long vigil.
    contact_games = sorted(
        (
            dict(seed=g["seed"], depth=g["depth"], game_index=g["game_index"],
                 hits=g["in_zone_with_legal_promotion"],
                 in_zone=g["promotable_in_zone"],
                 positions=g["positions"])
            for g in payload["per_game"]
            if g["in_zone_with_legal_promotion"]
        ),
        key=lambda g: -g["hits"],
    )
    high_seeds = [
        r["seed"]
        for r in both_arms
        if (r["in_zone_rate"] or 0.0) > (r["not_in_zone_rate"] or 0.0)
    ]
    high_hits = sum(r["in_zone_hit"] for r in rows if r["seed"] in high_seeds)
    high_obs = sum(r["in_zone"] for r in rows if r["seed"] in high_seeds)
    rest_hits = total_hits - high_hits
    rest_obs = totals["promotable_in_zone_observations"] - high_obs

    result = dict(
        role="DEEPSEEK_AUX",
        session="6de032cc-45b4-4938-8700-2abdcae346aa",
        question=(
            "Does the in-zone promotion-contact contrast hold when the seed, not the "
            "position observation, is treated as the independent unit?"
        ),
        source="results_bind_reachability_to_decisions.json",
        source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        reaggregation_checks=checks,
        reaggregates_to_published_summary=all(checks.values()),
        seeds=len(rows),
        seeds_with_any_in_zone_observation=sum(1 for r in rows if r["in_zone"]),
        seeds_with_any_contact=len(seeds_with_contact),
        contact_hits_total=total_hits,
        largest_seed_contact_count=contact_counts[0] if contact_counts else 0,
        largest_seed_contact_share=top_share,
        top3_seed_contact_share=top3_share,
        seeds_with_both_arms=len(both_arms),
        seeds_not_in_zone_rate_higher=len(favouring),
        seeds_in_zone_rate_higher=len(against),
        seeds_tied_in_both_arms=len(tied),
        seeds_where_in_zone_rate_exceeds_outside=high_seeds,
        in_zone_rate_inside_those_seeds=(
            round(high_hits / high_obs, 4) if high_obs else None
        ),
        in_zone_hits_inside_those_seeds=high_hits,
        in_zone_observations_inside_those_seeds=high_obs,
        in_zone_rate_in_remaining_seeds=(
            round(rest_hits / rest_obs, 4) if rest_obs else None
        ),
        in_zone_hits_in_remaining_seeds=rest_hits,
        in_zone_observations_in_remaining_seeds=rest_obs,
        games_with_any_contact=len(contact_games),
        contact_games=contact_games[:12],
        decision=decision,
        per_seed=rows,
        nonclaims=[
            "observations inside one game are not independent; this file only re-weights to the seed",
            "the seed panel is 36 rulesets, far too few for an interval worth quoting",
            "no claim that any term changed a chosen action, an outcome or a strength ranking",
        ],
    )
    OUT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("per_seed", "nonclaims")},
            indent=1,
        )
    )
    return 0 if result["reaggregates_to_published_summary"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
