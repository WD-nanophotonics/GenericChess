"""Regression checks for the audit-only F23V evaluator probe."""

import json
from pathlib import Path

from scripts import audit_f23v_minimal_analytic_evaluator as probe


ROOT = Path(__file__).resolve().parents[1]
SIGNAL = ROOT / "tests" / "fixtures" / "f23v_minimal_analytic_signal.json"


def test_f23v_fixture_records_failure_without_lowering_gates():
    report = json.loads(SIGNAL.read_text(encoding="utf-8"))
    assert report["plan_sha256"] == "426768dfc74d08db905c7440b1231759859386ac16a9cc9d51b5290d5a88a47e"
    assert report["passed"] is False
    assert report["selected_boundary"] == "F23W_EVALUATOR_SUPERVISION_STRATEGY_REASSESSMENT_R2"
    assert report["coverage"]["overall"]["admitted"] == 18
    assert all(report["coverage"]["by_group"][group]["admitted"] >= 6 for group in report["coverage"]["by_group"])
    assert report["coverage"]["overall"]["mean_top_set_precision"] < 0.70
    assert report["coverage"]["overall"]["optimal_hit"] < 0.75


def test_f23v_contract_and_mixed_mechanics():
    assert probe.FEATURE_NAMES == (
        "material_and_inventory",
        "safe_mobility_and_control",
        "attack_defense_and_anchor_safety",
        "forcing_capture_recapture",
        "capability_gated_promotion_drop",
    )
    assert probe.COEFFICIENTS == (1, 1, 1, 1, 1)
    assert probe._rename_invariance() == {"feature_vectors_equal": True, "scores_equal": True}
    assert probe._mixed_mechanic_smoke()["passes"] is True
    assert probe._complexity_audit()["forbidden_decision_strings"] == []
