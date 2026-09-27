"""Shared history-based automatic adjudication primitives."""

from __future__ import annotations

import json
from dataclasses import replace

from .actions import (
    BoardMove,
    DropMove,
    PassAction,
    SemanticBoardMove,
    SemanticDropMove,
    action_from_dict,
)


class IncompleteAdjudicationHistoryError(ValueError):
    """Raised when a threshold rule lacks authoritative completed-move history."""


def no_progress_draw_status(
    policy, position, ply_count, repetition_counts, history, compiled
):
    """Replay authoritative actions and determine a configured no-progress draw.

    Replay uses a compiled view with this policy disabled, avoiding recursive
    adjudication while preserving every other RuleSet rule and transition.
    """
    if policy is None or ply_count < policy.threshold_plies:
        return None
    if not isinstance(history, (tuple, list)):
        raise IncompleteAdjudicationHistoryError(
            "no-progress adjudication requires a history sequence"
        )
    if (
        len(history) != ply_count + 1
        or not history
        or getattr(history[0], "actor", None) != -1
    ):
        raise IncompleteAdjudicationHistoryError(
            "no-progress adjudication requires complete history from its initial position"
        )
    if hasattr(compiled, "support"):
        replay_compiled = replace(
            compiled,
            support=replace(compiled.support, no_progress_draw=None),
        )
    else:
        replay_compiled = replace(compiled, no_progress_draw=None)
    from .actions import action_from_dict, action_is_board, action_source_square
    from .coordinates import square_to_index
    from .transition import apply_action, initial_state

    try:
        replayed = initial_state(replay_compiled)
        if replayed.history[0] != history[0]:
            options = getattr(replay_compiled, "initial_setup_positions", None)
            if options is None:
                options = replay_compiled.support.initial_setup_options
            for setup_key in options:
                candidate = initial_state(replay_compiled, setup_key)
                if candidate.history[0] == history[0]:
                    replayed = candidate
                    break
            else:
                raise IncompleteAdjudicationHistoryError(
                    "no-progress history root is not a declared initial setup"
                )
        count = 0
        reset_types = frozenset(policy.reset_mover_type_ids)
        for ply, record in enumerate(history[1:], start=1):
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
            actor = before.side_to_move
            mover_type = None
            if action_is_board(action):
                source = action_source_square(action)
                if source is None:
                    raise IncompleteAdjudicationHistoryError(
                        f"no-progress history action {ply} has no source square"
                    )
                mover = before.board[square_to_index(source, before.board_shape)]
                if mover is None or mover.owner != actor:
                    raise IncompleteAdjudicationHistoryError(
                        f"no-progress history mover is unknown at action {ply}"
                    )
                mover_type = mover.current_type_id
            replayed = apply_action(replayed, action, replay_compiled)
            if replayed.history[-1] != record:
                raise IncompleteAdjudicationHistoryError(
                    f"no-progress history action {ply} does not replay exactly"
                )
            capture = False
            if policy.reset_on_capture:
                before_counts = [0, 0]
                after_counts = [0, 0]
                for piece in before.board:
                    if piece is not None:
                        before_counts[piece.owner] += 1
                for owner, hand in enumerate(before.hands):
                    before_counts[owner] += hand.total()
                for piece in replayed.position.board:
                    if piece is not None:
                        after_counts[piece.owner] += 1
                for owner, hand in enumerate(replayed.position.hands):
                    after_counts[owner] += hand.total()
                deltas = [after_counts[i] - before_counts[i] for i in (0, 1)]
                if deltas[1 - actor] < 0 and deltas[actor] in (0, -deltas[1 - actor]):
                    capture = True
                elif any(deltas):
                    raise IncompleteAdjudicationHistoryError(
                        f"no-progress history capture fact is ambiguous at action {ply}"
                    )
            if capture or mover_type in reset_types:
                count = 0
            else:
                count += 1
        if (
            replayed.position != position
            or replayed.ply_count != ply_count
            or replayed.repetition_counts != tuple(repetition_counts)
        ):
            raise IncompleteAdjudicationHistoryError(
                "no-progress history does not reconstruct the supplied state"
            )
        return policy.outcome if count >= policy.threshold_plies else None
    except IncompleteAdjudicationHistoryError:
        raise
    except Exception as exc:
        raise IncompleteAdjudicationHistoryError(
            f"no-progress history replay failed: {type(exc).__name__}: {exc}"
        ) from exc


