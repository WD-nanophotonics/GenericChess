"""Permanent regressions for the additive F23V corrective probe."""

import inspect
import json
from pathlib import Path

from scripts import audit_f23v_minimal_analytic_evaluator_r1 as probe


ROOT = Path(__file__).resolve().parents[1]
SIGNAL = ROOT / "tests" / "fixtures" / "f23v_minimal_analytic_signal_r1.json"


def test_r1_frozen_mechanic_active_plan_reports_insufficient_exact_coverage():
    report = json.loads(SIGNAL.read_text(encoding="utf-8"))
    assert report["plan_sha256"] == "827e0c25baeb5e47f7308a314c7499ebcd9aeb402264a6096d01f216c15e9ccd"
    assert report["candidate_count"] if "candidate_count" in report else len(report["records"]) == 30
    assert report["passed"] is False
    assert report["failure_code"] == "INSUFFICIENT_MECHANIC_ACTIVE_EXACT_COVERAGE"
    assert report["selected_boundary"] == "F23W_EVALUATOR_SUPERVISION_STRATEGY_REASSESSMENT_R2"
    assert report["planned_active_coverage"]["SHOGI_LIKE"]["capture_to_hand"] >= 3
    assert report["planned_active_coverage"]["WESTERN_CHESS_LIKE"]["remove_from_game"] >= 2
    assert report["planned_active_coverage"]["MIXED_MECHANIC"]["path_special"] >= 2
    assert report["coverage"]["overall"]["admitted"] == 0


def test_r1_authoritative_child_terminal_recapture_and_pairwise_contracts():
    assert all(probe._child_contract_probe().values())
    assert all(probe._terminal_contract_probe().values())
    recapture = probe._recapture_probe()
    assert recapture["found"] is True
    assert recapture["history_increases_signal"] is True
    assert probe._strict_pairwise(1.0, 1.0) == "tied"
    assert probe._strict_pairwise(1.0, 0.5) == "correct"
    assert probe._strict_pairwise(0.5, 1.0) == "reversed"


def test_r1_semantic_authority_and_five_feature_invariance():
    source = inspect.getsource(probe.AnalyticEvaluatorR1)
    assert "pseudo_attacks" not in source
    assert probe._type_name_invariance()["feature_vectors_equal"] is True
    assert probe._type_name_invariance()["scores_equal"] is True
    assert probe._complexity_audit()["feature_method_count"] == 5
    assert probe.COEFFICIENTS == (1, 1, 1, 1, 1)
