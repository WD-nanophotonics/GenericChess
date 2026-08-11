"""Conservative generic quiescence search."""

from __future__ import annotations

from ...core.actions import Action, BoardMove, DropMove
from ...core.attacks import is_in_check
from ...core.coordinates import square_to_index
from ...core.position import GameState
from .statistics import SearchStatistics


def classify_noisy(
    state: GameState,
    successors,
    compiled,
    stats: SearchStatistics | None = None,
) -> list[Action]:
    """Noisy qsearch actions from ``(action, child)`` successor pairs.

    Includes captures, promotions, immediate terminal actions, checking
    moves and checking drops.  Non-checking quiet drops are excluded (and
    counted separately for diagnostics).
    """
    n = state.position.board_size()
    side = state.position.side_to_move
    from ...core.semantic_executor import semantic_engine_for

    semantic_engine = semantic_engine_for(compiled)
    noisy: list[Action] = []
    for action, child in successors:
        if isinstance(action, BoardMove):
            if action.promotion_target_id is not None:
                noisy.append(action)
                if stats is not None:
                    stats.promotion_qactions += 1
                continue
            occupant = state.position.board[action.to_square.rank * n + action.to_square.file]
            if occupant is not None and occupant.owner != side:
                noisy.append(action)
                if stats is not None:
                    stats.capture_qactions += 1
                continue
        if child.terminal_status.is_terminal:
            noisy.append(action)
            continue
        child_in_check = (
            semantic_engine.in_check(child.position, 1 - side)
            if semantic_engine is not None
            else is_in_check(child.position, 1 - side, compiled)
        )
        if child_in_check:
            noisy.append(action)
            if stats is not None:
                if isinstance(action, DropMove):
                    stats.checking_drop_qactions += 1
                else:
                    stats.checking_move_qactions += 1
            continue
        if isinstance(action, DropMove) and stats is not None:
            stats.nonchecking_drop_excluded += 1
    return noisy
