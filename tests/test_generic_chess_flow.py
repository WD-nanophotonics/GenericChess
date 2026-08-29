from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generic_chess_flow", ROOT / "tools" / "generic_chess_flow.py"
)
assert SPEC and SPEC.loader
flow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flow)


def test_chat_control_footer_is_explicit_and_last_value_wins():
    text = """Work order body.
GENERICCHESS_STATUS=CONTINUE
GENERICCHESS_PROMOTION=HOLD
IGNORED=value
GENERICCHESS_STATUS=COMPLETE
GENERICCHESS_CANDIDATE_SHA=0123456789abcdef0123456789abcdef01234567
"""
    assert flow.parse_control_footer(text) == {
        "GENERICCHESS_STATUS": "COMPLETE",
        "GENERICCHESS_PROMOTION": "HOLD",
        "GENERICCHESS_CANDIDATE_SHA": "0123456789abcdef0123456789abcdef01234567",
    }


def test_local_start_never_requires_courier(monkeypatch, tmp_path):
    master = tmp_path / "master"
    sandbox = tmp_path / "sandbox"
    master.mkdir()
    sandbox.mkdir()
    monkeypatch.setattr(flow, "install_hooks", lambda _root: None)
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": master, "sandbox": sandbox})
    monkeypatch.setattr(flow, "require_clean", lambda _root: None)
    monkeypatch.setattr(flow, "require_synced", lambda _root, _branch: None)
    monkeypatch.setattr(flow, "sha", lambda path, ref="HEAD": "a" * 40 if path == master else "b" * 40)
    saved = {}
    monkeypatch.setattr(flow, "save_state", lambda _root, state: saved.update(state))
    monkeypatch.setattr(flow, "load_state", lambda _root, required=False: {})
    monkeypatch.setattr(
        flow, "courier_capabilities",
        lambda _root: pytest.fail("local mode must not inspect Courier"),
    )

    flow.command_start(tmp_path, SimpleNamespace(mode="local", message_file=None))

    assert saved["active"] is True
    assert saved["mode"] == "local"


def test_local_status_does_not_inspect_courier(monkeypatch, tmp_path, capsys):
    master = tmp_path / "master"
    sandbox = tmp_path / "sandbox"
    master.mkdir()
    sandbox.mkdir()
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": master, "sandbox": sandbox})
    monkeypatch.setattr(flow, "sha", lambda _path, ref="HEAD": "a" * 40)
    monkeypatch.setattr(flow, "clean", lambda _root: True)
    monkeypatch.setattr(flow, "git", lambda *_args, **_kwargs: "exists")
    monkeypatch.setattr(flow, "git_ok", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        flow,
        "load_state",
        lambda _root, required=False: {"active": True, "mode": "local"},
    )
    monkeypatch.setattr(
        flow,
        "courier_capabilities",
        lambda _root: pytest.fail("local status must not inspect Courier"),
    )

    flow.command_status(tmp_path, SimpleNamespace())

    payload = json.loads(capsys.readouterr().out)
    assert payload["courier"] == {
        "checked": False,
        "reason": "skipped_due_to_local_mode",
    }


def test_courier_events_are_streamed_in_order(monkeypatch, tmp_path, capsys):
    events = [
        '{"event":"queue_waiting","ok":true,"queue_position":2}\n',
        '{"event":"queue_turn_acquired","ok":true}\n',
        '{"event":"response_received","ok":true,"response_path":"response.txt"}\n',
    ]

    class FakeProcess:
        def __init__(self):
            self.stdout = iter(events)

        @staticmethod
        def wait():
            return 0

    monkeypatch.setattr(flow, "courier_launcher", lambda _root: tmp_path / "chat-courier.cmd")
    monkeypatch.setattr(flow.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())

    flow.courier(tmp_path, "courier_capabilities")
    assert capsys.readouterr().out == ""

    final = flow.courier(tmp_path, "courier_dispatch", "request", stream=True)

    assert [json.loads(line)["event"] for line in capsys.readouterr().out.splitlines()] == [
        "queue_waiting",
        "queue_turn_acquired",
        "response_received",
    ]
    assert final["event"] == "response_received"


def test_resume_reuses_the_saved_request_directory(monkeypatch, tmp_path):
    state = {
        "active": True,
        "mode": "courier",
        "active_request_directory": r"C:\outbox\same-request",
    }
    called = []
    monkeypatch.setattr(flow, "load_state", lambda _root: state)
    monkeypatch.setattr(
        flow,
        "courier",
        lambda _root, *args, **kwargs: called.append((args, kwargs))
        or {"event": "queue_duplicate_runner", "ok": True},
    )

    flow.command_resume(tmp_path, SimpleNamespace())

    assert called == [
        (("courier_dispatch", r"C:\outbox\same-request"), {"stream": True})
    ]


