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


def test_work_starts_courier_with_builtin_request(monkeypatch, tmp_path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    seen = {}
    monkeypatch.setattr(flow, "branch", lambda _root: "sandbox")
    monkeypatch.setattr(flow, "load_state", lambda _root, required=False: {})
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path)

    def fake_start(_root, args):
        seen["mode"] = args.mode
        seen["token"] = args.work_request_token
        seen["message"] = Path(args.message_file).read_text(encoding="utf-8")

    monkeypatch.setattr(flow, "command_start", fake_start)

    flow.command_work(tmp_path, SimpleNamespace())

    assert seen["mode"] == "courier"
    assert "next concrete GenericChess work order" in seen["message"]
    assert f"WORK_SESSION_ID={seen['token']}" in seen["message"]


def test_work_uses_a_new_idempotency_token_for_a_new_finished_session(
    monkeypatch, tmp_path
):
    tokens = iter(("first-session", "second-session"))
    started = []
    monkeypatch.setattr(flow, "branch", lambda _root: "sandbox")
    monkeypatch.setattr(flow, "load_state", lambda _root, required=False: {"active": False})
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path)
    monkeypatch.setattr(flow.uuid, "uuid4", lambda: SimpleNamespace(hex=next(tokens)))
    monkeypatch.setattr(
        flow, "command_start", lambda _root, args: started.append(args.work_request_token)
    )

    flow.command_work(tmp_path, SimpleNamespace())
    flow.command_work(tmp_path, SimpleNamespace())

    assert started == ["first-session", "second-session"]


def test_work_resumes_the_same_active_request(monkeypatch, tmp_path):
    state = {
        "active": True,
        "mode": "courier",
        "active_request_directory": r"C:\outbox\same-request",
    }
    called = []
    monkeypatch.setattr(flow, "branch", lambda _root: "sandbox")
    monkeypatch.setattr(flow, "load_state", lambda _root, required=False: state)
    monkeypatch.setattr(flow, "active_supervisor_hold", lambda _root: None)
    monkeypatch.setattr(flow, "command_recover", lambda root, args: called.append((root, args)))

    marker = SimpleNamespace()
    flow.command_work(tmp_path, marker)

    assert called == [(tmp_path, marker)]


def test_work_redisplays_the_current_order_without_new_courier_request(
    monkeypatch, tmp_path, capsys
):
    response = tmp_path / "response.txt"
    response.write_text("Do the bounded task.\n", encoding="utf-8")
    state = {
        "active": True,
        "mode": "courier",
        "active_request_directory": None,
        "work_request_token": "same-session-token",
        "last_response_path": str(response),
    }
    monkeypatch.setattr(flow, "branch", lambda _root: "sandbox")
    monkeypatch.setattr(flow, "load_state", lambda _root, required=False: state)
    monkeypatch.setattr(flow, "active_supervisor_hold", lambda _root: None)
    monkeypatch.setattr(
        flow,
        "command_start",
        lambda *_args: pytest.fail("an active work order must not create another request"),
    )

    flow.command_work(tmp_path, SimpleNamespace())

    output = capsys.readouterr().out
    assert "Do the bounded task." in output
    assert "NEXT_ACTION=execute this work order" in output


def test_work_recovers_session_saved_before_request_directory(monkeypatch, tmp_path):
    state = {
        "active": True,
        "mode": "courier",
        "active_request_directory": None,
        "work_request_token": "same-session-token",
    }
    seen = {}
    monkeypatch.setattr(flow, "branch", lambda _root: "sandbox")
    monkeypatch.setattr(flow, "load_state", lambda _root, required=False: state)
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path)

    def fake_dispatch(root, current_state, source, purpose):
        seen.update(
            root=root,
            state=current_state,
            message=source.read_text(encoding="utf-8"),
            purpose=purpose,
        )

    monkeypatch.setattr(flow, "dispatch_message", fake_dispatch)

    flow.command_work(tmp_path, SimpleNamespace())

    assert seen["root"] == tmp_path
    assert seen["state"] is state
    assert seen["purpose"] == "start"
    assert "next concrete GenericChess work order" in seen["message"]
    assert "WORK_SESSION_ID=same-session-token" in seen["message"]


