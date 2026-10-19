import unittest
from results.dev_aux.task2606.train import METHODS, learner_controls, observes

class FixedOpponentScheduleTests(unittest.TestCase):
    def test_both_learners_control_only_their_assigned_color(self):
        self.assertEqual(set(METHODS), {"TD95", "LocalLambda"})
        for method in METHODS:
            for color in (0, 1):
                self.assertTrue(learner_controls(method, color, color))
                self.assertFalse(learner_controls(method, 1 - color, color))

    def test_observation_schedule_matches_controlled_side_and_requires_complete_search(self):
        for method in METHODS:
            self.assertTrue(observes(method, 0, 0, True))
            self.assertTrue(observes(method, 1, 1, True))
            self.assertFalse(observes(method, 1, 0, True))
            self.assertFalse(observes(method, 0, 0, False))

    def test_unknown_methods_are_rejected(self):
        with self.assertRaises(ValueError):
            learner_controls("SelfEvery", 0, 0)
        self.assertFalse(observes("SelfEvery", 0, 0, True))

if __name__ == "__main__":
    unittest.main()