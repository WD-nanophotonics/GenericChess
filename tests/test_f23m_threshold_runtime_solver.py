"""F23M threshold proof and SearchPathRuntime contracts."""

from __future__ import annotations

from pathlib import Path

from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23g_preference_corpus_r2 as f23g
from scripts import exact_generic_preference_solver_v2 as v2
from scripts import exact_generic_preference_solver_v3 as v3


ROOT = Path(__file__).parents[1]


def _case(variant=0):
    m = f23c._imports()
    compiled, pieces = f23g._semantic_variant(m, variant)
    return compiled, m["make_state"](compiled, f23g._rows(5, pieces))


def test_f23m_matches_both_historical_and_v2_oracles_on_deep_control():
    compiled, state = _case()
    old = __import__("scripts.exact_generic_preference_solver", fromlist=["solve_root"]).solve_root(compiled, state, max_nodes=30000, max_depth=6)
    middle = v2.solve_root_proof_v2(compiled, state, max_nodes=30000, max_depth=6)
    new = v3.solve_root_threshold_v3(compiled, state, max_nodes=30000, max_depth=6)
    assert old.root_value == middle.root_value == new.root_value
    assert old.optimal_actions == middle.optimal_actions == new.optimal_actions
    assert [(row["action"], row["value"]) for row in old.action_values] == [(row["action"], row["value"]) for row in new.action_values]
    assert new.stats["runtime_pushes"] == new.stats["runtime_pops"]
    assert new.stats["history_key_mode"] == "REPETITION_COUNTS_SUFFICIENT"


def test_f23m_tt_on_and_off_have_identical_exact_results_and_balanced_runtime():
    compiled, state = _case(4)
    enabled = v3.solve_root_threshold_v3(compiled, state, max_nodes=30000, max_depth=6, use_tt=True)
    disabled = v3.solve_root_threshold_v3(compiled, state, max_nodes=30000, max_depth=6, use_tt=False)
    assert enabled.strong == disabled.strong is True
    assert enabled.root_value == disabled.root_value
    assert enabled.action_values == disabled.action_values
    assert enabled.stats["runtime_pushes"] == enabled.stats["runtime_pops"]
    assert disabled.stats["runtime_pushes"] == disabled.stats["runtime_pops"]


def test_f23m_threshold_solver_refuses_caps_without_caching_unresolved():
    compiled, state = _case()
    result = v3.solve_root_threshold_v3(compiled, state, max_nodes=0, max_depth=None)
    assert result.strong is False
    assert result.unresolved_reason.startswith("REFERENCE_SOLVE_UNRESOLVED:")
    assert result.stats["tt_entries"] == 0
    assert result.stats["runtime_pushes"] == result.stats["runtime_pops"]


def test_f23m_source_is_evaluator_free_and_horizon_is_authoritative():
    source = Path(v3.__file__).read_text(encoding="utf-8")
    assert "Evaluator" not in source
    assert "ADR-040" not in source
    assert "AlphaSho" not in source
    compiled, state = _case()
    result = v3.solve_root_threshold_v3(compiled, state, max_nodes=30000, max_depth=None)
    assert result.stats["authoritative_horizon"] is True
    assert result.stats["effective_max_depth"] == compiled.support.max_ply - state.ply_count
