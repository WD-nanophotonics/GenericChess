"""Post-hoc verification of one source-level observation made during the A4 run.

While reading the A4 near-zone cases (placements whose empty-board forward
mobility reaches the promotion zone) the served promotion score stayed 0 in
every one.  The A4 plan did not predict this; it is recorded here as a separate
post-hoc verification with a fixed endpoint, not as part of the A4 decision.

Claim under test: in ``Evaluator._promotion_bonus`` the forward-adjacency branch
compares ``Square`` objects taken from ``empty_forward_mobility`` against
``self._zones`` entries, which are integer board indices, so that branch cannot
fire.

Endpoint, per (rule, owner, promotable base type with positive gain):
  * element type of ``empty_forward_mobility[base][owner][idx]``
  * element type of ``_zones[(base, owner)]``
  * number of (square, target) pairs whose membership test is True exactly as
    coded, and the number that would be True if the target were converted to a
    board index first
  * the number of placements that would receive the half bonus under each

No search, no evaluation of positions beyond the branch arithmetic, no learning.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import scan_profile_transform as base  # noqa: E402

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.core.coordinates import Square  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

OUT = HERE / "results_half_bonus_branch.json"
SEEDS = base.SEEDS
SIZES = base.SIZES


def scan_rule(seed: int, size: int) -> dict:
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
    )
    compiled = game.compiled_ruleset
    config = EvaluationConfig(hand_weight=base.HAND_WEIGHT)
    profile = build_ruleset_profile(compiled, config)
    evaluator = Evaluator(compiled, profile, config)
    n = compiled.board_size

    records = []
    for pt in compiled.piece_types:
        if not pt.is_promotable:
            continue
        gain = profile.promotion_gain_by_type.get(pt.type_id, 0)
        if gain <= 0:
            continue
        for owner in (0, 1):
            zone = evaluator._zones.get((pt.type_id, owner))
            if zone is None:
                records.append(
                    {
                        "base_type": pt.type_id,
                        "owner": owner,
                        "status": "no_zone",
                        "gain": gain,
                    }
                )
                continue
            forward = compiled.empty_forward_mobility[pt.type_id][owner]
            sample_entry = next(
                (forward[idx][0] for idx in range(n * n) if forward[idx]), None
            )
            sample_zone = next(iter(zone), None)
            as_coded = 0
            as_index = 0
            near_squares_coded = 0
            near_squares_index = 0
            for idx in range(n * n):
                if idx in zone:
                    continue
                coded_hit = any(target in zone for target in forward[idx])
                index_hit = any(
                    (target.rank * n + target.file) in zone for target in forward[idx]
                )
                as_coded += coded_hit
                as_index += index_hit
                near_squares_coded += coded_hit
                near_squares_index += index_hit
            records.append(
                {
                    "base_type": pt.type_id,
                    "owner": owner,
                    "status": "ok",
                    "gain": gain,
                    "unit": max(1, gain // 1000),
                    "zone_squares": len(zone),
                    "forward_entry_type": type(sample_entry).__name__,
                    "zone_element_type": type(sample_zone).__name__,
                    "coded_target_membership_hits": as_coded,
                    "index_converted_target_membership_hits": as_index,
                    "squares_receiving_half_bonus_as_coded": near_squares_coded,
                    "squares_receiving_half_bonus_if_index_converted": near_squares_index,
                }
            )
    return {"seed": seed, "board_size": size, "records": records}


def decide(rules: list[dict]) -> dict:
    records = [
        record
        for rule in rules
        for record in rule["records"]
        if record["status"] == "ok"
    ]
    entry_types = sorted({record["forward_entry_type"] for record in records})
    zone_types = sorted({record["zone_element_type"] for record in records})
    coded = sum(record["coded_target_membership_hits"] for record in records)
    converted = sum(
        record["index_converted_target_membership_hits"] for record in records
    )
    coded_squares = sum(
        record["squares_receiving_half_bonus_as_coded"] for record in records
    )
    converted_squares = sum(
        record["squares_receiving_half_bonus_if_index_converted"] for record in records
    )
    if coded == 0 and converted > 0:
        decision = "forward_adjacency_half_bonus_branch_cannot_fire_as_coded"
    elif coded > 0:
        decision = "branch_is_reachable_as_coded"
    else:
        decision = "no_rule_exercises_the_branch_either_way"
    return {
        "decision": decision,
        "records": len(records),
        "distinct_forward_entry_types": entry_types,
        "distinct_zone_element_types": zone_types,
        "target_membership_hits_as_coded": coded,
        "target_membership_hits_if_index_converted": converted,
        "squares_receiving_half_bonus_as_coded": coded_squares,
        "squares_receiving_half_bonus_if_index_converted": converted_squares,
        "records_with_unreachable_branch": sum(
            1
            for record in records
            if record["coded_target_membership_hits"] == 0
            and record["index_converted_target_membership_hits"] > 0
        ),
    }


def main() -> int:
    started = time.time()
    rules = [scan_rule(seed, size) for size in SIZES for seed in SEEDS]
    verdict = decide(rules)
    payload = {
        "role": "DEEPSEEK_AUX",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provenance": "post-hoc verification of an observation made while reading the A4 near-zone cases; written after the A4 run and labelled as such in the report",
        "source_sha256": {
            path: base.sha256_file(ROOT / path)
            for path in (
                "generic_chess/ai/evaluation/evaluator.py",
                "generic_chess/rules/compiler.py",
                "generic_chess/core/coordinates.py",
            )
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
            "endpoint": "count of forward-target membership tests that are True as coded versus after converting the target to a board index",
            "square_type_reference": Square.__module__ + "." + Square.__qualname__,
        },
        "verdict": verdict,
        "rules": rules,
        "nonclaims": [
            "no search and no strength, utility or outcome claim",
            "this records an unreachable evaluation branch, not a validated defect report or a proposed repair",
            "one generator family, square boards 6 and 8, 40 seeds",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "elapsed_seconds": round(time.time() - started, 2),
                **{k: v for k, v in verdict.items()},
                "sha256": base.sha256_file(OUT),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
