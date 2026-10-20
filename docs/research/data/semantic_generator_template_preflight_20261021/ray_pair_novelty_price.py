"""Jointly measure ray graph novelty, profile price, and root exposure."""
from __future__ import annotations

import json
from dataclasses import replace

from generic_chess.core.coordinates import index_to_square, square_to_index
from generic_chess.core.movement import RayAtom, empty_mobility
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleActionEffect, RuleGeometrySpec, RuleInvariant, RuleSemanticAction,
    RuleSquareRef,
)
from generic_chess.ai.evaluation import EvaluationConfig
from generic_chess.ai.evaluation.analyzer import profile_movement_atoms
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.session.session import GameSession

SEEDS = tuple(range(202610431, 202610439))
DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1),
              (1, 1), (1, -1), (-1, 1), (-1, -1))


def edge_set(atoms) -> set[tuple[int, int, int]]:
    edges = set()
    for owner in (0, 1):
        for source in range(36):
            for target in empty_mobility(
                6, owner, index_to_square(source, 6), atoms
            ):
                edges.add((owner, source, square_to_index(target, 6)))
    return edges


def run_seed(seed: int, config: EvaluationConfig) -> list[dict]:
    cfg = GeneratorConfig(seed=seed, board_size=6, setup_preset="classic_like")
    base = generate_game(cfg)
    present = {
        piece.current_type_id
        for row in base.ruleset.initial_position for piece in row if piece
    }
    eligible = []
    for piece_type in base.ruleset.piece_types:
        existing = {
            atom.direction for atom in piece_type.movement_atoms
            if isinstance(atom, RayAtom)
        }
        if (not piece_type.is_anchor and not piece_type.is_promotable
                and piece_type.type_id in present and piece_type.movement_atoms):
            eligible.extend(
                (piece_type, direction) for direction in DIRECTIONS
                if direction not in existing
            )
    base_profile = build_ruleset_profile(base.compiled_ruleset, config)
    rows = []
    for index, (piece_type, direction) in enumerate(eligible):
        name = f"ray_pair_{index:03d}"
        action = RuleSemanticAction(
            name=name, type_ids=(piece_type.type_id,),
            geometry=RuleGeometrySpec(kind="ray", direction=direction,
                                      min_steps=1, max_steps=3),
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
        base_atoms = profile_movement_atoms(base.compiled_ruleset, piece_type.type_id)
        combined_atoms = profile_movement_atoms(compiled, piece_type.type_id)
        base_edges = edge_set(base_atoms)
        combined_edges = edge_set(combined_atoms)
        pattern_id = next(
            pattern.pattern_id for pattern in compiled.ir.patterns
            if pattern.pattern_id.endswith(name)
        )
        candidates = sum(
            move.pattern_id == pattern_id
            for move in GameSession(compiled).legal_actions()
        )
        rows.append({
            "type_id": piece_type.type_id,
            "direction": list(direction),
            "candidate_actions": candidates,
            "novel_edges": len(combined_edges - base_edges),
            "raw_capability_delta": (
                profile.piece_profiles[piece_type.type_id].raw_capability_score
                - base_profile.piece_profiles[piece_type.type_id].raw_capability_score
            ),
            "selected_type_board_value_delta": (
                profile.board_value_by_type[piece_type.type_id]
                - base_profile.board_value_by_type[piece_type.type_id]
            ),
            "all_type_price_deltas": {
                type_id: profile.board_value_by_type[type_id]
                - base_profile.board_value_by_type[type_id]
                for type_id in base_profile.board_value_by_type
            },
        })
    return rows


def main() -> None:
    config = EvaluationConfig()
    roots = [{"seed": seed, "pairs": run_seed(seed, config)} for seed in SEEDS]
    pairs = [pair for root in roots for pair in root["pairs"]]
    direction_summary = {}
    for direction in DIRECTIONS:
        selected = [pair for pair in pairs if tuple(pair["direction"]) == direction]
        direction_summary[str(direction)] = {
            "pairs": len(selected),
            "with_candidate": sum(pair["candidate_actions"] > 0 for pair in selected),
            "with_novel_edges": sum(pair["novel_edges"] > 0 for pair in selected),
            "with_raw_price_change": sum(
                abs(pair["raw_capability_delta"]) > 1e-12 for pair in selected
            ),
            "with_selected_normalized_price_change": sum(
                pair["selected_type_board_value_delta"] != 0 for pair in selected
            ),
        }
    zero_novel = [pair for pair in pairs if pair["novel_edges"] == 0]
    print(json.dumps({
        "question": "Do finite-board graph novelty, price delta and opening exposure agree across absent rays?",
        "roots": roots,
        "summary": {
            "roots": len(roots),
            "pairs": len(pairs),
            "pairs_with_candidate": sum(pair["candidate_actions"] > 0 for pair in pairs),
            "pairs_with_novel_edges": sum(pair["novel_edges"] > 0 for pair in pairs),
            "zero_novel_pairs": len(zero_novel),
            "zero_novel_with_raw_price_change": sum(
                abs(pair["raw_capability_delta"]) > 1e-12 for pair in zero_novel
            ),
            "direction_summary": direction_summary,
            "limitations": "Frozen 6x6 roots and finite catalogue only; no post-move reachability, outcomes, search, training, calibration, or utility claim.",
        },
    }, indent=2))


if __name__ == "__main__":
    main()
