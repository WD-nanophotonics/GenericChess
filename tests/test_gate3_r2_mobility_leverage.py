"""Regression coverage for the Gate 3 R2 mobility leverage diagnostic."""

from scripts.gate3_r2_mobility_leverage import run_gate3_r2


def test_gate3_r2_classifies_mobility_leverage_with_gen0_guard():
    result = run_gate3_r2()

    assert result["status"] == "PASS"
    assert result["gen0_checkpoint_id"] == "0d71bf4f9385820bf30fc905a65c6456d70ad7c4c4f90c3809729853eaa38c1d"
    assert result["root_digests"] == [
        "48cdc72b8ca6551f2a5cc0bd3b5c4aec6e05aa49a602c7436a22f49f59728114",
        "0d3d1f1d40190e526e2f8d60cafb5817734d8aa558572a9d753f1366a7035472",
        "2904701542900474233a19ca2796b391bceda73235aeaeae20cad4adaa658fe9",
    ]
    assert result["compute"]["search_count"] in (9, 15)
    assert result["classification"] in {
        "GATE3_MOBILITY_HAS_LOCAL_LEVERAGE",
        "GATE3_MOBILITY_NO_LOCAL_LEVERAGE",
    }
