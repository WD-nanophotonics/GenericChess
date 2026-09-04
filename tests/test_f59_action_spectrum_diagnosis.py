"""Focused contracts for the F59 offline policy-surface diagnostic."""

import numpy as np

from scripts.f59_action_spectrum_diagnosis import (
    SpectrumRow,
    _fit_model,
    _metrics,
    _root_player_q,
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
