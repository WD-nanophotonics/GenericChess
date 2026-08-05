"""Conservative generic quiescence search."""

from __future__ import annotations

from ...core.actions import Action, BoardMove
from ...core.position import GameState
from .statistics import SearchStatistics


def classify_noisy(state: GameState, actions: list[Action]) -> list[Action]:
    """Captures and promotions only (v1; checking drops are quiet moves)."""
    n = state.position.board_size()
    side = state.position.side_to_move
    noisy: list[Action] = []
    for action in actions:
        if isinstance(action, BoardMove):
            if action.promotion_target_id is not None:
                noisy.append(action)
                continue
            occupant = state.position.board[action.to_square.rank * n + action.to_square.file]
            if occupant is not None and occupant.owner != side:
                noisy.append(action)
    return noisy
