"""Compare initial evaluator components with/without the frozen blocked ray."""
from __future__ import annotations

import json
import random
import statistics
from dataclasses import replace

from generic_chess.core.movement import RayAtom
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleActionEffect, RuleGeometrySpec, RuleInvariant, RuleSemanticAction,
    RuleSquareRef,
)
from generic_chess.ai.evaluation import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.session.session import GameSession

SEEDS = tuple(range(202610431, 202610439))


def build_ray(base, seed: int):
    present = {
        piece.current_type_id
        for row in base.ruleset.initial_position for piece in row if piece
    }
    eligible = []
    for piece_type in base.ruleset.piece_types:
        has_direction = any(
            isinstance(atom, RayAtom) and atom.direction == (1, 0)
            for atom in piece_type.movement_atoms
        )
        if (not piece_type.is_anchor and not piece_type.is_promotable
                and piece_type.type_id in present and piece_type.movement_atoms
                and not has_direction):
            eligible.append(piece_type)
    chosen = random.Random(seed ^ 0xA651).choice(
        sorted(eligible, key=lambda piece_type: piece_type.type_id)
    )
    action = RuleSemanticAction(
        name="direct_ray_profile_probe",
        type_ids=(chosen.type_id,),
        geometry=RuleGeometrySpec(kind="ray", direction=(1, 0),
                                  min_steps=1, max_steps=3),
        target_relation="empty", composition="augment",
        effects=(RuleActionEffect(
            "move", from_ref=RuleSquareRef("source"),
            to_ref=RuleSquareRef("target"),
        ),),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    return (compile_ruleset_for_execution(
        replace(base.ruleset, semantic_actions=(action,))
    ), chosen.type_id)


def components(compiled, config, state):
    profile = build_ruleset_profile(compiled, config)
    evaluator = Evaluator(compiled, profile, config)
    position = state.position
    material_by_owner = {0: 0, 1: 0}
    piece_counts = {
        piece_type.type_id: {"0": 0, "1": 0}
        for piece_type in compiled.piece_types
    }
    for piece in position.board:
        if piece is not None:
            value = profile.board_value_by_type[piece.current_type_id]
            material_by_owner[piece.owner] += value
            piece_counts[piece.current_type_id][str(piece.owner)] += 1
    for owner in (0, 1):
        for type_id, count in position.hands[owner].counts:
            value = profile.hand_value_by_base_type[type_id]
            material_by_owner[owner] += count * value
            piece_counts[type_id][str(owner)] += count

    attacks = evaluator._attack_maps(state)
    mobility_by_owner = {
        owner: config.dynamic_mobility_weight * len(attacks[owner])
        for owner in (0, 1)
    }
    escape_by_owner = {0: 0, 1: 0}
    if config.anchor_escape_weight:
        for owner in (0, 1):
            escape_by_owner[owner] = config.anchor_escape_weight * evaluator._anchor_escape(
                position, owner, attacks[1 - owner]
            )
        from generic_chess.core.attacks import anchor_square
        if anchor_square(position, 0, compiled) in attacks[1]:
            escape_by_owner[0] -= config.anchor_escape_weight * 10
        if anchor_square(position, 1, compiled) in attacks[0]:
            escape_by_owner[1] -= config.anchor_escape_weight * 10
    promotion_by_owner = {0: 0, 1: 0}
    for idx, piece in enumerate(position.board):
        if piece is not None:
            promotion_by_owner[piece.owner] += abs(evaluator._promotion_bonus(piece, idx))
    material = material_by_owner[0] - material_by_owner[1]
    mobility = mobility_by_owner[0] - mobility_by_owner[1]
    escape = escape_by_owner[0] - escape_by_owner[1]
    promotion = promotion_by_owner[0] - promotion_by_owner[1]
    raw = material + mobility + escape + promotion
    perspective = raw if position.side_to_move == 0 else -raw
    observed = evaluator.evaluate(state)
    assert perspective == observed, (perspective, observed)
    return {
        "material": material,
        "material_by_owner": material_by_owner,
        "dynamic_mobility": mobility,
        "dynamic_mobility_by_owner": mobility_by_owner,
        "anchor_escape_and_check": escape,
        "anchor_escape_and_check_by_owner": escape_by_owner,
        "promotion_potential": promotion,
        "promotion_potential_by_owner": promotion_by_owner,
        "side_to_move_score": observed,
        "profile_board_values": dict(profile.board_value_by_type),
        "raw_capability_by_type": {
            type_id: value.raw_capability_score
            for type_id, value in profile.piece_profiles.items()
        },
        "normalizer_raw_median": statistics.median(
            value.raw_capability_score
            for value in profile.piece_profiles.values() if not value.is_anchor
        ),
        "piece_counts_by_type_owner": piece_counts,
    }


def run_seed(seed: int) -> dict:
    base = generate_game(GeneratorConfig(
        seed=seed, board_size=6, setup_preset="classic_like"
    ))
    ray, chosen_type = build_ray(base, seed)
    base_state = GameSession(base.compiled_ruleset).state
    ray_state = GameSession(ray).state
    config = EvaluationConfig()
    base_terms = components(base.compiled_ruleset, config, base_state)
    ray_terms = components(ray, config, ray_state)
    delta = {}
    def subtract(ray_value, base_value):
        if isinstance(base_value, dict):
            return {key: subtract(ray_value[key], item)
                    for key, item in base_value.items()}
        return ray_value - base_value
    delta = {key: subtract(ray_terms[key], value)
             for key, value in base_terms.items()}
    per_type_material_delta = {}
    for type_id, counts in base_terms["piece_counts_by_type_owner"].items():
        value_delta = delta["profile_board_values"].get(type_id, 0)
        per_type_material_delta[type_id] = {
            owner: counts[owner] * value_delta for owner in counts
        }
    delta["material_delta_by_type_owner"] = per_type_material_delta
    return {
        "seed": seed,
        "chosen_type": chosen_type,
        "base": base_terms,
        "ray": ray_terms,
        "delta": delta,
    }


def main() -> None:
    rows = [run_seed(seed) for seed in SEEDS]
    delta_totals = {}
    def sum_tree(values):
        if isinstance(values[0], dict):
            return {key: sum_tree([value[key] for value in values])
                    for key in values[0]}
        return sum(values)
    delta_totals = {
        key: sum_tree([row["delta"][key] for row in rows])
        for key in rows[0]["delta"]
    }
    compact = []
    for row in rows:
        compact.append({
            "seed": row["seed"],
            "chosen_type": row["chosen_type"],
            "profile_board_value_deltas": row["delta"]["profile_board_values"],
            "raw_capability_deltas": row["delta"]["raw_capability_by_type"],
            "normalizer_raw_median_delta": row["delta"]["normalizer_raw_median"],
            "material_deltas_by_owner": row["delta"]["material_by_owner"],
            "dynamic_mobility_deltas_by_owner": row["delta"][
                "dynamic_mobility_by_owner"
            ],
            "anchor_escape_check_and_promotion_deltas_by_owner": {
                owner: row["delta"]["anchor_escape_and_check_by_owner"][int(owner)]
                + row["delta"]["promotion_potential_by_owner"][int(owner)]
                for owner in ("0", "1")
            },
            "production_score_delta": row["delta"]["side_to_move_score"],
        })
    aggregate = {
        "profile_board_value_deltas_by_type": delta_totals["profile_board_values"],
        "raw_capability_deltas_by_type": delta_totals["raw_capability_by_type"],
        "normalizer_raw_median_delta_sum": delta_totals["normalizer_raw_median"],
        "material_deltas_by_owner": delta_totals["material_by_owner"],
        "dynamic_mobility_deltas_by_owner": delta_totals[
            "dynamic_mobility_by_owner"
        ],
        "production_score_delta_sum": delta_totals["side_to_move_score"],
        "material_delta_by_type_and_owner": delta_totals[
            "material_delta_by_type_owner"
        ],
    }
    print(json.dumps({
        "question": "Does a blocked direct ray alter live initial evaluation and through which terms?",
        "roots": compact,
        "aggregate_delta_sum_over_eight_roots": aggregate,
        "all_component_sums_reconciled": True,
        "limitations": "Default production Evaluator at initial roots only; no move submission, search, outcome, training, calibration or utility claim.",
    }, indent=2))


if __name__ == "__main__":
    main()