def test_work_does_not_probe_courier_during_local_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(flow, "branch", lambda _root: "sandbox")
    monkeypatch.setattr(
        flow,
        "load_state",
        lambda _root, required=False: {"active": True, "mode": "local"},
    )
    monkeypatch.setattr(
        flow,
        "courier_capabilities",
        lambda _root: pytest.fail("work must not probe Courier during Local mode"),
    )

    with pytest.raises(flow.FlowError, match="Local mode session is active"):
        flow.command_work(tmp_path, SimpleNamespace())


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
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)

    def fake_courier(_root, *args, **kwargs):
        called.append((args, kwargs))
        if args[0] == "courier_status":
            return {"event": "courier_status", "ok": True, "state": "queue_recovery_required"}
        if args[0] == "courier_capture_latest":
            return {
                "event": "courier_capture_latest_empty", "ok": True,
                "latest_user_turn_found": True,
            }
        return {"event": "queue_recovery_required", "ok": False}

    monkeypatch.setattr(flow, "courier", fake_courier)
    monkeypatch.setattr(flow, "create_escalation", lambda *_args, **_kwargs: None)

    flow.command_resume(tmp_path, SimpleNamespace())

    assert [entry[0][0] for entry in called] == [
        "courier_status", "courier_capture_latest", "courier_recover"
    ]


def test_recover_uses_single_evidence_retry_when_probe_finds_no_request(monkeypatch, tmp_path):
    state = {"active": True, "mode": "courier", "active_request_directory": "request", "recovery_attempts": 0}
    calls = []
    monkeypatch.setattr(flow, "load_state", lambda _root, required=True: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setattr(flow, "create_escalation", lambda *_args, **_kwargs: calls.append("escalate"))

    def fake_courier(_root, operation, *_args, **_kwargs):
        calls.append(operation)
        if operation == "courier_status":
            return {"event": operation, "ok": True, "state": "queue_recovery_required"}
        if operation == "courier_capture_latest":
            return {"event": "courier_capture_latest_empty", "ok": True,
                    "latest_user_turn_found": False, "captured_at": 1.0}
        return {"event": "queue_recovery_required", "ok": False}

    monkeypatch.setattr(flow, "courier", fake_courier)
    flow.command_recover(tmp_path, SimpleNamespace(worker_thread_id="worker"))

    assert calls == ["courier_status", "courier_capture_latest", "courier_retry_once", "escalate"]
    assert state["recovery_attempts"] == 1
    assert state.get("chat_control", {}).get("GENERICCHESS_STATUS") != "BLOCKED"


def test_recover_imports_matching_reply_without_retry(monkeypatch, tmp_path):
    response = tmp_path / "response.txt"
    response.write_text(
        "Continue safely.\nWORK_ORDER_ID=F24B\nGENERICCHESS_STATUS=CONTINUE\n"
        "GENERICCHESS_CANDIDATE_SHA=NONE\nGENERICCHESS_PROMOTION=HOLD\n",
        encoding="utf-8",
    )
    state = {"active": True, "mode": "courier", "active_request_directory": "request"}
    saved = []
    operations = []
    monkeypatch.setattr(flow, "load_state", lambda _root, required=True: state)
    monkeypatch.setattr(flow, "save_state", lambda _root, value: saved.append(dict(value)))

    def fake_courier(_root, operation, *_args, **_kwargs):
        operations.append(operation)
        if operation == "courier_status":
            return {"event": operation, "ok": True}
        return {"event": "courier_latest_response_captured", "ok": True,
                "request_match": True, "response_path": str(response)}

    monkeypatch.setattr(flow, "courier", fake_courier)
    flow.command_recover(tmp_path, SimpleNamespace(worker_thread_id="worker"))

    assert operations == ["courier_status", "courier_capture_latest"]
    assert state["last_work_order_id"] == "F24B"
    assert state["recovery_state"] == "RECOVERED"


def test_escalation_is_idempotent_and_records_thread_identity(monkeypatch, tmp_path):
    sandbox = tmp_path / "sandbox"
    master = tmp_path / "master"
    sandbox.mkdir()
    master.mkdir()
    request = tmp_path / "request"
    request.mkdir()
    (request / "receipt.json").write_text("{}", encoding="utf-8")
    (request / "events.jsonl").write_text("{}\n", encoding="utf-8")
    state = {"active": True, "mode": "courier", "active_request_directory": str(request),
             "last_published_sha": "a" * 40, "last_probe": {"request_match": False}}
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: tmp_path / "runtime")
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": master, "sandbox": sandbox})
    monkeypatch.setattr(flow, "sha", lambda path, ref="HEAD": "b" * 40 if path == master else "a" * 40)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)

    first = flow.create_escalation(tmp_path, state, reason="transport", worker_thread_id="worker")
    second = flow.create_escalation(tmp_path, state, reason="transport again", worker_thread_id="other")

    assert first["escalation_id"] == second["escalation_id"]
    assert second["worker_thread_id"] == "worker"
    assert len(list((tmp_path / "runtime" / "escalations").glob("*/dossier.json"))) == 1


