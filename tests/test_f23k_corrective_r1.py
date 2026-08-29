"""F23K corrective soundness, horizon, and capability-v2 contracts."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import audit_f23k_solver_foundation_v2 as capability
from scripts import exact_generic_preference_solver_v2 as solver


ROOT = Path(__file__).parents[1]
V1 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json"
V2 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v2.json"
V3 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v3.json"
V4 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v4.json"
V5 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v5.json"
V6 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v6.json"
CAPABILITY_V1 = ROOT / "tests" / "fixtures" / "f23k_solver_capability_v1.json"
CAPABILITY_V2 = ROOT / "tests" / "fixtures" / "f23k_solver_capability_v2.json"


def test_f23k_corrective_rebuild_does_not_mutate_historical_artifacts():
    frozen = {path: path.read_bytes() for path in (V1, V2, V3, V4, V5, V6, CAPABILITY_V1)}
    expected = json.loads(CAPABILITY_V2.read_text(encoding="utf-8"))
    assert capability.build_report() == expected
    assert {path: path.read_bytes() for path in frozen} == frozen


def test_f23k_corrective_uses_authoritative_horizon_and_fixed_budget_ladder():
    fixture = json.loads(CAPABILITY_V2.read_text(encoding="utf-8"))
    assert fixture["horizon_mode"].startswith("max_depth=None")
    assert [tier for tier, _limits in capability.PROOF_BUDGET_LADDER] == ["SMALL", "MEDIUM", "LARGE"]
    assert all(limits["max_depth"] is None for _tier, limits in capability.PROOF_BUDGET_LADDER)
    assert all(row["first_resolving_tier"] is None for row in fixture["rows"])
    assert all(row["new"]["blocker"] == "NODE_EXPLOSION" for row in fixture["rows"])
    assert fixture["capability_gate_passed"] is False
    assert fixture["selected_next_boundary"] == "F23L_EXACT_REFERENCE_SOLVER_FOUNDATION_R2"


def test_f23k_corrective_unresolved_paths_never_cache_synthetic_zero_bounds():
    assert "_TTEntry(0" not in Path(solver.__file__).read_text(encoding="utf-8")
    assert "An unresolved descendant supplies no certified bound" in Path(solver.__file__).read_text(encoding="utf-8")
