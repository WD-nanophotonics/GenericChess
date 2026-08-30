"""Deterministic F23W strategy-assessment checks."""

import json
from pathlib import Path

from scripts import audit_f23w_evaluator_strategy_r2 as assessment


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "f23w_evaluator_strategy_r2.json"


def test_f23w_selects_layered_validation_and_preserves_frozen_evidence():
    report = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert report["status"] == "ASSESSMENT_COMPLETE"
    assert report["selected_philosophy"] == "LOCAL_METAMORPHIC_PLUS_REAL_GAME_SEARCH_SHADOW"
    assert report["selected_boundary"] == "F23X_MINIMAL_ANALYTIC_EVALUATOR_METAMORPHIC_AND_SHOGI_SHADOW"
    assert report["f23v_closure"]["exact_supervision_default"] == "RETIRED"
    assert report["artifact_integrity"]["all_match"] is True
    assert report["f22_evidence"]["position_count"] == 10
    assert report["f22_evidence"]["reference_count"] == 10


def test_f23w_contract_matrix_context_and_preregistered_shadow():
    report = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(report["metamorphic_contract_matrix"]) == 10
    assert {row["feature"] for row in report["metamorphic_contract_matrix"]} == set(assessment.FEATURES)
    assert report["evaluation_context_design"]["one_shared_read_only_pass"] is True
    assert report["standard_shogi_shadow_plan"]["source"]["positions"] == 10
    assert report["standard_shogi_shadow_plan"]["quality_gate"]["candidate_reference_top1_agreement_delta"] == ">= +2 positions out of 10 over evaluator-v1 OR"
    assert report["standard_shogi_shadow_plan"]["performance_gate"]["candidate_evaluator_fraction"] == "<= 25% of total search wall time"
    assert report["evaluator_v1"]["available_for_standard_shogi"] is True
    assert report["f23x_implemented"] is False
