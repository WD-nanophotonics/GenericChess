"""Tests for the corrected Gate 2 mate-in-three horizon diagnostic."""

from scripts.gate2_mate3_solving_horizon_diagnostic import run_diagnostic


def test_gate2_mate3_solving_horizon_diagnostic():
    result = run_diagnostic()

    assert result["status"] == "PASS"
    assert result["ground_truth"]["passed"] is True
    assert result["ground_truth"]["forced_action_count"] == 1
    assert result["ground_truth"]["forced_uci"] == ["d4e5"]
    assert result["compute"]["production_searches"] == 2
    assert result["compute"]["max_depth"] == 3
    assert result["compute"]["node_cap"] is None
    assert result["compute"]["exact_controls"] == 0
    assert result["classification"] == (
        "GATE2_MATE3_FAILURE_IS_NODE_BUDGET_HORIZON_SHORTFALL"
    )
    assert result["searches"]["depth_2"]["selected_uci"] != "d4e5"
    assert result["searches"]["depth_3"]["selected_uci"] == "d4e5"
    assert result["searches"]["depth_2"]["completed_depth"] == 2
    assert result["searches"]["depth_3"]["completed_depth"] == 3
    assert result["searches"]["depth_2"]["termination_reason"] == "completed_depth"
    assert result["searches"]["depth_3"]["termination_reason"] == "completed_depth"
    assert result["exact_depth3_control"] is None
