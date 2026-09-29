"""Compare mate by held-pawn drop with mate by board-pawn advance."""

from dataclasses import replace
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import SemanticDropMove
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.terminal import terminal_result
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


SOURCE = 6 * 9 + 4
TARGET = 7 * 9 + 4


def audit():
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    initial = initial_state(compiled)
    board = [None] * 81

    def put(owner, type_id, file, rank):
        index = rank * 9 + file
        assert board[index] is None
        board[index] = Piece(owner, type_id, type_id)

    put(0, "K", 0, 0)
    put(0, "G", 3, 6)  # Protects the pawn's mating target.
    put(1, "K", 4, 8)
    for file, rank in ((3, 7), (5, 7), (3, 8), (5, 8)):
        put(1, "P", file, rank)
    drop_state = replace(initial, position=replace(
        initial.position, board=tuple(board),
        hands=(Hands((("P", 1),)), Hands.empty()), side_to_move=0,
    ))
    drop_actions = [action for action in legal_actions(drop_state, compiled)
                    if isinstance(action, SemanticDropMove)
                    and action.base_type_id == "P"
                    and action.to_square.rank * 9 + action.to_square.file == TARGET]

    board[SOURCE] = Piece(0, "P", "P")
    advance_state = replace(initial, position=replace(
        initial.position, board=tuple(board),
        hands=(Hands.empty(), Hands.empty()), side_to_move=0,
    ))
    advances = [action for action in legal_actions(advance_state, compiled)
                if not isinstance(action, SemanticDropMove)
                and action.actor_type_id == "P"
                and action.promotion_target_id is None
                and action.from_square.rank * 9 + action.from_square.file == SOURCE
                and action.to_square.rank * 9 + action.to_square.file == TARGET]
    assert len(advances) == 1, advances
    after_advance = apply_action(advance_state, advances[0], compiled)

    board[SOURCE] = None
    board[TARGET] = Piece(0, "P", "P")
    hypothetical_drop = replace(drop_state, position=replace(
        drop_state.position, board=tuple(board),
        hands=(Hands.empty(), Hands.empty()), side_to_move=1,
    ))
    return {
        "pawn_drop_legal": bool(drop_actions),
        "pawn_advance_legal": True,
        "same_postmove_position": hypothetical_drop.position == after_advance.position,
        "postmove_terminal": terminal_result(after_advance, compiled).status.value,
        "postmove_reply_count": len(legal_actions(after_advance, compiled)),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(audit(), indent=2))
