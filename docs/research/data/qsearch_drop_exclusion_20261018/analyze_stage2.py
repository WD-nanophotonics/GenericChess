"""DEEPSEEK_AUX stage-2 analysis: recompute endpoint from stored per-position records.

All descriptive extras are labelled post_hoc and do not change the pre-written rule.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results_stage2_fresh_seeds.json"
OUT = HERE / "stage2-analysis.json"
MATE_THRESHOLD = 900_000_000


def main() -> int:
    payload = json.loads(RESULTS.read_text(encoding="utf-8"))
    positions = payload["positions"]
    endpoints = payload["endpoints"]

    recomputed = []
    for p in positions:
        records = p["excluded_drop_records"]
        recomputed.append(
            {
                "seed": p["seed"],
                "mate_bound": abs(p["d2_score"]) >= MATE_THRESHOLD
                or abs(p["d3_score"]) >= MATE_THRESHOLD,
                "excluded_drops": len(records),
                "blind_threat_drops": sum(1 for r in records if r["blind_threats"]),
                "profitable_blind_threat_drops": sum(
                    1 for r in records if r["profitable_blind_threats"]
                ),
                "new_enemy_attack_drops": sum(
                    1 for r in records if r["new_enemy_attacks"] > 0
                ),
            }
        )

    mismatch = [
        (p["seed"], key, p[key], r[key])
        for p, r in zip(positions, recomputed)
        for key in (
            "mate_bound",
            "excluded_drops",
            "blind_threat_drops",
            "profitable_blind_threat_drops",
        )
        if p[key] != r[key]
    ]

    eligible = [p for p in positions if not r_mate(p)]
    group = [p for p in eligible if p["blind_threat_drops"] > 0]
    rest = [p for p in eligible if p["blind_threat_drops"] == 0]
    group_deltas = sorted(p["abs_score_delta_2_3"] for p in group)
    rest_deltas = sorted(p["abs_score_delta_2_3"] for p in rest)
    group_median = statistics.median(group_deltas) if group_deltas else None
    rest_median = statistics.median(rest_deltas) if rest_deltas else None
    group_flips = sum(1 for p in group if not p["action_equal_2_3"])
    rest_flips = sum(1 for p in rest if not p["action_equal_2_3"])
    delta_ok = (
        group_median is not None
        and rest_median is not None
        and rest_median > 0
        and group_median >= 2 * rest_median
    )
    flip_ok = (
        len(group) >= 3
        and group_flips >= 3
        and rest_flips / len(rest) * 2 <= group_flips / len(group)
    )
    supported = len(group) >= 3 and (delta_ok or flip_ok)

    blind_drops = [
        {
            "seed": p["seed"],
            "action": r["action_key"],
            "base_type": r["base_type"],
            "blind_threats": r["blind_threats"],
            "profitable_blind_threats": r["profitable_blind_threats"],
            "max_blind_threat_value_gap": r["max_blind_threat_value_gap"],
            "drop_square": r["drop_square"],
            "mover_score_depth1": r["confirmation"]["child_score_mover_perspective"]
            if r["confirmation"]
            else None,
            "parent_static": r["confirmation"]["parent_static"]
            if r["confirmation"]
            else None,
            "exceeds_parent_static": r["confirmation"]["exceeds_parent_static"]
            if r["confirmation"]
            else None,
        }
        for p in positions
        for r in p["excluded_drop_records"]
        if r["blind_threats"]
    ]

    profitable = [
        {"seed": p["seed"], **rec}
        for p in positions
        for r in p["excluded_drop_records"]
        for rec in r["profitable_records"]
    ]

    # Post-hoc descriptive sensitivity only; not a second endpoint.
    clean_group = [p for p in group if p["profitable_blind_threat_drops"] == 0]
    hard_limit_d2 = [
        p["seed"]
        for p in positions
        if p["search_reason_d2"] != "completed_depth"
        or p["search_reason_d3"] != "completed_depth"
    ]
    group_hard_limited = [
        p["seed"]
        for p in group
        if p["search_reason_d2"] != "completed_depth"
        or p["search_reason_d3"] != "completed_depth"
    ]
    d4_action = {
        p["seed"]: p["depth4_secondary"]["action"] for p in positions
    }
    d4_changed = [
        p["seed"]
        for p in positions
        if d4_action.get(p["seed"]) != p["d3_action"]
    ]
    d4_changed_group = [s for s in d4_changed if s in {p["seed"] for p in group}]

    analysis = {
        "role": "DEEPSEEK_AUX",
        "source_result": str(RESULTS),
        "positions": len(positions),
        "record_recomputation_mismatches": mismatch,
        "mate_bound_positions": [p["seed"] for p in positions if r_mate(p)],
        "mate_bound_share": round(
            sum(1 for p in positions if r_mate(p)) / len(positions), 4
        ),
        "eligible_non_mate_positions": len(eligible),
        "endpoint_recomputed": {
            "blind_group_positions": len(group),
            "rest_positions": len(rest),
            "group_median_abs_delta": group_median,
            "rest_median_abs_delta": rest_median,
            "group_flips": group_flips,
            "rest_flips": rest_flips,
            "group_flip_rate": group_flips / len(group) if group else None,
            "rest_flip_rate": rest_flips / len(rest) if rest else None,
            "delta_criterion": bool(delta_ok),
            "flip_criterion": bool(flip_ok),
            "supported": bool(supported),
            "matches_stored": {
                "blind_group_positions": len(group)
                == endpoints["blind_group_positions"],
                "rest_positions": len(rest) == endpoints["rest_positions"],
                "group_median": group_median
                == endpoints["blind_group_median_abs_delta"],
                "rest_median": rest_median == endpoints["rest_median_abs_delta"],
                "supported": bool(supported) == endpoints["supported"],
            },
        },
        "group_deltas_sorted": group_deltas,
        "rest_deltas_sorted": rest_deltas,
        "group_zero_deltas": sum(1 for d in group_deltas if d == 0),
        "group_positive_deltas": [d for d in group_deltas if d > 0],
        "profitable_blind_threats": len(profitable),
        "profitable_records": profitable,
        "blind_drops": blind_drops,
        "blind_confirmations_above_parent_static": sum(
            1 for b in blind_drops if b["exceeds_parent_static"]
        ),
        "hard_limit_positions_d2_or_d3": hard_limit_d2,
        "group_hard_limited_positions": group_hard_limited,
        "post_hoc_sensitivity": {
            "note": "descriptive only; the pre-written rule above is the endpoint",
            "group_excluding_profitable_positions": len(clean_group),
            "group_median_excluding_profitable": statistics.median(
                [p["abs_score_delta_2_3"] for p in clean_group]
            )
            if clean_group
            else None,
            "group_seeds": [p["seed"] for p in group],
            "group_positive_delta_seeds": [
                p["seed"] for p in group if p["abs_score_delta_2_3"] > 0
            ],
            "d3_to_d4_action_changes": len(d4_changed),
            "d3_to_d4_action_changes_in_group": len(d4_changed_group),
        },
        "interpretation_limits": [
            "score change |d3-d2| is sensitivity, not utility or strength",
            "the group median sits between four zeros and four large deltas; "
            "it is not evidence of a typical position",
            "pseudo-attack geometry ignores pins; undefended is approximate",
            "4x4 generated rules, one sampled position per seed",
        ],
    }
    OUT.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(
        {
            k: analysis[k]
            for k in (
                "record_recomputation_mismatches",
                "eligible_non_mate_positions",
                "endpoint_recomputed",
                "profitable_blind_threats",
                "blind_confirmations_above_parent_static",
                "post_hoc_sensitivity",
            )
        },
        indent=2,
    ))
    return 0


def r_mate(p: dict) -> bool:
    return abs(p["d2_score"]) >= MATE_THRESHOLD or abs(p["d3_score"]) >= MATE_THRESHOLD


if __name__ == "__main__":
    raise SystemExit(main())
