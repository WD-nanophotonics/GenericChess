"""Focused F23X contract and benchmark-boundary regressions."""

import json
import inspect
from pathlib import Path

from scripts import audit_f23x_metamorphic_shogi_shadow as f23x


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "tests" / "fixtures" / "f23x_shogi_shadow.json"


def test_f23x_phase_a_is_exactly_ten_contracts_and_passes():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    phase_a = report["phase_a"]
    assert phase_a["contract_count"] == 10
    assert len(phase_a["contracts"]) == 10
    assert phase_a["passed"] is True
    assert all(row["passed"] for row in phase_a["contracts"])
    assert phase_a["context_parity"]["passed"] is True
    assert phase_a["renamed_equivalence"]["passed"] is True
    assert phase_a["complexity"]["passed"] is True


def test_f23x_phase_b_records_real_gate_failures_without_production_change():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    phase_b = report["phase_b"]
    assert report["phase_b_ran"] is True
    assert report["status"] == "FAIL"
    assert phase_b["search_harness_v1_parity"]["passed"] is True
    assert len(phase_b["fixed_node_runs"]) == 60
    assert len(phase_b["fixed_time_runs"]) == 120
    assert phase_b["quality_gate"]["top1_delta"] == -1
    assert phase_b["quality_gate"]["controls_passed"] is False
    assert phase_b["quality_gate"]["all_node_runs_complete"] is False
    assert phase_b["performance_gate"]["passed"] is False
    assert report["production_changed"] is False
    assert report["selected_boundary"] == "F23Y_EVALUATOR_REPRESENTATION_REASSESSMENT"


def test_f23x_candidate_is_audit_only_and_has_five_consumers():
    source = inspect.getsource(f23x.ContextAnalyticEvaluator)
    assert all(name in source for name in f23x.FEATURES)
    assert f23x.COEFFICIENTS == (1, 1, 1, 1, 1)
    assert "generic_chess" not in source.split("class ContextAnalyticEvaluator", 1)[1].split("class ShadowCandidateEvaluator", 1)[0]
    assert "reference" not in inspect.signature(f23x.ShadowCandidateEvaluator.evaluate).parameters
