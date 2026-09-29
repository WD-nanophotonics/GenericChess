"""Compare local occupancy events with executable Xiangqi legal actions.

This checks a semantic boundary, not material values or a sampled game model.
"""

from collections import Counter
from dataclasses import replace
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from scripts.intrinsic_action_events import collect_intrinsic_board_events


NON_ANCHOR = ("A", "C", "E", "H", "R", "S")


def board_with_pieces(initial, pieces):
    board = [None] * 90
    for owner, type_id, file, rank in pieces:
        index = rank * 9 + file
        assert board[index] is None
        board[index] = Piece(owner, type_id, type_id)
    return replace(initial, position=replace(initial.position, board=tuple(board), side_to_move=0))


def compare(state, compiled, event_ledgers):
    board = state.position.board

    def cube_holds(cube):
        for square, labels in cube:
            piece = board[square]
            actual = "empty" if piece is None else "own" if piece.owner == 0 else "enemy"
            if actual not in labels:
                return False
        return True

    intrinsic = set()
    for type_id, ledger in event_ledgers.items():
        for (owner, _, source, target, _target_state, _removals, _result), cubes in ledger.items():
            source_piece = board[source]
            if (owner == 0 and source_piece is not None and source_piece.owner == 0
                    and source_piece.current_type_id == type_id
                    and any(cube_holds(cube) for cube in cubes)):
                intrinsic.add((type_id, source, target))
    legal = {
        (action.actor_type_id, action.from_square.rank * 9 + action.from_square.file,
         action.to_square.rank * 9 + action.to_square.file)
        for action in legal_actions(state, compiled) if action.actor_type_id in NON_ANCHOR
    }
    return {
        "intrinsic_count": len(intrinsic),
        "legal_count": len(legal),
        "intrinsic_only": sorted(intrinsic - legal),
        "legal_only": sorted(legal - intrinsic),
        "intrinsic_by_type": dict(sorted(Counter(row[0] for row in intrinsic).items())),
    }


def audit():
    compiled = compile_ruleset_for_execution(build_xiangqi_diagnostic_ruleset())
    initial = initial_state(compiled)
    event_ledgers = {
        type_id: collect_intrinsic_board_events(compiled, type_id)["events"]
        for type_id in NON_ANCHOR
    }
    screen = board_with_pieces(initial, (
        (0, "G", 4, 0), (1, "G", 4, 9), (0, "S", 4, 5),
    ))
    return {"initial": compare(initial, compiled, event_ledgers),
            "last_screen": compare(screen, compiled, event_ledgers)}


if __name__ == "__main__":
    import json
    print(json.dumps(audit(), indent=2))
