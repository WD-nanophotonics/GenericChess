"""Identity-bearing immediate-recapture facts from verified game history.

This opt-in projection joins the position-level legal-recapture probe to
ephemeral identities reconstructed from complete history. It records facts
only; it does not classify protection, roots, chase, or adjudication outcomes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from .actions import (
    action_from_dict,
    action_is_board,
    action_source_square,
    action_target_square,
)
from .capture_sources import probe_immediate_recaptures
from .coordinates import Square, square_to_index
from .history_provenance import PieceInstanceId, reconstruct_history_provenance
from .position import GameState


@dataclass(frozen=True, slots=True)
class HistoryImmediateRecaptureFact:
    """Verified legal recapture sources joined to stable board identities.

    ``recapturer_tokens`` is parallel to ``recapturer_sources``; both preserve
    the probe's deterministic square order.
    """

    capture_ply: int
    actor: int
    capture_source: Square
    capture_target: Square
    capturer_token: PieceInstanceId
    captured_token: PieceInstanceId
    recapturer_sources: tuple[Square, ...]
    recapturer_tokens: tuple[PieceInstanceId, ...]


@dataclass(frozen=True, slots=True)
class HistoryImmediateRecaptureTrace:
    """All-or-nothing facts for captures in a completely verified history."""

    status: Literal["verified", "unknown"]
    facts: tuple[HistoryImmediateRecaptureFact, ...] = ()
    reason: str | None = None


def _unknown(reason: str) -> HistoryImmediateRecaptureTrace:
    return HistoryImmediateRecaptureTrace("unknown", reason=reason)


def trace_history_immediate_recaptures(
    state: GameState, compiled
) -> HistoryImmediateRecaptureTrace:
    """Join each historical legal capture's recapture squares to piece tokens.

    The capture is replayed from its verified pre-move frame by
    :func:`probe_immediate_recaptures`. Recapture source squares are mapped to
    identities only when those same occupants persist across the actual
    historical capture. Unsupported, incomplete, or mismatched evidence
    invalidates the whole trace; no partial facts are returned.
    """
    provenance = reconstruct_history_provenance(state, compiled)
    if provenance.status != "verified":
        return _unknown(provenance.reason or "history provenance is unknown")
    if len(provenance.frames) != state.ply_count + 1:
        return _unknown("provenance frames do not cover the complete history")

    facts = []
    for ply, record in enumerate(state.history[1:], start=1):
        before_frame = provenance.frames[ply - 1]
        after_frame = provenance.frames[ply]
        if record.actor not in (0, 1) or before_frame.position.side_to_move != record.actor:
            return _unknown(f"history actor does not match turn at ply {ply}")
        try:
            action = action_from_dict(json.loads(record.action_signature))
        except (TypeError, ValueError, KeyError, IndexError) as exc:
            return _unknown(f"malformed action at ply {ply}: {exc}")
        if not action_is_board(action):
            continue

        source = action_source_square(action)
        target = action_target_square(action)
        if source is None or target is None:
            return _unknown(f"board capture action has no source or target at ply {ply}")
        shape = before_frame.position.board_shape
        source_index = square_to_index(source, shape)
        target_index = square_to_index(target, shape)
        mover = before_frame.position.board[source_index]
        victim = before_frame.position.board[target_index]
        if victim is None:
            continue
        if mover is None or mover.owner != record.actor or victim.owner == record.actor:
            return _unknown(f"capture occupants are inconsistent at ply {ply}")

        capturer_token = before_frame.identities[source_index]
        captured_token = before_frame.identities[target_index]
        if capturer_token is None or captured_token is None:
            return _unknown(f"capture identity is unavailable at ply {ply}")
        probe = probe_immediate_recaptures(before_frame.position, action, compiled)
        if probe.status != "verified":
            return _unknown(
                f"immediate recapture probe is unknown at ply {ply}: "
                f"{probe.reason or 'unsupported capture'}"
            )
        if probe.capture_source != source or probe.capture_target != target:
            return _unknown(f"probe capture does not match history at ply {ply}")
        if (
            after_frame.position.board[source_index] is not None
            or after_frame.identities[source_index] is not None
            or after_frame.identities[target_index] != capturer_token
        ):
            return _unknown(f"capture identity transition is inconsistent at ply {ply}")

        recapturer_tokens = []
        for recapture_source in probe.recapture_sources:
            recapture_index = square_to_index(recapture_source, shape)
            recapturer = before_frame.position.board[recapture_index]
            recapturer_token = before_frame.identities[recapture_index]
            if (
                recapturer is None
                or recapturer.owner != 1 - record.actor
                or recapturer_token is None
                or after_frame.position.board[recapture_index] != recapturer
                or after_frame.identities[recapture_index] != recapturer_token
            ):
                return _unknown(
                    f"recapture source identity is not preserved at ply {ply}"
                )
            recapturer_tokens.append(recapturer_token)

        facts.append(
            HistoryImmediateRecaptureFact(
                capture_ply=ply,
                actor=record.actor,
                capture_source=source,
                capture_target=target,
                capturer_token=capturer_token,
                captured_token=captured_token,
                recapturer_sources=probe.recapture_sources,
                recapturer_tokens=tuple(recapturer_tokens),
            )
        )

    return HistoryImmediateRecaptureTrace("verified", tuple(facts))
