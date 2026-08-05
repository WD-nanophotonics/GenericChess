"""Terminal conditions: checkmate, stalemate, repetition and ply limits."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from .attacks import is_in_check
from .errors import ensure_ruleset_match
from .movegen import has_legal_action
from .position import Position
from .repetition import is_repetition_draw

if TYPE_CHECKING:
    from ..rules.compiled import CompiledRuleSet
    from .position import GameState


class TerminalStatus(Enum):
    ONGOING = "ongoing"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    REPETITION = "repetition"
    MAX_PLY = "max_ply"


@dataclass(frozen=True, slots=True)
class TerminalResult:
    status: TerminalStatus
    winner: int | None = None  # 0/1 for checkmate; None for draws and ongoing

    @property
    def is_terminal(self) -> bool:
        return self.status is not TerminalStatus.ONGOING

    def __str__(self) -> str:
        if self.status is TerminalStatus.CHECKMATE:
            return f"checkmate, player {self.winner} wins"
        if self.status is TerminalStatus.ONGOING:
            return "ongoing"
        return f"{self.status.value}, draw"


def _terminal_from_parts(
    position: Position,
    ply_count: int,
    repetition_counts: tuple[tuple[str, int], ...],
    compiled: "CompiledRuleSet",
) -> TerminalResult:
    side = position.side_to_move
    if not has_legal_action(position, compiled):
        if is_in_check(position, side, compiled):
            return TerminalResult(TerminalStatus.CHECKMATE, 1 - side)
        return TerminalResult(TerminalStatus.STALEMATE)
    if is_repetition_draw(repetition_counts, compiled.repetition_limit):
        return TerminalResult(TerminalStatus.REPETITION)
    if ply_count >= compiled.max_ply:
        return TerminalResult(TerminalStatus.MAX_PLY)
    return TerminalResult(TerminalStatus.ONGOING)


def terminal_result(state: "GameState", compiled: "CompiledRuleSet") -> TerminalResult:
    """Public API: terminal status of a game state (freshly recomputed)."""
    ensure_ruleset_match(state.position, compiled)
    return _terminal_from_parts(
        state.position, state.ply_count, state.repetition_counts, compiled
    )
