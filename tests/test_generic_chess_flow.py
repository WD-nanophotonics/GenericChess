from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generic_chess_flow", ROOT / "tools" / "generic_chess_flow.py"
)
assert SPEC and SPEC.loader
flow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flow)


class _NoopContext:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _heavy_start_mocks(monkeypatch, tmp_path):
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path)
    monkeypatch.setattr(flow, "active_state", lambda _root: {"active": True})
    monkeypatch.setattr(flow, "require_worker_write_authority", lambda *_args: None)
    monkeypatch.setattr(flow, "require_no_supervisor_hold", lambda _root: None)
    monkeypatch.setattr(flow, "branch", lambda _root: "sandbox")


def _resource_path(tmp_path: Path) -> Path:
    path = tmp_path / "resource-envelope.json"
    path.write_text(json.dumps({
        "schema": flow.COMPUTE_ENVELOPE_SCHEMA,
        "envelope_id": "test-envelope",
        "logical_cpu_count": 2,
        "intended_cpu_lanes": 1,
        "expected_wall_minutes": 1,
        "hard_wall_minutes": 2,
        "expected_cpu_hours": 0.1,
        "hard_cpu_hours": 1,
        "arena_pairs": 1,
        "maximum_games": 1,
        "maximum_nodes": 100,
        "maximum_plies": 10,
        "maximum_concurrent_games": 1,
        "stage_count": 1,
    }), encoding="utf-8")
    return path


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


def test_repo_relative_path_accepts_relative_absolute_and_rejects_escape(tmp_path):
    inside = tmp_path / "nested" / "result.json"
    inside.parent.mkdir()
    inside.write_text("{}", encoding="utf-8")
    assert flow.repo_relative_path(tmp_path, "nested/result.json") == "nested/result.json"
    assert flow.repo_relative_path(tmp_path, inside) == "nested/result.json"
    with pytest.raises(flow.FlowError, match="outside"):
        flow.repo_relative_path(tmp_path, tmp_path.parent / "outside.json")


@pytest.mark.parametrize(
    ("footer", "expected"),
    [
        ("", {"GENERICCHESS_STATUS": "CONTINUE", "GENERICCHESS_CANDIDATE_SHA": "NONE", "GENERICCHESS_PROMOTION": "HOLD"}),
        ("GENERICCHESS_STATUS=COMPLETE\n", {"GENERICCHESS_STATUS": "COMPLETE", "GENERICCHESS_CANDIDATE_SHA": "NONE", "GENERICCHESS_PROMOTION": "HOLD"}),
        ("GENERICCHESS_STATUS=wat\n", {"GENERICCHESS_STATUS": "CONTINUE", "GENERICCHESS_CANDIDATE_SHA": "NONE", "GENERICCHESS_PROMOTION": "HOLD"}),
        ("GENERICCHESS_CANDIDATE_SHA=bad\n", {"GENERICCHESS_STATUS": "CONTINUE", "GENERICCHESS_CANDIDATE_SHA": "NONE", "GENERICCHESS_PROMOTION": "HOLD"}),
        ("GENERICCHESS_PROMOTION=wat\n", {"GENERICCHESS_STATUS": "CONTINUE", "GENERICCHESS_CANDIDATE_SHA": "NONE", "GENERICCHESS_PROMOTION": "HOLD"}),
    ],
)
def test_control_footer_missing_partial_and_invalid_values_normalize(footer, expected):
    control, warnings = flow.normalize_control_footer(footer)
    assert control == expected
    assert warnings


def test_control_footer_approve_without_candidate_is_downgraded():
    control, warnings = flow.normalize_control_footer(
        "GENERICCHESS_PROMOTION=APPROVE\n"
        "GENERICCHESS_STATUS=CONTINUE\n"
    )
    assert control["GENERICCHESS_PROMOTION"] == "HOLD"
    assert any("without a valid candidate" in warning for warning in warnings)


def test_local_supervisor_required_is_recorded_once_without_transport_recovery(
        monkeypatch, tmp_path):
    response = tmp_path / "response.txt"
    response.write_text(
        "LOCAL_SUPERVISOR_REQUIRED=true\nordinary result\n",
        encoding="utf-8",
    )
    state = {"active_request_id": "req-1", "recovery_timeline": []}
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path / "runtime")

    flow.update_response_state(tmp_path, state, {
        "event": "response_received", "response_path": str(response)})
    flow.update_response_state(tmp_path, state, {
        "event": "response_received", "response_path": str(response)})

    assert state["local_supervisor_required"] is True
    assert len(state["business_supervisor_notifications"]) == 1
    assert state["recovery_state"] == "IDLE"
    assert state["chat_control"]["GENERICCHESS_STATUS"] == "CONTINUE"


def test_response_console_output_survives_legacy_windows_encoding(
        monkeypatch, tmp_path, capsys):
    response = tmp_path / "response.txt"
    response.write_text("next → step\nGENERICCHESS_STATUS=CONTINUE\n"
                        "GENERICCHESS_CANDIDATE_SHA=NONE\n"
                        "GENERICCHESS_PROMOTION=HOLD\n", encoding="utf-8")
    state = {"recovery_timeline": []}
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    original = flow._console_safe
    monkeypatch.setattr(flow, "_console_safe", lambda text: original(text, "cp1252"))

    flow.update_response_state(tmp_path, state, {
        "event": "response_received", "response_path": str(response)})

    assert r"\u2192" in capsys.readouterr().out
    assert state["work_order_active"] is True


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
    assert "courier" not in payload
    assert payload["session"]["mode"] == "local"


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


def test_scoped_complete_requires_follow_on_work_contract():
    contract = (
        "A Chat `COMPLETE` closes the whole project only when the response explicitly "
        "says no further GenericChess work is needed."
    )
    normalized = lambda path: " ".join(path.read_text(encoding="utf-8").split())
    assert contract in normalized(ROOT / "AGENTS.md")
    assert "Policy and authority live only in `AGENTS.md`" in normalized(ROOT / "WORKFLOW.md")
    assert "A phase-level result continues to the next work order" in normalized(ROOT / "AGENTS.md")


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


def test_work_redisplay_survives_legacy_windows_encoding(monkeypatch, tmp_path, capsys):
    response = tmp_path / "response.txt"
    response.write_text("下一工单：保持 DEFER\n", encoding="utf-8")
    state = {"active": True, "mode": "courier", "active_request_directory": None,
             "last_response_path": str(response), "work_order_active": True}
    monkeypatch.setattr(flow, "branch", lambda _root: "sandbox")
    monkeypatch.setattr(flow, "load_state", lambda _root, required=False: state)
    monkeypatch.setattr(flow, "active_supervisor_hold", lambda _root: None)
    original = flow._console_safe
    monkeypatch.setattr(flow, "_console_safe", lambda text: original(text, "cp1252"))

    flow.command_work(tmp_path, SimpleNamespace())

    output = capsys.readouterr().out
    assert r"\u4e0b" in output
    assert "NEXT_ACTION=execute this work order" in output


def _followup_state(response: Path):
    return {
        "active": True,
        "mode": "courier",
        "active_request_directory": None,
        "recovery_state": "IDLE",
        "last_response_path": str(response),
        "last_response_sha256": hashlib.sha256(response.read_bytes()).hexdigest(),
    }


def test_followup_dispatches_short_delta_with_existing_session(monkeypatch, tmp_path):
    response = tmp_path / "response.txt"
    response.write_text("accepted\n", encoding="utf-8")
    message = tmp_path / "message.txt"
    message.write_text("V2 binding delta\n", encoding="utf-8")
    state = _followup_state(response)
    seen = {}
    monkeypatch.setattr(flow, "active_state", lambda _root: state)
    monkeypatch.setattr(flow, "require_worker_write_authority", lambda *_args: None)
    monkeypatch.setattr(flow, "require_no_supervisor_hold", lambda _root: None)
    monkeypatch.setattr(flow, "require_clean", lambda _root: None)
    monkeypatch.setattr(flow, "require_synced", lambda *_args: None)
    monkeypatch.setattr(flow, "_unresolved_escalation_ids", lambda _root: [])
    monkeypatch.setattr(flow, "dispatch_message", lambda root, current, source, purpose: seen.update(root=root, state=current, body=source.read_text(encoding="utf-8"), purpose=purpose))

    flow.command_followup(tmp_path, SimpleNamespace(message_file=str(message)))

    assert seen == {"root": tmp_path, "state": state, "body": "V2 binding delta\n", "purpose": "followup"}


