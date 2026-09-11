"""F86G mate-reachability and state-distribution probe contracts."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from scripts.f86g_mate_reachability_probe import DedupSafetyError, _assert_equivalent_representatives


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86g_mate_reachability"


def _load(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_f86g_reuses_exact_cells_and_common_tapes_for_eight_trajectories():
    payload = _load("trajectory_probe.json")
    assert payload["trajectory_count"] == 8
    assert payload["policy_tape_algorithm"] == "python_random_mt19937_random_floor_index_v1"
    assert payload["policy_tape_seeds"] == {
        "V4-3": {"A": 8624301, "B": 8624302},
        "V5-3": {"A": 8625301, "B": 8625302},
    }
    assert len(payload["trajectories"]) == 8
    assert {row["cell"] for row in payload["trajectories"]} == {"ORTHO4_CURRENT", "FULL8_CURRENT"}
    assert payload["legal_child_probe_count"] == 867
    assert payload["legal_child_probe_count"] <= 4096
    assert payload["probe_truncated"] is False
    assert payload["schema_version"] == 2
    required = {
        "side_to_move",
        "ordinary_pieces_remaining_by_owner",
        "legal_action_count",
        "side_to_move_currently_in_check",
        "legal_checking_move_count",
        "legal_mate_in_one_move_count",
        "enemy_anchor_zone_size",
        "ordinary_only_attacked_squares_in_enemy_anchor_zone",
        "ordinary_only_anchor_zone_coverage_fraction",
        "enemy_anchor_itself_ordinary_attacked",
        "capture_occurred_since_previous",
        "ordinary_anchor_zone_coverage_by_owner",
        "captured_owner",
        "captured_piece_type",
        "captured_owner_pre_capture_coverage",
        "captured_owner_post_capture_coverage",
        "same_owner_capture_coverage_delta",
    }
    assert required <= set(payload["trajectories"][0]["states"][0])
    capture_states = [
        state for trajectory in payload["trajectories"] for state in trajectory["states"]
        if state["capture_occurred_since_previous"]
    ]
    assert capture_states
    for state in capture_states:
        assert state["captured_owner"] in (0, 1)
        assert state["captured_piece_type"]
        assert state["same_owner_capture_coverage_delta"] == pytest.approx(
            state["captured_owner_post_capture_coverage"]
            - state["captured_owner_pre_capture_coverage"]
        )


def test_f86g_cooperative_search_is_bounded_and_fail_closed():
    payload = _load("cooperative_reachability.json")
    assert len(payload["results"]) == 4
    assert payload["total_state_expansions"] == 32768
    assert payload["total_state_expansions"] <= 32768
    assert payload["any_node_truncation"] is True
    assert all(row["node_truncated"] is True for row in payload["results"].values())
    assert all(row["first_reachable_checkmate_depth"] is None for row in payload["results"].values())
    assert payload["routing"] == ["MATE_REACHABILITY_UNRESOLVED_DUE_TO_STATE_CAP"]
    for row in payload["results"].values():
        assert row["dedup_enabled"] is True
        assert all(row["dedup_preconditions"].values())
        assert row["generated_child_states"] == (
            row["unique_enqueued_states"] + row["duplicate_pruned_states"]
        )
        assert row["unexpanded_current_frontier"] == row["frontier_size"]
        assert row["unexpanded_current_frontier"] > 0
        assert row["exact_truncation_reason"] == (
            "state_expansion_cap_with_unexpanded_current_frontier"
        )
    assert payload["path_safe_dedup"]["key_fields"] == [
        "position", "ply_count", "repetition_counts"
    ]


def test_f86g_scope_has_no_new_random_or_teacher_compute():
    trajectory = _load("trajectory_probe.json")
    cooperative = _load("cooperative_reachability.json")
    assert trajectory["real_new_random_seeds"] == 0
    assert trajectory["teacher_learned_search_compute"] == 0
    assert cooperative["real_new_random_seeds"] == 0
    assert cooperative["teacher_learned_search_compute"] == 0
    assert trajectory["default_generator_changed"] is False
    assert cooperative["default_generator_changed"] is False
    assert trajectory["f85_actual_compute"] == 0
    assert cooperative["f85_actual_compute"] == 0


def test_f86g_dedup_safety_compares_different_history_representatives():
    state = SimpleNamespace(
        position=("same-position",),
        ply_count=4,
        repetition_counts=(("same", 1),),
    )
    left = SimpleNamespace(
        state=state,
        history=("history-a",),
        result=SimpleNamespace(status=SimpleNamespace(value="ongoing")),
        legal_actions=lambda: (),
    )
    right = SimpleNamespace(
        state=state,
        history=("history-b", "different-history"),
        result=SimpleNamespace(status=SimpleNamespace(value="ongoing")),
        legal_actions=lambda: (),
    )
    _assert_equivalent_representatives(left, right)

    mismatch = SimpleNamespace(
        state=state,
        history=("history-c",),
        result=SimpleNamespace(status=SimpleNamespace(value="ongoing")),
        legal_actions=lambda: (BoardMove(Square(0, 0), Square(1, 0)),),
    )
    with pytest.raises(DedupSafetyError):
        _assert_equivalent_representatives(left, mismatch)
