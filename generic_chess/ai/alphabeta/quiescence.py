"""Conservative generic quiescence search."""

from __future__ import annotations

from ...core.actions import (
    Action,
    action_is_board,
    action_is_drop,
    action_promotion_target_id,
    action_target_square,
)
from ...core.attacks import is_in_check
from ...core.coordinates import square_to_index
from ...core.position import GameState
from .statistics import SearchStatistics


def enemy_board_count(position, side: int) -> int:
    """Conservative material-removal signal, including off-target captures.

    Read the parent count before pushing a mutable runtime view. This does
    not infer capture from a debug name, board geometry or an EP slot.
    """
    return sum(piece is not None and piece.owner != side for piece in position.board)


def classify_noisy(
    state: GameState,
    successors,
    compiled,
    stats: SearchStatistics | None = None,
    *,
    capture_only: bool = False,
) -> list[Action]:
    """Noisy qsearch actions from ``(action, child)`` successor pairs.

    Includes captures, promotions, immediate terminal actions, checking
    moves and checking drops.  Non-checking quiet drops are excluded (and
    counted separately for diagnostics).
    """
    n = state.position.board_size()
    side = state.position.side_to_move
    parent_enemies = enemy_board_count(state.position, side)
    from ...core.semantic_executor import semantic_engine_for

    semantic_engine = semantic_engine_for(compiled)
    noisy: list[Action] = []
    for action, child in successors:
        if action_is_board(action):
            if action_promotion_target_id(action) is not None:
                noisy.append(action)
                if stats is not None:
                    stats.promotion_qactions += 1
                continue
            target = action_target_square(action)
            occupant = state.position.board[target.rank * n + target.file]
            if occupant is not None and occupant.owner != side:
                noisy.append(action)
                if stats is not None:
                    stats.capture_qactions += 1
                continue
        if enemy_board_count(child.position, side) < parent_enemies:
            noisy.append(action)
            if stats is not None:
                stats.capture_qactions += 1
            continue
        if child.terminal_status.is_terminal:
            noisy.append(action)
            continue
        if capture_only:
            continue
        child_in_check = (
            semantic_engine.in_check(child.position, 1 - side)
            if semantic_engine is not None
            else is_in_check(child.position, 1 - side, compiled)
        )
        if child_in_check:
            noisy.append(action)
            if stats is not None:
                if action_is_drop(action):
                    stats.checking_drop_qactions += 1
                else:
                    stats.checking_move_qactions += 1
            continue
        if action_is_drop(action) and stats is not None:
            stats.nonchecking_drop_excluded += 1
    return noisy
