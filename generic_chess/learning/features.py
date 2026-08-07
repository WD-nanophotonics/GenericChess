"""Learnable material feature extractor (side-to-move independent)."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.position import Position


@dataclass(frozen=True, slots=True)
class MaterialFeatureVector:
    """Count differences per non-anchor type from a fixed reference player
    (``perspective`` at extraction time).  ``f(state, 1) == -f(state, 0)``.

    * ``board_counts``: per type, (#pieces of that current type owned by the
      reference player) - (owned by the other player), on the board.
    * ``hand_counts``: per type, (hand count of that base type for the
      reference player) - (for the other player).
    """

    type_ids: tuple[str, ...]
    board_counts: tuple[int, ...]
    hand_counts: tuple[int, ...]

    def __post_init__(self) -> None:
        if not (len(self.board_counts) == len(self.hand_counts) == len(self.type_ids)):
            raise ValueError("feature vector dimension mismatch")

    def array(self) -> list[float]:
        return [float(v) for v in self.board_counts + self.hand_counts]

    def negated(self) -> "MaterialFeatureVector":
        return MaterialFeatureVector(
            self.type_ids,
            tuple(-v for v in self.board_counts),
            tuple(-v for v in self.hand_counts),
        )


def non_anchor_type_ids(compiled) -> tuple[str, ...]:
    return tuple(
        sorted(
            pt.type_id
            for pt in compiled.piece_types
            if not pt.is_anchor
        )
    )


def material_features(
    position: Position,
    type_ids: tuple[str, ...],
    *,
    perspective: int = 0,
) -> MaterialFeatureVector:
    """Extract material count differences from the reference player's view.

    Anchors are excluded by construction (``type_ids`` must not contain them).
    """
    if perspective not in (0, 1):
        raise ValueError("perspective must be 0 or 1")
    index = {tid: i for i, tid in enumerate(type_ids)}
    board = [0] * len(type_ids)
    hand = [0] * len(type_ids)
    for piece in position.board:
        if piece is None or piece.current_type_id not in index:
            continue
        idx = index[piece.current_type_id]
        board[idx] += 1 if piece.owner == 0 else -1
    for owner in (0, 1):
        for tid, count in position.hands[owner].counts:
            if tid not in index:
                continue
            idx = index[tid]
            hand[idx] += count if owner == 0 else -count
    if perspective == 1:
        board = [-v for v in board]
        hand = [-v for v in hand]
    return MaterialFeatureVector(
        type_ids, tuple(board), tuple(hand)
    )


def linear_value(
    features: MaterialFeatureVector,
    board_weights,
    hand_weights,
) -> float:
    """V = sum(board_weights[t] * board_counts[t]) +
           sum(hand_weights[t] * hand_counts[t])."""
    return sum(
        float(board_weights[tid]) * bc
        + float(hand_weights[tid]) * hc
        for tid, bc, hc in zip(
            features.type_ids, features.board_counts, features.hand_counts
        )
    )
