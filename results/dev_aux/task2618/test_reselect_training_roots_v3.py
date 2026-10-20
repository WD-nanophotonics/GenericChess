from __future__ import annotations

import unittest

from results.dev_aux.task2618.reselect_training_roots_v3 import build_panel


class ReselectTrainingRootsV3Tests(unittest.TestCase):
    def test_excludes_full_registered_v2_panel_without_reading_outcomes(self):
        training = {"roots": [
            {"family": family, "record": {"moves": [str(family)]}}
            for family in range(100, 580)
        ]}
        evaluation = {"roots": [{"family": 999, "record": {"moves": ["eval"]}}]}
        audit = {"selection": {
            "training_root_indices_remaining": [0, 480],
            "training_root_count_remaining": 480,
        }}
        v2_plan = {"training_families": list(range(100, 220))}
        panel = build_panel(training, evaluation, audit, v2_plan, {"fixture": "a" * 64})
        selected = {row["family"] for row in panel["roots"]}
        self.assertEqual(len(selected), 120)
        self.assertTrue(selected.isdisjoint(v2_plan["training_families"]))
        self.assertEqual(panel["registered_v2_panel_families_excluded"], v2_plan["training_families"])
        self.assertEqual(panel["eligible_remaining_count"], 360)
        self.assertFalse(panel["outcome_fields_used_for_selection"])
        self.assertEqual(panel["training_evaluation_exact_record_overlap"], 0)

    def test_rejects_changed_v2_panel_size(self):
        training = {"roots": [
            {"family": family, "record": {"moves": [str(family)]}}
            for family in range(100, 580)
        ]}
        with self.assertRaisesRegex(ValueError, "v2 registered panel"):
            build_panel(training, {"roots": []}, {"selection": {
                "training_root_indices_remaining": [0, 480],
                "training_root_count_remaining": 480,
            }}, {"training_families": [100]}, {"fixture": "a" * 64})


if __name__ == "__main__":
    unittest.main()
