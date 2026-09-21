"""Tests for the Gate 2 R3 solving-horizon disambiguation."""

from scripts.gate2_r3_forced_win_horizon_disambiguation import run_gate2_r3


def test_gate2_r3_shows_depth2_counterexample_is_horizon_local():
    result = run_gate2_r3()

    assert result["status"] == "PASS"
    assert result["classification"] == "GATE2_DEPTH2_COUNTEREXAMPLE_IS_HORIZON_LOCAL"
    assert result["root_position_digest"] == "48cdc72b8ca6551f2a5cc0bd3b5c4aec6e05aa49a602c7436a22f49f59728114"
    assert result["compute"] == {"depth_3_root_searches": 2, "exact_actions_checked": 1, "max_plies": 3}
    assert result["depth_3_decisions"]["rule_prior"]["completed_depth"] == 3
    assert result["depth_3_decisions"]["flat_control"]["completed_depth"] == 3
    assert result["depth_3_decisions"]["rule_prior"]["action_digest"] == result["depth_3_decisions"]["flat_control"]["action_digest"]
    assert result["exact_forced_win_checks"][0]["forced_mate_within_3_plies"] is True
