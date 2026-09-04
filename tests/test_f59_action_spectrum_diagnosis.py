"""Focused contracts for the F59 offline policy-surface diagnostic."""

import numpy as np

from scripts.f59_action_spectrum_diagnosis import (
    SpectrumRow,
    _fit_model,
    _is_mate_band_native,
    _metrics,
    _ordinary_usable,
    _predict_total_q,
    _root_player_q,
    _soft_policy_grad_prediction,
    _soft_policy_loss,
    _softmax,
)
from scripts.f59_overlap_sensitivity import overlap_matrix, unique_indices


def _rows(values):
    return [
        SpectrumRow({"index": index}, str(index), np.asarray([float(index), 1.0]), 0.0, 0.0, float(value), float(value))
        for index, value in enumerate(values)
    ]


def test_softmax_is_stable_and_normalized():
    probabilities = _softmax(np.asarray([-1_000_000.0, 0.0, 1_000_000.0]))
    assert np.isclose(np.sum(probabilities), 1.0)
    assert probabilities[-1] > probabilities[0]


def test_metrics_uses_teacher_regret_and_ranking_as_primary_signals():
    rows = [_rows([3.0, 2.0, 1.0])]
    result = _metrics(rows, [np.asarray([3.0, 2.0, 1.0])])
    assert result["top1_agreement"] == 1.0
    assert result["teacher_regret_mean"] == 0.0
    assert result["ranking_accuracy"] == 1.0
    assert result["mse_secondary"] == 0.0


def test_child_value_is_negated_for_both_root_perspectives():
    assert _root_player_q(7.5, 0) == -7.5
    assert _root_player_q(7.5, 1) == -7.5


def test_pairwise_objective_ranks_total_q_not_residual_only():
    features = np.asarray([[0.0], [1.0]])
    base = np.asarray([10.0, 0.0])
    targets = np.asarray([0.0, 10.0])
    predict = _fit_model(features, base, targets, [np.arange(2)], "PAIRWISE_RANKING", 59011)
    values = base + predict(features)
    assert values[1] > values[0]


def test_holdout_total_q_prediction_preserves_each_base_q():
    rows = [
        SpectrumRow({"index": 0}, "0", np.asarray([0.0]), 10.0, 0.0, 0.0, 0.0),
        SpectrumRow({"index": 1}, "1", np.asarray([1.0]), 0.0, 0.0, 0.0, 0.0),
    ]
    zero_residual = lambda features: np.zeros(len(features))
    total = _predict_total_q(rows, zero_residual)
    assert np.array_equal(total, np.asarray([10.0, 0.0]))

    nonconstant_residual = lambda features: np.asarray([1.0, 20.0])
    assert np.array_equal(_predict_total_q(rows, nonconstant_residual), np.asarray([11.0, 20.0]))


def test_soft_policy_gradient_matches_finite_difference():
    teacher = np.asarray([120.0, 10.0, -40.0])
    base = np.asarray([30.0, 0.0, -5.0])
    prediction = np.asarray([0.2, -0.1, 0.4])
    target_scale = 37.0
    analytic = _soft_policy_grad_prediction(teacher, base, prediction, target_scale)
    epsilon = 1e-5
    numeric = []
    for index in range(len(prediction)):
        plus = prediction.copy()
        minus = prediction.copy()
        plus[index] += epsilon
        minus[index] -= epsilon
        numeric.append((_soft_policy_loss(teacher, base, plus, target_scale)
                        - _soft_policy_loss(teacher, base, minus, target_scale)) / (2 * epsilon))
    assert np.allclose(analytic, numeric, rtol=1e-5, atol=1e-8)


def test_mate_band_roots_are_not_ordinary_usable():
    assert _is_mate_band_native(90_000_001)
    assert not _is_mate_band_native(90_000_000)
    assert _ordinary_usable({"root_80k_mate_band": False, "retained_q20_any_mate_band": False})
    assert not _ordinary_usable({"root_80k_mate_band": True, "retained_q20_any_mate_band": False})
    assert not _ordinary_usable({"root_80k_mate_band": False, "retained_q20_any_mate_band": True})


def test_fixed_architecture_objectives_return_finite_predictions():
    features = np.asarray([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    base = np.zeros(4)
    targets = np.asarray([0.0, 1.0, 2.0, 3.0])
    groups = [np.arange(4)]
    for objective in ("POINTWISE_Q", "PAIRWISE_RANKING", "SOFT_POLICY_DISTILLATION"):
        predict = _fit_model(features, base, targets, groups, objective, 59011)
        assert np.all(np.isfinite(predict(features)))


def test_overlap_and_unique_subsets_preserve_frozen_membership():
    distributions = {
        "D0_RANDOM_REACHABLE": {"roots_metadata": [{"position_key": "a"}, {"position_key": "b"}]},
        "D1_V2_SELFPLAY": {"roots_metadata": [{"position_key": "b"}, {"position_key": "c"}]},
        "D2_V2_PV_CORRIDOR": {"roots_metadata": [{"position_key": "c"}, {"position_key": "d"}]},
    }
    matrix = overlap_matrix(distributions)
    assert matrix["D1_V2_SELFPLAY"]["D2_V2_PV_CORRIDOR"] == 1
    assert unique_indices(distributions, "D1_V2_SELFPLAY") == []
    assert unique_indices(distributions, "D2_V2_PV_CORRIDOR") == [1]
    assert [row["position_key"] for row in distributions["D1_V2_SELFPLAY"]["roots_metadata"]] == ["b", "c"]
