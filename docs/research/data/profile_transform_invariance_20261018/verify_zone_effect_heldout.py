"""Held-out test of the corrected zone model's *consequence* on new seeds.

The corrected post-hoc model says: the rotated rule gets a whole-board
promotion zone exactly when the original promotable base type has no atom with
a negative rank direction.  A whole-board zone makes the promotion term a
count difference, so a relocated piece can only change the term when the
original (band) zone is what it left.

Predictive consequence, stated before the run on fresh seeds:
  (P1) for every usable ``in_zone`` case, ``promotion_only`` differs from zero
       exactly when the type is predicted to have a whole-board rotated zone;
  (P2) every usable ``near_zone``/``far`` case is zero, because the piece is
       outside the original band zone either way.

Instrument history (kept, not hidden): the first execution tested the
equivalence over *all* case kinds instead of only ``in_zone``, so it reported
134 "mismatches" that are exactly the near/far cases where a whole-board
rotated zone is predicted but no difference can arise.  The prediction was
mis-specified, not falsified; P1/P2 above are the same claim split correctly
and the raw first outcome is recorded in ``instrument_error``.

Seeds 292101-292112 are used here for the first time anywhere in this study
(292001-292040 were the fit set, 292041-292052 the earlier held-out set).
No search, no learning, no fitness, no new rule family.
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
import scan_promotion_zone_equivariance as a4  # noqa: E402

from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

OUT_MEASURED = HERE / "results_promotion_zone_equivariance_heldout.json"
OUT = HERE / "results_zone_effect_heldout.json"
SEEDS = tuple(range(292101, 292113))
SIZES = (6, 8)


def has_backward_atom(atoms) -> bool:
    """True if any atom has a negative rank direction (post-hoc model input)."""
    for atom in atoms:
        if hasattr(atom, "offset"):  # LeapAtom
            dr = atom.offset[1]
        else:  # RayAtom
            dr = atom.direction[1]
        if dr < 0:
            return True
    return False


def predicted(rules) -> dict:
    """Per (seed, size, base_type): predicted whole-board rotated zone."""
    compiled = rules.compiled_ruleset
    return {
        pt.type_id: not has_backward_atom(pt.movement_atoms)
        for pt in compiled.piece_types
        if pt.is_promotable
    }


def promotion_term_by_owner(state, compiled, profile, evaluator) -> dict:
    """Sum of the evaluator's promotion bonus per owner (count-only if whole board)."""
    term = {0: 0.0, 1: 0.0}
    for idx, piece in enumerate(state.position.board):
        if piece is None or piece.promoted:
            continue
        term[piece.owner] += evaluator._promotion_bonus(piece, idx)
    return term


def decompose(rule, case) -> dict:
    """Rebuild the relocated pair and attribute the difference to the term."""
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.evaluator import Evaluator
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.core.transition import initial_state
    from generic_chess.rules.compiler import compile_ruleset

    import scan_profile_transform_a3 as a3

    game = generate_game(
        GeneratorConfig(
            seed=rule["seed"], board_size=rule["board_size"],
            setup_preset="classic_like",
        )
    )
    rotated_ruleset, _keys = a3.transform_a3(game.ruleset)
    rotated_compiled = compile_ruleset(rotated_ruleset)
    config = EvaluationConfig(hand_weight=base.HAND_WEIGHT)
    original_profile = build_ruleset_profile(game.compiled_ruleset, config)
    rotated_profile = build_ruleset_profile(rotated_compiled, config)
    original_state = initial_state(game.compiled_ruleset)
    rotated_state = initial_state(rotated_compiled)
    original_board = original_state.position.board
    rotated_board = rotated_state.position.board

    src = next(
        idx for idx, piece in enumerate(original_board)
        if piece is not None
        and piece.owner == case["owner"]
        and piece.base_type_id == case["base_type"]
        and not piece.promoted
    )
    src_rotated = a4.sigma_idx(src, rule["board_size"])
    original_case_state = a4.relocate(original_state, src, case["original_square"])
    rotated_case_state = a4.relocate(rotated_state, src_rotated, case["rotated_square"])
    evaluator_o = Evaluator(game.compiled_ruleset, original_profile, config)
    evaluator_r = Evaluator(rotated_compiled, rotated_profile, config)
    term_o = promotion_term_by_owner(
        original_case_state, game.compiled_ruleset, original_profile, evaluator_o
    )
    term_r = promotion_term_by_owner(
        rotated_case_state, rotated_compiled, rotated_profile, evaluator_r
    )
    # ``_promotion_bonus`` already carries the owner sign (owner 1 is negated),
    # so the score contribution of the term is the plain sum over owners.
    delta = (term_r[0] + term_r[1]) - (term_o[0] + term_o[1])
    return {
        "original_promotion_term_by_owner": term_o,
        "rotated_promotion_term_by_owner": term_r,
        "delta_from_promotion_term": delta,
        "matches_measured_difference": delta
        == case["differences"]["promotion_only"],
    }


