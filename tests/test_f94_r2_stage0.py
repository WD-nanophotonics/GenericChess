"""Result-free contract tests for the bounded F94-R2 Stage-0 probe."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import scripts.f94_r2_strength_calibration as f94


def test_stage0_prep_freezes_source_identities_and_opening_zero(tmp_path):
    output = tmp_path / "stage0-prep.json"
    payload = f94.build_stage0_prep(output=output)

    assert payload["schema"] == "generic-chess-f94-r2-stage0-prep-v1"
    assert payload["result_free"] is True
    assert payload["budgets"]["arena_invocations"] == 6
    assert payload["budgets"]["arena_games"] == 12
    assert payload["stage0_prep_fingerprint"] == f94._stage0_fingerprint(payload)
    for candidate in payload["candidates"]:
        assert candidate["source_prep_fingerprint"]
        assert all(row["selected_opening_index"] == 0 for row in candidate["opening_corpora"])
        assert all(row["selected_opening_seed"] for row in candidate["opening_corpora"])
    assert payload["boundary_control"]["compute"] == 0
    assert json.loads(output.read_text(encoding="utf-8")) == payload


def test_r3_prep_is_result_free_and_changes_only_depth_limit(tmp_path):
    output = tmp_path / "r3-prep.json"
    payload = f94.build_r3_nonbinding_depth_calibration_prep(output=output)
    r2 = f94._load_stage0_prep()

    assert payload["schema"] == "generic-chess-f94-r3-nonbinding-depth-calibration-prep-v1"
    assert payload["status"] == "R3_PREP_FROZEN"
    assert payload["result_free"] is True
    assert payload["r3_prep_fingerprint"] == f94._r3_prep_fingerprint(payload)
    assert payload["budgets"] == {**r2["budgets"], "max_depth": 64}
    assert payload["candidates"] == r2["candidates"]
    assert payload["boundary_control"] == r2["boundary_control"]
    assert payload["r2_protocol_calibration"]["classification"] == "OBSERVED_NOT_POOLABLE"
    assert "Arena" in payload["execution_authority"]
    assert json.loads(output.read_text(encoding="utf-8")) == payload


def test_stage0_direction_prioritizes_fallback_and_depth_censoring():
    assert f94._stage0_status(1.0, [{"completed_depth": f94.MAX_DEPTH}]) == "DEPTH_CENSORED"
    assert f94._stage0_status(1.0, [{"used_fallback": True}]) == "FALLBACK"
    assert f94._stage0_status(1.0, [{"completed_depth": 8}]) == "POSITIVE_DIRECTION"
    assert f94._stage0_status(0.0, [{"completed_depth": 8}]) == "NEGATIVE_DIRECTION"
    assert f94._stage0_status(0.5, [{"completed_depth": 8}]) == "MIXED_OR_UNCERTAIN"
    assert f94._stage0_overall_direction(["FALLBACK", "DEPTH_CENSORED"], [1.0, 1.0]) == "DEPTH_CENSORED"
    assert f94._stage0_overall_direction(["OPERATIONALLY_UNRESOLVED", "FALLBACK"], [1.0]) == "FALLBACK"


def test_stage0_rejects_tampered_source_before_arena(tmp_path, monkeypatch):
    staged_path = tmp_path / "stage0-prep.json"
    payload = f94.build_stage0_prep(output=staged_path)
    payload["source_prep_artifact_sha256"] = "0" * 64
    payload["stage0_prep_fingerprint"] = f94._stage0_fingerprint(payload)
    staged_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(f94, "run_arena", lambda *args, **kwargs: pytest.fail("Arena called after source mismatch"))
    with pytest.raises(RuntimeError, match="source PREP artifact SHA"):
        f94.run_stage0(prep_path=staged_path, output=tmp_path / "result.json")


def test_stage0_runs_six_ready_invocations_and_skips_boundary(tmp_path, monkeypatch):
    staged_path = tmp_path / "stage0-prep.json"
    f94.build_stage0_prep(output=staged_path)
    arena_calls = []
    native_calls = []

    def fake_native(*args, **kwargs):
        native_calls.append(args[0].ruleset_fingerprint)
        return SimpleNamespace(fingerprint=args[0].ruleset_fingerprint)

    def fake_arena(*args, **kwargs):
        arena_calls.append(args[0].ruleset_fingerprint)
        metric = {
            "nodes": 10,
            "elapsed_seconds": 1.0,
            "completed_depth": 8,
            "used_fallback": False,
        }
        game0 = SimpleNamespace(child_owner=0, winner=0, result="draw", plies=4, search_metrics=(metric,))
        game1 = SimpleNamespace(child_owner=1, winner=1, result="draw", plies=4, search_metrics=(metric,))
        pair = SimpleNamespace(child_pair_score=1.0, game_child_owner0=game0, game_child_owner1=game1)
        return SimpleNamespace(pairs=[pair])

    monkeypatch.setattr(f94, "compile_native_semantic_rules", fake_native)
    monkeypatch.setattr(f94, "run_arena", fake_arena)
    result = f94.run_stage0(prep_path=staged_path, output=tmp_path / "result.json")

    assert len(native_calls) == 2
    assert len(arena_calls) == 6
    assert result["status"] == "STAGE0_RESULT_COMPLETE"
    assert result["derived_compute"] == {
        "arena_invocations": 6,
        "arena_games": 12,
        "boundary_arena_invocations": 0,
    }
    boundary = next(row for row in result["candidates"] if row["class"] == "boundary")
    assert boundary["status"] == "PREREQUISITE_A_C_NOT_PASS"
    assert boundary["arena_invocations"] == 0
    assert boundary["tape_results"] == []
