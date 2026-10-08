"""Conservative generic quiescence search."""

from __future__ import annotations

from collections.abc import Callable

from ...core.actions import (
    Action,
    action_is_board,
    action_is_drop,
    action_promotion_target_id,
    action_target_square,
)
from ...core.attacks import is_in_check
from ...core.position import GameState
from .statistics import SearchStatistics


def enemy_board_count(position, side: int) -> int:
    """Conservative material-removal signal, including off-target captures.

    Read the parent count before pushing a mutable runtime view. This does
    not infer capture from a debug name, board geometry or an EP slot.
    """
    return sum(piece is not None and piece.owner != side for piece in position.board)


def material_inventory(position) -> dict[tuple[int, str], int]:
    """Actual board-current/hand-base counts, copied before a mutable push.

    An ordinary drop conserves this inventory. A type/ownership/quantity change
    may not. Balanced type swaps, spatial and auxiliary effects can conserve it;
    this is a limited q inclusion signal, not a complete tactical classifier.
    """
    counts: dict[tuple[int, str], int] = {}
    for piece in position.board:
        if piece is not None:
            key = (piece.owner, piece.current_type_id)
            counts[key] = counts.get(key, 0) + 1
    for owner, hand in enumerate(position.hands):
        for type_id, count in hand.items():
            key = (owner, type_id)
            counts[key] = counts.get(key, 0) + count
    return counts


def legacy_noisy_kind(position, action: Action) -> str | None:
    """Metadata shortcuts only for the legacy execution contract."""
    if not action_is_board(action):
        return None
    if action_promotion_target_id(action) is not None:
        return "promotion"
    target = action_target_square(action)
    occupant = position.board[target.rank * position.board_size() + target.file]
    if occupant is not None and occupant.owner != position.side_to_move:
        return "capture"
    return None


def noisy_child(
    action: Action, child, side: int, parent_enemies: int,
    parent_inventory: dict[tuple[int, str], int] | None,
    child_in_check: Callable[[], bool], stats: SearchStatistics | None = None,
    *, capture_only: bool = False, legacy_kind: str | None = None,
) -> bool:
    """One shared policy for an already applied child, including runtime views.

    Parent counts/kind must be copied before a mutable push. Check is lazy so
    material/terminal inclusion never pays for a second attack query.
    """
    if legacy_kind == "promotion":
        if stats is not None:
            stats.promotion_qactions += 1
        return True
    if legacy_kind == "capture" or enemy_board_count(child.position, side) < parent_enemies:
        if stats is not None:
            stats.capture_qactions += 1
        return True
    if parent_inventory is not None and material_inventory(child.position) != parent_inventory:
        if stats is not None:
            stats.material_change_qactions += 1
            if action_promotion_target_id(action) is not None:
                stats.promotion_qactions += 1
        return True
    if child.terminal_status.is_terminal:
        return True
    if capture_only:
        return False
    if child_in_check():
        if stats is not None:
            if action_is_drop(action):
                stats.checking_drop_qactions += 1
            else:
                stats.checking_move_qactions += 1
        return True
    if action_is_drop(action) and stats is not None:
        stats.nonchecking_drop_excluded += 1
    return False


def classify_noisy(
    state: GameState,
    successors,
    compiled,
    stats: SearchStatistics | None = None,
    *,
    capture_only: bool = False,
) -> list[Action]:
    """Noisy qsearch actions from ``(action, child)`` successor pairs.

    Legacy captures/promotions retain their shortcuts. Semantic actions use
    actual enemy removal and material-inventory change, never promotion/target
    metadata alone. Terminals and checks remain; ordinary quiet drops stay out.
    """
    side = state.position.side_to_move
    parent_enemies = enemy_board_count(state.position, side)
    from ...core.semantic_executor import semantic_engine_for

    semantic_engine = semantic_engine_for(compiled)
    parent_inventory = material_inventory(state.position) if semantic_engine is not None else None
    noisy: list[Action] = []
    for action, child in successors:
        check = (
            lambda: semantic_engine.in_check(child.position, 1 - side)
            if semantic_engine is not None
            else is_in_check(child.position, 1 - side, compiled)
        )
        kind = legacy_noisy_kind(state.position, action) if semantic_engine is None else None
        if noisy_child(action, child, side, parent_enemies, parent_inventory,
                       check, stats, capture_only=capture_only, legacy_kind=kind):
            noisy.append(action)
    return noisy
