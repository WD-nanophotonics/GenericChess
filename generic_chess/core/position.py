"""Position, hands and game state containers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .coordinates import BoardShape
from .pieces import Piece

if TYPE_CHECKING:
    from .terminal import TerminalResult


@dataclass(frozen=True, slots=True)
class Hands:
    """Immutable hand of captured pieces, keyed by ``base_type_id``.

    Internally stored as a sorted tuple of ``(type_id, count)`` pairs so the
    value is hashable and serializes canonically.
    """

    counts: tuple[tuple[str, int], ...] = ()

    @staticmethod
    def empty() -> "Hands":
        return Hands(())

    def count(self, type_id: str) -> int:
        for tid, c in self.counts:
            if tid == type_id:
                return c
        return 0

    def total(self) -> int:
        return sum(c for _, c in self.counts)

    def add(self, type_id: str) -> "Hands":
        d = dict(self.counts)
        d[type_id] = d.get(type_id, 0) + 1
        return Hands(tuple(sorted(d.items())))

    def remove(self, type_id: str) -> "Hands":
        d = dict(self.counts)
        if d.get(type_id, 0) <= 0:
            raise ValueError(f"cannot remove {type_id!r}: not in hand")
        d[type_id] -= 1
        if d[type_id] == 0:
            del d[type_id]
        return Hands(tuple(sorted(d.items())))

    def items(self) -> tuple[tuple[str, int], ...]:
        return self.counts

    def __iter__(self):
        return iter(self.counts)


def count_entities(position: "Position") -> int:
    """Total on-board pieces plus pieces in both hands."""
    return sum(1 for p in position.board if p is not None) + sum(
        h.total() for h in position.hands
    )


@dataclass(frozen=True, slots=True)
class Position:
    """A full chess-like position.

    ``board`` is a flat row-major tuple (index ``rank * width + file``), with
    ``None`` for empty squares. ``hands`` is a tuple of two :class:`Hands`
    (indexed by owner). The fingerprint links the position to its rule set.
    """

    board: tuple[Piece | None, ...]
    hands: tuple[Hands, Hands] = (Hands.empty(), Hands.empty())
    side_to_move: int = 0
    ruleset_fingerprint: str = ""
    # Legality-affecting auxiliary semantic state (Phase 1.9B-2): sorted
    # canonical physical keys ``(slot_id, owner_tag)`` with GLOBAL owner tag
    # -1 and PER_OWNER tags 0/1 (ADR-015 section 4).  Value is bool-ish (0/1)
    # for right slots or a square (file, rank) / None for square_or_none
    # slots.  Legacy positions keep the canonical empty value.
    aux_state: tuple[tuple[tuple[int, int], "int | tuple[int, int] | None"], ...] = ()
    # Optional canonical shape for compile-only rectangular carriers. Kept at
    # the end to preserve the legacy positional constructor contract.
    board_width: int | None = None
    board_height: int | None = None

    def __post_init__(self) -> None:
        if (self.board_width is None) != (self.board_height is None):
            raise ValueError("board_width and board_height must be specified together")
        if self.board_width is not None and self.board_height is not None:
            shape = BoardShape(self.board_width, self.board_height)
            if shape.area != len(self.board):
                raise ValueError(
                    f"board shape {shape.width}x{shape.height} does not match "
                    f"board length {len(self.board)}"
                )

    @property
    def board_shape(self) -> BoardShape:
        if self.board_width is not None and self.board_height is not None:
            return BoardShape(self.board_width, self.board_height)
        n = self.board_size()
        return BoardShape(n, n)

    def board_size(self) -> int:
        if self.board_width is not None and self.board_height is not None:
            if self.board_width != self.board_height:
                raise ValueError("board_size is undefined for a rectangular position")
            return self.board_width
        return int(len(self.board) ** 0.5)


@dataclass(frozen=True, slots=True)
class HistoryRecord:
    """Canonical, generic event in the legality-relevant game history."""

    position_key: str
    actor: int
    action_signature: str
    gave_check: bool = False


@dataclass(frozen=True, slots=True)
class GameState:
    """A position plus history-dependent information.

    Kept distinct from :class:`Position` because search reuse must retain the
    repetition/path context held here; position identity alone is not a safe
    transposition key for every ruleset.
    """

    position: Position
    ply_count: int
    repetition_counts: tuple[tuple[str, int], ...]
    terminal_status: "TerminalResult"
    history: tuple[HistoryRecord, ...] = ()
