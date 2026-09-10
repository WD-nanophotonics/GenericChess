"""Static and data-contract checks for the bounded F71-R1 corrective probe."""

from pathlib import Path

from scripts import f71_causal_root_hint_probe as f71


ROOT = Path(__file__).resolve().parents[1]


def test_f71_r1_contract_is_bounded_and_does_not_authorize_heavy_or_promotion():
    source = (ROOT / "scripts" / "f71_causal_root_hint_probe.py").read_text(encoding="utf-8")
    assert f71.WORK_ORDER == "GENERICCHESS-F71-R1-ROOT-HINT-HARNESS-CORRECTIVE"
    assert f71.PARENT_SHA == "1f378782db9c1b1c314abdf863d4a94d37294cd4"
    assert f71.HINT_SEED == 59011
    assert f71.NODES == 2_000
    assert f71.EXPECTED_STABLE_ROOTS == 20
    assert "SUPPORTED" in source
    assert "NEUTRAL" in source
    assert "NEGATIVE" in source
    assert "HARNESS_MISMATCH" in source
    assert "root_order_hint=hint" in source
    assert "_inject_root_hint" not in source
    assert "ctypes" not in source
    assert "arena" not in source.lower()
    assert "self-play" not in source.lower()


def test_f71_f62_development_filter_has_exact_twenty_stable_roots():
    roots = f71._load_stable_roots()
    assert len(roots) == 20
    assert all(root["record"]["source_split"] == "development" for root in roots)
    assert all(
        root["metadata"]["root_40k"]["action_key"]
        == root["metadata"]["root_80k"]["action_key"]
        for root in roots
    )
