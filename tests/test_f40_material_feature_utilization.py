import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / "tests" / "fixtures"


def load(name):
    return json.loads((FX / name).read_text(encoding="utf-8"))


def test_f40_exact_material_recomposition_and_validation_gates():
    material = load("f40_material_prior_audit.json")
    western = material["profiles"]["western_chess"]
    shogi = material["profiles"]["standard_shogi"]
    assert western["CURRENT_PROFILE_EXACT_RECOMPOSITION"] is True
    assert shogi["CURRENT_PROFILE_EXACT_RECOMPOSITION"] is True
    assert material["western_human_validation"]["normalized_by_pawn"] == {"P": 1.0, "N": 775.0, "B": 1000.0, "R": 1462.0, "Q": 2439.0}
    assert material["western_human_validation"]["WESTERN_MATERIAL_PRIOR_SEVERE_PATHOLOGY"] is True
    metrics = material["standard_shogi_human_validation"]["metrics"]
    assert metrics["cosine"] >= 0.95
    assert metrics["spearman"] >= 0.90
    assert metrics["pairwise_ordering_accuracy"] >= 0.90


def test_f40_utilization_learning_native_and_boundary_selection():
    feature = load("f40_feature_utilization_ledger.json")
    learning = load("f40_learning_leverage_ledger.json")
    native = load("f40_native_consumption_sidecar.json")
    selection = load("f40_material_feature_selection.json")
    assert feature["drop_information"]["DROP_INFORMATION_COMPUTED_BUT_NOT_UTILIZED"] is True
    assert feature["MEANINGFUL_RULE_SIGNAL_UTILIZATION_GAP"] is True
    assert learning["MATERIAL_ONLY_LEARNING_CAPACITY_LOW_LEVERAGE"] is True
    assert native["SECOND_RULE_COMPILER_REQUIRED"] is False
    assert native["COMPILED_SEMANTIC_RESULTS_UNDERCONSUMED_BY_PRODUCT_SEARCH"] is True
    assert selection["aggregate_classification"] == "MATERIAL_AND_FEATURE_UTILIZATION_GAP"
    assert selection["selected_boundary"] == "F41_RULE_DERIVED_MATERIAL_PRIOR_AND_SIGNAL_UTILIZATION_CORRECTIVE"
    assert all(selection["flags"].values())


def test_f40_keeps_production_scope_zero():
    assert subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode == 0
