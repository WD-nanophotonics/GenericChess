"""Fixed-seed compile/transition probe for orthogonal history-policy support."""
from __future__ import annotations

import json
import random
from dataclasses import replace

from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleActionEffect, RuleAuxState, RuleAutomaticAdjudication,
    RuleConsecutiveActionAdjudication, RuleGeometrySpec, RuleInvariant,
    RuleNoProgressDraw, RuleRepeatedCycleTargetCondition, RuleSemanticAction,
    RuleSlotGuard, RuleSquareRef, compute_fingerprint,
)
from generic_chess.session.session import GameSession


SEED = 202610401


def base_semantic_ruleset():
    generated = generate_game(GeneratorConfig(
        seed=SEED, board_size=6, setup_preset="classic_like"
    ))
    eligible = [piece for piece in generated.ruleset.piece_types
                if not piece.is_anchor and not piece.is_promotable
                and piece.movement_atoms]
    chosen = random.Random(SEED ^ 0xA651).choice(eligible)
    families = sorted({"leap" if isinstance(atom, LeapAtom) else "ray"
                       for atom in chosen.movement_atoms})
    family = random.Random(SEED ^ 0x6E0).choice(families)
    action = RuleSemanticAction(
        name="sampled_once_audit", type_ids=(chosen.type_id,),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind=family),
        target_relation="empty", composition="augment",
        aux_state=(RuleAuxState("sampled_once", "bool", "global",
                                "persistent", 0),),
        slot_guards=(RuleSlotGuard("sampled_once", value=0),),
        effects=(
            RuleActionEffect("move", from_ref=RuleSquareRef("source"),
                             to_ref=RuleSquareRef("target")),
            RuleActionEffect("set_bool", slot_name="sampled_once", value=1),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    return generated, replace(generated.ruleset, semantic_actions=(action,))


def main():
    _, base = base_semantic_ruleset()
    profiles = {
        "default": {},
        "repeat_continuous_check": {
            "repetition_limit": 3, "repetition_policy": "continuous_check_loss"
        },
        "max_ply": {"max_ply": 64},
        "automatic_ply": {
            "automatic_adjudications": (RuleAutomaticAdjudication("auto", 256),)
        },
        "pass_adjudication": {
            "pass_enabled": True,
            "consecutive_action_adjudications": (
                RuleConsecutiveActionAdjudication("pass", 3, "DRAW"),
            ),
        },
        "repeated_cycle": {
            "repeated_cycle_target_conditions": (
                RuleRepeatedCycleTargetCondition(actor=0),
            ),
        },
        "no_progress": {"no_progress_draw": RuleNoProgressDraw(20, True)},
    }
    rows = []
    for name, changes in profiles.items():
        rules = replace(base, **changes)
        compiled = compile_ruleset_for_execution(rules)
        rows.append({
            "profile": name,
            "fingerprint": compute_fingerprint(rules),
            "native_executable": compiled.ir.capabilities.native_executable,
            "core_executable": compiled.ir.capabilities.new_ir_core_executable,
            "repetition_limit": compiled.support.repetition_limit,
            "repetition_policy": compiled.support.repetition_policy,
            "max_ply": compiled.support.max_ply,
            "automatic_count": len(compiled.ir.automatic_adjudications),
            "consecutive_count": len(compiled.ir.consecutive_action_adjudications),
            "repeated_cycle_count": len(compiled.ir.repeated_cycle_target_conditions),
            "has_no_progress": compiled.support.no_progress_draw is not None,
            "pass_enabled": compiled.support.pass_enabled,
        })

    auto_rules = replace(
        base, automatic_adjudications=(RuleAutomaticAdjudication("first-ply", 1),)
    )
    auto_compiled = compile_ruleset_for_execution(auto_rules)
    session = GameSession(auto_compiled)
    candidates = [action for action in session.legal_actions()
                  if action.pattern_id == "sem_00_sampled_once_audit"]
    assert candidates
    before = session.state.position.aux_state
    session.submit(candidates[0])
    transition = {
        "candidate_count": len(candidates),
        "native_executable": auto_compiled.ir.capabilities.native_executable,
        "core_executable": auto_compiled.ir.capabilities.new_ir_core_executable,
        "aux_changed": before != session.state.position.aux_state,
        "history_actions": len(session.history),
        "result_status": session.result.status.value,
    }
    assert transition == {
        "candidate_count": len(candidates), "native_executable": False,
        "core_executable": True, "aux_changed": True,
        "history_actions": 1, "result_status": "no_contest",
    }
    print(json.dumps({"seed": SEED, "history_profiles": rows,
                      "automatic_transition": transition}, indent=2))


if __name__ == "__main__":
    main()