def test_followup_parser_is_available():
    args = flow.parser().parse_args(["followup", "--message-file", "delta.txt"])
    assert args.command == "followup"
    assert args.message_file == "delta.txt"


@pytest.mark.parametrize(
    ("state_update", "error"),
    [
        ({"mode": "local"}, "courier mode"),
        ({"active_request_directory": "request"}, "request is unresolved"),
        ({"recovery_state": "ESCALATED"}, "recovery is unresolved"),
    ],
)
def test_followup_rejects_invalid_session_state(monkeypatch, tmp_path, state_update, error):
    response = tmp_path / "response.txt"
    response.write_text("accepted\n", encoding="utf-8")
    state = _followup_state(response)
    state.update(state_update)
    message = tmp_path / "message.txt"
    message.write_text("delta\n", encoding="utf-8")
    monkeypatch.setattr(flow, "active_state", lambda _root: state)
    monkeypatch.setattr(flow, "require_worker_write_authority", lambda *_args: None)
    monkeypatch.setattr(flow, "require_no_supervisor_hold", lambda _root: None)
    monkeypatch.setattr(flow, "_unresolved_escalation_ids", lambda _root: [])
    with pytest.raises(flow.FlowError, match=error):
        flow.command_followup(tmp_path, SimpleNamespace(message_file=str(message)))


def test_followup_rejects_unresolved_escalation_and_response_tamper(monkeypatch, tmp_path):
    response = tmp_path / "response.txt"
    response.write_text("accepted\n", encoding="utf-8")
    message = tmp_path / "message.txt"
    message.write_text("delta\n", encoding="utf-8")
    state = _followup_state(response)
    monkeypatch.setattr(flow, "active_state", lambda _root: state)
    monkeypatch.setattr(flow, "require_worker_write_authority", lambda *_args: None)
    monkeypatch.setattr(flow, "require_no_supervisor_hold", lambda _root: None)
    monkeypatch.setattr(flow, "_unresolved_escalation_ids", lambda _root: ["pending-id"])
    with pytest.raises(flow.FlowError, match="escalation is unresolved"):
        flow.command_followup(tmp_path, SimpleNamespace(message_file=str(message)))

    monkeypatch.setattr(flow, "_unresolved_escalation_ids", lambda _root: [])
    response.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(flow.FlowError, match="response hash mismatch"):
        flow.command_followup(tmp_path, SimpleNamespace(message_file=str(message)))


def test_followup_rejects_long_inline_body(monkeypatch, tmp_path):
    response = tmp_path / "response.txt"
    response.write_text("accepted\n", encoding="utf-8")
    message = tmp_path / "message.txt"
    message.write_text("x" * (flow.INLINE_CHAT_REFERENCE_THRESHOLD + 1), encoding="utf-8")
    state = _followup_state(response)
    monkeypatch.setattr(flow, "active_state", lambda _root: state)
    monkeypatch.setattr(flow, "require_worker_write_authority", lambda *_args: None)
    monkeypatch.setattr(flow, "require_no_supervisor_hold", lambda _root: None)
    monkeypatch.setattr(flow, "_unresolved_escalation_ids", lambda _root: [])
    with pytest.raises(flow.FlowError, match="short inline"):
        flow.command_followup(tmp_path, SimpleNamespace(message_file=str(message)))


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


