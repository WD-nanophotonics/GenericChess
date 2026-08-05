"""Independent UI interaction state (never part of Core/Record/position)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.actions import Action
from ..core.coordinates import Square


@dataclass
class BoardInteractionState:
    """Transient UI state that never influences game rules or records."""

    selected_square: Square | None = None
    selected_hand_piece_type_id: str | None = None
    legal_actions: tuple[Action, ...] = ()
    preview_squares: tuple[Square, ...] = ()
    preview_piece_square: Square | None = None
    hovered_square: Square | None = None
    orientation_owner: int = 0  # owner shown at the bottom of the board
    displayed_ply: int | None = None  # None = live position
    pending_promotion_actions: tuple[Action, ...] = field(default_factory=tuple)

    def clear_selection(self) -> None:
        self.selected_square = None
        self.selected_hand_piece_type_id = None
        self.legal_actions = ()
        self.preview_squares = ()
        self.preview_piece_square = None
        self.pending_promotion_actions = ()
