import json
from pathlib import Path

from scripts.f87a_phase_gate_reconciliation import reconcile
from scripts.f87a_ruleset_qualification import build_prep, run as run_qualification
from scripts.f87a_r9_western_dynamic_discovery import run as run_r9


def test_f87a_reconciliation_satisfies_frozen_playability_scope_without_opening_d_or_e(tmp_path):
    r9_result = run_r9(output_dir=tmp_path / "r9")
    prep_path = tmp_path / "qualification" / "manifest.json"
    result_dir = tmp_path / "qualification" / "results"
    root = Path(__file__).resolve().parents[1]
    build_prep(root, prep_path)
    run_qualification(root, prep_path, result_dir)
    qualification_reports = json.loads((result_dir / "reports.json").read_text(encoding="utf-8"))
    assert all(
        qualification_reports[name]["overall_status"] == "PASS"
        for name in ("Built-in Western Chess", "Built-in Standard Shogi")
    )
    result = reconcile(r9_result, qualification_reports)
    assert result["charter"]["declared_target"] == "PLAYABILITY"
    assert result["charter"]["required_layers"] == ["A", "B", "C"]
    assert result["scope_decision"] == "PLAYABILITY_SCOPE_SATISFIED"
    assert result["layers"]["A"]["status"] == "PASS"
    assert result["layers"]["B"]["status"] == "DIAGNOSTIC_ONLY"
    assert result["layers"]["C"]["status"] == "PASS"
    assert result["deferred_follow_on"] == {"D": "DEFERRED_IN_F87A", "E": "DEFERRED_IN_F87A"}
    assert result["promotion_decision"] == "NOT_GRANTED_BY_SCOPE_RECONCILIATION"


def test_f87a_reconciliation_rejects_unreconciled_termination_evidence():
    unreconciled = {
        "dynamic_viability_pass": False,
        "search_budget_censored_count": 0,
        "terminal_discovery_count": 1,
    }
    try:
        reconcile(unreconciled, {})
    except ValueError as exc:
        assert "termination-viability" in str(exc)
    else:
        raise AssertionError("unreconciled R9 evidence must fail closed")


def test_f87a_reconciliation_rejects_nonpassing_positive_report():
    r9_result = {
        "dynamic_viability_pass": True,
        "search_budget_censored_count": 0,
        "terminal_discovery_count": 1,
        "horizon_censored_count": 5,
    }
    report = {
        "blocking_layers": ["A", "C"],
        "layers": {"A": "PASS", "C": "PASS"},
        "overall_status": "DEFER",
    }
    reports = {
        "Built-in Western Chess": report,
        "Built-in Standard Shogi": {**report, "overall_status": "PASS"},
    }
    try:
        reconcile(r9_result, reports)
    except ValueError as exc:
        assert "must pass overall" in str(exc)
    else:
        raise AssertionError("non-passing positive QualificationReport must fail closed")
