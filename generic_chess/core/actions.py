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


@dataclass(frozen=True, slots=True)
class SemanticBoardMove:
    """Lossless public semantic board action (Phase 1.9B-2 R2).

    Carries the exact compiled ``pattern_id`` and ``geometry_id`` so two
    semantically different bindings with identical visible coordinates stay
    distinct public actions (ADR-015).
    """

    pattern_id: str
    geometry_id: str
    actor_type_id: str
    from_square: Square
    to_square: Square
    promotion_target_id: str | None = None

    def __str__(self) -> str:
        base = f"{square_str(self.from_square)}-{square_str(self.to_square)}"
        if self.promotion_target_id is not None:
            base = f"{base}={self.promotion_target_id}"
        return f"{self.pattern_id}:{self.geometry_id}:{base}"


@dataclass(frozen=True, slots=True)
class SemanticDropMove:
    """Lossless public semantic drop action (Phase 1.9B-2 R2)."""

    pattern_id: str
    geometry_id: str
    base_type_id: str
    to_square: Square

    def __str__(self) -> str:
        return (
            f"{self.pattern_id}:{self.geometry_id}:"
            f"{self.base_type_id}@{square_str(self.to_square)}"
        )


Action = BoardMove | DropMove | SemanticBoardMove | SemanticDropMove


def action_is_board(action: Action) -> bool:
    """Return whether an action moves an on-board piece.

    This shape check deliberately preserves the concrete action object and
    semantic identity; callers only use it to share legacy/semantic routing.
    """
    return isinstance(action, (BoardMove, SemanticBoardMove))


def action_is_drop(action: Action) -> bool:
    """Return whether an action places a piece from a hand."""
    return isinstance(action, (DropMove, SemanticDropMove))


def action_source_square(action: Action) -> Square | None:
    """Return a board action's source square, or ``None`` for drops."""
    return action.from_square if action_is_board(action) else None


def action_target_square(action: Action) -> Square:
    """Return the destination square for any public action shape."""
    return action.to_square


def action_promotion_target_id(action: Action) -> str | None:
    """Return the public promotion target for board actions."""
    return action.promotion_target_id if action_is_board(action) else None


def action_drop_base_type_id(action: Action) -> str | None:
    """Return the hand piece type for drop actions."""
    return action.base_type_id if action_is_drop(action) else None


def action_to_dict(action: Action) -> dict[str, Any]:
    """Stable dict representation of an action (JSON-serializable)."""
    if isinstance(action, BoardMove):
        return {
            "kind": "board",
            "from": [action.from_square.file, action.from_square.rank],
            "to": [action.to_square.file, action.to_square.rank],
            "promotion_target_id": action.promotion_target_id,
        }
    if isinstance(action, DropMove):
        return {
            "kind": "drop",
            "base_type_id": action.base_type_id,
            "to": [action.to_square.file, action.to_square.rank],
        }
    if isinstance(action, SemanticBoardMove):
        return {
            "kind": "semantic_board",
            "pattern_id": action.pattern_id,
            "geometry_id": action.geometry_id,
            "actor_type_id": action.actor_type_id,
            "from": [action.from_square.file, action.from_square.rank],
            "to": [action.to_square.file, action.to_square.rank],
            "promotion_target_id": action.promotion_target_id,
        }
    return {
        "kind": "semantic_drop",
        "pattern_id": action.pattern_id,
        "geometry_id": action.geometry_id,
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
    if data["kind"] == "drop":
        to_file, to_rank = data["to"]
        return DropMove(data["base_type_id"], Square(to_file, to_rank))
    if data["kind"] == "semantic_board":
        from_file, from_rank = data["from"]
        to_file, to_rank = data["to"]
        return SemanticBoardMove(
            pattern_id=data["pattern_id"],
            geometry_id=data["geometry_id"],
            actor_type_id=data["actor_type_id"],
            from_square=Square(from_file, from_rank),
            to_square=Square(to_file, to_rank),
            promotion_target_id=data.get("promotion_target_id"),
        )
    to_file, to_rank = data["to"]
    return SemanticDropMove(
        pattern_id=data["pattern_id"],
        geometry_id=data["geometry_id"],
        base_type_id=data["base_type_id"],
        to_square=Square(to_file, to_rank),
    )
