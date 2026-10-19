from math import tanh
from types import SimpleNamespace
import unittest

from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2593.episode import OutcomeGatedTDLeafEpisode


class LinearModel:
    scale = 1.0

    def __init__(self):
        self.weights = [0.0, 0.0]

    def gradient(self, phi):
        return tuple(phi)

    def apply(self, delta):
        self.weights = [w + d for w, d in zip(self.weights, delta)]


def receipt(value, phi, terminal=False, complete=True):
    return SimpleNamespace(value=value, pv_phi=phi, pv_terminal=terminal,
                           complete=complete)


def direct_reference(rows, outcome, eta, base_lambda):
    """Literal finite-sum specification, independent of candidate loop code."""
    predictions = [tanh(value) for value, _, _ in rows]
    grads = [((0.0, 0.0) if terminal else tuple(phi))
             for _, phi, terminal in rows]
    delta = [0.0, 0.0]
    losses = []
    for t, prediction in enumerate(predictions):
        if t + 1 < len(rows):
            target = predictions[t + 1]
            trace_lambda = 1.0 if rows[t + 1][2] else base_lambda
        else:
            target = outcome
            trace_lambda = base_lambda
        if target is None:
            break
        error = target - prediction
        losses.append(error * error / 2.0)
        for k in range(2):
            eligibility = sum((trace_lambda ** (t - j)) * grads[j][k]
                              for j in range(t + 1))
            delta[k] += error * eligibility
    return [eta * value for value in delta], sum(losses) / max(1, len(losses)), len(losses)


class ExactResidualMatrixTests(unittest.TestCase):
    def test_candidate_matches_literal_per_residual_matrix(self):
        rows = [(0.0, (1.0, 0.0), False),
                (0.2, (0.0, 2.0), True),
                (-0.4, (1.0, 1.0), False)]
        outcome = 0.7
        expected_delta, expected_loss, expected_n = direct_reference(
            rows, outcome, eta=0.05, base_lambda=0.95)
        model = LinearModel()
        learner = OutcomeGatedTDLeafEpisode(eta=0.05, lam=0.95)
        for value, phi, terminal in rows:
            learner.observe(model, receipt(value, phi, terminal))
        stats = learner.finish(model, outcome)
        for got, expected in zip(model.weights, expected_delta):
            self.assertAlmostEqual(got, expected, places=14)
        self.assertAlmostEqual(stats['loss'], expected_loss, places=14)
        self.assertEqual(stats['samples'], expected_n)

    def test_lambda_one_reduces_to_episode_tdleaf(self):
        rows = [(0.0, (1.0, 0.0), False),
                (0.2, (0.0, 2.0), True),
                (-0.4, (1.0, 1.0), False)]
        models = [LinearModel(), LinearModel()]
        learners = [OutcomeGatedTDLeafEpisode(eta=0.05, lam=1.0),
                    TDLeafEpisode(eta=0.05, lam=1.0)]
        for learner, model in zip(learners, models):
            for value, phi, terminal in rows:
                learner.observe(model, receipt(value, phi, terminal))
        for learner, model in zip(learners, models):
            learner.finish(model, 0.7)
        self.assertEqual(models[0].weights, models[1].weights)

    def test_episode_snapshot_rejects_intermediate_update(self):
        model = LinearModel()
        learner = OutcomeGatedTDLeafEpisode()
        learner.observe(model, receipt(0.0, (1.0, 0.0)))
        model.weights[0] += 0.01
        with self.assertRaisesRegex(ValueError, 'weights'):
            learner.finish(model, 1.0)


if __name__ == '__main__':
    unittest.main()