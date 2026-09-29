"""Bounded Western Chess quiescence boundary probe on F156's frozen root.

The indexed material values are a backend control, not a value prior. This
probe measures search-policy sensitivity, not exact root-action quality.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.transition import apply_action
from scripts.f156_known_game_shallow_search_equivalence import (
    CommonMaterialEvaluator,
    _session,
    _values,
    _western_pair,
    _western_state,
)


DEFAULT_FEN = "4k3/8/8/p7/8/8/8/R3K3 w - - 0 1"


def run_probe(fen: str = DEFAULT_FEN) -> dict:
    compiled, _ = _western_pair()
    state = _western_state(compiled, fen)
    values = _values(compiled)
    rows = []
    for depth in (1, 2):
        for qdepth in (0, 4):
            player = AlphaBetaPlayer(
                compiled,
                evaluation_config=None,
                use_disk_cache=False,
                use_tt=False,
                use_ordering=False,
                use_native_semantic_legality=True,
                tuning=SearchTuning(),
                evaluator_override=CommonMaterialEvaluator(values),
            )
            decision = player.choose_action(
                _session(compiled, state),
                SearchLimits(
                    max_depth=depth,
                    max_nodes=2000,
                    max_time_seconds=5,
                    quiescence_max_depth=qdepth,
                    quiescence_hard_max_depth=0 if qdepth == 0 else 8,
                    deterministic=True,
                ),
            )
            child = apply_action(state, decision.action, compiled) if decision.action else None
            rows.append(
                {
                    "depth": depth,
                    "quiescence_max_depth": qdepth,
                    "action": action_to_dict(decision.action) if decision.action else None,
                    "score": decision.score,
                    "completed_depth": decision.completed_depth,
                    "nodes": decision.nodes,
                    "qnodes": decision.qnodes,
                    "termination_reason": decision.termination_reason,
                    "child_status": child.terminal_status.status.value if child else None,
                    "child_winner": child.terminal_status.winner if child else None,
                }
            )
    return {
        "root_fen": fen,
        "material_values": values,
        "max_nodes": 2000,
        "max_time_seconds": 5,
        "rows": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fen", default=DEFAULT_FEN)
    args = parser.parse_args()
    print(json.dumps(run_probe(args.fen), indent=2, sort_keys=True))
