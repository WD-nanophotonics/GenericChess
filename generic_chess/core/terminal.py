"""Terminal conditions: mate, repetition, automatic adjudication and ply limits."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from .attacks import is_in_check
from .adjudication import (
    automatic_adjudication_status,
    consecutive_action_adjudication_status,
    no_progress_draw_status,
)
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
    NO_CONTEST = "no_contest"
    ACTION_CLASS_DRAW = "action_class_draw"
    NO_PROGRESS_DRAW = "no_progress_draw"
    RULE_LOSS = "rule_loss"


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
        if self.status is TerminalStatus.STALEMATE and self.winner is not None:
            return f"stalemate, player {self.winner} wins"
        if self.status is TerminalStatus.ONGOING:
            return "ongoing"
        if self.status is TerminalStatus.PERPETUAL_CHECK:
            return f"perpetual check, player {1 - self.winner} loses"
        if self.status is TerminalStatus.NO_CONTEST:
            return "no-contest/restart"
        if self.status is TerminalStatus.RULE_LOSS:
            loser = None if self.winner is None else 1 - self.winner
            return f"rule loss, player {loser} loses, player {self.winner} wins"
        return f"{self.status.value}, draw"


def _repeated_cycle_checking_sides(history, limit):
    """Return actors checking on every turn in the current repeated interval."""
    if not history:
        return ()
    current_key = history[-1].position_key
    configured = max(2, int(limit))
    occurrences = [
        i for i, record in enumerate(history) if record.position_key == current_key
    ]
    if len(occurrences) < 2:
        return ()
    window = (
        occurrences[-configured:]
        if len(occurrences) >= configured
        else occurrences[-2:]
    )
    start, end = window[0], window[-1]
    cycle = history[start + 1 : end + 1]
    if not cycle:
        return ()
    checks_by_actor = {0: [], 1: []}
    for record in cycle:
        if record.actor in checks_by_actor:
            checks_by_actor[record.actor].append(bool(record.gave_check))
    if any(not checks for checks in checks_by_actor.values()):
        return ()
    return tuple(
        actor
        for actor, checks in checks_by_actor.items()
        if checks and all(checks)
    )


def _perpetual_check_result(repetition_counts, history, limit):
    """Classify a repeated position using generic action-history evidence."""
    if not history:
        return None
    current_key = history[-1].position_key
    if dict(repetition_counts).get(current_key, 0) < limit:
        return None
    checking_sides = _repeated_cycle_checking_sides(
        history, limit
    )
    # A legal repeated cycle alternates the checking side with replies.  The
    # checking side loses only when exactly one side gave check on every move
    # it made; requiring both sides to have participated avoids classifying a
    # malformed/synthetic one-sided history as perpetual check.
    if len(checking_sides) != 1:
        return None
    checker = checking_sides[0]
    return TerminalResult(TerminalStatus.PERPETUAL_CHECK, 1 - checker)


def _repeated_cycle_target_result(
    position: Position,
    ply_count: int,
    repetition_counts,
    compiled: "CompiledRuleSet",
    history=(),
) -> TerminalResult | None:
    """Apply an opt-in RuleSet result to a verified repeated-cycle fact."""
    conditions = getattr(compiled, "repeated_cycle_target_conditions", ())
    if not conditions:
        return None
    if ply_count == 0 and not history:
        # The initial position cannot contain a completed repeated cycle.
        return None
    from .adjudication import IncompleteAdjudicationHistoryError

    if len(history) != ply_count + 1:
        raise IncompleteAdjudicationHistoryError(
            "repeated-cycle target adjudication requires complete verifiable history"
        )
    from .identity import position_identity_key

    current_key = position_identity_key(position, compiled)
    occurrences = dict(repetition_counts).get(current_key, 0)
    if occurrences < 2:
        return None
    support = getattr(compiled, "support", None)
    configured_limit = getattr(
        support,
        "repetition_limit",
        getattr(compiled, "repetition_limit", 2),
    )
    repeat_limit = max(2, int(configured_limit))
    if occurrences < repeat_limit:
        # Unlike ordinary per-cycle facts, an actor-loss result is terminal:
        # do not adjudicate it before this RuleSet's declared repeat threshold.
        return None

    from .history_cycle_trace import (
        evaluate_repeated_cycle_target_condition,
        summarize_repeated_cycle_targets,
        trace_latest_repeated_cycle_capture_facts,
    )
    from dataclasses import replace
    from .position import GameState

    if hasattr(compiled, "ir"):
        trace_compiled = replace(
            compiled,
            ir=replace(
                compiled.ir, repeated_cycle_target_conditions=()
            ),
        )
    else:
        trace_compiled = replace(
            compiled, repeated_cycle_target_conditions=()
        )
    engine = None
    try:
        from .semantic_executor import semantic_engine_for

        engine = semantic_engine_for(trace_compiled)
    except (ImportError, AttributeError):
        engine = None
    baseline_terminal = (
        engine.terminal_result(
            position, ply_count, repetition_counts, history
        )
        if engine is not None
        else _terminal_from_parts(
            position,
            ply_count,
            tuple(repetition_counts),
            trace_compiled,
            history,
        )
    )

    state = GameState(
        position=position,
        ply_count=ply_count,
        repetition_counts=tuple(repetition_counts),
        terminal_status=baseline_terminal,
        history=tuple(history),
    )
    trace = trace_latest_repeated_cycle_capture_facts(state, trace_compiled)
    if trace.status != "verified":
        raise IncompleteAdjudicationHistoryError(
            "repeated-cycle target adjudication requires complete verifiable "
            f"history: {trace.reason or 'history could not be verified'}"
        )
    summary = summarize_repeated_cycle_targets(trace)
    if summary.status != "verified":
        raise IncompleteAdjudicationHistoryError(
            "repeated-cycle target adjudication requires complete verifiable "
            f"history: {summary.reason or 'cycle facts could not be verified'}"
        )
    satisfied_conditions = []
    for condition in conditions:
        status = evaluate_repeated_cycle_target_condition(summary, condition.actor)
        if status == "unknown":
            raise IncompleteAdjudicationHistoryError(
                "repeated-cycle target adjudication condition is unknown"
            )
        if status == "satisfied" and condition.outcome == "actor_loss":
            satisfied_conditions.append(condition)
    if (
        satisfied_conditions
        and getattr(compiled, "repetition_policy", "draw")
        == "continuous_check_loss"
        and _repeated_cycle_checking_sides(
            history,
            getattr(compiled, "repetition_limit", 2),
        )
    ):
        # Defer this lower-priority outcome while the same verified cycle is a
        # continuous-check candidate. At the configured threshold the caller
        # applies check adjudication first; mutual checks then fall through to
        # the ordinary repetition result instead of an actor-specific loss.
        return None
    if satisfied_conditions:
        return TerminalResult(
            TerminalStatus.RULE_LOSS, 1 - satisfied_conditions[0].actor
        )
    return None


def _terminal_from_parts(
    position: Position,
    ply_count: int,
    repetition_counts: tuple[tuple[str, int], ...],
    compiled: "CompiledRuleSet",
    history=(),
) -> TerminalResult:
    side = position.side_to_move
    consecutive = consecutive_action_adjudication_status(
        getattr(compiled, "consecutive_action_adjudications", ()),
        ply_count,
        history,
    )
    if consecutive == "DRAW":
        return TerminalResult(TerminalStatus.ACTION_CLASS_DRAW)
    if not has_legal_action(position, compiled):
        if is_in_check(position, side, compiled):
            return TerminalResult(TerminalStatus.CHECKMATE, 1 - side)
        winner = 1 - side if getattr(compiled, "stalemate_result", "draw") == "loss" else None
        return TerminalResult(TerminalStatus.STALEMATE, winner)
    repetition_limit = getattr(
        compiled,
        "repetition_limit",
        compiled.support.repetition_limit
        if getattr(compiled, "support", None) is not None
        else 4,
    )
    repeated_target_result = _repeated_cycle_target_result(
        position, ply_count, repetition_counts, compiled, history
    )
    if repeated_target_result is not None:
        return repeated_target_result
    if getattr(compiled, "repetition_policy", "draw") == "continuous_check_loss":
        perpetual = _perpetual_check_result(
            repetition_counts, history, repetition_limit
        )
        if perpetual is not None:
            return perpetual
    if is_repetition_draw(repetition_counts, repetition_limit):
        return TerminalResult(TerminalStatus.REPETITION)
    no_progress = no_progress_draw_status(
        getattr(compiled, "no_progress_draw", None),
        position,
        ply_count,
        repetition_counts,
        history,
        compiled,
    )
    if no_progress == "DRAW":
        return TerminalResult(TerminalStatus.NO_PROGRESS_DRAW)
    automatic = automatic_adjudication_status(
        getattr(compiled, "automatic_adjudications", ()),
        ply_count,
        history,
    )
    if automatic == "NO_CONTEST":
        return TerminalResult(TerminalStatus.NO_CONTEST)
    if automatic == "PENDING":
        return TerminalResult(TerminalStatus.ONGOING)
    max_ply = getattr(
        compiled,
        "max_ply",
        compiled.support.max_ply
        if getattr(compiled, "support", None) is not None
        else 512,
    )
    if ply_count >= max_ply:
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


def _repeated_cycle_target_history_projection(runtime):
    """Project complete exact search history or reject the opt-in rule."""
    compiled = runtime.compiled
    from collections import Counter

    from .adjudication import IncompleteAdjudicationHistoryError
    from .identity import position_identity_key
    from .position import HistoryRecord
    from .search_runtime import RuntimePositionIdentity

    if (
        not getattr(runtime, "_history_complete", False)
        or getattr(runtime, "history_witness_misses", 0)
        or getattr(runtime, "_opaque_imported_keys", ())
        or len(runtime.history) != runtime.ply_count + 1
    ):
        raise IncompleteAdjudicationHistoryError(
            "repeated-cycle target rule requires complete trusted search history"
        )

    projected = []
    counts: Counter[str] = Counter()
    for record in runtime.history:
        if not isinstance(record.identity, RuntimePositionIdentity):
            raise IncompleteAdjudicationHistoryError(
                "repeated-cycle target rule cannot use opaque search history"
            )
        key = position_identity_key(record.identity.position, compiled)
        counts[key] += 1
        projected.append(
            HistoryRecord(
                key,
                record.actor,
                record.action_signature,
                record.gave_check,
            )
        )
    if (
        not projected
        or projected[0].actor != -1
        or projected[0].action_signature != ""
        or projected[-1].position_key
        != position_identity_key(runtime.position, compiled)
        or runtime.history[-1].identity.position != runtime.position
    ):
        raise IncompleteAdjudicationHistoryError(
            "repeated-cycle target rule requires an exact search-history boundary"
        )

    # Runtime counts must be derivable from the same complete identity stream.
    runtime_counts: Counter[str] = Counter()
    for identity, count in runtime.repetition_counts.items():
        if isinstance(identity, RuntimePositionIdentity):
            key = position_identity_key(identity.position, compiled)
        elif isinstance(identity, str):
            # At the imported root the runtime intentionally keeps the
            # authoritative external stable keys until the first local push.
            key = identity
        else:
            raise IncompleteAdjudicationHistoryError(
                "repeated-cycle target rule cannot use opaque repetition counts"
            )
        runtime_counts[key] += count
    if runtime_counts != counts:
        raise IncompleteAdjudicationHistoryError(
            "repeated-cycle target rule history does not match search repetition counts"
        )

    return tuple(sorted(counts.items())), tuple(projected)


def _require_complete_runtime_rule_history(runtime) -> None:
    if (
        not getattr(runtime, "_history_complete", False)
        or getattr(runtime, "history_witness_misses", 0)
        or getattr(runtime, "_opaque_imported_keys", ())
        or len(runtime.history) != runtime.ply_count + 1
    ):
        from .adjudication import IncompleteAdjudicationHistoryError

        raise IncompleteAdjudicationHistoryError(
            "repeated-cycle target rule requires complete trusted search history"
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
    repeated_target_history = None
    if getattr(compiled, "repeated_cycle_target_conditions", ()):
        _require_complete_runtime_rule_history(runtime)
        if runtime.occurrence_count() >= 2:
            repeated_target_history = _repeated_cycle_target_history_projection(runtime)
    consecutive = consecutive_action_adjudication_status(
        getattr(compiled, "consecutive_action_adjudications", ()),
        runtime.ply_count,
        runtime.history,
        history_complete=getattr(runtime, "_history_complete", False),
    )
    if consecutive == "DRAW":
        return TerminalResult(TerminalStatus.ACTION_CLASS_DRAW)
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
        support = getattr(compiled, "support", None)
        if support is not None:
            stalemate_result = support.stalemate_result
        else:
            stalemate_result = getattr(compiled, "stalemate_result", "draw")
        winner = (
            1 - position.side_to_move
            if stalemate_result == "loss"
            else None
        )
        return TerminalResult(TerminalStatus.STALEMATE, winner)
    if repeated_target_history is not None:
        repeated_target_result = _repeated_cycle_target_result(
            position,
            runtime.ply_count,
            repeated_target_history[0],
            compiled,
            repeated_target_history[1],
        )
        if repeated_target_result is not None:
            return repeated_target_result
    if getattr(compiled, "repetition_policy", "draw") == "continuous_check_loss":
        perpetual = _runtime_perpetual_check_result(runtime)
        if perpetual is not None:
            return perpetual
    limit = getattr(compiled, "repetition_limit", compiled.support.repetition_limit if hasattr(compiled, "support") else 4)
    if runtime.occurrence_count() >= limit:
        return TerminalResult(TerminalStatus.REPETITION)
    automatic = automatic_adjudication_status(
        getattr(compiled, "automatic_adjudications", ()),
        runtime.ply_count,
        runtime.history,
        history_complete=getattr(runtime, "_history_complete", False),
    )
    if automatic == "NO_CONTEST":
        return TerminalResult(TerminalStatus.NO_CONTEST)
    if automatic == "PENDING":
        return TerminalResult(TerminalStatus.ONGOING)
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
