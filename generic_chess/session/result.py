"""Session-level results (resignation lives here, not in Core)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..core.terminal import TerminalResult, TerminalStatus


class SessionStatus(Enum):
    ONGOING = "ongoing"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    REPETITION = "repetition"
    PERPETUAL_CHECK = "perpetual_check"
    MAX_PLY = "max_ply"
    RESIGNATION = "resignation"


@dataclass(frozen=True, slots=True)
class SessionResult:
    status: SessionStatus
    winner: int | None
    resigned_by: int | None = None

    def __str__(self) -> str:
        if self.status is SessionStatus.ONGOING:
            return "ongoing"
        if self.status is SessionStatus.RESIGNATION:
            return f"resignation, player {self.winner} wins (player {self.resigned_by} resigned)"
        if self.status is SessionStatus.CHECKMATE:
            return f"checkmate, player {self.winner} wins"
        if self.status is SessionStatus.PERPETUAL_CHECK:
            loser = 1 - self.winner if self.winner is not None else None
            return f"perpetual check, player {self.winner} wins (player {loser} loses)"
        return f"{self.status.value}, draw"


def _session_status_from_terminal(terminal: TerminalResult) -> SessionStatus:
    mapping = {
        TerminalStatus.ONGOING: SessionStatus.ONGOING,
        TerminalStatus.CHECKMATE: SessionStatus.CHECKMATE,
        TerminalStatus.STALEMATE: SessionStatus.STALEMATE,
        TerminalStatus.REPETITION: SessionStatus.REPETITION,
        TerminalStatus.PERPETUAL_CHECK: SessionStatus.PERPETUAL_CHECK,
        TerminalStatus.MAX_PLY: SessionStatus.MAX_PLY,
    }
    return mapping[terminal.status]


def session_result_from_terminal(terminal: TerminalResult) -> SessionResult:
    """Map a Core TerminalResult to a SessionResult (no resignation)."""
    return SessionResult(
        status=_session_status_from_terminal(terminal),
        winner=terminal.winner,
        resigned_by=None,
    )