def test_recover_waits_for_matching_live_owner_without_escalation(monkeypatch, tmp_path, capsys):
    request_id = "GENERICCHESS-20260911-144204-d1f0a876"
    state = {
        "active": True,
        "mode": "courier",
        "active_request_directory": str(tmp_path / request_id),
        "active_request_id": request_id,
        "active_request_fingerprint": "f" * 64,
        "recovery_attempts": 5,
    }
    calls = []
    monkeypatch.setattr(flow, "active_state", lambda _root: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setattr(flow, "_same_process", lambda pid, created: False)
    monkeypatch.setattr(flow, "create_escalation", lambda *_args, **_kwargs: pytest.fail("matching live owner must not escalate"))

    def fake_courier(_root, operation, *_args, **_kwargs):
        calls.append(operation)
        if operation == "courier_status":
            return {"event": operation, "ok": True, "state": "waiting_for_response"}
        return {
            "event": "courier_capture_latest_busy",
            "ok": False,
            "project_id": "GENERICCHESS",
            "request_id": request_id,
            "fingerprint": "f" * 64,
            "live_owner_found": True,
            "submission_count": 1,
            "owner_pid": 123,
            "owner_created_at": 1.0,
        }

    monkeypatch.setattr(flow, "courier", fake_courier)
    flow.command_recover(tmp_path, SimpleNamespace(worker_thread_id="worker"))

    assert calls == ["courier_status", "courier_capture_latest"]
    assert state["recovery_attempts"] == 5
    assert state["recovery_state"] == "IDLE"
    assert "healthy_live_owner_waiting" in capsys.readouterr().out


def test_recover_escalates_unverifiable_busy_owner(monkeypatch, tmp_path):
    request_id = "GENERICCHESS-20260911-144204-d1f0a876"
    state = {
        "active": True,
        "mode": "courier",
        "active_request_directory": str(tmp_path / request_id),
        "active_request_id": request_id,
        "active_request_fingerprint": "f" * 64,
        "recovery_attempts": 5,
    }
    escalated = []
    monkeypatch.setattr(flow, "active_state", lambda _root: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setattr(flow, "create_escalation", lambda *_args, **kwargs: escalated.append(kwargs["reason"]))

    def fake_courier(_root, operation, *_args, **_kwargs):
        if operation == "courier_status":
            return {"event": operation, "ok": True}
        return {
            "event": "courier_capture_latest_busy",
            "ok": False,
            "project_id": "OTHER_PROJECT",
            "request_id": request_id,
            "fingerprint": "f" * 64,
            "live_owner_found": True,
        }

    monkeypatch.setattr(flow, "courier", fake_courier)
    flow.command_recover(tmp_path, SimpleNamespace(worker_thread_id="worker"))

    assert escalated == ["read-only Chat probe needs Supervisor judgment: courier_capture_latest_busy"]


def test_recover_treats_verified_chat_contention_as_healthy(monkeypatch, tmp_path, capsys):
    request_id = "GENERICCHESS-20260911-145701-eeb145bb"
    state = {
        "active": True,
        "mode": "courier",
        "active_request_directory": str(tmp_path / request_id),
        "active_request_id": request_id,
        "active_request_fingerprint": "f" * 64,
        "recovery_attempts": 5,
    }
    calls = []
    monkeypatch.setattr(flow, "active_state", lambda _root: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setattr(
        flow, "create_escalation",
        lambda *_args, **_kwargs: pytest.fail("live Chat contention must not escalate"),
    )

    def fake_courier(_root, operation, *_args, **_kwargs):
        calls.append(operation)
        assert operation == "courier_status"
        return {
            "event": "courier_status",
            "ok": True,
            "state": "chat_busy_waiting",
            "project_id": "GENERICCHESS",
            "request_id": request_id,
            "fingerprint": "f" * 64,
            "contention_wait_active": True,
            "agent_action_required": False,
            "safe_next_action": "wait_for_same_request",
        }

    monkeypatch.setattr(flow, "courier", fake_courier)
    flow.command_recover(tmp_path, SimpleNamespace(worker_thread_id="worker"))

    assert calls == ["courier_status"]
    assert state["recovery_attempts"] == 5
    assert state["recovery_state"] == "IDLE"
    assert state["last_probe"]["contention_wait_active"] is True
    assert "healthy_chat_contention_waiting" in capsys.readouterr().out


def test_recover_rejects_stale_chat_contention(monkeypatch, tmp_path):
    request_id = "GENERICCHESS-20260911-145701-eeb145bb"
    state = {
        "active": True,
        "mode": "courier",
        "active_request_directory": str(tmp_path / request_id),
        "active_request_id": request_id,
        "active_request_fingerprint": "f" * 64,
    }
    escalated = []
    monkeypatch.setattr(flow, "active_state", lambda _root: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setattr(flow, "create_escalation", lambda *_args, **kwargs: escalated.append(kwargs["reason"]))

    def fake_courier(_root, operation, *_args, **_kwargs):
        if operation == "courier_status":
            return {
                "event": "courier_status", "ok": True, "state": "chat_busy_waiting",
                "project_id": "GENERICCHESS", "request_id": request_id,
                "fingerprint": "f" * 64, "contention_wait_active": False,
                "agent_action_required": False, "safe_next_action": "wait_for_same_request",
            }
        return {"event": "courier_capture_latest_failed", "ok": False}

    monkeypatch.setattr(flow, "courier", fake_courier)
    flow.command_recover(tmp_path, SimpleNamespace(worker_thread_id="worker"))

    assert escalated == ["read-only Chat probe needs Supervisor judgment: courier_capture_latest_failed"]


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


def test_recover_imports_durable_completed_status_without_browser_probe(monkeypatch, tmp_path):
    response = tmp_path / "response.txt"
    response.write_text(
        "Next mainline work.\nWORK_ORDER_ID=F88\nGENERICCHESS_STATUS=CONTINUE\n"
        "GENERICCHESS_CANDIDATE_SHA=NONE\nGENERICCHESS_PROMOTION=HOLD\n",
        encoding="utf-8",
    )
    state = {"active": True, "mode": "courier", "active_request_directory": "request"}
    operations = []
    monkeypatch.setattr(flow, "load_state", lambda _root, required=True: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)

    def fake_courier(_root, operation, *_args, **_kwargs):
        operations.append(operation)
        assert operation == "courier_status"
        return {"event": "courier_status", "ok": True,
                "state": "response_received", "response_path": str(response)}

    monkeypatch.setattr(flow, "courier", fake_courier)
    flow.command_recover(tmp_path, SimpleNamespace(worker_thread_id="worker"))

    assert operations == ["courier_status"]
    assert state["active_request_directory"] is None
    assert state["last_work_order_id"] == "F88"
    assert state["recovery_state"] == "RECOVERED"


def test_recover_restores_request_binding_from_pending_escalation(monkeypatch, tmp_path):
    request_id = "GENERICCHESS-20260915-074503-2ea339bc"
    request = tmp_path / "outbox" / request_id
    request.mkdir(parents=True)
    response = request / "response.txt"
    response.write_text(
        "Resume mainline.\nWORK_ORDER_ID=F95\nGENERICCHESS_STATUS=CONTINUE\n"
        "GENERICCHESS_CANDIDATE_SHA=NONE\nGENERICCHESS_PROMOTION=HOLD\n",
        encoding="utf-8",
    )
    escalation_id = "7" * 20
    escalation = tmp_path / "runtime" / "escalations" / escalation_id
    escalation.mkdir(parents=True)
    (escalation / "dossier.json").write_text(
        json.dumps({"request_directory": str(request)}), encoding="utf-8"
    )
    (escalation / "resolution.json").write_text(
        json.dumps({"action": "RESUME_WORKER"}), encoding="utf-8"
    )
    state = {
        "active": True,
        "mode": "courier",
        "active_request_directory": None,
        "active_request_id": request_id,
        "escalation_id": escalation_id,
    }
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: tmp_path / "runtime")
    monkeypatch.setattr(flow, "load_state", lambda _root, required=True: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setattr(
        flow,
        "courier",
        lambda *_args, **_kwargs: {
            "event": "courier_status",
            "ok": True,
            "state": "response_received",
            "response_path": str(response),
        },
    )

    flow.command_recover(tmp_path, SimpleNamespace(worker_thread_id="worker"))

    assert state["active_request_directory"] is None
    assert state["last_work_order_id"] == "F95"
    assert any(item["event"] == "request_binding_restored"
               for item in state["recovery_timeline"])


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


def test_resolved_escalation_is_not_reopened(monkeypatch, tmp_path):
    sandbox = tmp_path / "sandbox"
    master = tmp_path / "master"
    sandbox.mkdir()
    master.mkdir()
    request = tmp_path / "request"
    request.mkdir()
    (request / "receipt.json").write_text("{}", encoding="utf-8")
    (request / "events.jsonl").write_text("{}\n", encoding="utf-8")
    state = {"active": True, "mode": "courier", "active_request_directory": str(request),
             "last_published_sha": "a" * 40, "last_probe": {"request_match": False},
             "recovery_state": "RECOVERED"}
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: tmp_path / "runtime")
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": master, "sandbox": sandbox})
    monkeypatch.setattr(flow, "sha", lambda path, ref="HEAD": "b" * 40 if path == master else "a" * 40)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)

    first = flow.create_escalation(tmp_path, state, reason="transport", worker_thread_id="worker")
    directory = tmp_path / "runtime" / "escalations" / first["escalation_id"]
    original_dossier = json.loads((directory / "dossier.json").read_text(encoding="utf-8"))
    resolution = {"action": "RECOVERED", "resolution_sha256": "r" * 64}
    (directory / "resolution.json").write_text(json.dumps(resolution), encoding="utf-8")
    state["recovery_state"] = "RECOVERED"

    second = flow.create_escalation(tmp_path, state, reason="transport again", worker_thread_id="other")

    assert second == original_dossier
    assert json.loads((directory / "dossier.json").read_text(encoding="utf-8")) == original_dossier
    assert json.loads((directory / "resolution.json").read_text(encoding="utf-8")) == resolution
    assert state["recovery_state"] == "RECOVERED"


def test_pending_diagnostic_and_resolution_return_to_original_worker(monkeypatch, tmp_path, capsys):
    runtime = tmp_path / "runtime"
    directory = runtime / "escalations" / ("a" * 20)
    directory.mkdir(parents=True)
    dossier = {"escalation_id": "a" * 20, "worker_thread_id": "worker-1",
               "worker_host_id": "local", "status": "PENDING"}
    (directory / "dossier.json").write_text(json.dumps(dossier), encoding="utf-8")
    (runtime / "supervisor.json").write_text(json.dumps({
        "supervisor_thread_id": "supervisor-1"}), encoding="utf-8")
    state = {
        "active": True, "mode": "courier", "recovery_timeline": [],
        "local_supervisor_required": True, "escalation_id": "a" * 20,
        "business_supervisor_notice_path": "old-notice.json",
        "recovery_state": "ESCALATED",
    }
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
    assert state["recovery_state"] == "IDLE"
    assert state["local_supervisor_required"] is False
    assert state.get("escalation_id") is None
    assert "business_supervisor_notice_path" not in state


def test_old_resolution_cannot_clear_a_newer_business_notice_after_status_and_work(
        monkeypatch, tmp_path, capsys):
    runtime = tmp_path / "runtime"
    directory = runtime / "escalations" / ("9" * 20)
    directory.mkdir(parents=True)
    (directory / "dossier.json").write_text(json.dumps({
        "escalation_id": "9" * 20, "request_directory": None,
    }), encoding="utf-8")
    (directory / "resolution.json").write_text(json.dumps({
        "action": "RESUME_WORKER", "resolved_at": 10.0,
        "resolution_sha256": "r" * 64,
    }), encoding="utf-8")
    state = {
        "active": True, "mode": "courier", "active_request_directory": None,
        "recovery_state": "ESCALATED", "escalation_id": "9" * 20,
        "local_supervisor_required": True,
        "business_supervisor_notice_path": "new-notice.json",
        "recovery_timeline": [{"event": "response_accepted", "at": 20.0}],
    }
    _state_path = runtime / "session.json"
    runtime.mkdir(exist_ok=True)
    _state_path.write_text(json.dumps(state), encoding="utf-8")
    master, sandbox = tmp_path / "master", tmp_path / "sandbox"
    master.mkdir(); sandbox.mkdir()
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, **_kwargs: runtime)
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": master, "sandbox": sandbox})
    monkeypatch.setattr(flow, "sha", lambda *_args, **_kwargs: "a" * 40)
    monkeypatch.setattr(flow, "clean", lambda _path: True)
    monkeypatch.setattr(flow, "git_ok", lambda *_args: True)
    monkeypatch.setattr(flow, "require_handoff_owner", lambda *_args: None)
    monkeypatch.setattr(flow, "require_no_supervisor_hold", lambda *_args: None)
    monkeypatch.setattr(flow, "branch", lambda _root: "sandbox")
    monkeypatch.setattr(flow, "dispatch_message", lambda *_args, **_kwargs: None)

    flow.command_status(tmp_path, SimpleNamespace())
    capsys.readouterr()
    flow.command_work(tmp_path, SimpleNamespace())

    persisted = json.loads(_state_path.read_text(encoding="utf-8"))
    assert persisted["local_supervisor_required"] is True
    assert persisted["escalation_id"] == "9" * 20
    assert persisted["business_supervisor_notice_path"] == "new-notice.json"


def test_newer_supervisor_resolution_clears_sticky_local_pause(monkeypatch, tmp_path, capsys):
    runtime = tmp_path / "runtime"
    directory = runtime / "escalations" / ("8" * 20)
    directory.mkdir(parents=True)
    (directory / "resolution.json").write_text(json.dumps({
        "action": "RECOVERED", "resolved_at": 10.0,
        "resolution_sha256": "r" * 64,
    }), encoding="utf-8")
    state = {
        "active": True, "escalation_id": "8" * 20,
        "recovery_state": "ESCALATED",
        "local_supervisor_required": True,
        "recovery_timeline": [],
    }
    runtime.mkdir(exist_ok=True)
    state_path = runtime / "session.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, **_kwargs: runtime)

    assert flow.active_state(tmp_path)["local_supervisor_required"] is False
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted.get("escalation_id") is None
    assert persisted["recovery_state"] == "IDLE"
    capsys.readouterr()


def test_newer_response_supersedes_old_local_supervisor_state(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    state_path = runtime / "session.json"
    state = {
        "active": True,
        "active_request_id": "request",
        "escalation_id": "7" * 20,
        "local_supervisor_required": True,
        "business_supervisor_notice_path": "old-notice.json",
        "recovery_state": "ESCALATED",
        "recovery_timeline": [],
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, **_kwargs: runtime)
    response_path = tmp_path / "response.txt"
    response_path.write_text(
        "New Supervisor decision.\nGENERICCHESS_STATUS=CONTINUE\n",
        encoding="utf-8",
    )

    flow.update_response_state(
        tmp_path,
        state,
        {"event": "response_received", "response_path": str(response_path)},
    )

    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["local_supervisor_required"] is False
    assert persisted["recovery_state"] == "IDLE"
    assert "escalation_id" not in persisted
    assert "business_supervisor_notice_path" not in persisted


def test_supervisor_resend_uses_evidence_retry_for_proven_unsent_request(
        monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    escalation_id = "b" * 20
    directory = runtime / "escalations" / escalation_id
    directory.mkdir(parents=True)
    (directory / "dossier.json").write_text(json.dumps({
        "escalation_id": escalation_id}), encoding="utf-8")
    (directory / "claim.json").write_text(json.dumps({
        "supervisor_thread_id": "supervisor-1"}), encoding="utf-8")
    request = str(tmp_path / "outbox" / "same-request")
    state = {"active_request_directory": request, "recovery_timeline": []}
    calls = []

    def fake_courier(_root, command, _request, **_kwargs):
        calls.append(command)
        if command == "courier_capture_latest":
            return {
                "event": "courier_capture_latest_empty",
                "latest_user_turn_found": False,
                "safe_next_action": "courier_retry_once",
                "submission_count": 0,
            }
        return {"event": "response_received", "response_path": "response.txt"}

    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)
    monkeypatch.setattr(flow, "active_state", lambda _root: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setattr(flow, "courier", fake_courier)
    monkeypatch.setattr(flow, "update_response_state", lambda *_args, **_kwargs: None)
    monkeypatch.setenv("CODEX_THREAD_ID", "supervisor-1")

    flow.command_supervisor_resend(
        tmp_path, SimpleNamespace(escalation_id=escalation_id))

    assert calls == ["courier_capture_latest", "courier_retry_once"]
    assert state["recovery_timeline"][-1]["recovery_command"] == "courier_retry_once"


def test_supervisor_resend_falls_back_after_consumed_unsent_evidence_retry(
        monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    escalation_id = "c" * 20
    directory = runtime / "escalations" / escalation_id
    directory.mkdir(parents=True)
    (directory / "dossier.json").write_text(json.dumps({
        "escalation_id": escalation_id}), encoding="utf-8")
    (directory / "claim.json").write_text(json.dumps({
        "supervisor_thread_id": "supervisor-1"}), encoding="utf-8")
    request = str(tmp_path / "outbox" / "same-request")
    state = {"active_request_directory": request, "recovery_timeline": []}
    calls = []

    def fake_courier(_root, command, _request, **_kwargs):
        calls.append(command)
        if command == "courier_capture_latest":
            return {
                "event": "courier_capture_latest_empty",
                "latest_user_turn_found": False,
                "safe_next_action": "courier_retry_once",
                "submission_count": 0,
            }
        if command == "courier_retry_once":
            return {"event": "courier_retry_refused"}
        return {"event": "response_received", "response_path": "response.txt"}

    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)
    monkeypatch.setattr(flow, "active_state", lambda _root: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setattr(flow, "courier", fake_courier)
    monkeypatch.setattr(flow, "update_response_state", lambda *_args, **_kwargs: None)
    monkeypatch.setenv("CODEX_THREAD_ID", "supervisor-1")

    flow.command_supervisor_resend(
        tmp_path, SimpleNamespace(escalation_id=escalation_id))

    assert calls == ["courier_capture_latest", "courier_retry_once", "courier_resend_once"]
    assert state["recovery_timeline"][-1]["recovery_command"] == "courier_resend_once"


def test_supervisor_resolution_clears_proven_replied_request(monkeypatch, tmp_path, capsys):
    runtime = tmp_path / "runtime"
    directory = runtime / "escalations" / ("d" * 20)
    directory.mkdir(parents=True)
    request = str(tmp_path / "outbox" / "same-request")
    response = tmp_path / "outbox" / "same-request" / "response.txt"
    response.parent.mkdir(parents=True)
    response.write_text("reply without footer →\n", encoding="utf-8")
    dossier = {
        "escalation_id": "d" * 20,
        "worker_thread_id": "worker-1",
        "worker_host_id": "local",
        "status": "PENDING",
        "request_directory": request,
        "last_probe": {
            "request_match": True,
            "post_submission_reply_found": True,
            "response_path": str(response),
        },
    }
    (directory / "dossier.json").write_text(json.dumps(dossier), encoding="utf-8")
    (runtime / "supervisor.json").write_text(json.dumps({
        "supervisor_thread_id": "supervisor-1"}), encoding="utf-8")
    state = {"active": True, "mode": "courier", "active_request_directory": request,
             "recovery_state": "ESCALATED", "recovery_timeline": [],
             "last_response_path": "old-response.txt", "last_response_sha256": "o" * 64}
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)
    monkeypatch.setattr(flow, "load_state", lambda _root, required=True: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setenv("CODEX_THREAD_ID", "supervisor-1")

    flow.command_supervisor_claim(tmp_path, SimpleNamespace(escalation_id="d" * 20))
    capsys.readouterr()
    flow.command_supervisor_resolve(
        tmp_path, SimpleNamespace(escalation_id="d" * 20, action="RESUME_WORKER", detail_file=None)
    )
    capsys.readouterr()

    assert state["active_request_directory"] is None
    assert state["recovery_state"] == "IDLE"
    assert state["last_response_path"] == str(response)
    assert state["last_response_sha256"] == flow.hashlib.sha256(
        "reply without footer →\n".encode("utf-8")).hexdigest()
    assert any(item["event"] == "resolved_reply_request_cleared"
               for item in state["recovery_timeline"])


def test_supervisor_resolution_preserves_unproven_request(monkeypatch, tmp_path, capsys):
    runtime = tmp_path / "runtime"
    directory = runtime / "escalations" / ("e" * 20)
    directory.mkdir(parents=True)
    request = str(tmp_path / "outbox" / "same-request")
    dossier = {"escalation_id": "e" * 20, "worker_thread_id": "worker-1",
               "worker_host_id": "local", "status": "PENDING",
               "request_directory": request, "last_probe": {
                   "request_match": False,
                   "post_submission_reply_found": True,
                   "response_path": request + "\\response.txt",
               }}
    (directory / "dossier.json").write_text(json.dumps(dossier), encoding="utf-8")
    (runtime / "supervisor.json").write_text(json.dumps({
        "supervisor_thread_id": "supervisor-2"}), encoding="utf-8")
    state = {"active": True, "mode": "courier", "active_request_directory": request,
             "recovery_state": "ESCALATED", "recovery_timeline": []}
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)
    monkeypatch.setattr(flow, "load_state", lambda _root, required=True: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setenv("CODEX_THREAD_ID", "supervisor-2")

    flow.command_supervisor_claim(tmp_path, SimpleNamespace(escalation_id="e" * 20))
    capsys.readouterr()
    flow.command_supervisor_resolve(
        tmp_path, SimpleNamespace(escalation_id="e" * 20, action="RESUME_WORKER", detail_file=None)
    )
    capsys.readouterr()

    assert state["active_request_directory"] == request
    assert state["recovery_state"] == "RECOVERED"


def test_supervisor_resolution_rebinds_legacy_partially_cleared_request(
        monkeypatch, tmp_path, capsys):
    runtime = tmp_path / "runtime"
    directory = runtime / "escalations" / ("f" * 20)
    directory.mkdir(parents=True)
    request = str(tmp_path / "outbox" / "same-request")
    response = tmp_path / "outbox" / "same-request" / "response.txt"
    response.parent.mkdir(parents=True)
    response.write_text("reply without footer\n", encoding="utf-8")
    dossier = {"escalation_id": "f" * 20, "worker_thread_id": "worker-1",
               "worker_host_id": "local", "status": "PENDING",
               "request_directory": request, "last_probe": {
                   "request_match": True, "post_submission_reply_found": True,
                   "request_id": "same-request", "response_path": str(response)}}
    (directory / "dossier.json").write_text(json.dumps(dossier), encoding="utf-8")
    (runtime / "supervisor.json").write_text(json.dumps({
        "supervisor_thread_id": "supervisor-3"}), encoding="utf-8")
    state = {"active": True, "mode": "courier", "active_request_directory": None,
             "active_request_id": "same-request", "escalation_id": "f" * 20,
             "recovery_state": "RECOVERED", "recovery_timeline": [],
             "last_response_sha256": "o" * 64}
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)
    monkeypatch.setattr(flow, "load_state", lambda _root, required=True: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setenv("CODEX_THREAD_ID", "supervisor-3")

    flow.command_supervisor_claim(tmp_path, SimpleNamespace(escalation_id="f" * 20))
    capsys.readouterr()
    flow.command_supervisor_resolve(
        tmp_path, SimpleNamespace(escalation_id="f" * 20, action="RESUME_WORKER", detail_file=None)
    )
    capsys.readouterr()

    assert state["recovery_state"] == "IDLE"
    assert state["last_response_path"] == str(response)
    assert state["last_response_sha256"] == flow.hashlib.sha256(
        b"reply without footer\n").hexdigest()


def test_supervisor_resolution_rejects_cross_request_rebind(
        monkeypatch, tmp_path, capsys):
    runtime = tmp_path / "runtime"
    directory = runtime / "escalations" / ("1" * 20)
    directory.mkdir(parents=True)
    request = str(tmp_path / "outbox" / "same-request")
    response = tmp_path / "outbox" / "same-request" / "response.txt"
    response.parent.mkdir(parents=True)
    response.write_text("reply without footer\n", encoding="utf-8")
    dossier = {"escalation_id": "1" * 20, "worker_thread_id": "worker-1",
               "worker_host_id": "local", "status": "PENDING",
               "request_directory": request, "last_probe": {
                   "request_match": True, "post_submission_reply_found": True,
                   "request_id": "same-request", "response_path": str(response)}}
    (directory / "dossier.json").write_text(json.dumps(dossier), encoding="utf-8")
    (runtime / "supervisor.json").write_text(json.dumps({
        "supervisor_thread_id": "supervisor-4"}), encoding="utf-8")
    state = {"active": True, "mode": "courier", "active_request_directory": None,
             "active_request_id": "different-request", "escalation_id": "1" * 20,
             "recovery_state": "RECOVERED", "recovery_timeline": [],
             "last_response_path": "old-response.txt", "last_response_sha256": "o" * 64}
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)
    monkeypatch.setattr(flow, "load_state", lambda _root, required=True: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setenv("CODEX_THREAD_ID", "supervisor-4")

    flow.command_supervisor_claim(tmp_path, SimpleNamespace(escalation_id="1" * 20))
    capsys.readouterr()
    flow.command_supervisor_resolve(
        tmp_path, SimpleNamespace(escalation_id="1" * 20, action="RESUME_WORKER", detail_file=None)
    )
    capsys.readouterr()

    assert state["recovery_state"] == "RECOVERED"
    assert state["last_response_path"] == "old-response.txt"
    assert state["last_response_sha256"] == "o" * 64


def test_supervisor_resolution_accepts_escalation_without_request_directory(
        monkeypatch, tmp_path, capsys):
    runtime = tmp_path / "runtime"
    directory = runtime / "escalations" / ("2" * 20)
    directory.mkdir(parents=True)
    dossier = {"escalation_id": "2" * 20, "worker_thread_id": "worker-1",
               "worker_host_id": "local", "status": "PENDING",
               "request_directory": None, "last_probe": {}}
    (directory / "dossier.json").write_text(json.dumps(dossier), encoding="utf-8")
    (runtime / "supervisor.json").write_text(json.dumps({
        "supervisor_thread_id": "supervisor-5"}), encoding="utf-8")
    state = {"active": True, "mode": "courier", "active_request_directory": None,
             "active_request_id": "request-1", "escalation_id": "2" * 20,
             "recovery_state": "ESCALATED", "recovery_timeline": []}
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)
    monkeypatch.setattr(flow, "load_state", lambda _root, required=True: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setenv("CODEX_THREAD_ID", "supervisor-5")

    flow.command_supervisor_claim(tmp_path, SimpleNamespace(escalation_id="2" * 20))
    capsys.readouterr()
    flow.command_supervisor_resolve(
        tmp_path, SimpleNamespace(escalation_id="2" * 20, action="RESUME_WORKER", detail_file=None)
    )
    capsys.readouterr()

    assert state["recovery_state"] == "IDLE"


def test_update_response_state_imports_body_and_normalizes_missing_footer(
        monkeypatch, tmp_path):
    response = tmp_path / "response.txt"
    response.write_text("missing footer\n", encoding="utf-8")
    state = {"last_response_path": "old-response.txt", "last_response_sha256": "o" * 64}
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)

    flow.update_response_state(tmp_path, state, {
        "event": "response_received", "response_path": str(response)})

    assert state["last_response_path"] == str(response)
    assert state["chat_control"] == {
        "GENERICCHESS_STATUS": "CONTINUE",
        "GENERICCHESS_CANDIDATE_SHA": "NONE",
        "GENERICCHESS_PROMOTION": "HOLD",
    }
    assert len(state["control_warnings"]) == 3


def test_supervisor_resolution_console_output_survives_legacy_windows_encoding(
        monkeypatch, tmp_path, capsys):
    runtime = tmp_path / "runtime"
    directory = runtime / "escalations" / ("c" * 20)
    directory.mkdir(parents=True)
    dossier = {"escalation_id": "c" * 20, "worker_thread_id": "worker-2",
               "worker_host_id": "local", "status": "PENDING"}
    (directory / "dossier.json").write_text(json.dumps(dossier), encoding="utf-8")
    (directory / "claim.json").write_text(json.dumps({
        "supervisor_thread_id": "supervisor-2"}), encoding="utf-8")
    detail_file = tmp_path / "detail.txt"
    detail_file.write_text("中文恢复说明", encoding="utf-8")
    state = {"active": True, "mode": "courier", "recovery_timeline": []}
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)
    monkeypatch.setattr(flow, "load_state", lambda _root, required=True: state)
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setenv("CODEX_THREAD_ID", "supervisor-2")
    original = flow._console_safe
    monkeypatch.setattr(flow, "_console_safe", lambda text: original(text, "cp1252"))

    flow.command_supervisor_resolve(
        tmp_path,
        SimpleNamespace(escalation_id="c" * 20, action="RESUME_WORKER",
                         detail_file=str(detail_file)),
    )

    assert '"detail":' in capsys.readouterr().out
    resolution = json.loads((directory / "resolution.json").read_text(encoding="utf-8"))
    assert resolution["detail"] == "中文恢复说明"


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


def test_register_worker_updates_current_session(monkeypatch, tmp_path, capsys):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "supervisor.json").write_text(json.dumps({
        "schema": "generic-chess-supervisor-v1",
        "supervisor_thread_id": "supervisor-1",
        "worker_thread_id": "old-worker",
    }), encoding="utf-8")
    (runtime / "session.json").write_text(json.dumps({
        "active": True, "mode": "courier", "worker_thread_id": "old-worker",
    }), encoding="utf-8")
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, create=True: runtime)
    monkeypatch.setenv("CODEX_THREAD_ID", "supervisor-1")

    flow.command_register_worker(
        tmp_path, SimpleNamespace(thread_id="new-worker", host_id="local")
    )

    assert json.loads((runtime / "supervisor.json").read_text())["worker_thread_id"] == "new-worker"
    assert json.loads((runtime / "session.json").read_text())["worker_thread_id"] == "new-worker"
    assert json.loads(capsys.readouterr().out)["worker_thread_id"] == "new-worker"


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
    assert state["superseded_request_migration"]["status"] == "PENDING"


