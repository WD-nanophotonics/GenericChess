"""Explain the zero root candidates in the frozen direct-ray screen."""
from __future__ import annotations

import json
import random
from dataclasses import replace

from generic_chess.core.coordinates import Square, index_to_square, square_to_index
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


def run_seed(seed: int) -> dict:
    cfg = GeneratorConfig(seed=seed, board_size=6, setup_preset="classic_like")
    base = generate_game(cfg)
    board = base.ruleset.initial_position
    present = {piece.current_type_id for row in board for piece in row if piece}
    eligible = []
    for piece_type in base.ruleset.piece_types:
        already_has_ray = any(
            isinstance(atom, RayAtom) and atom.direction == (1, 0)
            for atom in piece_type.movement_atoms
        )
        if (not piece_type.is_anchor and not piece_type.is_promotable
                and piece_type.type_id in present and piece_type.movement_atoms
                and not already_has_ray):
            eligible.append(piece_type)
    chosen = random.Random(seed ^ 0xA651).choice(
        sorted(eligible, key=lambda piece_type: piece_type.type_id)
    )
    action = RuleSemanticAction(
        name="direct_ray_profile_probe",
        type_ids=(chosen.type_id,),
        geometry=RuleGeometrySpec(kind="ray", direction=(1, 0),
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
    pattern = next(pattern for pattern in compiled.ir.patterns
                   if pattern.pattern_id == "sem_00_direct_ray_profile_probe")
    geometry = compiled.ir.geometry[pattern.geometry_ids[0]]
    source_paths = []
    for row_index, row in enumerate(board):
        for file_index, piece in enumerate(row):
            if piece is None or piece.current_type_id != chosen.type_id:
                continue
            source = square_to_index(Square(file_index, 5 - row_index), 6)
            targets = geometry.paths[str(piece.owner)][source]
            path = []
            first_blocker = None
            for target_index in targets:
                square = index_to_square(target_index, 6)
                occupant = board[5 - square.rank][square.file]
                item = {
                    "square": str(square),
                    "occupant": None if occupant is None else {
                        "owner": occupant.owner,
                        "type": occupant.current_type_id,
                    },
                }
                path.append(item)
                if occupant is not None:
                    first_blocker = item
                    break
            source_paths.append({
                "owner": piece.owner,
                "source": str(index_to_square(source, 6)),
                "path_until_first_blocker": path,
                "first_blocker": first_blocker,
            })
    session = GameSession(compiled)
    semantic_candidates = [
        move for move in session.legal_actions()
        if move.pattern_id == "sem_00_direct_ray_profile_probe"
    ]
    filters = run_soft_filters(
        cfg, compiled, {piece.type_id: piece for piece in compiled.piece_types}
    )
    return {
        "seed": seed,
        "selected_type": chosen.type_id,
        "sources": source_paths,
        "first_step_blocked_at_every_source": bool(source_paths) and all(
            source["first_blocker"] is not None for source in source_paths
        ),
        "semantic_root_candidates": len(semantic_candidates),
        "soft_filters": [
            {"name": item.name, "passed": item.passed, "detail": item.detail}
            for item in filters
        ],
    }


def main() -> None:
    rows = [run_seed(seed) for seed in range(202610431, 202610439)]
    compact = []
    for row in rows:
        opening_filter = next(
            item for item in row["soft_filters"]
            if item["name"] == "opening_legal_moves_in_range"
        )
        compact.append({
            "seed": row["seed"],
            "selected_type": row["selected_type"],
            "source_count": len(row["sources"]),
            "all_sources_blocked_at_first_step": row[
                "first_step_blocked_at_every_source"
            ],
            "first_blockers": sorted({
                f"{source['first_blocker']['square']}:{source['first_blocker']['occupant']['owner']}:"
                f"{source['first_blocker']['occupant']['type']}"
                for source in row["sources"]
            }),
            "semantic_root_candidates": row["semantic_root_candidates"],
            "opening_filter_pass": opening_filter["passed"],
            "opening_filter_detail": opening_filter["detail"],
        })
    print(json.dumps({
        "question": "Why did all eight frozen direct-ray roots have zero semantic candidates while filters passed?",
        "source_interpretation": (
            "The ray geometry is owner-relative and has max_steps=3."
            " The frozen initial placements block the first step for every selected source."
            " The aggregate opening-legal-move filter does not require a candidate from each semantic pattern."
        ),
        "roots": compact,
        "summary": {
            "roots": len(rows),
            "all_selected_sources_first_step_blocked": all(
                row["first_step_blocked_at_every_source"] for row in rows
            ),
            "roots_with_semantic_candidate": sum(
                row["semantic_root_candidates"] > 0 for row in rows
            ),
            "opening_move_filter_passes": sum(
                any(item["name"] == "opening_legal_moves_in_range" and item["passed"]
                    for item in row["soft_filters"])
                for row in rows
            ),
        },
        "limitations": "Root-specific obstruction and filter-scope diagnosis; no play, post-move reachability, value calibration, utility, or all-domain claim.",
    }, indent=2))


if __name__ == "__main__":
    main()
