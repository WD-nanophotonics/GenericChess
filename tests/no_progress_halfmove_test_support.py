"""Test-only reconstruction of a generic no-progress halfmove fact.

This intentionally derives facts from immutable GameState history by replaying
the canonical action signatures through the ordinary transition API. It does
not store a counter or alter production state, RuleSet, or terminal behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from generic_chess.core.actions import (
    PassAction,
    action_from_dict,
    action_is_board,
    action_source_square,
)
from generic_chess.core.coordinates import square_to_index
from generic_chess.core.position import GameState, HistoryRecord, Position
from generic_chess.core.transition import apply_action, initial_state


@dataclass(frozen=True, slots=True)
class NoProgressHalfmoveFact:
    """Verified suffix length, or fail-closed unknown when replay is incomplete."""

    status: Literal["verified", "unknown"]
    count: int | None
    reset_reasons: tuple[str, ...] = ()
    reason: str | None = None


def _unknown(reason: str) -> NoProgressHalfmoveFact:
    return NoProgressHalfmoveFact("unknown", None, reason=reason)


def _owned_entity_counts(position: Position) -> tuple[int, int]:
    counts = [0, 0]
    for piece in position.board:
        if piece is None:
            continue
        if piece.owner not in (0, 1):
            raise ValueError("piece has an invalid owner")
        counts[piece.owner] += 1
    for owner, hand in enumerate(position.hands):
        counts[owner] += hand.total()
    return counts[0], counts[1]


def _capture_fact(
    before: Position, after: Position, actor: int
) -> tuple[bool | None, str | None]:
    """Recognize a capture from authoritative pre/post piece inventories.

    Capturing may remove an opposing token or transfer it to the mover's hand.
    No destination-square guess is used, so off-target captures are represented
    by the same inventory transition.
    """
    try:
        before_counts = _owned_entity_counts(before)
        after_counts = _owned_entity_counts(after)
    except (AttributeError, TypeError, ValueError) as exc:
        return None, f"piece inventory unavailable: {exc}"
    deltas = tuple(after_counts[owner] - before_counts[owner] for owner in (0, 1))
    own_delta, opponent_delta = deltas[actor], deltas[1 - actor]
    if own_delta == 0 and opponent_delta == 0:
        return False, None
    if opponent_delta < 0 and own_delta in (0, -opponent_delta):
        return True, None
    return None, "action produced an unclassified owner-inventory transition"


def extract_no_progress_halfmove_fact(
    state: GameState,
    compiled,
    *,
    reset_type_ids: frozenset[str] | set[str] | tuple[str, ...],
) -> NoProgressHalfmoveFact:
    """Replay complete canonical history and count plies since the last reset.

    ``reset_type_ids`` is declarative input. A mover type is read from the
    pre-action board piece's *current* type, not from a public action's optional
    actor label. Captures are recognized from verified owner inventories
    before and after transition. Any malformed, truncated, custom-root, or
    replay-inconsistent history returns unknown rather than guessing.
    """
    if not isinstance(state, GameState):
        return _unknown("input is not a GameState")
    if isinstance(reset_type_ids, (str, bytes)):
        return _unknown("reset type IDs must be a collection of strings")
    try:
        reset_types = frozenset(reset_type_ids)
    except TypeError:
        return _unknown("reset type IDs are not iterable")
    if any(not isinstance(type_id, str) or not type_id for type_id in reset_types):
        return _unknown("reset type IDs must be non-empty strings")
    types_by_id = getattr(compiled, "types_by_id", {})
    if any(type_id not in types_by_id for type_id in reset_types):
        return _unknown("a configured reset type is absent from the compiled RuleSet")
    if isinstance(state.ply_count, bool) or state.ply_count < 0:
        return _unknown("ply count is invalid")
    if len(state.history) != state.ply_count + 1:
        return _unknown("history does not cover every completed ply")
    if not state.history or not isinstance(state.history[0], HistoryRecord):
        return _unknown("initial history record is missing or malformed")

    try:
        replayed = initial_state(compiled)
        initial_setup_positions = getattr(compiled, "initial_setup_positions", {})
        if state.history[0] != replayed.history[0]:
            for setup_key in initial_setup_positions:
                candidate = initial_state(compiled, setup_key)
                if state.history[0] == candidate.history[0]:
                    replayed = candidate
                    break
            else:
                return _unknown("history does not begin at a declared initial setup")
        if state.history[0] != replayed.history[0]:
            return _unknown("history root does not match the replayed setup")

        count = 0
        last_reset_reasons = ("initial",)
        for ply, record in enumerate(state.history[1:], start=1):
            if not isinstance(record, HistoryRecord) or not record.action_signature:
                return _unknown(f"missing canonical action at ply {ply}")
            try:
                action_data = json.loads(record.action_signature)
                action = action_from_dict(action_data)
            except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
                return _unknown(f"malformed action at ply {ply}: {exc}")

            before = replayed.position
            actor = before.side_to_move
            mover_type = None
            if action_is_board(action):
                source = action_source_square(action)
                if source is None:
                    return _unknown(f"board action lacks a source at ply {ply}")
                try:
                    source_index = square_to_index(source, before.board_shape)
                    mover = before.board[source_index]
                except (IndexError, TypeError, ValueError) as exc:
                    return _unknown(f"invalid mover square at ply {ply}: {exc}")
                if mover is None or mover.owner != actor:
                    return _unknown(f"mover cannot be established at ply {ply}")
                mover_type = mover.current_type_id
            elif not isinstance(action, PassAction) and not hasattr(action, "to_square"):
                return _unknown(f"unsupported action at ply {ply}")

            try:
                replayed = apply_action(replayed, action, compiled)
            except Exception as exc:
                return _unknown(f"authoritative replay failed at ply {ply}: {exc}")
            if replayed.history[-1] != record:
                return _unknown(f"history record does not match replay at ply {ply}")

            capture = False
            if action_is_board(action):
                capture, capture_error = _capture_fact(
                    before, replayed.position, actor
                )
                if capture is None:
                    return _unknown(f"capture status unknown at ply {ply}: {capture_error}")

            reasons = []
            if capture:
                reasons.append("capture")
            if mover_type in reset_types:
                reasons.append(f"mover_type:{mover_type}")
            if reasons:
                count = 0
                last_reset_reasons = tuple(reasons)
            else:
                count += 1
                last_reset_reasons = ()

        if (
            replayed.position != state.position
            or replayed.ply_count != state.ply_count
            or replayed.repetition_counts != tuple(state.repetition_counts)
            or replayed.terminal_status != state.terminal_status
        ):
            return _unknown("replayed history does not match the supplied state")
        return NoProgressHalfmoveFact(
            "verified", count, last_reset_reasons
        )
    except Exception as exc:
        return _unknown(f"history replay failed: {type(exc).__name__}: {exc}")
