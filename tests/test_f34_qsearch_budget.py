import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f34_qsearch_budget_manifest.json"
RESULT = ROOT / "tests" / "fixtures" / "f34_qsearch_budget_matrix.json"
SAFETY = ROOT / "tests" / "fixtures" / "f34_qsearch_tactical_safety.json"
SELECTION = ROOT / "tests" / "fixtures" / "f34_qsearch_budget_selection.json"


def test_f34_budget_architecture_selection_is_frozen():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    safety = json.loads(SAFETY.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    assert manifest["manifest_sha256"] == "6a5600c4fc1fb82582b42d47235fd72b4e02d60322749e1b97ebbae98500b75d"
    assert result["status"] == "PASS"
    assert result["production_changed"] is False
    assert result["selected_architecture"] == "Q34C"
    assert result["selected_soft_cap"] == "Q34A_SOFT_CAP_256"
    assert result["eligible_soft_caps"] == [16, 256]
    assert result["next_boundary"] == "F35_FIRST_ITERATION_QUIESCENCE_RESERVE_IMPLEMENTATION"
    assert result["budget_semantics"]["classification"] == "MIXED"
    assert all(result["budget_semantics"][key] for key in ("ordinary_noncheck_cap_hit", "in_check_cap_hit", "prior_completed_iteration", "no_prior_completed_iteration"))
    assert safety["status"] == "PASS"
    assert result["gates"]["Q34C"]["accessibility_material"] is True
    assert result["gates"]["Q34C"]["no_depth_regression_over_two"] is True
    assert result["gates"]["Q34B_D_MINUS_1"]["accessibility_material"] is True
    assert result["gates"]["Q34B_D"]["accessibility_material"] is False
    assert result["gates"]["Q34A_SOFT_CAP_256"]["accessibility_material"] is False
    assert selection["selected_architecture"] == "Q34C"
    assert selection["flags"]["QUIESCENCE_BUDGET_ARCHITECTURE_SELECTED"] is True
