"""Reproduce the P-exposure/decision-sensitivity preflight without games."""
from __future__ import annotations
import json, random
from dataclasses import replace
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
from rule_semantics_ir_fixtures import _own_anchor, _ref
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.schema import RuleSemanticAction, RuleGeometrySpec, RuleActionEffect
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.execution import ExecutableSemanticRuleset
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus

GENERATOR_SEEDS = (202610301, 202610302, 202610303, 202610304)
PREFIX_SEED_OFFSET = 900000
NODE_CAP = 4096

def compound_action():
    return RuleSemanticAction(
        name="move_and_shift_adjacent_friendly", type_ids=("P",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 1)),
        target_relation="empty", composition="augment",
        effects=(
            RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),
            RuleActionEffect("shift", from_ref=_ref("offset_from_source", offset=(0, 1)),
                             to_ref=_ref("offset_from_source", offset=(0, 2)), piece_owner="self"),
        ), invariants=_own_anchor(),
    )

def main():
    cfg = EvaluationConfig()
    rows = []
    for seed in GENERATOR_SEEDS:
        base = generate_game(GeneratorConfig(seed=seed, board_size=4,
                                            setup_preset="bilateral_random", allow_hybrid=True))
        initial_p = sum(p is not None and p.current_type_id == "P"
                        for side in base.ruleset.initial_position for p in side)
        if initial_p == 0:
            raise RuntimeError(f"preselected seed {seed} lost P-start eligibility")
        rules = replace(base.ruleset, semantic_actions=(compound_action(),))
        compiled = ExecutableSemanticRuleset.from_compiled(compile_semantic_ruleset(rules))
        candidate = build_ruleset_profile(compiled, cfg)
        control = build_ruleset_profile(compiled._legacy_compiled, cfg)
        session = GameSession(compiled)
        prefix_rng = random.Random(seed + PREFIX_SEED_OFFSET)
        prefix = []
        for _ in range(12):
            if session.result.status is not SessionStatus.ONGOING:
                break
            legal = sorted(session.legal_actions(), key=str)
            if not legal:
                break
            action = prefix_rng.choice(legal)
            prefix.append(str(action))
            session.submit(action)
        position = session.state.position
        semantic = [str(a) for a in session.legal_actions()
                    if getattr(a, "pattern_id", "").startswith("sem_")]
        p_board = sum(p is not None and p.current_type_id == "P" for p in position.board)
        p_hand = sum(dict(h.counts).get("P", 0) for h in position.hands)
        root = {
            "generator_seed": seed,
            "prefix_seed": seed + PREFIX_SEED_OFFSET,
            "base_fingerprint": base.compiled_ruleset.ruleset_fingerprint,
            "augmented_fingerprint": compiled.ruleset_fingerprint,
            "initial_P_count": initial_p,
            "prefix": prefix,
            "prefix_plies": len(prefix),
            "status": session.result.status.value,
            "side_to_move": position.side_to_move,
            "board_P_count": p_board,
            "hand_P_count": p_hand,
            "legal_semantic_actions": semantic,
            "legal_action_count": len(session.legal_actions()),
            "candidate_P_board": candidate.board_value_by_type.get("P"),
            "control_P_board": control.board_value_by_type.get("P"),
            "candidate_P_hand": candidate.hand_value_by_base_type.get("P"),
            "control_P_hand": control.hand_value_by_base_type.get("P"),
            "candidate_static_score": Evaluator(compiled, candidate, cfg).evaluate(session.state),
            "control_static_score": Evaluator(compiled, control, cfg).evaluate(session.state),
        }
        if root["status"] != "ongoing" or len(prefix) != 12:
            raise RuntimeError(f"preselected seed {seed} did not yield the fixed 12-ply ongoing root")
        search_rows = []
        for label, profile in (("candidate", candidate), ("control", control)):
            player = AlphaBetaPlayer(
                compiled, evaluator_override=Evaluator(compiled, profile, cfg),
                use_tt=False, use_ordering=False,
                tuning=SearchTuning(use_root_tactical=False),
            )
            decision = player.choose_action(
                session, SearchLimits(max_depth=2, max_nodes=NODE_CAP, quiescence_max_depth=0)
            )
            search_rows.append({
                "arm": label,
                "action": str(decision.action),
                "score": decision.score,
                "depth": decision.completed_depth,
                "nodes": decision.nodes + decision.qnodes,
                "stop": decision.termination_reason,
                "pv": [str(a) for a in decision.principal_variation],
            })
        root["search"] = search_rows
        rows.append(root)
    result = {
        "question": "Do the first four fresh P-start generated rules expose this recombined profile contrast in a legal compound action or a depth-2 action choice?",
        "selection": "first four P-start generated rules in fixed block 202610301-202610304; deterministic 12-ply legal prefix RNG = generator seed + 900000; no selection on evaluations, actions, or game outcomes",
        "comparison": "same augmented ruleset/state per pair; candidate profile from compiled semantic action versus legacy-atom-reconstructed profile; public AlphaBeta D2, TT/order/root-tactical/qsearch disabled, 4096 node ceiling",
        "games_run": 0,
        "roots": rows,
        "decision": "close without a utility panel: all four D2 action/PV choices match and none exposes a legal compound action; score differences alone do not show usefulness",
        "limitations": ["four generated rules and fixed 12-ply roots only", "finite action sensitivity is not game utility or a validated static price", "no broad semantic-action or generic-domain claim"],
    }
    out = Path("docs/research/data/semantic_generated_substrate_utility_preflight_20261020.json")
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(out), "games_run": 0,
                      "roots": [{"seed": r["generator_seed"], "P": r["board_P_count"] + r["hand_P_count"],
                                 "semantic_actions": len(r["legal_semantic_actions"]),
                                 "candidate_score": r["search"][0]["score"],
                                 "control_score": r["search"][1]["score"],
                                 "actions_match": r["search"][0]["action"] == r["search"][1]["action"],
                                 "depths": [x["depth"] for x in r["search"]]} for r in rows]}, indent=2))

if __name__ == "__main__":
    main()
