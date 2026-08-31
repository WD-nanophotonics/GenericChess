"""Shared history-based automatic adjudication primitives."""

from __future__ import annotations


class IncompleteAdjudicationHistoryError(ValueError):
    """Raised when a threshold rule lacks authoritative completed-move history."""


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
