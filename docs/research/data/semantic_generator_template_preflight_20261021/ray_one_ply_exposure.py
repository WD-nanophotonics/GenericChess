"""One-ply legality availability for the fixed absent-ray universe."""
from __future__ import annotations

import json
from dataclasses import replace

from generic_chess.core.actions import action_to_dict
from generic_chess.core.movement import RayAtom
from generic_chess.generation.config import GeneratorConfig
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


def run_seed(seed: int) -> list[dict]:
    base = generate_game(GeneratorConfig(
        seed=seed, board_size=6, setup_preset="classic_like"))
    present = {piece.current_type_id for row in base.ruleset.initial_position
               for piece in row if piece}
    eligible = []
    for piece_type in base.ruleset.piece_types:
        existing = {atom.direction for atom in piece_type.movement_atoms
                    if isinstance(atom, RayAtom)}
        if (not piece_type.is_anchor and not piece_type.is_promotable
                and piece_type.type_id in present and piece_type.movement_atoms):
            eligible.extend((piece_type, direction) for direction in DIRECTIONS
                            if direction not in existing)

    rows = []
    for index, (piece_type, direction) in enumerate(eligible):
        name = f"ray_pair_{index:03d}"
        action = RuleSemanticAction(
            name=name, type_ids=(piece_type.type_id,),
            geometry=RuleGeometrySpec(kind="ray", direction=direction,
                                      min_steps=1, max_steps=3),
            target_relation="empty", composition="augment",
            effects=(RuleActionEffect("move", from_ref=RuleSquareRef("source"),
                                      to_ref=RuleSquareRef("target")),),
            invariants=(RuleInvariant("own_anchor_safe"),),
        )
        compiled = compile_ruleset_for_execution(
            replace(base.ruleset, semantic_actions=(action,)))
        pattern_id = next(pattern.pattern_id for pattern in compiled.ir.patterns
                          if pattern.pattern_id.endswith(name))
        root = GameSession(compiled)
        root_actions = root.legal_actions()
        root_ray_count = sum(a.pattern_id == pattern_id for a in root_actions)
        reply_rows = []
        reply_live_states = 0
        reply_terminal_states = 0
        for first_action in root_actions:
            reply = GameSession(compiled)
            reply.submit(first_action)
            if reply.result.status.name != "ONGOING":
                reply_terminal_states += 1
                continue
            reply_live_states += 1
            actions = reply.legal_actions()
            matches = sum(a.pattern_id == pattern_id for a in actions)
            if matches:
                reply_rows.append({
                    "first_action": action_to_dict(first_action),
                    "reply_ray_action_count": matches,
                    "reply_side": reply.state.position.side_to_move,
                })
        rows.append({
            "type_id": piece_type.type_id,
            "direction": list(direction),
            "root_ray_action_count": root_ray_count,
            "root_legal_action_count": len(root_actions),
            "reply_live_states": reply_live_states,
            "reply_terminal_states": reply_terminal_states,
            "reply_root_actions_with_ray": len(reply_rows),
            "reply_ray_action_total": sum(r["reply_ray_action_count"]
                                           for r in reply_rows),
            "one_ply_recovered": root_ray_count == 0 and bool(reply_rows),
            "reply_examples": reply_rows[:3],
        })
    return rows


def main() -> None:
    roots = [{"seed": seed, "pairs": run_seed(seed)} for seed in SEEDS]
    rows = [pair for root in roots for pair in root["pairs"]]
    no_root = [r for r in rows if r["root_ray_action_count"] == 0]
    recovered = [r for r in no_root if r["one_ply_recovered"]]
    summary = {
        "roots": len(roots),
        "pairs": len(rows),
        "pairs_with_root_ray_action": len(rows) - len(no_root),
        "no_root_pairs": len(no_root),
        "no_root_pairs_recovered_after_one_legal_action": len(recovered),
        "no_root_pairs_still_without_reply_action": len(no_root) - len(recovered),
        "first_action_transitions_examined": sum(r["root_legal_action_count"]
                                                  for r in rows),
        "reply_terminal_states": sum(r["reply_terminal_states"] for r in rows),
        "reply_states_with_matching_ray_actions": sum(
            r["reply_root_actions_with_ray"] for r in rows),
        "limitations": "One legal root-action transition only; no policy, probability, deeper play, outcomes, search, training, value or utility claim.",
    }
    print(json.dumps({"question": "Does a one-ply legality horizon recover absent rays?",
                      "summary": summary, "roots": roots}, indent=2))


if __name__ == "__main__":
    main()
