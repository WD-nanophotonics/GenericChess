"""Does the movement-atom rank span predict the promotion zone exactly?

Pre-registered in ``plan_a5.json``.  A4 measured that the A3-rotated promotion
zone is the whole board in all 152 rule-owner records.  This scan checks the
structural explanation against the same rules, with both predictions written
down before the run.

No search, no evaluation of positions, no new seeds.
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

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.core.movement import LeapAtom, RayAtom  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402
from generic_chess.rules.compiler import compile_ruleset  # noqa: E402

OUT = HERE / "results_zone_mechanism.json"
SEEDS = base.SEEDS
SIZES = base.SIZES


def atom_dr_span(atoms, n: int) -> tuple[int, int]:
    # Instrument fix (2026-10-18T13:44Z): every RayAtom in this generator has
    # ``max_steps=None`` (unbounded).  A ray can therefore advance at most
    # ``n - 1`` ranks on the board, which is the finite cap used here.  This
    # does not change any pre-written predictor in plan_a5.json.
    values = []
    for atom in atoms:
        if isinstance(atom, LeapAtom):
            values.append(atom.offset[1])
        elif isinstance(atom, RayAtom):
            steps = atom.max_steps if atom.max_steps is not None else n - 1
            values.append(atom.direction[1] * steps)
        else:
            raise TypeError(f"unsupported atom {atom!r}")
    return min(values), max(values)


def min_forward_step(atoms) -> int | None:
    """Smallest positive rank advance reachable in one atom (post-hoc)."""
    steps = []
    for atom in atoms:
        if isinstance(atom, LeapAtom):
            dr = atom.offset[1]
        elif isinstance(atom, RayAtom):
            dr = atom.direction[1]
        else:
            raise TypeError(f"unsupported atom {atom!r}")
        if dr > 0:
            steps.append(dr)
    return min(steps) if steps else None


def zone_rows(compiled, base_type: str, owner: int) -> list[int]:
    n = compiled.board_size
    forward = compiled.empty_forward_mobility[base_type][owner]
    return sorted({idx // n for idx in range(n * n) if not forward[idx]})


def scan_rule(seed: int, size: int) -> dict:
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
    )
    original_compiled = game.compiled_ruleset
    rotated_ruleset, _keys = a3.transform_a3(game.ruleset)
    rotated_compiled = compile_ruleset(rotated_ruleset)
    config = EvaluationConfig(hand_weight=base.HAND_WEIGHT)
    profile = build_ruleset_profile(original_compiled, config)
    n = size

    records = []
    for pt in original_compiled.piece_types:
        if not pt.is_promotable:
            continue
        gain = profile.promotion_gain_by_type.get(pt.type_id, 0)
        if gain <= 0:
            continue
        min_dr, max_dr = atom_dr_span(pt.movement_atoms, n)
        smallest_step = min_forward_step(pt.movement_atoms)
        # plan_a5 states the rotated-whole-board predictor in terms of the
        # span of the ROTATED rule (every dr negated), not the original one.
        rot_min_dr, rot_max_dr = -max_dr, -min_dr
        for owner in (0, 1):
            rows = zone_rows(original_compiled, pt.type_id, owner)
            rotated_rows = zone_rows(rotated_compiled, pt.type_id, owner)
            if owner == 0:
                predicted_rows = min(n, max(0, max_dr))
                predicted_rotated_full = rot_max_dr <= 0
                predicted_rows_minstep = (
                    n if smallest_step is None else min(n, smallest_step)
                )
            else:
                predicted_rows = min(n, max(0, -min_dr))
                predicted_rotated_full = rot_min_dr >= 0
                predicted_rows_minstep = (
                    n if smallest_step is None else min(n, smallest_step)
                )
            records.append(
                {
                    "base_type": pt.type_id,
                    "owner": owner,
                    "gain": gain,
                    "min_dr": min_dr,
                    "max_dr": max_dr,
                    "measured_zone_rows": len(rows),
                    "predicted_zone_rows": predicted_rows,
                    "band_matches": len(rows) == predicted_rows,
                    "min_forward_step": smallest_step,
                    "predicted_zone_rows_minstep_post_hoc": predicted_rows_minstep,
                    "band_matches_minstep_post_hoc": len(rows) == predicted_rows_minstep,
                    "rotated_zone_whole_board": len(rotated_rows) == n,
                    "predicted_rotated_whole_board": predicted_rotated_full,
                    "rotated_matches": (len(rotated_rows) == n) == predicted_rotated_full,
                    # Post-hoc corrected model (see report): the compiler
                    # negates owner-1 offsets, so both owners have a forward
                    # move iff some atom has dr > 0.  The band width is then
                    # the smallest positive advance, and the rotated zone is
                    # the whole board iff the original rule has no dr < 0.
                    "post_hoc_no_backward_atom": min_dr >= 0,
                    "post_hoc_predicted_rotated_whole_board": min_dr >= 0,
                    "post_hoc_rotated_matches": (len(rotated_rows) == n)
                    == (min_dr >= 0),
                    "atom_count": len(pt.movement_atoms),
                }
            )
    return {"seed": seed, "board_size": size, "records": records}


def decide(rules: list[dict]) -> dict:
    records = [record for rule in rules for record in rule["records"]]
    band_failures = [record for record in records if not record["band_matches"]]
    rotated_failures = [record for record in records if not record["rotated_matches"]]
    if not band_failures and not rotated_failures:
        decision = "zone_geometry_is_explained_by_atom_span"
    elif rotated_failures and not band_failures:
        decision = "zone_geometry_only_partially_explained"
    else:
        decision = "zone_geometry_is_not_explained_by_atom_span"
    return {
        "decision": decision,
        "records": len(records),
        "band_matches": len(records) - len(band_failures),
        "rotated_matches": len(records) - len(rotated_failures),
        "post_hoc_minstep": {
            "label": "post-hoc corrected predictor, not the pre-registered one",
            "matches": sum(1 for record in records if record["band_matches_minstep_post_hoc"]),
            "failures": [
                record
                for record in records
                if not record["band_matches_minstep_post_hoc"]
            ][:8],
            "rotated_matches": sum(
                1 for record in records if record["post_hoc_rotated_matches"]
            ),
            "records_with_no_backward_atom": sum(
                1 for record in records if record["post_hoc_no_backward_atom"]
            ),
        },
        "band_failure_sample": band_failures[:8],
        "rotated_failure_sample": rotated_failures[:8],
        "records_with_max_dr_le_0": sum(
            1 for record in records if record["max_dr"] <= 0
        ),
        "records_with_min_dr_ge_0": sum(
            1 for record in records if record["min_dr"] >= 0
        ),
        "distinct_min_dr": sorted({record["min_dr"] for record in records}),
        "distinct_max_dr": sorted({record["max_dr"] for record in records}),
    }


def main() -> int:
    started = time.time()
    rules = [scan_rule(seed, size) for size in SIZES for seed in SEEDS]
    verdict = decide(rules)
    payload = {
        "role": "DEEPSEEK_AUX",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "plan_sha256": base.sha256_file(HERE / "plan_a5.json"),
        "a4_results_sha256": base.sha256_file(
            HERE / "results_promotion_zone_equivariance.json"
        ),
        "source_sha256": {
            path: base.sha256_file(ROOT / path)
            for path in (
                "generic_chess/rules/compiler.py",
                "generic_chess/core/coordinates.py",
                "generic_chess/core/movement.py",
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
            "endpoint": "measured original zone row count versus min(n, max(0, max_forward_dr)), and measured rotated zone whole-board status versus max_forward_dr <= 0 (owner 0) / min_forward_dr >= 0 (owner 1)",
        },
        "instrument_correction": {
            "first_run": "crashed with TypeError because RayAtom.max_steps is None (unbounded) for every ray in this generator",
            "fix": "unbounded rays are capped at n-1 rank steps, the maximum attainable on the board; pre-written predictors unchanged",
            "second_change": "added a post-hoc predictor that uses the smallest positive rank advance instead of the largest, because the plan_a5 derivation conflates maximum reach with band width; it is reported separately and is not the pre-registered test",
        },
        "verdict": verdict,
        "rules": rules,
        "nonclaims": [
            "no search and no strength, utility or outcome claim",
            "the explanation is about zone geometry only",
            "one generator family, square boards 6 and 8, 40 seeds",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "elapsed_seconds": round(time.time() - started, 2),
                **verdict,
                "sha256": base.sha256_file(OUT),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