def test_pending_diagnostic_and_resolution_return_to_original_worker(monkeypatch, tmp_path, capsys):
    runtime = tmp_path / "runtime"
    directory = runtime / "escalations" / ("a" * 20)
    directory.mkdir(parents=True)
    dossier = {"escalation_id": "a" * 20, "worker_thread_id": "worker-1",
               "worker_host_id": "local", "status": "PENDING"}
    (directory / "dossier.json").write_text(json.dumps(dossier), encoding="utf-8")
    (runtime / "supervisor.json").write_text(json.dumps({
        "supervisor_thread_id": "supervisor-1"}), encoding="utf-8")
    state = {"active": True, "mode": "courier", "recovery_timeline": []}
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)
    monkeypatch.setattr(flow, "load_state", lambda _root, required=True: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setenv("CODEX_THREAD_ID", "supervisor-1")

    flow.command_supervisor_pending(tmp_path, SimpleNamespace())
    assert json.loads(capsys.readouterr().out)["pending"][0]["worker_thread_id"] == "worker-1"
    flow.command_supervisor_claim(tmp_path, SimpleNamespace(escalation_id="a" * 20))
    capsys.readouterr()
    flow.command_supervisor_resolve(
        tmp_path,
        SimpleNamespace(escalation_id="a" * 20, action="RESUME_WORKER", detail_file=None),
    )
    output = capsys.readouterr().out
    resolution = json.loads((directory / "resolution.json").read_text(encoding="utf-8"))
    assert "WORKER_THREAD_ID=worker-1" in output
    assert len(resolution["resolution_sha256"]) == 64
    assert state["recovery_state"] == "RECOVERED"


def test_recovery_response_cannot_approve_promotion(monkeypatch, tmp_path):
    candidate = "c" * 40
    state = {"active": True, "mode": "courier", "last_response_source": "read_only_recover",
             "tested_shas": {candidate: ["test"]}, "chat_control": {
                 "GENERICCHESS_PROMOTION": "APPROVE", "GENERICCHESS_CANDIDATE_SHA": candidate}}
    master, sandbox = tmp_path / "master", tmp_path / "sandbox"
    master.mkdir(); sandbox.mkdir()
    monkeypatch.setattr(flow, "load_state", lambda _root: state)
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": master, "sandbox": sandbox})
    monkeypatch.setattr(flow, "require_clean", lambda _root: None)
    monkeypatch.setattr(flow, "require_synced", lambda *_args: None)
    monkeypatch.setattr(flow, "sha", lambda path, ref="HEAD": candidate if path == sandbox else "a" * 40)
    monkeypatch.setattr(flow, "git_ok", lambda *_args: True)

    with pytest.raises(flow.FlowError, match="cannot implicitly authorize promotion"):
        flow.command_promote(tmp_path, SimpleNamespace(candidate=candidate))


def test_escalation_freezes_worker_repository_commands(monkeypatch, tmp_path):
    monkeypatch.setattr(flow, "load_state", lambda _root, required=True: {
        "active": True, "mode": "courier", "recovery_state": "ESCALATED"})
    monkeypatch.setattr(flow, "branch", lambda _root: "sandbox")
    with pytest.raises(flow.FlowError, match="writes are frozen"):
        flow.command_publish(tmp_path, SimpleNamespace(tests=[]))


def test_supervisor_hold_is_authorized_idempotent_and_hashed_on_release(
        monkeypatch, tmp_path, capsys):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "supervisor.json").write_text(json.dumps({
        "schema": "generic-chess-supervisor-v1",
        "supervisor_thread_id": "supervisor-1",
        "supervisor_host_id": "local",
        "worker_thread_id": "worker-1",
        "worker_host_id": "local",
    }), encoding="utf-8")
    reason = tmp_path / "reason.md"
    reason.write_text("The worker is about to publish outside the work order.", encoding="utf-8")
    detail = tmp_path / "release.md"
    detail.write_text("Chat revised the order and the worker acknowledged it.", encoding="utf-8")
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)
    monkeypatch.setenv("CODEX_THREAD_ID", "supervisor-1")

    args = SimpleNamespace(reason_file=str(reason), worker_thread_id=None)
    flow.command_supervisor_hold(tmp_path, args)
    first = json.loads(capsys.readouterr().out)
    flow.command_supervisor_hold(tmp_path, args)
    second = json.loads(capsys.readouterr().out)

    assert first["hold_id"] == second["hold_id"]
    assert flow.active_supervisor_hold(tmp_path)["worker_thread_id"] == "worker-1"
    with pytest.raises(flow.FlowError, match="blocks worker writes"):
        flow.require_no_supervisor_hold(tmp_path)

    flow.command_supervisor_release(tmp_path, SimpleNamespace(
        hold_id=first["hold_id"], detail_file=str(detail)))
    released = json.loads(capsys.readouterr().out)
    assert released["status"] == "RELEASED"
    assert len(released["resolution_sha256"]) == 64
    assert flow.active_supervisor_hold(tmp_path) is None


