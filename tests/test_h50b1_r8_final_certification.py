"""Portable validation for the immutable H50B1-R8 evidence closure."""

import hashlib
import json
from pathlib import Path

import pytest

from scripts.run_r7_regression import parse_junit

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "h50b1_r8_final_certification.json"
EVIDENCE = ROOT / "tests" / "fixtures" / "h50b1_r8_regression_evidence"
RESIDUALS = {
    "tests/test_f24f_western_chess_perft.py::test_f24f_mandatory_perft_one_shot",
    "tests/test_round5_corrective_r1_harness.py::test_r1_maps_every_initial_legal_action_losslessly",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_record(label: str, record: dict) -> None:
    pytest_record = record["pytest"]
    for kind, suffix in (("junit", ".junit.xml"), ("metadata", ".json"), ("raw", ".raw.txt")):
        artifact = record["pytest"]["evidence_artifacts"][kind]
        path = ROOT / artifact["path"]
        assert path.is_file()
        assert _sha(path) == artifact["sha256"]
        assert path.stat().st_size == artifact["bytes"]
    junit = EVIDENCE / f"{label}.junit.xml"
    parsed = parse_junit(junit, EVIDENCE)
    for key in ("tests", "passed", "skipped", "failures", "errors", "failing_test_ids"):
        assert parsed[key] == pytest_record[key]
    assert pytest_record["tests"] == pytest_record["passed"] + pytest_record["skipped"] + pytest_record["failures"] + pytest_record["errors"]


def test_r8_fixture_is_portable_and_artifacts_are_immutable():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["checkpoint"] == "H50B1-R8_F50_SEMANTIC_NATIVE_CANONICAL_EXECUTION_FINAL"
    assert fixture["parent_sha"] == "d7c89011dfb9db2e542389b51f067c4d2d092478"
    assert fixture["parent_chain"] == {
        "R5": "a2ce9048bd336d5dbe3d359e3da93aa0f9e8ab63",
        "R6": "18970563e0870b06fc47f51c7b67d19fc8ff4c79",
        "H50A": "7ff0039bcc469bdc6b0b3c5ade61558d72ccf681",
    }
    assert fixture["h50a_identity"]["head"] == fixture["parent_chain"]["H50A"]
    assert fixture["h50a_identity"]["compiler_source_sha256"] == fixture["h50a_identity"]["h50a_git_blob_sha256"]
    assert fixture["h50a_identity"]["declared_semantic_payload_version"] == 2
    assert fixture["isolated_h50a"]["probe"]["semantic_payload_version"] == 2
    assert fixture["current_r7"]["probe"]["semantic_payload_version"] == 4
    assert fixture["semantic_differential"]["all_rows_pass"] is True
    assert len(fixture["semantic_differential"]["western"]) == 24
    assert len(fixture["semantic_differential"]["standard_shogi"]) == 21
    assert fixture["abi_measurements"]["status"] == "PASS"
    assert fixture["scientific_protocol_contract"]["scientific_contract_equal"] is True
    assert fixture["cumulative_production_diff"]["status"] == "PASS"
    assert fixture["F50B2_status"] == "NOT_STARTED"
    _check_record("h50a", fixture["isolated_h50a"])
    _check_record("current-r7", fixture["current_r7"])
    assert fixture["isolated_h50a"]["pytest"]["failures"] == 13
    assert fixture["historical_repair_ledger"]["historical_candidate_only_failure_count"] == 11
    assert set(fixture["current_r7"]["pytest"]["failing_test_ids"]) == RESIDUALS


def test_r8_post_freeze_result_is_recorded_after_final_full_run():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    record = fixture["current_r8_post_freeze"]
    if record is None:
        pytest.skip("post-freeze evidence is populated after the initial R8 full run")
    assert record is not None
    assert record["pytest"]["tests"] == record["pytest"]["passed"] + record["pytest"]["skipped"] + record["pytest"]["failures"] + record["pytest"]["errors"]
    assert set(record["pytest"]["failing_test_ids"]) <= RESIDUALS
