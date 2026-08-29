"""F23K exact reference solver correctness and refusal contracts."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from generic_chess.core.position import HistoryRecord
from generic_chess.core.terminal import TerminalResult, TerminalStatus, _perpetual_check_result
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23e_preference_corpus as f23e
from scripts import build_f23g_preference_corpus_r2 as f23g
from scripts import exact_generic_preference_solver as legacy
from scripts import exact_generic_preference_solver_v2 as v2
from scripts import audit_f23k_solver_foundation as benchmark


def _deep_case(variant: int = 0):
    m = f23c._imports()
    compiled, pieces = f23g._semantic_variant(m, variant)
    return m, compiled, m["make_state"](compiled, f23g._rows(5, pieces))


def test_f23k_matches_legacy_oracle_root_value_and_complete_optimal_set():
    m, compiled, state = _deep_case()
    old = legacy.solve_root(compiled, state, max_nodes=30000, max_depth=6)
    new = v2.solve_root_proof_v2(compiled, state, max_nodes=30000, max_depth=6)
    assert new.strong is old.strong is True
    assert new.root_value == old.root_value
    assert new.optimal_actions == old.optimal_actions
    assert [(item["action"], item["value"]) for item in new.action_values] == [(item["action"], item["value"]) for item in old.action_values]
    assert new.stats["history_key_mode"] == "full_state_and_history"


def test_f23k_differential_parity_covers_historical_tiny_preference_families():
    m = f23c._imports()
    for case in f23e._case_specs(m):
        old = legacy.solve_root(case["compiled"], case["state_object"], max_nodes=5000, max_depth=1)
        new = v2.solve_root_proof_v2(case["compiled"], case["state_object"], max_nodes=5000, max_depth=1)
        assert new.root_value == old.root_value
        assert new.optimal_actions == old.optimal_actions
        assert [(row["action"], row["value"]) for row in new.action_values] == [(row["action"], row["value"]) for row in old.action_values]


def test_f23k_maps_any_authoritative_terminal_winner_not_only_checkmate():
    sentinel = object()
    with patch.object(v2, "terminal_result", return_value=TerminalResult(TerminalStatus.PERPETUAL_CHECK, winner=1)):
        assert v2._terminal_value(sentinel, sentinel, 1)[0] == "WIN"
        assert v2._terminal_value(sentinel, sentinel, 0)[0] == "LOSS"
    with patch.object(v2, "terminal_result", return_value=TerminalResult(TerminalStatus.STALEMATE)):
        assert v2._terminal_value(sentinel, sentinel, 0)[0] == "DRAW"


def test_f23k_preserves_perpetual_check_winner_and_maps_checker_loss():
    history = (
        HistoryRecord("root", -1, "", False),
        HistoryRecord("checked", 0, "a", True),
        HistoryRecord("root", 1, "b", False),
        HistoryRecord("checked", 0, "c", True),
        HistoryRecord("root", 1, "d", False),
    )
    result = _perpetual_check_result((("root", 2),), history, 2)
    assert result == TerminalResult(TerminalStatus.PERPETUAL_CHECK, winner=1)
    sentinel = object()
    with patch.object(v2, "terminal_result", return_value=result):
        assert v2._terminal_value(sentinel, sentinel, 1)[0] == "WIN"
        assert v2._terminal_value(sentinel, sentinel, 0)[0] == "LOSS"


def test_f23k_refuses_node_depth_and_active_cycle_without_guessing():
    m, compiled, state = _deep_case()
    for max_nodes, max_depth in ((0, 6), (30000, 0)):
        result = v2.solve_root_proof_v2(compiled, state, max_nodes=max_nodes, max_depth=max_depth)
        assert result.strong is False
        assert result.root_value is None
        assert result.unresolved_reason.startswith("REFERENCE_SOLVE_UNRESOLVED:")
    action, _child = legacy.legal_successors(state, compiled)[0]
    with patch.object(v2, "legal_successors", return_value=((action, state),)):
        result = v2.solve_root_proof_v2(compiled, state, max_nodes=100, max_depth=10)
    assert result.strong is False
    assert result.unresolved_reason == "REFERENCE_SOLVE_UNRESOLVED:cycle"
    assert result.stats["cycle_edges"] > 0


def test_f23k_certificate_is_deterministic_and_reports_proof_stats():
    _m, compiled, state = _deep_case(4)
    first = v2.solve_root_proof_v2(compiled, state, max_nodes=30000, max_depth=6)
    second = v2.solve_root_proof_v2(compiled, state, max_nodes=30000, max_depth=6)
    assert first == second
    assert first.stats["legal_successors_generated"] > 0
    assert "terminal_statuses" in first.stats
    assert "exact_tt_hits" in first.stats
    assert "lower_bound_hits" in first.stats
    assert "upper_bound_hits" in first.stats


def test_f23k_fixed_capability_matrix_is_reproducible_and_evaluator_blind():
    fixture = Path(__file__).parents[1] / "tests" / "fixtures" / "f23k_solver_capability_v1.json"
    expected = json.loads(fixture.read_text(encoding="utf-8"))
    assert benchmark.build_report() == expected
    assert expected["legacy_parity"] is True
    assert expected["non_control_families"] == 5
    assert expected["non_control_solved_families"] == 0
    assert expected["selected_next_boundary"] == "F23L_EXACT_REFERENCE_SOLVER_FOUNDATION_R2"
