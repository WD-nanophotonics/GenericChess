"""Tests for the Gate 2 mate-in-three exact node threshold diagnostic."""

from scripts.gate2_mate3_exact_node_threshold import run_diagnostic


def test_gate2_mate3_exact_node_threshold():
    result = run_diagnostic()

    assert result["status"] == "PASS"
    assert result["ground_truth_reproduction"] == {
        "forced_action_count": 1,
        "forced_uci": ["d4e5"],
        "passed": True,
    }
    assert result["compute"] == {
        "production_searches": 2,
        "max_depth": 3,
        "node_caps": [21248, 21249],
    }
    assert len(result["searches"]) == 2
    capped, boundary = result["searches"]
    assert result["classification"] == "GATE2_MATE3_EXACT_MIN_NODE_CAP_21249"
    assert capped["max_nodes"] == 21248
    assert capped["completed_depth"] == 2
    assert capped["selected_uci"] != "d4e5"
    assert capped["nodes"] == 21248
    assert capped["termination_reason"] == "node_limit"
    assert boundary["max_nodes"] == 21249
    assert boundary["completed_depth"] == 3
    assert boundary["selected_uci"] == "d4e5"
    assert boundary["root_score"] == 999999997
    assert boundary["nodes"] == 21248
    assert boundary["termination_reason"] == "completed_depth"
