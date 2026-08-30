"""Regression tests for the F24A minimal cheap evaluator signal probe."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "tests" / "fixtures" / "f24a_minimal_cheap_evaluator.json"


def _report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_f24a_freezes_four_terms_and_passes_preflight():
    report = _report()
    formula = report["frozen_formula"]
    assert formula["concepts"] == [
        "material_and_inventory",
        "rule_derived_positional_capability",
        "bounded_anchor_structural_space",
        "promotion_and_drop_structural_capability",
    ]
    assert formula["coefficients"] == "none"
    assert report["preflight"]["passed"] is True
    assert report["preflight"]["formula_contracts"]["passed"] is True
    assert report["preflight"]["type_name_invariance"]["passed"] is True
    assert report["preflight"]["mixed_mechanic_applicability"]["passed"] is True
    assert report["preflight"]["no_dynamic_hot_path"]["passed"] is True
    assert report["preflight"]["f22_hashes"]["matches_f23y_ledger"] is True


def test_f24a_micro_gate_and_boundary_are_recorded_without_lowering_gates():
    report = _report()
    micro = report["micro_gate"]
    assert micro["full_descriptor_count"] == 48
    assert micro["shogi_subset_count"] == 40
    assert micro["passed"] is True
    assert micro["median_ratio"] <= 2.0
    assert micro["p95_ratio"] <= 3.0
    assert report["shogi_search_allowed"] is True
    assert report["fixed_search"]["v1_harness_parity"]["passed"] is True
    assert report["fixed_search"]["fixed_time_passed"] is True
    assert report["fixed_search"]["quality_gate"]["valid"] is True
    assert report["fixed_search"]["quality_gate"]["passed"] is False
    assert report["fixed_search"]["quality_gate"]["top1_delta"] < 2
    assert report["selected_boundary"] == "F24B_MIXED_MECHANIC_RULESET_CERTIFICATION"
    assert report["defer_evaluator_v2"] is True


def test_f24a_preserves_prior_evidence_and_keeps_production_untouched():
    report = _report()
    assert report["artifact_identity"]["f23z_files_unchanged"] is True
    assert report["production_changed"] is False
    assert report["master_locked"] is True
    assert report["evidence_classes"] == {
        "playing_strength": "NOT_RUN",
        "real_game": "REAL_GAME_BENCHMARK_EVIDENCE",
        "semantic": "SEMANTIC_CONTRACT_EVIDENCE",
    }
