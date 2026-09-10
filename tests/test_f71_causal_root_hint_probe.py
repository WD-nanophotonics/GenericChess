"""Static and data-contract checks for the bounded F71 causal probe."""

from pathlib import Path

import pytest

from generic_chess.native import native_available
from scripts import f71_causal_root_hint_probe as f71


ROOT = Path(__file__).resolve().parents[1]


def test_f71_contract_is_bounded_and_does_not_authorize_heavy_or_promotion():
    source = (ROOT / "scripts" / "f71_causal_root_hint_probe.py").read_text(encoding="utf-8")
    assert f71.WORK_ORDER == "GENERICCHESS-F71-CAUSAL-ROOT-HINT-PROBE"
    assert f71.PARENT_SHA == "a180486b6a709a456d4a55a44a35ef716d4e4e20"
    assert f71.HINT_SEED == 59011
    assert f71.NODES == 2_000
    assert f71.EXPECTED_STABLE_ROOTS == 20
    assert "ROOT_HINT_CAUSAL_SUPPORTED" in source
    assert "ROOT_HINT_CAUSAL_NEUTRAL" in source
    assert "ROOT_HINT_CAUSAL_NEGATIVE" in source
    assert "HARNESS_MISMATCH" in source
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


@pytest.mark.skipif(not native_available(), reason="native extension is not built")
def test_f71_native_capsule_layout_matches_runtime():
    assert f71.ctypes.sizeof(f71._SemPosition) == 53920
    assert f71.ctypes.sizeof(f71._SemEntry) > 0

