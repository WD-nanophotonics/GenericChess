"""Tests for the exact Gate 2 R2 selected-action predicate."""

from scripts.gate2_r2_selected_action_forced_win_check import run_gate2_r2


def test_gate2_r2_confirms_rule_prior_tactical_counterexample():
    result = run_gate2_r2()

    assert result["status"] == "PASS"
    assert result["classification"] == "RULE_PRIOR_TACTICAL_COUNTEREXAMPLE_CONFIRMED"
    assert result["root_position_digest"] == "48cdc72b8ca6551f2a5cc0bd3b5c4aec6e05aa49a602c7436a22f49f59728114"
    assert result["r1_reproduction"]["flat_control"]["equals_certified_action"] is True
    assert result["r1_reproduction"]["rule_prior"]["equals_certified_action"] is False
    certified, rule_prior = result["actions"]
    assert certified["forced_mate_within_3_plies"] is True
    assert certified["opponent_reply_count"] == 2
    assert [row["mating_continuation_count"] for row in certified["opponent_replies"]] == [1, 1]
    assert rule_prior["forced_mate_within_3_plies"] is False
    assert rule_prior["opponent_reply_count"] == 8
    assert all(row["mating_continuation_count"] == 0 for row in rule_prior["opponent_replies"])
