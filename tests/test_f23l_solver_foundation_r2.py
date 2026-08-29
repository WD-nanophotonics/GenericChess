"""F23L capability-v3 and proof-window contracts."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import audit_f23l_solver_foundation as capability


ROOT = Path(__file__).parents[1]
HISTORICAL = (
    ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json",
    ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v2.json",
    ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v3.json",
    ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v4.json",
    ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v5.json",
    ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v6.json",
    ROOT / "tests" / "fixtures" / "evaluator_v2_candidate_spec_f23f.json",
    ROOT / "tests" / "fixtures" / "f23k_solver_capability_v1.json",
    ROOT / "tests" / "fixtures" / "f23k_solver_capability_v2.json",
)
V3 = ROOT / "tests" / "fixtures" / "f23l_solver_capability_v3.json"


def test_f23l_capability_v3_is_frozen_and_historical_artifacts_are_immutable():
    frozen = {path: path.read_bytes() for path in HISTORICAL}
    expected = json.loads(V3.read_text(encoding="utf-8"))
    assert {path: path.read_bytes() for path in frozen} == frozen
    assert expected["benchmark_version"] == "f23l-solver-foundation-v3"
    assert [row["construction_family"] for row in expected["rows"]] == [item[0] for item in capability.BENCHMARK_PLAN]


def test_f23l_uses_fixed_horizon_ladder_and_reports_branching_blocker():
    fixture = json.loads(V3.read_text(encoding="utf-8"))
    assert fixture["proof_budget_ladder"] == [
        ["SMALL", {"max_nodes": 2000, "max_depth": None}],
        ["MEDIUM", {"max_nodes": 20000, "max_depth": None}],
        ["LARGE", {"max_nodes": 100000, "max_depth": None}],
    ]
    assert fixture["attempt_wall_seconds"] == 8
    assert fixture["non_control_solved_families"] == 0
    assert fixture["capability_gate_passed"] is False
    assert fixture["dominant_blocker"] == "BRANCHING_EXPLOSION"
    assert all(row["first_resolving_tier"] is None for row in fixture["rows"])
    assert all(len(row["attempts"]) == 3 for row in fixture["rows"])
