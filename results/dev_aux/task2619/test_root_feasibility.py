import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent


def read_json(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def canonical(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


class RootFeasibilityTest(unittest.TestCase):
    def test_regenerated_pools_are_complete_unique_and_disjoint(self):
        subprocess.run([sys.executable, str(HERE / "root_feasibility.py")], check=True, capture_output=True, text=True)
        summary = read_json("root-feasibility.json")
        training = read_json("prospective-training-roots.json")["roots"]
        evaluation = read_json("prospective-evaluation-roots.json")["roots"]
        self.assertEqual(summary["status"], "OUTCOME_BLIND_ROOT_FEASIBILITY_ONLY")
        self.assertEqual(len(training), 512)
        self.assertEqual(len(evaluation), 32)
        train_keys = {canonical(row["record"]) for row in training}
        eval_keys = {canonical(row["record"]) for row in evaluation}
        self.assertEqual(len(train_keys), 512)
        self.assertEqual(len(eval_keys), 32)
        self.assertFalse(train_keys & eval_keys)
        self.assertEqual(summary["prospective_training"]["overlap_with_all_prior_roots"], 0)
        self.assertEqual(summary["prospective_evaluation"]["overlap_with_prior_roots_or_training"], 0)
        for row in training + evaluation:
            self.assertEqual(len(row["record"]["moves"]), 8)
            digest = hashlib.sha256(canonical(row["record"]).encode("utf-8")).hexdigest()
            self.assertEqual(row["record_sha256"], digest)
        self.assertIn("not descendant-state", summary["claim_limit"])


if __name__ == "__main__":
    unittest.main()
