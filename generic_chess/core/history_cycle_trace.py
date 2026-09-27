"""Opt-in capture facts bounded to the latest repeated-position interval.

This module joins verified replay provenance to existing legal-capture facts.
It identifies a repeated-position interval only; it does not classify chase,
infer reply intent, or apply a ruleset-specific adjudication policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .capture_pressure_trace import (
    NextTurnLegalCaptureFact,
    trace_next_turn_legal_captures,
)
from .history_provenance import reconstruct_history_provenance
from .position import GameState


@dataclass(frozen=True, slots=True)
class RepeatedPositionCycleCaptureFacts:
    """One interval between the last two visits to the current position."""

    position_key: str
    start_ply: int
    end_ply: int
    capture_facts: tuple[NextTurnLegalCaptureFact, ...]


@dataclass(frozen=True, slots=True)
class RepeatedPositionCycleTrace:
    """Fail-closed result; ``cycle=None`` means verified history has no repeat."""

    status: Literal["verified", "unknown"]
    cycle: RepeatedPositionCycleCaptureFacts | None = None
    reason: str | None = None


def trace_latest_repeated_cycle_capture_facts(
    state: GameState, compiled
) -> RepeatedPositionCycleTrace:
    """Return ordered, identity-bearing capture facts for the latest cycle.

    The interval is the moves after the previous occurrence of the current
    position through the current occurrence: ``start_ply < frame_ply <=
    end_ply``. A complete exact replay and a fully verified legal-capture
    trace are both required. Incomplete or unsupported histories return
    ``unknown`` with no partial cycle or facts.
    """
    provenance = reconstruct_history_provenance(state, compiled)
    if provenance.status != "verified":
        return RepeatedPositionCycleTrace("unknown", reason=provenance.reason)

    capture_trace = trace_next_turn_legal_captures(state, compiled)
    if capture_trace.status != "verified":
        return RepeatedPositionCycleTrace("unknown", reason=capture_trace.reason)

    if not state.history or len(provenance.frames) != len(state.history):
        return RepeatedPositionCycleTrace(
            "unknown", reason="verified replay did not align with history plies"
        )

    current_key = state.history[-1].position_key
    occurrences = [
        ply for ply, record in enumerate(state.history)
        if record.position_key == current_key
    ]
    if len(occurrences) < 2:
        return RepeatedPositionCycleTrace("verified")

    start_ply, end_ply = occurrences[-2], occurrences[-1]
    if start_ply >= end_ply or end_ply != state.ply_count:
        return RepeatedPositionCycleTrace(
            "unknown", reason="current repeated-position interval is inconsistent"
        )

    facts = tuple(
        sorted(
            (
                fact for fact in capture_trace.facts
                if start_ply < fact.frame_ply <= end_ply
            ),
            key=lambda fact: (
                fact.frame_ply,
                fact.source_token.serial,
                fact.target_token.serial,
            ),
        )
    )
    return RepeatedPositionCycleTrace(
        "verified",
        RepeatedPositionCycleCaptureFacts(
            position_key=current_key,
            start_ply=start_ply,
            end_ply=end_ply,
            capture_facts=facts,
        ),
    )
