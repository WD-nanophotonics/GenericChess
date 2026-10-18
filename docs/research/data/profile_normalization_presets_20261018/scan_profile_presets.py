"""Preset generalization scan: profile normalization under other setups.

Imports the published endpoint implementation unchanged and only substitutes
``setup_preset`` through ``dataclasses.replace``, and reuses the published
aggregation helper from the board-size scan.  Plan: ``plan.json``.
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

SEEDS = tuple(range(293001, 293041))
PRESETS = ("bilateral_random", "free_random")
BOARD_SIZE = 8
OUT = HERE / "results_profile_presets.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def tie_details(rules: list[dict]) -> list[dict]:
    details = []
    for rule in rules:
        rows = {t["type_id"]: t for t in rule["ordinary_types"]}
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
        for preset in PRESETS:
            def patched(config, _preset=preset):
                return original_generate(
                    dataclasses.replace(config, setup_preset=_preset)
                )

            base.generate_game = patched
            base.BOARD_SIZE = BOARD_SIZE
            rules = [base.scan_rule(seed) for seed in SEEDS]
            aggregate = scale.aggregate(BOARD_SIZE, rules)
            aggregate.pop("board_size", None)
            aggregate["bound_violation_detail"] = aggregate.pop(
                "_bound_violation_detail", []
            )
            aggregate["preset"] = preset
            aggregate["tie_detail"] = tie_details(rules)
            aggregate["tie_groups_with_identical_signature"] = sum(
                1 for d in aggregate["tie_detail"] if d["same_signature"]
            )
            blocks.append({"aggregate": aggregate, "rules": rules})
    finally:
        base.generate_game = original_generate

    decisions = [b["aggregate"]["decision"] for b in blocks]
    if "bound_violated" in decisions:
        overall = "bound_violated"
    elif "defect_at_larger_size" in decisions:
        overall = "defect_at_other_presets"
    elif "coarse_normalization_at_larger_size" in decisions:
        overall = "coarse_normalization_at_other_presets"
    else:
        overall = "ratio_rounding_bounded_persists_at_other_presets"

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
            "board_size": BOARD_SIZE,
            "setup_presets": list(PRESETS),
            "hand_weight": base.HAND_WEIGHT,
            "max_static_eval": base.MAX_STATIC_EVAL,
            "material_tie_raw_ratio": base.MATERIAL_TIE_RAW_RATIO,
            "ratio_pair_min_raw_ratio": base.RATIO_PAIR_MIN_RAW_RATIO,
            "search": False,
            "endpoint_implementation": "imported scan_profile_normalization.scan_rule with preset-substituted generate_game",
            "decision_rule": "any inversion/ceiling clip -> defect_at_other_presets; else material-tie rule fraction >=0.10 -> coarse_normalization_at_other_presets; else ratio_rounding_bounded_persists_at_other_presets; any pair outside 0.5*(1/v_min+1/v_max) -> bound_violated",
        },
        "overall_decision": overall,
        "blocks": blocks,
        "nonclaims": [
            "no strength, utility or game-outcome claim",
            "no human-price or external-label fit",
            "two presets, one board size, one fresh seed block",
            "a tie group is a normalization compression fact, not evidence the pieces are strategically equal",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "elapsed_seconds": round(time.time() - started, 2),
                "overall_decision": overall,
                "per_preset": {
                    b["aggregate"]["preset"]: {
                        k: b["aggregate"][k]
                        for k in (
                            "ordinary_types",
                            "rules_with_inversion",
                            "ceiling_clip_types",
                            "tie_groups",
                            "rules_with_material_tie",
                            "ratio_pairs",
                            "max_ratio_distortion",
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
