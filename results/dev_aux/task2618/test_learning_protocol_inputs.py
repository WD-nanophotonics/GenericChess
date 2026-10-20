from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from results.dev_aux.task2618 import audit_learning_protocol_inputs as audit


class LearningProtocolInputAuditTests(unittest.TestCase):
    def test_seed_derivation_is_stable_and_fresh_against_recorded_plans(self):
        seeds = audit.derive_seeds()
        self.assertEqual(seeds, [1407393461, 285297431, 1428194790, 1534967704])
        self.assertEqual(len(set(seeds)), 4)
        recorded: set[int] = set()
        for _path, value in audit.seed_source_plans():
            recorded.update(audit.plan_seed_values(value))
        self.assertTrue(set(seeds).isdisjoint(recorded))

    def test_remaining_training_pool_excludes_cost_roots_and_eval(self):
        with tempfile.TemporaryDirectory(dir=audit.ROOT / ".local_agent") as temp:
            output = Path(temp) / "audit.json"
            with patch.object(audit, "OUT", output):
                result = audit.audit()
        self.assertEqual(result["status"], "PREPARATION_AUDIT_ONLY_NOT_REGISTERED")
        selection = result["selection"]
        self.assertEqual(selection["cost_only_training_root_indices_excluded"], list(range(32)))
        self.assertEqual(selection["training_root_indices_remaining"], [32, 512])
        self.assertEqual(selection["training_root_count_remaining"], 480)
        self.assertEqual(selection["training_roots_per_seed_if_four_seed_design"], 120)
        self.assertEqual(selection["evaluation_root_count"], 32)
        self.assertEqual(selection["exact_history_overlap_training_evaluation"], 0)
        self.assertFalse(result["search_or_outcome_access"])
        self.assertFalse(result["registration_or_launch_authorized"])

    def test_plan_seed_scanner_reads_seed_fields_only(self):
        value = {"seeds": [1, 2], "nested": {"seed": 3}, "not_a_seed": 4}
        self.assertEqual(audit.plan_seed_values(value), {1, 2, 3})


if __name__ == "__main__":
    unittest.main()
