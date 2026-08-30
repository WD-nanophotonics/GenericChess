"""Regression tests for the corrective, executable F23X R1 audit."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "tests" / "fixtures" / "f23x_shogi_shadow_r1.json"
CONTRACT_REPORT = ROOT / "tests" / "fixtures" / "f23x_metamorphic_contracts_r1.json"


def _reports():
    return json.loads(REPORT.read_text(encoding="utf-8")), json.loads(CONTRACT_REPORT.read_text(encoding="utf-8"))


def test_r1_executes_all_ten_contracts_from_actual_before_after_states():
    report, contract_report = _reports()
    phase_a = report["phase_a"]
    assert contract_report["phase_a"] == phase_a
    assert phase_a["contract_count"] == 10
    assert [row["id"] for row in phase_a["contracts"]] == [f"M{i}" for i in range(1, 11)]
    assert phase_a["passed"] is True

    for contract in phase_a["contracts"]:
        assert contract["passed"] is True
        assert contract["renamed_equivalent"]["executed"] is True
        assert contract["renamed_equivalent"]["passed"] is True
        for variant in contract["variants"]:
            before = variant["before_feature_vector"]
            after = variant["after_feature_vector"]
            feature = variant["feature"]
            assert before and after and feature in before and feature in after
            assert variant["target_delta"] == after[feature] - before[feature]
            assert variant["semantic_witness"]["passed"] is True
            assert variant["strict_positive"] is True
            assert "expected" not in variant


def test_r1_hoists_profile_and_preserves_first_pass_artifacts():
    report, _ = _reports()
    phase_a = report["phase_a"]
    assert phase_a["context_parity"]["passed"] is True
    assert phase_a["context_parity"]["nonterminal_count"] == 8
    assert all(case["profile_build_count_after_two_calls"] == 1 for case in phase_a["context_parity"]["cases"])
    assert phase_a["complexity"]["profile_build_once"] is True
    assert phase_a["complexity"]["coefficients"] == [1, 1, 1, 1, 1]
    assert report["first_pass_artifact_integrity"]["all_match"] is True
    assert report["production_changed"] is False


def test_r1_records_incomplete_node_quality_without_inventing_rank_or_quality():
    report, _ = _reports()
    phase_b = report["phase_b"]
    assert report["phase_b_ran"] is True
    assert phase_b["search_harness_v1_parity"]["passed"] is True
    assert phase_b["native_routing_policy"] == ["PYTHON_AUTHORITY_FALLBACK"]
    assert phase_b["progressive_stop"] == {"budget": 2048, "reason": "NOT_COMPLETED_WITHIN_OUTER_WATCHDOG"}
    assert phase_b["quality_gate"]["valid"] is False
    assert phase_b["quality_gate"]["top1_delta"] is None
    assert phase_b["quality_gate"]["root_rank_status"] == "ROOT_RANK_HARNESS_UNAVAILABLE"
    assert len(phase_b["fixed_node_runs"]) == 60
    assert len(phase_b["fixed_time_runs"]) == 120
    assert phase_b["performance_gate"]["passed"] is False
    assert report["selected_boundary"] == "F23Y_EVALUATOR_REPRESENTATION_REASSESSMENT"


def test_r1_fixed_time_matrix_is_complete_and_costs_are_decomposed():
    report, _ = _reports()
    phase_b = report["phase_b"]
    for seconds in ("0.25", "1.0"):
        for evaluator in ("v1", "candidate"):
            summary = phase_b["fixed_time_summary"][seconds][evaluator]
            assert summary["runs"] == 30
            assert summary["complete"] is True
            expected_profile_build_counts = [None] if evaluator == "v1" else [1]
            assert summary["profile_build_counts"] == expected_profile_build_counts
            assert summary["evaluator_time"] >= summary["context_time"]
            assert summary["aggregation_time"] >= 0
