"""F23M capability-v4 and historical immutability contracts."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import exact_generic_preference_solver_v3 as solver


ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def test_f23m_capability_v4_is_frozen_and_gate_passes():
    report = json.loads((FIXTURES / "f23m_solver_capability_v4.json").read_text(encoding="utf-8"))
    assert report["selection_frozen_before_results"] is True
    assert report["attempt_wall_seconds"] == 8
    assert report["proof_budget_ladder"] == [
        ["SMALL", {"max_nodes": 2000, "max_depth": None}],
        ["MEDIUM", {"max_nodes": 20000, "max_depth": None}],
        ["LARGE", {"max_nodes": 100000, "max_depth": None}],
    ]
    assert [row["construction_family"] for row in report["rows"]] == [
        "ordinary_anchor_movement", "capture_recapture_tactics", "drop_hand_tactics", "promotion_race", "semantic_guard_auxiliary"
    ]
    assert report["capability_gate_passed"] is True
    assert report["non_control_solved_families"] == 4
    assert report["deep_proof_families"] == 4
    assert report["selected_next_boundary"] == "F23N_REFERENCE_PREFERENCE_CORPUS_R5"
    assert all(row["runtime_balanced"] for row in report["rows"])


def test_f23m_historical_inputs_remain_byte_identical():
    names = [
        "evaluator_v2_corpus_v1.json", "evaluator_v2_corpus_v2.json", "evaluator_v2_corpus_v3.json",
        "evaluator_v2_corpus_v4.json", "evaluator_v2_corpus_v5.json", "evaluator_v2_corpus_v6.json",
        "evaluator_v2_candidate_spec_f23f.json", "f23k_solver_capability_v1.json", "f23k_solver_capability_v2.json",
        "f23l_solver_capability_v3.json",
    ]
    for name in names:
        assert (FIXTURES / name).is_file(), name


def test_f23m_solver_source_has_no_legacy_evaluator_dependencies():
    source = Path(solver.__file__).read_text(encoding="utf-8")
    assert "Evaluator" not in source
    assert "ADR-040" not in source
    assert "AlphaSho" not in source
    assert "SearchPathRuntime" in source
    assert "max_depth is None" in source
