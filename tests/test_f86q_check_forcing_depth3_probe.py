"""F86Q PREP and bounded depth-3 forcing-probe contracts."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86q_check_forcing_depth3_probe"
MANIFEST = ARTIFACTS / "manifest.json"
RESULT = ARTIFACTS / "summary.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_f86q_prep_freezes_authority_replay_and_probe_contract():
    manifest = _load(MANIFEST)
    assert manifest["status"] == "PRE_REGISTERED_F86Q_CHECK_FORCING_DEPTH3_PROBE"
    assert manifest["baseline_commit"] == "e0aa2d7c606b395402ec252c5688a51c8eac2c2a"
    assert manifest["source_f86o_manifest_blob"] == "1d16cf69a7ce5f7347352162dcbd351485ee8c5af"
    assert len(manifest["rulesets"]) == 6
    assert len(manifest["frozen_replay_evidence"]) == 12
    assert len(manifest["policy_tapes"]) == 2
    assert all(len(data["uniforms"]) == 32 for sample in manifest["policy_tapes"].values() for data in sample.values())
    assert manifest["state_selection"]["deduplication"] == ["ruleset_fingerprint", "position_identity_key"]
    assert manifest["probe_accounting"]["hard_cap"] == 8192


def test_f86q_result_is_deferred_until_after_prep_publish():
    assert not RESULT.exists() or _load(RESULT)["status"] in {
        "F86Q_CHECK_FORCING_DEPTH3_PROBE_COMPLETE",
        "F86Q_CHECK_FORCING_DEPTH3_PROBE_TRUNCATED",
    }


def test_f86q_result_replays_all_frozen_games_without_new_games():
    if not RESULT.exists():
        pytest.skip("F86Q RESULT is created after PREP publish")
    result = _load(RESULT)
    assert result["status"] == "F86Q_CHECK_FORCING_DEPTH3_PROBE_COMPLETE"
    assert result["replayed_trajectories"] == 12
    assert result["new_real_games"] == 0
    assert result["replay_equality"] == {"action_sequence_matches": 12, "final_position_digest_matches": 12}
    assert result["truncation"] is False
    assert result["probe_successor_count"] <= result["probe_cap"] == 8192


def test_f86q_result_stays_within_specialized_depth_and_prohibited_compute_zero():
    if not RESULT.exists():
        pytest.skip("F86Q RESULT is created after PREP publish")
    result = _load(RESULT)
    assert result["specialized_forcing_depth_plies"] == 3
    assert result["generic_search_depth"] == 0
    assert result["alphabeta_nodes"] == 0
    assert result["bfs_expansions"] == 0
    assert result["training_compute"] == 0
    assert result["teacher_compute"] == 0
    assert result["f85_actual_compute"] == 0
    assert result["default_generator_changed"] is False


def test_f86q_records_root_occurrence_multiplicity_and_exact_forcing_fields():
    if not RESULT.exists():
        pytest.skip("F86Q RESULT is created after PREP publish")
    result = _load(RESULT)
    assert set(result["by_arm_sample"]) == {"L", "F", "N"}
    assert all(set(result["by_arm_sample"][arm]) == {"V4-3", "V5-3"} for arm in ("L", "F", "N"))
    assert result["selected_roots"]
    for root in result["selected_roots"]:
        assert root["trajectory_occurrence_count"] >= 1
        assert root["actions"]
        for action in root["actions"]:
            assert len(action["checking_action_canonical_digest"]) == 64
            assert action["opponent_legal_reply_count"] >= 0
            assert action["minimum_attacker_continuation_count"] <= action["maximum_attacker_continuation_count"]
            assert action["classification"] in {"MATE_IN_ONE", "FORCED_MATE_IN_TWO", "FORCED_CHECK_CONTINUATION", "ESCAPABLE_CHECK"}


def test_f86q_arm_n_routes_are_reported_separately():
    if not RESULT.exists():
        pytest.skip("F86Q RESULT is created after PREP publish")
    result = _load(RESULT)
    assert result["routing"]["arm_n_by_sample"] == {
        "V4-3": "CHECK_PRESSURE_IS_NONFORCING",
        "V5-3": "CHECK_PRESSURE_IS_NONFORCING",
    }
    assert result["routing"]["overall"] == ["CHECK_PRESSURE_IS_NONFORCING"]
