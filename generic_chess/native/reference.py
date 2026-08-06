"""Python Core reference helpers for native differential testing."""

from __future__ import annotations

import json

from ..core.actions import action_to_dict
from ..core.transition import apply_action, legal_successors


def python_legal_actions(state, compiled) -> list:
    return [action for action, _ in legal_successors(state, compiled)]


def python_perft(compiled, state, depth: int) -> int:
    if depth <= 0:
        return 1
    total = 0
    for _action, child in legal_successors(state, compiled):
        total += python_perft(compiled, child, depth - 1)
    return total


def canonical_action_set(actions) -> list[str]:
    return sorted(
        json.dumps(action_to_dict(a), sort_keys=True) for a in actions
    )


def python_child_snapshot(state, action, compiled) -> dict:
    child = apply_action(state, action, compiled)
    n = compiled.board_size
    board = []
    for piece in child.position.board:
        if piece is None:
            board.append(None)
        else:
            board.append(
                {
                    "base_type_id": piece.base_type_id,
                    "current_type_id": piece.current_type_id,
                    "owner": piece.owner,
                    "promoted": piece.promoted,
                }
            )
    hands = [
        dict(child.position.hands[owner].counts) for owner in (0, 1)
    ]
    from ..core.keys import position_key

    key = position_key(child.position, compiled)
    repetition_count = dict(child.repetition_counts).get(key, 0)
    return {
        "side_to_move": child.position.side_to_move,
        "ply": child.ply_count,
        "board": board,
        "hands": hands,
        "terminal": child.terminal_status.status.value,
        "repetition_count": repetition_count,
    }


def python_terminal(state) -> str:
    return state.terminal_status.status.value
