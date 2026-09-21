"""Regression coverage for the Gate 3 R1 leverage diagnostic."""

from scripts.gate3_r1_rule_prior_contrast_leverage import run_gate3


def test_gate3_r1_proves_checkpoint_parity_and_classifies_leverage():
    result = run_gate3()

    assert result["status"] == "PASS"
    assert result["source_ruleset_fingerprint"] == "29390db6050d1ba482a393f7466608a6f19d0df9e6d4f7c3bd3a556f2d194fff"
    assert result["root_position_digests"] == [
        "48cdc72b8ca6551f2a5cc0bd3b5c4aec6e05aa49a602c7436a22f49f59728114",
        "0d3d1f1d40190e526e2f8d60cafb5817734d8aa558572a9d753f1366a7035472",
        "2904701542900474233a19ca2796b391bceda73235aeaeae20cad4adaa658fe9",
    ]
    assert all(row["root"]["exact"] for row in result["parity"])
    assert all(all(child["exact"] for child in row["children"]) for row in result["parity"])
    assert result["compute"]["search_count"] in (9, 15)
    assert result["classification"] in {
        "GATE3_RULE_PRIOR_CONTRAST_HAS_LOCAL_LEVERAGE",
        "GATE3_RULE_PRIOR_CONTRAST_NO_LOCAL_LEVERAGE",
    }
