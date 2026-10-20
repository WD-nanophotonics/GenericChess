import unittest

from results.dev_aux.task2617.analysis_orientation_audit import summarize


class OrientationAuditTests(unittest.TestCase):
    def test_learner_counts_flip_black_and_keep_unknown_censored(self):
        rows = []
        for color, outcome in ((0, 1), (0, -1), (1, 1), (1, -1), (0, 0), (1, None)):
            rows.append({"slot": [0, 1, 710001, color, "TD", "uniform"], "outcome": outcome})
        # summarize enforces the frozen panel size, so exercise the full six
        # cells with repeated balanced slots and verify just this target cell.
        repeated = []
        for cap in (20000, 40000):
            for endpoint in ("initial", "TD", "WDL", "TreeStrap"):
                capmap = {str(f): (20000 if f <= 710016 else 40000) for f in range(710001, 710033)}
                families = [710001, 710002] if cap == 20000 else [710017, 710018]
                examples = rows if (cap, endpoint) == (20000, "TD") else []
                pad = examples + [{"slot": [0, 1, families[i % 2], i % 2, endpoint, "uniform"], "outcome": None} for i in range(128 - len(examples))]
                repeated.extend(pad)
        result = summarize(repeated, capmap)
        cell = result["by_cap_endpoint"]["20000/TD"]
        self.assertEqual(cell["player0_L_D_W"], [2, 1, 2])
        self.assertEqual(cell["learner_L_D_W"], [2, 1, 2])
        self.assertEqual(cell["unknown_censored"], 123)
        self.assertEqual(result["unknown_censored"], 1019)


if __name__ == "__main__":
    unittest.main()
