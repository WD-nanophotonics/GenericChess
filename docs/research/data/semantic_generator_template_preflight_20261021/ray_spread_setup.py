"""Test whether a wider three-rank setup unlocks additional ray directions."""
from __future__ import annotations

import json
import random
from dataclasses import replace

from generic_chess.core.pieces import Piece
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import _initial_anchors_attacked, generate_game
from generic_chess.rules.compiler import compile_ruleset, compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleActionEffect, RuleGeometrySpec, RuleInvariant, RuleSemanticAction,
    RuleSquareRef,
)
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.session.session import GameSession
from ray_setup_sensitivity import eligible_pairs

SEEDS = tuple(range(202610431, 202610439))
MAX_LAYOUT_ATTEMPTS = 256


def layout_for_seed(base, seed: int) -> dict:
    n = base.ruleset.board_size
    types = {pt.type_id: pt for pt in base.ruleset.piece_types}
    ordinary_ids = tuple(pt.type_id for pt in base.ruleset.piece_types
                         if not pt.is_anchor)
    orbit_representatives = [(rank, file) for rank in range(n // 2)
                             for file in range(n)]
    attempts = []
    for attempt in range(MAX_LAYOUT_ATTEMPTS):
        rng = random.Random(seed * 65537 + 0x5A7E + attempt * 104729)
        selected = sorted(rng.sample(orbit_representatives, 2 * n))
        anchor_square = rng.choice(selected)
        available = list(ordinary_ids)
        rng.shuffle(available)
        assigned = {}
        for square in selected:
            if square == anchor_square:
                assigned[square] = "K"
            else:
                assigned[square] = available.pop() if available else rng.choice(ordinary_ids)
        rows = [[None] * n for _ in range(n)]
        for (rank, file), type_id in assigned.items():
            rows[rank][file] = Piece(owner=0, base_type_id=type_id,
                                     current_type_id=type_id, promoted=False)
            rows[n - 1 - rank][n - 1 - file] = Piece(
                owner=1, base_type_id=type_id, current_type_id=type_id,
                promoted=False)
        rows = tuple(tuple(row) for row in rows)
        if _initial_anchors_attacked(n, rows, types):
            attempts.append({"attempt": attempt, "reason": "anchor_attacked"})
            continue
        metadata = dict(base.ruleset.metadata)
        metadata["setup_preset"] = "spread_three_rank_fixture"
        ruleset = replace(base.ruleset, initial_position=rows, metadata=metadata)
        compiled = compile_ruleset(ruleset)
        from generic_chess.core.movegen import legal_actions_from_position
        opening_count = len(legal_actions_from_position(compiled.initial_position,
                                                        compiled))
        if not 1 <= opening_count <= 256:
            attempts.append({"attempt": attempt, "reason": "opening_move_count",
                             "count": opening_count})
            continue
        return {"ruleset": ruleset, "attempt": attempt,
                "opening_count": opening_count, "rejections": attempts}
    return {"ruleset": None, "failure": "no_valid_layout_within_256",
            "rejections": attempts}


def exposure_with_check(ruleset, pairs):
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
        session = GameSession(compiled)
        legal = session.legal_actions()
        engine = semantic_engine_for(compiled)
        position = session.state.position
        rows.append({
            "type_id": type_id, "direction": list(direction),
            "type_present": any(piece is not None and
                                 piece.current_type_id == type_id
                                 for piece in position.board),
            "root_legal_action_count": len(legal),
            "matching_ray_action_count": sum(a.pattern_id == pattern_id
                                               for a in legal),
            "side0_in_check": engine.in_check(position, 0),
            "side1_in_check": engine.in_check(position, 1),
        })
    return rows


def main():
    roots = []
    for seed in SEEDS:
        base = generate_game(GeneratorConfig(seed=seed, board_size=6,
                                              setup_preset="classic_like"))
        pairs = eligible_pairs(base)
        layout = layout_for_seed(base, seed)
        root = {k: v for k, v in layout.items() if k != "ruleset"}
        root.update({"seed": seed, "pairs": (exposure_with_check(layout["ruleset"], pairs)
                                               if layout["ruleset"] is not None
                                               else None)})
        roots.append(root)
    rows = [r for root in roots for r in (root["pairs"] or [])]
    directions = sorted({tuple(r["direction"]) for r in rows})
    summary = {
        "roots": len(roots), "accepted_layouts": sum(r["pairs"] is not None
                                                      for r in roots),
        "pairs": len(rows),
        "present_type_pairs": sum(r["type_present"] for r in rows),
        "root_exposed_pairs": sum(r["matching_ray_action_count"] > 0
                                   for r in rows),
        "root_unexposed_pairs": sum(r["matching_ray_action_count"] == 0
                                     for r in rows),
        "semantic_root_checks": {
            "side0_in_check_rows": sum(r["side0_in_check"] for r in rows),
            "side1_in_check_rows": sum(r["side1_in_check"] for r in rows),
            "any_side_in_check_rows": sum(r["side0_in_check"] or r["side1_in_check"]
                                           for r in rows),
        },
        "exposure_by_direction": {
            str(d): {"pairs": sum(tuple(r["direction"]) == d for r in rows),
                     "exposed": sum(tuple(r["direction"]) == d and
                                    r["matching_ray_action_count"] > 0 for r in rows)}
            for d in directions
        },
        "layout_rejections": {
            "anchor_attacked": sum(item["reason"] == "anchor_attacked"
                                    for root in roots for item in root["rejections"]),
            "opening_move_count": sum(item["reason"] == "opening_move_count"
                                       for root in roots for item in root["rejections"]),
        },
        "limitations": "Synthetic accepted three-rank setups only; no games, outcomes, search or utility.",
    }
    print(json.dumps({"question": "Does a three-rank setup unlock additional ray directions?",
                      "summary": summary, "roots": roots}, indent=2))


if __name__ == "__main__":
    main()
