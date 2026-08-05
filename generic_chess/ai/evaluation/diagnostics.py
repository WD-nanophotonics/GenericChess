"""Human/JSON diagnostics for a ruleset evaluation profile."""

from __future__ import annotations

from dataclasses import asdict

from .profile import RuleSetEvaluationProfile


def profile_report(profile: RuleSetEvaluationProfile, cache_hit: bool, elapsed: float) -> dict:
    types = []
    for tid, p in sorted(profile.piece_profiles.items()):
        types.append(
            {
                "type_id": p.type_id,
                "name": p.type_id,
                "board_value": p.normalized_board_value,
                "hand_value": p.normalized_hand_value,
                "promotion_gain": p.promotion_option_value,
                "drop_freedom_ratio": p.drop_freedom_ratio,
                "drop_mobility": p.drop_mobility,
                "raw_capability_score": p.raw_capability_score,
                "is_anchor": p.is_anchor,
                "is_promotable": p.is_promotable,
            }
        )
    return {
        "ruleset_fingerprint": profile.ruleset_fingerprint,
        "evaluator_version": profile.evaluator_version,
        "cache_hit": cache_hit,
        "elapsed_seconds": elapsed,
        "median_non_anchor_value": profile.median_non_anchor_value,
        "piece_types": types,
    }


def report_text(report: dict) -> str:
    lines = [
        f"RuleSet fingerprint: {report['ruleset_fingerprint']}",
        f"Evaluator version:   {report['evaluator_version']}",
        f"Cache hit:           {report['cache_hit']}",
        f"Analysis elapsed:    {report['elapsed_seconds']:.4f} s",
        f"Median non-anchor:   {report['median_non_anchor_value']}",
        "",
    ]
    for t in report["piece_types"]:
        lines.append(
            f"Type {t['type_id']} (anchor={t['is_anchor']}, promotable={t['is_promotable']}): "
            f"board={t['board_value']} hand={t['hand_value']} "
            f"promo_gain={t['promotion_gain']} "
            f"drop_freedom={t['drop_freedom_ratio']:.3f} "
            f"drop_mobility={t['drop_mobility']:.2f} "
            f"raw={t['raw_capability_score']:.3f}"
        )
    return "\n".join(lines)
