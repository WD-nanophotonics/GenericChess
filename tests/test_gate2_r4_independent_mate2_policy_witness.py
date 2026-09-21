"""Tests for the independent Gate 2 R4 mate-in-two witness."""

from scripts.gate2_r4_independent_mate2_policy_witness import run_gate2_r4


def test_gate2_r4_builds_independent_nontrivial_witness_and_solves_at_depth3():
    result = run_gate2_r4()

    assert result["status"] == "PASS"
    assert result["classification"] == "GATE2_R4_NEITHER_GUIDED_TO_WINNING_ROUTE"
    assert result["source_ruleset_fingerprint"] == "856a810d3a21eec779f9ba8300ce602cd24d3e8850ba895e39579603fd4ff3e2"
    assert result["source_template_id"] == "T0075"
    assert result["source_validated_exact_checkmate"] is True
    assert result["compute"] == {"candidate_checks": 119, "depth_2_searches": 2, "depth_3_searches": 2}
    assert result["witness"]["legal_action_count"] == 6
    assert result["witness"]["forced_mate_action_count"] == 1
    assert result["witness"]["non_forced_action_count"] == 5
    assert result["depth_2"]["rule_prior"]["selected_forced_mate_action"] is False
    assert result["depth_2"]["flat_control"]["selected_forced_mate_action"] is False
    assert result["depth_3"]["rule_prior"]["selected_forced_mate_action"] is True
    assert result["depth_3"]["flat_control"]["selected_forced_mate_action"] is True
