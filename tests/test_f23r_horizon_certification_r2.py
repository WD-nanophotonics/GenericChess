"""F23R R2 deterministic ladder reconciliation contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import audit_f23r_horizon_certification_r2 as audit


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
V10 = FIXTURES / "evaluator_v2_corpus_v10.json"
R1 = FIXTURES / "f23r_v10_horizon_certification_r1.json"
R2 = FIXTURES / "f23r_v10_horizon_certification_r2.json"
ACTION = {"kind": "board", "from": [0, 0], "to": [0, 1], "promotion_target_id": None}


def _attempt(tier, status=None, causes=(), *, external=False):
    if external:
        result = {"action_values": [], "root_unresolved_causes": list(causes), "unresolved_reason": causes[0] if causes else None}
    else:
        proof = {"status": status, "necessary_unresolved_causes": list(causes)}
        result = {"action_values": [{"action": ACTION, "ge_win": proof, "ge_draw": proof, "value": None}], "root_unresolved_causes": list(causes)}
    return {"tier": tier, "result": result}


def test_synthetic_ladder_reconciliation_preserves_provenance():
    cases = [
        ([_attempt("SMALL", audit.abstraction.UNRESOLVED, [audit.abstraction.ABSTRACT_NODE_CAP]), _attempt("MEDIUM", audit.abstraction.UNRESOLVED, [audit.abstraction.MAX_PLY_ABSTRACT_LEAF])], "SEMANTIC_ONLY_UNRESOLVED"),
        ([_attempt("SMALL", audit.abstraction.UNRESOLVED, [audit.abstraction.MAX_PLY_ABSTRACT_LEAF, audit.abstraction.ABSTRACT_NODE_CAP]), _attempt("MEDIUM", audit.abstraction.UNRESOLVED, [audit.abstraction.MAX_PLY_ABSTRACT_LEAF])], "SEMANTIC_ONLY_UNRESOLVED"),
        ([_attempt("SMALL", audit.abstraction.UNRESOLVED, [audit.abstraction.MAX_PLY_ABSTRACT_LEAF]), _attempt("LARGE", external=True, causes=[audit.abstraction.ABSTRACT_TIME_CAP])], "SEMANTIC_ONLY_UNRESOLVED"),
        ([_attempt("SMALL", audit.abstraction.UNRESOLVED, [audit.abstraction.ABSTRACT_NODE_CAP]), _attempt("MEDIUM", audit.abstraction.UNRESOLVED, [audit.abstraction.ABSTRACT_NODE_CAP]), _attempt("LARGE", external=True, causes=[audit.abstraction.ABSTRACT_TIME_CAP])], "COMPUTATIONAL_ONLY_UNRESOLVED"),
        ([_attempt("SMALL", audit.abstraction.UNRESOLVED, [audit.abstraction.MAX_PLY_ABSTRACT_LEAF, audit.abstraction.ABSTRACT_NODE_CAP]), _attempt("MEDIUM", audit.abstraction.UNRESOLVED, [audit.abstraction.ABSTRACT_NODE_CAP]), _attempt("LARGE", external=True, causes=[audit.abstraction.ABSTRACT_TIME_CAP])], "MIXED_SEMANTIC_AND_COMPUTATIONAL_UNRESOLVED"),
        ([_attempt("SMALL", audit.abstraction.UNRESOLVED, [audit.abstraction.ABSTRACT_NODE_CAP]), _attempt("MEDIUM", audit.abstraction.PROVED_TRUE)], "EXACT"),
    ]
    for attempts, expected in cases:
        result = audit.reconcile_threshold(attempts, ACTION, "ge_win")
        assert result["reconciled_status"] == expected
    timeout_case = audit.reconcile_threshold(cases[2][0], ACTION, "ge_win")
    assert timeout_case["necessary_semantic_causes"] == [audit.abstraction.MAX_PLY_ABSTRACT_LEAF]
    assert timeout_case["necessary_computational_causes"] == []
    assert timeout_case["later_external_refusals"] == [{"tier": "LARGE", "causes": [audit.abstraction.ABSTRACT_TIME_CAP]}]


def test_r2_fixture_uses_development_only_quality_and_preserves_r1():
    v10 = json.loads(V10.read_text(encoding="utf-8"))
    r1 = json.loads(R1.read_text(encoding="utf-8"))
    r2 = json.loads(R2.read_text(encoding="utf-8"))
    assert r2["source_v10_fixture_sha256"] == hashlib.sha256(V10.read_bytes()).hexdigest()
    assert r2["source_r1_fixture_sha256"] == hashlib.sha256(R1.read_bytes()).hexdigest()
    assert len(r2["certifications"]) == 42
    assert r2["final_class_by_split"] == {
        "DEVELOPMENT": {"HORIZON_SENSITIVITY_UNKNOWN": 21, "HORIZON_STABLE_EXACT": 1, "MATERIALLY_MAX_PLY_DEPENDENT": 10},
        "HOLDOUT": {"HORIZON_SENSITIVITY_UNKNOWN": 3, "HORIZON_STABLE_EXACT": 2, "MATERIALLY_MAX_PLY_DEPENDENT": 5},
    }
    assert r2["summary"]["development_horizon_quality"] == 1
    assert r2["summary"]["development_material"] == 10
    assert r2["summary"]["holdout_material"] == 5
    assert r2["unknown_provenance_by_split"] == {
        "DEVELOPMENT": {"MIXED_SEMANTIC_AND_COMPUTATIONAL_UNRESOLVED": 10, "SEMANTICALLY_HORIZON_UNRESOLVED": 11},
        "HOLDOUT": {"COMPUTATIONALLY_UNRESOLVED": 2, "SEMANTICALLY_HORIZON_UNRESOLVED": 1},
    }
    assert r2["summary"]["max_ply_abstract_certified"] == 0
    assert r2["summary"]["horizon_stable_exact"] == 3
    assert r2["summary"]["materially_dependent"] == 15
    assert r2["summary"]["horizon_unknown"] == 24
    assert r2["frozen_non_horizon_gate_items"] == {key: value for key, value in v10["advancement_gate"]["items"].items() if key != "non_max_ply_minimum"}
    assert all(r2["frozen_non_horizon_gate_items"].values())
    assert r2["gate"]["passes"] is False
    assert r2["selected_next_boundary"] == "F23S_NATURAL_TERMINAL_REFERENCE_CORPUS_R9"
    assert r1["summary"]["horizon_unknown"] == 24
