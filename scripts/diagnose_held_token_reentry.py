"""Zero-game extraction of legal re-entry successor states after a capture.

This diagnostic does not assign material value. It compares one position
before and after a capture, matches opponent board-token removal to a hand
count increase for the capturing owner, and asks Core for legal drop
successors. Returned records pair destination indices with canonical position
identities, so equivalent descriptions reaching the same state collapse.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace

from generic_chess.core.actions import action_is_drop
from generic_chess.core.coordinates import square_to_index
from generic_chess.core.identity import position_identity_key
from generic_chess.core.position import GameState, HistoryRecord, Position
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.core.transition import legal_successors


def reentry_successor_state_keys(
    before: Position,
    after_capture: Position,
    compiled,
    capturing_owner: int,
) -> dict[str, frozenset[tuple[int, str]]]:
    """Return per-type canonical successor-state sets for transferred tokens.

    A type is included only when an opposing on-board base token disappeared
    and the capturing owner's hand count for that type increased. This
    identifies transfer-to-hand rather than board removal alone. Hands do not
    preserve individual token identity, so the observable identity is the
    captured token's base type and owner.
    """
    if capturing_owner not in (0, 1):
        raise ValueError("capturing_owner must be 0 or 1")
    if (
        before.ruleset_fingerprint != compiled.ruleset_fingerprint
        or after_capture.ruleset_fingerprint != compiled.ruleset_fingerprint
    ):
        raise ValueError("positions and compiled ruleset must have matching fingerprints")

    before_board = Counter(
        (piece.owner, piece.base_type_id) for piece in before.board if piece is not None
    )
    after_board = Counter(
        (piece.owner, piece.base_type_id) for piece in after_capture.board if piece is not None
    )
    removed_opponent_types = {
        type_id
        for (owner, type_id), count in (before_board - after_board).items()
        if owner != capturing_owner and count > 0
    }
    gained_types = {
        type_id
        for type_id, count in after_capture.hands[capturing_owner].items()
        if count > before.hands[capturing_owner].count(type_id)
    }
    transferred_types = sorted(removed_opponent_types & gained_types)
    if not transferred_types:
        return {}

    # This is a static continuation probe: preserve the exact post-capture
    # board/hands/auxiliary state, set the capturing owner to move, and ask
    # Core's legal-successor authority for the possible re-entry states.
    probe_position = replace(after_capture, side_to_move=capturing_owner)
    key = str(position_identity_key(probe_position, compiled))
    probe_state = GameState(
        position=probe_position,
        ply_count=0,
        repetition_counts=((key, 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
        history=(HistoryRecord(key, -1, "", False),),
    )
    successors = legal_successors(probe_state, compiled)
    result: dict[str, frozenset[tuple[int, str]]] = {}
    for type_id in transferred_types:
        result[type_id] = frozenset(
            (
                square_to_index(action.to_square, compiled.board_size),
                str(position_identity_key(child.position, compiled)),
            )
            for action, child in successors
            if action_is_drop(action) and action.base_type_id == type_id
        )
    return result
