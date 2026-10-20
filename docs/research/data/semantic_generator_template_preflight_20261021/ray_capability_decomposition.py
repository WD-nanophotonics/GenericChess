"""Decompose default static raw capability changes for the frozen ray screen."""
from __future__ import annotations

import json

from generic_chess.ai.evaluation import EvaluationConfig
from generic_chess.ai.evaluation.analyzer import (
    build_movement_capability, profile_movement_atoms,
)
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from ray_root_evaluation import SEEDS, build_ray


def run_seed(seed: int) -> dict:
    base = generate_game(GeneratorConfig(
        seed=seed, board_size=6, setup_preset="classic_like"
    ))
    ray, selected_type = build_ray(base, seed)
    config = EvaluationConfig()
    before_atoms = profile_movement_atoms(base.compiled_ruleset, selected_type)
    after_atoms = profile_movement_atoms(ray, selected_type)
    before = build_movement_capability(6, before_atoms, config)
    after = build_movement_capability(6, after_atoms, config)
    before_profile = build_ruleset_profile(base.compiled_ruleset, config)
    after_profile = build_ruleset_profile(ray, config)
    raw_before = before_profile.piece_profiles[selected_type].raw_capability_score
    raw_after = after_profile.piece_profiles[selected_type].raw_capability_score
    curve_delta = tuple(b - a for a, b in zip(
        before.expected_mobility, after.expected_mobility
    ))
    contributions = {
        "expected_mobility": sum(
            weight * delta
            for weight, delta in zip(config.density_weights, curve_delta)
        ),
        "coverage": config.coverage_weight * (
            after.coverage_ratio - before.coverage_ratio
        ),
        "reachable_pairs": config.reachability_weight * (
            after.reachable_pair_ratio - before.reachable_pair_ratio
        ),
        "path_efficiency": config.path_efficiency_weight * (
            (1 / (1 + after.average_shortest_path)
             if after.average_shortest_path is not None else 0)
            - (1 / (1 + before.average_shortest_path)
               if before.average_shortest_path is not None else 0)
        )
    }
    raw_from_features = sum(contributions.values())
    return {
        "seed": seed,
        "type": selected_type,
        "expected_mobility_delta": curve_delta,
        "empty_board_mobility_delta": after.empty_board_mobility - before.empty_board_mobility,
        "coverage_ratio_delta": after.coverage_ratio - before.coverage_ratio,
        "reachable_pair_ratio_delta": after.reachable_pair_ratio - before.reachable_pair_ratio,
        "average_shortest_path_delta": (
            None if before.average_shortest_path is None or after.average_shortest_path is None
            else after.average_shortest_path - before.average_shortest_path
        ),
        "directional_asymmetry_delta": after.directional_asymmetry - before.directional_asymmetry,
        "profile_raw_capability_delta": raw_after - raw_before,
        "raw_score_contributions": contributions,
        "raw_delta_from_features": raw_from_features,
        "raw_formula_reconciled": abs(raw_from_features - (raw_after - raw_before)) < 1e-12,
    }


def main() -> None:
    rows = [run_seed(seed) for seed in SEEDS]
    print(json.dumps({
        "question": "Which empty-board capability features account for the blocked ray's raw-price delta?",
        "roots": rows,
        "summary": {
            "roots": len(rows),
            "formula_reconciliations": sum(row["raw_formula_reconciled"] for row in rows),
            "sum_raw_capability_delta": sum(row["profile_raw_capability_delta"] for row in rows),
            "sum_raw_score_contributions": {
                key: sum(row["raw_score_contributions"][key] for row in rows)
                for key in rows[0]["raw_score_contributions"]
            },
            "limitations": "Fixed 6x6 classic-like initial-root type selections and one geometry; no realized-position or utility interpretation.",
        },
    }, indent=2))


if __name__ == "__main__":
    main()
