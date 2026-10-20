from __future__ import annotations

import json
import unittest

from results.dev_aux.task2618.reselect_training_roots_v4 import build_panel


def fixture_inputs():
    training = {"roots": [
        {"family": family, "record": {"moves": [str(family)]}}
        for family in range(480)
    ]}
    evaluation = {"roots": [{"family": 9999, "record": {"moves": ["eval"]}}]}
    audit = {"selection": {
        "training_root_indices_remaining": [0, 480],
        "training_root_count_remaining": 480,
    }}
    v1 = [
        {"family": family, "unstarted": False, "outcome_white_relative": family % 3}
        for family in range(51)
    ] + [
        {"family": 51 + index, "unstarted": True, "outcome_white_relative": "UNSTARTED"}
        for index in range(69)
    ]
    v2 = {"training_families": list(range(51, 171))}
    v3 = {"training_families": list(range(0, 18)) + list(range(171, 273))}
    projection = {
        "status": "OUTCOME_FREE_EXPOSURE_PROJECTION",
        "projected_fields": ["family", "unstarted"],
        "rows": [{"family": row["family"], "unstarted": row["unstarted"]} for row in v1],
        "source_sha256": "b" * 64,
        "outcome_fields_used": False,
    }
    return training, evaluation, audit, projection, v2, v3


class ReselectTrainingRootsV4Tests(unittest.TestCase):
    def test_excludes_union_and_is_deterministic_without_outcomes(self):
        training, evaluation, audit, projection, v2, v3 = fixture_inputs()
        hashes = {"fixture": "a" * 64}
        first = build_panel(training, evaluation, audit, projection, v2, v3, hashes)
        selected = {row["family"] for row in first["roots"]}
        exposed = {row["family"] for row in projection["rows"]
                   if row.get("unstarted") is not True}
        excluded = exposed | set(v2["training_families"]) | set(v3["training_families"])
        self.assertEqual(len(exposed), 51)
        self.assertEqual(first["registered_panel_pairwise_overlap_counts"],
                         {"v1_v2": 0, "v1_v3": 18, "v2_v3": 0})
        self.assertEqual(first["excluded_union_count"], 273)
        self.assertEqual(first["eligible_remaining_count"], 207)
        self.assertEqual(len(selected), 120)
        self.assertTrue(selected.isdisjoint(excluded))
        self.assertFalse(first["outcome_fields_used_for_selection"])
        self.assertEqual(first["training_evaluation_exact_record_overlap"], 0)

        second = build_panel(training, evaluation, audit, projection, v2, v3, hashes)
        self.assertEqual([r["family"] for r in first["roots"]],
                         [r["family"] for r in second["roots"]])

    def test_rejects_incomplete_v1_exposure_evidence(self):
        training, evaluation, audit, projection, v2, v3 = fixture_inputs()
        short = dict(projection, rows=projection["rows"][1:])
        with self.assertRaisesRegex(ValueError, "v1 exposure family count"):
            build_panel(training, evaluation, audit, short, v2, v3, {})

    def test_rejects_unexpected_prior_panel_overlap(self):
        training, evaluation, audit, projection, v2, v3 = fixture_inputs()
        v3["training_families"][-1] = 51
        with self.assertRaisesRegex(ValueError, "overlap differs"):
            build_panel(training, evaluation, audit, projection, v2, v3, {})


if __name__ == "__main__":
    unittest.main()
