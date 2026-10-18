"""Why exactly 3 points disappear after the A3 rotation (post-hoc).

A4 measured delta = -/+3 in every in-zone case while the rotated promotion
zone is the whole board.  This script checks the arithmetic reason: with a
whole-board zone every non-promoted promotable piece carries the full
``weight * unit`` bonus, so the term only depends on the *count difference*
between the two owners.  When both owners hold the same number of such
pieces the term is a constant and the relocated piece contributes nothing.

No search, no position sampling beyond the initial boards, no new seeds.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import scan_profile_transform as base  # noqa: E402
import scan_profile_transform_a3 as a3  # noqa: E402

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402
from generic_chess.rules.compiler import compile_ruleset  # noqa: E402
from generic_chess.core.transition import initial_state  # noqa: E402

OUT = HERE / "results_promotion_cancellation.json"
AFFECTED = {
    (292009, 6), (292009, 8), (292015, 6), (292015, 8), (292021, 6), (292021, 8),
    (292023, 8), (292026, 8), (292028, 6), (292028, 8), (292032, 6), (292032, 8),
}


def counts(state, profile, compiled) -> dict:
    out = {0: 0, 1: 0}
    for piece in state.position.board:
        if piece is None or piece.promoted:
            continue
        if profile.promotion_gain_by_type.get(piece.base_type_id, 0) > 0:
            out[piece.owner] += 1
    return out


def main() -> int:
    started = time.time()
    config = EvaluationConfig(hand_weight=base.HAND_WEIGHT)
    records = []
    for seed, size in sorted(AFFECTED):
        game = generate_game(
            GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
        )
        rr, _ = a3.transform_a3(game.ruleset)
        rc = compile_ruleset(rr)
        po = build_ruleset_profile(game.compiled_ruleset, config)
        pr = build_ruleset_profile(rc, config)
        so = initial_state(game.compiled_ruleset)
        sr = initial_state(rc)
        co = counts(so, po, game.compiled_ruleset)
        cr = counts(sr, pr, rc)
        eo = Evaluator(game.compiled_ruleset, po, config)
        er = Evaluator(rc, pr, config)
        full_o = eo.evaluate(so)
        full_r = er.evaluate(sr)
        records.append(
            {
                "seed": seed,
                "board_size": size,
                "promotable_counts_original": co,
                "promotable_counts_rotated": cr,
                "rotated_zone_is_whole_board": all(
                    len(zone) == size * size for zone in er._zones.values()
                ),
                "rotated_promotion_term_by_owner": {
                    owner: sum(
                        er._promotion_bonus(piece, idx)
                        for idx, piece in enumerate(sr.position.board)
                        if piece is not None and piece.owner == owner
                    )
                    for owner in (0, 1)
                },
                "initial_full_score_equal": full_o == full_r,
            }
        )
    balanced = sum(
        1 for r in records
        if r["promotable_counts_rotated"][0] == r["promotable_counts_rotated"][1]
    )
    cancels = sum(
        1 for r in records
        if r["rotated_promotion_term_by_owner"][0]
        + r["rotated_promotion_term_by_owner"][1]
        == 0
    )
    decision = (
        "whole_board_zone_makes_the_promotion_term_a_constant"
        if balanced == len(records) and cancels == len(records)
        else "cancellation_not_general"
    )
    payload = {
        "role": "DEEPSEEK_AUX",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "post-hoc mechanism check of the A4 result",
        "a4_results_sha256": base.sha256_file(
            HERE / "results_promotion_zone_equivariance.json"
        ),
        "rules_checked": len(records),
        "balanced_counts": balanced,
        "term_cancels": cancels,
        "decision": decision,
        "records": records,
        "nonclaims": [
            "score arithmetic on the initial boards only, no search",
            "no strength, utility or outcome claim",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "decision": decision,
                "rules": len(records),
                "balanced": balanced,
                "cancels": cancels,
                "elapsed_seconds": round(time.time() - started, 2),
                "sha256": base.sha256_file(OUT),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
