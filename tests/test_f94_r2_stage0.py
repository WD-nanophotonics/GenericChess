"""Result-free contract tests for the bounded F94-R2 Stage-0 probe."""

from __future__ import annotations

import json

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


def test_stage0_direction_prioritizes_fallback_and_depth_censoring():
    assert f94._stage0_status(1.0, [{"used_fallback": True}]) == "FALLBACK"
    assert f94._stage0_status(1.0, [{"completed_depth": f94.MAX_DEPTH}]) == "DEPTH_CENSORED"
    assert f94._stage0_status(1.0, [{"completed_depth": 8}]) == "POSITIVE_DIRECTION"
    assert f94._stage0_status(0.0, [{"completed_depth": 8}]) == "NEGATIVE_DIRECTION"
    assert f94._stage0_status(0.5, [{"completed_depth": 8}]) == "MIXED_OR_UNCERTAIN"
