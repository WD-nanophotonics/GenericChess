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
    PERPETUAL_CHECK = "perpetual_check"
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
        if self.status is TerminalStatus.PERPETUAL_CHECK:
            return f"perpetual check, player {1 - self.winner} loses"
        return f"{self.status.value}, draw"


def _perpetual_check_result(repetition_counts, history, limit):
    """Classify a repeated position using generic action-history evidence."""
    if not history:
        return None
    current_key = history[-1].position_key
    if dict(repetition_counts).get(current_key, 0) < limit:
        return None
    occurrences = [
        i for i, record in enumerate(history) if record.position_key == current_key
    ]
    if len(occurrences) < limit:
        return None
    start, end = occurrences[-limit], occurrences[-1]
    cycle = history[start + 1 : end + 1]
    if not cycle:
        return None
    checks_by_actor = {0: [], 1: []}
    for record in cycle:
        if record.actor in checks_by_actor:
            checks_by_actor[record.actor].append(bool(record.gave_check))
    checking_sides = [
        actor
        for actor, checks in checks_by_actor.items()
        if checks and all(checks)
    ]
    # A legal repeated cycle alternates the checking side with replies.  The
    # checking side loses only when exactly one side gave check on every move
    # it made; requiring both sides to have participated avoids classifying a
    # malformed/synthetic one-sided history as perpetual check.
    if len(checking_sides) != 1 or any(not checks for checks in checks_by_actor.values()):
        return None
    checker = checking_sides[0]
    return TerminalResult(TerminalStatus.PERPETUAL_CHECK, 1 - checker)


def _terminal_from_parts(
    position: Position,
    ply_count: int,
    repetition_counts: tuple[tuple[str, int], ...],
    compiled: "CompiledRuleSet",
    history=(),
) -> TerminalResult:
    side = position.side_to_move
    if not has_legal_action(position, compiled):
        if is_in_check(position, side, compiled):
            return TerminalResult(TerminalStatus.CHECKMATE, 1 - side)
        return TerminalResult(TerminalStatus.STALEMATE)
    if getattr(compiled, "repetition_policy", "draw") == "continuous_check_loss":
        perpetual = _perpetual_check_result(
            repetition_counts, history, compiled.repetition_limit
        )
        if perpetual is not None:
            return perpetual
    if is_repetition_draw(repetition_counts, compiled.repetition_limit):
        return TerminalResult(TerminalStatus.REPETITION)
    if ply_count >= compiled.max_ply:
        return TerminalResult(TerminalStatus.MAX_PLY)
    return TerminalResult(TerminalStatus.ONGOING)


def terminal_result(state: "GameState", compiled: "CompiledRuleSet") -> TerminalResult:
    """Public API: terminal status of a game state (freshly recomputed)."""
    from .semantic_executor import semantic_engine_for

    engine = semantic_engine_for(compiled)
    if engine is not None:
        return engine.terminal_result(
            state.position, state.ply_count, state.repetition_counts, state.history
        )
    ensure_ruleset_match(state.position, compiled)
    return _terminal_from_parts(
        state.position,
        state.ply_count,
        state.repetition_counts,
        compiled,
        state.history,
    )
