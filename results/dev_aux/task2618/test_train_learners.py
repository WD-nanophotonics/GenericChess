from __future__ import annotations

from types import SimpleNamespace
from io import StringIO
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import chess

from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2618 import train_learners as runner


class FakeAction:
    def uci(self):
        return "a2a3"


class TinyEnv:
    def __init__(self, plies=0):
        self.plies = plies

    def record(self):
        return {"plies": self.plies}

    def terminal(self):
        return 0 if self.plies >= 2 else None

    def player(self):
        return self.plies % 2

    def push(self, _action):
        self.plies += 1


class TinySearch:
    calls = []

    def __init__(self, depth, qdepth):
        self.depth = depth
        self.qdepth = qdepth

    def search(self, env, model, *, nodes, seconds, seed, cancel):
        self.calls.append({"actor": env.player(), "weights": tuple(model.weights), "nodes": nodes, "seed": seed})
        return SimpleNamespace(
            complete=True,
            action=FakeAction(),
            value=0.0,
            pv_phi=(0, 0, 0, 0, 0),
            pv_terminal=False,
            samples=(),
            nodes=1,
            seconds=0.001,
            reason="complete",
        )


class TrainLearnerRunnerTests(unittest.TestCase):
    def test_registered_preflight_accepts_exact_hashes_without_search(self):
        session = json.loads((runner.ROOT / ".local_agent/session.json").read_text(encoding="utf-8"))
        role = json.loads((runner.ROOT / ".local_agent/role.json").read_text(encoding="utf-8"))
        source = "results/dev_aux/task2618/train_learners.py"
        source_hash = hashlib.sha256((runner.ROOT / source).read_bytes()).hexdigest()
        plan = {
            "status": "FROZEN_BEFORE_SEARCH",
            "task": "DEV_AUX2618_CHESS_LEARNER_COMPARISON",
            "methods": list(runner.METHODS),
            "session_id": session["id"],
            "python_chess_version": chess.__version__,
            "source_sha256": {source: source_hash},
            "roots_per_seed": 1,
            "seeds": [17],
            "evaluation": {"root_count": 1},
        }
        plan_raw = json.dumps(plan, sort_keys=True).encode()
        roots = {"status": "FROZEN_BEFORE_TRAINING", "roots": [{"family": 1, "record": {"moves": []}}]}
        root_raw = json.dumps(roots, sort_keys=True).encode()
        eval_roots = {"status": "FROZEN_BEFORE_TRAINING", "roots": [{"family": 2, "record": {"moves": []}}]}
        eval_root_raw = json.dumps(eval_roots, sort_keys=True).encode()
        registration = {
            "status": "REGISTERED_PRE_TRAINING",
            "session_id": session["id"],
            "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
            "root_manifest_sha256": hashlib.sha256(root_raw).hexdigest(),
            "evaluation_root_manifest_sha256": hashlib.sha256(eval_root_raw).hexdigest(),
            "source_sha256": plan["source_sha256"],
        }
        with tempfile.TemporaryDirectory(dir=runner.ROOT / "results/dev_aux/task2618") as temp:
            run_dir = Path(temp)
            (run_dir / "plan.json").write_bytes(plan_raw)
            (run_dir / "registration.json").write_text(json.dumps(registration), encoding="utf-8")
            (run_dir / "root-manifest.json").write_bytes(root_raw)
            (run_dir / "evaluation-root-manifest.json").write_bytes(eval_root_raw)
            with patch.object(runner, "RUN", run_dir):
                loaded, loaded_registration, loaded_roots = runner.validate_registration()
            self.assertEqual(loaded["session_id"], session["id"])
            self.assertEqual(loaded_registration["status"], "REGISTERED_PRE_TRAINING")
            self.assertEqual(len(loaded_roots["roots"]), 1)
            self.assertFalse(list(run_dir.glob("*started.json")))

    def test_registered_preflight_rejects_changed_source_and_write_once_outputs(self):
        session = json.loads((runner.ROOT / ".local_agent/session.json").read_text(encoding="utf-8"))
        source = "results/dev_aux/task2618/train_learners.py"
        plan = {
            "status": "FROZEN_BEFORE_SEARCH",
            "task": "DEV_AUX2618_CHESS_LEARNER_COMPARISON",
            "methods": list(runner.METHODS),
            "session_id": session["id"],
            "python_chess_version": chess.__version__,
            "source_sha256": {source: hashlib.sha256((runner.ROOT / source).read_bytes()).hexdigest()},
            "roots_per_seed": 1,
            "seeds": [17],
            "evaluation": {"root_count": 1},
        }
        plan_raw = json.dumps(plan, sort_keys=True).encode()
        roots_raw = json.dumps({"status": "FROZEN_BEFORE_TRAINING", "roots": [{"family": 1}]}).encode()
        eval_roots_raw = json.dumps({"status": "FROZEN_BEFORE_TRAINING", "roots": [{"family": 2}]}).encode()
        registration = {
            "status": "REGISTERED_PRE_TRAINING", "session_id": session["id"],
            "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
            "root_manifest_sha256": hashlib.sha256(roots_raw).hexdigest(),
            "evaluation_root_manifest_sha256": hashlib.sha256(eval_roots_raw).hexdigest(),
            "source_sha256": plan["source_sha256"],
        }
        with tempfile.TemporaryDirectory(dir=runner.ROOT / "results/dev_aux/task2618") as temp:
            run_dir = Path(temp)
            (run_dir / "plan.json").write_bytes(plan_raw)
            (run_dir / "registration.json").write_text(json.dumps(registration), encoding="utf-8")
            (run_dir / "root-manifest.json").write_bytes(roots_raw)
            (run_dir / "evaluation-root-manifest.json").write_bytes(eval_roots_raw)
            with patch.object(runner, "RUN", run_dir):
                (run_dir / "started.json").write_text("{}", encoding="utf-8")
                with self.assertRaisesRegex(FileExistsError, "refusing rerun/top-up"):
                    runner.validate_registration()
                (run_dir / "started.json").unlink()
                (run_dir / "arm-progress.jsonl").write_text("{}\n", encoding="utf-8")
                with self.assertRaisesRegex(FileExistsError, "refusing rerun/top-up"):
                    runner.validate_registration()
                (run_dir / "arm-progress.jsonl").unlink()
                plan["source_sha256"][source] = "0" * 64
                plan_raw = json.dumps(plan, sort_keys=True).encode()
                registration["plan_sha256"] = hashlib.sha256(plan_raw).hexdigest()
                registration["source_sha256"] = plan["source_sha256"]
                (run_dir / "plan.json").write_bytes(plan_raw)
                (run_dir / "registration.json").write_text(json.dumps(registration), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "registered source changed"):
                    runner.validate_registration()

    def test_root_block_and_missing_slot_are_fixed_and_censored(self):
        plan = {"roots_per_seed": 2}
        roots = [{"family": n, "record": {"moves": []}} for n in range(8)]
        self.assertEqual([r["family"] for r in runner.episode_root_rows(plan, roots, 2)], [4, 5])
        slot = runner.missing_slot(
            method="TDLeaf", seed_index=0, seed=17, family=99, game_index=4,
            variant="TDLeaf", learner_color=1, reason="UNSTARTED_AFTER_CAP",
        )
        self.assertIsNone(slot["outcome_white_relative"])
        self.assertTrue(slot["unstarted"])
        self.assertEqual(slot["ending"], "UNSTARTED_AFTER_CAP")

    def test_completed_arm_is_fsynced_before_a_later_arm_failure(self):
        session = json.loads((runner.ROOT / ".local_agent/session.json").read_text(encoding="utf-8"))
        plan = {
            "task": "DEV_AUX2618_CHESS_LEARNER_COMPARISON",
            "session_id": session["id"],
            "python_chess_version": chess.__version__,
            "source_sha256": {},
            "arm_order": [[0, "TreeStrap"], [0, "TDLeaf"]],
            "seeds": [17],
            "roots_per_seed": 1,
            "training_hard_cap_seconds": 30,
        }
        registration = {}
        roots = {"roots": [{"family": 1, "record": {"moves": []}}]}
        with tempfile.TemporaryDirectory(dir=runner.ROOT / "results/dev_aux/task2618") as temp:
            run_dir = Path(temp)
            (run_dir / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            (run_dir / "registration.json").write_text(json.dumps(registration), encoding="utf-8")
            (run_dir / "root-manifest.json").write_text(json.dumps(roots), encoding="utf-8")
            first_arm = {
                "seed_index": 0, "seed": 17, "method": "TreeStrap",
                "status": "NODE_BUDGET_REACHED", "nodes_total": 100,
            }
            with patch.object(runner, "RUN", run_dir), \
                 patch.object(runner, "validate_registration", return_value=(plan, registration, roots)), \
                 patch.object(runner, "SharedDeleteStopReader", return_value=lambda: None), \
                 patch.object(runner, "_run_arm", side_effect=[first_arm, RuntimeError("later arm fault")]):
                with self.assertRaisesRegex(RuntimeError, "later arm fault"):
                    runner.run()
            progress = [json.loads(line) for line in (run_dir / "arm-progress.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(progress, [first_arm])
            self.assertFalse((run_dir / "training-result.json").exists())

    def test_candidate_and_fixed_foe_route_on_opposite_turns_and_draw_is_actual(self):
        TinySearch.calls = []
        plan = {
            "max_plies_per_game": 8,
            "training_hard_cap_seconds": 10,
            "nodes_per_seed_method_arm": 100,
            "max_nodes_per_search": 10,
            "seconds_per_search_cap": 1,
            "ordering_seed_base": 1000,
            "search": {"depth": 2, "qdepth": 0},
        }
        candidate = Model([1, 0.8, 0.9, 1.1, 1.2])
        foe = Model([1, 1, 1, 1, 1])
        counts = {"candidate_nodes": 0, "foe_nodes": 0, "searches": 0,
                  "complete_searches": 0, "incomplete_searches": 0,
                  "actual_terminal_games": 0, "unknown_games": 0}
        with patch.object(runner, "restore", side_effect=lambda _g, _cc, record: TinyEnv(record["plies"])), \
             patch.object(runner, "AlphaBeta", TinySearch):
            game, queries, end = runner.play_episode(
                plan=plan, method="WDL", seed=19, game_index=0, family=33,
                record={"plies": 0}, learner_color=0, candidate=candidate, foe=foe,
                variant="proposal", tree=None, td=None, arm_counts=counts,
                started=0.0, global_started=__import__("time").perf_counter(), stop=lambda: None,
            )
        self.assertEqual([call["actor"] for call in TinySearch.calls], [0, 1])
        self.assertEqual(TinySearch.calls[0]["weights"], tuple(candidate.weights))
        self.assertEqual(TinySearch.calls[1]["weights"], tuple(foe.weights))
        self.assertEqual(counts["candidate_nodes"], 1)
        self.assertEqual(counts["foe_nodes"], 1)
        self.assertEqual(end["outcome"], 0)
        self.assertEqual(game["ending"], "ACTUAL_TERMINAL")
        self.assertEqual(len(queries), 2)

    def test_nonfinite_search_bounds_are_serialized_as_strings(self):
        self.assertEqual(runner.json_number(float("inf")), "inf")
        self.assertEqual(runner.json_number(float("-inf")), "-inf")

    def test_wdl_arm_records_complete_four_game_block_and_actual_draw_bounds(self):
        TinySearch.calls = []
        plan = {
            "roots_per_seed": 1,
            "nodes_per_seed_method_arm": 100,
            "training_hard_cap_seconds": 30,
            "max_plies_per_game": 8,
            "max_nodes_per_search": 10,
            "seconds_per_search_cap": 1,
            "ordering_seed_base": 1000,
            "search": {"depth": 2, "qdepth": 0},
            "fixed_foe_weights": [1, 1, 1, 1, 1],
            "learner_parameters": {},
        }
        roots = [{"family": 810033, "record": {"plies": 0}}]
        games_out, queries_out, blocks_out = StringIO(), StringIO(), StringIO()
        with patch.object(runner, "restore", side_effect=lambda _g, _cc, record: TinyEnv(record["plies"])), \
             patch.object(runner, "AlphaBeta", TinySearch):
            result = runner._run_arm(
                plan, roots, 0, 19, "WDL", time.perf_counter(), lambda: None,
                queries_out, games_out, blocks_out,
            )
        self.assertEqual(result["started_games"], 4)
        self.assertEqual(result["games_or_slots"], 4)
        self.assertEqual(result["missing_slots"], 0)
        self.assertEqual(result["wdl_proposal_blocks"], 1)
        self.assertEqual(result["wdl_proposals_rejected"], 1)
        self.assertEqual(result["nodes_total"], result["nodes_candidate"] + result["nodes_fixed_foe"])
        block = __import__("json").loads(blocks_out.getvalue())
        self.assertEqual(block["interval_proposal_minus_incumbent"], [0.0, 0.0])
        self.assertFalse(block["accepted"])


if __name__ == "__main__":
    unittest.main()
