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
    trace_capture_pressure,
    trace_next_turn_legal_captures,
)
from .capture_sources import query_counterfactual_legal_capture_sources
from .coordinates import index_to_square
from .history_provenance import PieceInstanceId, reconstruct_history_provenance
from .position import GameState


@dataclass(frozen=True, slots=True)
class CaptureEdgeResponseFact:
    """Observed next action and exact edge status after that response.

    ``None`` means the response or the corresponding fact is unavailable; it
    is never converted to a guessed yes/no value.
    """

    threat_frame_ply: int
    response_ply: int | None
    response_wrapped: bool
    actor: int
    response_actor: int | None
    source_token: PieceInstanceId
    target_token: PieceInstanceId
    response_action_source_token: PieceInstanceId | None
    response_action_target_token: PieceInstanceId | None
    target_moved: bool | None
    specific_capture_still_legal: bool | None


@dataclass(frozen=True, slots=True)
class RepeatedPositionCycleCaptureFacts:
    """One verified repeat window ending at the current position."""

    position_key: str
    start_ply: int
    end_ply: int
    capture_facts: tuple[NextTurnLegalCaptureFact, ...]
    response_facts: tuple[CaptureEdgeResponseFact, ...] = ()
    action_actors: tuple[tuple[int, int], ...] = ()


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

    The interval ends at the current position. When the configured repetition
    limit has been reached, it spans the last ``repetition_limit`` occurrences;
    otherwise it spans the last two occurrences. Moves are bounded by
    ``start_ply < frame_ply <= end_ply``. A complete exact replay and fully
    verified capture traces are required. At a closed boundary, the first
    observed response can wrap to the last threat only when the positions and
    the source/target token locations match exactly. Unsupported or
    incomplete evidence stays unknown.
    """
    provenance = reconstruct_history_provenance(state, compiled)
    if provenance.status != "verified":
        return RepeatedPositionCycleTrace("unknown", reason=provenance.reason)

    capture_trace = trace_next_turn_legal_captures(state, compiled)
    if capture_trace.status != "verified":
        return RepeatedPositionCycleTrace("unknown", reason=capture_trace.reason)
    pressure_trace = trace_capture_pressure(state, compiled)
    if pressure_trace.status != "verified":
        return RepeatedPositionCycleTrace("unknown", reason=pressure_trace.reason)

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

    support = getattr(compiled, "support", None)
    configured_limit = getattr(
        support,
        "repetition_limit",
        getattr(compiled, "repetition_limit", 2),
    )
    repeat_limit = max(2, int(configured_limit))
    window = (
        occurrences[-repeat_limit:]
        if len(occurrences) >= repeat_limit
        else occurrences[-2:]
    )
    start_ply, end_ply = window[0], window[-1]
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
    pressure_by_ply_and_edge = {
        (fact.ply, fact.source_token, fact.target_token): fact
        for fact in pressure_trace.facts
    }
    frame_by_ply = {frame.ply: frame for frame in provenance.frames}
    responses = []
    for fact in facts:
        response_ply = fact.frame_ply + 1
        response_wrapped = response_ply > end_ply
        if response_ply > end_ply:
            response_ply = start_ply + 1
            start_frame = frame_by_ply[start_ply]
            end_frame = frame_by_ply[end_ply]
            boundary_identity_matches = (
                start_frame.position == end_frame.position
                and fact.source_token in start_frame.identities
                and fact.source_token in end_frame.identities
                and fact.target_token in start_frame.identities
                and fact.target_token in end_frame.identities
                and start_frame.identities.index(fact.source_token)
                == end_frame.identities.index(fact.source_token)
                and start_frame.identities.index(fact.target_token)
                == end_frame.identities.index(fact.target_token)
            )
            if not boundary_identity_matches:
                responses.append(
                    CaptureEdgeResponseFact(
                        threat_frame_ply=fact.frame_ply,
                        response_ply=response_ply,
                        response_wrapped=True,
                        actor=fact.actor,
                        response_actor=None,
                        source_token=fact.source_token,
                        target_token=fact.target_token,
                        response_action_source_token=None,
                        response_action_target_token=None,
                        target_moved=None,
                        specific_capture_still_legal=None,
                    )
                )
                continue

        response_record = state.history[response_ply]
        if response_record.actor != 1 - fact.actor:
            return RepeatedPositionCycleTrace(
                "unknown", reason="capture edge and response actors do not alternate"
            )
        pressure = pressure_by_ply_and_edge.get(
            (response_ply, fact.source_token, fact.target_token)
        )
        if pressure is None:
            return RepeatedPositionCycleTrace(
                "unknown", reason="verified response lacks its adjacent capture-pressure fact"
            )

        if pressure.target_transition == "moved":
            target_moved: bool | None = True
        elif pressure.target_transition in ("stayed", "captured", "left_board"):
            target_moved = False
        else:
            target_moved = None

        response_frame = frame_by_ply[response_ply]
        target_index = (
            response_frame.identities.index(fact.target_token)
            if fact.target_token in response_frame.identities
            else None
        )
        source_index = (
            response_frame.identities.index(fact.source_token)
            if fact.source_token in response_frame.identities
            else None
        )
        if target_index is None or source_index is None:
            capture_still_legal: bool | None = False
        else:
            target_piece = response_frame.position.board[target_index]
            if target_piece is None or target_piece.owner == fact.actor:
                capture_still_legal = False
            else:
                target_square = index_to_square(
                    target_index, response_frame.position.board_shape
                )
                source_square = index_to_square(
                    source_index, response_frame.position.board_shape
                )
                try:
                    legal_sources = query_counterfactual_legal_capture_sources(
                        response_frame.position, target_square, fact.actor, compiled
                    )
                except Exception as exc:
                    return RepeatedPositionCycleTrace(
                        "unknown",
                        reason=(
                            "response legal-capture query failed: "
                            f"{type(exc).__name__}: {exc}"
                        ),
                    )
                capture_still_legal = (
                    None if legal_sources is None else source_square in legal_sources
                )

        responses.append(
            CaptureEdgeResponseFact(
                threat_frame_ply=fact.frame_ply,
                response_ply=response_ply,
                response_wrapped=response_wrapped,
                actor=fact.actor,
                response_actor=response_record.actor,
                source_token=fact.source_token,
                target_token=fact.target_token,
                response_action_source_token=pressure.action_source_token,
                response_action_target_token=pressure.action_target_token,
                target_moved=target_moved,
                specific_capture_still_legal=capture_still_legal,
            )
        )
    return RepeatedPositionCycleTrace(
        "verified",
        RepeatedPositionCycleCaptureFacts(
            position_key=current_key,
            start_ply=start_ply,
            end_ply=end_ply,
            capture_facts=facts,
            response_facts=tuple(responses),
            action_actors=tuple(
                (ply, state.history[ply].actor)
                for ply in range(start_ply + 1, end_ply + 1)
            ),
        ),
    )
