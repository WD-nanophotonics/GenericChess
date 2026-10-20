"""No-search integrity tests for the task2617 frozen cap protocol."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from results.dev_aux.task2617.evaluate import (
    family_cap,
    run as run_evaluation,
    terminal_reward,
    validate_slots,
)
from results.dev_aux.task2617.analyze import analyze, analyze_data
from results.dev_aux.task2617.register_run import build_registration


ROOT = Path.cwd()
TASK = ROOT / "results/dev_aux/task2617"
TEST_TMP = ROOT / ".local_agent"


class Task2617ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.feasibility = json.loads((TASK / "feasibility.json").read_text(encoding="utf-8"))
        cls.roots = json.loads((TASK / "prospective-roots.json").read_text(encoding="utf-8"))["roots"]
        cls.order = json.loads((TASK / "execution-order.json").read_text(encoding="utf-8"))["slots"]
        cls.caps = {
            str(row["family"]): row["node_cap_both_sides"]
            for row in cls.feasibility["protocol"]["budget_assignments"]
        }
        cls.plan = {
            "caps_by_family": cls.caps,
            "cap_values_nodes_both_sides": [20000, 40000],
        }
        cls.eval_plan = {
            "rules": [0],
            "seeds": [1977, 8173, 27182, 31415],
            "endpoints": ["initial", "TD", "WDL", "TreeStrap"],
            "foes": {"uniform": [1.0] * 5},
        }
        cls.slots = [
            [0, seed, family, color, endpoint, "uniform"]
            for family, seed, color, endpoint in cls.order
        ]
        cls.eval_plan["slots"] = cls.slots

    def test_family_caps_are_frozen_and_balanced(self):
        self.assertEqual(len(self.caps), 32)
        self.assertEqual({family_cap(self.plan, family) for family in range(710001, 710033)}, {20000, 40000})
        self.assertEqual(sum(value == 20000 for value in self.caps.values()), 16)
        self.assertEqual(sum(value == 40000 for value in self.caps.values()), 16)
        with self.assertRaises(ValueError):
            family_cap(self.plan, -1)

    def test_slot_order_is_exact_frozen_cross_product(self):
        validate_slots(self.slots, self.plan, self.eval_plan)
        self.assertEqual(len(self.slots), 1024)
        malformed = [list(slot) for slot in self.slots]
        malformed[0][4] = "not-a-registered-endpoint"
        with self.assertRaises(ValueError):
            validate_slots(malformed, self.plan, self.eval_plan)
        with self.assertRaises(ValueError):
            validate_slots(self.slots[:-1], self.plan, self.eval_plan)

    def test_unknown_is_censored_and_only_actual_wdl_is_scored(self):
        self.assertIsNone(terminal_reward(None, 0))
        self.assertIsNone(terminal_reward(None, 1))
        self.assertEqual([terminal_reward(x, 0) for x in (-1, 0, 1)], [-1, 0, 1])
        self.assertEqual([terminal_reward(x, 1) for x in (-1, 0, 1)], [1, 0, -1])
        with self.assertRaises(ValueError):
            terminal_reward(2, 0)

    def test_registration_is_deterministic_and_exactly_bound(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as tmp:
            first = Path(tmp) / "first"
            second = Path(tmp) / "second"
            reg_a = build_registration(first)
            reg_b = build_registration(second)
            self.assertEqual(reg_a, reg_b)
            self.assertEqual(reg_a["registered_slots"], 1024)
            self.assertTrue(reg_a["no_training_yet"])
            self.assertTrue(reg_a["no_evaluation_yet"])
            for directory, registration in ((first, reg_a), (second, reg_b)):
                for name, field in (
                    ("plan.json", "plan_sha256"),
                    ("eval-plan.json", "eval_plan_sha256"),
                    ("root-manifest.json", "root_manifest_sha256"),
                    ("runner-registration.json", "runner_registration_sha256"),
                    ("model-binding.json", "model_binding_sha256"),
                ):
                    digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
                    self.assertEqual(digest, registration[field])
                runner_registration = json.loads((directory / "runner-registration.json").read_text(encoding="utf-8"))
                self.assertIn("results/dev_aux/task2617/analyze.py", runner_registration["runtime_pins"])
                self.assertIn("python_version", runner_registration)
                self.assertIn("python_chess_version", runner_registration)
                plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
                self.assertEqual(plan["max_paid_nodes"], 30_720_000)
                self.assertEqual(plan["hard_cap_plus_reserve_seconds"], 6300)
                self.assertFalse((directory / "eval-started.json").exists())
                self.assertFalse((directory / "eval-games.jsonl").exists())
            with self.assertRaises(FileExistsError):
                build_registration(first)

    def test_evaluator_refuses_unregistered_run_without_search(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as tmp:
            with self.assertRaises(FileNotFoundError):
                run_evaluation(Path(tmp) / "empty-run")
            with self.assertRaises(FileNotFoundError):
                analyze(Path(tmp) / "empty-run")

    def test_analysis_censors_unknown_and_missing_without_awarding_draws(self):
        report = analyze_data(self.plan, self.eval_plan, [], [])
        for cap in ("20000", "40000"):
            for endpoint in self.eval_plan["endpoints"]:
                row = report["by_cap"][cap]["endpoints"][endpoint]
                self.assertEqual((row["lower"], row["upper"]), (-1.0, 1.0))
                self.assertEqual(row["censored"], row["n"])
                self.assertEqual(row["actual_wdl"]["draw"], 0)
        for row in report["cap_40000_minus_20000_endpoint_reward_bounds"].values():
            self.assertEqual((row["lower"], row["upper"]), (-2.0, 2.0))

        slot = self.slots[0]
        cap = family_cap(self.plan, slot[2])
        color = slot[3]
        game = {
            "slot": slot,
            "family_cap_nodes_both_sides": cap,
            "outcome": 1,
            "reward": terminal_reward(1, color),
            "ending": "ACTUAL_TERMINAL",
            "nodes": 2,
            "queries": 1,
        }
        query = {
            "slot": slot,
            "family_cap_nodes_both_sides": cap,
            "nodes": 2,
            "effective_nodes": 8192,
        }
        partial = analyze_data(self.plan, self.eval_plan, [game], [query])
        endpoint_row = partial["by_cap"][str(cap)]["endpoints"][slot[4]]
        self.assertEqual(endpoint_row["actual_wdl"]["win"], 1)
        self.assertEqual(endpoint_row["censored"], endpoint_row["n"] - 1)
        self.assertAlmostEqual(endpoint_row["lower"], (1 - (endpoint_row["n"] - 1)) / endpoint_row["n"])
        self.assertEqual(endpoint_row["upper"], 1.0)
        self.assertEqual(partial["paid_nodes_from_query_receipts"], 2)

    def test_analysis_audits_query_caps_and_run_summary(self):
        slot = self.slots[0]
        cap = family_cap(self.plan, slot[2])
        color = slot[3]
        game = {
            "slot": slot,
            "family_cap_nodes_both_sides": cap,
            "outcome": 0,
            "reward": 0,
            "ending": "ACTUAL_TERMINAL",
            "nodes": 3,
            "queries": 1,
        }
        query = {
            "slot": slot,
            "family_cap_nodes_both_sides": cap,
            "nodes": 3,
            "effective_nodes": 8192,
        }
        summary = {
            "expected": 1024,
            "actual": 1,
            "missing": 1023,
            "missing_slots": self.slots[1:],
            "actual_terminal": 1,
            "unknown": 0,
            "nodes": 3,
            "queries": 1,
            "status": "PARTIAL_CAP",
        }
        self.assertEqual(analyze_data(self.plan, self.eval_plan, [game], [query], summary)["paid_nodes_from_query_receipts"], 3)
        bad_summary = dict(summary, nodes=4)
        with self.assertRaisesRegex(ValueError, "run summary disagrees"):
            analyze_data(self.plan, self.eval_plan, [game], [query], bad_summary)
        over_cap_queries = [dict(query, nodes=8192) for _ in range(cap // 8192 + 1)]
        with self.assertRaisesRegex(ValueError, "combined actor nodes exceed"):
            analyze_data(self.plan, self.eval_plan, [], over_cap_queries)

    def test_analysis_reproduces_complete_finite_panel_wdl_and_pairs(self):
        games, queries = [], []
        for index, slot in enumerate(self.slots):
            outcome = (-1, 0, 1)[index % 3]
            cap = family_cap(self.plan, slot[2])
            games.append({
                "slot": slot,
                "family_cap_nodes_both_sides": cap,
                "outcome": outcome,
                "reward": terminal_reward(outcome, slot[3]),
                "ending": "ACTUAL_TERMINAL",
                "nodes": 2,
                "queries": 1,
            })
            queries.append({
                "slot": slot,
                "family_cap_nodes_both_sides": cap,
                "nodes": 2,
                "effective_nodes": 8192,
            })
        summary = {
            "expected": 1024,
            "actual": 1024,
            "missing": 0,
            "missing_slots": [],
            "actual_terminal": 1024,
            "unknown": 0,
            "nodes": 2048,
            "queries": 1024,
            "status": "COMPLETE",
        }
        report = analyze_data(self.plan, self.eval_plan, games, queries, summary)
        self.assertEqual(report["observed_game_rows"], 1024)
        self.assertEqual(report["paid_nodes_from_query_receipts"], 2048)
        for cap in ("20000", "40000"):
            for endpoint in self.eval_plan["endpoints"]:
                row = report["by_cap"][cap]["endpoints"][endpoint]
                self.assertEqual(row["censored"], 0)
                self.assertEqual(row["actual_wdl"]["loss"] + row["actual_wdl"]["draw"] + row["actual_wdl"]["win"], 128)
            for endpoint in ("TD", "WDL", "TreeStrap"):
                row = report["by_cap"][cap]["endpoint_minus_initial"][endpoint]
                self.assertEqual(row["lower"], row["upper"])
                self.assertEqual(row["censored_pairs"], 0)

    def test_evaluator_rejects_tampered_registered_plan(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as tmp:
            directory = Path(tmp) / "run"
            build_registration(directory)
            path = directory / "plan.json"
            plan = json.loads(path.read_text(encoding="utf-8"))
            plan["evaluation_hard_cap_seconds"] += 1
            path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "registered plan hash mismatch"):
                run_evaluation(directory)
            self.assertFalse((directory / "eval-started.json").exists())
            self.assertFalse((directory / "eval-games.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
