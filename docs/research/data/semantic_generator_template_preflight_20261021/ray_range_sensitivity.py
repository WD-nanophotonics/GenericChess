"""Test bounded-ray length sensitivity without games or changed root selection."""
from __future__ import annotations

import json
import random
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
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.session.session import GameSession

SEEDS = tuple(range(202610431, 202610439))


def run_seed(seed: int) -> dict:
    cfg = GeneratorConfig(seed=seed, board_size=6, setup_preset="classic_like")
    base = generate_game(cfg)
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
    config = EvaluationConfig()
    base_profile = build_ruleset_profile(base.compiled_ruleset, config)
    rows = []
    for max_steps in (1, 2, 3):
        action = RuleSemanticAction(
            name="ray_range_sensitivity",
            type_ids=(chosen.type_id,),
            geometry=RuleGeometrySpec(kind="ray", direction=(1, 0),
                                      min_steps=1, max_steps=max_steps),
            target_relation="empty", composition="augment",
            effects=(RuleActionEffect(
                "move", from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),),
            invariants=(RuleInvariant("own_anchor_safe"),),
        )
        compiled = compile_ruleset_for_execution(
            replace(base.ruleset, semantic_actions=(action,))
        )
        profile = build_ruleset_profile(compiled, config)
        pattern_id = next(
            pattern.pattern_id for pattern in compiled.ir.patterns
            if pattern.pattern_id.endswith("ray_range_sensitivity")
        )
        candidates = sum(
            move.pattern_id == pattern_id
            for move in GameSession(compiled).legal_actions()
        )
        rows.append({
            "max_steps": max_steps,
            "candidate_actions": candidates,
            "raw_capability_delta": (
                profile.piece_profiles[chosen.type_id].raw_capability_score
                - base_profile.piece_profiles[chosen.type_id].raw_capability_score
            ),
            "selected_type_board_value_delta": (
                profile.board_value_by_type[chosen.type_id]
                - base_profile.board_value_by_type[chosen.type_id]
            ),
            "board_value_deltas_by_type": {
                type_id: profile.board_value_by_type[type_id]
                - base_profile.board_value_by_type[type_id]
                for type_id in base_profile.board_value_by_type
            },
        })
    return {"seed": seed, "selected_type": chosen.type_id, "ranges": rows}


def main() -> None:
    roots = [run_seed(seed) for seed in SEEDS]
    print(json.dumps({
        "question": "How do range 1/2/3 affect direct-ray price and root exposure?",
        "roots": roots,
        "summary": {
            "roots": len(roots),
            "candidate_roots_by_range": {
                str(steps): sum(
                    next(item for item in root["ranges"]
                         if item["max_steps"] == steps)["candidate_actions"] > 0
                    for root in roots
                )
                for steps in (1, 2, 3)
            },
            "limitations": "Same fixed roots, type selector and horizontal owner-relative ray; no games, post-move reachability, outcomes, search, training, calibration or utility claim.",
        },
    }, indent=2))


if __name__ == "__main__":
    main()
