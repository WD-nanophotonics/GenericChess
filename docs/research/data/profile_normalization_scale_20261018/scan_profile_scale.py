"""Generalization scan: profile normalization at board sizes 6 and 8.

Reuses the published 4x4 endpoint implementation verbatim by importing
``scan_rule`` from the earlier scan and overriding its board-size constant.
Plan: ``plan.json`` (written before this run).  No product code is modified.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
BASE_DIR = ROOT / ".local_agent/profile-normalization-20261018"
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(ROOT))

import scan_profile_normalization as base  # noqa: E402

SEEDS = tuple(range(292001, 292041))
SIZES = (6, 8)
OUT = HERE / "results_profile_scale.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def aggregate(size: int, rules: list[dict]) -> dict:
    material_rules = [r["seed"] for r in rules if r["material_tie_groups"]]
    distortions = [d["distortion"] for r in rules for d in r["ratio_distortions"]]
    hand = [v for r in rules for v in r["hand_rounding_deviations"]]
    promos = [p for r in rules for p in r["promotion_checks"]]
    bound_violations = []
    max_bound_slack = 0.0
    for rule in rules:
        by_id = {t["type_id"]: t for t in rule["ordinary_types"]}
        for entry in rule["ratio_distortions"]:
            a, b = entry["pair"]
            v_min = min(by_id[a]["board"], by_id[b]["board"])
            v_max = max(by_id[a]["board"], by_id[b]["board"])
            bound = 0.5 * (1.0 / v_min + 1.0 / v_max) + 1e-12
            max_bound_slack = max(max_bound_slack, entry["distortion"] / bound)
            if entry["distortion"] > bound:
                bound_violations.append(
                    {
                        "seed": rule["seed"],
                        "pair": [a, b],
                        "distortion": entry["distortion"],
                        "bound": bound,
                    }
                )

    per_rule = []
    for rule in rules:
        min_value = min(t["board"] for t in rule["ordinary_types"])
        max_dist = max(
            (d["distortion"] for d in rule["ratio_distortions"]), default=0.0
        )
        per_rule.append(
            {
                "seed": rule["seed"],
                "min_normalized_value": min_value,
                "types": len(rule["ordinary_types"]),
                "pairs_over_threshold": len(rule["ratio_distortions"]),
                "max_ratio_distortion": max_dist,
            }
        )
    smallest = sorted(per_rule, key=lambda r: r["min_normalized_value"])[:5]
    largest_dist = sorted(per_rule, key=lambda r: -r["max_ratio_distortion"])[:5]

    any_inversion = any(r["inversions"] for r in rules)
    any_ceiling = any(r["ceiling_clips"] for r in rules)
    fraction = len(material_rules) / len(rules)
    if any_inversion or any_ceiling:
        decision = "defect_at_larger_size"
    elif fraction >= 0.10:
        decision = "coarse_normalization_at_larger_size"
    else:
        decision = "ratio_rounding_bounded_persists"
    if bound_violations:
        decision = "bound_violated"

    counts = [len(r["ordinary_types"]) for r in rules]
    return {
        "board_size": size,
        "rules": len(rules),
        "ordinary_types": sum(counts),
        "types_per_rule_min": min(counts),
        "types_per_rule_max": max(counts),
        "pairs_per_rule": sum(
            len(r["ordinary_types"]) * (len(r["ordinary_types"]) - 1) // 2 for r in rules
        )
        // len(rules),
        "rules_with_inversion": sum(bool(r["inversions"]) for r in rules),
        "inversion_count": sum(len(r["inversions"]) for r in rules),
        "rules_with_ceiling_clip": sum(bool(r["ceiling_clips"]) for r in rules),
        "ceiling_clip_types": sum(len(r["ceiling_clips"]) for r in rules),
        "rules_with_floor_value_1": sum(bool(r["floor_clips"]) for r in rules),
        "floor_value_1_types": sum(len(r["floor_clips"]) for r in rules),
        "min_normalized_value": min(t["board"] for r in rules for t in r["ordinary_types"]),
        "max_normalized_value": max(t["board"] for r in rules for t in r["ordinary_types"]),
        "rules_with_any_tie": sum(bool(r["tie_groups"]) for r in rules),
        "tie_groups": sum(len(r["tie_groups"]) for r in rules),
        "rules_with_material_tie": len(material_rules),
        "material_tie_rules": material_rules,
        "material_tie_rule_fraction": fraction,
        "ratio_pairs": len(distortions),
        "max_ratio_distortion": max(distortions, default=0.0),
        "median_ratio_distortion": (
            statistics.median(distortions) if distortions else 0.0
        ),
        "promotion_checks": len(promos),
        "promotion_inconsistent": sum(not p["consistent"] for p in promos),
        "hand_rounding_max_deviation": max(hand, default=0.0),
        "hand_rounding_median_deviation": (
            statistics.median(hand) if hand else 0.0
        ),
        "quantization_bound_violations": len(bound_violations),
        "quantization_bound_max_ratio_to_bound": max_bound_slack,
        "smallest_value_rules": smallest,
        "largest_distortion_rules": largest_dist,
        "decision": decision,
        "_bound_violation_detail": bound_violations,
    }


def main() -> int:
    started = time.time()
    blocks = []
    for size in SIZES:
        base.BOARD_SIZE = size
        rules = [base.scan_rule(seed) for seed in SEEDS]
        blocks.append({"aggregate": aggregate(size, rules), "rules": rules})

    decisions = [b["aggregate"]["decision"] for b in blocks]
    if "bound_violated" in decisions:
        overall = "bound_violated"
    elif "defect_at_larger_size" in decisions:
        overall = "defect_at_larger_size"
    elif "coarse_normalization_at_larger_size" in decisions:
        overall = "coarse_normalization_at_larger_size"
    else:
        overall = "ratio_rounding_bounded_persists"

    payload = {
        "role": "DEEPSEEK_AUX",
        "session_id": "4615243a-f2b9-40ce-a634-266bb0b2e3b7",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "plan_sha256": sha256_file(HERE / "plan.json"),
        "base_scan_sha256": sha256_file(BASE_DIR / "scan_profile_normalization.py"),
        "source_sha256": {
            path: sha256_file(ROOT / path) for path in base.SOURCE_FILES
        },
        "git_head": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
        "design": {
            "seeds": list(SEEDS),
            "board_sizes": list(SIZES),
            "setup_preset": "classic_like",
            "hand_weight": base.HAND_WEIGHT,
            "max_static_eval": base.MAX_STATIC_EVAL,
            "material_tie_raw_ratio": base.MATERIAL_TIE_RAW_RATIO,
            "ratio_pair_min_raw_ratio": base.RATIO_PAIR_MIN_RAW_RATIO,
            "search": False,
            "endpoint_implementation": "imported scan_profile_normalization.scan_rule",
            "decision_rule": "any inversion/ceiling clip -> defect_at_larger_size; else material-tie rule fraction >=0.10 -> coarse_normalization_at_larger_size; else ratio_rounding_bounded_persists; any pair outside 0.5*(1/v_min+1/v_max) -> bound_violated",
        },
        "overall_decision": overall,
        "blocks": blocks,
        "nonclaims": [
            "no strength, utility or game-outcome claim",
            "no human-price or external-label fit",
            "one generator family and one fresh seed block per size",
            "a null result at sizes 6 and 8 does not prove preservation for every rule",
        ],
    }
    for block in blocks:
        block["aggregate"].pop("_bound_violation_detail", None)
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    elapsed = time.time() - started
    print(
        json.dumps(
            {
                "out": str(OUT),
                "elapsed_seconds": round(elapsed, 2),
                "overall_decision": overall,
                "per_size": {
                    b["aggregate"]["board_size"]: {
                        k: b["aggregate"][k]
                        for k in (
                            "ordinary_types",
                            "rules_with_inversion",
                            "ceiling_clip_types",
                            "floor_value_1_types",
                            "tie_groups",
                            "ratio_pairs",
                            "max_ratio_distortion",
                            "median_ratio_distortion",
                            "min_normalized_value",
                            "quantization_bound_violations",
                        )
                    }
                    for b in blocks
                },
                "sha256": sha256_file(OUT),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