def test_superseded_closeout_uses_one_fresh_idempotent_migration_identity(
        monkeypatch, tmp_path):
    sandbox = tmp_path / "sandbox"
    runtime = tmp_path / "runtime"
    old_request = tmp_path / "old-request"
    report = sandbox / "report.md"
    sandbox.mkdir()
    runtime.mkdir()
    old_request.mkdir()
    report.write_text("F88R1 closeout\n", encoding="utf-8")

    monkeypatch.setattr(flow, "sandbox_root", lambda _root: sandbox)
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: runtime)
    monkeypatch.setattr(flow, "worktrees", lambda _root: {
        "master": sandbox, "sandbox": sandbox})
    monkeypatch.setattr(flow, "sha", lambda *_args: "a" * 40)
    monkeypatch.setattr(flow, "require_clean", lambda _root: None)
    monkeypatch.setattr(flow, "require_synced", lambda *_args: None)
    monkeypatch.setattr(flow, "chat_message_body",
                        lambda _root, source, **_kwargs: source.read_text(encoding="utf-8"))
    monkeypatch.setattr(flow, "update_response_state", lambda *_args, **_kwargs: None)

    prepared_by_key = {}
    prepare_keys = []
    prepared_bodies = []
    dispatch_directories = []

    def fake_courier(_root, *args, **_kwargs):
        if args[0] == "courier_prepare":
            key = args[args.index("--idempotency-key") + 1]
            prepare_keys.append(key)
            prepared_bodies.append(Path(args[args.index("--message-file") + 1]).read_text(encoding="utf-8"))
            if key not in prepared_by_key:
                request = tmp_path / "requests" / key
                request.mkdir(parents=True)
                prepared_by_key[key] = str(request)
            return {"request_directory": prepared_by_key[key], "request_id": key}
        dispatch_directories.append(args[1])
        return {"event": "response_waiting"}

    monkeypatch.setattr(flow, "courier", fake_courier)
    old_key = "closeout-old-request"
    state = {
        "active": True,
        "mode": "courier",
        "active_request_directory": str(old_request),
        "active_request_id": "OLD-REQUEST",
        "retired_request_directory": str(old_request),
        "retired_request_id": "OLD-REQUEST",
        "retired_request_key": old_key,
        "last_request_key": old_key,
        "recovery_timeline": [],
    }

    flow.dispatch_message(tmp_path, state, report, "closeout")
    first_request = state["active_request_directory"]
    flow.dispatch_message(tmp_path, state, report, "closeout")

    assert old_request.is_dir()
    assert state["retired_request_directory"] == str(old_request)
    assert first_request != str(old_request)
    assert prepare_keys == [prepare_keys[0], prepare_keys[0]]
    assert prepare_keys[0] != old_key
    assert "-migration-" in prepare_keys[0]
    assert prepared_bodies == [prepared_bodies[0], prepared_bodies[0]]
    assert len(prepared_by_key) == 1
    assert dispatch_directories == [first_request, first_request]
    assert state["active_request_directory"] == first_request


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


