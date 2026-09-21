"""Regression coverage for the single corrected merged Gate 2 benchmark."""

from scripts.gate2_merged_benchmark import (
    PASS_RATIO,
    _normalized_regrets,
    _trend_bucket,
    run_merged,
)


def test_merged_gate2_uses_horizon_aware_mate_three_and_stops_on_next_failure():
    result = run_merged()

    assert result["status"] == "FIRST_HARD_FAILURE"
    assert result["gate2_status"] == "FAILED"
    assert result["gate3_status"] == "FROZEN"
    assert result["classification"] == "RULE_PRIOR_ABP_BASIC_COMPETENCE_UNRESOLVED_AT_CAPABILITY"
    assert result["first_hard_failure"] == {
        "layer": "capability",
        "ruleset": "shogi",
        "reason": "extreme_material",
        "failure_type": "HARD_FAILURE",
    }
    assert result["gate1"]["games"] == ["chess", "shogi"]
    assert [row["label"] for row in result["rulesets"]] == ["chess", "shogi"]
    assert result["short_games"] == []

    tasks = result["rulesets"][0]["capability"]["tasks"]
    assert result["rulesets"][0]["capability"]["status"] == "PASS"
    assert tasks["mate_in_one"]["status"] == "PASS"
    assert tasks["mate_in_one"]["primary_expected"] is True
    assert tasks["mate_in_three"]["status"] == "PASS"
    assert tasks["mate_in_three"]["witness_label"] == "mate_three"
    assert len(tasks["mate_in_three"]["expected_actions"]) == 1
    assert tasks["mate_in_three"]["primary_expected"] is True
    assert tasks["mate_in_three"]["reviewer_expected"] is True
    expected = tasks["mate_in_three"]["expected_actions"][0]
    assert expected["from"] == [3, 3]
    assert expected["to"] == [4, 4]
    mate_three = tasks["mate_in_three"]["decisions"]
    for role in ("primary", "reviewer"):
        assert mate_three[role]["search_limit_mode"] == "fixed_depth_3"
        assert mate_three[role]["max_nodes"] is None
        assert mate_three[role]["max_depth"] == 3
        assert mate_three[role]["completed_depth"] == 3
        assert mate_three[role]["termination_reason"] == "completed_depth"
        assert mate_three[role]["selected_action"] == expected
    assert mate_three["weak"]["search_limit_mode"] == "node_budget"
    assert mate_three["weak"]["max_nodes"] == 128

    mate_one = tasks["mate_in_one"]["decisions"]
    assert mate_one["primary"]["max_nodes"] == 1000
    assert mate_one["weak"]["max_nodes"] == 128
    assert mate_one["reviewer"]["max_nodes"] == 8000
    assert all(
        decision["search_limit_mode"] == "node_budget"
        for decision in mate_one.values()
    )

    shogi = result["rulesets"][1]["capability"]
    assert shogi["status"] == "HARD_FAILURE"
    assert shogi["first_failure"] == "extreme_material"
    assert list(shogi["tasks"]) == [
        "mate_in_one",
        "mate_in_three",
        "avoid_immediate_mate",
        "extreme_material",
    ]
    assert shogi["tasks"]["mate_in_three"]["status"] == "PASS"
    assert shogi["tasks"]["extreme_material"]["status"] == "HARD_FAILURE"

    review = result["review"]
    assert review["primary_node_budget"] == 1000
    assert review["weak_node_budget"] == 128
    assert review["review_node_budget"] == 8000
    assert review["trend_plies"] == (10, 20, 30)
    assert review["pass_thresholds"] == {
        "candidate_to_weak_max_ratio": 0.5,
        "metrics": [
            "normalized_regret",
            "forced_mate_miss_rate",
            "obvious_error_rate",
        ],
        "obvious_regret_floor": 0.5,
    }


def test_reviewer_regret_is_normalized_from_8000_node_action_scores():
    regrets, best_action = _normalized_regrets(
        "reviewer", 100, {"primary": 80, "weak": 40}
    )

    assert best_action == "reviewer"
    assert regrets["primary"] == 1 / 3
    assert regrets["weak"] == 1.0
    assert regrets["primary"] <= regrets["weak"] * PASS_RATIO


def test_exact_half_weak_threshold_covers_all_required_review_metrics():
    row = {
        "normalized_regret": 0.25,
        "weak_normalized_regret": 0.5,
        "forced_mate_miss": 0.0,
        "weak_forced_mate_miss": 0.0,
        "avoid_mate_miss": 0.0,
        "weak_avoid_mate_miss": 0.0,
        "obvious_error": 0.5,
        "weak_obvious_error": 1.0,
    }
    passing = _trend_bucket([row])
    assert passing["primary_at_most_half_weak"] is True
    assert all(passing["threshold_checks"].values())

    failing = _trend_bucket([{**row, "normalized_regret": 0.250001}])
    assert failing["primary_at_most_half_weak"] is False
    assert failing["threshold_checks"]["normalized_regret"] is False
