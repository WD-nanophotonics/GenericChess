import hashlib
import json
from pathlib import Path

from scripts.audit_f23u_supervision_strategy import build_assessment


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
V12 = FIXTURES / "evaluator_v2_corpus_v12.json"


def test_f23u_is_diagnostic_and_preserves_v12():
    before = hashlib.sha256(V12.read_bytes()).hexdigest()
    result = build_assessment()
    assert result["source_v12_sha256"] == before
    assert result["v12_rewritten"] is False
    assert result["production_changed"] is False
    assert result["selected_boundary"] == "F23V_MINIMAL_ANALYTIC_EVALUATOR_SIGNAL_PROBE"


def test_f23u_corrects_r10_witness_and_metadata_free_orbits():
    result = build_assessment()["r10_corrected_reaudit"]
    assert result["strict_witness"]["current_count"] == 8
    assert result["strict_witness"]["causal_surviving_count"] == 8
    behavior = result["metadata_free_behavior"]
    assert behavior["raw_strict_count"] == 8
    assert behavior["raw_strict_orbit_count"] == 8
    assert behavior["deduplicated_strict_count"] == 8
    assert behavior["cross_split_collisions"] == []
    assert behavior["raw_effective_count"] == 7
    assert behavior["deduplicated_effective_orbit_count"] == 7
    assert behavior["cross_split_effective_collisions"] == []
    visibility = result["short_natural_terminal_visibility"]
    assert visibility["visible_count"] == 10
    assert visibility["by_family"] == {
        "drop_hand_terminal": 2,
        "interposition_leaper_terminal": 1,
        "ordinary_anchor_terminal": 5,
        "semantic_guard_terminal": 2,
    }


def test_f23u_historical_table_and_strategy_are_fixed():
    result = build_assessment()
    rows = {row["generation"]: row for row in result["historical_generations"]}
    assert [rows[name]["physical"] for name in ("V5", "V6", "V7", "V8", "V9", "V10", "V11", "V12")] == [30, 36, 40, 32, 24, 32, 48, 60]
    assert rows["V12"]["dev"] == 6 and rows["V12"]["holdout"] == 1
    table = result["strategy_comparison"]["table"]
    assert max(table, key=lambda row: row["total"])["strategy"] == "B_ANALYTIC_RULE_DERIVED_EVALUATOR"
    assert result["production_complexity_budget"]["feature_families"] == 5
    assert result["minimal_next_experiment"]["name"] == "MINIMAL_ANALYTIC_EVALUATOR_SIGNAL_PROBE"


def test_f23u_architecture_audit_has_no_missing_primitive():
    result = build_assessment()["genericity_checkpoint"]
    assert result["implementation_in_f23u"] is False
    assert "no game-name branches" in result["mixed_mechanic_acceptance_target"]
    audit = build_assessment()["production_complexity_budget"]
    assert audit["game_specific_branches"] == 0
