import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2618/wdl-shared-cost"


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SharedWDLCostScanAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan_bytes = (RUN / "plan.json").read_bytes()
        cls.plan = json.loads(cls.plan_bytes)
        cls.registration = json.loads((RUN / "registration.json").read_text())
        cls.started = json.loads((RUN / "started.json").read_text())
        cls.result = json.loads((RUN / "result.json").read_text())
        cls.rows = [json.loads(line) for line in (RUN / "episodes.jsonl").read_text().splitlines()]

    def test_write_once_plan_and_source_pins(self):
        self.assertEqual(self.registration["plan_sha256"], sha(self.plan_bytes))
        self.assertEqual(self.result["plan_sha256"], self.registration["plan_sha256"])
        self.assertEqual(self.started["plan_sha256"], self.registration["plan_sha256"])
        self.assertEqual(self.registration["session_id"], self.plan["session_id"])
        self.assertFalse(self.registration["search_started"])
        self.assertEqual(self.plan["root_indices"], list(range(32)))
        self.assertIn("training", self.plan["training_roots_path"])
        self.assertFalse(self.plan["fitness_evaluation"])
        for name, digest in self.plan["source_sha256"].items():
            self.assertEqual(sha((ROOT / name).read_bytes()), digest, name)
        roots_bytes = (ROOT / self.plan["training_roots_path"]).read_bytes()
        self.assertEqual(sha(roots_bytes), self.plan["training_roots_sha256"])

    def test_only_cost_and_censoring_fields_are_persisted(self):
        forbidden = {"white_outcome", "reward", "interval", "weights", "proposal_weights", "accepted"}
        self.assertEqual(len(self.rows), 20)
        for row in self.rows:
            self.assertTrue(forbidden.isdisjoint(row))
            self.assertFalse(row["terminal_label_or_model_weights_emitted"])
            self.assertEqual(row["candidate_nodes"] + row["fixed_foe_nodes"], row["total_nodes"])
        self.assertFalse(self.result["terminal_outcomes_or_coefficients_emitted"])
        self.assertFalse(self.result["fitness_evaluation"])

    def test_all_four_frozen_arms_spent_shared_cap_and_unknowns_remain_censored(self):
        self.assertEqual(self.result["status"], "COMPLETE_COST_ONLY")
        self.assertEqual(self.result["arm_count"], 4)
        self.assertEqual(sum(a["total_nodes"] for a in self.result["arms"]), 400000)
        self.assertEqual(sum(a["searches"] for a in self.result["arms"]), 3562)
        self.assertEqual(sum(a["complete_searches"] for a in self.result["arms"]), 3558)
        self.assertEqual(sum(a["paired_blocks_completed"] for a in self.result["arms"]), 4)
        self.assertEqual(sum(a["unknown_or_partial_episodes"] for a in self.result["arms"]), 4)
        self.assertEqual(sum(a["actual_terminal_episodes"] for a in self.result["arms"]), 16)
        for arm in self.result["arms"]:
            self.assertEqual(arm["total_nodes"], 100000)
            self.assertEqual(arm["games"], len([r for r in self.rows if r["seed"] == arm["seed"]]))
            self.assertEqual(arm["games"], arm["actual_terminal_episodes"] + arm["unknown_or_partial_episodes"])
            self.assertLessEqual(arm["incomplete_block_slots"], 3)


if __name__ == "__main__":
    unittest.main()
