"""POST-HOC: which stored near-equal pairs actually become rounding ties?

Reads the already-written ``results_tie_risk.json`` and recomputes the exact
normalized values from the stored raw scores.  No rule is generated, no search
is run and no published cell is rerun.  Plan: ``plan_posthoc.json``.

Two quantities are distinguished:

* raw ratio  -- scale-free closeness of two capability scores;
* normalized gap ``|round-target difference|`` -- the actual distance to the
  unit rounding grid, which is what can produce a collision.

A tie is only reachable when the exact normalized gap is below 1.0, so the
interesting quantity is the per-rule nearest distinct gap ("headroom").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "generic_chess").is_dir():
            return candidate
    raise SystemExit(f"no checkout containing generic_chess above {start}")


ROOT = find_root(HERE)
RESULTS = HERE / "results_tie_risk.json"
OUT = HERE / "results_gap_headroom.json"

sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import MAX_STATIC_EVAL  # noqa: E402

SCALE = 1000  # EvaluationConfig().normal_piece_median_value default
NEAR_EQUAL_RAW_RATIO = 1.001


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def rule_pairs(rule: dict) -> tuple[dict, list[dict]]:
    rows = rule["ordinary_types"]
    raws = [row["raw"] for row in rows]
    median_raw = median(raws)
    recon = {}
    for row in rows:
        exact = SCALE * row["raw"] / median_raw if median_raw > 0 else 1.0
        recon[row["type_id"]] = {
            "exact": exact,
            "board": max(1, min(int(round(exact)), MAX_STATIC_EVAL)),
            "stored": row["board"],
            "signature": row["signature"],
        }
    mismatches = sum(1 for v in recon.values() if v["board"] != v["stored"])

    pairs = []
    for left_id, right_id in combinations(recon, 2):
        left, right = recon[left_id], recon[right_id]
        distinct_capability = left["signature"] != right["signature"]
        distinct_raw = abs(left["exact"] - right["exact"]) > 1e-9
        low, high = sorted((left["exact"], right["exact"]))
        pairs.append(
            {
                "pair": sorted([left_id, right_id]),
                "raw_ratio": high / low if low > 0 else float("inf"),
                "exact_gap": high - low,
                "exact_low": low,
                "exact_high": high,
                "tied": left["board"] == right["board"] and distinct_raw,
                "distinct_capability": distinct_capability,
                "distinct_raw": distinct_raw,
            }
        )
    return {"reconstruction_mismatches": mismatches}, pairs


def bucket(gap: float) -> str:
    if gap < 1.0:
        return "<1.0"
    if gap < 2.0:
        return "1.0-2.0"
    if gap < 5.0:
        return "2.0-5.0"
    if gap < 20.0:
        return "5.0-20.0"
    return ">=20.0"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="omit the per-pair arrays; keeps every aggregate and distribution",
    )
    args = parser.parse_args(argv)
    results_path = args.results if args.results.exists() else RESULTS

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    cells = []
    reconstruction_mismatches = 0
    for block in payload["blocks"]:
        cell_pairs: list[dict] = []
        rules_with_distinct_pair = 0
        nearest_gaps: list[float] = []
        nearest_ratios: list[float] = []
        for rule in block["rules"]:
            check, pairs = rule_pairs(rule)
            reconstruction_mismatches += check["reconstruction_mismatches"]
            distinct = [p for p in pairs if p["distinct_capability"]]
            for pair in distinct:
                pair["seed"] = rule["seed"]
                cell_pairs.append(pair)
            if distinct:
                rules_with_distinct_pair += 1
                nearest_gaps.append(min(p["exact_gap"] for p in distinct))
                nearest_ratios.append(min(p["raw_ratio"] for p in distinct))

        near = [p for p in cell_pairs if p["raw_ratio"] <= NEAR_EQUAL_RAW_RATIO]
        near_tied = [p for p in near if p["tied"]]
        reachable = [p for p in cell_pairs if p["exact_gap"] < 1.0]
        reachable_tied = [p for p in reachable if p["tied"]]
        tied_all = [p for p in cell_pairs if p["tied"]]
        near_scale = {
            "min_exact_low": min((p["exact_low"] for p in near), default=None),
            "median_exact_low": (
                statistics.median([p["exact_low"] for p in near]) if near else None
            ),
            "max_exact_high": max((p["exact_high"] for p in near), default=None),
        }
        reachable_ids = {id(p) for p in reachable}
        near_ids = {id(p) for p in near}
        reachable_equal_score = [p for p in reachable if not p["distinct_raw"]]
        reachable_distinct_score = [p for p in reachable if p["distinct_raw"]]
        reachable_distinct_tied = [p for p in reachable_distinct_score if p["tied"]]
        by_bucket: dict[str, dict[str, int]] = {}
        for pair in cell_pairs:
            entry = by_bucket.setdefault(bucket(pair["exact_gap"]), {"pairs": 0, "tied": 0})
            entry["pairs"] += 1
            entry["tied"] += int(pair["tied"])

        cells.append(
            {
                "preset": block["preset"],
                "board_size": block["board_size"],
                "rules": len(block["rules"]),
                "rules_with_distinct_capability_pair": rules_with_distinct_pair,
                "distinct_capability_pairs": len(cell_pairs),
                "tied_pairs": len(tied_all),
                "tied_without_distinct_signature": sum(
                    1 for p in tied_all if not p["distinct_capability"]
                ),
                "raw_ratio_le_1.001_pairs": len(near),
                "raw_ratio_le_1.001_tied": len(near_tied),
                "exact_gap_lt_1_pairs": len(reachable),
                "exact_gap_lt_1_tied": len(reachable_tied),
                "exact_gap_lt_1_escaped_adjacent": len(reachable) - len(reachable_tied),
                "gap_lt_1_equal_score_pairs": len(reachable_equal_score),
                "gap_lt_1_distinct_score_pairs": len(reachable_distinct_score),
                "gap_lt_1_distinct_score_tied": len(reachable_distinct_tied),
                "gap_lt_1_adjacent_escapes_distinct_score": (
                    len(reachable_distinct_score) - len(reachable_distinct_tied)
                ),
                "tied_pairs_outside_gap_lt_1": len(tied_all) - len(reachable_tied),
                "near_pair_value_scale": near_scale,
                "gap_lt_1_but_raw_ratio_gt_1.001": len(reachable_ids - near_ids),
                "raw_ratio_le_1.001_but_gap_ge_1": len(near_ids - reachable_ids),
                "distinct_signature_zero_gap_pairs": sum(
                    1
                    for p in cell_pairs
                    if p["distinct_capability"] and not p["distinct_raw"]
                ),
                "gap_buckets": dict(sorted(by_bucket.items())),
                "nearest_gap": {
                    "min": min(nearest_gaps) if nearest_gaps else None,
                    "median": statistics.median(nearest_gaps) if nearest_gaps else None,
                    "max": max(nearest_gaps) if nearest_gaps else None,
                    "rules_below_1": sum(1 for g in nearest_gaps if g < 1.0),
                    "rules_below_2": sum(1 for g in nearest_gaps if g < 2.0),
                },
                "nearest_raw_ratio": {
                    "min": min(nearest_ratios) if nearest_ratios else None,
                    "median": statistics.median(nearest_ratios) if nearest_ratios else None,
                    "max": max(nearest_ratios) if nearest_ratios else None,
                },
                "pairs": cell_pairs,
            }
        )

    pooled = {}
    for size in (4, 6, 8):
        rows = [c for c in cells if c["board_size"] == size]
        near = sum(c["raw_ratio_le_1.001_pairs"] for c in rows)
        near_tied = sum(c["raw_ratio_le_1.001_tied"] for c in rows)
        reach = sum(c["exact_gap_lt_1_pairs"] for c in rows)
        reach_tied = sum(c["exact_gap_lt_1_tied"] for c in rows)
        pooled[str(size)] = {
            "raw_ratio_le_1.001_pairs": near,
            "raw_ratio_le_1.001_tied": near_tied,
            "raw_ratio_conversion": near_tied / near if near else None,
            "exact_gap_lt_1_pairs": reach,
            "exact_gap_lt_1_tied": reach_tied,
            "exact_gap_conversion": reach_tied / reach if reach else None,
            "tied_pairs": sum(c["tied_pairs"] for c in rows),
        }

    result = {
        "role": "DEEPSEEK_AUX",
        "session_id": payload["session_id"],
        "analysis_status": "POST_HOC_EXPLORATORY",
        "registered": False,
        "note": (
            "Not pre-registered. Derived from the stored results_tie_risk.json after "
            "that run closed; no rule generated, no seed/threshold retuned, no cell rerun."
        ),
        "source_results_sha256": sha256_file(results_path),
        "analysis_script_sha256": sha256_file(Path(__file__)),
        "pair_detail_included": not args.summary_only,
        "plan_posthoc_sha256": (
            sha256_file(HERE / "plan_posthoc.json")
            if (HERE / "plan_posthoc.json").exists()
            else None
        ),
        "method": {
            "scale": SCALE,
            "near_equal_raw_ratio": NEAR_EQUAL_RAW_RATIO,
            "exact_reconstruction": "exact = 1000 * raw / median(raw over ordinary types); "
            "board = max(1, min(round(exact), MAX_STATIC_EVAL))",
            "tie_definition": "equal stored board value with distinct raw scores",
            "capability_distinction": "movement signature differs",
            "necessary_condition": "a tie implies exact_gap < 1.0 (two values rounding to "
            "the same integer differ by less than one grid unit)",
        },
        "reconstruction_mismatches": reconstruction_mismatches,
        "pooled_by_board_size": pooled,
        "cells": cells,
        "nonclaims": [
            "no strength, utility or game-outcome claim",
            "movement signatures are the generator's own capability encoding, not a strategic-equivalence proof",
            "raw-ratio closeness is not a price statement",
            "post-hoc: no hypothesis test was pre-registered for these conversions",
        ],
    }
    if args.summary_only:
        for cell in result["cells"]:
            cell.pop("pairs", None)
    args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    summary = {
        "out": str(args.out),
        "sha256": sha256_file(args.out),
        "reconstruction_mismatches": reconstruction_mismatches,
        "pooled_by_board_size": pooled,
    }
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
