"""F86I reversible-mobility rescue result contracts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86i_reversibility_rescue"
SAMPLES = ("V4-2", "V4-3", "V4-4", "V4-5", "V5-2", "V5-3", "V5-4", "V5-5")


def _load(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_f86i_results_bind_to_the_preregistered_manifest_and_stay_experimental():
    results = _load("results.json")
    assert results["manifest"] == "artifacts/f86i_reversibility_rescue/manifest.json"
    assert results["candidate_profile"] == "ORTHO4_PLUS_REVERSE_CLOSED_ORDINARY"
    assert results["manifest_result_driven_replacement_forbidden"] is True
    assert set(results["ruleset_fingerprints"]) == set(SAMPLES)
    assert all(set(cells) == {"CANDIDATE"} for cells in results["ruleset_fingerprints"].values())
    assert results["default_generator_changed"] is False
    assert results["bfs_expansions"] == 0
    assert results["teacher_search_compute"] == 0
    assert results["f85_actual_compute"] == 0


def test_f86i_static_mechanism_and_census_routes_are_fail_closed():
    results = _load("results.json")
    assert [row["sample_id"] for row in results["static"]] == list(SAMPLES)
    for row in results["static"]:
        mechanism = row["mechanism"]
        assert mechanism["ordinary_direct_reverse_edge_fraction"] == 1.0
        assert mechanism["ordinary_nontrivial_scc_vertex_fraction"] > 0.0
        assert mechanism["ordinary_all_monotone_dag"] is False

    census = {row["census"]["sample_id"]: row for row in results["candidate_static_mate_capacity"]}
    assert set(census) == {"V4-3", "V5-3"}
    assert census["V4-3"]["census"]["candidate_position_count"] == 504
    assert census["V4-3"]["census"]["validated_position_count"] == 398
    assert census["V4-3"]["census"]["validated_template_count"] == 40
    assert census["V4-3"]["census"]["truncation"] is False
    assert census["V4-3"]["kinematic"]["ordinary_assignment_reachable_count"] == 0
    assert census["V4-3"]["kinematic"]["joint_kinematically_reachable_count"] == 0
    assert census["V5-3"]["census"]["candidate_position_count"] == 2048
    assert census["V5-3"]["census"]["validated_position_count"] == 1890
    assert census["V5-3"]["census"]["validated_template_count"] == 98
    assert census["V5-3"]["census"]["truncation"] is True
    assert results["routing"]["static"] == [
        {"sample_id": "V4-3", "routing": "REVERSIBILITY_RESCUE_INSUFFICIENT_KINEMATICALLY"},
        {"sample_id": "V5-3", "routing": "MATE_CAPACITY_UNRESOLVED_DUE_TO_CENSUS_CAP"},
    ]


def test_f86i_dynamic_smoke_has_exact_budget_and_conservative_accounting():
    results = _load("results.json")
    dynamic = results["dynamic"]
    assert dynamic["game_count"] == 16
    assert dynamic["real_games"] == 16
    assert dynamic["max_ply"] == 32
    assert len(dynamic["games"]) == 16
    assert {row["sample_id"] for row in dynamic["games"]} == set(SAMPLES)
    assert all(len(row["actions"]) <= 32 for row in dynamic["games"])
    labels = [row["outcome_label"] for row in dynamic["games"]]
    assert labels.count("checkmate") == 1
    assert labels.count("ongoing@32") == 15
    assert "stalemate" not in labels
    assert "repetition" not in labels
    assert results["routing"]["dynamic"] == ["REVERSIBILITY_RESCUE_SHOWS_TERMINATION_VIABILITY"]


def test_f86i_raw_game_artifact_is_durable_and_matches_result_summary():
    results = _load("results.json")
    games = _load("game_results.json")
    assert games["games"] == results["dynamic"]["games"]
    assert games["tactical_probe_nodes"] == 0
    assert all(row["policy_move_counts"]["A"] <= 32 for row in games["games"])
    assert all(row["policy_move_counts"]["B"] <= 32 for row in games["games"])
