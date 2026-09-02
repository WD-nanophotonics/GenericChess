from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_h49c_closeout_freezes_blocker_without_measurement_claims():
    evidence = json.loads((ROOT / "tests" / "fixtures" / "h49c_f49_architectural_blocker_closeout.json").read_text(encoding="utf-8"))
    assert evidence["classification"] == "BLOCKED_ARCHITECTURAL_TRANSPORT"
    assert evidence["causal_finding"] == "CANONICAL_SEMANTIC_RULESET_NOT_REPRESENTABLE_BY_CURRENT_LEGACY_NATIVE_SEARCH_TRANSPORT"
    assert evidence["next_boundary"] == "F50_SEMANTIC_NATIVE_SEARCH_EXECUTION_PATH"
    assert evidence["F50_status"] == "NOT_STARTED"
    assert evidence["f49_scientific_hypotheses"] == "NOT_MEASURED_DUE_TO_PREREQUISITE_FAILURE"
    assert evidence["valid_f49_native_search_matrix_exists"] is False
    assert evidence["valid_f49_python_search_matrix_exists"] is False
    assert evidence["selector_classification_inferred"] is False
    assert evidence["production_diff"] == "ZERO"
    assert evidence["S49_regenerated"] is False
    assert all(row["evidentiary_status"] == "NONE" for row in evidence["aborted_run_records"].values())

