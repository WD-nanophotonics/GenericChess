from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from results.dev_aux.task2618 import launch_registered_run as launcher


class FakeProcess:
    pid = 4242

    def __init__(self, _command, *, cwd, stdout, stderr):
        self.cwd = cwd
        stdout.write(b"fake stdout\n")
        stderr.write(b"fake stderr\n")

    def wait(self):
        return 0


class LaunchRegisteredRunTests(unittest.TestCase):
    def test_launcher_pins_process_and_exit_receipts_and_refuses_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "results/dev_aux/task2618/learner-comparison-v2"
            run_dir.mkdir(parents=True)
            source = root / "runner.py"
            source.write_text("frozen source\n", encoding="utf-8")
            plan = {
                "design_revision": 2,
                "session_id": "segment-1",
                "source_sha256": {"runner.py": hashlib.sha256(source.read_bytes()).hexdigest()},
            }
            plan_raw = json.dumps(plan).encode()
            (run_dir / "plan.json").write_bytes(plan_raw)
            (run_dir / "registration.json").write_text(json.dumps({
                "status": "REGISTERED_PRE_TRAINING",
                "search_started": False,
                "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
            }), encoding="utf-8")

            with patch.object(launcher, "ROOT", root), patch.object(
                launcher.subprocess, "Popen", FakeProcess
            ):
                result = launcher.launch("learner-comparison-v2")
                with self.assertRaisesRegex(FileExistsError, "refusing launch or top-up"):
                    launcher.launch("learner-comparison-v2")

            self.assertEqual(result["status"], "EXIT_RECORDED")
            self.assertEqual(result["return_code"], 0)
            self.assertEqual(result["stdout_sha256"], hashlib.sha256(b"fake stdout\n").hexdigest())
            self.assertEqual(result["stderr_sha256"], hashlib.sha256(b"fake stderr\n").hexdigest())
            self.assertEqual(json.loads((run_dir / "launch-started.json").read_text())["pid"], 4242)
            self.assertEqual(json.loads((run_dir / "launch-exit.json").read_text())["return_code"], 0)

    def test_launcher_rejects_registered_source_drift_before_creating_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "results/dev_aux/task2618/learner-comparison-v2"
            run_dir.mkdir(parents=True)
            plan = {"design_revision": 2, "source_sha256": {"runner.py": "0" * 64}}
            plan_raw = json.dumps(plan).encode()
            (run_dir / "plan.json").write_bytes(plan_raw)
            (run_dir / "registration.json").write_text(json.dumps({
                "status": "REGISTERED_PRE_TRAINING",
                "search_started": False,
                "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
            }), encoding="utf-8")
            (root / "runner.py").write_text("changed\n", encoding="utf-8")

            with patch.object(launcher, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "registered source changed"):
                    launcher.launch("learner-comparison-v2")

            self.assertFalse((run_dir / "launch-claim.json").exists())


if __name__ == "__main__":
    unittest.main()
