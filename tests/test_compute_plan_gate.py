from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generic_chess_flow_compute_gate", ROOT / "tools" / "generic_chess_flow.py"
)
assert SPEC and SPEC.loader
flow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flow)


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _envelope(*, large: bool = False, expanded: bool = False) -> dict:
    return {
        "schema": flow.COMPUTE_ENVELOPE_SCHEMA,
        "envelope_id": "large-envelope" if large else "small-envelope",
        "logical_cpu_count": 20,
        "intended_cpu_lanes": 8 if large else 2,
        "expected_wall_minutes": 40 if large else 5,
        "hard_wall_minutes": 60 if large else 10,
        "expected_cpu_hours": 6 if large else 0.5,
        "hard_cpu_hours": 8 if large else 1,
        "arena_pairs": 16 if large else 2,
        "maximum_games": 32 if large else 4,
        "maximum_nodes": 1_000_000 if large else 10_000,
        "maximum_plies": 200 if large else 20,
        "maximum_concurrent_games": 8 if large else 2,
        "stage_count": 2 if large else 1,
        **({"maximum_games": 33} if expanded else {}),
    }


def _plan(envelope: dict, sandbox_sha: str = "a" * 40) -> dict:
    return {
        "schema": flow.COMPUTE_PLAN_SCHEMA,
        "plan_id": "plan-f63-r1",
        "version": 1,
        "sandbox_sha": sandbox_sha,
        "command_argv": ["python", "-c", "pass"],
        "scientific_decision": "Bounded arena decision",
        "why_smaller_evidence_insufficient": "The declared paired sample is required.",
        "reusable_evidence": ["published checkpoint"],
        "stages": ["comparison", "confirmation"],
        "resource_envelope": envelope,
        "checkpoint_behavior": "Persist each completed game atomically.",
        "stage_pause_points": ["after every game"],
        "early_stop_rules": ["stop only when decision is locked"],
        "failure_exit_path": "Leave incomplete stage resumable.",
        "alternatives": ["smaller pilot"],
    }


def _setup_approval(monkeypatch, tmp_path: Path, *, supervisor: str = "supervisor-1"):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    state = {
        "active": True,
        "mode": "courier",
        "last_response_source": "normal",
        "last_response_sha256": "r" * 64,
        "chat_control": {
            "GENERICCHESS_COMPUTE_PLAN_APPROVAL": "APPROVE",
        },
    }
    _write(runtime / "session.json", state)
    _write(runtime / "supervisor.json", {
        "schema": "generic-chess-supervisor-v1",
        "supervisor_thread_id": supervisor,
    })
    monkeypatch.setattr(flow, "runtime_dir", lambda _root, **_kwargs: runtime)
    monkeypatch.setattr(flow, "sha", lambda _root, _ref="HEAD": "a" * 40)
    monkeypatch.setenv("CODEX_THREAD_ID", supervisor)
    return runtime, state


def test_resource_declaration_is_required_and_small_runs_pass_through(tmp_path):
    with pytest.raises(flow.FlowError, match="resource-envelope"):
        flow._enforce_compute_gate(tmp_path, SimpleNamespace())
    envelope_path = _write(tmp_path / "small.json", _envelope())
    metadata = flow._enforce_compute_gate(
        tmp_path, SimpleNamespace(resource_envelope=str(envelope_path), compute_plan=None)
    )
    assert metadata["compute_size"] == "small_or_medium"
    unknown = _envelope()
    unknown["expected_wall_minutes"] = None
    assert flow._compute_is_large(unknown) is True


def test_canonical_argv_ignores_repo_path_spelling_but_not_real_changes(tmp_path):
    script = tmp_path / "scripts" / "runner.py"
    script.parent.mkdir()
    script.write_text("", encoding="utf-8")
    (script.parent / "other.py").write_text("", encoding="utf-8")
    assert flow._canonical_argv(tmp_path, ["scripts\\runner.py"]) == ["scripts/runner.py"]
    assert flow._canonical_argv(tmp_path, [str(script)]) == ["scripts/runner.py"]
    assert flow._canonical_argv(tmp_path, ["scripts\\other.py"]) == ["scripts/other.py"]
    assert flow._canonical_argv(tmp_path, ["python", "-c", "pass"]) != ["python", "-c", "expanded"]


def test_v2_plan_digest_is_canonical_json_not_file_whitespace(tmp_path, monkeypatch):
    monkeypatch.setattr(flow, "sha", lambda *_args: "a" * 40)
    plan = _plan(_envelope(large=True))
    plan["version"] = 2
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan, indent=4) + "\n", encoding="utf-8")
    loaded, digest = flow._load_compute_plan(tmp_path, path)
    assert digest == flow._json_digest(loaded)
    assert digest != flow._file_digest(path)


