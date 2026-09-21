"""Contract test for the bounded F158 rule-prior micro-arena."""

from scripts.f158_rule_prior_vs_flat_control_microarena import run_benchmark


def test_f158_rule_prior_vs_flat_control_microarena_is_inconclusive():
    result = run_benchmark()
    assert result["classification"] == "RULE_PRIOR_BASELINE_STRENGTH_SIGNAL_INCONCLUSIVE", result
    assert result["ruleset_seeds"] == [15701, 15702]
    assert result["pair_count"] == 4
    assert result["game_count"] == 8
    assert result["search"] == {
        "max_depth": 2,
        "qsearch": "0/0",
        "max_nodes": None,
        "use_ordering": False,
        "use_tt": False,
    }
    for data in result["games"].values():
        assert len(data["pairs"]) == 2
        assert all(pair["pair_score"] == 0.5 for pair in data["pairs"])
        assert all(
            game["terminal_status"] == "stalemate"
            and game["score"] == 0.5
            for pair in data["pairs"]
            for game in pair["games"]
        )
