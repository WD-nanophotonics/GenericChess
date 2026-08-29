"""F23D supervision, leakage, and no-fabricated-prototype contracts."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_f23d_evaluator_v2_prototype import (
    PREFERENCE_STRONG,
    PREFERENCE_WEAK,
    STRUCTURAL_ONLY,
    audit,
    classify_entry,
)


V2 = Path(__file__).parent / "fixtures" / "evaluator_v2_corpus_v2.json"


def test_f23d_classification_never_promotes_structural_labels():
    fixture = json.loads(V2.read_text(encoding="utf-8"))
    classes = {entry["id"]: classify_entry(entry) for entry in fixture["generic_exact"]}
    assert classes["generic-8x8-mate-capture"] == PREFERENCE_WEAK
    assert classes["generic-ray-5x5-capture-recapture-0"] == STRUCTURAL_ONLY
    assert classes["generic-semantic-nifu-r2-1"] == STRUCTURAL_ONLY
    assert PREFERENCE_STRONG not in classes.values()


def test_f23d_refuses_fit_without_strong_development_roots_and_seals_holdout():
    report = audit()
    assert report["status"] == "PASS"
    assert report["development_metrics"]["strong_roots"] == 0
    assert report["development_metrics"]["weak_roots"] > 0
    assert report["candidate_produced"] is False
    assert report["candidate_spec_sha256"] is None
    assert report["holdout"]["opened"] is False
    assert report["shogi_transfer"]["opened"] is False
    assert report["decision"]["selected_next_boundary"] == "F23E_REFERENCE_PREFERENCE_CORPUS"


def test_f23d_feature_selection_is_deterministic_and_bounded():
    report = audit()
    selection = report["feature_selection"]
    assert selection["selection_is_not_fitting"] is True
    assert len(selection["selected_for_future_prototype_only"]) <= 4
    assert len(set(selection["selected_for_future_prototype_only"])) == len(selection["selected_for_future_prototype_only"])
    assert report["production_changed"] is False


def test_f23d_baseline_metrics_are_separate_from_structural_cases():
    report = audit()
    metrics = report["development_metrics"]
    assert metrics["preference_roots_available"] == metrics["weak_roots"]
    assert metrics["strong_roots"] == 0
    assert isinstance(metrics["by_ruleset"], dict)
    assert metrics["prototype"] == "not_evaluated_no_preference_strong_supervision"
