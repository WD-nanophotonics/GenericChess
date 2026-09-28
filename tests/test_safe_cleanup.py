import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.safe_cleanup import CleanupRegistry


class SafeCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.candidate = self.root / "pytest-output"
        self.candidate.mkdir()
        (self.candidate / "result.txt").write_text("initial", encoding="utf-8")
        self.registry = CleanupRegistry(self.root)

    def test_registration_does_not_delete_and_requires_approval(self):
        self.registry.register("pytest-output", "Disposable test output")
        self.assertTrue(self.candidate.exists())
        self.assertEqual([], self.registry.execute("DELETE_REGISTERED"))
        self.assertTrue(self.candidate.exists())

    def test_changed_tree_is_rejected_before_deletion(self):
        self.registry.register("pytest-output", "Disposable test output")
        self.registry.approve("pytest-output")
        (self.candidate / "result.txt").write_text("changed", encoding="utf-8")
        with patch("tools.safe_cleanup.shutil.rmtree") as remove:
            with self.assertRaisesRegex(ValueError, "changed"):
                self.registry.execute("DELETE_REGISTERED")
            remove.assert_not_called()

    def test_execute_requires_exact_confirmation(self):
        self.registry.register("pytest-output", "Disposable test output")
        self.registry.approve("pytest-output")
        with patch("tools.safe_cleanup.shutil.rmtree") as remove:
            with self.assertRaisesRegex(ValueError, "confirm"):
                self.registry.execute("wrong")
            remove.assert_not_called()

    def test_protected_and_parent_paths_are_rejected(self):
        (self.root / ".git").mkdir()
        for name in ("..", ".", ".git", "../outside"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.registry.register(name, "Should be rejected")

    def test_execute_calls_remove_only_for_approved_unchanged_path(self):
        self.registry.register("pytest-output", "Disposable test output")
        self.registry.approve("pytest-output")
        with patch("tools.safe_cleanup.shutil.rmtree") as remove:
            self.assertEqual(["pytest-output"], self.registry.execute("DELETE_REGISTERED"))
            remove.assert_called_once_with(self.candidate)


if __name__ == "__main__":
    unittest.main()
