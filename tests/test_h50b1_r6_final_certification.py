"""Machine checks for the record-only H50B1-R6 certification closure."""

import json
from pathlib import Path

import pytest

from generic_chess.native import native_available
from scripts.audit_h50b1_r6_final import build_report


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "h50b1_r6_final_certification.json"


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_h50b1_r6_reproducible_differential_and_provenance_gate():
    report = build_report()
    assert report["status"] == "PASS"
    assert len(report["western_matrix_witnesses"]) == 24
    assert len(report["standard_shogi_matrix_witnesses"]) == 21
    assert all(row["status"] == "PASS" for row in report["western_matrix_witnesses"] + report["standard_shogi_matrix_witnesses"])
    assert report["declaration_controls"]["all_native_python_equal"] is True
    assert report["generic_spatial_selector_controls"]["all_native_python_equal"] is True
    assert report["scientific_protocol_contract"]["scientific_contract_equal"] is True
    assert report["cumulative_production_diff"]["R5_TO_R6_DIFF"] == []


def test_h50b1_r6_fixture_binds_all_required_sections():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["checkpoint"] == "H50B1-R6_F50_SEMANTIC_NATIVE_CANONICAL_EXECUTION_FINAL"
    assert fixture["parent_sha"] == "a2ce9048bd336d5dbe3d359e3da93aa0f9e8ab63"
    assert fixture["production_code_byte_frozen_at_r5"] is True
    assert fixture["native_payload_version"] == 4
    assert all(row["status"] == "PASS" for row in fixture["western_matrix_witnesses"] + fixture["standard_shogi_matrix_witnesses"])
    ids = {row["matrix_cell_id"]: row for row in fixture["standard_shogi_matrix_witnesses"]}
    western_ids = {row["matrix_cell_id"]: row for row in fixture["western_matrix_witnesses"]}
    for cell in ("attack_parity", "check_parity"):
        assert western_ids[cell]["supporting_differential_section"] == "run_audit.western"
        assert western_ids[cell]["substantive_differential_witness"]["western"] == fixture["differential"]["attack_check"]["western"]
    for cell in ("continuous_check_loss_owner_0", "continuous_check_loss_owner_1", "imported_history_roundtrip", "automatic_adjudication", "weighted_declaration_score"):
        assert "substantive_differential_witness" in ids[cell]
    assert fixture["declaration_controls"]["status"] == "PASS"
    assert {"R->TR", "B->TB", "P->TP", "S->TS"}.issubset(set(next(row for row in fixture["declaration_controls"]["cases"] if row["id"] == "promoted_base_family_weighting")["families"]))
    assert fixture["generic_spatial_selector_controls"]["status"] == "PASS"
    assert fixture["generic_witness"]["canonical_native_v4_payload_sha256"]
    assert fixture["abi_measurements"]["status"] == "PASS"
    assert [row["sizeof"] for row in fixture["abi_measurements"]["records"]] == [27296, 53920, 53920]
    assert fixture["isolated_h50a_regression"]["failed"] == 13
    assert fixture["isolated_h50a_regression"]["native_binary"]["sha256"] == "6d1c4a0d8777f61dc64a0466f9dbcef6fcc1aaa0c59bfdbba34842479c85411e"
    assert fixture["isolated_h50a_regression"]["native_binary"]["size_bytes"] == 338944
    assert len(fixture["isolated_h50a_regression"]["failing_test_ids"]) == 13
    assert fixture["historical_repair_ledger"]["actual_isolated_h50a_historical_candidate_only_failures"] == 11
    assert len(fixture["historical_repair_ledger"]["rows"]) == 11
    assert fixture["scientific_protocol_contract"]["scientific_contract_equal"] is True
    assert fixture["cumulative_production_diff"]["status"] == "PASS"
    assert fixture["final_current_regression"]["passed"] == 1538
    assert fixture["final_current_regression"]["skipped"] == 3
    assert fixture["final_current_regression"]["failed"] == 2
    assert fixture["final_current_regression"]["failing_test_ids"] == [
        "tests/test_f24f_western_chess_perft.py::test_f24f_mandatory_perft_one_shot",
        "tests/test_round5_corrective_r1_harness.py::test_r1_maps_every_initial_legal_action_losslessly",
    ]
    assert fixture["final_current_regression"]["native_binary"]["sha256"] == "6653bb1867d6fb70bb1bec341ddc427cba2e89623c31efc3eb8bd89076467416"
    assert fixture["F50B2_status"] == "NOT_STARTED"