def test_unregistered_task_cannot_hold_or_release(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "supervisor.json").write_text(json.dumps({
        "supervisor_thread_id": "supervisor-1",
        "worker_thread_id": "worker-1",
    }), encoding="utf-8")
    reason = tmp_path / "reason.md"
    reason.write_text("urgent", encoding="utf-8")
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)
    monkeypatch.setenv("CODEX_THREAD_ID", "worker-1")

    with pytest.raises(flow.FlowError, match="registered Supervisor"):
        flow.command_supervisor_hold(tmp_path, SimpleNamespace(
            reason_file=str(reason), worker_thread_id=None))


def test_hold_status_check_write_returns_nonzero(monkeypatch, tmp_path, capsys):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "active-supervisor-hold.json").write_text(json.dumps({
        "schema": "generic-chess-supervisor-hold-v1",
        "hold_id": "a" * 20,
        "status": "ACTIVE",
    }), encoding="utf-8")
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)

    assert flow.command_supervisor_hold_status(
        tmp_path, SimpleNamespace(check_write=True)) == 3
    assert json.loads(capsys.readouterr().out)["active"] is True


def test_user_superseded_resolution_retires_request_without_deleting_evidence(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    directory = runtime / "escalations" / ("b" * 20)
    request = tmp_path / "immutable-request"
    request.mkdir()
    directory.mkdir(parents=True)
    (directory / "dossier.json").write_text(json.dumps({
        "escalation_id": "b" * 20, "worker_thread_id": "worker"}), encoding="utf-8")
    (directory / "claim.json").write_text(json.dumps({
        "supervisor_thread_id": "supervisor"}), encoding="utf-8")
    state = {"active": True, "mode": "courier", "active_request_directory": str(request),
             "last_response_path": "old-response", "work_order_active": True,
             "recovery_timeline": []}
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)
    monkeypatch.setattr(flow, "load_state", lambda _root, required=True: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setenv("CODEX_THREAD_ID", "supervisor")

    flow.command_supervisor_resolve(tmp_path, SimpleNamespace(
        escalation_id="b" * 20, action="USER_SUPERSEDED_REQUEST", detail_file=None))

    assert state["retired_request_directory"] == str(request)
    assert state["active_request_directory"] is None
    assert state["last_response_path"] is None
    assert request.is_dir()


def test_large_chat_report_requires_published_git_reference(monkeypatch, tmp_path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    external = tmp_path / "large-report.json"
    external.write_text("x" * (flow.INLINE_CHAT_REFERENCE_THRESHOLD + 1), encoding="utf-8")
    monkeypatch.setattr(flow, "sandbox_root", lambda _root: sandbox)
    with pytest.raises(flow.FlowError, match="committed inside the sandbox"):
        flow.chat_message_body(tmp_path, external)


def test_large_published_report_becomes_compact_sha_bound_reference(monkeypatch, tmp_path):
    sandbox = tmp_path / "sandbox"
    report = sandbox / "docs" / "audit.json"
    report.parent.mkdir(parents=True)
    report.write_text("x" * (flow.INLINE_CHAT_REFERENCE_THRESHOLD + 1), encoding="utf-8")
    monkeypatch.setattr(flow, "sandbox_root", lambda _root: sandbox)
    monkeypatch.setattr(flow, "git_ok", lambda *_args: True)
    monkeypatch.setattr(flow, "sha", lambda *_args: "a" * 40)
    monkeypatch.setattr(flow, "git", lambda _root, *args, **_kwargs:
                        "https://example.invalid/repo.git" if args[:3] == ("remote", "get-url", "origin") else "")

    body = flow.chat_message_body(tmp_path, report)

    assert len(body.encode("utf-8")) < flow.INLINE_CHAT_REFERENCE_THRESHOLD
    assert "COMMIT=" + "a" * 40 in body
    assert "PATH=docs/audit.json" in body


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
    monkeypatch.setattr(flow, "active_supervisor_hold", lambda _root: None)

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
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path / "runtime")
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


def test_portable_closeout_is_normalized_and_rejects_local_or_chat_data(tmp_path):
    report = tmp_path / "closeout.md"
    report.write_text("F41 complete at d50aff9.\n", encoding="utf-8")
    text, digest = flow._portable_closeout(str(report))
    assert text == "F41 complete at d50aff9.\n"
    assert len(digest) == 64

    report.write_text(r"local C:\Users\person\secret", encoding="utf-8")
    with pytest.raises(flow.FlowError, match="non-portable"):
        flow._portable_closeout(str(report))
    report.write_text("https://chatgpt.com/c/private", encoding="utf-8")
    with pytest.raises(flow.FlowError, match="non-portable"):
        flow._portable_closeout(str(report))


def test_remote_owner_mismatch_blocks_mutation(monkeypatch, tmp_path):
    (tmp_path / ".workflow-state-enabled").write_text("v1", encoding="utf-8")
    repo = tmp_path / "state"
    repo.mkdir()
    (repo / "handoff.json").write_text(json.dumps({
        "schema": flow.HANDOFF_SCHEMA,
        "generation": 2,
        "state": "CLAIMED",
        "owner": {"host_id": "other", "machine_id": "other-id"},
    }), encoding="utf-8")
    monkeypatch.setattr(flow, "load_machine", lambda required=True: {
        "host_id": "primary", "machine_id": "primary-id"})
    monkeypatch.setattr(flow, "ensure_handoff_repo", lambda _root: repo)

    with pytest.raises(flow.FlowError, match="does not own"):
        flow.require_handoff_owner(tmp_path)


def test_release_capsule_preserves_business_candidate_without_paths(monkeypatch, tmp_path):
    master = tmp_path / "master"; master.mkdir()
    sandbox = tmp_path / "sandbox"; sandbox.mkdir()
    report = tmp_path / "report.md"; report.write_text("F41 closeout\n", encoding="utf-8")
    state = {
        "active": True, "mode": "courier", "active_request_directory": None,
        "recovery_state": "RECOVERED", "work_order_active": True,
        "last_work_order_id": "F41", "last_published_sha": "d" * 40,
        "tested_shas": {"d" * 40: ["tests/test_f41.py"]},
        "chat_control": {"GENERICCHESS_STATUS": "CONTINUE"},
        "work_request_token": "token",
    }
    repo = tmp_path / "state"; repo.mkdir()
    captured = {}
    monkeypatch.setattr(flow, "require_handoff_owner", lambda _root: None)
    monkeypatch.setattr(flow, "active_state", lambda _root: state)
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": master, "sandbox": sandbox})
    monkeypatch.setattr(flow, "require_clean", lambda _root: None)
    monkeypatch.setattr(flow, "require_synced", lambda *_args: None)
    monkeypatch.setattr(flow, "courier_quiescence", lambda _root: {"quiescent": True})
    monkeypatch.setattr(flow, "_capsule_repository_state", lambda _root: (
        {"repository": "https://example/generic", "master_sha": "a" * 40,
         "sandbox_sha": "f" * 40},
        {"repository": "https://example/courier", "branch": "sandbox",
         "sha": "c" * 40, "build_id": "build"},
    ))
    monkeypatch.setattr(flow, "ensure_handoff_repo", lambda _root: repo)
    monkeypatch.setattr(flow, "load_handoff", lambda _repo: {
        "schema": flow.HANDOFF_SCHEMA, "generation": 4, "state": "CLAIMED"})
    monkeypatch.setattr(flow, "commit_handoff", lambda _root, _repo, capsule, **kwargs:
                        captured.update(capsule=capsule, closeout=kwargs["closeout"]))
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)

    flow.command_handoff_release(
        tmp_path, SimpleNamespace(to="standby", closeout_file=str(report)))
    capsule = captured["capsule"]
    assert capsule["state"] == "RELEASED"
    assert capsule["generation"] == 5
    assert capsule["generic"]["business_candidate_sha"] == "d" * 40
    assert capsule["workflow"]["resume_stage"] == "SUBMIT_CLOSEOUT"
    serialized = json.dumps(capsule)
    assert "C:\\" not in serialized and "THREAD" not in serialized


