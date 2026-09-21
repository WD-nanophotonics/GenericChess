"""Contract test for the bounded F159 policy-divergence probe."""

from scripts.f159_f158_policy_divergence_microprobe import run_probe


def test_f159_reproduces_four_f158_roots_and_runs_eight_searches():
    result = run_probe()
    assert result["classification"] == "F158_POLICY_DIVERGENCE_EXISTS_BUT_STALEMATE_ERASES_OUTCOME_SIGNAL", result
    assert result["rulesets"] == [15701, 15702]
    assert result["search_count"] == 8
    assert result["game_count"] == 0
    assert result["heavy"] is False
    assert len(result["rows"]) == 4
    assert {row["seed"] for row in result["rows"]} == {15701, 15702}
    assert sorted(row["opening_plies"] for row in result["rows"]) == [0, 0, 2, 2]
    assert all(row["legal_action_count"] > 0 for row in result["rows"])
    assert any(not row["actions_equal"] for row in result["rows"])
