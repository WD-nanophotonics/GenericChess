"""Compact integrity checks for the F24H frozen Western baseline evidence."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _fixture():
    return json.loads(
        (ROOT / "tests/fixtures/f24h_western_search_baseline.json").read_text(
            encoding="utf-8"
        )
    )


def test_f24h_baseline_fixture_is_complete_and_passed():
    fixture = _fixture()
    assert fixture["status"] == "PASS"
    assert fixture["western_chess_product_ready_baseline"] is True
    assert fixture["manifest_sha256"] == "cbf3d5bfdaad12dd54a7868f9bbf68bf9ce875931e2b4e8acdc34129c847e308"
    assert fixture["manifest"]["ruleset_fingerprint"] == "7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35"
    assert fixture["manifest"]["native_provider_policy"]["actual"] == "PYTHON_AUTHORITY_FALLBACK"
    assert len(fixture["canonical_perft"]) == 20
    assert all(row["actual"] == row["expected"] for row in fixture["canonical_perft"])
    assert len(fixture["fixed_node"]) == 18
    assert len(fixture["fixed_time"]) == 12
    assert len(fixture["fixed_time_summaries"]) == 12
    for row in fixture["fixed_node"]:
        assert row["deterministic"] is True
        assert len(row["repeats"]) == 2
        assert row["repeats"][0]["action"] == row["repeats"][1]["action"]
        assert row["repeats"][0]["score"] == row["repeats"][1]["score"]
        assert row["repeats"][0]["pv"] == row["repeats"][1]["pv"]

