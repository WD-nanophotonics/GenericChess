"""Isolate the Standard Shogi pawn-drop-mate postcondition."""

import sys
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import SemanticDropMove
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.core.terminal import terminal_result
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.intrinsic_action_events import collect_intrinsic_held_drop_events


TARGET = 7 * 9 + 4


def audit():
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    initial = initial_state(compiled)
    coarse = collect_intrinsic_held_drop_events(compiled, "P")
    assert (0, "P", "hand", TARGET, "empty", (), "P") in coarse["events"]
    outcomes = {}
    for protected in (False, True):
        board = [None] * 81

        def put(owner, type_id, file, rank):
            square = rank * 9 + file
            assert board[square] is None
            board[square] = Piece(owner, type_id, type_id)

        put(0, "K", 0, 0)
        put(1, "K", 4, 8)
        for file, rank in ((3, 7), (5, 7), (3, 8), (5, 8)):
            put(1, "P", file, rank)
        if protected:
            put(0, "G", 4, 6)
        state = replace(initial, position=replace(
            initial.position, board=tuple(board),
            hands=(Hands((("P", 1),)), Hands.empty()), side_to_move=0,
        ))
        legal_drop_targets = {action.to_square.rank * 9 + action.to_square.file
                              for action in legal_actions(state, compiled)
                              if isinstance(action, SemanticDropMove)
                              and action.base_type_id == "P"}
        # Evaluate the prospective board consequence without applying the
        # forbidden action through the public transition API.
        board[TARGET] = Piece(0, "P", "P")
        prospective = replace(state, position=replace(
            state.position, board=tuple(board),
            hands=(Hands.empty(), Hands.empty()), side_to_move=1,
        ))
        outcomes["protected" if protected else "unprotected"] = {
            "coarse_target_present": True,
            "legal_drop_present": TARGET in legal_drop_targets,
            "prospective_opponent_in_check": SemanticEngine(compiled).in_check(
                prospective.position, 1),
            "prospective_reply_count": len(legal_actions(prospective, compiled)),
            "prospective_terminal": terminal_result(prospective, compiled).status.value,
        }
    return outcomes


if __name__ == "__main__":
    import json
    print(json.dumps(audit(), indent=2))
