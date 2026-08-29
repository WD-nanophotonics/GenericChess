"""F23E exact preference-solver, provenance, and immutability contracts."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23e_preference_corpus as f23e
from scripts.exact_generic_preference_solver import solve_root


V1 = Path(__file__).parent / "fixtures" / "evaluator_v2_corpus_v1.json"
V2 = Path(__file__).parent / "fixtures" / "evaluator_v2_corpus_v2.json"
V3 = Path(__file__).parent / "fixtures" / "evaluator_v2_corpus_v3.json"


def test_f23e_v1_v2_are_byte_immutable_and_v3_rebuilds_deterministically():
    v1_before, v2_before = V1.read_bytes(), V2.read_bytes()
    expected = json.loads(V3.read_text(encoding="utf-8"))
    assert f23e.build_corpus() == expected
    assert V1.read_bytes() == v1_before
    assert V2.read_bytes() == v2_before
    assert expected["source_v1_sha256"] == __import__("hashlib").sha256(v1_before).hexdigest()
    assert expected["source_v2_sha256"] == __import__("hashlib").sha256(v2_before).hexdigest()


def test_f23e_strong_gate_has_diverse_development_and_holdout_roots():
    fixture = json.loads(V3.read_text(encoding="utf-8"))
    strong = [entry for entry in fixture["generic_exact"] if entry.get("supervision_class") == "PREFERENCE_STRONG"]
    dev = [entry for entry in strong if entry["split"] == "DEVELOPMENT"]
    holdout = [entry for entry in strong if entry["split"] == "HOLDOUT"]
    assert len(strong) == 24
    assert len(dev) == 20
    assert len(holdout) == 4
    assert len({entry["ruleset_id"] for entry in dev}) == 4
    assert max(sum(entry["ruleset_id"] == rid for entry in dev) for rid in {entry["ruleset_id"] for entry in dev}) <= len(dev) / 2


def test_f23e_every_strong_root_preserves_all_wdl_ties_and_strictly_worse_actions():
    fixture = json.loads(V3.read_text(encoding="utf-8"))
    strong = [entry for entry in fixture["generic_exact"] if entry.get("supervision_class") == "PREFERENCE_STRONG"]
    for entry in strong:
        proof = entry["preference_authority"]
        values = {json.dumps(row["action"], sort_keys=True): row["value"] for row in proof["all_root_action_values"]}
        optimal = {json.dumps(action, sort_keys=True) for action in proof["optimal_root_actions"]}
        assert optimal
        assert {values[key] for key in optimal} == {proof["root_value"]}
        assert all(value != proof["root_value"] and value == "DRAW" for key, value in values.items() if key not in optimal)
        assert proof["cap_hits"] == 0
        assert proof["cycle_edges"] == 0


def test_f23e_solver_refuses_a_deliberately_capped_case():
    m = f23c._imports()
    case = f23e._case_specs(m)[0]
    result = solve_root(case["compiled"], case["state_object"], max_nodes=0, max_depth=1)
    assert result.strong is False
    assert result.root_value is None
    assert result.unresolved_reason.startswith("REFERENCE_SOLVE_UNRESOLVED:")
    assert result.stats["cap_hits"] > 0


def test_f23e_solver_has_no_evaluator_dependency_and_type_id_rename_is_equivalent():
    source = Path(__file__).parents[1].joinpath("scripts", "exact_generic_preference_solver.py").read_text(encoding="utf-8")
    assert "Evaluator" not in source
    m = f23c._imports()
    original = f23e._case_specs(m)[0]
    renamed_compiled = f23e._orthogonal(8, m, tid="Q")
    renamed_rows = [row.replace("R", "Q").replace("r", "q") for row in original["state"]["rows"]]
    renamed_state = m["make_state"](renamed_compiled, renamed_rows)
    left = solve_root(original["compiled"], original["state_object"], max_nodes=5000, max_depth=1)
    right = solve_root(renamed_compiled, renamed_state, max_nodes=5000, max_depth=1)
    assert left.root_value == right.root_value == "WIN"
    assert len(left.optimal_actions) == len(right.optimal_actions)


def test_f23e_owner_side_symmetry_preserves_root_outcome():
    m = f23c._imports()
    case = f23e._case_specs(m)[0]
    rows = case["state"]["rows"]
    swapped = []
    for row in reversed(rows):
        swapped.append("".join(ch.swapcase() if ch != "." else ch for ch in reversed(row)))
    state = m["make_state"](case["compiled"], swapped, side_to_move=1)
    original = solve_root(case["compiled"], case["state_object"], max_nodes=5000, max_depth=1)
    rotated = solve_root(case["compiled"], state, max_nodes=5000, max_depth=1)
    assert original.root_value == rotated.root_value == "WIN"
    assert len(original.optimal_actions) == len(rotated.optimal_actions)