def test_heavy_uses_below_normal_priority_and_returns_child_code(monkeypatch, tmp_path):
    seen = {}

    class FakeProcess:
        @staticmethod
        def wait():
            return 7

    class FakeLock:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(flow, "active_state", lambda _root: {"active": True, "mode": "local"})
    monkeypatch.setattr(flow, "branch", lambda _root: "sandbox")
    monkeypatch.setattr(flow, "heavy_lock", lambda _root: FakeLock())

    def fake_popen(argv, **kwargs):
        seen.update({"argv": argv, **kwargs})
        return FakeProcess()

    monkeypatch.setattr(flow.subprocess, "Popen", fake_popen)
    code = flow.command_heavy(tmp_path, SimpleNamespace(argv=["--", "python", "work.py"]))

    assert code == 7
    assert seen["argv"] == ["python", "work.py"]
    assert seen["cwd"] == tmp_path
    assert seen["creationflags"] == getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)


def test_publish_tests_use_the_same_low_priority_lock(monkeypatch, tmp_path):
    seen = {"locked": False}

    class FakeLock:
        def __enter__(self):
            seen["locked"] = True

        def __exit__(self, *_args):
            seen["locked"] = False

    def fake_run(argv, **kwargs):
        assert seen["locked"] is True
        seen["argv"] = argv
        seen["creationflags"] = kwargs["creationflags"]
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(flow, "python_for", lambda _root: "python")
    monkeypatch.setattr(flow, "heavy_lock", lambda _root: FakeLock())
    monkeypatch.setattr(flow, "run", fake_run)

    flow.run_tests(tmp_path, ["tests/test_session.py"])

    assert seen["argv"][-1] == "tests/test_session.py"
    assert seen["creationflags"] == getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)


@pytest.mark.skipif(flow.os.name != "nt", reason="the workflow lock is Windows-only")
def test_second_heavy_lock_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path)
    with flow.heavy_lock(tmp_path):
        with pytest.raises(flow.FlowError, match="already running"):
            with flow.heavy_lock(tmp_path):
                pass


def test_active_session_cannot_change_authority_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(
        flow, "load_state", lambda _root, required=False: {"active": True, "mode": "courier"}
    )
    with pytest.raises(flow.FlowError, match="cannot change authority mode"):
        flow.command_start(tmp_path, SimpleNamespace(mode="local", message_file=None))


def test_commands_reject_finished_session(monkeypatch, tmp_path):
    monkeypatch.setattr(
        flow, "load_state", lambda _root, required=True: {"active": False, "mode": "courier"}
    )
    with pytest.raises(flow.FlowError, match="no active"):
        flow.command_closeout(tmp_path, SimpleNamespace(report_file="unused.txt"))


def test_courier_promotion_requires_exact_approved_sha(monkeypatch, tmp_path):
    candidate = "c" * 40
    state = {
        "active": True,
        "mode": "courier",
        "tested_shas": {candidate: ["tests/test_session.py"]},
        "chat_control": {
            "GENERICCHESS_PROMOTION": "APPROVE",
            "GENERICCHESS_CANDIDATE_SHA": "d" * 40,
        },
    }
    master = tmp_path / "master"
    sandbox = tmp_path / "sandbox"
    master.mkdir()
    sandbox.mkdir()
    monkeypatch.setattr(flow, "load_state", lambda _root: state)
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": master, "sandbox": sandbox})
    monkeypatch.setattr(flow, "require_clean", lambda _root: None)
    monkeypatch.setattr(flow, "require_synced", lambda _root, _branch: None)
    monkeypatch.setattr(flow, "sha", lambda path, ref="HEAD": candidate if path == sandbox else "a" * 40)
    monkeypatch.setattr(flow, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))

    with pytest.raises(flow.FlowError, match="not bound"):
        flow.command_promote(tmp_path, SimpleNamespace(candidate=candidate))


def test_promotion_rejects_unpublished_or_untested_candidate(monkeypatch, tmp_path):
    candidate = "c" * 40
    master = tmp_path / "master"
    sandbox = tmp_path / "sandbox"
    master.mkdir()
    sandbox.mkdir()
    monkeypatch.setattr(
        flow,
        "load_state",
        lambda _root: {"active": True, "mode": "local", "tested_shas": {}},
    )
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": master, "sandbox": sandbox})
    monkeypatch.setattr(flow, "require_clean", lambda _root: None)
    monkeypatch.setattr(flow, "require_synced", lambda _root, _branch: None)
    monkeypatch.setattr(flow, "sha", lambda path, ref="HEAD": candidate if path == sandbox else "a" * 40)

    with pytest.raises(flow.FlowError, match="has not passed publish tests"):
        flow.command_promote(tmp_path, SimpleNamespace(candidate=candidate))
