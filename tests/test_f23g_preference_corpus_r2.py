"""F23G deep exact-preference corpus and solver contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23e_preference_corpus as f23e
from scripts import build_f23g_preference_corpus_r2 as f23g
from scripts.audit_f23g_decision_orbits import audit
from scripts import exact_generic_preference_solver as solver
from scripts.exact_generic_preference_solver import decision_subtree_fingerprint, solve_root


ROOT = Path(__file__).parents[1]
V1 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v1.json"
V2 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v2.json"
V3 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v3.json"
V4 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v4.json"
F23F_SPEC = ROOT / "tests" / "fixtures" / "evaluator_v2_candidate_spec_f23f.json"


def test_f23g_rebuild_is_deterministic_and_prior_artifacts_are_byte_immutable():
    frozen = {path: path.read_bytes() for path in (V1, V2, V3, F23F_SPEC)}
    expected = json.loads(V4.read_text(encoding="utf-8"))
    assert f23g.build_corpus() == expected
    assert {path: path.read_bytes() for path in frozen} == frozen
    assert expected["source_v3_sha256"] == hashlib.sha256(frozen[V3]).hexdigest()


def test_f23g_deep_gate_has_non_immediate_multiruleset_ordinary_reply_roots():
    fixture = json.loads(V4.read_text(encoding="utf-8"))
    deep = [entry for entry in fixture["generic_exact"] if entry["id"].startswith("generic-deep-")]
    dev = [entry for entry in deep if entry["split"] == "DEVELOPMENT"]
    holdout = [entry for entry in deep if entry["split"] == "HOLDOUT"]
    assert len(deep) == 30
    assert len(dev) == 25
    assert len(holdout) == 5
    assert len({entry["ruleset_id"] for entry in dev}) == 5
    assert max(sum(entry["ruleset_id"] == rid for entry in dev) for rid in {entry["ruleset_id"] for entry in dev}) <= len(dev) * 0.35
    assert sum(entry["preference_authority"]["proof_depth_class"] == "MULTIPLY_DEPENDENT" for entry in dev) >= 8
    assert not any(entry["preference_authority"]["max_ply_dependence"] for entry in deep)
    assert all(min(entry["preference_authority"]["optimal_proof_depths"]) >= 2 for entry in deep)
    assert sum(len({row["value"] for row in entry["preference_authority"]["all_root_action_values"]}) > 1 for entry in dev) > len(dev) / 2


def test_f23g_known_deep_root_has_two_reply_proof_and_strict_wdl_preference():
    m = f23c._imports()
    compiled, pieces = f23g._semantic_variant(m, 0)
    state = m["make_state"](compiled, f23g._rows(5, pieces))
    result = solve_root(compiled, state, max_nodes=30000, max_depth=6)
    assert result.strong is True
    assert result.root_value == "DRAW"
    assert max(item["proof_depth"] for item in result.action_values if item["value"] == "DRAW") == 5
    assert any(item["value"] == "LOSS" for item in result.action_values)
    assert result.stats["cap_hits"] == 0
    assert result.stats["cycle_edges"] == 0


def test_f23g_solver_preserves_f23e_immediate_classification():
    m = f23c._imports()
    case = f23e._case_specs(m)[0]
    result = solve_root(case["compiled"], case["state_object"], max_nodes=5000, max_depth=1)
    assert result.strong is True
    assert all(item["proof_depth"] == 1 for item in result.action_values)


def test_f23g_solver_refuses_node_and_depth_caps_without_guessing():
    m = f23c._imports()
    compiled, pieces = f23g._semantic_variant(m, 0)
    state = m["make_state"](compiled, f23g._rows(5, pieces))
    for max_nodes, max_depth in ((0, 1), (5000, 0)):
        result = solve_root(compiled, state, max_nodes=max_nodes, max_depth=max_depth)
        assert result.strong is False
        assert result.root_value is None
        assert result.unresolved_reason.startswith("REFERENCE_SOLVE_UNRESOLVED:")
        assert result.stats["cap_hits"] > 0


def test_f23g_solver_refuses_an_active_stack_cycle():
    m = f23c._imports()
    case = f23e._case_specs(m)[0]
    action, _child = solver.legal_successors(case["state_object"], case["compiled"])[0]
    with patch.object(solver, "legal_successors", return_value=((action, case["state_object"]),)):
        result = solve_root(case["compiled"], case["state_object"], max_nodes=100, max_depth=10)
    assert result.strong is False
    assert result.unresolved_reason == "REFERENCE_SOLVE_UNRESOLVED:cycle"
    assert result.stats["cycle_edges"] > 0


def test_f23g_solver_has_no_evaluator_or_f23f_sampling_dependency():
    source = (ROOT / "scripts" / "exact_generic_preference_solver.py").read_text(encoding="utf-8")
    builder = (ROOT / "scripts" / "build_f23g_preference_corpus_r2.py").read_text(encoding="utf-8")
    assert "Evaluator" not in source
    assert "generic_chess.ai" not in builder
    assert "generic_chess.learning" not in builder


def test_f23g_behavioral_orbits_collapse_inert_hands_and_detect_leakage():
    result = audit()
    assert result["physical_corpus_rows"] == 30
    assert result["canonical_state_identity_count"] == 30
    assert result["effective_decision_orbit_count"] == 5
    assert set(result["duplicate_multiplicity_per_orbit"].values()) == {6}
    assert result["decision_orbit_split_leakage_count"] == 4
    assert result["eligible_development_orbits_after_leakage_exclusion"] == 1
    assert result["eligible_holdout_orbits_after_leakage_exclusion"] == 0
    assert result["corrected_deep_supervision_gate"]["passes"] is False


def test_f23g_behavioral_fingerprint_changes_when_a_reply_branch_changes():
    m = f23c._imports()
    compiled, pieces = f23g._semantic_variant(m, 0)
    base = m["make_state"](compiled, f23g._rows(5, pieces))
    changed_pieces = dict(pieces)
    del changed_pieces[(2, 2)]
    changed_pieces[(2, 1)] = "b"
    changed = m["make_state"](compiled, f23g._rows(5, changed_pieces))
    base_fp = decision_subtree_fingerprint(compiled, base, max_nodes=30000, max_depth=6)
    changed_fp = decision_subtree_fingerprint(compiled, changed, max_nodes=30000, max_depth=6)
    assert base_fp != changed_fp
