"""Hold generated movement genomes fixed while varying valid root layouts."""
from __future__ import annotations

import json
import random
from dataclasses import replace

from generic_chess.core.movegen import legal_actions_from_position
from generic_chess.core.movement import RayAtom
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import _initial_anchors_attacked, generate_game
from generic_chess.generation.setup_generator import build_initial_setup
from generic_chess.rules.compiler import compile_ruleset, compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleActionEffect, RuleGeometrySpec, RuleInvariant, RuleSemanticAction,
    RuleSquareRef,
)
from generic_chess.session.session import GameSession

SEEDS = tuple(range(202610431, 202610439))
DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1),
              (1, 1), (1, -1), (-1, 1), (-1, -1))
PRESETS = ("bilateral_random", "free_random")
MAX_LAYOUT_ATTEMPTS = 64


def setup_rng_seed(seed: int, preset: str, attempt: int) -> int:
    tag = 0xB11A if preset == "bilateral_random" else 0xF2EE
    return (seed * 1009 + tag + attempt * 7919) & 0x7FFFFFFF


def select_valid_layout(base, seed: int, preset: str) -> dict:
    n = base.ruleset.board_size
    ids = tuple(pt.type_id for pt in base.ruleset.piece_types if not pt.is_anchor)
    types = {pt.type_id: pt for pt in base.ruleset.piece_types}
    attempts = []
    for attempt in range(MAX_LAYOUT_ATTEMPTS):
        rng_seed = setup_rng_seed(seed, preset, attempt)
        rows = build_initial_setup(random.Random(rng_seed), preset, n, ids)
        if _initial_anchors_attacked(n, rows, types):
            attempts.append({"attempt": attempt, "reason": "anchor_attacked"})
            continue
        metadata = dict(base.ruleset.metadata)
        metadata["setup_preset"] = preset
        candidate_ruleset = replace(base.ruleset, initial_position=rows,
                                     metadata=metadata)
        compiled = compile_ruleset(candidate_ruleset)
        opening_count = len(legal_actions_from_position(
            compiled.initial_position, compiled))
        if not (1 <= opening_count <= 256):
            attempts.append({"attempt": attempt,
                             "reason": "opening_move_count",
                             "count": opening_count})
            continue
        return {"ruleset": candidate_ruleset, "compiled": compiled,
                "attempt": attempt, "rng_seed": rng_seed,
                "opening_count": opening_count, "rejections": attempts}
    return {"ruleset": None, "compiled": None,
            "rejections": attempts, "failure": "no_valid_layout_within_64"}


def eligible_pairs(base):
    present = {p.current_type_id for row in base.ruleset.initial_position
               for p in row if p}
    pairs = []
    for pt in base.compiled_ruleset.piece_types:
        existing = {a.direction for a in pt.movement_atoms
                    if isinstance(a, RayAtom)}
        if (not pt.is_anchor and not pt.is_promotable and pt.type_id in present
                and pt.movement_atoms):
            pairs.extend((pt.type_id, direction) for direction in DIRECTIONS
                         if direction not in existing)
    return pairs


def exposure(ruleset, pairs):
    rows = []
    for index, (type_id, direction) in enumerate(pairs):
        name = f"ray_pair_{index:03d}"
        action = RuleSemanticAction(
            name=name, type_ids=(type_id,),
            geometry=RuleGeometrySpec(kind="ray", direction=direction,
                                      min_steps=1, max_steps=3),
            target_relation="empty", composition="augment",
            effects=(RuleActionEffect("move", from_ref=RuleSquareRef("source"),
                                      to_ref=RuleSquareRef("target")),),
            invariants=(RuleInvariant("own_anchor_safe"),),
        )
        compiled = compile_ruleset_for_execution(
            replace(ruleset, semantic_actions=(action,)))
        pattern_id = next(p.pattern_id for p in compiled.ir.patterns
                          if p.pattern_id.endswith(name))
        legal = GameSession(compiled).legal_actions()
        type_present = any(piece is not None and piece.current_type_id == type_id
                           for piece in compiled.initial_position.board)
        rows.append({
            "type_id": type_id, "direction": list(direction),
            "type_present": type_present,
            "root_legal_action_count": len(legal),
            "matching_ray_action_count": sum(a.pattern_id == pattern_id
                                               for a in legal),
        })
    return rows


def summarize(layouts):
    result = {}
    for preset in ("classic_like", *PRESETS):
        rows = [r for layout in layouts if layout["preset"] == preset
                for r in layout["pairs"]]
        result[preset] = {
            "accepted_layouts": sum(layout["pairs"] is not None
                                     for layout in layouts if layout["preset"] == preset),
            "pairs": len(rows),
            "type_present_pairs": sum(r["type_present"] for r in rows),
            "root_exposed_pairs": sum(r["matching_ray_action_count"] > 0
                                       for r in rows),
            "root_unexposed_pairs": sum(r["matching_ray_action_count"] == 0
                                         for r in rows),
            "exposure_by_direction": {
                str(direction): {
                    "pairs": sum(tuple(r["direction"]) == direction for r in rows),
                    "exposed": sum(tuple(r["direction"]) == direction and
                                   r["matching_ray_action_count"] > 0 for r in rows),
                } for direction in DIRECTIONS
            },
        }
    return result


def main():
    layouts = []
    for seed in SEEDS:
        base = generate_game(GeneratorConfig(
            seed=seed, board_size=6, setup_preset="classic_like"))
        pairs = eligible_pairs(base)
        layouts.append({"seed": seed, "preset": "classic_like",
                        "attempt": 0, "opening_count": base.generation_report.opening_legal_move_count,
                        "pairs": exposure(base.ruleset, pairs)})
        for preset in PRESETS:
            selected = select_valid_layout(base, seed, preset)
            layout = {k: v for k, v in selected.items()
                      if k not in ("ruleset", "compiled")}
            layout.update({"seed": seed, "preset": preset})
            layout["pairs"] = (exposure(selected["ruleset"], pairs)
                               if selected["ruleset"] is not None else None)
            layouts.append(layout)
    print(json.dumps({"question": "How does root ray exposure vary across held-genome setup layouts?",
                      "summary": summarize(layouts), "layouts": layouts}, indent=2))


if __name__ == "__main__":
    main()
