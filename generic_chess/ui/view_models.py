"""Immutable view models consumed by the Qt views (Qt-free)."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.actions import Action
from ..core.coordinates import Square
from ..core.pieces import Piece
from ..session.result import SessionResult


@dataclass(frozen=True)
class SquareViewModel:
    square: Square
    piece: Piece | None
    is_last_move_from: bool
    is_last_move_to: bool
    is_selected: bool
    is_legal_move: bool
    is_legal_capture: bool
    is_preview: bool
    is_hovered: bool
    is_check_anchor: bool


@dataclass(frozen=True)
class BoardViewModel:
    board_size: int
    squares: tuple[SquareViewModel, ...]  # flat, logical rank*n+file order
    side_to_move: int
    check_side: int | None


@dataclass(frozen=True)
class HandEntry:
    type_id: str
    count: int


@dataclass(frozen=True)
class GameViewModel:
    side_to_move: int
    ply_count: int
    result: SessionResult
    hands: tuple[tuple[HandEntry, ...], tuple[HandEntry, ...]]
    fingerprint: str
    fingerprint_short: str
    seed: int | None
    ruleset_path: str | None
    record_path: str | None
    board_size: int
    piece_type_count: int


@dataclass(frozen=True)
class HistoryEntry:
    ply: int
    player: int
    action: Action
    label: str


@dataclass(frozen=True)
class PieceInfo:
    type_id: str
    name: str
    owner: int | None
    square: Square | None
    base_type_id: str | None
    promoted: bool
    movement_lines: tuple[str, ...]
    legal_action_count: int | None
    capture_count: int | None
    promotion_count: int | None
    preview_count: int | None
    is_actionable: bool
    is_preview: bool


@dataclass(frozen=True)
class PromotionOption:
    action: Action
    label: str
    summary: str


@dataclass(frozen=True)
class RulesInfo:
    board_size: int
    seed: int | None
    fingerprint: str
    piece_type_count: int
    promotion_relations: tuple[str, ...]
    drop_summary: str
    terminal_summary: str
    initial_entity_count: int
    piece_types: tuple[tuple[str, str, tuple[str, ...]], ...]  # (type_id, name, movement lines)
