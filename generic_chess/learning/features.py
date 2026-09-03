"""Learnable generic feature extractors (side-to-move independent)."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.attacks import is_in_check, is_square_attacked, pseudo_attacks
from ..core.coordinates import Square, square_to_index
from ..core.movement import LeapAtom, RayAtom
from ..core.position import Position

DYNAMIC_FEATURE_NAMES = (
    "mobility",
    "promotion_potential",
    "anchor_safety",
)


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


@dataclass(frozen=True, slots=True)
class DynamicFeatureVector:
    """Small generic non-material signal vector."""

    mobility: int = 0
    promotion_potential: int = 0
    anchor_safety: int = 0

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.mobility, self.promotion_potential, self.anchor_safety)

    def as_dict(self) -> dict[str, int]:
        return dict(zip(DYNAMIC_FEATURE_NAMES, self.as_tuple()))

    def negated(self) -> "DynamicFeatureVector":
        return DynamicFeatureVector(*( -value for value in self.as_tuple()))


def non_anchor_type_ids(compiled) -> tuple[str, ...]:
    if not hasattr(compiled, "piece_types"):
        metadata = getattr(getattr(compiled, "support", None), "type_metadata", {})
        return tuple(sorted(
            type_id for type_id, item in metadata.items()
            if not getattr(item, "is_anchor", False)
        ))
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
    dynamic: DynamicFeatureVector | tuple[int, ...] | None = None,
    dynamic_weights=None,
) -> float:
    """V = sum(board_weights[t] * board_counts[t]) +
           sum(hand_weights[t] * hand_counts[t])."""
    value = sum(
        float(board_weights[tid]) * bc
        + float(hand_weights[tid]) * hc
        for tid, bc, hc in zip(
            features.type_ids, features.board_counts, features.hand_counts
        )
    )
    if dynamic is not None and dynamic_weights:
        values = dynamic.as_tuple() if isinstance(dynamic, DynamicFeatureVector) else tuple(dynamic)
        value += sum(
            float(dynamic_weights.get(name, 0.0)) * feature
            for name, feature in zip(DYNAMIC_FEATURE_NAMES, values)
        )
    return value


def dynamic_features(position: Position, compiled) -> DynamicFeatureVector:
    """Extract dynamic features for a legacy compiled RuleSet.

    Semantic positions use the Native extractor in ``generic_chess.native``
    so the learning path and Native leaf evaluator share one definition.
    """
    from ..rules.ir import CompiledSemanticRuleset

    if isinstance(compiled, CompiledSemanticRuleset):
        raise TypeError("semantic dynamic features require the Native position helper")
    mobility = len(pseudo_attacks(position, 0, compiled)) - len(
        pseudo_attacks(position, 1, compiled)
    )
    promotion = 0
    n = compiled.board_size
    for idx, piece in enumerate(position.board):
        if piece is None or piece.promoted:
            continue
        piece_type = compiled.types_by_id[piece.base_type_id]
        if not piece_type.is_promotable:
            continue
        zone = {
            square
            for square in range(n * n)
            if not compiled.empty_forward_mobility[piece.base_type_id][piece.owner][square]
        }
        forward = compiled.empty_forward_mobility[piece.base_type_id][piece.owner][idx]
        potential = 2 if idx in zone else (1 if any(
            square_to_index(target, n) in zone for target in forward
        ) else 0)
        promotion += potential if piece.owner == 0 else -potential
    anchor_safety = _anchor_safety(position, compiled, 0) - _anchor_safety(
        position, compiled, 1
    )
    return DynamicFeatureVector(mobility, promotion, anchor_safety)


def _anchor_safety(position: Position, compiled, owner: int) -> int:
    """Anchor escape count plus the existing generic check-pressure term."""
    n = compiled.board_size
    anchor_idx = next(
        (
            idx for idx, piece in enumerate(position.board)
            if piece is not None and piece.owner == owner
            and compiled.types_by_id[piece.current_type_id].is_anchor
        ),
        None,
    )
    escapes = 0
    if anchor_idx is not None:
        piece = position.board[anchor_idx]
        square = Square(anchor_idx % n, anchor_idx // n)
        for atom in compiled.types_by_id[piece.current_type_id].movement_atoms:
            if isinstance(atom, LeapAtom) and max(abs(atom.offset[0]), abs(atom.offset[1])) <= 1:
                targets = (Square(square.file + atom.offset[0], square.rank + atom.offset[1]),)
            elif isinstance(atom, RayAtom) and atom.max_steps == 1:
                targets = (Square(square.file + atom.direction[0], square.rank + atom.direction[1]),)
            else:
                targets = ()
            for target in targets:
                if not (0 <= target.file < n and 0 <= target.rank < n):
                    continue
                target_idx = square_to_index(target, n)
                if position.board[target_idx] is None and not is_square_attacked(
                    position, target, 1 - owner, compiled
                ):
                    escapes += 1
    if is_in_check(position, owner, compiled):
        escapes -= 10
    return escapes
