"""Does rounding-tie risk grow with the number of ordinary types per rule?

Imports the published endpoint (``scan_profile_normalization.scan_rule``) and
the published aggregation helper unchanged; only ``BOARD_SIZE`` and the
``generate_game`` binding are substituted.  Plan: ``plan.json``.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
BASE_DIR = ROOT / ".local_agent/profile-normalization-20261018"
SCALE_DIR = ROOT / ".local_agent/profile-normalization-scale-20261018"
sys.path.insert(0, str(SCALE_DIR))
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(ROOT))

import scan_profile_normalization as base  # noqa: E402
import scan_profile_scale as scale  # noqa: E402

SEED_BLOCK_SIZE = 120
PLAN = {
    "classic_like": (294001, 294120),
    "bilateral_random": (295001, 295120),
    "free_random": (296001, 296120),
}
BOARD_SIZES = (4, 6, 8)
OUT = HERE / "results_tie_risk.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def tie_rows(rule: dict) -> list[dict]:
    rows = {t["type_id"]: t for t in rule["ordinary_types"]}
    details = []
    for group in rule["tie_groups"]:
        members = [rows[t] for t in group["types"]]
        details.append(
            {
                "seed": rule["seed"],
                "board_value": group["board_value"],
                "types": group["types"],
                "raw_scores": [round(m["raw"], 9) for m in members],
                "raw_ratio": group["raw_ratio"],
                "material": group["material"],
                "same_signature": len({m["signature"] for m in members}) == 1,
            }
        )
    return details


def main() -> int:
    started = time.time()
    original_generate = base.generate_game
    blocks = []
    try:
        for preset, (first, last) in PLAN.items():
            def patched(config, _preset=preset):
                return original_generate(
                    dataclasses.replace(config, setup_preset=_preset)
                )

            base.generate_game = patched
            for board_size in BOARD_SIZES:
                base.BOARD_SIZE = board_size
                rules = [base.scan_rule(seed) for seed in range(first, last + 1)]
                aggregate = scale.aggregate(board_size, rules)
                aggregate["bound_violation_detail"] = aggregate.pop(
                    "_bound_violation_detail", []
                )
                ties = [detail for rule in rules for detail in tie_rows(rule)]
                aggregate["tie_detail"] = ties
                aggregate["tie_groups_from_tie_detail"] = len(ties)
                aggregate["rules_with_tie_detail"] = len(
                    {detail["seed"] for detail in ties}
                )
                aggregate["rules_with_tie_fraction"] = (
                    aggregate["rules_with_tie_detail"] / len(rules)
                )
                aggregate["preset"] = preset
                blocks.append(
                    {
                        "preset": preset,
                        "board_size": board_size,
                        "seed_range": [first, last],
                        "aggregate": aggregate,
                        "rules": rules,
                    }
                )
    finally:
        base.generate_game = original_generate

    by_preset: dict[str, dict[int, dict]] = {}
    for block in blocks:
        by_preset.setdefault(block["preset"], {})[block["board_size"]] = block[
            "aggregate"
        ]

    predictions = {}
    for preset, cells in by_preset.items():
        counts = [cells[size]["tie_groups"] for size in BOARD_SIZES]
        predictions[preset] = {
            "tie_groups_by_size": dict(zip(BOARD_SIZES, counts)),
            "non_decreasing": counts[0] <= counts[1] <= counts[2],
            "strict_4_to_8": counts[2] > counts[0],
            "pair_counts": dict(
                zip(BOARD_SIZES, [cells[size]["ratio_pairs"] for size in BOARD_SIZES])
            ),
        }

    monotone_all = all(p["non_decreasing"] for p in predictions.values())
    strict_some = sum(p["strict_4_to_8"] for p in predictions.values())
    if not monotone_all:
        overall = "tie_risk_not_monotone_in_types_per_rule"
    elif strict_some >= 2:
        overall = "tie_risk_increases_with_types_per_rule"
    else:
        overall = "tie_risk_flat_between_sizes"

    payload = {
        "role": "DEEPSEEK_AUX",
        "session_id": "4615243a-f2b9-40ce-a634-266bb0b2e3b7",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "plan_sha256": sha256_file(HERE / "plan.json"),
        "scan_script_sha256": sha256_file(HERE / "scan_tie_risk.py"),
        "base_scan_sha256": sha256_file(BASE_DIR / "scan_profile_normalization.py"),
        "aggregate_helper_sha256": sha256_file(SCALE_DIR / "scan_profile_scale.py"),
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
            "seed_blocks": {k: list(v) for k, v in PLAN.items()},
            "seeds_per_cell": SEED_BLOCK_SIZE,
            "board_sizes": list(BOARD_SIZES),
            "presets": list(PLAN),
            "hand_weight": base.HAND_WEIGHT,
            "max_static_eval": base.MAX_STATIC_EVAL,
            "material_tie_raw_ratio": base.MATERIAL_TIE_RAW_RATIO,
            "ratio_pair_min_raw_ratio": base.RATIO_PAIR_MIN_RAW_RATIO,
            "search": False,
            "cells": len(PLAN) * len(BOARD_SIZES),
            "rules": len(PLAN) * len(BOARD_SIZES) * SEED_BLOCK_SIZE,
        },
        "predictions": predictions,
        "overall_decision": overall,
        "nonclaims": [
            "no strength, utility or game-outcome claim",
            "no human-price or external-label fit",
            "three presets, three board sizes, one fresh seed block per preset",
            "a tie group is a normalization compression fact, not evidence the pieces are strategically equal",
            "seed blocks are paired across board sizes within a preset but not across presets",
        ],
        "blocks": blocks,
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "elapsed_seconds": round(time.time() - started, 2),
                "overall_decision": overall,
                "predictions": predictions,
                "sha256": sha256_file(OUT),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
