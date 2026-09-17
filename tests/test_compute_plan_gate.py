from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generic_chess_flow_resource_envelope", ROOT / "tools" / "generic_chess_flow.py"
)
assert SPEC and SPEC.loader
flow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flow)


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _envelope() -> dict:
    return {
        "schema": flow.COMPUTE_ENVELOPE_SCHEMA,
        "envelope_id": "bounded-envelope",
        "logical_cpu_count": 4,
        "intended_cpu_lanes": 1,
        "expected_wall_minutes": 5,
        "hard_wall_minutes": 10,
        "expected_cpu_hours": 0.5,
        "hard_cpu_hours": 1,
        "arena_pairs": 2,
        "maximum_games": 4,
        "maximum_nodes": 10_000,
        "maximum_plies": 20,
        "maximum_concurrent_games": 1,
        "stage_count": 1,
    }


def test_resource_envelope_validates_without_approval_metadata(tmp_path):
    path = _write(tmp_path / "envelope.json", _envelope())
    metadata = flow._resource_metadata(path)
    assert metadata["resource_envelope"]["envelope_id"] == "bounded-envelope"
    assert metadata["hard_wall_minutes"] == 10
    assert metadata["expected_wall_minutes"] == 5
    assert set(metadata) == {"resource_envelope", "hard_wall_minutes", "expected_wall_minutes"}


def test_resource_envelope_rejects_estimates_over_hard_limits():
    envelope = _envelope()
    envelope["expected_wall_minutes"] = 11
    with pytest.raises(flow.FlowError, match="wall estimate exceeds hard ceiling"):
        flow._validate_resource_envelope(envelope)


def test_heavy_entrypoints_require_a_declared_resource_envelope():
    with pytest.raises(SystemExit):
        flow.parser().parse_args(["heavy", "--", "python", "-c", "pass"])
    with pytest.raises(SystemExit):
        flow.parser().parse_args(["heavy-start", "--label", "bounded", "--", "python", "-c", "pass"])


def test_retired_compute_plan_commands_are_not_in_normal_parser_surface():
    with pytest.raises(SystemExit):
        flow.parser().parse_args(["compute-plan-request", "--plan-file", "plan.json"])
