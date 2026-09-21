"""Gate 2: establish the exact node-cap boundary for the Chess mate in three."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.gate1_known_game_backend_equivalence import _gc_chess_uci
from scripts.gate2_mate3_solving_horizon_diagnostic import EXPECTED_UCI, FEN
from scripts.gate2_merged_benchmark import (
    _fixed_state_from_position,
    _forced_mate_in_exactly_three,
    _make_player,
    _session_with_state,
    _successors,
)


CAPS = (21248, 21249)
EXPECTED_MATE_SCORE = 999999997


def _decision(compiled, state, profile, config, max_nodes):
    result = _make_player(compiled, profile, config).choose_action(
        _session_with_state(compiled, state, (state.position,)),
        SearchLimits(
            max_depth=3,
            max_nodes=max_nodes,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
        ),
    )
    return {
        "max_nodes": max_nodes,
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
        "forced_action_count": len(forced),
        "forced_uci": forced_uci,
        "passed": len(forced) == 1 and forced_uci == [EXPECTED_UCI],
    }
    result = {
        "status": "PASS",
        "classification": None,
        "position": {"fen": FEN, "expected_uci": EXPECTED_UCI},
        "ground_truth_reproduction": ground_truth,
        "searches": [],
        "compute": {
            "production_searches": 0,
            "max_depth": 3,
            "node_caps": list(CAPS),
        },
    }
    if not ground_truth["passed"]:
        result["status"] = "HARD_FAILURE"
        result["classification"] = "GATE2_MATE3_GROUND_TRUTH_REPRODUCTION_FAILURE"
        return result

    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    searches = [
        _decision(compiled, state, profile, config, max_nodes) for max_nodes in CAPS
    ]
    result["searches"] = searches
    result["compute"]["production_searches"] = 2

    capped, boundary = searches
    if capped["completed_depth"] == 3:
        result["classification"] = "GATE2_MATE3_NODE_ACCOUNTING_BOUNDARY_DRIFT"
    elif not (
        boundary["completed_depth"] == 3
        and boundary["selected_uci"] == EXPECTED_UCI
        and boundary["root_score"] == EXPECTED_MATE_SCORE
        and boundary["nodes"] == 21248
        and boundary["termination_reason"] == "completed_depth"
    ):
        result["classification"] = "GATE2_MATE3_NODE_CAP_PATH_DIVERGENCE"
    else:
        result["classification"] = "GATE2_MATE3_EXACT_MIN_NODE_CAP_21249"
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
