"""Contrast coarse pawn-drop events with executable same-file legality."""

from dataclasses import replace

from generic_chess.core.actions import SemanticDropMove
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.intrinsic_action_events import collect_intrinsic_held_drop_events


def audit():
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    initial = initial_state(compiled)
    coarse = collect_intrinsic_held_drop_events(compiled, "P")
    assert coarse["coarse_coverage_complete"]
    outcomes = {}
    label_projections = []
    for current in ("P", "TP"):
        board = [None] * 81
        board[4] = Piece(0, "K", "K")
        board[76] = Piece(1, "K", "K")
        board[40] = Piece(0, "P", current, current == "TP")
        label_projections.append(tuple("empty" if piece is None else
                                       "own" if piece.owner == 0 else "enemy"
                                       for piece in board))
        state = replace(initial, position=replace(
            initial.position, board=tuple(board),
            hands=(Hands((("P", 1),)), Hands.empty()), side_to_move=0,
        ))
        intrinsic = {key[3] for key in coarse["events"]
                     if key[0] == 0 and board[key[3]] is None}
        legal = {action.to_square.rank * 9 + action.to_square.file
                 for action in legal_actions(state, compiled)
                 if isinstance(action, SemanticDropMove) and action.base_type_id == "P"}
        outcomes[current] = {
            "intrinsic_count": len(intrinsic),
            "legal_count": len(legal),
            "intrinsic_only": sorted(intrinsic - legal),
            "legal_only": sorted(legal - intrinsic),
        }
    outcomes["same_three_label_projection"] = label_projections[0] == label_projections[1]
    return outcomes


if __name__ == "__main__":
    import json
    print(json.dumps(audit(), indent=2))
