import json
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("feasibility.py")


class FeasibilityTest(unittest.TestCase):
    def test_source_bound_projection_and_threshold(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "FEASIBILITY_ONLY")
        self.assertAlmostEqual(data["estimate_minutes"], 95.7683580958, places=8)
        self.assertEqual(data["all_in_cap_minutes"], 110)
        self.assertLess(data["estimate_minutes"], data["all_in_cap_minutes"])
        self.assertLess(data["all_in_cap_minutes"], 120)
        self.assertEqual(data["threshold_assessment"], "BELOW_120_MINUTES")
        self.assertEqual(len(data["source_pins"]), 4)
        self.assertTrue(all(len(pin["sha256"]) == 64 for pin in data["source_pins"].values()))
        self.assertEqual(set(data["cost_scan_runner_source_pins"]), {
            "shared_chess_cost_scan", "shared_wdl_cost_scan",
        })
        for source_map in data["cost_scan_runner_source_pins"].values():
            self.assertTrue(source_map)
            self.assertTrue(all(len(pin["sha256"]) == 64 for pin in source_map.values()))


if __name__ == "__main__":
    unittest.main()
