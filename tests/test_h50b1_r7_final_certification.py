"""Machine checks for executable H50B1-R7 binary/regression provenance."""

import json
from pathlib import Path

import pytest

from generic_chess.native import native_available
from scripts.audit_h50b1_r3_native_differential import run_audit


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "h50b1_r7_final_certification.json"


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_h50b1_r7_replays_semantic_differential():
    report = run_audit()
    assert all(row["status"] == "PASS" for row in report["western"] + report["standard_shogi"])
    assert all(row["status"] == "PASS" for row in report["history_differential"].values())
    assert report["declaration_differential"]["status"] == "PASS"
    assert report["zone_guard_differential"]["status"] == "PASS"
    assert report["automatic_500_differential"]["actual_legal_plies"] == 500


def test_h50b1_r7_fixture_is_bound_to_actual_artifacts():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["checkpoint"] == "H50B1-R7_F50_SEMANTIC_NATIVE_CANONICAL_EXECUTION_FINAL"
    assert fixture["parent_sha"] == "18970563e0870b06fc47f51c7b67d19fc8ff4c79"
    assert fixture["native_payload_version"] == 4
    assert len(fixture["semantic_differential"]["western"]) == 24
    assert len(fixture["semantic_differential"]["standard_shogi"]) == 21
    assert fixture["semantic_differential"]["all_rows_pass"] is True
    for label, version in (("isolated_h50a", 2), ("current_r7", 4)):
        record = fixture[label]
        assert record["probe"]["semantic_payload_version"] == version
        assert Path(record["probe"]["module_path"]).is_file()
        assert len(record["probe"]["module_sha256"]) == 64
        assert record["pytest"]["junit_sha256"]
        assert record["pytest"]["raw_sha256"]
        assert record["pytest"]["tests"] == record["pytest"]["passed"] + record["pytest"]["skipped"] + record["pytest"]["failures"] + record["pytest"]["errors"]
    assert fixture["isolated_h50a"]["pytest"]["returncode"] == 1
    assert fixture["current_r7"]["pytest"]["returncode"] == 1
    assert set(fixture["current_r7"]["pytest"]["failing_test_ids"]) <= {
        "tests/test_f24f_western_chess_perft.py::test_f24f_mandatory_perft_one_shot",
        "tests/test_round5_corrective_r1_harness.py::test_r1_maps_every_initial_legal_action_losslessly",
    }
    assert fixture["abi_measurements"]["status"] == "PASS"
    assert fixture["historical_repair_ledger"]["historical_candidate_only_failure_count"] == len(fixture["historical_repair_ledger"]["rows"])
    assert fixture["scientific_protocol_contract"]["scientific_contract_equal"] is True
    assert fixture["cumulative_production_diff"]["status"] == "PASS"
    assert fixture["F50B2_status"] == "NOT_STARTED"
