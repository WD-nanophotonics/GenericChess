"""Exact root admission and reversible no-progress search facts.

Full public history and action-sensitive search identity remain authoritative.
This context avoids replaying that complete prefix at every DFS child; it never
substitutes a scalar counter for history identity or swallows an ambiguous fact.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace

from .actions import action_from_dict, action_is_board, action_source_square
from .adjudication import (
    IncompleteAdjudicationHistoryError,
    _no_progress_count_after_transition,
)
from .coordinates import square_to_index


@dataclass(frozen=True, slots=True)
class NoProgressContext:
    quiet_plies: int = 0
    error: str | None = None


def advance(context, before, after, action, policy, ply):
    """Retain the first ambiguity until the adjudication threshold is reached.

    Core accepts some entity-creating actions before that threshold. Raising on
    the first such push would change legal continuation and terminal priority.
    """
    if context.error is not None:
        return context
    mover_type = None
    try:
        if action_is_board(action):
            source = action_source_square(action)
            if source is None:
                raise IncompleteAdjudicationHistoryError(
                    f"no-progress history action {ply} has no source square"
                )
            mover = before.board[square_to_index(source, before.board_shape)]
            if mover is None or mover.owner != before.side_to_move:
                raise IncompleteAdjudicationHistoryError(
                    f"no-progress history mover is unknown at action {ply}"
                )
            mover_type = mover.current_type_id
        count = _no_progress_count_after_transition(
            context.quiet_plies, before, after, policy, mover_type, ply
        )
    except IncompleteAdjudicationHistoryError as exc:
        return NoProgressContext(context.quiet_plies, str(exc))
    return NoProgressContext(count)


def prepare(state, compiled, runtime_records):
    """Verify one declared-root public replay and bind every runtime witness.

    Root preparation, like the existing runtime import, is currently indivisible
    with respect to the caller token. Its cost counts against the call budget;
    no hard deadline or bound on arbitrary larger contexts is promised.
    """
    policy = compiled.no_progress_draw
    if policy is None:
        return None
    history = state.history
    if (not isinstance(history, (tuple, list)) or not history
            or len(history) != state.ply_count + 1 or history[0].actor != -1):
        raise IncompleteAdjudicationHistoryError(
            "no-progress context requires complete initial history"
        )
    if len(runtime_records) != len(history):
        raise IncompleteAdjudicationHistoryError(
            "no-progress runtime witness length mismatch"
        )
    if hasattr(compiled, "support"):
        replay_compiled = replace(
            compiled, support=replace(compiled.support, no_progress_draw=None)
        )
    else:
        replay_compiled = replace(compiled, no_progress_draw=None)
    from .transition import initial_state, apply_action
    from .search_runtime import _runtime_position_identity

    try:
        replayed = initial_state(replay_compiled)
        if replayed.history[0] != history[0]:
            setups = (replay_compiled.support.initial_setup_options
                      if hasattr(replay_compiled, "support")
                      else replay_compiled.initial_setup_positions)
            for setup_key in setups:
                candidate = initial_state(replay_compiled, setup_key)
                if candidate.history[0] == history[0]:
                    replayed = candidate
                    break
            else:
                raise IncompleteAdjudicationHistoryError(
                    "no-progress history root is not a declared initial setup"
                )

        def bind(ply):
            if runtime_records[ply].identity != _runtime_position_identity(
                    replayed.position, compiled):
                raise IncompleteAdjudicationHistoryError(
                    "no-progress runtime witness differs from exact public "
                    f"replay at action {ply}"
                )

        bind(0)
        context = NoProgressContext()
        for ply, record in enumerate(history[1:], 1):
            if not record.action_signature:
                raise IncompleteAdjudicationHistoryError(
                    f"no-progress history is missing action {ply}"
                )
            try:
                action = action_from_dict(json.loads(record.action_signature))
            except (TypeError, ValueError, KeyError, IndexError) as exc:
                raise IncompleteAdjudicationHistoryError(
                    f"no-progress history has malformed action {ply}"
                ) from exc
            before = replayed.position
            replayed = apply_action(replayed, action, replay_compiled)
            if replayed.history[-1] != record:
                raise IncompleteAdjudicationHistoryError(
                    f"no-progress history action {ply} does not replay exactly"
                )
            bind(ply)
            context = advance(context, before, replayed.position, action, policy, ply)
        if (replayed.position != state.position
                or replayed.ply_count != state.ply_count
                or replayed.repetition_counts != tuple(state.repetition_counts)):
            raise IncompleteAdjudicationHistoryError(
                "no-progress history does not reconstruct the supplied state"
            )
        return context
    except IncompleteAdjudicationHistoryError:
        raise
    except Exception as exc:
        raise IncompleteAdjudicationHistoryError(
            f"no-progress history replay failed: {type(exc).__name__}: {exc}"
        ) from exc


def status(runtime):
    """Called only at no-progress's existing place in terminal precedence."""
    policy = runtime.compiled.no_progress_draw
    if policy is None or runtime.ply_count < policy.threshold_plies:
        return None
    context = runtime._no_progress_context
    if context.error is not None:
        raise IncompleteAdjudicationHistoryError(context.error)
    return policy.outcome if context.quiet_plies >= policy.threshold_plies else None