def test_courier_non_quiescent_state_blocks_handoff(monkeypatch, tmp_path):
    monkeypatch.setattr(flow, "courier", lambda *_args, **_kwargs: {
        "event": "courier_quiescence", "ok": False, "quiescent": False,
        "queue_entries": [{"request_id": "P-1"}],
    })
    with pytest.raises(flow.FlowError, match="not quiescent"):
        flow.courier_quiescence(tmp_path)


def test_claim_restores_exact_closeout_stage_after_remote_claim(monkeypatch, tmp_path):
    master = tmp_path / "master"; master.mkdir()
    sandbox = tmp_path / "sandbox"; sandbox.mkdir()
    courier = tmp_path / "courier"; courier.mkdir()
    repo = tmp_path / "state"; repo.mkdir()
    closeout = "F41 closeout\n"
    (repo / "closeout.md").write_text(closeout, encoding="utf-8")
    capsule = {
        "schema": flow.HANDOFF_SCHEMA, "generation": 6, "state": "RELEASED",
        "owner": None, "target_host_id": "standby",
        "generic": {"master_sha": "a" * 40, "sandbox_sha": "f" * 40,
                    "business_candidate_sha": "d" * 40},
        "courier": {"sha": "c" * 40},
        "workflow": {
            "mode": "courier", "resume_stage": "SUBMIT_CLOSEOUT",
            "work_order_active": True, "last_work_order_id": "F41",
            "chat_control": {"GENERICCHESS_STATUS": "CONTINUE"},
            "tested_candidate_targets": ["tests/test_f41.py"],
            "closeout_sha256": __import__("hashlib").sha256(closeout.encode()).hexdigest(),
        },
    }
    saved = {}
    monkeypatch.setattr(flow, "save_machine", lambda host_id: {
        "host_id": host_id, "machine_id": "standby-id"})
    monkeypatch.setattr(flow, "ensure_handoff_repo", lambda _root: repo)
    monkeypatch.setattr(flow, "load_handoff", lambda _repo: capsule)
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": master, "sandbox": sandbox})
    monkeypatch.setattr(flow, "require_clean", lambda _root: None)
    monkeypatch.setattr(flow, "require_synced", lambda *_args: None)
    monkeypatch.setattr(flow, "sha", lambda path, ref="HEAD": {
        master: "a" * 40, sandbox: "f" * 40, courier: "c" * 40}[path])
    monkeypatch.setattr(flow, "courier_repository", lambda _root: courier)
    monkeypatch.setattr(flow, "fetch", lambda *_args: None)
    monkeypatch.setattr(flow, "synced", lambda *_args: True)
    monkeypatch.setattr(flow, "courier_capabilities", lambda _root: {
        "projects": [flow.PROJECT_ID]})
    monkeypatch.setattr(flow, "courier_quiescence", lambda _root: {"quiescent": True})
    monkeypatch.setattr(flow, "commit_handoff", lambda *_args, **_kwargs: None)
    runtime = tmp_path / "runtime"; runtime.mkdir()
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: runtime)
    monkeypatch.setattr(flow, "save_state", lambda _root, value: saved.update(value))

    flow.command_handoff_claim(tmp_path, SimpleNamespace(host_id="standby"))
    assert saved["last_work_order_id"] == "F41"
    assert saved["business_candidate_sha"] == "d" * 40
    assert saved["resume_stage"] == "SUBMIT_CLOSEOUT"
    assert Path(saved["handoff_closeout_path"]).read_text(encoding="utf-8") == closeout


