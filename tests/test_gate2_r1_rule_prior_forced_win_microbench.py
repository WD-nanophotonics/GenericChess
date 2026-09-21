"""Tests for the bounded Gate 2 R1 evaluator microbenchmark."""

from scripts.gate2_r1_rule_prior_forced_win_microbench import run_gate2


def test_gate2_r1_replays_frozen_root_and_stops_on_nonwinning_divergence():
    result = run_gate2()

    assert result["status"] == "PASS"
    assert result["source_ruleset_fingerprint"] == "29390db6050d1ba482a393f7466608a6f19d0df9e6d4f7c3bd3a556f2d194fff"
    assert result["root_position_digest"] == "48cdc72b8ca6551f2a5cc0bd3b5c4aec6e05aa49a602c7436a22f49f59728114"
    assert result["replay"]["prefix_plies"] == 10
    assert result["rule_prior_values"]["P0"] == 1095
    assert result["rule_prior_values"]["P1"] == 905
    assert result["compute"] == {"root_searches": 2, "conversion_trials": 0, "max_conversion_plies": 6}
    assert result["classification"] == "GATE2_R1_POLICY_DIVERGENCE_WITHOUT_WINNING_ROUTE"
    assert result["root_decisions"]["flat_control"]["equals_certified_action"] is True
    assert result["root_decisions"]["rule_prior"]["equals_certified_action"] is False
    assert result["conversion_trials"] == []
