"""Immutable, hashable, serializable actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .coordinates import Square, square_str


@dataclass(frozen=True, slots=True)
class BoardMove:
    """A move of a piece already on the board, with optional promotion."""

    from_square: Square
    to_square: Square
    promotion_target_id: str | None = None

    def __str__(self) -> str:
        base = f"{square_str(self.from_square)}-{square_str(self.to_square)}"
        if self.promotion_target_id is not None:
            return f"{base}={self.promotion_target_id}"
        return base


@dataclass(frozen=True, slots=True)
class DropMove:
    """Drop of a captured piece from the hand onto an empty square."""

    base_type_id: str
    to_square: Square

    def __str__(self) -> str:
        return f"{self.base_type_id}@{square_str(self.to_square)}"


Action = BoardMove | DropMove


def action_to_dict(action: Action) -> dict[str, Any]:
    """Stable dict representation of an action (JSON-serializable)."""
    if isinstance(action, BoardMove):
        return {
            "kind": "board",
            "from": [action.from_square.file, action.from_square.rank],
            "to": [action.to_square.file, action.to_square.rank],
            "promotion_target_id": action.promotion_target_id,
        }
    return {
        "kind": "drop",
        "base_type_id": action.base_type_id,
        "to": [action.to_square.file, action.to_square.rank],
    }


def action_from_dict(data: dict[str, Any]) -> Action:
    if data["kind"] == "board":
        from_file, from_rank = data["from"]
        to_file, to_rank = data["to"]
        return BoardMove(
            Square(from_file, from_rank),
            Square(to_file, to_rank),
            data.get("promotion_target_id"),
        )
    to_file, to_rank = data["to"]
    return DropMove(data["base_type_id"], Square(to_file, to_rank))
