"""Final R2 admission-contract regressions."""

import json
import inspect
from pathlib import Path

from scripts import audit_f23v_minimal_analytic_evaluator_r1 as r1
from scripts import audit_f23v_minimal_analytic_evaluator_r2 as r2


ROOT = Path(__file__).resolve().parents[1]
SIGNAL = ROOT / "tests" / "fixtures" / "f23v_minimal_analytic_signal_r2.json"


def test_r2_uses_exact_eight_second_admission_and_stops_phase_a():
    report = json.loads(SIGNAL.read_text(encoding="utf-8"))
    assert r2.REFERENCE_WALL_SECONDS == 8
    assert report["reference_contract"] == {"abstraction_max_nodes": 100000, "isolated_wall_seconds": 8, "v3_max_nodes": 100000}
    assert report["stopped_at"] == "PHASE_A"
    assert report["failure_code"] == "INSUFFICIENT_MECHANIC_ACTIVE_EXACT_COVERAGE"
    assert report["replacement_plan_created"] is False
    assert report["scoring_started"] is False


def test_r2_runs_abstraction_despite_global_max_ply_diagnostic():
    report = json.loads(SIGNAL.read_text(encoding="utf-8"))
    synthetic = report["synthetic_max_ply_proof_regression"]
    assert synthetic["passes"] is True
    assert synthetic["strong"] is True
    assert synthetic["max_ply_visited_diagnostic"] > 0
    assert synthetic["r1_policy_would_reject"] is True
    assert report["strong_v3_max_ply_visitation_abstraction_ran"] > 0
    assert report["strong_abstraction_certifications_with_nonzero_max_ply"] > 0
    assert "_no_max_ply_dependency" not in inspect.getsource(r2._phase_a)
    assert r1._no_max_ply_dependency(synthetic) is not None


def test_r2_enforces_structural_preflight_without_replacing_frozen_plan():
    report = json.loads(SIGNAL.read_text(encoding="utf-8"))
    preflight = report["structural_preflight"]
    assert preflight["passes"] is False
    assert preflight["checks"]["SHOGI_LIKE"]["promotion"] is False
    assert preflight["planned_active_coverage"]["SHOGI_LIKE"]["promotion"] == 2
    assert preflight["planned_active_coverage"]["MIXED_MECHANIC"]["drop"] == 0
    assert report["viability"]["admitted_counts"] == {"MIXED_MECHANIC": 3, "SHOGI_LIKE": 0, "WESTERN_CHESS_LIKE": 1}
