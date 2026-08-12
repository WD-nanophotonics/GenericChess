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


def terminal_from_search_runtime(runtime, checkpoint=None) -> TerminalResult:
    """Compute terminal status from a Core-owned mutable search path.

    The runtime supplies mutable occurrence counts and history evidence so
    child pushes do not materialize a public ``GameState`` or copy the full
    repetition tuple.  Rule precedence intentionally mirrors
    :func:`_terminal_from_parts` and the semantic executor.
    """
    from .semantic_executor import semantic_engine_for

    position = runtime.position
    compiled = runtime.compiled
    engine = semantic_engine_for(compiled)
    # Terminal probing only needs one legal action.  Full legal-set
    # materialization is intentionally deferred to the next search node;
    # root tactical scans may inspect many children without recursing into
    # them, and must not pay for every complete child action set.
    if engine is not None:
        has_legal = engine.has_legal_action(position, checkpoint=checkpoint)
    else:
        has_legal = has_legal_action(position, compiled)
    if engine is not None:
        checked = engine.in_check(position, position.side_to_move, checkpoint=checkpoint)
    else:
        checked = is_in_check(position, position.side_to_move, compiled)
    if not has_legal:
        if checked:
            return TerminalResult(TerminalStatus.CHECKMATE, 1 - position.side_to_move)
        return TerminalResult(TerminalStatus.STALEMATE)
    if getattr(compiled, "repetition_policy", "draw") == "continuous_check_loss":
        perpetual = _runtime_perpetual_check_result(runtime)
        if perpetual is not None:
            return perpetual
    limit = getattr(compiled, "repetition_limit", compiled.support.repetition_limit if hasattr(compiled, "support") else 4)
    if runtime.occurrence_count() >= limit:
        return TerminalResult(TerminalStatus.REPETITION)
    max_ply = getattr(compiled, "max_ply", compiled.support.max_ply if hasattr(compiled, "support") else 512)
    if runtime.ply_count >= max_ply:
        return TerminalResult(TerminalStatus.MAX_PLY)
    return TerminalResult(TerminalStatus.ONGOING)


def _runtime_perpetual_check_result(runtime):
    """The continuous-check rule over mutable runtime history evidence."""
    if not runtime.history or not getattr(runtime, "_history_complete", True):
        return None
    current_identity = runtime.current_identity
    configured_limit = getattr(runtime.compiled, "repetition_limit", runtime.compiled.support.repetition_limit if hasattr(runtime.compiled, "support") else 4)
    limit = max(1, int(configured_limit))
    if runtime.occurrence_count(current_identity, runtime.runtime_hash) < limit:
        return None
    occurrences = runtime.history_occurrences(current_identity)
    if len(occurrences) < limit:
        return None
    cycle = runtime.history[occurrences[-limit] + 1 : occurrences[-1] + 1]
    if not cycle:
        return None
    checks_by_actor = {0: [], 1: []}
    for record in cycle:
        if record.actor in checks_by_actor:
            checks_by_actor[record.actor].append(bool(record.gave_check))
    checking_sides = [
        actor for actor, checks in checks_by_actor.items()
        if checks and all(checks)
    ]
    if len(checking_sides) != 1 or any(not checks for checks in checks_by_actor.values()):
        return None
    checker = checking_sides[0]
    return TerminalResult(TerminalStatus.PERPETUAL_CHECK, 1 - checker)