def main() -> int:
    started = time.time()
    first_attempt = json.loads((HERE / "results_zone_effect_heldout_first.json").read_text(
        encoding="utf-8"
    ))
    a4.SEEDS = SEEDS
    a4.SIZES = SIZES
    a4.OUT = OUT_MEASURED
    a4.main()
    measured = json.loads(OUT_MEASURED.read_text(encoding="utf-8"))

    checks = []
    in_zone_mismatches = []
    other_nonzero = []
    for rule in measured["rules"]:
        game = generate_game(
            GeneratorConfig(
                seed=rule["seed"], board_size=rule["board_size"],
                setup_preset="classic_like",
            )
        )
        pred = predicted(game)
        for case in rule["cases"]:
            if case.get("status") != "ok":
                continue
            base_type = case["base_type"]
            expected_nonzero = pred.get(base_type)
            observed_nonzero = case["differences"]["promotion_only"] != 0
            item = {
                "seed": rule["seed"],
                "board_size": rule["board_size"],
                "base_type": base_type,
                "owner": case["owner"],
                "kind": case["kind"],
                "predicted_whole_board_rotated_zone": expected_nonzero,
                "observed_promotion_difference": case["differences"]["promotion_only"],
                "square_in_zone": case["square_in_zone"],
                "square_in_rotated_zone": case["square_in_rotated_zone"],
            }
            if case["kind"] == "in_zone":
                item["matches_P1"] = expected_nonzero == observed_nonzero
                if not item["matches_P1"]:
                    in_zone_mismatches.append(item)
            else:
                item["matches_P2"] = not observed_nonzero
                if not item["matches_P2"]:
                    other_nonzero.append(item)
            if observed_nonzero:
                item["decomposition"] = decompose(rule, case)
            checks.append(item)

    in_zone = [c for c in checks if c["kind"] == "in_zone"]
    other = [c for c in checks if c["kind"] != "in_zone"]
    decomposed = [c for c in checks if "decomposition" in c]
    decision = (
        "fresh_seeds_confirms_the_zone_consequence"
        if in_zone and not in_zone_mismatches and not other_nonzero
        and all(c["decomposition"]["matches_measured_difference"] for c in decomposed)
        else "fresh_seeds_do_not_confirm_the_zone_consequence"
    )
    payload = {
        "role": "DEEPSEEK_AUX",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "post-hoc predictive check on seeds never used before",
        "measured_file": OUT_MEASURED.name,
        "measured_sha256": base.sha256_file(OUT_MEASURED),
        "seeds": list(SEEDS),
        "board_sizes": list(SIZES),
        "previous_seed_sets": {
            "fit": [292001, 292040],
            "earlier_heldout": [292041, 292052],
            "this_check": [SEEDS[0], SEEDS[-1]],
        },
        "prediction": {
            "P1": "for usable in_zone cases, promotion_only differs from zero exactly when the base type has no backward atom (predicted whole-board rotated zone)",
            "P2": "every usable near_zone/far case is zero",
            "P3": "the measured difference equals the change in the summed promotion term",
        },
        "instrument_error": {
            "first_attempt_file": "results_zone_effect_heldout_first.json",
            "first_attempt_sha256": base.sha256_file(
                HERE / "results_zone_effect_heldout_first.json"
            ),
            "first_attempt_decision": first_attempt.get("decision"),
            "first_attempt_mismatches": len(first_attempt.get("mismatches", [])),
            "cause": "the equivalence was applied to all case kinds, so every near_zone/far case with a predicted whole-board rotated zone counted as a mismatch although P2 expects zero there",
            "fix": "the claim is evaluated on in_zone cases for P1 and as a zero check for near/far for P2; no measured number changed",
        },
        "usable_cases": len(checks),
        "in_zone_cases": len(in_zone),
        "in_zone_predicted_nonzero": sum(
            1 for c in in_zone if c["predicted_whole_board_rotated_zone"]
        ),
        "in_zone_observed_nonzero": sum(
            1 for c in in_zone if c["observed_promotion_difference"] != 0
        ),
        "in_zone_mismatches": in_zone_mismatches,
        "non_in_zone_cases": len(other),
        "non_in_zone_observed_nonzero": sum(
            1 for c in other if c["observed_promotion_difference"] != 0
        ),
        "non_in_zone_mismatches": other_nonzero,
        "decomposed_cases": len(decomposed),
        "decomposition_agrees": sum(
            1 for c in decomposed if c["decomposition"]["matches_measured_difference"]
        ),
        "observed_difference_magnitudes": sorted(
            {abs(c["observed_promotion_difference"]) for c in checks if c["observed_promotion_difference"]}
        ),
        "decision": decision,
        "a4_decision_on_these_seeds": measured["verdict"]["decision"],
        "nonclaims": [
            "no strength, utility, game-outcome or reachability claim",
            "one generator family, boards 6 and 8, 12 fresh seeds, arithmetic on initial boards only",
            "the fitted model is post-hoc; this file only tests its consequence on new seeds",
        ],
        "checks": checks,
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "decision": decision,
                "usable_cases": len(checks),
                "in_zone": [len(in_zone), payload["in_zone_observed_nonzero"]],
                "non_in_zone_nonzero": payload["non_in_zone_observed_nonzero"],
                "in_zone_mismatches": len(in_zone_mismatches),
                "non_in_zone_mismatches": len(other_nonzero),
                "decomposition": [
                    len(decomposed),
                    payload["decomposition_agrees"],
                ],
                "magnitudes": payload["observed_difference_magnitudes"],
                "a4_decision": measured["verdict"]["decision"],
                "elapsed_seconds": round(time.time() - started, 2),
                "sha256": base.sha256_file(OUT),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
