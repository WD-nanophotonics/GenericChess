"""Check movement-edge overlap for frozen raw-capability plateau roots."""
from __future__ import annotations

import json
import random
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

SEEDS = (202610432, 202610435)


def edges(atoms) -> set[tuple[int, int, int]]:
    result = set()
    for owner in (0, 1):
        for source in range(36):
            for target in empty_mobility(
                6, owner, index_to_square(source, 6), atoms
            ):
                result.add((owner, source, square_to_index(target, 6)))
    return result


def run_seed(seed: int) -> dict:
    base = generate_game(GeneratorConfig(
        seed=seed, board_size=6, setup_preset="classic_like"
    ))
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
    base_atoms = profile_movement_atoms(base.compiled_ruleset, chosen.type_id)
    base_edges = edges(base_atoms)
    config = EvaluationConfig()
    base_raw = build_ruleset_profile(base.compiled_ruleset, config).piece_profiles[
        chosen.type_id
    ].raw_capability_score
    ranges = []
    prior_novel: set[tuple[int, int, int]] = set()
    prior_raw = base_raw
    for max_steps in (1, 2, 3):
        action = RuleSemanticAction(
            name="ray_plateau_overlap",
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
        atoms = profile_movement_atoms(compiled, chosen.type_id)
        combined = edges(atoms)
        novel = combined - base_edges
        raw = build_ruleset_profile(compiled, config).piece_profiles[
            chosen.type_id
        ].raw_capability_score
        ranges.append({
            "max_steps": max_steps,
            "combined_edge_count": len(combined),
            "novel_edge_count_vs_legacy": len(novel),
            "marginal_novel_edges_vs_previous_range": len(novel - prior_novel),
            "raw_capability_delta": raw - base_raw,
            "raw_delta_vs_previous_range": raw - prior_raw,
            "raw_plateau_vs_previous_range": raw == prior_raw,
            "profile_atom_signature_equal_to_legacy": atoms == base_atoms,
        })
        prior_novel = novel
        prior_raw = raw
    return {
        "seed": seed,
        "selected_type": chosen.type_id,
        "legacy_edge_count": len(base_edges),
        "ranges": ranges,
    }


def main() -> None:
    roots = [run_seed(seed) for seed in SEEDS]
    print(json.dumps({
        "question": "Do movement-edge plateaus explain the frozen raw-capability plateaus?",
        "roots": roots,
        "summary": {
            "roots": len(roots),
            "all_observed_raw_plateaus_have_zero_marginal_edges": all(
                row["marginal_novel_edges_vs_previous_range"] == 0
                for root in roots for row in root["ranges"]
                if row["raw_plateau_vs_previous_range"]
            ),
            "limitations": "Two fixed roots and one horizontal ray family; geometry graph only, no board position, outcomes, value utility or full-domain claim.",
        },
    }, indent=2))


if __name__ == "__main__":
    main()
