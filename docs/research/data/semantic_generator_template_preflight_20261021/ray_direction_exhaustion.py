"""Exhaust absent direct-ray directions on the frozen eight initial roots."""
from __future__ import annotations

import json
from dataclasses import replace

from generic_chess.core.movement import RayAtom
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.filters import run_soft_filters
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleActionEffect, RuleGeometrySpec, RuleInvariant, RuleSemanticAction,
    RuleSquareRef,
)
from generic_chess.session.session import GameSession

SEEDS = tuple(range(202610431, 202610439))
DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1),
              (1, 1), (1, -1), (-1, 1), (-1, -1))


def run_seed(seed: int) -> dict:
    cfg = GeneratorConfig(seed=seed, board_size=6, setup_preset="classic_like")
    base = generate_game(cfg)
    present = {
        piece.current_type_id
        for row in base.ruleset.initial_position for piece in row if piece
    }
    eligible = []
    for piece_type in base.ruleset.piece_types:
        if (piece_type.is_anchor or piece_type.is_promotable
                or piece_type.type_id not in present or not piece_type.movement_atoms):
            continue
        existing_ray_directions = {
            atom.direction for atom in piece_type.movement_atoms
            if isinstance(atom, RayAtom)
        }
        eligible.extend(
            (piece_type, direction) for direction in DIRECTIONS
            if direction not in existing_ray_directions
        )

    rows = []
    for ordinal, (piece_type, direction) in enumerate(eligible):
        name = f"ray_direction_screen_{ordinal:03d}"
        action = RuleSemanticAction(
            name=name,
            type_ids=(piece_type.type_id,),
            geometry=RuleGeometrySpec(kind="ray", direction=direction,
                                      min_steps=1, max_steps=3),
            target_relation="empty",
            composition="augment",
            effects=(RuleActionEffect(
                "move", from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            ),),
            invariants=(RuleInvariant("own_anchor_safe"),),
        )
        compiled = compile_ruleset_for_execution(
            replace(base.ruleset, semantic_actions=(action,))
        )
        pattern_id = next(
            pattern.pattern_id for pattern in compiled.ir.patterns
            if pattern.pattern_id.endswith(name)
        )
        session = GameSession(compiled)
        count = sum(move.pattern_id == pattern_id for move in session.legal_actions())
        filters = run_soft_filters(
            cfg, compiled,
            {piece.type_id: piece for piece in compiled.piece_types},
        )
        opening_filter = next(
            item for item in filters if item.name == "opening_legal_moves_in_range"
        )
        rows.append({
            "type_id": piece_type.type_id,
            "direction": list(direction),
            "candidate_actions": count,
            "opening_filter_pass": opening_filter.passed,
            "opening_filter_detail": opening_filter.detail,
        })
    return {"seed": seed, "pairs": rows}


def main() -> None:
    roots = [run_seed(seed) for seed in SEEDS]
    pairs = [pair for root in roots for pair in root["pairs"]]
    root_summaries = []
    for root in roots:
        root_pairs = root["pairs"]
        root_summaries.append({
            "seed": root["seed"],
            "eligible_pairs": len(root_pairs),
            "pairs_with_candidates": sum(
                pair["candidate_actions"] > 0 for pair in root_pairs
            ),
            "direction_pairs_with_candidates": {
                str(direction): sum(
                    pair["candidate_actions"] > 0
                    for pair in root_pairs if tuple(pair["direction"]) == direction
                )
                for direction in DIRECTIONS
            },
            "opening_filter_failures": sum(
                not pair["opening_filter_pass"] for pair in root_pairs
            ),
        })
    print(json.dumps({
        "question": "On the frozen roots, is zero opening exposure specific to direct ray direction (1,0)?",
        "roots": root_summaries,
        "summary": {
            "roots": len(roots),
            "eligible_pairs": len(pairs),
            "pairs_with_candidates": sum(pair["candidate_actions"] > 0 for pair in pairs),
            "roots_with_any_candidate_pair": sum(
                any(pair["candidate_actions"] > 0 for pair in root["pairs"])
                for root in roots
            ),
            "opening_filter_failures": sum(
                not pair["opening_filter_pass"] for pair in pairs
            ),
            "direction_counts_with_exposure": {
                str(direction): sum(
                    pair["candidate_actions"] > 0
                    for pair in pairs if tuple(pair["direction"]) == direction
                )
                for direction in DIRECTIONS
            },
        },
        "limitations": "Fixed-root initial-action feasibility only; no post-move reachability, games, outcome, search, training, value calibration or utility claim.",
    }, indent=2))


if __name__ == "__main__":
    main()
