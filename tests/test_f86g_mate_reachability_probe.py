"""F86G mate-reachability and state-distribution probe contracts."""

import json
from pathlib import Path


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
    assert payload["legal_child_probe_count"] == 788
    assert payload["legal_child_probe_count"] <= 4096
    assert payload["probe_truncated"] is False
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
        "coverage_delta_across_capture",
    }
    assert required <= set(payload["trajectories"][0]["states"][0])


def test_f86g_cooperative_search_is_bounded_and_fail_closed():
    payload = _load("cooperative_reachability.json")
    assert len(payload["results"]) == 4
    assert payload["total_state_expansions"] == 32768
    assert payload["total_state_expansions"] <= 32768
    assert payload["any_node_truncation"] is True
    assert all(row["node_truncated"] is True for row in payload["results"].values())
    assert all(row["first_reachable_checkmate_depth"] is None for row in payload["results"].values())
    assert payload["routing"] == ["MATE_REACHABILITY_UNRESOLVED_DUE_TO_STATE_CAP"]


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
