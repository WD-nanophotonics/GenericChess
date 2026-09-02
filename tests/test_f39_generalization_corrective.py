import json
import subprocess
from pathlib import Path

from scripts.historical_validation import historical_scope_unchanged_worktree

ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / "tests" / "fixtures"


def load(name):
    return json.loads((FX / name).read_text(encoding="utf-8"))


def test_f39_rank_robustness_and_component_additivity_are_certified():
    robust = load("f39_rank_robustness.json")
    ablation = load("f39_component_ablation.json")
    assert robust["status"] == "PASS"
    assert robust["reproduced_f38_where_overlapping"] is True
    assert sum(robust["classification_counts"].values()) == 20
    assert ablation["status"] == "PASS"
    assert ablation["R37_COMPONENT_SCORE_ADDITIVITY"] is True
    assert len(ablation["rows"]) == 20
    assert all(set(row["child_decompositions"]) == {"target", "top_v1", "top_r37c"} for row in ablation["rows"])
    assert all(set(row["child_decompositions"]["target"]) == {"V1", "R37A", "R37B", "R37C"} for row in ablation["rows"])


def test_f39_diagnoses_broad_transfer_failure_without_selection():
    shift = load("f39_distribution_shift.json")
    search = load("f39_component_search.json")
    selection = load("f39_generalization_selection.json")
    assert shift["status"] == "PASS"
    assert set(shift["groups"]) == {"f37_selection_set", "f38_holdout"}
    assert len(search["rows"]) == 10
    assert all(set(row["counterfactuals"]) == {"R37A", "R37B"} for row in search["rows"])
    assert selection["aggregate_causal_classification"] == "BROAD_REPRESENTATION_TRANSFER_FAILURE"
    assert selection["selected_boundary"] == "F40_RULE_DERIVED_MATERIAL_AND_FEATURE_UTILIZATION_AUDIT"
    assert selection["F39_MUST_NOT_SELECT_R37A_OR_R37B_FOR_PRODUCTION"] is True
    assert all(selection["flags"].values())
    assert selection["f37_to_f38_reversal_matrix"]["R37B"]["transfer"] == "IN_SAMPLE_ONLY_SIGNAL"
    assert selection["f37_to_f38_reversal_matrix"]["R37C"]["transfer"] == "IN_SAMPLE_ONLY_SIGNAL"


def test_f39_production_scope():
    assert historical_scope_unchanged_worktree()
