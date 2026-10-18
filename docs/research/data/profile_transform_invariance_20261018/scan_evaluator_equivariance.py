"""Is the served leaf evaluator rotation-equivariant, and if not, which term?

Pre-registered in ``plan_evaluator_equivariance.json``.  The static profile was
exactly invariant under the A3 full rotation; the evaluator is a different
function.  For each of the 80 rulesets the initial position of the original rule
and of its A3 rotation are scored under five configurations that differ only in
the dynamic weights, so the difference is decomposed per evaluation term.

No search, no learning, no new seeds, no position sampling beyond the one initial
state of each rule.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import replace
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
from generic_chess.core.transition import initial_state  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402
from generic_chess.rules.compiler import compile_ruleset  # noqa: E402

OUT = HERE / "results_evaluator_equivariance.json"
SEEDS = base.SEEDS
SIZES = base.SIZES
PROFILE_HAND_WEIGHT = base.HAND_WEIGHT

CONFIGURATIONS = {
    "material_only": EvaluationConfig(
        hand_weight=PROFILE_HAND_WEIGHT,
        dynamic_mobility_weight=0,
        anchor_escape_weight=0,
        promotion_potential_weight=0,
    ),
    "mobility_only": EvaluationConfig(
        hand_weight=PROFILE_HAND_WEIGHT,
        dynamic_mobility_weight=2,
        anchor_escape_weight=0,
        promotion_potential_weight=0,
    ),
    "anchor_only": EvaluationConfig(
        hand_weight=PROFILE_HAND_WEIGHT,
        dynamic_mobility_weight=0,
        anchor_escape_weight=5,
        promotion_potential_weight=0,
    ),
    "no_promotion_potential": EvaluationConfig(
        hand_weight=PROFILE_HAND_WEIGHT,
        dynamic_mobility_weight=2,
        anchor_escape_weight=5,
        promotion_potential_weight=0,
    ),
    "default": EvaluationConfig(hand_weight=PROFILE_HAND_WEIGHT),
}

SOURCE_FILES = base.SOURCE_FILES + (
    "generic_chess/ai/evaluation/evaluator.py",
    "generic_chess/core/actions.py",
    "generic_chess/core/position.py",
    "generic_chess/core/transition.py",
)


def material_multiset(position) -> list:
    items = []
    for piece in position.board:
        if piece is None:
            continue
        items.append((piece.owner, piece.current_type_id, piece.base_type_id))
    for owner in (0, 1):
        for type_id, count in position.hands[owner].counts:
            items.append((owner, f"hand:{type_id}", count))
    return sorted(items, key=str)


def score_all(compiled, profile) -> dict:
    state = initial_state(compiled)
    return {
        name: Evaluator(compiled, profile, config).evaluate(state)
        for name, config in CONFIGURATIONS.items()
    }


def scan_rule(seed: int, size: int) -> dict:
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
    )
    original_ruleset = game.ruleset
    original_compiled = game.compiled_ruleset
    profile_config = EvaluationConfig(hand_weight=PROFILE_HAND_WEIGHT)
    original_profile = build_ruleset_profile(original_compiled, profile_config)

    rotated_ruleset, _keys = a3.transform_a3(original_ruleset)
    rotated_compiled = compile_ruleset(rotated_ruleset)
    rotated_profile = build_ruleset_profile(rotated_compiled, profile_config)

    original_scores = score_all(original_compiled, original_profile)
    rotated_scores = score_all(rotated_compiled, rotated_profile)
    material_original = material_multiset(initial_state(original_compiled).position)
    material_rotated = material_multiset(initial_state(rotated_compiled).position)

    promotable_on_board = sorted(
        {
            piece.base_type_id
            for piece in original_compiled.initial_position.board
            if piece is not None and not piece.promoted
        }
        & {
            piece_type.type_id
            for piece_type in original_compiled.piece_types
            if piece_type.is_promotable
        }
    )

    return {
        "seed": seed,
        "board_size": size,
        "ruleset_fingerprint": original_compiled.ruleset_fingerprint,
        "rotated_fingerprint": rotated_compiled.ruleset_fingerprint,
        "material_parity": material_original == material_rotated,
        "promotable_types_on_board": promotable_on_board,
        "original_scores": original_scores,
        "rotated_scores": rotated_scores,
        "differences": {
            name: rotated_scores[name] - original_scores[name]
            for name in CONFIGURATIONS
        },
    }


def decide(rules: list[dict]) -> dict:
    names = list(CONFIGURATIONS)
    nonzero = {
        name: [
            {"seed": rule["seed"], "board_size": rule["board_size"],
             "difference": rule["differences"][name]}
            for rule in rules
            if rule["differences"][name] != 0
        ]
        for name in names
    }
    if nonzero["default"] and not (
        nonzero["material_only"]
        or nonzero["mobility_only"]
        or nonzero["anchor_only"]
        or nonzero["no_promotion_potential"]
    ):
        decision = "evaluator_orientation_dependence_localized_to_promotion_potential"
    elif not nonzero["default"] and not any(nonzero[name] for name in names):
        decision = "evaluator_is_rotation_equivariant"
    else:
        decision = "evaluator_has_additional_orientation_dependence"
    return {
        "decision": decision,
        "rules_total": len(rules),
        "material_parity_rules": sum(rule["material_parity"] for rule in rules),
        "rules_with_promotable_piece_on_board": sum(
            bool(rule["promotable_types_on_board"]) for rule in rules
        ),
        "nonzero_by_configuration": {
            name: {"rules": len(nonzero[name]), "sample": nonzero[name][:8]}
            for name in names
        },
        "max_abs_difference_by_configuration": {
            name: max((abs(rule["differences"][name]) for rule in rules), default=0)
            for name in names
        },
        "sign_pattern_default": sorted(
            {
                (rule["differences"]["default"] > 0) - (rule["differences"]["default"] < 0)
                for rule in rules
            }
        ),
        "distinct_default_differences": sorted(
            {rule["differences"]["default"] for rule in rules}
        )[:20],
    }


def main() -> int:
    started = time.time()
    rules = [scan_rule(seed, size) for size in SIZES for seed in SEEDS]
    verdict = decide(rules)
    payload = {
        "role": "DEEPSEEK_AUX",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "plan_sha256": base.sha256_file(HERE / "plan_evaluator_equivariance.json"),
        "a3_plan_sha256": base.sha256_file(HERE / "plan_a3.json"),
        "a3_results_sha256": base.sha256_file(HERE / "results_profile_transform_a3.json"),
        "source_sha256": {path: base.sha256_file(ROOT / path) for path in SOURCE_FILES},
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
            "setup_preset": "classic_like",
            "profile_hand_weight": PROFILE_HAND_WEIGHT,
            "search": False,
            "states_per_rule": 1,
            "configurations": {
                name: {
                    "dynamic_mobility_weight": config.dynamic_mobility_weight,
                    "anchor_escape_weight": config.anchor_escape_weight,
                    "promotion_potential_weight": config.promotion_potential_weight,
                }
                for name, config in CONFIGURATIONS.items()
            },
            "endpoint": "score(rotated initial position under the rotated rule) - score(original initial position under the original rule), same side to move, per configuration",
            "decision_rule": "see plan_evaluator_equivariance.json; the localized decision requires every weight-0 configuration to be zero on all 80 rules while default is nonzero somewhere",
        },
        "verdict": verdict,
        "rules": rules,
        "nonclaims": [
            "no strength, utility or game-outcome claim",
            "a nonzero score difference is a statement about the evaluation function, not about which side is better",
            "one initial position per rule and one generator family; not a distribution over positions",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "elapsed_seconds": round(time.time() - started, 2),
                "decision": verdict["decision"],
                "material_parity_rules": verdict["material_parity_rules"],
                "rules_with_promotable_piece_on_board": verdict[
                    "rules_with_promotable_piece_on_board"
                ],
                "nonzero_by_configuration": {
                    name: item["rules"]
                    for name, item in verdict["nonzero_by_configuration"].items()
                },
                "max_abs_difference_by_configuration": verdict[
                    "max_abs_difference_by_configuration"
                ],
                "sign_pattern_default": verdict["sign_pattern_default"],
                "sha256": base.sha256_file(OUT),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
