"""Generic move ordering (no chess-specific knowledge)."""

from __future__ import annotations

from ...core.actions import Action, BoardMove
from ...core.coordinates import square_to_index
from ...core.position import GameState
from ..evaluation.evaluator import Evaluator


class MoveOrderer:
    """TT move, captures, promotions, killers, history, canonical tie-break."""

    def __init__(self) -> None:
        self._killers: dict[int, list[Action]] = {}
        self._history: dict[tuple[int, str], int] = {}

    def clear(self) -> None:
        self._killers.clear()
        self._history.clear()

    def record_killer(self, depth: int, action: Action) -> None:
        killers = self._killers.setdefault(depth, [])
        if action in killers:
            killers.remove(action)
        killers.insert(0, action)
        del killers[2:]

    def record_history(self, player: int, action: Action) -> None:
        key = (player, str(action))
        self._history[key] = self._history.get(key, 0) + 1

    def order(
        self,
        state: GameState,
        actions: list[Action],
        evaluator: Evaluator,
        depth: int,
        tt_move: Action | None,
    ) -> list[Action]:
        n = state.position.board_size()
        side = state.position.side_to_move
        killers = self._killers.get(depth, [])

        def priority(action: Action) -> int:
            if tt_move is not None and action == tt_move:
                return -1000
            if isinstance(action, BoardMove):
                occupant = state.position.board[square_to_index(action.to_square, n)]
                if occupant is not None and occupant.owner != side:
                    mover = state.position.board[square_to_index(action.from_square, n)]
                    return -100 - evaluator.capture_order_value(mover, occupant)
                if action.promotion_target_id is not None:
                    return -60
            if action in killers:
                return -30
            return -min(self._history.get((side, str(action)), 0), 20)

        return sorted(actions, key=lambda a: (priority(a), str(a)))
