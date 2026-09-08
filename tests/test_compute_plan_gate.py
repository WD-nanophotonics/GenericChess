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
    state["chat_control"].update({
        "GENERICCHESS_COMPUTE_PLAN_SHA": plan_sha,
        "GENERICCHESS_COMPUTE_ENVELOPE_SHA": envelope_sha,
    })
    _write(runtime / "session.json", state)
    args = SimpleNamespace(plan_file=str(plan_path), chat_approval_file=str(tmp_path / "chat.json"))
    assert flow.command_compute_plan_approve(tmp_path, args) == 0
    first = json.loads((runtime / "compute-approvals" / "plan-f63-r1.json").read_text())
    assert flow.command_compute_plan_approve(tmp_path, args) == 0
    second = json.loads((runtime / "compute-approvals" / "plan-f63-r1.json").read_text())
    assert first == second
    metadata = flow._enforce_compute_gate(
        tmp_path, SimpleNamespace(resource_envelope=str(envelope_path), compute_plan=str(plan_path))
    )
    assert metadata["compute_size"] == "large"


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
    with pytest.raises(flow.FlowError, match="differs|stale"):
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
