"""F86P deterministic replay and one-ply diagnostic contracts."""

import json
from pathlib import Path

from generic_chess.core.transition import initial_state
from generic_chess.core.attacks import is_in_check
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from scripts.f86p_capture_check_pressure_diagnosis import _canonical_successors, _child_gives_check

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "artifacts" / "f86p_capture_check_pressure_diagnosis" / "summary.json"


def _load():
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


def test_f86p_replays_only_the_frozen_f86o_trajectories():
    result = _load()
    assert result["status"] == "F86P_FROZEN_TRAJECTORY_INTERACTION_DIAGNOSIS_COMPLETE"
    assert result["replayed_trajectories"] == 12
    assert result["new_real_games"] == 0
    assert result["one_ply_child_probes"] <= result["one_ply_child_probe_cap"] == 4096
    assert result["truncation"] is False
    assert result["deeper_search_nodes"] == 0
    assert result["bfs_expansions"] == 0
    assert result["alphabeta_nodes"] == 0


def test_f86p_preserves_all_f86o_action_and_final_position_digests():
    result = _load()
    f86o = json.loads((ROOT / "artifacts" / "f86o_common_tape_triarm_dynamic_smoke" / "summary.json").read_text(encoding="utf-8"))
    expected = {
        (row["arm"], row["sample_id"], row["seat_assignment"]["player0"], row["seat_assignment"]["player1"]): row
        for row in f86o["games"]
    }
    for row in result["games"]:
        key = (row["arm"], row["sample_id"], row["seat_assignment"]["player0"], row["seat_assignment"]["player1"])
        assert row["action_sequence_sha256"] == expected[key]["action_sequence_sha256"]
        assert row["final_position_digest"] == expected[key]["final_position_digest"]


def test_f86p_keeps_controls_and_per_arm_interaction_metrics():
    result = _load()
    assert set(result["by_arm"]) == {"L", "F", "N"}
    assert all(result["by_arm"][arm]["trajectory_count"] == 4 for arm in ("L", "F", "N"))
    assert all(len(row["opponent_anchor_pressure_trajectories"]) == 4 for row in result["by_arm"].values())
    assert all("capture_available_ply_count" in game for game in result["games"])
    assert all("check_available_ply_count" in game for game in result["games"])
    assert all("mate_in_one_opportunity_count" in game for game in result["games"])
    assert all("template_distance_surrogate" in game for game in result["games"] if game["arm"] == "N")
    assert result["training_compute"] == 0
    assert result["teacher_compute"] == 0
    assert result["f85_actual_compute"] == 0
    assert result["default_generator_changed"] is False


def test_f86p_records_exact_one_ply_metrics_and_conservative_route():
    result = _load()
    assert result["one_ply_child_probes"] == 1620
    assert result["routing"] == ["CHECK_PRESSURE_PRESENT_BUT_MATE_BASIN_UNREACHED"]
    assert result["by_arm"]["L"]["plies_with_capture_available_fraction"] == 0.21428571428571427
    assert result["by_arm"]["F"]["plies_with_capture_available_fraction"] == 0.5
    assert result["by_arm"]["N"]["plies_with_capture_available_fraction"] == 0.3828125
    assert result["by_arm"]["N"]["chosen_capture_count"] == 13
    assert result["by_arm"]["N"]["check_available_ply_count"] == 13
    assert result["by_arm"]["N"]["chosen_check_count"] == 2
    assert result["by_arm"]["N"]["mate_in_one_opportunity_count"] == 0


def test_f86p_template_distance_surrogates_are_recorded_for_arm_n():
    result = _load()
    rows = {
        (game["sample_id"], game["seat_assignment"]["player0"]): game["template_distance_surrogate"]
        for game in result["games"]
        if game["arm"] == "N"
    }
    assert rows[("V4-3", "A")]["start_value"] == 4
    assert rows[("V4-3", "A")]["minimum_value"] == 2
    assert rows[("V4-3", "A")]["final_value"] == 21
    assert rows[("V5-3", "A")]["start_value"] == 1
    assert rows[("V5-3", "A")]["minimum_value"] == 0
    assert rows[("V5-3", "A")]["final_value"] == 55
    assert all("occupancy/check/capture-ignorant" in row["definition"] for row in rows.values())
    assert all(row["authority"] == "NON_AUTHORITY_CROSS_RULESET_GEOMETRY_REFERENCE" for row in rows.values())


def test_f86p_check_helper_matches_core_history_on_actual_legal_successors():
    manifest = json.loads((ROOT / "artifacts" / "f86o_common_tape_triarm_dynamic_smoke" / "manifest.json").read_text(encoding="utf-8"))
    row = next(row for row in manifest["rulesets"] if row["arm"] == "N" and row["sample_id"] == "V4-3")
    compiled = compile_ruleset(ruleset_from_dict(row["ruleset"]))
    successors = _canonical_successors(initial_state(compiled), compiled)
    assert successors
    for _action, child in successors:
        assert _child_gives_check(child, compiled) == is_in_check(child.position, child.position.side_to_move, compiled)
        assert _child_gives_check(child, compiled) == child.history[-1].gave_check
