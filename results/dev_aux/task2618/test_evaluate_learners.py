from __future__ import annotations

import unittest

from results.dev_aux.task2618.evaluate_learners import (
    finite_reward_bounds,
    learner_reward,
    verify_training_result,
)


class EvaluateLearnerTests(unittest.TestCase):
    def test_terminal_rewards_are_color_oriented_and_unknown_is_censored(self):
        self.assertEqual(learner_reward(1, 0), 1)
        self.assertEqual(learner_reward(1, 1), -1)
        self.assertEqual(learner_reward(0, 1), 0)
        self.assertIsNone(learner_reward(None, 0))
        self.assertEqual(finite_reward_bounds(None, 0), (-1, 1))
        self.assertEqual(finite_reward_bounds(-1, 1), (1, 1))

    def test_evaluation_requires_all_full_budget_training_arms(self):
        plan = {"seeds": [7], "methods": ["TreeStrap", "TDLeaf", "WDL"],
                "nodes_per_seed_method_arm": 100}
        arms = [
            {"seed_index": 0, "seed": 7, "method": method,
             "status": "NODE_BUDGET_REACHED", "nodes_total": 100,
             "final_weights": [1, 1, 1, 1, 1]}
            for method in plan["methods"]
        ]
        result = {"status": "COMPLETE_TRAINING", "eligible_for_evaluation": True,
                  "plan_sha256": "plan-sha", "arms": arms}
        self.assertEqual(len(verify_training_result(plan, result, "plan-sha")), 3)
        result["arms"] = arms[:-1]
        with self.assertRaises(ValueError):
            verify_training_result(plan, result, "plan-sha")


if __name__ == "__main__":
    unittest.main()
