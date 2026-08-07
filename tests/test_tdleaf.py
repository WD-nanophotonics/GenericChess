"""Learning Phase 1: TDLeaf(lambda) hand-computed correctness."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.tdleaf import TDLeafConfig, tdleaf_update
from generic_chess.learning.trajectory import TrainingPoint, TrainingTrajectory


def _checkpoint(value_scale=None):
    weights = [100.0, 300.0]
    ordered = sorted(weights)
    median = (ordered[0] + ordered[1]) / 2.0
    value_scale = value_scale if value_scale is not None else median * 4.0
    return LearnableMaterialCheckpoint(
        ruleset_fingerprint="fp",
        evaluation_profile_version="v1",
        generation=0,
        created_at="t",
        board_weights={"P": 100.0, "Q": 300.0},
        hand_weights={"P": 90.0, "Q": 270.0},
        value_scale=value_scale,
        w_max=10000.0,
    )


def _trajectory(type_ids, points, terminal, winner):
    return TrainingTrajectory(
        ruleset_fingerprint="fp",
        generation=0,
        game_seed=1,
        initial_position_key="init",
        actions=(),
        search_nodes=1,
        search_max_depth=1,
        terminal=terminal,
        winner=winner,
        type_ids=type_ids,
        points=tuple(points),
    )


def _point(ply, board, hand, value, completed=2):
    return TrainingPoint(
        ply=ply,
        root_position_key=f"root{ply}",
        action=None,
        exploration=False,
        pv=(),
        leaf_position_key=f"leaf{ply}",
        leaf_feature_board=board,
        leaf_feature_hand=hand,
        leaf_value=value,
        completed_depth=completed,
    )


def _tanh(v, scale):
    return math.tanh(v / scale)


def _hand_update(points, terminal_z, checkpoint, config, alpha, value_scale):
    """Reference implementation of the batch TDLeaf update."""
    type_ids = ("P", "Q")
    x: list[list[float]] = []
    values: list[float] = []
    for p in points:
        board = dict(zip(type_ids, p.leaf_feature_board))
        hand = dict(zip(type_ids, p.leaf_feature_hand))
        v = sum(checkpoint.board_weights[t] * board[t] + checkpoint.hand_weights[t] * hand[t] for t in type_ids)
        x.append(
            [float(board[t]) for t in type_ids]
            + [float(hand[t]) for t in type_ids]
        )
        values.append(math.tanh(v / value_scale))
    deltas = []
    for i in range(len(points)):
        if i + 1 < len(points):
            deltas.append(values[i + 1] - values[i])
        else:
            deltas.append(terminal_z - values[i])
    e = [0.0] * len(x[0])
    acc = [0.0] * len(x[0])
    for i in range(len(points)):
        grad_scale = (1.0 - values[i] ** 2) / value_scale
        for j in range(len(x[0])):
            e[j] = config.lambd * e[j] + grad_scale * x[i][j]
            acc[j] += alpha * deltas[i] * e[j]
    return acc, deltas, values


def _median_of(weights):
    ordered = sorted(abs(v) for v in weights.values())
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _normalize_pair(board_w, hand_w, checkpoint):
    """Mirror the pipeline's single-factor normalization."""
    median = _median_of(board_w)
    target = checkpoint.value_scale / 4.0
    if median <= 0:
        raise ValueError("median collapsed")
    factor = target / median
    clip = lambda w: max(-checkpoint.w_max, min(checkpoint.w_max, w * factor))
    return {k: clip(v) for k, v in board_w.items()}, {
        k: clip(v) for k, v in hand_w.items()
    }


@pytest.mark.parametrize("lambd", [0.0, 0.7, 1.0])
@pytest.mark.parametrize("terminal,winner,z", [
    ("checkmate", 0, 1.0),
    ("checkmate", 1, -1.0),
    ("stalemate", None, 0.0),
])
def test_hand_computed_update(lambd, terminal, winner, z):
    checkpoint = _checkpoint()
    config = TDLeafConfig(gamma=1.0, lambd=lambd, alpha=0.1)
    points = [
        _point(0, (1, 0), (0, 1), 0.0),
        _point(1, (0, 1), (1, 0), 0.0),
    ]
    trajectory = _trajectory(("P", "Q"), points, terminal, winner)
    result = tdleaf_update([trajectory], checkpoint, config)
    expected_acc, deltas, values = _hand_update(
        points, z, checkpoint, config, 0.1, checkpoint.value_scale
    )
    keys = ("P", "Q")
    board_keys = keys
    actual = []
    for t in board_keys:
        actual.append(result.board_weights[t] - checkpoint.board_weights[t])
    for t in keys:
        actual.append(result.hand_weights[t] - checkpoint.hand_weights[t])
    # The pipeline normalizes after the update, so mirror that in the
    # reference: expected weights = normalize(checkpoint + acc).
    board_w = {t: checkpoint.board_weights[t] + expected_acc[i] for i, t in enumerate(("P", "Q"))}
    hand_w = {t: checkpoint.hand_weights[t] + expected_acc[2 + i] for i, t in enumerate(("P", "Q"))}
    board_w, hand_w = _normalize_pair(board_w, hand_w, checkpoint)
    for i, t in enumerate(("P", "Q")):
        assert result.board_weights[t] == pytest.approx(board_w[t], abs=1e-8)
        assert result.hand_weights[t] == pytest.approx(hand_w[t], abs=1e-8)
    assert abs(result.mean_abs_td_error - sum(abs(d) for d in deltas) / len(deltas)) < 1e-9
    assert result.mean_td_error == pytest.approx(sum(deltas) / len(deltas), abs=1e-9)


def test_no_nan_and_normalization():
    checkpoint = _checkpoint()  # consistent: value_scale == median * 4
    config = TDLeafConfig(gamma=1.0, lambd=0.7, alpha=0.1)
    points = [_point(0, (2, 1), (0, 3), 0.0), _point(1, (1, 2), (1, 0), 0.0)]
    trajectory = _trajectory(("P", "Q"), points, "repetition", None)
    result = tdleaf_update([trajectory], checkpoint, config)
    for t in ("P", "Q"):
        assert math.isfinite(result.board_weights[t])
        assert math.isfinite(result.hand_weights[t])
    values = list(result.board_weights.values())
    ordered = sorted(abs(v) for v in values)
    med = (ordered[0] + ordered[1]) / 2.0
    assert abs(med - checkpoint.value_scale / 4.0) < 1e-6


def test_owner_zero_perspective_terminal_sign():
    # A loss for owner 0 must push weights in the opposite direction of a win.
    checkpoint = _checkpoint()
    config = TDLeafConfig(gamma=1.0, lambd=0.7, alpha=0.1)
    points = [_point(0, (1, 0), (0, 0), 0.0)]
    win = _trajectory(("P", "Q"), points, "checkmate", 0)
    loss = _trajectory(("P", "Q"), points, "checkmate", 1)
    r_win = tdleaf_update([win], checkpoint, config)
    r_loss = tdleaf_update([loss], checkpoint, config)
    assert math.copysign(1.0, r_win.board_weights["P"] - checkpoint.board_weights["P"]) == \
        -math.copysign(1.0, r_loss.board_weights["P"] - checkpoint.board_weights["P"])
