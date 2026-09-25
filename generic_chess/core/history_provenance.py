"""Opt-in reconstruction of ephemeral on-board piece provenance.

This diagnostic deliberately does not add identity to ``Piece`` or ``Position``
and is never called by ordinary transitions, move generation, or adjudication.
It only returns identities when the public history can be replayed exactly
from the ruleset's declared initial state.

The supported action slice is one ordinary on-board mover with at most a
capture on its destination, or one drop onto an empty square. Any transition
with additional board effects (for example, a multi-piece semantic action) is
reported as unknown rather than guessed from the primary source/target.
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
from .coordinates import square_to_index
from .position import GameState, HistoryRecord, Position


@dataclass(frozen=True, slots=True)
class PieceInstanceId:
    """Ephemeral identity, local to a single provenance reconstruction."""

    serial: int
    created_ply: int
    origin_index: int


@dataclass(frozen=True, slots=True)
class ProvenanceFrame:
    """Instance identities aligned with ``Position.board`` for one ply."""

    ply: int
    identities: tuple[PieceInstanceId | None, ...]


@dataclass(frozen=True, slots=True)
class HistoryProvenance:
    """Fail-closed result of explicitly requested history reconstruction."""

    status: Literal["verified", "unknown"]
    frames: tuple[ProvenanceFrame, ...] = ()
    reason: str | None = None


def _unknown(reason: str) -> HistoryProvenance:
    return HistoryProvenance(status="unknown", reason=reason)


def _same_instance(before, after) -> bool:
    # Promotion may change current_type_id/promoted, but ownership and base
    # type are intrinsic to the board instance throughout its on-board life.
    return (
        before is not None
        and after is not None
        and before.owner == after.owner
        and before.base_type_id == after.base_type_id
    )


def _advance_identities(
    before: Position,
    after: Position,
    identities: tuple[PieceInstanceId | None, ...],
    action,
    ply: int,
    next_serial: int,
) -> tuple[tuple[PieceInstanceId | None, ...], int]:
    shape = before.board_shape
    if after.board_shape != shape or len(identities) != len(before.board):
        raise ValueError("board shape changed during replay")
    changed = {i for i, (a, b) in enumerate(zip(before.board, after.board)) if a != b}
    moved = list(identities)

    if action_is_board(action):
        source = action_source_square(action)
        if source is None:
            raise ValueError("board action has no source square")
        target = action_target_square(action)
        src = square_to_index(source, shape)
        dst = square_to_index(target, shape)
        if src == dst or src not in changed or dst not in changed:
            raise ValueError("board action does not match the observed board delta")
        if before.board[src] is None or after.board[src] is not None:
            raise ValueError("board mover did not leave its source square")
        if not _same_instance(before.board[src], after.board[dst]):
            raise ValueError("board mover identity cannot be verified at destination")
        if identities[src] is None:
            raise ValueError("board mover has no reconstructed identity")
        if changed - {src, dst}:
            raise ValueError("unexpected board changes outside action squares")
        moved[src] = None
        moved[dst] = identities[src]
    elif action_is_drop(action):
        dst = square_to_index(action_target_square(action), shape)
        if changed != {dst} or before.board[dst] is not None or after.board[dst] is None:
            raise ValueError("drop action does not match a single-square appearance")
        placed = after.board[dst]
        if placed.base_type_id != action.base_type_id:
            raise ValueError("dropped piece type does not match its action")
        moved[dst] = PieceInstanceId(next_serial, ply, dst)
        next_serial += 1
    else:  # Defensive if the public Action union ever grows.
        raise ValueError("unsupported action shape")

    # Any board occupant remaining at the same square must retain its identity.
    for index, (old_piece, new_piece) in enumerate(zip(before.board, after.board)):
        if index in changed:
            continue
        if old_piece != new_piece:
            raise ValueError("unreported board mutation")
        if (new_piece is None) != (moved[index] is None):
            raise ValueError("piece occupancy lacks a matching identity")
    for index, piece in enumerate(after.board):
        if (piece is None) != (moved[index] is None):
            raise ValueError("resulting board occupancy is not fully identified")
    return tuple(moved), next_serial


def reconstruct_history_provenance(state: GameState, compiled) -> HistoryProvenance:
    """Reconstruct board-instance identities from a complete verifiable history.

    This function is opt-in and side-effect-free. Custom/imported roots,
    truncated records, malformed action signatures, and any replay mismatch
    produce ``status='unknown'`` rather than guessed identities.
    """
    from .transition import apply_action, initial_state

    try:
        replayed = initial_state(compiled)
        if not state.history:
            return _unknown("empty history")
        first = state.history[0]
        if first != replayed.history[0]:
            return _unknown("history does not begin at the declared initial state")
        if len(state.history) != state.ply_count + 1:
            return _unknown("history length does not cover every ply")

        identities: tuple[PieceInstanceId | None, ...] = tuple(
            PieceInstanceId(i, 0, i) if piece is not None else None
            for i, piece in enumerate(replayed.position.board)
        )
        serial = len(identities)
        frames = [ProvenanceFrame(0, identities)]
        for ply, record in enumerate(state.history[1:], start=1):
            if not isinstance(record, HistoryRecord) or not record.action_signature:
                return _unknown(f"missing canonical action at ply {ply}")
            action = action_from_dict(json.loads(record.action_signature))
            before = replayed.position
            replayed = apply_action(replayed, action, compiled)
            if replayed.history[-1] != record:
                return _unknown(f"history record mismatch at ply {ply}")
            identities, serial = _advance_identities(
                before,
                replayed.position,
                identities,
                action,
                ply,
                serial,
            )
            frames.append(ProvenanceFrame(ply, identities))

        if (
            replayed.position != state.position
            or replayed.ply_count != state.ply_count
            or replayed.repetition_counts != tuple(state.repetition_counts)
            or replayed.terminal_status != state.terminal_status
        ):
            return _unknown("replayed history does not match supplied game state")
        return HistoryProvenance(status="verified", frames=tuple(frames))
    except Exception as exc:
        return _unknown(f"history replay failed: {type(exc).__name__}: {exc}")
