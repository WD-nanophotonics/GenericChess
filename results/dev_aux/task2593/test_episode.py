from math import tanh
from types import SimpleNamespace
import unittest

from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2593.episode import OutcomeGatedTDLeafEpisode


class Model:
    scale = 10.0

    def __init__(self):
        self.weights = [0.0, 0.0]

    def gradient(self, phi):
        return tuple(phi)

    def apply(self, delta):
        self.weights = [w + d for w, d in zip(self.weights, delta)]


def receipt(value, phi, terminal=False):
    return SimpleNamespace(complete=True, value=value, pv_phi=phi,
                           pv_terminal=terminal)


def train(cls, rows, outcome):
    model = Model()
    learner = cls(eta=0.05, lam=0.95)
    for row in rows:
        learner.observe(model, row)
    stats = learner.finish(model, outcome)
    return model.weights, stats


class OutcomeGatedTests(unittest.TestCase):
  def test_no_terminal_target_matches_existing_tdleaf(self):
    rows = [receipt(0.0, (1.0, 0.0)), receipt(2.0, (0.0, 1.0))]
    self.assertEqual(train(OutcomeGatedTDLeafEpisode, rows, -1.0), train(
        TDLeafEpisode, rows, -1.0))


  def test_terminal_target_changes_only_its_residual_trace(self):
    rows = [receipt(0.0, (1.0, 0.0)), receipt(1.0, (0.0, 1.0)),
            receipt(2.0, (0.0, 0.0), terminal=True)]
    gated_weights, gated_stats = train(OutcomeGatedTDLeafEpisode, rows, -1.0)
    base_weights, _ = train(TDLeafEpisode, rows, -1.0)
    terminal_target_error = tanh(0.2) - tanh(0.1)
    expected_change = 0.05 * terminal_target_error * (1.0 - 0.95)
    self.assertAlmostEqual(gated_weights[0] - base_weights[0], expected_change,
                           places=12)
    self.assertEqual(gated_weights[1], base_weights[1])
    self.assertEqual(gated_stats["samples"], 3)


  def test_unknown_still_censors_final_outcome_residual(self):
    rows = [receipt(0.0, (1.0, 0.0)), receipt(2.0, (0.0, 1.0))]
    gated_weights, gated_stats = train(OutcomeGatedTDLeafEpisode, rows, None)
    base_weights, base_stats = train(TDLeafEpisode, rows, None)
    self.assertTrue(gated_stats["censored"])
    self.assertEqual(gated_stats["samples"], base_stats["samples"])
    self.assertEqual(gated_stats["samples"], 1)
    for actual, expected in zip(gated_weights, base_weights):
      self.assertAlmostEqual(actual, expected, places=12)


  def test_incomplete_search_is_not_observed(self):
    model = Model()
    learner = OutcomeGatedTDLeafEpisode()
    skipped = SimpleNamespace(complete=False)
    self.assertEqual(learner.observe(model, skipped)["samples"], 0)
    stats = learner.finish(model, None)
    self.assertEqual(stats["observed_searches"], 0)
    self.assertEqual(stats["samples"], 0)
    self.assertEqual(model.weights, [0.0, 0.0])


if __name__ == "__main__":
  unittest.main()