def test_large_compute_quota_fails_closed_without_local_receipt(tmp_path, monkeypatch):
    runtime, _ = _setup_approval(monkeypatch, tmp_path)
    envelope = _envelope(large=True)
    envelope.update({"expected_wall_minutes": 121, "hard_wall_minutes": 180})
    with pytest.raises(flow.FlowError, match="locally recorded work-order timestamp"):
        flow._enforce_large_compute_quota(tmp_path, envelope, {"recovery_timeline": []})


def test_large_compute_quota_counts_only_successful_children_in_rolling_window(tmp_path, monkeypatch):
    runtime, _ = _setup_approval(monkeypatch, tmp_path)
    envelope = _envelope(large=True)
    envelope.update({"expected_wall_minutes": 121, "hard_wall_minutes": 180})
    state = {
        "last_response_sha256": "r" * 64,
        "recovery_timeline": [{"event": "response_accepted", "at": 2_000.0, "response_sha256": "r" * 64}],
    }
    run_state = runtime / "heavy-runs" / "prior-run" / "state.json"
    run_state.parent.mkdir(parents=True)
    run_state.write_text(json.dumps({
        "quota_counted": True,
        "expected_wall_minutes": 121,
        "work_order_recorded_at": 2_000.0,
    }), encoding="utf-8")
    with pytest.raises(flow.FlowError, match="one successful Heavy child"):
        flow._enforce_large_compute_quota(tmp_path, envelope, state)
    old = json.loads(run_state.read_text(encoding="utf-8"))
    old["work_order_recorded_at"] = 2_000.0 - flow.LARGE_COMPUTE_QUOTA_WINDOW_SECONDS - 1
    run_state.write_text(json.dumps(old), encoding="utf-8")
    assert flow._enforce_large_compute_quota(tmp_path, envelope, state) == 2_000.0


def test_heavy_entrypoints_fail_closed_without_resource_declaration(monkeypatch, tmp_path):
    monkeypatch.setattr(flow, "active_state", lambda _root: {"active": True})
    monkeypatch.setattr(flow, "require_worker_write_authority", lambda *_args: None)
    monkeypatch.setattr(flow, "require_no_supervisor_hold", lambda _root: None)
    monkeypatch.setattr(flow, "branch", lambda _root: "sandbox")
    with pytest.raises(flow.FlowError, match="resource-envelope"):
        flow.command_heavy(tmp_path, SimpleNamespace(argv=["--", "python", "-c", "pass"]))
    with pytest.raises(flow.FlowError, match="resource-envelope"):
        flow.command_heavy_start(
            tmp_path, SimpleNamespace(label="missing", argv=["--", "python", "-c", "pass"])
        )


def test_large_run_requires_versioned_plan_and_approval(tmp_path, monkeypatch):
    envelope_path = _write(tmp_path / "large.json", _envelope(large=True))
    with pytest.raises(flow.FlowError, match="versioned --compute-plan"):
        flow._enforce_compute_gate(
            tmp_path, SimpleNamespace(resource_envelope=str(envelope_path), compute_plan=None)
        )
    _setup_approval(monkeypatch, tmp_path)
    plan_path = _write(tmp_path / "plan.json", _plan(_envelope(large=True)))
    with pytest.raises(flow.FlowError, match="command/stage/budget"):
        flow._enforce_compute_gate(
            tmp_path,
            SimpleNamespace(resource_envelope=str(envelope_path), compute_plan=str(plan_path)),
            ["python", "-c", "expanded"],
        )
    with pytest.raises(flow.FlowError, match="valid Supervisor approval"):
        flow._enforce_compute_gate(
            tmp_path,
            SimpleNamespace(resource_envelope=str(envelope_path), compute_plan=str(plan_path)),
        )


