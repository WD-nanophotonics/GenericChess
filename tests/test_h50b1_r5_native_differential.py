"""R5 exact matrix and long-history Native/Python differential closure."""

import json
from pathlib import Path

import pytest

from generic_chess.native import native_available
from scripts.audit_h50b1_r3_native_differential import run_audit


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "h50b1_r5_semantic_native_execution.json"


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_h50b1_r5_exact_matrix_and_differential_closure():
    result = run_audit()
    assert len(result["western"]) == 24
    assert len(result["standard_shogi"]) == 21
    assert all(row["status"] == "PASS" for row in result["western"] + result["standard_shogi"])
    assert all(row["status"] == "PASS" for row in result["history_differential"].values())
    assert all(row["status"] == "PASS" for row in result["attack_check_differential"].values())
    assert result["declaration_differential"]["status"] == "PASS"
    assert result["zone_guard_differential"]["status"] == "PASS"
    assert result["automatic_500_differential"]["actual_legal_plies"] == 500
    assert result["automatic_500_differential"]["history_exact"] is True
    assert result["automatic_500_differential"]["history_events_exact"] is True
    assert result["automatic_500_differential"]["python_terminal"] == "no_contest"
    assert result["automatic_500_differential"]["native_terminal"]["status"] == "no_contest"


def test_h50b1_r5_fixture_freezes_scope_and_matrix_ids():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["status"] == "PASS"
    assert fixture["parent_sha"] == "8a1306645b43e642da732272c866f6654cea018c"
    assert fixture["production_scope"] == ["generic_chess/_native/native_semantic_runtime.c"]
    assert fixture["native_payload_version"] == 4
    assert fixture["matrix"]["western_count"] == len(fixture["matrix"]["western_ids"]) == 24
    assert fixture["matrix"]["standard_shogi_count"] == len(fixture["matrix"]["standard_shogi_ids"]) == 21
    assert fixture["automatic_500"]["actual_legal_plies"] == 500
    assert fixture["historical_regression"]["F50B2_status"] == "NOT_STARTED"