def test_handoff_closeout_accepts_legacy_double_cr_checkout(tmp_path):
    path = tmp_path / "closeout.md"
    expected_text = "# Closeout\r\n\r\n- result\r\n"
    path.write_bytes(expected_text.replace("\r\n", "\r\r\n").encode("utf-8"))
    expected = __import__("hashlib").sha256(expected_text.encode("utf-8")).hexdigest()

    assert flow._validated_handoff_closeout(path, expected) == expected_text


def test_portable_closeout_uses_lf_on_every_platform(tmp_path):
    path = tmp_path / "closeout.md"
    path.write_bytes(b"# Closeout\r\n\r\n- result\r\n")

    text, digest = flow._portable_closeout(str(path))

    assert text == "# Closeout\n\n- result\n"
    assert digest == __import__("hashlib").sha256(text.encode("utf-8")).hexdigest()


def test_pre_push_hook_allows_only_flow_owned_fast_forward_state_push():
    hook = (ROOT / ".githooks" / "pre-push").read_text(encoding="utf-8")
    assert "refs/heads/workflow-state" in hook
    assert 'GENERIC_CHESS_FLOW_PUSH:-}' in hook
    assert "GENERIC_CHESS_NON_FAST_FORWARD_PUSH_FORBIDDEN" in hook
    assert "GENERIC_CHESS_SUPERVISOR_HOLD_BLOCKS_PUSH" in hook


def test_pre_commit_hook_blocks_active_supervisor_hold():
    hook = (ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    assert "active-supervisor-hold.json" in hook
    assert "GENERIC_CHESS_SUPERVISOR_HOLD_BLOCKS_COMMIT" in hook


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