def test_valid_chat_and_registered_supervisor_approval_is_idempotent(tmp_path, monkeypatch):
    runtime, _ = _setup_approval(monkeypatch, tmp_path)
    envelope = _envelope(large=True)
    envelope_path = _write(tmp_path / "large.json", envelope)
    plan_path = _write(tmp_path / "plan.json", _plan(envelope))
    plan_sha = flow._file_digest(plan_path)
    envelope_sha = flow._json_digest(envelope)
    _write(tmp_path / "chat.json", {
        "schema": "generic-chess-chat-compute-approval-v1",
        "decision": "APPROVE",
        "plan_id": "plan-f63-r1",
        "plan_sha256": plan_sha,
        "sandbox_sha": "a" * 40,
        "envelope_sha256": envelope_sha,
        "chat_response_sha256": "r" * 64,
    })
    state = json.loads((runtime / "session.json").read_text(encoding="utf-8"))
    state["chat_control"] = {
        "GENERICCHESS_COMPUTE_PLAN_APPROVAL": "APPROVE",
        "GENERICCHESS_COMPUTE_PLAN_SHA": plan_sha,
        "GENERICCHESS_COMPUTE_ENVELOPE_SHA": envelope_sha,
    }
    state["pending_compute_plan"] = {
        "plan_id": "plan-f63-r1",
        "plan_sha256": plan_sha,
        "envelope_sha256": envelope_sha,
        "sandbox_sha": "a" * 40,
        "command_argv": ["python", "-c", "pass"],
        "response_sha256": "r" * 64,
    }
    _write(runtime / "session.json", state)
    args = SimpleNamespace(plan_file=str(plan_path), chat_approval_file=str(tmp_path / "chat.json"))
    assert flow.command_compute_plan_approve(tmp_path, args) == 0
    first = json.loads((runtime / "compute-approvals" / "plan-f63-r1.json").read_text())
    assert first["approval_version"] == 2
    assert "envelope_sha256" not in first and "command_argv" not in first
    assert flow.command_compute_plan_approve(tmp_path, args) == 0
    second = json.loads((runtime / "compute-approvals" / "plan-f63-r1.json").read_text())
    assert first == second
    metadata = flow._enforce_compute_gate(
        tmp_path, SimpleNamespace(resource_envelope=str(envelope_path), compute_plan=str(plan_path))
    )
    assert metadata["compute_size"] == "large"


def test_v1_compute_approval_remains_readable(tmp_path, monkeypatch):
    runtime, state = _setup_approval(monkeypatch, tmp_path)
    envelope = _envelope(large=True)
    plan = _plan(envelope)
    plan_path = _write(tmp_path / "plan.json", plan)
    plan_sha = flow._file_digest(plan_path)
    envelope_sha = flow._json_digest(envelope)
    state["chat_control"].update({
        "GENERICCHESS_COMPUTE_PLAN_SHA": plan_sha,
        "GENERICCHESS_COMPUTE_ENVELOPE_SHA": envelope_sha,
    })
    _write(runtime / "session.json", state)
    _write(runtime / "compute-approvals" / "plan-f63-r1.json", {
        "schema": flow.COMPUTE_APPROVAL_SCHEMA,
        "plan_id": "plan-f63-r1",
        "plan_sha256": plan_sha,
        "sandbox_sha": "a" * 40,
        "envelope_sha256": envelope_sha,
        "chat_response_sha256": "r" * 64,
        "supervisor_thread_id": "supervisor-1",
        "approved_at": 1.0,
        "revoked": False,
        "binding_mode": "local_pending",
        "command_argv": plan["command_argv"],
    })
    assert flow._validate_compute_approval(tmp_path, plan, plan_sha, envelope_sha)["plan_id"] == "plan-f63-r1"


def test_compute_plan_approve_can_bind_current_normal_chat_response_without_file(
        tmp_path, monkeypatch):
    runtime, state = _setup_approval(monkeypatch, tmp_path)
    envelope = _envelope(large=True)
    plan_path = _write(tmp_path / "plan.json", _plan(envelope))
    plan_sha = flow._file_digest(plan_path)
    envelope_sha = flow._json_digest(envelope)
    state["pending_compute_plan"] = {
        "plan_id": "plan-f63-r1",
        "plan_sha256": plan_sha,
        "envelope_sha256": envelope_sha,
        "sandbox_sha": "a" * 40,
        "command_argv": ["python", "-c", "pass"],
        "response_sha256": "r" * 64,
    }
    _write(runtime / "session.json", state)
    assert flow.command_compute_plan_approve(
        tmp_path, SimpleNamespace(plan_file=str(plan_path), chat_approval_file=None)
    ) == 0
    approval = json.loads((runtime / "compute-approvals" / "plan-f63-r1.json").read_text())
    assert approval["chat_response_sha256"] == "r" * 64