def consecutive_action_adjudication_status(
    adjudications,
    ply_count: int,
    history,
    *,
    history_complete: bool = True,
):
    """Return ``DRAW`` when the completed history ends in a configured run."""
    for adjudication in adjudications:
        if ply_count < adjudication.threshold:
            continue
        if not history_complete or len(history) != ply_count + 1:
            raise IncompleteAdjudicationHistoryError(
                "consecutive action adjudication requires complete history "
                f"through ply {ply_count}"
            )
        if not history or history[0].actor != -1:
            raise IncompleteAdjudicationHistoryError(
                "consecutive action adjudication requires the initial history sentinel"
            )
        if any(record.actor not in (0, 1) for record in history[1:]):
            raise IncompleteAdjudicationHistoryError(
                "consecutive action adjudication encountered an invalid history actor"
            )

        count = 0
        for record in reversed(history[1:]):
            try:
                action = action_from_dict(json.loads(record.action_signature))
            except (TypeError, ValueError, KeyError, IndexError) as exc:
                raise IncompleteAdjudicationHistoryError(
                    "consecutive action adjudication encountered a malformed action record"
                ) from exc
            if isinstance(action, PassAction):
                action_class = "pass"
            elif isinstance(action, (BoardMove, SemanticBoardMove)):
                action_class = "board_move"
            elif isinstance(action, (DropMove, SemanticDropMove)):
                action_class = "drop"
            else:
                raise IncompleteAdjudicationHistoryError(
                    "consecutive action adjudication encountered an unsupported action"
                )
            if action_class != adjudication.action_class:
                break
            count += 1
            if count >= adjudication.threshold:
                return "DRAW"
    return None


def automatic_adjudication_status(
    adjudications,
    ply_count: int,
    history,
    *,
    history_complete: bool = True,
):
    """Return ``None``, ``PENDING`` or the configured terminal outcome.

    History index zero is the initial-position sentinel; completed move ``N``
    is therefore ``history[N]``.  A configured rule is deliberately fail
    closed once its threshold is reached unless that complete prefix is
    available.  The continuation policy uses the threshold actor's
    ``gave_check`` evidence, never the current position's check state.
    """
    for adjudication in adjudications:
        if ply_count < adjudication.trigger_ply:
            continue
        if not history_complete or len(history) != ply_count + 1:
            raise IncompleteAdjudicationHistoryError(
                f"automatic adjudication {adjudication.adjudication_id!r} "
                f"requires complete history through ply {ply_count}"
            )
        if not history or history[0].actor != -1:
            raise IncompleteAdjudicationHistoryError(
                f"automatic adjudication {adjudication.adjudication_id!r} "
                "requires the initial history sentinel"
            )
        if any(record.actor not in (0, 1) for record in history[1:]):
            raise IncompleteAdjudicationHistoryError(
                f"automatic adjudication {adjudication.adjudication_id!r} "
                "encountered an invalid history actor"
            )

        threshold_record = history[adjudication.trigger_ply]
        if adjudication.continuation_policy == "threshold_actor_continuous_check":
            if not threshold_record.gave_check:
                return adjudication.outcome
            checker = threshold_record.actor
            for record in history[adjudication.trigger_ply + 1 :]:
                if record.actor == checker and not record.gave_check:
                    return adjudication.outcome
            return "PENDING"
        raise IncompleteAdjudicationHistoryError(
            f"unsupported continuation policy "
            f"{adjudication.continuation_policy!r}"
        )
    return None
