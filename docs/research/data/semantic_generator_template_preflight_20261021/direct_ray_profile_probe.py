"""Fresh-seed screen for an unguarded, statically projectable semantic ray."""
from __future__ import annotations

import json
import random
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
from generic_chess.ai.evaluation import EvaluationConfig
from generic_chess.ai.evaluation.analyzer import profile_movement_atoms
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.session.session import GameSession


SEEDS = tuple(range(202610431, 202610439))
NOVEL_RAY = RayAtom((1, 0), 3)


def run_seed(seed: int) -> dict:
    cfg = GeneratorConfig(seed=seed, board_size=6, setup_preset="classic_like")
    base = generate_game(cfg)
    present = {piece.current_type_id for row in base.ruleset.initial_position
               for piece in row if piece is not None}
    eligible = [piece for piece in base.ruleset.piece_types
                if (not piece.is_anchor and not piece.is_promotable
                    and piece.type_id in present and piece.movement_atoms
                    and not any(isinstance(atom, RayAtom)
                                and atom.direction == (1, 0)
                                for atom in piece.movement_atoms))]
    if not eligible:
        return {"seed": seed, "selection": "no_eligible_present_type"}
    chosen = random.Random(seed ^ 0xA651).choice(sorted(eligible, key=lambda p: p.type_id))
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
    ruleset = replace(base.ruleset, semantic_actions=(action,))
    compiled = compile_ruleset_for_execution(ruleset)
    filters = run_soft_filters(
        cfg, compiled, {piece.type_id: piece for piece in ruleset.piece_types}
    )
    semantic_profile = build_ruleset_profile(compiled, EvaluationConfig())
    legacy_profile = build_ruleset_profile(base.compiled_ruleset, EvaluationConfig())
    session = GameSession(compiled)
    candidates = [move for move in session.legal_actions()
                  if move.pattern_id == "sem_00_direct_ray_profile_probe"]
    atoms = profile_movement_atoms(compiled, chosen.type_id)
    return {
        "seed": seed,
        "selected_type": chosen.type_id,
        "type_present_at_root": True,
        "filter_pass": all(item.passed for item in filters),
        "failed_filters": [item.name for item in filters if not item.passed],
        "candidate_actions": len(candidates),
        "profile_contains_novel_ray": NOVEL_RAY in atoms,
        "legacy_board_value": legacy_profile.board_value_by_type[chosen.type_id],
        "semantic_board_value": semantic_profile.board_value_by_type[chosen.type_id],
        "board_value_delta": (semantic_profile.board_value_by_type[chosen.type_id]
                              - legacy_profile.board_value_by_type[chosen.type_id]),
        "native_executable": compiled.ir.capabilities.native_executable,
        "core_executable": compiled.ir.capabilities.new_ir_core_executable,
    }


def main() -> None:
    results = [run_seed(seed) for seed in SEEDS]
    print(json.dumps({
        "seeds": list(SEEDS),
        "template": "unguarded direct ray (1,0), steps 1..3, empty target, move effect, own_anchor_safe",
        "limitations": "Construction and static-profile sensitivity only; not calibrated value, utility, full-domain support or outcome evidence.",
        "results": results,
        "summary": {
            "eligible_roots": sum("selection" not in row for row in results),
            "filter_pass_roots": sum(row.get("filter_pass") is True for row in results),
            "roots_with_candidate": sum(row.get("candidate_actions", 0) > 0 for row in results),
            "profile_contains_novel_ray": sum(row.get("profile_contains_novel_ray") is True for row in results),
            "nonzero_board_value_delta": sum(row.get("board_value_delta", 0) != 0 for row in results),
            "games": 0, "searches": 0, "training_updates": 0,
        },
    }, indent=2))


if __name__ == "__main__":
    main()
