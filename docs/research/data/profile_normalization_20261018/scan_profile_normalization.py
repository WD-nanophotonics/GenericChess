"""Zero-search audit of static-profile normalization across generated rules.

Plan: ``plan.json`` (written before this run).  No product code is modified.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
import sys
import time
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import (  # noqa: E402
    MAX_STATIC_EVAL,
    EvaluationConfig,
)
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

SEEDS = tuple(range(291001, 291041))
BOARD_SIZE = 4
HAND_WEIGHT = 0.9
MATERIAL_TIE_RAW_RATIO = 1.10
RATIO_PAIR_MIN_RAW_RATIO = 1.05
OUT = HERE / "results_profile_normalization.json"
SOURCE_FILES = (
    "generic_chess/ai/evaluation/config.py",
    "generic_chess/ai/evaluation/profile.py",
    "generic_chess/generation/generator.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def scan_rule(seed: int) -> dict:
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=BOARD_SIZE, setup_preset="classic_like")
    )
    compiled = game.compiled_ruleset
    config = EvaluationConfig(hand_weight=HAND_WEIGHT)
    profile = build_ruleset_profile(compiled, config)

    ordinary = [
        pt.type_id
        for pt in compiled.piece_types
        if not pt.is_anchor and pt.type_id in profile.board_value_by_type
    ]
    rows = []
    for type_id in ordinary:
        piece_profile = profile.piece_profiles[type_id]
        rows.append(
            {
                "type_id": type_id,
                "raw": float(piece_profile.raw_capability_score),
                "board": int(profile.board_value_by_type[type_id]),
                "hand": int(profile.hand_value_by_base_type[type_id]),
                "signature": json.dumps(
                    piece_profile.movement_signature,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            }
        )

    ceiling = [r["type_id"] for r in rows if r["board"] >= MAX_STATIC_EVAL]
    floor = [r["type_id"] for r in rows if r["board"] == 1]

    inversions = []
    ratio_distortions = []
    for left, right in combinations(rows, 2):
        raw_ratio = max(left["raw"], right["raw"]) / min(left["raw"], right["raw"])
        if left["raw"] < right["raw"] and left["board"] > right["board"]:
            inversions.append([left["type_id"], right["type_id"]])
        if right["raw"] < left["raw"] and right["board"] > left["board"]:
            inversions.append([right["type_id"], left["type_id"]])
        if raw_ratio >= RATIO_PAIR_MIN_RAW_RATIO:
            normalized_ratio = max(left["board"], right["board"]) / min(
                left["board"], right["board"]
            )
            ratio_distortions.append(
                {
                    "pair": sorted([left["type_id"], right["type_id"]]),
                    "raw_ratio": raw_ratio,
                    "normalized_ratio": normalized_ratio,
                    "distortion": abs(normalized_ratio / raw_ratio - 1.0),
                }
            )

    by_board: dict[int, list[dict]] = {}
    for row in rows:
        by_board.setdefault(row["board"], []).append(row)
    tie_groups = []
    for board_value, group in sorted(by_board.items()):
        raw_values = {round(row["raw"], 12) for row in group}
        if len(raw_values) > 1:
            raw_ratio = max(raw_values) / min(raw_values)
            tie_groups.append(
                {
                    "board_value": board_value,
                    "types": sorted(row["type_id"] for row in group),
                    "raw_ratio": raw_ratio,
                    "material": raw_ratio >= MATERIAL_TIE_RAW_RATIO,
                }
            )

    hand_rounding = [
        abs(row["hand"] / row["board"] - HAND_WEIGHT)
        for row in rows
        if row["board"] > 0
    ]
    promotion_checks = []
    for pt in compiled.piece_types:
        if not pt.is_promotable:
            continue
        source = profile.board_value_by_type.get(pt.type_id)
        targets = [
            profile.board_value_by_type[t]
            for t in pt.promotion_target_ids
            if t in profile.board_value_by_type
        ]
        expected = max(0, (max(targets) if targets else 0) - source)
        actual = profile.promotion_gain_by_type.get(pt.type_id)
        promotion_checks.append(
            {
                "type_id": pt.type_id,
                "targets": list(pt.promotion_target_ids),
                "expected_gain": expected,
                "actual_gain": actual,
                "consistent": expected == actual,
            }
        )

    return {
        "seed": seed,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "ordinary_types": rows,
        "ceiling_clips": ceiling,
        "floor_clips": floor,
        "inversions": inversions,
        "tie_groups": tie_groups,
        "material_tie_groups": [g for g in tie_groups if g["material"]],
        "ratio_distortions": ratio_distortions,
        "max_ratio_distortion": max(
            (d["distortion"] for d in ratio_distortions), default=0.0
        ),
        "hand_rounding_deviations": hand_rounding,
        "promotion_checks": promotion_checks,
    }


def main() -> int:
    started = time.time()
    rules = [scan_rule(seed) for seed in SEEDS]

    signatures: dict[str, list[tuple[int, str, float]]] = {}
    for rule in rules:
        for row in rule["ordinary_types"]:
            signatures.setdefault(row["signature"], []).append(
                (rule["seed"], row["type_id"], row["raw"])
            )
    repeated_signatures = {k: v for k, v in signatures.items() if len(v) > 1}
    signature_mismatches = []
    for signature, entries in repeated_signatures.items():
        raws = [raw for _, _, raw in entries]
        if max(raws) - min(raws) > 1e-12:
            signature_mismatches.append(
                {
                    "signature": signature,
                    "entries": [[seed, type_id, raw] for seed, type_id, raw in entries],
                }
            )

    material_tie_rules = [r["seed"] for r in rules if r["material_tie_groups"]]
    total_types = sum(len(r["ordinary_types"]) for r in rules)
    total_pairs = sum(len(r["ratio_distortions"]) for r in rules)
    distortions = [d["distortion"] for r in rules for d in r["ratio_distortions"]]
    hand_deviations = [
        value for r in rules for value in r["hand_rounding_deviations"]
    ]
    promotions = [p for r in rules for p in r["promotion_checks"]]
    any_inversion = any(r["inversions"] for r in rules)
    any_ceiling = any(r["ceiling_clips"] for r in rules)
    material_tie_rule_fraction = len(material_tie_rules) / len(rules)

    if any_inversion or any_ceiling:
        decision = "defect_detected"
    elif material_tie_rule_fraction >= 0.10:
        decision = "coarse_normalization_supported"
    else:
        decision = "ratio_rounding_bounded"

    payload = {
        "role": "DEEPSEEK_AUX",
        "session_id": "4615243a-f2b9-40ce-a634-266bb0b2e3b7",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "plan_sha256": sha256_file(HERE / "plan.json"),
        "source_sha256": {
            path: sha256_file(ROOT / path) for path in SOURCE_FILES
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
            "setup_preset": "classic_like",
            "hand_weight": HAND_WEIGHT,
            "max_static_eval": MAX_STATIC_EVAL,
            "material_tie_raw_ratio": MATERIAL_TIE_RAW_RATIO,
            "ratio_pair_min_raw_ratio": RATIO_PAIR_MIN_RAW_RATIO,
            "search": False,
            "decision_rule": "any inversion or ceiling clip -> defect_detected; else material-tie rule fraction >=0.10 -> coarse_normalization_supported; else ratio_rounding_bounded",
        },
        "aggregate": {
            "rules": len(rules),
            "ordinary_types": total_types,
            "rules_with_inversion": sum(bool(r["inversions"]) for r in rules),
            "inversion_count": sum(len(r["inversions"]) for r in rules),
            "rules_with_ceiling_clip": sum(bool(r["ceiling_clips"]) for r in rules),
            "ceiling_clip_types": sum(len(r["ceiling_clips"]) for r in rules),
            "rules_with_floor_value_1": sum(bool(r["floor_clips"]) for r in rules),
            "floor_value_1_types": sum(len(r["floor_clips"]) for r in rules),
            "rules_with_any_tie": sum(bool(r["tie_groups"]) for r in rules),
            "tie_groups": sum(len(r["tie_groups"]) for r in rules),
            "rules_with_material_tie": len(material_tie_rules),
            "material_tie_rules": material_tie_rules,
            "material_tie_groups": sum(
                len(r["material_tie_groups"]) for r in rules
            ),
            "material_tie_rule_fraction": material_tie_rule_fraction,
            "ratio_pairs": total_pairs,
            "max_ratio_distortion": max(distortions, default=0.0),
            "median_ratio_distortion": (
                statistics.median(distortions) if distortions else 0.0
            ),
            "repeated_movement_signatures": len(repeated_signatures),
            "signature_raw_mismatches": len(signature_mismatches),
            "hand_rounding_max_deviation": max(hand_deviations, default=0.0),
            "hand_rounding_median_deviation": (
                statistics.median(hand_deviations) if hand_deviations else 0.0
            ),
            "promotion_checks": len(promotions),
            "promotion_inconsistent": sum(not p["consistent"] for p in promotions),
            "decision": decision,
        },
        "signature_mismatches": signature_mismatches,
        "rules": rules,
        "nonclaims": [
            "no strength, utility or game-outcome claim",
            "no human-price or external-label fit",
            "one generator family, board size 4 and one fixed seed block",
            "clipping and tie counts are descriptive, not a threshold for product use",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    elapsed = time.time() - started
    print(json.dumps({"out": str(OUT), "elapsed_seconds": round(elapsed, 2), "decision": decision, "sha256": sha256_file(OUT)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
