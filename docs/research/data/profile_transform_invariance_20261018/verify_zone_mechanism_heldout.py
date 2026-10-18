"""Post-hoc predictive check of the corrected zone-geometry model.

The pre-registered predictor in ``plan_a5.json`` failed (see
``results_zone_mechanism.json``).  The corrected model says:

* both owners have a forward move on a square iff some atom has ``dr > 0``
  (the compiler negates owner-1 offsets, then ``is_forward`` uses absolute
  rank), so the original zone is the same band for both owners and its row
  count is the smallest positive rank advance, or the whole board when no
  atom advances;
* the 180-degree-rotated rule has a whole-board zone iff the original rule
  has no atom with ``dr < 0``.

That model was fitted on the 40 seeds used by A4/A5.  This script checks it
predictively on seeds that were never used by the transform study.  No
search, no position evaluation.
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
import scan_profile_transform_a3 as a3  # noqa: E402
from scan_zone_mechanism import (  # noqa: E402
    atom_dr_span,
    min_forward_step,
    zone_rows,
)

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402
from generic_chess.rules.compiler import compile_ruleset  # noqa: E402

OUT = HERE / "results_zone_mechanism_heldout.json"
HELDOUT_SEEDS = tuple(range(292041, 292053))
SIZES = base.SIZES


def main() -> int:
    started = time.time()
    records = []
    for size in SIZES:
        for seed in HELDOUT_SEEDS:
            game = generate_game(
                GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
            )
            rotated_ruleset, _keys = a3.transform_a3(game.ruleset)
            rotated_compiled = compile_ruleset(rotated_ruleset)
            profile = build_ruleset_profile(
                game.compiled_ruleset,
                EvaluationConfig(hand_weight=base.HAND_WEIGHT),
            )
            n = size
            for pt in game.compiled_ruleset.piece_types:
                if not pt.is_promotable:
                    continue
                if profile.promotion_gain_by_type.get(pt.type_id, 0) <= 0:
                    continue
                smallest = min_forward_step(pt.movement_atoms)
                min_dr, _max_dr = atom_dr_span(pt.movement_atoms, n)
                predicted_rows = n if smallest is None else min(n, smallest)
                predicted_rotated_full = min_dr >= 0
                for owner in (0, 1):
                    rows = zone_rows(game.compiled_ruleset, pt.type_id, owner)
                    rot_rows = zone_rows(rotated_compiled, pt.type_id, owner)
                    records.append(
                        {
                            "seed": seed,
                            "board_size": size,
                            "base_type": pt.type_id,
                            "owner": owner,
                            "smallest_forward_step": smallest,
                            "min_dr": min_dr,
                            "measured_zone_rows": len(rows),
                            "predicted_zone_rows": predicted_rows,
                            "band_matches": len(rows) == predicted_rows,
                            "rotated_zone_whole_board": len(rot_rows) == n,
                            "predicted_rotated_whole_board": predicted_rotated_full,
                            "rotated_matches": (len(rot_rows) == n)
                            == predicted_rotated_full,
                        }
                    )
    band_fail = [r for r in records if not r["band_matches"]]
    rot_fail = [r for r in records if not r["rotated_matches"]]
    if records and not band_fail and not rot_fail:
        decision = "corrected_zone_model_predicts_heldout_records"
    elif records:
        decision = "corrected_zone_model_fails_on_heldout_records"
    else:
        decision = "no_heldout_records"
    payload = {
        "role": "DEEPSEEK_AUX",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "post-hoc predictive check, not pre-registered",
        "derived_from": "results_zone_mechanism.json post_hoc_minstep model",
        "plan_a5_sha256": base.sha256_file(HERE / "plan_a5.json"),
        "zone_results_sha256": base.sha256_file(HERE / "results_zone_mechanism.json"),
        "heldout_seeds": list(HELDOUT_SEEDS),
        "board_sizes": list(SIZES),
        "records": len(records),
        "band_matches": len(records) - len(band_fail),
        "rotated_matches": len(records) - len(rot_fail),
        "band_failure_sample": band_fail[:5],
        "rotated_failure_sample": rot_fail[:5],
        "decision": decision,
        "git_head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "nonclaims": [
            "no search and no strength, utility or outcome claim",
            "zone geometry only; one generator family, square boards 6 and 8",
        ],
        "records_detail": records,
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "decision": decision,
                "records": len(records),
                "band_matches": payload["band_matches"],
                "rotated_matches": payload["rotated_matches"],
                "elapsed_seconds": round(time.time() - started, 2),
                "sha256": base.sha256_file(OUT),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
