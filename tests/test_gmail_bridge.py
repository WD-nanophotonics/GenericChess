import json
import unittest
from pathlib import Path
from unittest.mock import patch

from generic_chess.bridge.core import Paths, State, assert_chat_repo, atomic_json, existing_unit, git_environment, is_protocol_message, receive_message, safe_name, status, task_slug


def message(subject="[GC-BRIDGE][TASK] example"):
    return {"payload": {"headers": [
        {"name": "Subject", "value": subject},
        {"name": "From", "value": "icywoods.1@gmail.com"},
        {"name": "To", "value": "icywoods.1@gmail.com"},
    ]}}


class Request:
    def __init__(self, value=None, error=None): self.value, self.error = value, error
    def execute(self):
        if self.error: raise self.error
        return self.value


class Gmail:
    def __init__(self, msg, data=b"task", fail=False): self.msg, self.data, self.fail = msg, data, fail; self.downloads = 0
    def users(self): return self
    def messages(self): return self
    def get(self, **_): return Request(self.msg)
    def attachments(self): return self
    def get(self, **kwargs):
        if "messageId" not in kwargs: return Request(self.msg)
        self.downloads += 1
        encoded = __import__("base64").urlsafe_b64encode(self.data).decode().rstrip("=")
        return Request({"data": encoded}, RuntimeError("download failed") if self.fail else None)


class BridgeTests(unittest.TestCase):
    def test_protocol_requires_prefix_and_self_addresses(self):
        self.assertTrue(is_protocol_message(message()))
        self.assertFalse(is_protocol_message(message("ordinary message")))
        external = message(); external["payload"]["headers"][1]["value"] = "outside@example.com"
        self.assertFalse(is_protocol_message(external))


    def test_attachment_names_cannot_escape(self):
        for raw in ("../escape.py", "C:\\evil.ps1", "CON", "", ".."):
            value = safe_name(raw)
            self.assertNotIn("/", value); self.assertNotIn("\\", value); self.assertNotIn(value, {"", ".", ".."})


    def test_slug_is_stable_and_bounded(self):
        self.assertEqual(task_slug("[GC-BRIDGE][TASK] hello world", "abc"), "hello-world")


    def test_status_is_stale_for_dead_pid(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            paths = Paths(Path(tmp))
            atomic_json(paths.status, {"state": "running", "pid": 99999999, "last_poll_at": "2020-01-01T00:00:00+00:00"})
            self.assertEqual(status(paths)["state"], "STALE")


    def test_atomic_json_replaces_complete_document(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "manifest.json"; atomic_json(target, {"message_id": "x"})
            self.assertEqual(json.loads(target.read_text())["message_id"], "x")

    def test_existing_unit_recovers_after_state_crash(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            paths = Paths(Path(tmp)); unit = paths.inbox / "task"; unit.mkdir(parents=True)
            atomic_json(unit / "manifest.json", {"message_id": "gmail-id"})
            self.assertEqual(existing_unit(paths, "gmail-id"), unit)

    def test_mock_gmail_download_is_deduplicated(self):
        import tempfile
        full = message("[GC-BRIDGE][TASK] mock-task")
        full.update({"id": "gmail-1", "threadId": "thread-1", "internalDate": "1"})
        full["payload"]["parts"] = [{"filename": "task.md", "body": {"attachmentId": "a"}}]
        service = Gmail(full)
        with tempfile.TemporaryDirectory() as tmp, patch("generic_chess.bridge.core.commit_and_push"):
            paths, state = Paths(Path(tmp)), State(Paths(Path(tmp)))
            self.assertTrue(receive_message(service, paths, state, {"id": "gmail-1"}))
            self.assertFalse(receive_message(service, paths, state, {"id": "gmail-1"}))
            self.assertEqual(service.downloads, 1)
            self.assertEqual(json.loads(next(paths.inbox.glob("*/manifest.json")).read_text())["attachments"][0]["filename"], "task.md")
            state.close()

    def test_download_failure_publishes_no_unit_or_dedupe_record(self):
        import tempfile
        full = message(); full.update({"id": "gmail-2", "threadId": "thread", "internalDate": "1"})
        full["payload"]["parts"] = [{"filename": "task.md", "body": {"attachmentId": "a"}}]
        with tempfile.TemporaryDirectory() as tmp:
            paths, state = Paths(Path(tmp)), State(Paths(Path(tmp)))
            with self.assertRaisesRegex(RuntimeError, "download failed"):
                receive_message(Gmail(full, fail=True), paths, state, {"id": "gmail-2"})
            self.assertIsNone(state.get("gmail-2")); self.assertEqual(list(paths.inbox.iterdir()), [])
            state.close()

    def test_git_operations_fail_closed_outside_chat_branch(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "refusing Git operation"):
                assert_chat_repo(Paths(Path(tmp)))

    def test_git_environment_drops_broken_proxy_variables(self):
        with patch.dict("os.environ", {"HTTP_PROXY": "http://127.0.0.1:9", "GIT_HTTPS_PROXY": "http://127.0.0.1:9"}, clear=False):
            environment = git_environment()
        self.assertNotIn("HTTP_PROXY", environment)
        self.assertNotIn("GIT_HTTPS_PROXY", environment)
