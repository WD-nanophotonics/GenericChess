"""Frozen-contract test: UNKNOWN censors only the terminal residual."""
import math
import pytest

from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2492.learning import Model, Receipt


def complete_receipt(value, phi):
    return Receipt(None, value, phi, False, (), 1, True, 0, 0.0, "contract-test")


def test_unknown_terminal_censors_last_residual_but_keeps_prior_bootstrap():
    model = Model([1.0, 1.0], scale=10.0)
    learner = TDLeafEpisode(eta=0.1, lam=0.95)
    first_phi = (0.0, 1.0)
    second_phi = (0.0, 2.0)
    first_prediction = model.prediction(first_phi)
    first_gradient = model.gradient(first_phi)[1]
    second_target = math.tanh(0.2)

    learner.observe(model, complete_receipt(1.0, first_phi))
    learner.observe(model, complete_receipt(2.0, second_phi))
    stats = learner.finish(model, None)

    residual = second_target - first_prediction
    expected_delta = 0.1 * first_gradient * residual
    assert stats["censored"] is True
    assert stats["samples"] == 1
    assert stats["loss"] == pytest.approx(residual * residual / 2.0)
    assert model.weights[1] == pytest.approx(1.0 + expected_delta)
    assert model.weights[0] == 1.0


def test_incomplete_receipt_is_ignored_and_unknown_end_adds_no_terminal_residual():
    model = Model([1.0, 1.0], scale=10.0)
    learner = TDLeafEpisode(eta=0.1, lam=0.95)
    learner.observe(model, complete_receipt(1.0, (0.0, 1.0)))
    partial = Receipt(None, None, None, False, (), 1, False, 0, 0.0, "budget")
    before = list(model.weights)

    stats = learner.observe(model, partial)
    finish = learner.finish(model, None)

    assert stats["samples"] == 0
    assert finish["samples"] == 0
    assert finish["censored"] is True
    assert model.weights == before
