"""TDLeaf(lambda) trainer for the learnable material evaluator."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .features import DYNAMIC_FEATURE_NAMES, linear_value
from .material import LearnableMaterialCheckpoint, LearningNumericalError
from .trajectory import TrainingTrajectory, TrainingPoint


@dataclass(frozen=True, slots=True)
class TDLeafConfig:
    gamma: float = 1.0
    lambd: float = 0.7
    alpha: float | None = None  # default = 0.01 * initial weight scale
    value_scale: float | None = None


@dataclass(frozen=True, slots=True)
class TDLeafUpdateResult:
    board_weights: dict[str, float]
    hand_weights: dict[str, float]
    mean_td_error: float
    mean_abs_td_error: float
    max_abs_td_error: float
    weight_l2_delta: float
    weight_max_delta: float
    normalization_factor: float
    positions_seen: int
    dynamic_weights: dict[str, float] = field(default_factory=dict)
    spatial_occupancy_weights: dict[str, tuple[float, ...]] = field(default_factory=dict)
    localized_control_weights: tuple[float, ...] = ()


def _normalized_value(
    features,
    board_weights,
    hand_weights,
    value_scale: float,
    dynamic=None,
    dynamic_weights=None,
) -> float:
    v = linear_value(
        features, board_weights, hand_weights, dynamic, dynamic_weights
    )
    return math.tanh(v / value_scale) if value_scale > 0 else 0.0


def tdleaf_update(
    trajectories: list[TrainingTrajectory],
    checkpoint: LearnableMaterialCheckpoint,
    config: TDLeafConfig,
) -> TDLeafUpdateResult:
    """Batch episode-after-the-fact TDLeaf(lambda) update.

    All leaf values for every episode are computed with the frozen
    ``checkpoint`` weights first; the eligibility-traced updates are then
    accumulated and applied once.
    """
    value_scale = config.value_scale or checkpoint.value_scale
    alpha = config.alpha
    if alpha is None:
        median = (
            checkpoint.reference_median
            if checkpoint.reference_median > 0
            else checkpoint.value_scale / 4.0
        )
        alpha = 0.01 * max(median, 1.0)
    if not (0.0 < alpha < 1e6):
        raise ValueError(f"unreasonable learning rate {alpha}")
    if not (0.0 <= config.lambd <= 1.0):
        raise ValueError(f"lambda must be in [0, 1], got {config.lambd}")

    board_delta: dict[str, float] = {}
    hand_delta: dict[str, float] = {}
    dynamic_delta: dict[str, float] = {}
    td_errors: list[float] = []
    positions_seen = 0
    for trajectory in trajectories:
        points = trajectory.points
        if not points:
            continue
        # Frozen evaluator: precompute all leaf values.
        values = [
            _normalized_value(
                trajectory.leaf_features_at(p),
                checkpoint.board_weights,
                checkpoint.hand_weights,
                value_scale,
                trajectory.dynamic_features_at(p),
                checkpoint.dynamic_weights,
            )
            for p in points
        ]
        terminal = trajectory.terminal_z
        eligibility_board: dict[str, float] = {}
        eligibility_hand: dict[str, float] = {}
        eligibility_dynamic: dict[str, float] = {}
        for t, point in enumerate(points):
            positions_seen += 1
            u_t = values[t]
            u_next = terminal if t == len(points) - 1 else values[t + 1]
            delta = u_next - u_t
            td_errors.append(delta)
            grad_scale = (1.0 - u_t * u_t) / value_scale
            for tid, bc in zip(trajectory.type_ids, point.leaf_feature_board):
                eligibility_board[tid] = (
                    config.lambd * eligibility_board.get(tid, 0.0)
                    + grad_scale * bc
                )
            for tid, hc in zip(trajectory.type_ids, point.leaf_feature_hand):
                eligibility_hand[tid] = (
                    config.lambd * eligibility_hand.get(tid, 0.0)
                    + grad_scale * hc
                )
            for name, feature in zip(
                DYNAMIC_FEATURE_NAMES, trajectory.dynamic_features_at(point).as_tuple()
            ):
                eligibility_dynamic[name] = (
                    config.lambd * eligibility_dynamic.get(name, 0.0)
                    + grad_scale * feature
                )
            for tid in trajectory.type_ids:
                board_delta[tid] = board_delta.get(tid, 0.0) + alpha * delta * eligibility_board.get(tid, 0.0)
                hand_delta[tid] = hand_delta.get(tid, 0.0) + alpha * delta * eligibility_hand.get(tid, 0.0)
            for name in DYNAMIC_FEATURE_NAMES:
                dynamic_delta[name] = dynamic_delta.get(name, 0.0) + alpha * delta * eligibility_dynamic.get(name, 0.0)

    board = {tid: float(checkpoint.board_weights.get(tid, 0.0)) for tid in checkpoint.board_weights}
    hand = {tid: float(checkpoint.hand_weights.get(tid, 0.0)) for tid in checkpoint.hand_weights}
    dynamic = {
        name: float(checkpoint.dynamic_weights.get(name, 0.0))
        for name in set(checkpoint.dynamic_weights) | set(dynamic_delta)
    }
    for tid, d in board_delta.items():
        board[tid] = board.get(tid, 0.0) + d
    for tid, d in hand_delta.items():
        hand[tid] = hand.get(tid, 0.0) + d
    for name, d in dynamic_delta.items():
        dynamic[name] = dynamic.get(name, 0.0) + d

    candidate = LearnableMaterialCheckpoint(
        ruleset_fingerprint=checkpoint.ruleset_fingerprint,
        evaluation_profile_version=checkpoint.evaluation_profile_version,
        generation=checkpoint.generation,
        parent_checkpoint_id=checkpoint.parent_checkpoint_id,
        created_at=checkpoint.created_at,
        training_config_hash=checkpoint.training_config_hash,
        board_weights=board,
        hand_weights=hand,
        dynamic_weights=dynamic,
        spatial_occupancy_weights=checkpoint.spatial_occupancy_weights,
        localized_control_weights=checkpoint.localized_control_weights,
        material_scale=checkpoint.material_scale,
        value_scale=value_scale,
        reference_median=checkpoint.reference_median,
        w_max=checkpoint.w_max,
        training_seed=checkpoint.training_seed,
    )
    candidate.ensure_within_limits()
    normalization_factor = candidate.normalize_and_clip()
    candidate.ensure_within_limits()

    l2 = math.sqrt(
        sum(
            (candidate.board_weights.get(t, 0.0) - checkpoint.board_weights.get(t, 0.0)) ** 2
            + (candidate.hand_weights.get(t, 0.0) - checkpoint.hand_weights.get(t, 0.0)) ** 2
            for t in checkpoint.board_weights
        )
        + sum(
            (candidate.dynamic_weights.get(name, 0.0) - checkpoint.dynamic_weights.get(name, 0.0)) ** 2
            for name in set(candidate.dynamic_weights) | set(checkpoint.dynamic_weights)
        )
    )
    max_delta = max(
        [abs(candidate.board_weights.get(t, 0.0) - checkpoint.board_weights.get(t, 0.0)) for t in checkpoint.board_weights]
        + [abs(candidate.hand_weights.get(t, 0.0) - checkpoint.hand_weights.get(t, 0.0)) for t in checkpoint.hand_weights]
        + [0.0]
        + [abs(candidate.dynamic_weights.get(name, 0.0) - checkpoint.dynamic_weights.get(name, 0.0))
           for name in set(candidate.dynamic_weights) | set(checkpoint.dynamic_weights)]
    )
    if any(not math.isfinite(v) for v in td_errors + list(board.values()) + list(hand.values()) + list(dynamic.values())):
        raise LearningNumericalError("TDLeaf update produced non-finite values")
    mean = sum(td_errors) / len(td_errors) if td_errors else 0.0
    mean_abs = sum(abs(e) for e in td_errors) / len(td_errors) if td_errors else 0.0
    return TDLeafUpdateResult(
        board_weights=candidate.board_weights,
        hand_weights=candidate.hand_weights,
        mean_td_error=mean,
        mean_abs_td_error=mean_abs,
        max_abs_td_error=max((abs(e) for e in td_errors), default=0.0),
        weight_l2_delta=l2,
        weight_max_delta=max_delta,
        normalization_factor=normalization_factor,
        positions_seen=positions_seen,
        dynamic_weights=candidate.dynamic_weights,
        spatial_occupancy_weights=candidate.spatial_occupancy_weights,
        localized_control_weights=candidate.localized_control_weights,
    )
