"""Opt-in, identity-aware trace of pseudo-capture eligibility.

This module records rule facts only. It does not classify chase, evasion,
legality of a threat policy, or any WXF verdict.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from .actions import (
    action_from_dict,
    action_is_board,
    action_is_drop,
    action_source_square,
    action_target_square,
)
from .capture_sources import (
    query_counterfactual_legal_capture_sources,
    query_pseudo_capture_sources,
)
from .coordinates import Square, index_to_square, square_to_index
from .history_provenance import (
    PieceInstanceId,
    ProvenanceFrame,
    reconstruct_history_provenance,
)
from .position import GameState


@dataclass(frozen=True, slots=True)
class CapturePressureFact:
    """One source-token/target-token eligibility observation around a ply."""

    ply: int
    actor: int
    source_token: PieceInstanceId
    target_token: PieceInstanceId
    before_source: Square | None
    after_source: Square | None
    before_target: Square | None
    after_target: Square | None
    pseudo_capture_before: bool
    pseudo_capture_after: bool
    action_source_token: PieceInstanceId | None
    action_target_token: PieceInstanceId | None
    target_transition: Literal[
        "stayed", "moved", "captured", "left_board", "appeared"
    ]


@dataclass(frozen=True, slots=True)
class CapturePressureTrace:
    status: Literal["verified", "unknown"]
    facts: tuple[CapturePressureFact, ...] = ()
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class NextTurnLegalCaptureFact:
    """One next-turn legal capture edge after an intervening opponent turn."""

    frame_ply: int
    actor: int
    side_to_move: int
    source_token: PieceInstanceId
    target_token: PieceInstanceId
    source: Square
    target: Square


@dataclass(frozen=True, slots=True)
class NextTurnLegalCaptureTrace:
    status: Literal["verified", "unknown"]
    facts: tuple[NextTurnLegalCaptureFact, ...] = ()
    reason: str | None = None


def _capture_edges(frame: ProvenanceFrame, compiled):
    edges = {}
    shape = frame.position.board_shape
    for target_index, target_piece in enumerate(frame.position.board):
        if target_piece is None:
            continue
        target = index_to_square(target_index, shape)
        target_token = frame.identities[target_index]
        if target_token is None:
            raise ValueError("occupied target lacks verified identity")
        for source in query_pseudo_capture_sources(
            frame.position, target, 1 - target_piece.owner, compiled
        ):
            source_index = square_to_index(source, shape)
            source_token = frame.identities[source_index]
            if source_token is None:
                raise ValueError("capture source lacks verified identity")
            edges[(source_token, target_token)] = (source, target)
    return edges


def _token_location(frame: ProvenanceFrame, token: PieceInstanceId):
    try:
        index = frame.identities.index(token)
    except ValueError:
        return None
    return index_to_square(index, frame.position.board_shape)


def trace_capture_pressure(state: GameState, compiled) -> CapturePressureTrace:
    """Trace pseudo-capture edges over exact replay, or return no facts if unknown."""
    history = reconstruct_history_provenance(state, compiled)
    if history.status != "verified":
        return CapturePressureTrace("unknown", reason=history.reason)

    try:
        by_frame = tuple(_capture_edges(frame, compiled) for frame in history.frames)
        facts = []
        for ply, (before_frame, after_frame, before, after) in enumerate(
            zip(history.frames, history.frames[1:], by_frame, by_frame[1:]), start=1
        ):
            record = state.history[ply]
            action = action_from_dict(json.loads(record.action_signature))
            source_token = target_token = None
            if action_is_board(action):
                source_square = action_source_square(action)
                target_square = action_target_square(action)
                if source_square is not None:
                    source_token = before_frame.identities[
                        square_to_index(
                            source_square, before_frame.position.board_shape
                        )
                    ]
                target_token = before_frame.identities[
                    square_to_index(target_square, before_frame.position.board_shape)
                ]
            elif action_is_drop(action):
                target_square = action_target_square(action)
                target_token = after_frame.identities[
                    square_to_index(target_square, after_frame.position.board_shape)
                ]

            for edge in sorted(
                before.keys() | after.keys(),
                key=lambda item: (item[0].serial, item[1].serial),
            ):
                before_source = _token_location(before_frame, edge[0])
                before_target = _token_location(before_frame, edge[1])
                after_source = _token_location(after_frame, edge[0])
                after_target = _token_location(after_frame, edge[1])
                if before_target is None and after_target is not None:
                    response = "appeared"
                elif before_target is not None and after_target is None:
                    response = (
                        "captured"
                        if action_is_board(action) and edge[1] == target_token
                        else "left_board"
                    )
                elif before_target == after_target:
                    response = "stayed"
                else:
                    response = "moved"
                facts.append(
                    CapturePressureFact(
                        ply=ply,
                        actor=record.actor,
                        source_token=edge[0],
                        target_token=edge[1],
                        before_source=before_source,
                        after_source=after_source,
                        before_target=before_target,
                        after_target=after_target,
                        pseudo_capture_before=edge in before,
                        pseudo_capture_after=edge in after,
                        action_source_token=source_token,
                        action_target_token=target_token,
                        target_transition=response,
                    )
                )
        return CapturePressureTrace("verified", tuple(facts))
    except Exception as exc:
        return CapturePressureTrace(
            "unknown", reason=f"capture trace failed: {type(exc).__name__}: {exc}"
        )


def trace_next_turn_legal_captures(
    state: GameState, compiled
) -> NextTurnLegalCaptureTrace:
    """Join verified after-move frames to counterfactual legal capture edges.

    For each completed frame, ``actor`` is its just-finished mover and
    ``side_to_move`` is the intervening opponent. The side switch holds the
    board fixed; no opponent action or actual future turn is predicted. Facts
    are limited to non-anchor opposing targets. Any unverified history,
    unsupported side switch, or missing identity invalidates the whole trace;
    no partial facts are returned. This records capture availability only,
    not a WXF chase/root decision.
    """
    from .semantic_executor import semantic_engine_for

    provenance = reconstruct_history_provenance(state, compiled)
    if provenance.status != "verified":
        return NextTurnLegalCaptureTrace("unknown", reason=provenance.reason)

    try:
        engine = semantic_engine_for(compiled)
        if engine is not None:
            metadata = engine.support.type_metadata
            is_anchor = lambda piece: metadata[piece.current_type_id].is_anchor
        else:
            type_metadata = compiled.types_by_id
            is_anchor = lambda piece: type_metadata[piece.current_type_id].is_anchor

        facts = []
        for frame in provenance.frames[1:]:
            actor = state.history[frame.ply].actor
            side_to_move = frame.position.side_to_move
            if actor not in (0, 1) or side_to_move != 1 - actor:
                return NextTurnLegalCaptureTrace(
                    "unknown", reason="history actor does not match replayed turn order"
                )
            for target_index, target_piece in enumerate(frame.position.board):
                if target_piece is None or target_piece.owner == actor:
                    continue
                if is_anchor(target_piece):
                    continue
                target = index_to_square(target_index, frame.position.board_shape)
                sources = query_counterfactual_legal_capture_sources(
                    frame.position, target, actor, compiled
                )
                if sources is None:
                    return NextTurnLegalCaptureTrace(
                        "unknown",
                        reason=(
                            "counterfactual turn is unsupported at frame "
                            f"{frame.ply}, target {target}"
                        ),
                    )
                target_token = frame.identities[target_index]
                if target_token is None:
                    return NextTurnLegalCaptureTrace(
                        "unknown", reason="opposing target lacks verified identity"
                    )
                for source in sources:
                    source_index = square_to_index(source, frame.position.board_shape)
                    source_token = frame.identities[source_index]
                    if source_token is None:
                        return NextTurnLegalCaptureTrace(
                            "unknown", reason="legal capture source lacks verified identity"
                        )
                    facts.append(
                        NextTurnLegalCaptureFact(
                            frame_ply=frame.ply,
                            actor=actor,
                            side_to_move=side_to_move,
                            source_token=source_token,
                            target_token=target_token,
                            source=source,
                            target=target,
                        )
                    )
        facts.sort(
            key=lambda fact: (
                fact.frame_ply,
                fact.source_token.serial,
                fact.target_token.serial,
            )
        )
        return NextTurnLegalCaptureTrace("verified", tuple(facts))
    except Exception as exc:
        return NextTurnLegalCaptureTrace(
            "unknown", reason=f"legal-capture trace failed: {type(exc).__name__}: {exc}"
        )
