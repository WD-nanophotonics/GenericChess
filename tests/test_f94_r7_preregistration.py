from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs/architecture/GENERICCHESS_F94_R7_PREREGISTRATION_V1.json"


def test_r7_preregistration_is_frozen_and_zero_compute():
    payload = json.loads(PREREG.read_text(encoding="utf-8"))
    assert payload["schema"] == "generic-chess-f94-r7-layer-d-preregistration-v1"
    assert payload["status"] == "FROZEN_PROSPECTIVE_NO_DATA_COLLECTED"
    assert payload["compute_boundary"] == {"new_arena_authorized": False, "new_heavy_authorized": False, "compute_plan_required_before_execution": True, "classifier_mutation_allowed": False}
    assert payload["budget_response_gate"]["primary_endpoint"] == "4096_vs_256"
    assert payload["budget_response_gate"]["diagnostic_matchups"] == ["1024_vs_256", "4096_vs_1024"]
    assert payload["budget_response_gate"]["strict_negative_reversal_guard"]["definition"].startswith("A pair_score strictly less than 0.5")


def test_r7_tapes_are_fresh_and_fallback_strata_are_not_merged():
    payload = json.loads(PREREG.read_text(encoding="utf-8"))
    tapes = payload["fresh_disjoint_tapes"]
    assert tapes["tape_seeds"] == [9811, 9812, 9813]
    assert not set(tapes["tape_seeds"]) & set(tapes["excluded_r6_tape_seeds"])
    strata = payload["fallback_strata"]
    assert strata["LOW_BUDGET_PRE_ITERATION_NODE_FALLBACK"]["blocking"] is False
    assert strata["HIGH_BUDGET_PRE_ITERATION_NODE_FALLBACK"]["blocking"] is True
    assert strata["OPERATIONAL_OR_ABORT_FALLBACK"]["blocking"] is True
    assert strata["UNCLASSIFIED_OR_POST_ITERATION_FALLBACK"]["blocking"] is True


def test_r7_result_schema_and_regression_fixtures_are_explicit():
    payload = json.loads(PREREG.read_text(encoding="utf-8"))
    schema = payload["result_schema"]
    assert schema["schema"] == "generic-chess-f94-r7-layer-d-authority-result-v1"
    assert schema["response_matrix_key"] == "(control, tape_seed, pair_index)"
    assert "fallback_records" in schema["required_observation"]
    assert "tests/test_f94_r7_preregistration.py" in payload["regression_fixtures"]["tests"]
    assert payload["regression_fixtures"]["no_new_games"] is True
    assert payload["authority"] == "prospective_design_only"
    assert payload["r6_reinterpretation"] == "forbidden"