def _stub_reference_git(monkeypatch, sandbox, *, tracked=True, dirty=False, published=True):
    monkeypatch.setattr(flow, "sandbox_root", lambda _root: sandbox)
    monkeypatch.setattr(flow, "git_ok", lambda _root, *args: tracked if args[:1] == ("ls-files",) else True)
    monkeypatch.setattr(flow, "git", lambda _root, *args, **_kwargs:
                        "report.md" if args[:2] == ("diff", "--name-only") and dirty
                        else "https://example.invalid/repo.git" if args[:3] == ("remote", "get-url", "origin")
                        else "")
    monkeypatch.setattr(flow, "sha", lambda _root, ref="HEAD": "a" * 40 if ref == "HEAD" or published else "b" * 40)


def test_small_closeout_is_inline_even_when_reference_only_requested(monkeypatch, tmp_path):
    sandbox = tmp_path / "sandbox"
    report = sandbox / "report.md"
    sandbox.mkdir()
    report.write_text("private blocker details\n", encoding="utf-8")
    _stub_reference_git(monkeypatch, sandbox)

    body = flow.chat_message_body(tmp_path, report, reference_only=True)

    assert body == "private blocker details\n"


@pytest.mark.parametrize("case", ["untracked", "dirty", "unpublished"])
def test_closeout_rejects_untracked_dirty_or_unpublished_before_browser_dispatch(monkeypatch, tmp_path, case):
    sandbox = tmp_path / "sandbox"
    report = sandbox / "report.md"
    sandbox.mkdir()
    report.write_text("x" * (flow.INLINE_CHAT_REFERENCE_THRESHOLD + 1), encoding="utf-8")
    _stub_reference_git(monkeypatch, sandbox, tracked=case != "untracked", dirty=case == "dirty", published=case != "unpublished")
    monkeypatch.setattr(flow, "require_clean", lambda _root: None)
    monkeypatch.setattr(flow, "require_synced", lambda *_args: None)
    monkeypatch.setattr(flow, "courier", lambda *_args, **_kwargs: pytest.fail("browser dispatch must not start"))

    with pytest.raises(flow.FlowError, match="exceeds 24 KiB"):
        flow.dispatch_message(tmp_path, {"active": True}, report, "closeout")


