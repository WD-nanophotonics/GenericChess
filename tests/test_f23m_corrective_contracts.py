"""F23M corrective threshold and history-key behavior contracts."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import terminal_result

from ai_fixtures import build_4x4_rooks
from scripts import exact_generic_preference_solver_v2 as v2
from scripts import exact_generic_preference_solver_v3 as v3
from test_f23m_threshold_runtime_solver import _case
from test_search_path_runtime import _continuous_history_pair


def _statuses(*names):
    return [v3.ThresholdResult(name) for name in names]


def test_threshold_maximizer_true_short_circuits_over_unresolved():
    assert v3._combine_threshold_children(True, _statuses(v3.PROVED_TRUE, v3.UNRESOLVED)).status == v3.PROVED_TRUE


def test_threshold_maximizer_false_requires_all_children_false():
    assert v3._combine_threshold_children(True, _statuses(v3.PROVED_FALSE, v3.UNRESOLVED)).status == v3.UNRESOLVED
    assert v3._combine_threshold_children(True, _statuses(v3.PROVED_FALSE, v3.PROVED_FALSE)).status == v3.PROVED_FALSE


def test_threshold_minimizer_false_short_circuits_over_unresolved():
    assert v3._combine_threshold_children(False, _statuses(v3.PROVED_FALSE, v3.UNRESOLVED)).status == v3.PROVED_FALSE


def test_threshold_minimizer_true_requires_all_children_true():
    assert v3._combine_threshold_children(False, _statuses(v3.PROVED_TRUE, v3.UNRESOLVED)).status == v3.UNRESOLVED
    assert v3._combine_threshold_children(False, _statuses(v3.PROVED_TRUE, v3.PROVED_TRUE)).status == v3.PROVED_TRUE


def test_threshold_unresolved_is_never_cached_and_root_actions_are_all_certified():
    compiled, state = _case()
    refused = v3.solve_root_threshold_v3(compiled, state, max_nodes=0, max_depth=None)
    assert refused.strong is False
    assert refused.stats["tt_entries"] == 0
    exact = v3.solve_root_threshold_v3(compiled, state, max_nodes=30000, max_depth=6)
    assert exact.strong is True
    assert exact.action_values
    assert all(row["value"] in {"WIN", "DRAW", "LOSS"} for row in exact.action_values)
    assert len(exact.optimal_actions) == sum(row["value"] == exact.root_value for row in exact.action_values)


def test_ordinary_repetition_key_merges_only_irrelevant_history_and_matches_v2_when_bounded():
    continuous, (left, right), _paths = _continuous_history_pair()
    ordinary = replace(continuous, repetition_policy="draw", max_ply=8)
    left_runtime = SearchPathRuntime.from_state(left, ordinary)
    right_runtime = SearchPathRuntime.from_state(right, ordinary)
    assert left.position == right.position
    assert left.position.side_to_move == right.position.side_to_move
    assert left.ply_count == right.ply_count
    assert left.repetition_counts == right.repetition_counts
    assert v2._state_key(left) != v2._state_key(right)
    assert v3._runtime_key(left_runtime, policy="draw") == v3._runtime_key(right_runtime, policy="draw")

    left_v3 = v3.solve_root_threshold_v3(ordinary, left, max_nodes=30000, max_depth=None, use_tt=True)
    right_v3 = v3.solve_root_threshold_v3(ordinary, right, max_nodes=30000, max_depth=None, use_tt=False)
    left_v2 = v2.solve_root_proof_v2(ordinary, left, max_nodes=30000, max_depth=None)
    assert left_v3.strong and right_v3.strong and left_v2.strong
    def classified(result):
        rows = tuple(sorted(((json.dumps(row["action"], sort_keys=True), row["value"]) for row in result.action_values)))
        optimal = tuple(sorted(json.dumps(action, sort_keys=True) for action in result.optimal_actions))
        return result.root_value, rows, optimal
    assert classified(left_v3) == classified(right_v3)
    assert classified(left_v3) == classified(left_v2)


def test_continuous_check_history_key_does_not_merge_distinct_valid_histories():
    compiled, (left, right), _paths = _continuous_history_pair()
    left_runtime = SearchPathRuntime.from_state(left, compiled)
    right_runtime = SearchPathRuntime.from_state(right, compiled)
    assert left.position == right.position
    assert left.repetition_counts == right.repetition_counts
    assert left_runtime.tt_eligible and right_runtime.tt_eligible
    assert left_runtime.search_key().history_context != right_runtime.search_key().history_context
    assert v3._runtime_key(left_runtime, policy="continuous_check_loss") != v3._runtime_key(right_runtime, policy="continuous_check_loss")
    assert left_runtime.terminal_status == terminal_result(left, compiled)
    assert right_runtime.terminal_status == terminal_result(right, compiled)
