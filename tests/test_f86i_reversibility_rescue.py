"""F86I reversible-mobility rescue result contracts."""

import json
from pathlib import Path

import pytest

from scripts.f86i_reversibility_rescue import _dynamic_route
from scripts.f86i_r1_quality_metrics import _paired_outcomes

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86i_reversibility_rescue"
SAMPLES = ("V4-2", "V4-3", "V4-4", "V4-5", "V5-2", "V5-3", "V5-4", "V5-5")


def _load(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_f86i_results_bind_to_the_preregistered_manifest_and_stay_experimental():
    summary = _load("quality_summary.json")
    assert summary["status"] == "F86I_R1_ZERO_NEW_COMPUTE_CORRECTIVE"
    assert summary["real_games"] == 16
    assert summary["raw_evidence_retained_in_checkpoint"] is False
    assert summary["raw_evidence_retained_local_only"] is True
    assert summary["source_evidence"]["commit"] == "0fbfbf2b5c3cc1e2efd1300cba4da0f5587f4976"
    assert summary["source_evidence"]["raw_artifacts"] == {
        "artifacts/f86i_reversibility_rescue/game_results.json": {
            "blob": "7723862c4f18f297d239590f49fa1265462efdc9",
            "retained_local_ignored": True,
        },
        "artifacts/f86i_reversibility_rescue/results.json": {
            "blob": "21ecbe3d87fe06e92848c231b290ea2148dcd95b",
            "retained_local_ignored": True,
        },
        "artifacts/f86i_reversibility_rescue/static_results.json": {
            "blob": "e2d8dfa8aced6aed750d0d0bb9dc3d4026eeac4a",
            "retained_local_ignored": True,
        },
    }
    assert summary["default_generator_changed"] is False
    assert summary["bfs_expansions"] == 0
    assert summary["teacher_search_compute"] == 0
    assert summary["f85_actual_compute"] == 0


def test_f86i_static_mechanism_and_census_routes_are_fail_closed():
    summary = _load("quality_summary.json")
    assert [row["sample_id"] for row in summary["static"]] == list(SAMPLES)
    for row in summary["static"]:
        mechanism = row["mechanism"]
        assert mechanism["ordinary_direct_reverse_edge_fraction"] == 1.0
        assert mechanism["ordinary_nontrivial_scc_vertex_fraction"] > 0.0
        assert mechanism["ordinary_all_monotone_dag"] is False

    census = {row["sample_id"]: row for row in summary["candidate_static_mate_capacity"]}
    assert set(census) == {"V4-3", "V5-3"}
    assert census["V4-3"]["candidate_position_count"] == 504
    assert census["V4-3"]["validated_position_count"] == 398
    assert census["V4-3"]["validated_template_count"] == 40
    assert census["V4-3"]["truncation"] is False
    assert census["V4-3"]["ordinary_assignment_reachable_count"] == 0
    assert census["V4-3"]["joint_kinematically_reachable_count"] == 0
    assert census["V5-3"]["candidate_position_count"] == 2048
    assert census["V5-3"]["validated_position_count"] == 1890
    assert census["V5-3"]["validated_template_count"] == 98
    assert census["V5-3"]["truncation"] is True
    assert summary["static_candidate_checks"] == {
        "V4-3": 504,
        "V5-3": 2048,
        "total": 2552,
        "per_cell_cap": 2048,
        "total_cap": 4096,
    }
    assert summary["routing"]["static"] == [
        {"sample_id": "V4-3", "routing": "REVERSIBILITY_RESCUE_INSUFFICIENT_KINEMATICALLY"},
        {"sample_id": "V5-3", "routing": "MATE_CAPACITY_UNRESOLVED_DUE_TO_CENSUS_CAP"},
    ]


def test_f86i_dynamic_smoke_has_exact_budget_and_conservative_accounting():
    summary = _load("quality_summary.json")
    quality = summary["quality"]
    assert summary["real_games"] == 16
    assert summary["max_ply"] == 32
    assert quality["aggregate"]["trajectory_count"] == 16
    assert quality["outcomes"]["terminal_distribution"] == {"checkmate": 1, "ongoing@32": 15}
    assert quality["outcomes"]["game_length_distribution"] == {"13": 1, "32": 15}
    assert summary["routing"]["dynamic"] == ["REVERSIBILITY_OVERCOMPENSATES_TO_CYCLIC_NONTERMINATION"]
    assert summary["routing"]["reason"] == {
        "directional_dag_obstruction_removed": True,
        "partial_static_kinematic_rescue_on_V5_3": True,
        "checkmate_observed": 1,
        "ongoing_at_32": 15,
        "dynamic_outcomes_dominated_by_censored_nontermination": True,
        "repetition_observed": False,
    }


def test_f86i_quality_reuses_existing_measurement_definition_and_fails_closed_pairs():
    summary = _load("quality_summary.json")
    aggregate = summary["quality"]["aggregate"]
    assert summary["quality"]["definition"] == "generic_chess.benchmark.game_quality.profile_from_observations"
    assert aggregate["median_branching"] == pytest.approx(5.0)
    assert aggregate["p10_game_branching"] == pytest.approx(2.0)
    assert aggregate["p90_game_branching"] == pytest.approx(10.0)
    assert aggregate["forced_move_fraction"] == pytest.approx(0.02434077079107505)
    assert aggregate["low_branch_fraction"] == pytest.approx(0.14198782961460446)
    assert aggregate["branching_collapse_fraction"] == pytest.approx(0.15616438356164383)
    paired = summary["quality"]["paired_outcomes"]
    assert paired["scoreable_pair_count"] == 0
    assert paired["first_player_score"] is None
    assert paired["second_player_score"] is None
    assert paired["incomplete_pairs_are_unresolved"] is True
    assert "games" not in summary
    assert "actions" not in json.dumps(summary)


def test_f86i_r2_routing_predicate_rejects_censored_termination_viability_claims():
    assert _dynamic_route(["checkmate"] + ["ongoing@32"] * 15) == (
        "REVERSIBILITY_OVERCOMPENSATES_TO_CYCLIC_NONTERMINATION"
    )
    assert _dynamic_route(["ongoing@32"] * 16) != "REVERSIBILITY_RESCUE_SHOWS_TERMINATION_VIABILITY"
    assert _dynamic_route(["checkmate", "stalemate"]) == "REVERSIBILITY_RESCUE_SHOWS_TERMINATION_VIABILITY"


def test_f86i_r2_paired_outcomes_use_half_for_terminal_draw_and_null_for_ongoing():
    draw_pair = [
        {"sample_id": "V4-2", "terminal_status": "stalemate", "winner": None},
        {"sample_id": "V4-2", "terminal_status": "repetition", "winner": None},
    ]
    ongoing_pair = [
        {"sample_id": "V4-3", "terminal_status": "ongoing", "winner": None},
        {"sample_id": "V4-3", "terminal_status": "checkmate", "winner": 0},
    ]
    result = _paired_outcomes(draw_pair + ongoing_pair)
    assert result["scoreable_pair_count"] == 1
    assert result["by_sample"]["V4-2"]["first_player_score"] == 0.5
    assert result["by_sample"]["V4-2"]["second_player_score"] == 0.5
    assert result["by_sample"]["V4-3"]["first_player_score"] is None
    assert result["by_sample"]["V4-3"]["second_player_score"] is None
