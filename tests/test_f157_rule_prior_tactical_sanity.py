"""Contract test for the bounded F157 rule-prior diagnostic."""

from scripts.f157_rule_prior_tactical_sanity import run_probe


def test_f157_rule_prior_tactical_sanity_passes():
    result = run_probe()
    assert result["classification"] == "RULE_PRIOR_TACTICAL_SANITY_PASS", result
    assert len(result["witnesses"]) == 2
    assert result["compute"] == {
        "games": 0,
        "heavy": False,
        "depth1_searches": 2,
        "depth2_searches": 0,
    }
    for row in result["witnesses"]:
        assert row["high_value"] > row["low_value"]
        assert row["material_owner0_perspective"]["difference"] > 0
        assert row["scores_owner0_perspective"]["difference"] > 0
        assert row["high_capture_unique_full_best"] is True
        assert row["search_smoke"]["high_capture_chosen"] is True
        assert row["search_smoke"]["completed_depth"] == 1
