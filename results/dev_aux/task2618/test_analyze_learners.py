from __future__ import annotations

import unittest

from results.dev_aux.task2618.analyze_learners import finite_panel_analysis, validate_evaluation_accounting
from results.dev_aux.task2618.evaluate_learners import ENDPOINTS, finite_reward_bounds


def panel_plan():
    slots = []
    for seed_index, seed, family, color in ((0, 17, 810033, 0), (1, 23, 810034, 1)):
        for endpoint in ENDPOINTS:
            slots.append([seed_index, seed, family, color, endpoint])
    return {"evaluation": {"expected_slots": len(slots), "ordered_slots": slots}}


def evaluation_row(slot_index, slot, outcome):
    seed_index, seed, family, color, endpoint = slot
    return {
        "slot_index": slot_index,
        "slot": slot,
        "seed_index": seed_index,
        "seed": seed,
        "family": family,
        "learner_color": color,
        "endpoint": endpoint,
        "outcome_white_relative": outcome,
        "reward_bounds": list(finite_reward_bounds(outcome, color)),
    }


class AnalyzeLearnersTests(unittest.TestCase):
    def test_actual_outcomes_and_missing_or_unknown_slots_keep_finite_bounds(self):
        plan = panel_plan()
        slots = plan["evaluation"]["ordered_slots"]
        rows = [
            evaluation_row(0, slots[0], 0),       # initial draw as White
            evaluation_row(1, slots[1], 1),       # TreeStrap win as White
            evaluation_row(4, slots[4], None),    # initial UNKNOWN as Black
        ]
        result = finite_panel_analysis(plan, rows)
        self.assertEqual(result["status"], "FINITE_PANEL_BOUNDS_ONLY")
        self.assertEqual(result["observed_slots"], 3)
        self.assertEqual(result["missing_slots"], 5)
        self.assertFalse(result["unknown_is_draw"])
        self.assertFalse(result["population_inference"])
        contrast = next(c for c in result["contrasts"] if c["left_minus_right"] == "initial - TreeStrap")
        self.assertEqual(contrast["matched_slots_planned"], 2)
        self.assertEqual(contrast["observed_pair_slots"], 1)
        self.assertEqual(contrast["difference_bounds"], [-1.5, 0.5])
        self.assertEqual(contrast["per_seed_finite_panel"]["0"]["difference_bounds"], [-1.0, -1.0])
        self.assertEqual(contrast["per_seed_finite_panel"]["1"]["difference_bounds"], [-2.0, 2.0])

    def test_rejects_row_whose_frozen_slot_or_reward_orientation_was_changed(self):
        plan = panel_plan()
        slot = plan["evaluation"]["ordered_slots"][0]
        row = evaluation_row(0, slot, 1)
        row["reward_bounds"] = [-1, -1]
        with self.assertRaisesRegex(ValueError, "reward bounds"):
            finite_panel_analysis(plan, [row])
        row = evaluation_row(0, slot, 1)
        row["slot"] = [*slot[:-1], "WDL"]
        with self.assertRaisesRegex(ValueError, "frozen slot"):
            finite_panel_analysis(plan, [row])

    def test_partial_artifact_accounting_must_reconcile_every_missing_slot(self):
        plan = panel_plan()
        rows = [{"slot_index": 0, "outcome_white_relative": None, "nodes": 3, "searches": 1}]
        result = {
            "expected_slots": 8, "actual_slots": 1, "missing_slots": [1, 2, 3, 4, 5, 6, 7],
            "status": "PARTIAL_GLOBAL_CAP", "actual_terminal": 0, "unknown": 1,
            "nodes": 3, "queries": 1,
        }
        validate_evaluation_accounting(plan, result, rows)
        result["missing_slots"] = [2, 3, 4, 5, 6, 7]
        with self.assertRaisesRegex(ValueError, "missing-slot accounting"):
            validate_evaluation_accounting(plan, result, rows)


if __name__ == "__main__":
    unittest.main()
