"""Corrective F23R evidence-precedence, provenance, and engine fixtures."""

from __future__ import annotations

import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path

from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23g_preference_corpus_r2 as f23g
from scripts import exact_generic_preference_solver_v3 as v3
from scripts import exact_generic_horizon_abstraction_v2 as abstraction
from scripts import audit_f23r_horizon_certification_r1 as audit


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
V10 = FIXTURES / "evaluator_v2_corpus_v10.json"
FIRST_PASS = FIXTURES / "f23r_v10_horizon_certification.json"
R1_ENGINE = FIXTURES / "f23r_engine_horizon_cases_r1.json"
R1_CERTIFICATION = FIXTURES / "f23r_v10_horizon_certification_r1.json"
V10_SHA256 = "65ba64f17effb4e96977b59a806153efae49a91dcb28948c89a9d73290350a43"
FIRST_PASS_SHA256 = "9f943af715e3e2529db5e81d1715872d6c07dec9593b39f53ca08c565e8f1e6f"
ADR060_SHA256 = "a35acbab6214b5313221b2fd4455d3636026d6b0c26b527191fc717cbdb058b9"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _engine_case(spec):
    m = f23c._imports()
    compiled = m["make_compiled"](3, [m["king"](), m["rook"]()], repetition_limit=2, max_ply=spec["max_ply"])
    return compiled, m["make_state"](compiled, spec["rows"], side_to_move=spec["side_to_move"])


def _signature(result):
    return (
        tuple(sorted((json.dumps(item["action"], sort_keys=True), item["value"]) for item in result.action_values)),
        tuple(sorted(json.dumps(action, sort_keys=True) for action in result.optimal_actions)),
    )


def test_first_pass_f23r_evidence_is_untouched():
    first = _load(FIRST_PASS)
    assert hashlib.sha256(V10.read_bytes()).hexdigest() == V10_SHA256
    assert hashlib.sha256(FIRST_PASS.read_bytes()).hexdigest() == FIRST_PASS_SHA256
    assert hashlib.sha256((ROOT / "docs/architecture/ADR-060-horizon-reference-certification-foundation.md").read_bytes()).hexdigest() == ADR060_SHA256
    assert first["source_v10_fixture_sha256"] == V10_SHA256
    assert first["summary"]["unknown"] == 42


def test_pure_tree_is_complete_for_independent_u1_u2_leaves():
    trees = [
        ("node", True, [("leaf", "U1"), ("leaf", 1)]),
        ("node", False, [("leaf", "U1"), ("leaf", -1)]),
        ("node", True, [("leaf", "U1"), ("leaf", "U2")]),
        ("node", False, [("node", True, [("leaf", "U1"), ("leaf", 0)]), ("leaf", "U2")]),
    ]
    for tree in trees:
        for threshold in (0, 1):
            abstract = abstraction.tree_threshold(tree, threshold)
            assignments = [
                dict(zip(("U1", "U2"), values))
                for values in itertools.product((-1, 0, 1), repeat=2)
            ]
            concrete = [abstraction.concrete_tree_value(tree, assignment) >= threshold for assignment in assignments]
            expected = True if all(concrete) else False if not any(concrete) else None
            assert abstract is expected


def test_real_engine_fixtures_a_to_g():
    cases = _load(R1_ENGINE)["cases"]
    by_id = {case["id"]: case for case in cases}

    win, win_state = _engine_case(by_id["A_horizon_independent_win"])
    win_result = abstraction.solve_root_horizon_abstract_v2(win, win_state, max_nodes=5000)
    assert win_result.strong and win_result.root_value == "WIN"

    loss, loss_state = _engine_case(by_id["B_horizon_independent_loss"])
    loss_result = abstraction.solve_root_horizon_abstract_v2(loss, loss_state, max_nodes=5000)
    assert loss_result.strong and loss_result.root_value == "LOSS"

    draw, draw_state = _engine_case(by_id["C_horizon_independent_draw"])
    draw_result = abstraction.solve_root_horizon_abstract_v2(draw, draw_state, max_nodes=5000)
    assert draw_result.strong and draw_result.root_value == "DRAW"
    assert all(row["ge_win"]["status"] == abstraction.PROVED_FALSE for row in draw_result.action_values)
    assert all(row["ge_draw"]["status"] == abstraction.PROVED_TRUE for row in draw_result.action_values)

    shallow, shallow_state = _engine_case(by_id["D_base_draw_deeper_win"])
    deep_spec = dict(by_id["D_base_draw_deeper_win"], max_ply=3)
    deep, deep_state = _engine_case(deep_spec)
    shallow_exact = v3.solve_root_threshold_v3(shallow, shallow_state, max_nodes=5000)
    deep_exact = v3.solve_root_threshold_v3(deep, deep_state, max_nodes=5000)
    assert shallow_exact.root_value == "DRAW" and deep_exact.root_value == "WIN"
    shallow_abstract = abstraction.solve_root_horizon_abstract_v2(shallow, shallow_state, max_nodes=5000)
    assert not shallow_abstract.strong
    assert abstraction.MAX_PLY_ABSTRACT_LEAF in shallow_abstract.root_unresolved_causes

    irrelevant, irrelevant_state = _engine_case(by_id["E_irrelevant_max_ply_branch"])
    irrelevant_result = abstraction.solve_root_horizon_abstract_v2(irrelevant, irrelevant_state, max_nodes=5000)
    assert irrelevant_result.strong and irrelevant_result.root_value == "LOSS"
    assert irrelevant_result.stats["max_ply_abstract_leaves"] > 0
    assert all(not row["max_ply_dependency"] for row in irrelevant_result.action_values)

    mixed, mixed_state = _engine_case(by_id["F_mixed_root"])
    mixed_result = abstraction.solve_root_horizon_abstract_v2(mixed, mixed_state, max_nodes=5000)
    assert not mixed_result.strong
    assert any(row["value"] is not None for row in mixed_result.action_values)
    assert any(row["value"] is None for row in mixed_result.action_values)

    tied, tied_state = _engine_case(by_id["G_exact_tied_optimal_actions"])
    tied_result = abstraction.solve_root_horizon_abstract_v2(tied, tied_state, max_nodes=5000)
    assert tied_result.strong and tied_result.root_value == "WIN"
    assert len(tied_result.optimal_actions) >= 2


