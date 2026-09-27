"""Shared history-based automatic adjudication primitives."""

from __future__ import annotations

import json

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