def test_closeout_forwards_explicit_evidence_attachments(monkeypatch, tmp_path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    report = sandbox / "report.md"
    attachment = sandbox / "plan.json"
    report.write_text("report\n", encoding="utf-8")
    attachment.write_text("{}\n", encoding="utf-8")
    _stub_reference_git(monkeypatch, sandbox)
    monkeypatch.setattr(flow, "require_clean", lambda _root: None)
    monkeypatch.setattr(flow, "require_synced", lambda *_args: None)
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path)
    monkeypatch.setattr(flow, "worktrees", lambda _root: {"master": sandbox, "sandbox": sandbox})
    monkeypatch.setattr(flow, "chat_message_body", lambda *_args, **_kwargs: "reference\n")
    monkeypatch.setattr(flow, "save_state", lambda *_args: None)
    monkeypatch.setattr(flow, "update_response_state", lambda *_args, **_kwargs: None)
    calls = []
    def fake_courier(_root, *args, **_kwargs):
        calls.append(args)
        return {"request_directory": str(tmp_path / "request")} if args[0] == "courier_prepare" else {"event": "response_waiting"}
    monkeypatch.setattr(flow, "courier", fake_courier)
    state = {"active": True, "mode": "courier"}
    flow.dispatch_message(tmp_path, state, report, "closeout", [attachment])
    prepare = calls[0]
    assert "--attachment" in prepare
    assert str(attachment.resolve()) in prepare


