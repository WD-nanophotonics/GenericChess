"""Independent validation of results_profile_normalization.json.

Recomputes every aggregate field from the stored per-rule data and, when a
replay directory is supplied, compares the replay payload to the stored one.
Reads only; never rewrites the stored result.
"""

from __future__ import annotations

import json
import statistics
import sys
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
STORED = HERE / "results_profile_normalization.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def recompute(payload: dict) -> dict:
    rules = payload["rules"]
    distortions = [d["distortion"] for r in rules for d in r["ratio_distortions"]]
    hand = [v for r in rules for v in r["hand_rounding_deviations"]]
    promos = [p for r in rules for p in r["promotion_checks"]]
    material_rules = [r["seed"] for r in rules if r["material_tie_groups"]]

    # Re-derive inversions and distortions straight from the raw rows.
    inv_recomputed = 0
    dist_recomputed: list[float] = []
    tie_recomputed = 0
    signatures: dict[str, list[float]] = {}
    for rule in rules:
        rows = rule["ordinary_types"]
        for left, right in combinations(rows, 2):
            if left["raw"] < right["raw"] and left["board"] > right["board"]:
                inv_recomputed += 1
            if right["raw"] < left["raw"] and right["board"] > left["board"]:
                inv_recomputed += 1
            raw_ratio = max(left["raw"], right["raw"]) / min(left["raw"], right["raw"])
            if raw_ratio >= payload["design"]["ratio_pair_min_raw_ratio"]:
                normalized_ratio = max(left["board"], right["board"]) / min(
                    left["board"], right["board"]
                )
                dist_recomputed.append(abs(normalized_ratio / raw_ratio - 1.0))
        for row in rows:
            signatures.setdefault(row["signature"], []).append(row["raw"])
        by_board: dict[int, list[float]] = {}
        for row in rows:
            by_board.setdefault(row["board"], []).append(row["raw"])
        for values in by_board.values():
            if len({round(v, 12) for v in values}) > 1:
                tie_recomputed += 1

    repeated_signatures = {k: v for k, v in signatures.items() if len(v) > 1}
    signature_mismatches = sum(
        1 for values in repeated_signatures.values() if max(values) - min(values) > 1e-12
    )
    counts = [len(r["ordinary_types"]) for r in rules]
    return {
        "rules": len(rules),
        "ordinary_types": sum(counts),
        "types_per_rule_min": min(counts),
        "types_per_rule_max": max(counts),
        "types_per_rule_uniform": len(set(counts)) == 1,
        "rules_with_inversion": sum(bool(r["inversions"]) for r in rules),
        "inversion_count": sum(len(r["inversions"]) for r in rules),
        "inversion_count_from_rows": inv_recomputed,
        "rules_with_ceiling_clip": sum(bool(r["ceiling_clips"]) for r in rules),
        "ceiling_clip_types": sum(len(r["ceiling_clips"]) for r in rules),
        "rules_with_floor_value_1": sum(bool(r["floor_clips"]) for r in rules),
        "floor_value_1_types": sum(len(r["floor_clips"]) for r in rules),
        "rules_with_any_tie": sum(bool(r["tie_groups"]) for r in rules),
        "tie_groups": sum(len(r["tie_groups"]) for r in rules),
        "tie_groups_from_rows": tie_recomputed,
        "rules_with_material_tie": len(material_rules),
        "material_tie_rules": material_rules,
        "material_tie_groups": sum(len(r["material_tie_groups"]) for r in rules),
        "material_tie_rule_fraction": len(material_rules) / len(rules),
        "ratio_pairs": sum(len(r["ratio_distortions"]) for r in rules),
        "ratio_pairs_from_rows": len(dist_recomputed),
        "repeated_movement_signatures": len(repeated_signatures),
        "signature_raw_mismatches": signature_mismatches,
        "max_ratio_distortion": max(distortions, default=0.0),
        "max_ratio_distortion_from_rows": max(dist_recomputed, default=0.0),
        "median_ratio_distortion": statistics.median(distortions) if distortions else 0.0,
        "median_ratio_distortion_from_rows": (
            statistics.median(dist_recomputed) if dist_recomputed else 0.0
        ),
        "hand_rounding_max_deviation": max(hand, default=0.0),
        "hand_rounding_median_deviation": (
            statistics.median(hand) if hand else 0.0
        ),
        "promotion_checks": len(promos),
        "promotion_inconsistent": sum(not p["consistent"] for p in promos),
        "decision": payload["aggregate"]["decision"],
    }


def decision_of(agg: dict, design: dict) -> str:
    if agg["inversion_count"] or agg["ceiling_clip_types"]:
        return "defect_detected"
    if agg["material_tie_rule_fraction"] >= 0.10:
        return "coarse_normalization_supported"
    return "ratio_rounding_bounded"


def parse_args(argv: list[str]) -> tuple[Path, Path | None]:
    """Accept an optional ``--stored`` result path and a positional replay path."""
    stored = STORED
    replay = None
    args = list(argv[1:])
    while args:
        arg = args.pop(0)
        if arg == "--stored":
            stored = Path(args.pop(0))
        else:
            replay = Path(arg)
    return stored, replay


def main(argv: list[str]) -> int:
    stored_path, replay_path = parse_args(argv)
    stored = load(stored_path)
    agg = recompute(stored)
    problems: list[str] = []

    for key, value in agg.items():
        if key in ("material_tie_rules", "ratio_pairs_from_rows"):
            continue
        if key in stored["aggregate"] and stored["aggregate"][key] != value:
            problems.append(f"{key}: stored={stored['aggregate'][key]!r} recomputed={value!r}")

    if agg["inversion_count"] != agg["inversion_count_from_rows"]:
        problems.append("inversion bookkeeping disagrees with row-level recomputation")
    if agg["tie_groups"] != agg["tie_groups_from_rows"]:
        problems.append("tie bookkeeping disagrees with row-level recomputation")
    if agg["ratio_pairs"] != agg["ratio_pairs_from_rows"]:
        problems.append("ratio-pair bookkeeping disagrees with row-level recomputation")
    if agg["signature_raw_mismatches"] != len(stored.get("signature_mismatches", [])):
        problems.append("stored signature_mismatches list disagrees with the recomputed count")
    if agg["decision"] != decision_of(agg, stored["design"]):
        problems.append("stored decision does not follow the pre-written rule")
    if stored.get("plan_sha256") != (
        "eeadd8ca8f5c42f05f78d1f5bbecf734193ec1525b2156c7e172330611894c64"
    ):
        problems.append("plan hash on the stored result is not the pre-run plan hash")

    replay_report = None
    if replay_path is not None:
        replay = load(replay_path)
        same_rules = replay["rules"] == stored["rules"]
        same_agg = replay["aggregate"] == stored["aggregate"]
        same_sources = replay["source_sha256"] == stored["source_sha256"]
        same_plan = replay["plan_sha256"] == stored["plan_sha256"]
        replay_report = {
            "replay_path": str(replay_path),
            "rules_identical": same_rules,
            "aggregate_identical": same_agg,
            "source_hashes_identical": same_sources,
            "plan_hash_identical": same_plan,
        }
        if not (same_rules and same_agg and same_sources):
            problems.append("deterministic replay differs from the stored result")

    print(json.dumps(
        {
            "recomputed": agg,
            "types_per_rule": [agg["types_per_rule_min"], agg["types_per_rule_max"], agg["types_per_rule_uniform"]],
            "replay": replay_report,
            "problems": problems,
            "ok": not problems,
        },
        indent=1,
    ))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
