from __future__ import annotations

import json
import unittest

from results.dev_aux.task2618.project_v1_exposure import project


class ProjectV1ExposureTests(unittest.TestCase):
    def test_projection_discards_all_outcome_and_weight_fields(self):
        rows = [
            {"family": 1, "unstarted": False, "outcome_white_relative": 1,
             "weights_at_episode_end": [1, 2, 3]},
            {"family": 2, "unstarted": True, "outcome_white_relative": "UNKNOWN",
             "weights_at_episode_end": [4, 5, 6]},
        ]
        first = project(b"\n".join(json.dumps(row).encode() for row in rows))
        for row in rows:
            row["outcome_white_relative"] = "CHANGED"
            row["weights_at_episode_end"] = [99]
        second = project(b"\n".join(json.dumps(row).encode() for row in rows))
        self.assertEqual(first["rows"], second["rows"])
        self.assertEqual(first["rows"], [
            {"family": 1, "unstarted": False},
            {"family": 2, "unstarted": True},
        ])
        self.assertFalse(first["outcome_fields_used"])


if __name__ == "__main__":
    unittest.main()
