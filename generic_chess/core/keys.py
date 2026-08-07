"""Stable position keys (never Python's process-randomized ``hash``)."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from .errors import ensure_ruleset_match
from .position import Position

if TYPE_CHECKING:
    from ..rules.compiled import CompiledRuleSet


def position_key(position: Position, compiled: "CompiledRuleSet") -> str:
    """A SHA-256 key over everything that defines a repetition-relevant position:

    * ruleset fingerprint
    * side to move
    * every square's owner, base type, current type and promoted flag
    * both hands (base type and quantity)
    """
    ensure_ruleset_match(position, compiled)
    board: list[list | None] = []
    for piece in position.board:
        if piece is None:
            board.append(None)
        else:
            board.append([piece.owner, piece.base_type_id, piece.current_type_id, piece.promoted])
    hands = [[list(h.counts) for h in position.hands]]
    payload = {
        "ruleset": compiled.ruleset_fingerprint,
        "side_to_move": position.side_to_move,
        "board": board,
        "hands": hands,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def semantic_position_key(
    position: Position,
    support,
    aux_slots: tuple = (),
) -> str:
    """Position identity for semantic rulesets: board/hands/side plus
    auxiliary slot values.  Legacy empty-aux positions are handled by the
    legacy :func:`position_key` and keep their historical keys."""
    board: list[list | None] = []
    for piece in position.board:
        if piece is None:
            board.append(None)
        else:
            board.append(
                [piece.owner, piece.base_type_id, piece.current_type_id, piece.promoted]
            )
    hands = [[list(h.counts) for h in position.hands]]
    aux = {
        str(key): (
            list(value) if isinstance(value, tuple) else value
        )
        for key, value in position.aux_state
    }
    payload = {
        "ruleset": support.ruleset_fingerprint,
        "side_to_move": position.side_to_move,
        "board": board,
        "hands": hands,
        "aux_state": aux,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
