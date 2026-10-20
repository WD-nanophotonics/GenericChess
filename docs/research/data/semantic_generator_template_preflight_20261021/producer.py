"""Small source-backed feasibility screen for one semantic generator template."""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import replace

from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.filters import run_soft_filters
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleActionEffect,
    RuleAuxState,
    RuleGeometrySpec,
    RuleInvariant,
    RuleSemanticAction,
    RuleSlotGuard,
    RuleSquareRef,
)
from generic_chess.session.session import GameSession


SEEDS = tuple(range(202610401, 202610409))


def run_seed(seed: int) -> dict:
    cfg = GeneratorConfig(seed=seed, board_size=6, setup_preset="classic_like")
    base = generate_game(cfg)
    eligible = [
        pt for pt in base.ruleset.piece_types
        if not pt.is_anchor and not pt.is_promotable and pt.movement_atoms
    ]
    if not eligible:
        return {"seed": seed, "generation_attempts": base.generation_report.generation_attempts,
                "failure": "no eligible non-promotable generated piece type"}

    chosen = random.Random(seed ^ 0xA651).choice(eligible)
    families = sorted({"leap" if isinstance(atom, LeapAtom) else "ray"
                       for atom in chosen.movement_atoms})
    family = random.Random(seed ^ 0x6E0).choice(families)
    name = f"sampled_once_{seed}"
    action = RuleSemanticAction(
        name=name,
        type_ids=(chosen.type_id,),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind=family),
        target_relation="empty",
        composition="augment",
        aux_state=(RuleAuxState(
            name="sampled_once", value_kind="bool", scope="global",
            lifetime="persistent", initial=0,
        ),),
        slot_guards=(RuleSlotGuard(slot_name="sampled_once", value=0),),
        effects=(
            RuleActionEffect("move", from_ref=RuleSquareRef("source"),
                             to_ref=RuleSquareRef("target")),
            RuleActionEffect("set_bool", slot_name="sampled_once", value=1),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    ruleset = replace(base.ruleset, semantic_actions=(action,))
    # Match the supported execution boundary used by product filters/tests;
    # direct compile_semantic_ruleset returns the lower-level IR type.
    compiled = compile_ruleset_for_execution(ruleset)
    filter_results = run_soft_filters(
        cfg, compiled, {pt.type_id: pt for pt in ruleset.piece_types}
    )
    legacy_session = GameSession(base.compiled_ruleset)
    semantic_session = GameSession(compiled)
    legacy_actions = legacy_session.legal_actions()
    semantic_actions = semantic_session.legal_actions()
    candidates = [a for a in semantic_actions if a.pattern_id == f"sem_00_{name}"]
    result = {
        "seed": seed,
        "generation_attempts": base.generation_report.generation_attempts,
        "selected_type": chosen.type_id,
        "selected_geometry_family": family,
        "legacy_opening_actions": len(legacy_actions),
        "semantic_opening_actions": len(semantic_actions),
        "candidate_opening_actions": len(candidates),
        "filter_results": [{"name": x.name, "passed": x.passed, "detail": x.detail}
                           for x in filter_results],
        "aux_before": semantic_session.state.position.aux_state,
    }
    if candidates:
        semantic_session.submit(candidates[0])
        result["aux_after"] = semantic_session.state.position.aux_state
        result["aux_state_changed"] = (
            semantic_session.state.position.aux_state != result["aux_before"]
        )
        result["history_length_after_submit"] = len(semantic_session.history)
        result["submitted_pattern_id"] = candidates[0].pattern_id
    else:
        result.update({"aux_after": result["aux_before"],
                       "aux_state_changed": False,
                       "history_length_after_submit": 0,
                       "submitted_pattern_id": None})
    return result


def main() -> int:
    results = []
    for seed in SEEDS:
        try:
            results.append(run_seed(seed))
        except Exception as exc:  # preserve each seed's first failure, do not adapt
            results.append({"seed": seed, "exception": type(exc).__name__,
                            "message": str(exc)})
    payload = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "seeds": list(SEEDS),
        "results": results,
        "summary": {
            "roots_with_candidate": sum(r.get("candidate_opening_actions", 0) > 0
                                         for r in results),
            "successful_aux_transitions": sum(
                r.get("candidate_opening_actions", 0) > 0
                and r.get("aux_state_changed") is True
                and r.get("history_length_after_submit") == 1
                for r in results
            ),
            "exceptions": sum("exception" in r or "failure" in r for r in results),
            "games_run": 0,
            "searches_run": 0,
            "training_updates": 0,
        },
    }
    text = json.dumps(payload, indent=2, default=str) + "\n"
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if payload["summary"]["exceptions"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
