"""Regression coverage for the single corrected merged Gate 2 benchmark."""

from scripts.gate2_merged_benchmark import (
    CAPABILITY_BRANCH_LIMIT,
    CAPABILITY_STATE_LIMIT,
    PASS_RATIO,
    _has_optional_promotion,
    _normalized_regrets,
    _trend_bucket,
    run_merged,
)
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


def test_optional_promotion_applicability_uses_compiled_contract():
    chess = compile_ruleset_for_execution(build_western_chess_ruleset())
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())

    assert _has_optional_promotion(chess) is False
    assert _has_optional_promotion(shogi) is True


def test_merged_gate2_resumes_after_exact_proxy_divergence_and_stops_next_failure():
    result = run_merged()

    assert result["status"] == "FIRST_HARD_FAILURE"
    assert result["gate2_status"] == "FAILED"
    assert result["gate3_status"] == "FROZEN"
    assert result["classification"] == "RULE_PRIOR_ABP_BASIC_COMPETENCE_UNRESOLVED_AT_CAPABILITY"
    assert result["first_hard_failure"] == {
        "layer": "capability",
        "ruleset": "generated_L_V5-3",
        "reason": "mobility",
        "failure_type": "HARD_FAILURE",
    }
    assert result["gate1"]["games"] == ["chess", "shogi"]
    assert [row["label"] for row in result["rulesets"]] == [
        "chess",
        "shogi",
        "generated_L_V4-3",
        "generated_F_V4-3",
        "generated_N_V4-3",
        "generated_L_V5-3",
    ]
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

    assert tasks["promotion"] == {
        "status": "NOT_APPLICABLE",
        "reason": "NO_OPTIONAL_PROMOTION_SEMANTICS",
    }
    extreme = tasks["extreme_material"]
    assert extreme["status"] == "PASS"
    assert extreme["all_children_nonterminal"] is True
    assert extreme["positive_capture_action_count"] >= 2
    assert len(extreme["positive_capture_value_set"]) >= 2
    assert extreme["one_ply_best_actions"] == extreme["expected_actions"]
    assert extreme["primary_expected"] is True
    assert extreme["reviewer_expected"] is True
    material_decisions = extreme["decisions"]
    for role in ("primary", "reviewer"):
        assert material_decisions[role]["search_limit_mode"] == "fixed_depth_1"
        assert material_decisions[role]["max_nodes"] is None
        assert material_decisions[role]["max_depth"] == 1
        assert material_decisions[role]["completed_depth"] == 1
        assert material_decisions[role]["termination_reason"] == "completed_depth"
        assert (
            material_decisions[role]["selected_action"]
            in extreme["expected_actions"]
        )
    assert material_decisions["weak"]["search_limit_mode"] == "node_budget"
    assert material_decisions["weak"]["max_nodes"] == 128

    shogi = result["rulesets"][1]["capability"]
    assert shogi["status"] == "PASS"
    assert shogi["tasks"]["mate_in_three"]["status"] == "PASS"
    assert shogi["tasks"]["extreme_material"]["status"] == "PASS"
    promotion = shogi["tasks"]["promotion"]
    assert promotion["status"] == "PASS"
    assert promotion["all_children_nonterminal"] is True
    assert promotion["optional_promotion_group_count"] >= 1
    assert promotion["promotion_favorable_group_count"] >= 1
    assert promotion["one_ply_best_actions"] == promotion["expected_actions"]
    assert all(
        action["promotion_target_id"] is not None
        for action in promotion["expected_actions"]
    )
    for group in promotion["promotion_favorable_groups"]:
        assert group["promoted"]
        assert group["unpromoted"]
        assert group["score_advantage"] > 0
        assert max(row["one_ply_score"] for row in group["promoted"]) > max(
            row["one_ply_score"] for row in group["unpromoted"]
        )
    promotion_decisions = promotion["decisions"]
    for role in ("primary", "reviewer"):
        assert promotion_decisions[role]["search_limit_mode"] == "fixed_depth_1"
        assert promotion_decisions[role]["max_nodes"] is None
        assert promotion_decisions[role]["max_depth"] == 1
        assert promotion_decisions[role]["completed_depth"] == 1
        assert promotion_decisions[role]["termination_reason"] == "completed_depth"
        assert promotion_decisions[role]["selected_action"] in promotion["expected_actions"]

    drop = shogi["tasks"]["drop"]
    assert drop["status"] == "PASS"
    assert drop["all_children_nonterminal"] is True
    assert drop["drop_action_count"] >= 1
    assert drop["non_drop_action_count"] >= 1
    assert drop["best_drop_score"] > drop["best_non_drop_score"]
    assert drop["drop_score_advantage"] == (
        drop["best_drop_score"] - drop["best_non_drop_score"]
    )
    assert drop["one_ply_best_actions"] == drop["expected_actions"]
    assert all(action["kind"].endswith("drop") for action in drop["expected_actions"])
    assert drop["expected_drop_base_type_ids"]
    assert drop["witness_history_mode"] == "fixed_root"
    drop_decisions = drop["decisions"]
    for role in ("primary", "reviewer"):
        assert drop_decisions[role]["search_limit_mode"] == "fixed_depth_1"
        assert drop_decisions[role]["max_nodes"] is None
        assert drop_decisions[role]["max_depth"] == 1
        assert drop_decisions[role]["completed_depth"] == 1
        assert drop_decisions[role]["termination_reason"] == "completed_depth"
        assert drop_decisions[role]["selected_action"] in drop["expected_actions"]
    assert drop_decisions["weak"]["search_limit_mode"] == "node_budget"
    assert drop_decisions["weak"]["max_nodes"] == 128

    for capability in (
        result["rulesets"][0]["capability"],
        result["rulesets"][1]["capability"],
    ):
        anchor = capability["tasks"]["anchor_danger"]
        assert anchor["status"] == "PASS"
        assert anchor["all_children_nonterminal"] is True
        assert anchor["checking_action_count"] >= 1
        assert anchor["nonchecking_action_count"] >= 1
        assert anchor["best_checking_score"] > anchor["best_nonchecking_score"]
        assert anchor["anchor_pressure_advantage"] == (
            anchor["best_checking_score"] - anchor["best_nonchecking_score"]
        )
        assert anchor["one_ply_best_actions"] == anchor["expected_actions"]
        assert anchor["one_ply_best_all_checking"] is True
        for role in ("primary", "reviewer"):
            decision = anchor["decisions"][role]
            assert decision["search_limit_mode"] == "fixed_depth_1"
            assert decision["max_nodes"] is None
            assert decision["completed_depth"] == 1
            assert decision["termination_reason"] == "completed_depth"
            assert decision["selected_action"] in anchor["expected_actions"]
        assert anchor["decisions"]["weak"]["max_nodes"] == 128

    generated = result["rulesets"][2]["capability"]
    assert generated["status"] == "PASS"
    assert generated["tasks"]["extreme_material"]["status"] == "PASS"
    assert generated["tasks"]["mobility"]["status"] == "PASS"
    assert generated["tasks"]["anchor_danger"] == {
        "status": "NOT_OBSERVED",
        "reason": "NO_CONTROLLED_ANCHOR_WITNESS_IN_BOUNDED_SCAN",
    }

    fv43 = result["rulesets"][3]["capability"]
    assert result["rulesets"][3]["ruleset_fingerprint"] == (
        "8ca58376a52e539c7c8519e902b8dd9e6991b002586d36d846a7a864fffea05d"
    )
    assert fv43["status"] == "PROXY_DIVERGENCE"
    assert fv43["disposition"] == "NON_BLOCKING_DIAGNOSTIC"
    assert fv43["first_failure"] is None
    assert fv43["tasks"]["extreme_material"]["status"] == "PASS"
    mobility = fv43["tasks"]["mobility"]
    assert mobility["criterion_status"] == "HARD_FAILURE"
    assert mobility["status"] == "PROXY_DIVERGENCE"
    assert mobility["disposition"] == "NON_BLOCKING_DIAGNOSTIC"
    assert mobility["primary_expected"] is False
    cause = mobility["cause_check"]
    assert cause["classification"] == (
        "GATE2_MOBILITY_CAUSE_GENERATED_SURFACE_PROXY_DIVERGENCE"
    )
    assert cause["criterion_argmax_actions"] == mobility["expected_actions"]
    assert cause["existing_expected_actions"] == mobility["expected_actions"]
    assert cause["production_mobility_component_argmax_actions"]
    assert cause["full_production_one_ply_argmax_actions"]
    assert cause["legal_action_count"] >= len(mobility["expected_actions"])
    assert cause["primary1000_action"] == mobility["primary_action"]
    assert cause["reviewer8000_action"] == mobility["reviewer_action"]
    fixed = cause["fixed_depth_1_production"]
    assert fixed["search_limit_mode"] == "fixed_depth_1"
    assert fixed["max_nodes"] is None
    assert fixed["max_depth"] == 1
    assert fixed["completed_depth"] == 1
    assert fixed["termination_reason"] == "completed_depth"
    reference = cause["reference_minimax_depth_1"]
    assert reference["selected_action"] is not None
    assert isinstance(reference["score"], int)
    local = cause["local_strength_review"]
    assert local["classification"] == (
        "GATE2_MOBILITY_PROXY_FAILURE_PRIMARY_TIES_WEAK"
    )
    assert local["primary_matches_reviewer_quality"] is True
    allowed_actions = [
        mobility["primary_action"],
        mobility["weak_action"],
        mobility["reviewer_action"],
        *mobility["expected_actions"],
    ]
    compared = local["compared_actions"]
    assert len(compared) <= 4
    assert len({str(row["action"]) for row in compared}) == len(compared)
    assert all(row["action"] in allowed_actions for row in compared)
    for row in compared:
        assert row["role_labels"]
        if row["review_limit_mode"] == "node_budget":
            assert row["review_max_nodes"] == 8000
            assert row["continuation_review_nodes"] > 0
        else:
            assert row["review_limit_mode"] == "terminal_score"
            assert row["review_max_nodes"] is None
            assert row["continuation_review_nodes"] == 0
    summaries = local["role_summaries"]
    assert set(summaries) == {
        "primary1000",
        "weak128",
        "reviewer8000",
        "criterion_expected",
    }
    for summary in summaries.values():
        assert summary["regret"] >= 0
        assert 0.0 <= summary["normalized_regret"] <= 1.0
    shadow = cause["shadow_ruleset_strength"]
    assert shadow["classification"] == (
        "GATE2_FV43_PRIMARY_STRENGTH_SUPPORTED_VS_WEAK128"
    )
    assert shadow["ruleset"] == "generated_F_V4-3"
    assert shadow["ruleset_fingerprint"] == (
        "8ca58376a52e539c7c8519e902b8dd9e6991b002586d36d846a7a864fffea05d"
    )
    assert shadow["budgets"] == {
        "primary_nodes": 1000,
        "weak_nodes": 128,
        "reviewer_nodes": 8000,
    }
    games = shadow["games"]
    assert len(games) == 4
    assert {game["label"] for game in games} == {"generated_F_V4-3"}
    assert {
        (game["opening"], game["primary_owner"]) for game in games
    } == {
        ("initial", 0),
        ("initial", 1),
        ("shallow_random", 0),
        ("shallow_random", 1),
    }
    assert shadow["summary"]["game_count"] == 4
    assert set(shadow["trends"]["aggregate"]) == {"10", "20", "30"}
    assert set(shadow["trends"]["by_ruleset"]) == {"generated_F_V4-3"}
    assert set(shadow["trends"]["by_ruleset"]["generated_F_V4-3"]) == {
        "10",
        "20",
        "30",
    }
    nv43 = result["rulesets"][4]
    assert nv43["label"] == "generated_N_V4-3"
    assert nv43["ruleset_fingerprint"] == (
        "856a810d3a21eec779f9ba8300ce602cd24d3e8850ba895e39579603fd4ff3e2"
    )
    assert nv43["capability"]["status"] == "PASS"

    lv53 = result["rulesets"][5]
    assert lv53["label"] == "generated_L_V5-3"
    assert lv53["ruleset_fingerprint"] == (
        "1a256a4fcc763cb6f4e5ca1037a77b72885d4e85a4d5e46ccf88c69f552b266d"
    )
    assert lv53["capability"]["status"] == "HARD_FAILURE"
    assert lv53["capability"]["first_failure"] == "mobility"
    extreme = lv53["capability"]["tasks"]["extreme_material"]
    assert extreme["status"] == "PASS"
    assert extreme["witness_label"] == "controlled_material_fixture"
    assert extreme["fixture_kind"] == "exact_fingerprint_controlled_material"
    assert extreme["positive_capture_action_count"] == 2
    assert extreme["positive_capture_value_set"] == [905, 1095]
    assert extreme["max_capture_value"] == 1095
    assert extreme["all_children_nonterminal"] is True
    assert extreme["expected_actions"] == extreme["one_ply_best_actions"]
    assert extreme["primary_expected"] is True
    assert extreme["reviewer_expected"] is True
    assert extreme["decisions"]["primary"]["completed_depth"] == 1
    assert extreme["decisions"]["reviewer"]["completed_depth"] == 1
    assert "witness_absence_cause" not in extreme
    mobility = lv53["capability"]["tasks"]["mobility"]
    assert mobility["status"] == "HARD_FAILURE"
    assert mobility["witness_label"] == "initial"
    assert mobility["primary_expected"] is False
    assert mobility["reviewer_expected"] is False
    assert CAPABILITY_STATE_LIMIT == 240
    assert CAPABILITY_BRANCH_LIMIT == 4
    material_absence_rows = [
        (ruleset["label"], task_name)
        for ruleset in result["rulesets"]
        for task_name, task in ruleset["capability"]["tasks"].items()
        if isinstance(task, dict) and "witness_absence_cause" in task
    ]
    assert material_absence_rows == []
    assert len(result["rulesets"]) == 6
    assert "generated_F_V5-3" not in {
        ruleset["label"] for ruleset in result["rulesets"]
    }
    dispositions = [
        (ruleset["label"], task_name, task["disposition"])
        for ruleset in result["rulesets"]
        for task_name, task in ruleset["capability"]["tasks"].items()
        if isinstance(task, dict) and "disposition" in task
    ]
    assert dispositions == [
        ("generated_F_V4-3", "mobility", "NON_BLOCKING_DIAGNOSTIC")
    ]

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
