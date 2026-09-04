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
SPATIAL_GRID_SIZE = 3
SPATIAL_CELL_COUNT = SPATIAL_GRID_SIZE * SPATIAL_GRID_SIZE
TACTICAL_INTERACTION_FEATURE_NAMES = (
    "attacked_by_type",
    "defended_by_type",
    "hanging_by_type",
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
    spatial_occupancy=None,
    localized_control=None,
    spatial_occupancy_weights=None,
    localized_control_weights=None,
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
    if spatial_occupancy is not None and spatial_occupancy_weights:
        for type_id, cells in spatial_occupancy.items():
            weights = spatial_occupancy_weights.get(type_id, ())
            value += sum(float(weight) * feature for weight, feature in zip(weights, cells))
    if localized_control is not None and localized_control_weights:
        value += sum(
            float(weight) * feature
            for weight, feature in zip(localized_control_weights, localized_control)
        )
    return value


def spatial_cell(index: int, board_size: int) -> int:
    """Map a row-major board square to a deterministic 3x3 cell."""
    if board_size <= 0 or not 0 <= index < board_size * board_size:
        raise ValueError("index must be inside a non-empty square board")
    rank, file = divmod(index, board_size)
    cell_rank = min(SPATIAL_GRID_SIZE - 1, rank * SPATIAL_GRID_SIZE // board_size)
    cell_file = min(SPATIAL_GRID_SIZE - 1, file * SPATIAL_GRID_SIZE // board_size)
    return cell_rank * SPATIAL_GRID_SIZE + cell_file


def spatial_occupancy_features(
    position: Position,
    type_ids: tuple[str, ...],
) -> dict[str, tuple[int, ...]]:
    """Return owner-specific occupancy per type and spatial cell.

    Owner-1 features are signed negative in the owner-0 value convention;
    they still have their own weight table, so asymmetric RuleSets retain an
    explicit owner axis rather than inheriting a mirrored evaluator.
    """
    features = {
        f"{owner}:{type_id}": [0] * SPATIAL_CELL_COUNT
        for owner in (0, 1) for type_id in type_ids
    }
    board_size = position.board_size()
    for index, piece in enumerate(position.board):
        if piece is None or f"{piece.owner}:{piece.current_type_id}" not in features:
            continue
        features[f"{piece.owner}:{piece.current_type_id}"][spatial_cell(index, board_size)] += (
            1 if piece.owner == 0 else -1
        )
    return {key: tuple(cells) for key, cells in features.items()}


def localized_control_features(position: Position, compiled) -> tuple[int, ...]:
    """Return zero-sum per-cell legal-control residuals.

    Each owner's cell count is residualized as ``9 * count - total`` before
    taking the owner-0 minus owner-1 difference.  This deliberately removes
    the global mobility direction already present in ``DYNAMIC_FEATURE_NAMES``.
    """
    from dataclasses import replace

    from ..core.actions import action_target_square
    from ..core.movegen import legal_actions_from_position
    from ..core.semantic_executor import semantic_engine_for

    board_size = position.board_size()
    counts = [[0] * SPATIAL_CELL_COUNT for _ in range(2)]
    engine = semantic_engine_for(compiled)
    for owner in (0, 1):
        view = replace(position, side_to_move=owner)
        actions = (
            engine.legal_actions(view)
            if engine is not None
            else legal_actions_from_position(view, compiled)
        )
        for action in actions:
            target = action.target if hasattr(action, "target") else action_target_square(action)
            target_index = target if isinstance(target, int) else target.rank * board_size + target.file
            counts[owner][spatial_cell(target_index, board_size)] += 1
    totals = [sum(row) for row in counts]
    return tuple(
        (SPATIAL_GRID_SIZE * SPATIAL_GRID_SIZE * counts[0][cell] - totals[0])
        - (SPATIAL_GRID_SIZE * SPATIAL_GRID_SIZE * counts[1][cell] - totals[1])
        for cell in range(SPATIAL_CELL_COUNT)
    )


def tactical_interaction_features(
    position: Position,
    compiled,
    type_ids: tuple[str, ...] | None = None,
) -> dict[str, int]:
    """Count semantic attack/defense relations per owner and current type.

    The extractor intentionally requires a compiled semantic attack engine;
    legacy movement atoms are not a safe substitute for RuleSets whose attack
    contract includes semantic guards.  Values are unsigned owner-specific
    counts so a later evaluator can learn asymmetric owner coefficients.
    """
    from ..core.semantic_executor import semantic_engine_for

    engine = semantic_engine_for(compiled)
    if engine is None:
        raise TypeError("tactical interaction features require compiled semantic rules")
    if type_ids is None:
        metadata = getattr(getattr(compiled, "support", None), "type_metadata", {})
        type_ids = tuple(sorted(metadata))
    type_ids = tuple(type_ids)
    expected = {
        f"{feature}:{owner}:{type_id}": 0
        for feature in TACTICAL_INTERACTION_FEATURE_NAMES
        for owner in (0, 1)
        for type_id in type_ids
    }
    allowed = set(type_ids)
    for square, piece in enumerate(position.board):
        if piece is None or piece.current_type_id not in allowed:
            continue
        owner = piece.owner
        type_id = piece.current_type_id
        attacked = engine.is_square_attacked(position, square, 1 - owner)
        defended = engine.is_square_attacked(position, square, owner)
        expected[f"attacked_by_type:{owner}:{type_id}"] += int(attacked)
        expected[f"defended_by_type:{owner}:{type_id}"] += int(defended)
        expected[f"hanging_by_type:{owner}:{type_id}"] += int(attacked and not defended)
    return expected


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
