"""Opt-in capture facts bounded to the latest repeated-position interval.

This module joins verified replay provenance to existing legal-capture facts.
It identifies a repeated-position interval only; it does not classify chase,
infer reply intent, or apply a ruleset-specific adjudication policy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from .actions import action_from_dict, action_source_square
from .capture_pressure_trace import (
    NextTurnLegalCaptureFact,
    trace_capture_pressure,
    trace_next_turn_legal_captures,
)
from .capture_sources import query_counterfactual_legal_capture_sources
from .coordinates import index_to_square, square_to_index
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
    action_source_tokens: tuple[tuple[int, PieceInstanceId | None], ...] = ()


@dataclass(frozen=True, slots=True)
class RepeatedPositionCycleTrace:
    """Fail-closed result; ``cycle=None`` means verified history has no repeat."""

    status: Literal["verified", "unknown"]
    cycle: RepeatedPositionCycleCaptureFacts | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ActorCycleTargetSummary:
    """Observed non-anchor legal-capture target identities on cycle turns.

    Each turn is included, even when it has no legal-capture targets. The
    all-source intersection is descriptive. The mover-source intersection is
    narrower: its source token must be the piece moved on that exact turn.
    """

    actor: int
    targets_by_ply: tuple[tuple[int, tuple[PieceInstanceId, ...]], ...]
    shared_target_tokens: tuple[PieceInstanceId, ...]
    all_target_tokens: tuple[PieceInstanceId, ...]
    mover_targets_by_ply: tuple[tuple[int, tuple[PieceInstanceId, ...]], ...] = ()
    shared_mover_target_tokens: tuple[PieceInstanceId, ...] = ()

    @property
    def shared_target_count(self) -> int:
        return len(self.shared_target_tokens)

    @property
    def distinct_target_count(self) -> int:
        return len(self.all_target_tokens)

    @property
    def shared_mover_target_count(self) -> int:
        return len(self.shared_mover_target_tokens)


@dataclass(frozen=True, slots=True)
class RepeatedCycleTargetSummary:
    """Immutable, game-name-independent target-set projection of a cycle."""

    status: Literal["verified", "unknown"]
    actors: tuple[ActorCycleTargetSummary, ...] = ()
    reason: str | None = None


def evaluate_repeated_cycle_target_condition(
    summary: RepeatedCycleTargetSummary, actor: int
) -> Literal["satisfied", "unsatisfied", "unknown"]:
    """Evaluate whether the moved source token shared a target across its turns."""
    if summary.status != "verified":
        return "unknown"
    if isinstance(actor, bool) or actor not in (0, 1):
        return "unknown"
    actor_summary = next(
        (item for item in summary.actors if item.actor == actor), None
    )
    if actor_summary is None:
        return "unsatisfied"
    return (
        "satisfied"
        if actor_summary.shared_mover_target_count >= 1
        else "unsatisfied"
    )


def summarize_repeated_cycle_targets(
    trace: RepeatedPositionCycleTrace,
) -> RepeatedCycleTargetSummary:
    """Summarize legal-capture target tokens over each actor's repeated-cycle turns.

    This projection consumes only a verified repeated-cycle trace. It preserves
    empty target sets for turns with no observed legal captures and reports the
    per-actor cross-turn intersection and union. It does not infer chase,
    response intent, role exceptions, or any adjudication result.
    """
    if trace.status != "verified":
        return RepeatedCycleTargetSummary("unknown", reason=trace.reason)
    cycle = trace.cycle
    if cycle is None:
        return RepeatedCycleTargetSummary("verified")

    actors_by_ply = dict(cycle.action_actors)
    if len(actors_by_ply) != len(cycle.action_actors):
        return RepeatedCycleTargetSummary(
            "unknown", reason="repeated-cycle actor list contains duplicate plies"
        )
    mover_by_ply = dict(cycle.action_source_tokens)
    if (
        len(mover_by_ply) != len(cycle.action_source_tokens)
        or set(mover_by_ply) != set(actors_by_ply)
    ):
        return RepeatedCycleTargetSummary(
            "unknown", reason="repeated-cycle mover identities do not align with actor plies"
        )
    targets_by_ply: dict[int, set[PieceInstanceId]] = {
        ply: set() for ply, _actor in cycle.action_actors
    }
    mover_targets_by_ply: dict[int, set[PieceInstanceId]] = {
        ply: set() for ply, _actor in cycle.action_actors
    }
    for fact in cycle.capture_facts:
        if actors_by_ply.get(fact.frame_ply) != fact.actor:
            return RepeatedCycleTargetSummary(
                "unknown", reason="capture fact does not match a repeated-cycle actor ply"
            )
        targets_by_ply[fact.frame_ply].add(fact.target_token)
        if fact.source_token == mover_by_ply[fact.frame_ply]:
            mover_targets_by_ply[fact.frame_ply].add(fact.target_token)

    result = []
    for actor in sorted({actor for _ply, actor in cycle.action_actors}):
        actor_turns = tuple(
            (ply, targets_by_ply[ply])
            for ply, mover in cycle.action_actors
            if mover == actor
        )
        source_turns = tuple(
            (ply, mover_targets_by_ply[ply])
            for ply, mover in cycle.action_actors
            if mover == actor
        )
        if not actor_turns:
            continue
        shared = set.intersection(*(targets for _ply, targets in actor_turns))
        union = set.union(*(targets for _ply, targets in actor_turns))
        shared_mover = set.intersection(
            *(targets for _ply, targets in source_turns)
        )
        token_order = lambda token: (
            token.serial,
            token.created_ply,
            token.origin_index,
        )
        result.append(
            ActorCycleTargetSummary(
                actor=actor,
                targets_by_ply=tuple(
                    (ply, tuple(sorted(targets, key=token_order)))
                    for ply, targets in actor_turns
                ),
                shared_target_tokens=tuple(sorted(shared, key=token_order)),
                all_target_tokens=tuple(sorted(union, key=token_order)),
                mover_targets_by_ply=tuple(
                    (ply, tuple(sorted(targets, key=token_order)))
                    for ply, targets in source_turns
                ),
                shared_mover_target_tokens=tuple(
                    sorted(shared_mover, key=token_order)
                ),
            )
        )
    return RepeatedCycleTargetSummary("verified", tuple(result))


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
    try:
        action_source_tokens = tuple(
            _action_source_token(state, provenance.frames, ply)
            for ply in range(start_ply + 1, end_ply + 1)
        )
    except Exception as exc:
        return RepeatedPositionCycleTrace(
            "unknown",
            reason=(
                "cycle action-source identity failed: "
                f"{type(exc).__name__}: {exc}"
            ),
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
            action_source_tokens=action_source_tokens,
        ),
    )


def _action_source_token(state: GameState, frames, ply: int):
    action = action_from_dict(json.loads(state.history[ply].action_signature))
    source = action_source_square(action)
    if source is None:
        return ply, None
    before = frames[ply - 1]
    index = square_to_index(source, before.position.board_shape)
    token = before.identities[index]
    if token is None:
        raise ValueError(f"action source lacks a verified token at ply {ply}")
    return ply, token
