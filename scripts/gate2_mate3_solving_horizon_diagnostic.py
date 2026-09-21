"""Gate 2: disambiguate the corrected Chess mate-in-three failure."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.search import reference_minimax
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.gate1_known_game_backend_equivalence import _gc_chess_uci
from scripts.gate2_merged_benchmark import (
    _fixed_state_from_position,
    _forced_mate_in_exactly_three,
    _make_player,
    _session_with_state,
    _successors,
)


FEN = "2r5/4np2/1p1k2p1/p1R1br2/Pp1P3p/3QPP2/1B2N2P/4K2R w - - 12 41"
EXPECTED_UCI = "d4e5"


def _decision(compiled, state, profile, config, depth):
    player = _make_player(compiled, profile, config)
    result = player.choose_action(
        _session_with_state(compiled, state, (state.position,)),
        SearchLimits(
            max_depth=depth,
            max_nodes=None,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
        ),
    )
    return {
        "selected_action": None if result.action is None else action_to_dict(result.action),
        "selected_uci": None if result.action is None else _gc_chess_uci(result.action),
        "root_score": result.score,
        "completed_depth": result.completed_depth,
        "nodes": result.nodes + result.qnodes,
        "termination_reason": result.termination_reason,
    }


def run_diagnostic():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    state = _fixed_state_from_position(compiled, position_from_fen(FEN, compiled))
    forced = tuple(
        action
        for action, _child in _successors(state, compiled)
        if _forced_mate_in_exactly_three(state, action, compiled)
    )
    forced_uci = [_gc_chess_uci(action) for action in forced]
    ground_truth = {
        "fen": FEN,
        "forced_action_count": len(forced),
        "forced_actions": [action_to_dict(action) for action in forced],
        "forced_uci": forced_uci,
        "expected_uci": EXPECTED_UCI,
        "display_action": "d4xe5",
        "passed": len(forced) == 1 and forced_uci == [EXPECTED_UCI],
    }
    result = {
        "status": "PASS",
        "classification": None,
        "ground_truth": ground_truth,
        "searches": {},
        "exact_depth3_control": None,
        "compute": {
            "production_searches": 0,
            "exact_controls": 0,
            "max_depth": 3,
            "node_cap": None,
        },
    }
    if not ground_truth["passed"]:
        result["status"] = "HARD_FAILURE"
        result["classification"] = "GATE2_MATE3_GROUND_TRUTH_REPRODUCTION_FAILURE"
        return result

    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    depth2 = _decision(compiled, state, profile, config, 2)
    depth3 = _decision(compiled, state, profile, config, 3)
    result["searches"] = {"depth_2": depth2, "depth_3": depth3}
    result["compute"]["production_searches"] = 2

    depth2_solves = depth2["selected_uci"] == EXPECTED_UCI
    depth3_solves = depth3["selected_uci"] == EXPECTED_UCI
    if not depth2_solves and depth3_solves:
        result["classification"] = "GATE2_MATE3_FAILURE_IS_NODE_BUDGET_HORIZON_SHORTFALL"
    elif depth2_solves and depth3_solves:
        result["classification"] = "GATE2_MATE3_NODE_CAP_INTERRUPTS_EVEN_SHALLOW_SOLVE"
    else:
        evaluator = Evaluator(compiled, profile, config)
        exact_score, exact_action = reference_minimax(state, 3, evaluator, compiled)
        exact = {
            "selected_action": None if exact_action is None else action_to_dict(exact_action),
            "selected_uci": None if exact_action is None else _gc_chess_uci(exact_action),
            "root_score": exact_score,
        }
        result["exact_depth3_control"] = exact
        result["compute"]["exact_controls"] = 1
        if exact["selected_uci"] == EXPECTED_UCI:
            result["classification"] = "GATE2_MATE3_PRODUCTION_ABP_DIVERGES_FROM_EXACT_DEPTH3"
        else:
            result["classification"] = "GATE2_MATE3_DEPTH_SEMANTICS_MISMATCH"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_diagnostic()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