def test_compute_plan_request_inlines_scientific_plan_and_local_hashes(
        monkeypatch, tmp_path):
    envelope = _envelope()
    plan = _plan(envelope)
    plan_path = _write(tmp_path / "plan.json", plan)
    seen = {}
    monkeypatch.setattr(flow, "active_state", lambda _root: {"active": True, "mode": "courier"})
    monkeypatch.setattr(flow, "require_worker_write_authority", lambda *_args: None)
    monkeypatch.setattr(flow, "require_no_supervisor_hold", lambda _root: None)
    monkeypatch.setattr(flow, "sha", lambda *_args: "a" * 40)
    monkeypatch.setattr(flow, "runtime_dir", lambda _root: tmp_path / "runtime")
    monkeypatch.setattr(flow, "dispatch_message", lambda _root, _state, source, purpose: seen.update({
        "source": source, "purpose": purpose,
    }))
    flow.command_compute_plan_request(tmp_path, SimpleNamespace(plan_file=str(plan_path)))
    body = seen["source"].read_text(encoding="utf-8")
    assert seen["purpose"] == "compute_plan_request"
    assert "PLAN_JSON=" in body and "resource_envelope" in body
    assert "LOCAL_COMPUTE_SUMMARY=" in body
    assert flow._file_digest(plan_path) in body


def test_compute_plan_approve_rejects_pending_binding_mismatch(tmp_path, monkeypatch):
    runtime, state = _setup_approval(monkeypatch, tmp_path)
    envelope = _envelope(large=True)
    plan_path = _write(tmp_path / "plan.json", _plan(envelope))
    state["pending_compute_plan"] = {
        "plan_id": "different-plan",
        "plan_sha256": "0" * 64,
        "envelope_sha256": "1" * 64,
        "sandbox_sha": "a" * 40,
        "response_sha256": "r" * 64,
    }
    _write(runtime / "session.json", state)
    with pytest.raises(flow.FlowError, match="pending compute-plan request"):
        flow.command_compute_plan_approve(
            tmp_path, SimpleNamespace(plan_file=str(plan_path), chat_approval_file=None)
        )


def test_forged_chat_wrong_supervisor_and_stale_or_expanded_plan_fail_closed(tmp_path, monkeypatch):
    _setup_approval(monkeypatch, tmp_path, supervisor="supervisor-1")
    envelope = _envelope(large=True)
    envelope_path = _write(tmp_path / "large.json", envelope)
    plan_path = _write(tmp_path / "plan.json", _plan(envelope))
    chat_path = _write(tmp_path / "chat.json", {
        "schema": "generic-chess-chat-compute-approval-v1",
        "decision": "APPROVE",
        "plan_id": "plan-f63-r1",
        "plan_sha256": "0" * 64,
        "sandbox_sha": "a" * 40,
        "envelope_sha256": "0" * 64,
        "chat_response_sha256": "r" * 64,
    })
    with pytest.raises(flow.FlowError, match="stale"):
        flow.command_compute_plan_approve(
            tmp_path, SimpleNamespace(plan_file=str(plan_path), chat_approval_file=str(chat_path))
        )
    monkeypatch.setenv("CODEX_THREAD_ID", "forged-supervisor")
    with pytest.raises(flow.FlowError, match="registered Supervisor"):
        flow.command_compute_plan_revoke(tmp_path, SimpleNamespace(plan_file=str(plan_path)))
    monkeypatch.setenv("CODEX_THREAD_ID", "supervisor-1")
    expanded = _write(tmp_path / "expanded.json", _envelope(large=True, expanded=True))
    with pytest.raises(flow.FlowError, match="valid Supervisor approval"):
        flow._enforce_compute_gate(
            tmp_path, SimpleNamespace(resource_envelope=str(expanded), compute_plan=str(plan_path))
        )


def test_revoke_is_supervisor_only_and_idempotent(tmp_path, monkeypatch):
    runtime, _ = _setup_approval(monkeypatch, tmp_path)
    envelope = _envelope(large=True)
    plan_path = _write(tmp_path / "plan.json", _plan(envelope))
    plan_sha = flow._file_digest(plan_path)
    envelope_sha = flow._json_digest(envelope)
    _write(runtime / "compute-approvals" / "plan-f63-r1.json", {
        "schema": flow.COMPUTE_APPROVAL_SCHEMA,
        "plan_id": "plan-f63-r1",
        "plan_sha256": plan_sha,
        "sandbox_sha": "a" * 40,
        "envelope_sha256": envelope_sha,
        "chat_response_sha256": "r" * 64,
        "supervisor_thread_id": "supervisor-1",
        "approved_at": 1.0,
        "revoked": False,
    })
    args = SimpleNamespace(plan_file=str(plan_path))
    assert flow.command_compute_plan_revoke(tmp_path, args) == 0
    assert flow.command_compute_plan_revoke(tmp_path, args) == 0
    approval = json.loads((runtime / "compute-approvals" / "plan-f63-r1.json").read_text())
    assert approval["revoked"] is True
