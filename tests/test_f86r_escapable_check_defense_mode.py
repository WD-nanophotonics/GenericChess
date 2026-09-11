"""F86R PREP and exact defensive-mechanism contracts."""

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86r_escapable_check_defense_mode"
MANIFEST = ARTIFACTS / "manifest.json"
RESULT = ARTIFACTS / "summary.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_f86r_prep_freezes_f86q_authority_and_selected_action_cohort():
    manifest = _load(MANIFEST)
    assert manifest["status"] == "PRE_REGISTERED_F86R_ESCAPABLE_CHECK_DEFENSE_MODE"
    assert manifest["baseline_commit"] == "35d9dfcbf76a5e51dc72f49722389e8dc1b60076"
    assert manifest["f86q_prep_manifest_blob"] == "76e15ba9320ab490d5d6321852eb5b683b6002fb"
    assert manifest["f86q_result_blob"] == "84fba9e85b918895f451ce478fdabe77d8fb00c4"
    assert manifest["f86o_manifest_blob"] == "1d16cf69a7ce5f7347352162dcbd351485ee8c5af"
    assert len(manifest["rulesets"]) == 6
    assert len(manifest["frozen_f86o_replay_evidence"]) == 12
    assert len(manifest["selected_f86q_checking_actions"]) == 63
    assert manifest["probe_accounting"]["hard_cap"] == 2048


def test_f86r_result_is_deferred_until_after_prep_publish():
    assert not RESULT.exists() or _load(RESULT)["status"] in {
        "F86R_ESCAPABLE_CHECK_DEFENSE_MODE_COMPLETE",
        "F86R_ESCAPABLE_CHECK_DEFENSE_MODE_TRUNCATED",
    }


def test_f86r_result_replays_exactly_and_stays_within_budget():
    if not RESULT.exists():
        pytest.skip("F86R RESULT is created after PREP publish")
    result = _load(RESULT)
    assert result["status"] == "F86R_ESCAPABLE_CHECK_DEFENSE_MODE_COMPLETE"
    assert result["replayed_trajectories"] == 12
    assert result["replay_equality"] == {"action_sequence_matches": 12, "final_position_digest_matches": 12}
    assert result["new_real_games"] == 0
    assert result["probe_successor_count"] <= result["probe_cap"] == 2048
    assert result["truncation"] is False


def test_f86r_checker_and_breaking_reply_contracts_are_recorded():
    if not RESULT.exists():
        pytest.skip("F86R RESULT is created after PREP publish")
    result = _load(RESULT)
    assert result["checking_actions"]
    for action in result["checking_actions"]:
        assert action["checker_multiplicity"] >= 1
        for reply in action["breaking_replies"]:
            assert reply["primary_mechanism"] in {"ANCHOR_FLIGHT", "CHECKER_CAPTURE", "INTERPOSITION_OR_SCREEN", "OTHER_CHECK_ESCAPE"}
            if reply["primary_mechanism"] == "CHECKER_CAPTURE":
                assert reply["captured_checking_piece"] is True


def test_f86r_arm_n_routes_and_f_positive_control_are_separate():
    if not RESULT.exists():
        pytest.skip("F86R RESULT is created after PREP publish")
    result = _load(RESULT)
    assert result["routing"]["arm_n_by_sample"]["V4-3"] in {
        "ANCHOR_FLIGHT_IS_PRIMARY_BREAKING_REPLY_MODE",
        "CHECKER_CAPTURE_IS_PRIMARY_BREAKING_REPLY_MODE",
        "INTERPOSITION_IS_PRIMARY_BREAKING_REPLY_MODE",
        "OTHER_ESCAPE_IS_PRIMARY_BREAKING_REPLY_MODE",
        "CHECK_ESCAPE_MECHANISM_IS_MIXED",
    }
    assert result["routing"]["arm_n_by_sample"]["V5-3"] in {
        "ANCHOR_FLIGHT_IS_PRIMARY_BREAKING_REPLY_MODE",
        "CHECKER_CAPTURE_IS_PRIMARY_BREAKING_REPLY_MODE",
        "INTERPOSITION_IS_PRIMARY_BREAKING_REPLY_MODE",
        "OTHER_ESCAPE_IS_PRIMARY_BREAKING_REPLY_MODE",
        "CHECK_ESCAPE_MECHANISM_IS_MIXED",
    }
    positive = result["by_arm_sample"]["F"]["V5-3"]["breaking_reply_mechanism_counts"]
    assert result["by_arm_sample"]["F"]["V5-3"]["checking_actions"] > 0
    assert positive
    assert all(
        action["breaking_reply_count"] == 0
        for action in result["checking_actions"]
        if action["f86q_classification"] in {"FORCED_CHECK_CONTINUATION", "FORCED_MATE_IN_TWO"}
    )


def test_f86r_prohibited_compute_is_zero_and_no_geometry_surrogate_is_present():
    if not RESULT.exists():
        pytest.skip("F86R RESULT is created after PREP publish")
    result = _load(RESULT)
    assert result["specialized_depth_plies"] == 3
    assert result["generic_search"] == 0
    assert result["alphabeta_nodes"] == 0
    assert result["bfs_expansions"] == 0
    assert result["training_compute"] == 0
    assert result["teacher_compute"] == 0
    assert result["f85_actual_compute"] == 0
    assert result["default_generator_changed"] is False
    assert all("template_distance_surrogate" not in row for row in result["checking_actions"])
