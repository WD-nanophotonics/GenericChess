from __future__ import annotations

import json
import unittest

from results.dev_aux.task2618.reselect_training_roots import build_panel


class ReselectTrainingRootsTests(unittest.TestCase):
    def setUp(self):
        self.training = {
            "roots": [
                {"family": family, "record": {"moves": [str(family)]}}
                for family in range(100, 221)
            ]
        }
        self.evaluation = {"roots": [{"family": 999, "record": {"moves": ["eval"]}}]}
        self.audit = {
            "selection": {
                "training_root_indices_remaining": [0, 121],
                "training_root_count_remaining": 121,
            }
        }
        self.source_hashes = {"fixture": "a" * 64}

    def test_fixed_seed_excludes_exposed_roots_and_ignores_outcome_values(self):
        first = b'\n'.join([
            json.dumps({"family": 102, "unstarted": False, "outcome_white_relative": 1}).encode(),
            json.dumps({"family": 104, "unstarted": True, "outcome_white_relative": -1}).encode(),
        ])
        second = b'\n'.join([
            json.dumps({"family": 102, "unstarted": False, "outcome_white_relative": -1}).encode(),
            json.dumps({"family": 104, "unstarted": True, "outcome_white_relative": 1}).encode(),
        ])
        left = build_panel(self.training, self.evaluation, self.audit, first, self.source_hashes)
        right = build_panel(self.training, self.evaluation, self.audit, second, self.source_hashes)
        left_families = [row["family"] for row in left["roots"]]
        right_families = [row["family"] for row in right["roots"]]
        self.assertEqual(left_families, right_families)
        self.assertEqual(len(left_families), 120)
        self.assertNotIn(102, left_families)
        self.assertIn(104, left_families)
        self.assertEqual(left["exposed_family_ids_excluded"], [102])
        self.assertFalse(left["outcome_fields_used_for_selection"])
        self.assertEqual(left["training_evaluation_exact_record_overlap"], 0)

    def test_insufficient_unexposed_roots_fails_closed(self):
        games = b'\n'.join(
            json.dumps({"family": family, "unstarted": False}).encode()
            for family in range(100, 102)
        )
        with self.assertRaisesRegex(ValueError, "not enough unexposed"):
            build_panel(self.training, self.evaluation, self.audit, games, self.source_hashes)


if __name__ == "__main__":
    unittest.main()