def test_start_message_remains_inline(monkeypatch, tmp_path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    source = tmp_path / "bootstrap.txt"
    source.write_text("start request body\n", encoding="utf-8")
    monkeypatch.setattr(flow, "sandbox_root", lambda _root: sandbox)

    assert flow.chat_message_body(tmp_path, source) == "start request body\n"


def test_heavy_uses_normal_priority_and_returns_child_code(monkeypatch, tmp_path):
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
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path)
    monkeypatch.setattr(flow, "active_supervisor_hold", lambda _root: None)

    def fake_popen(argv, **kwargs):
        seen.update({"argv": argv, **kwargs})
        return FakeProcess()

    monkeypatch.setattr(flow.subprocess, "Popen", fake_popen)
    code = flow.command_heavy(
        tmp_path, SimpleNamespace(argv=["--", "python", "work.py"],
                                  resource_envelope=str(_resource_path(tmp_path)))
    )

    assert code == 7
    assert seen["argv"] == ["python", "work.py"]
    assert seen["cwd"] == tmp_path
    assert "creationflags" not in seen


def test_heavy_rejects_recorded_live_child_even_when_lock_is_free(monkeypatch, tmp_path):
    monkeypatch.setattr(flow, "active_state", lambda _root: {"active": True, "mode": "local"})
    monkeypatch.setattr(flow, "branch", lambda _root: "sandbox")
    monkeypatch.setattr(flow, "_process_creation_time", lambda pid: {11: 101.0}.get(pid))
    run_dir = tmp_path / "heavy-runs" / "orphaned-run"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(json.dumps({
        "schema": "generic-chess-heavy-v1",
        "run_id": "orphaned-run",
        "label": "orphaned",
        "child_pid": 11,
        "child_created_at": 101.0,
        "status": "running",
    }), encoding="utf-8")
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path)

    with pytest.raises(flow.FlowError, match="existing GenericChess heavy child"):
        flow.command_heavy(
            tmp_path, SimpleNamespace(
                argv=["--", sys.executable, "-c", "pass"],
                resource_envelope=str(_resource_path(tmp_path)),
            )
        )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows process handle semantics")
def test_process_creation_time_excludes_terminated_queryable_child():
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
    try:
        created_at = flow._process_creation_time(process.pid)
        assert created_at is not None
        assert flow._same_process(process.pid, created_at)
    finally:
        process.terminate()
        process.wait(timeout=10)

    # Popen still owns a Windows handle, so OpenProcess can query the exited PID.
    assert flow._process_creation_time(process.pid) is None
    assert not flow._same_process(process.pid, created_at)


def test_publish_tests_use_the_same_exclusive_lock(monkeypatch, tmp_path):
    seen = {"locked": False}

    class FakeLock:
        def __enter__(self):
            seen["locked"] = True

        def __exit__(self, *_args):
            seen["locked"] = False

    def fake_run(argv, **kwargs):
        assert seen["locked"] is True
        seen["argv"] = argv
        seen["creationflags"] = kwargs.get("creationflags", 0)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(flow, "python_for", lambda _root: "python")
    monkeypatch.setattr(flow, "heavy_lock", lambda _root: FakeLock())
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path / "runtime")
    monkeypatch.setattr(flow, "run", fake_run)

    flow.run_tests(tmp_path, ["tests/test_session.py"])

    assert seen["argv"][-1] == "tests/test_session.py"
    assert seen["creationflags"] == 0


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


def test_heavy_state_uses_pid_and_creation_time_to_detect_reuse(monkeypatch):
    now = 1_000.0
    payload = {
        "schema": "generic-chess-heavy-v1",
        "run_id": "run-1",
        "label": "unit",
        "argv_digest": "a" * 64,
        "status": "running",
        "started_at": 900.0,
        "heartbeat_at": 999.0,
        "monitor_pid": 10,
        "monitor_created_at": 800.0,
        "child_pid": 11,
        "child_created_at": 810.0,
        "stdout_path": "stdout.log",
        "stderr_path": "stderr.log",
        "state_path": "state.json",
    }
    identities = {10: 800.0, 11: 810.0}
    monkeypatch.setattr(flow, "_process_creation_time", identities.get)
    assert flow._classified_heavy_state(payload, now=now)["status"] == "running"

    identities[11] = 811.0
    stale = flow._classified_heavy_state(payload, now=now)
    assert stale["status"] == "stale"
    assert stale["stale_reason"] == "child_process_identity_mismatch"
    assert payload["status"] == "running"

    malformed = dict(payload, argv_digest="not-a-digest")
    with pytest.raises(flow.FlowError, match="values"):
        flow._classified_heavy_state(malformed, now=now)


def test_monitorless_live_child_is_running_with_warning(monkeypatch):
    payload = {
        "schema": "generic-chess-heavy-v1",
        "run_id": "monitorless",
        "label": "monitorless",
        "argv_digest": "a" * 64,
        "status": "running",
        "started_at": 900.0,
        "heartbeat_at": 900.0,
        "monitor_pid": 10,
        "monitor_created_at": 800.0,
        "child_pid": 11,
        "child_created_at": 810.0,
        "stdout_path": "stdout.log",
        "stderr_path": "stderr.log",
        "state_path": "state.json",
    }
    monkeypatch.setattr(flow, "_process_creation_time", lambda pid: {11: 810.0}.get(pid))

    classified = flow._classified_heavy_state(payload, now=1_000.0)

    assert classified["status"] == "running"
    assert classified["warning"] == "monitor_process_identity_mismatch;heartbeat_expired"


@pytest.mark.parametrize("exit_code, expected_status", [(0, "completed"), (3, "failed")])
def test_heavy_monitor_records_completion_failure_and_separate_logs(
    monkeypatch, tmp_path, exit_code, expected_status
):
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path)
    monkeypatch.setattr(flow, "heavy_lock", lambda _root: _NoopContext())
    run_dir = tmp_path / "heavy-runs" / "logs-run"
    run_dir.mkdir(parents=True)
    command = [
        sys.executable,
        "-c",
        "import sys,time; print('OUT'); print('ERR', file=sys.stderr); "
        f"time.sleep(.2); raise SystemExit({exit_code})",
    ]
    flow._atomic_json(run_dir / "command.json", command)
    flow._atomic_json(run_dir / "state.json", {
        "schema": "generic-chess-heavy-v1",
        "run_id": "logs-run",
        "label": "logs",
        "argv_digest": "a" * 64,
        "status": "starting",
        "started_at": 1.0,
        "stdout_path": str(run_dir / "stdout.log"),
        "stderr_path": str(run_dir / "stderr.log"),
        "state_path": str(run_dir / "state.json"),
    })

    result = flow.command_heavy_monitor(
        tmp_path, SimpleNamespace(run_id="logs-run")
    )

    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert result == exit_code
    assert state["status"] == expected_status
    assert state["exit_code"] == exit_code
    assert state["monitor_created_at"] > 0
    assert state["child_created_at"] > 0
    assert "OUT" in (run_dir / "stdout.log").read_text(encoding="utf-8")
    assert "ERR" in (run_dir / "stderr.log").read_text(encoding="utf-8")


