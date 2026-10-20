from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from results.dev_aux.task2618 import register_evaluation as gate


class RegisterEvaluationTests(unittest.TestCase):
    def _prepare(self, root: Path, revision: int = 2) -> tuple[Path, dict, bytes]:
        run_name = f"learner-comparison-v{revision}"
        run_dir = root / "results/dev_aux/task2618" / run_name
        run_dir.mkdir(parents=True)
        source = root / "runner.py"
        source.write_text("pinned source\n", encoding="utf-8")
        roots = [{"family": 99, "record": {"moves": ["e2e4"]}}]
        root_raw = json.dumps({"roots": roots}, sort_keys=True).encode()
        eval_digest = hashlib.sha256(
            b"\n".join(json.dumps(r["record"], sort_keys=True, separators=(",", ":")).encode()
                       for r in roots)
        ).hexdigest()
        plan = {
            "design_revision": revision,
            "session_id": "segment-2",
            "source_sha256": {"runner.py": hashlib.sha256(source.read_bytes()).hexdigest()},
            "python_chess_version": gate.chess.__version__,
            "seeds": [3],
            "methods": ["TreeStrap"],
            "evaluation_root_selection": {"root_count": 1, "exact_selected_records_sha256": eval_digest},
            "evaluation": {"root_count": 1},
        }
        plan_raw = json.dumps(plan, sort_keys=True).encode()
        (run_dir / "plan.json").write_bytes(plan_raw)
        training_raw = json.dumps({"status": "COMPLETE_TRAINING"}).encode()
        (run_dir / "training-result.json").write_bytes(training_raw)
        (run_dir / "evaluation-root-manifest.json").write_bytes(root_raw)
        (run_dir / "registration.json").write_text(json.dumps({
            "status": "REGISTERED_PRE_TRAINING",
            "search_started": False,
            "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
            "evaluation_root_manifest_sha256": hashlib.sha256(root_raw).hexdigest(),
        }), encoding="utf-8")
        local = root / ".local_agent"
        local.mkdir()
        (local / "session.json").write_text(json.dumps({"state": "active", "id": "segment-2"}), encoding="utf-8")
        (local / "role.json").write_text(json.dumps({"role": "DEV_AUX", "branch": "sidemission"}), encoding="utf-8")
        return run_dir, plan, training_raw

    def test_evaluation_registration_is_bound_only_after_complete_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _plan, training_raw = self._prepare(root)
            with patch.object(gate, "ROOT", root), patch.object(
                gate, "SharedDeleteStopReader", lambda _root: (lambda: None)
            ), patch.object(gate, "verify_training_result", return_value={(0, "TreeStrap"): {}}):
                result = gate.register("learner-comparison-v2")
                registration = json.loads((run_dir / "evaluation-registration.json").read_text())
                self.assertEqual(registration["kind"], "BOUND_AFTER_COMPLETE_TRAINING_BEFORE_EVALUATION")
                self.assertEqual(registration["training_result_sha256"], hashlib.sha256(training_raw).hexdigest())
                self.assertFalse(registration["evaluation_search_started"])
                self.assertEqual(result["evaluation_root_count"], 1)
                with self.assertRaisesRegex(FileExistsError, "write-once"):
                    gate.register("learner-comparison-v2")

    def test_incomplete_training_cannot_open_evaluation_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _plan, _training_raw = self._prepare(root)
            with patch.object(gate, "ROOT", root), patch.object(
                gate, "SharedDeleteStopReader", lambda _root: (lambda: None)
            ), patch.object(gate, "verify_training_result", side_effect=ValueError("incomplete arm")):
                with self.assertRaisesRegex(ValueError, "incomplete arm"):
                    gate.register("learner-comparison-v2")
            self.assertFalse((run_dir / "evaluation-registration.json").exists())

    def test_revision3_evaluation_gate_is_supported_after_complete_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _plan, _training_raw = self._prepare(root, revision=3)
            with patch.object(gate, "ROOT", root), patch.object(
                gate, "SharedDeleteStopReader", lambda _root: (lambda: None)
            ), patch.object(gate, "verify_training_result", return_value={(0, "TreeStrap"): {}}):
                result = gate.register("learner-comparison-v3")
            registration = json.loads((run_dir / "evaluation-registration.json").read_text())
            self.assertEqual(registration["kind"], "BOUND_AFTER_COMPLETE_TRAINING_BEFORE_EVALUATION")
            self.assertEqual(result["status"], "PRE_EVALUATION_PREFLIGHT_PASS")
            self.assertFalse(result["evaluation_search_started"])

    def test_revision4_evaluation_gate_is_supported_after_complete_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _plan, _training_raw = self._prepare(root, revision=4)
            with patch.object(gate, "ROOT", root), patch.object(
                gate, "SharedDeleteStopReader", lambda _root: (lambda: None)
            ), patch.object(gate, "verify_training_result", return_value={(0, "TreeStrap"): {}}):
                result = gate.register("learner-comparison-v4")
            registration = json.loads((run_dir / "evaluation-registration.json").read_text())
            self.assertEqual(registration["kind"], "BOUND_AFTER_COMPLETE_TRAINING_BEFORE_EVALUATION")
            self.assertEqual(result["status"], "PRE_EVALUATION_PREFLIGHT_PASS")
            self.assertFalse(result["evaluation_search_started"])


if __name__ == "__main__":
    unittest.main()
