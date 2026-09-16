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


def _envelope(*, large: bool = False) -> dict:
    return {
        "schema": flow.COMPUTE_ENVELOPE_SCHEMA,
        "envelope_id": "large-envelope" if large else "small-envelope",
        "logical_cpu_count": 4,
        "intended_cpu_lanes": 1,
        "expected_wall_minutes": 40 if large else 5,
        "hard_wall_minutes": 60 if large else 10,
        "expected_cpu_hours": 6 if large else 0.5,
        "hard_cpu_hours": 8 if large else 1,
        "arena_pairs": 16 if large else 2,
        "maximum_games": 32 if large else 4,
        "maximum_nodes": 1_000_000 if large else 10_000,
        "maximum_plies": 200 if large else 20,
        "maximum_concurrent_games": 1,
        "stage_count": 2 if large else 1,
    }


def _plan(envelope: dict) -> dict:
    return {
        "schema": flow.COMPUTE_PLAN_SCHEMA,
        "plan_id": "plan-context",
        "version": 1,
        "command_argv": ["python", "-c", "pass"],
        "scientific_decision": "Bounded decision",
        "why_smaller_evidence_insufficient": "The declared sample is required.",
        "reusable_evidence": ["published checkpoint"],
        "stages": ["comparison"],
        "resource_envelope": envelope,
        "checkpoint_behavior": "Persist completed work.",
        "stage_pause_points": ["after the stage"],
        "early_stop_rules": ["stop when decided"],
        "failure_exit_path": "Leave work resumable.",
        "alternatives": ["smaller pilot"],
    }


def test_resource_envelope_is_required_and_large_runs_need_no_chat_approval(tmp_path):
    with pytest.raises(flow.FlowError, match="resource-envelope"):
        flow._enforce_compute_gate(tmp_path, SimpleNamespace())

    small_path = _write(tmp_path / "small.json", _envelope())
    small = flow._enforce_compute_gate(
        tmp_path, SimpleNamespace(resource_envelope=str(small_path), compute_plan=None)
    )
    assert small["compute_size"] == "small_or_medium"

    large_path = _write(tmp_path / "large.json", _envelope(large=True))
    large = flow._enforce_compute_gate(
        tmp_path, SimpleNamespace(resource_envelope=str(large_path), compute_plan=None)
    )
    assert large["compute_size"] == "large"
    assert "resource_envelope_sha256" not in large
    assert "compute_plan_sha256" not in large


def test_optional_plan_only_checks_local_command_consistency(tmp_path):
    plan_path = _write(tmp_path / "plan.json", _plan(_envelope(large=True)))
    args = SimpleNamespace(resource_envelope=None, compute_plan=str(plan_path))
    metadata = flow._enforce_compute_gate(tmp_path, args, ["python", "-c", "pass"])
    assert metadata["compute_plan_id"] == "plan-context"

    with pytest.raises(flow.FlowError, match="command/stage/budget"):
        flow._enforce_compute_gate(tmp_path, args, ["python", "-c", "expanded"])


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


def test_compute_plan_commands_are_not_in_normal_parser_surface():
    with pytest.raises(SystemExit):
        flow.parser().parse_args(["compute-plan-request", "--plan-file", "plan.json"])