def test_tt_and_traversal_order_preserve_engine_certificates():
    m = f23c._imports()
    compiled, pieces = f23g._semantic_variant(m, 0)
    state = m["make_state"](compiled, f23g._rows(5, pieces))
    tt = abstraction.solve_root_horizon_abstract_v2(compiled, state, max_nodes=5000, use_tt=True)
    no_tt = abstraction.solve_root_horizon_abstract_v2(compiled, state, max_nodes=5000, use_tt=False)
    reverse = abstraction.solve_root_horizon_abstract_v2(compiled, state, max_nodes=5000, reverse_actions=True)
    assert tt.strong == no_tt.strong == reverse.strong is True
    assert _signature(tt) == _signature(no_tt)
    assert _signature(tt) == _signature(reverse)
    assert tt.stats["threshold_tt_entries"] > 0
    assert no_tt.stats["threshold_tt_entries"] == 0


def test_proof_local_short_circuit_discards_irrelevant_max_ply_causes():
    tree = ("node", True, [("leaf", "U1"), ("leaf", 1)])
    assert abstraction.tree_threshold(tree, 1) is True


def test_f23q_secondary_evidence_has_precedence_over_unresolved_abstraction():
    v10 = _load(V10)
    first = _load(FIRST_PASS)
    assert Counter(row["horizon_dependence"] for row in v10["effective_preference_representatives"]) == Counter({
        "HORIZON_SENSITIVITY_UNKNOWN": 24,
        "MATERIALLY_MAX_PLY_DEPENDENT": 15,
        "HORIZON_STABLE_EXACT": 3,
    })
    assert first["summary"]["unknown"] == 42
    material = next(row for row in v10["effective_preference_representatives"] if row["horizon_dependence"] == "MATERIALLY_MAX_PLY_DEPENDENT")
    stable = next(row for row in v10["effective_preference_representatives"] if row["horizon_dependence"] == "HORIZON_STABLE_EXACT")
    assert audit._secondary_evidence(material)["accepted_class"] == "MATERIALLY_MAX_PLY_DEPENDENT"
    assert audit._secondary_evidence(stable)["accepted_class"] == "HORIZON_STABLE_EXACT"


def test_corrective_fixture_reconciles_all_42_roots_and_retains_evidence():
    v10 = _load(V10)
    first = _load(FIRST_PASS)
    r1 = _load(R1_CERTIFICATION)
    assert r1["source_v10_fixture_sha256"] == V10_SHA256
    assert r1["first_pass_f23r_fixture_sha256"] == FIRST_PASS_SHA256
    assert r1["source_effective_count"] == 42
    assert sum(r1["summary"][key] for key in ("max_ply_abstract_certified", "horizon_stable_exact", "materially_dependent", "horizon_unknown")) == 42
    assert r1["summary"]["f23q_secondary_counts"] == {
        "HORIZON_SENSITIVITY_UNKNOWN": 24,
        "HORIZON_STABLE_EXACT": 3,
        "MATERIALLY_MAX_PLY_DEPENDENT": 15,
    }
    assert r1["summary"]["max_ply_abstract_certified"] == 0
    assert r1["summary"]["horizon_stable_exact"] == 3
    assert r1["summary"]["materially_dependent"] == 15
    assert r1["summary"]["horizon_unknown"] == 24
    assert r1["summary"]["unknown_kinds"] == {
        "COMPUTATIONALLY_UNRESOLVED": 2,
        "MIXED_SEMANTIC_AND_COMPUTATIONAL_UNRESOLVED": 10,
        "SEMANTICALLY_HORIZON_UNRESOLVED": 12,
    }
    assert r1["summary"]["abstract_base_contradictions"] == 0
    assert r1["summary"]["abstract_material_evidence_contradictions"] == 0
    material = [item for item in r1["certifications"].values() if item["classification"] == "MATERIALLY_MAX_PLY_DEPENDENT"]
    stable = [item for item in r1["certifications"].values() if item["classification"] == "HORIZON_STABLE_EXACT"]
    assert all(item["secondary_f23q"]["alternate_differences"] for item in material)
    assert all(set(item["secondary_f23q"]["exact_resolving_tiers"]) >= {"base", "plus_2", "plus_4"} for item in stable)
    assert r1["gate"]["passes"] is False
    assert r1["selected_next_boundary"] == "F23S_NATURAL_TERMINAL_REFERENCE_CORPUS_R9"
    assert r1["production_changed"] is False and r1["v10_rewritten"] is False
    assert first["summary"]["unknown"] == 42