def test_heavy_monitor_marks_lock_failure_for_prompt_handshake(monkeypatch, tmp_path):
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path)
    run_dir = tmp_path / "heavy-runs" / "locked-run"
    run_dir.mkdir(parents=True)
    flow._atomic_json(run_dir / "command.json", [sys.executable, "-c", "pass"])
    flow._atomic_json(run_dir / "state.json", {
        "schema": "generic-chess-heavy-v1",
        "run_id": "locked-run",
        "label": "locked",
        "argv_digest": "a" * 64,
        "status": "starting",
        "started_at": 1.0,
        "stdout_path": str(run_dir / "stdout.log"),
        "stderr_path": str(run_dir / "stderr.log"),
        "state_path": str(run_dir / "state.json"),
    })

    def reject_lock(_root):
        raise flow.FlowError("another GenericChess heavy command is already running")

    monkeypatch.setattr(flow, "heavy_lock", reject_lock)
    assert flow.command_heavy_monitor(
        tmp_path, SimpleNamespace(run_id="locked-run")
    ) == 1
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert state["status"] == "failed"
    assert "already running" in state["error"]


def test_heavy_monitor_enforces_hard_wall_and_records_timed_out(monkeypatch, tmp_path):
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path)
    monkeypatch.setattr(flow, "heavy_lock", lambda _root: _NoopContext())
    monkeypatch.setattr(flow, "_process_creation_time", lambda _pid: 100.0)
    run_dir = tmp_path / "heavy-runs" / "timeout-run"
    run_dir.mkdir(parents=True)
    command = [sys.executable, "-c", "pass"]
    flow._atomic_json(run_dir / "command.json", command)
    flow._atomic_json(run_dir / "state.json", {
        "schema": "generic-chess-heavy-v1",
        "run_id": "timeout-run",
        "label": "timeout",
        "argv_digest": "a" * 64,
        "status": "starting",
        "started_at": 1.0,
        "hard_wall_minutes": 0.001,
        "stdout_path": str(run_dir / "stdout.log"),
        "stderr_path": str(run_dir / "stderr.log"),
        "state_path": str(run_dir / "state.json"),
    })

    class _HungProcess:
        pid = 4242

        def wait(self, timeout=None):
            raise flow.subprocess.TimeoutExpired(command, timeout)

        def terminate(self):
            return None

        def kill(self):
            return None

    process = _HungProcess()
    monkeypatch.setattr(flow.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(flow, "_terminate_heavy_process_tree", lambda child: None)

    result = flow.command_heavy_monitor(tmp_path, SimpleNamespace(run_id="timeout-run"))
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert result == 1
    assert state["status"] == "timed_out"
    assert state["timeout_reason"] == "hard_wall_minutes_exceeded"


def test_classified_timed_out_state_is_terminal():
    payload = {
        "schema": "generic-chess-heavy-v1",
        "run_id": "timeout",
        "label": "timeout",
        "argv_digest": "a" * 64,
        "status": "timed_out",
        "started_at": 1.0,
        "stdout_path": "out",
        "stderr_path": "err",
        "state_path": "state",
    }
    assert flow._classified_heavy_state(payload, now=1000)["status"] == "timed_out"


def test_heavy_start_uses_detached_hidden_monitor_and_waits_for_handshake(
    monkeypatch, tmp_path, capsys
):
    _heavy_start_mocks(monkeypatch, tmp_path)
    observed = {}

    class FakeMonitor:
        returncode = None

        def poll(self):
            return None

    def fake_popen(argv, **kwargs):
        observed["argv"] = argv
        observed.update(kwargs)
        run_id = argv[-1]
        state_path = tmp_path / "heavy-runs" / run_id / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.update({
            "status": "running",
            "monitor_pid": 10,
            "monitor_created_at": 100.0,
            "child_pid": 11,
            "child_created_at": 101.0,
            "handshake_at": 102.0,
            "heartbeat_at": 102.0,
        })
        flow._atomic_json(state_path, state)
        return FakeMonitor()

    monkeypatch.setattr(flow.subprocess, "Popen", fake_popen)
    result = flow.command_heavy_start(
        tmp_path,
        SimpleNamespace(label="survival", argv=["--", sys.executable, "-c", "pass"],
                        resource_envelope=str(_resource_path(tmp_path))),
    )
    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["status"] == "running"
    assert observed["creationflags"] & flow.subprocess.DETACHED_PROCESS
    assert observed["creationflags"] & flow.subprocess.CREATE_NO_WINDOW


def test_heavy_start_rejects_monitorless_live_child(monkeypatch, tmp_path):
    _heavy_start_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(flow, "_process_creation_time", lambda pid: {11: 101.0}.get(pid))
    run_dir = tmp_path / "heavy-runs" / "orphaned-run"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(json.dumps({
        "schema": "generic-chess-heavy-v1",
        "run_id": "orphaned-run",
        "label": "orphaned",
        "child_pid": 11,
        "child_created_at": 101.0,
        "status": "stale",
    }), encoding="utf-8")

    with pytest.raises(flow.FlowError, match="existing GenericChess heavy child"):
        flow.command_heavy_start(
            tmp_path,
            SimpleNamespace(label="replacement", argv=["--", sys.executable, "-c", "pass"],
                            resource_envelope=str(_resource_path(tmp_path))),
        )


def test_heavy_start_records_declared_envelope(monkeypatch, tmp_path, capsys):
    _heavy_start_mocks(monkeypatch, tmp_path)

    class FakeMonitor:
        returncode = None
        def poll(self):
            return None

    def fake_popen(argv, **kwargs):
        run_id = argv[-1]
        state_path = tmp_path / "heavy-runs" / run_id / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.update({"status": "running", "monitor_pid": 10, "monitor_created_at": 100.0,
                      "child_pid": 11, "child_created_at": 101.0, "handshake_at": 102.0,
                      "heartbeat_at": 102.0})
        flow._atomic_json(state_path, state)
        return FakeMonitor()

    monkeypatch.setattr(flow.subprocess, "Popen", fake_popen)
    assert flow.command_heavy_start(
        tmp_path, SimpleNamespace(label="declared", resource_envelope=str(_resource_path(tmp_path)),
                                  argv=["--", sys.executable, "-c", "pass"])
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["label"] == "declared"
    assert payload["status"] == "running"
    assert payload["hard_wall_minutes"] == 2


def test_heavy_start_atomically_records_monitor_launch_failure(monkeypatch, tmp_path):
    _heavy_start_mocks(monkeypatch, tmp_path)
    monkeypatch.setattr(
        flow.subprocess, "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("launch failed")),
    )
    with pytest.raises(flow.FlowError, match="could not launch monitor"):
        flow.command_heavy_start(
            tmp_path,
            SimpleNamespace(label="launch", resource_envelope=str(_resource_path(tmp_path)),
                            argv=["--", sys.executable, "-c", "pass"]),
        )
    state_paths = list((tmp_path / "heavy-runs").glob("*/state.json"))
    assert len(state_paths) == 1
    state = json.loads(state_paths[0].read_text(encoding="utf-8"))
    assert state["status"] == "failed"
    assert "launch failed" in state["error"]


@pytest.mark.parametrize("gate", ["worker", "hold", "master"])
def test_heavy_start_rejects_authority_hold_and_master(
    monkeypatch, tmp_path, gate
):
    _heavy_start_mocks(monkeypatch, tmp_path)
    if gate == "worker":
        monkeypatch.setattr(
            flow, "require_worker_write_authority",
            lambda *_args: (_ for _ in ()).throw(flow.FlowError("wrong worker")),
        )
        match = "wrong worker"
    elif gate == "hold":
        monkeypatch.setattr(
            flow, "require_no_supervisor_hold",
            lambda _root: (_ for _ in ()).throw(flow.FlowError("HOLD")),
        )
        match = "HOLD"
    else:
        monkeypatch.setattr(flow, "branch", lambda _root: "master")
        match = "sandbox"
    with pytest.raises(flow.FlowError, match=match):
        flow.command_heavy_start(
            tmp_path,
            SimpleNamespace(label="rejected", resource_envelope=str(_resource_path(tmp_path)),
                            argv=["--", sys.executable, "-c", "pass"]),
        )
