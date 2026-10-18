"""Secondary analysis of published profile evidence: cross-rule scale.

NOT pre-registered.  This is an exploratory reanalysis of the two published
result files, run after seeing them.  It generates nothing and searches
nothing; it reads stored ordinary-type raw scores and reports the per-rule raw
median that ``build_ruleset_profile`` divides by before rounding.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[3]
DATA = ROOT / "docs/research/data"
BOARD4 = DATA / "profile_normalization_20261018/results_profile_normalization.json"
SCALE68 = DATA / "profile_normalization_scale_20261018/results_profile_scale.json"
OUT = HERE / "results_cross_rule_scale.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarise(size: str, rules: list[dict]) -> dict:
    medians = sorted(
        statistics.median(t["raw"] for t in rule["ordinary_types"]) for rule in rules
    )
    n = len(medians)
    return {
        "board_size": size,
        "rules": n,
        "raw_median_min": medians[0],
        "raw_median_p25": medians[n // 4],
        "raw_median_p50": statistics.median(medians),
        "raw_median_p75": medians[3 * n // 4],
        "raw_median_max": medians[-1],
        "max_over_min": medians[-1] / medians[0],
        "p75_over_p25": medians[3 * n // 4] / medians[n // 4],
        "normalized_median_is": 1000,
    }


def main() -> int:
    board4 = json.loads(BOARD4.read_text(encoding="utf-8"))
    scale68 = json.loads(SCALE68.read_text(encoding="utf-8"))
    blocks = [summarise("4", board4["rules"])]
    blocks += [
        summarise(str(block["aggregate"]["board_size"]), block["rules"])
        for block in scale68["blocks"]
    ]
    payload = {
        "role": "DEEPSEEK_AUX",
        "status": "secondary_post_hoc_analysis_not_pre_registered",
        "session_id": "4615243a-f2b9-40ce-a634-266bb0b2e3b7",
        "source_files": {
            "board4_result_sha256": sha256(BOARD4),
            "scale68_result_sha256": sha256(SCALE68),
        },
        "blocks": blocks,
        "interpretation_limits": [
            "raw capability units are not semantically identical across rules, because the movement atoms and their weights differ",
            "the measurement shows only how much per-rule scale the median normalization removes",
            "no new rules were generated, so this adds no independent sample",
            "no strength, utility or human-price claim",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
