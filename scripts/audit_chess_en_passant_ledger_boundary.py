"""Find a history-legal Chess capture absent from the intrinsic board ledger."""

from dataclasses import replace

from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action, initial_state
from scripts.audit_f24f_western_chess_perft import position_from_fen, standard_engine
from scripts.intrinsic_action_events import collect_intrinsic_board_events


def index(square):
    return square.rank * 8 + square.file


def audit():
    compiled, _engine = standard_engine()
    position = position_from_fen("7k/8/8/8/4p3/8/3P4/K7 w - - 0 1", compiled)
    state = replace(initial_state(compiled), position=position)
    double = next(action for action in legal_actions(state, compiled)
                  if action.actor_type_id == "P" and index(action.from_square) == 11
                  and index(action.to_square) == 27 and "double_step" in action.pattern_id)
    after = apply_action(state, double, compiled)
    board = after.position.board
    ledger = collect_intrinsic_board_events(compiled, "P")
    assert any("en_passant" in name for name in ledger["excluded_history"])

    def cube_holds(cube):
        for square, labels in cube:
            piece = board[square]
            actual = "empty" if piece is None else "own" if piece.owner == 1 else "enemy"
            if actual not in labels:
                return False
        return True

    intrinsic = {(key[2], key[3]) for key, cubes in ledger["events"].items()
                 if key[0] == 1 and board[key[2]] is not None
                 and board[key[2]].owner == 1 and board[key[2]].current_type_id == "P"
                 and any(cube_holds(cube) for cube in cubes)}
    legal_actions_after = [action for action in legal_actions(after, compiled)
                           if action.actor_type_id == "P"]
    cleared = replace(after, position=replace(after.position, aux_state=position.aux_state))
    assert cleared.position.board == after.position.board
    assert cleared.position.hands == after.position.hands
    assert cleared.position.side_to_move == after.position.side_to_move
    cleared_legal = {(index(action.from_square), index(action.to_square))
                     for action in legal_actions(cleared, compiled)
                     if action.actor_type_id == "P"}
    legal = {(index(action.from_square), index(action.to_square))
             for action in legal_actions_after}
    en_passant = [action for action in legal_actions_after
                  if "en_passant" in action.pattern_id]
    return {
        "intrinsic": sorted(intrinsic),
        "legal": sorted(legal),
        "intrinsic_only": sorted(intrinsic - legal),
        "legal_only": sorted(legal - intrinsic),
        "same_board_aux_cleared_legal": sorted(cleared_legal),
        "en_passant": [(index(action.from_square), index(action.to_square))
                       for action in en_passant],
        "excluded_history_patterns": list(ledger["excluded_history"]),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(audit(), indent=2))
