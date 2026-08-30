"""Regression tests for the bounded F23Y P0/P1 context performance probe."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "tests" / "fixtures" / "f23y_context_performance.json"


def _report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_f23y_preflight_proves_m9_and_contract_specific_renaming():
    report = _report()
    preflight = report["preflight"]
    assert preflight["passed"] is True
    m9 = preflight["m9_positive_gain"]
    assert m9["passed"] is True
    assert m9["promotion_action_only_after"] is True
    assert m9["base_type"] == "P"
    assert m9["promotion_target"] == "G"
    assert m9["promotion_gain"] > 0
    rename = preflight["contract_specific_rename"]
    assert rename["contract_count"] == 10
    assert rename["variant_count"] == 14
    assert rename["passed"] is True
    assert all(row["passed"] for row in rename["rows"])


def test_f23y_p1_has_exact_semantic_and_mathematical_parity():
    report = _report()
    parity = report["p1_parity"]
    assert parity["passed"] is True
    assert parity["context_math"]["state_count"] == 48
    assert parity["bulk_semantic"]["attack"]["passed"] is True
    assert parity["bulk_semantic"]["legal_action"]["passed"] is True
    assert parity["bulk_semantic"]["check"]["passed"] is True
    assert parity["metamorphic_delta"]["contract_count"] == 10
    assert parity["metamorphic_delta"]["variant_count"] == 14
    assert parity["metamorphic_delta"]["passed"] is True


def test_f23y_records_performance_and_quality_boundaries_honestly():
    report = _report()
    assert report["micro_cost"]["state_count"] == 48
    assert len(report["preflight"]["microbenchmark"]["descriptors"]) == 48
    assert report["preflight"]["microbenchmark"]["descriptor_sha256"]
    assert report["micro_cost"]["summaries"]["P1"]["speedup_vs_P0"] > 1
    assert report["fixed_time"]["summaries"]["0.25"]["gates"]["paired_median_nps_ratio"] < 0.35
    assert report["fixed_time"]["summaries"]["1.0"]["gates"]["paired_median_nps_ratio"] < 0.35
    quality = report["fixed_node"]["quality_gate"]
    assert quality["valid"] is True
    assert quality["top1_delta"] == -1
    assert quality["controls_passed"] is False
    assert quality["root_rank_status"] == "ROOT_RANK_HARNESS_UNAVAILABLE"
    assert report["native_routing_policy"] == ["PYTHON_AUTHORITY_FALLBACK"]
    assert report["artifact_integrity"]["all_match"] is True
    assert report["production_changed"] is False
    assert report["selected_boundary"] == "F23Z_EVALUATOR_REPRESENTATION_REASSESSMENT"
