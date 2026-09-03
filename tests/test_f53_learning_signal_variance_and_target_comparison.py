import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from f53_learning_signal_variance_and_target_comparison import (  # noqa: E402
    DIAGNOSTIC_FRACTION,
    _cosine,
    _normalized_distillation_target,
    _sign_consistency,
    _zero_like,
)


def _direction(board, hand, dynamic):
    return {"board": board, "hand": hand, "dynamic": dynamic}


def test_f53_full_vector_cosine_is_magnitude_neutral():
    left = _direction({"P": 1.0}, {"P": 2.0}, {"mobility": -3.0})
    right = _direction({"P": 10.0}, {"P": 20.0}, {"mobility": -30.0})
    assert abs(_cosine(left, right) - 1.0) < 1e-12


def test_f53_sign_consistency_reports_agreement_and_conflict():
    a = _direction({"P": 1.0}, {"P": -1.0}, {"mobility": 0.0})
    b = _direction({"P": 2.0}, {"P": -2.0}, {"mobility": 0.0})
    c = _direction({"P": -1.0}, {"P": 1.0}, {"mobility": 0.0})
    same = _sign_consistency([a, b])
    mixed = _sign_consistency([a, c])
    assert same["full"] == 1.0
    assert mixed["full"] == 0.5
    assert DIAGNOSTIC_FRACTION == 0.0005


def test_f53_zero_like_preserves_all_three_feature_blocks():
    class Checkpoint:
        board_weights = {"P": 1.0}
        hand_weights = {"P": 2.0}
        dynamic_weights = {"mobility": 3.0}

    assert _zero_like(Checkpoint()) == {
        "board": {"P": 0.0},
        "hand": {"P": 0.0},
        "dynamic": {"mobility": 0.0},
    }


def test_distillation_target_uses_semantic_fixed_point_scale_and_owner_zero_perspective():
    class Checkpoint:
        semantic_native_scale = 256
        value_scale = 4.0

    owner_zero = _normalized_distillation_target(256, 0, Checkpoint())
    owner_one = _normalized_distillation_target(256, 1, Checkpoint())
    assert owner_zero == pytest.approx(math.tanh(1.0 / 4.0))
    assert owner_one == pytest.approx(-owner_zero)
