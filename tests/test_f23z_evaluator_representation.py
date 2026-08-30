"""Regression tests for the final F23 evaluator representation reassessment."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "tests" / "fixtures" / "f23z_evaluator_representation.json"


def _report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_f23z_records_the_accepted_f23y_ledger_and_current_responsibilities():
    report = _report()
    ledger = report["accepted_f23y_evidence_ledger"]
    assert report["status"] == "PASS"
    assert ledger["semantic_contracts"] == "PASS"
    assert ledger["m9_positive_gain"] is True
    assert ledger["contract_specific_rename"] is True
    assert ledger["p0_p1_math_parity"] is True
    assert ledger["real_shogi_2048"] == {"controls_passed": False, "top1_delta": -1, "valid": True}
    assert ledger["playing_strength"] == "NOT_RUN"
    evidence = report["search_responsibility_evidence"]
    assert evidence["passed"] is True
    assert len(report["responsibility_matrix"]) == 10
    assert {row["class"] for row in report["responsibility_matrix"]} == {"LEAF_STRUCTURAL", "SEARCH_RESIDENT", "STATIC_PROXY_CANDIDATE", "REJECT_LEAF_HOT_PATH"}


def test_f23z_strategy_matrix_and_cheap_inputs_are_deterministic():
    report = _report()
    ranking = report["strategy_matrix"]["ranking"]
    assert ranking[0] == {"strategy": "CHEAP_RULE_DERIVED_LEAF_WITH_SEARCH_RESIDENT_TACTICS", "total": 72}
    assert report["strategy_matrix"]["score_scale"].startswith("1=poor fit")
    assert len(report["cheap_ruleset_ingredients"]) >= 6
    assert all(item["available"] is True and item["cross_ruleset"] is True for item in report["cheap_ruleset_ingredients"])
    assert report["selected_representation_philosophy"].startswith("generic adversarial search")


def test_f23z_freezes_a_bounded_f24a_without_implementing_it():
    report = _report()
    decision = report["decision"]
    assert decision["conclusion"] == "CONTINUE_WITH_MINIMAL_CHEAP_EVALUATOR"
    assert len(decision["basis"]) == 4
    assert "no semantic legal-action enumeration in evaluate()" in decision["frozen_constraints"]
    assert "no full-board semantic attack sweep in evaluate()" in decision["frozen_constraints"]
    assert decision["next_boundary"] == "F24A_MINIMAL_CHEAP_RULE_DERIVED_EVALUATOR_SIGNAL_PROBE"
    assert report["artifact_identity"]["f23y_files_unchanged"] is True
    assert report["artifact_identity"]["historical_f23x_r1_fixture_identity"] is True
    assert report["production_changed"] is False
    assert report["master_locked"] is True
