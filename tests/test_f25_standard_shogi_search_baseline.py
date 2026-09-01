"""Integrity checks for the F25 ten-position Shogi baseline evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from generic_chess.rules.schema import canonical_json


ROOT = Path(__file__).resolve().parents[1]


def _fixture():
    return json.loads(
        (ROOT / "tests/fixtures/f25_standard_shogi_search_baseline.json").read_text(
            encoding="utf-8"
        )
    )


def test_f25_descriptor_and_baseline_integrity():
    descriptor = ROOT / "tests/fixtures/f25_standard_shogi_position_descriptors.json"
    assert hashlib.sha256(descriptor.read_bytes()).hexdigest() == "251884e9a1d0f64ac97be115fa463075e84afee420d5386ec1aac761058469ac"
    fixture = _fixture()
    assert fixture["status"] == "PASS"
    assert fixture["standard_shogi_product_surface_available"] is True
    assert fixture["standard_shogi_search_baseline_frozen"] is True
    assert fixture["standard_shogi_nyugyoku_supported"] is False
    assert fixture["standard_shogi_full_rule_product_ready"] is False
    assert fixture["dual_standard_internal_baseline"] is True
    assert fixture["manifest_sha256"] == "88c94ba6607b3dea85bdbf4b8a08c4265680135fc7b3ccc2833aca21cb693de4"
    assert hashlib.sha256(canonical_json(fixture["manifest"]).encode()).hexdigest() == fixture["manifest_sha256"]
    assert len(fixture["manifest"]["positions"]) == 10
    assert len(fixture["fixed_node"]) == 30
    assert len(fixture["fixed_time"]) == 20
    assert len(fixture["fixed_time_summaries"]) == 20
    assert fixture["dual_standard_summary"]["western_chess"]["position_count"] == 6
    assert fixture["dual_standard_summary"]["standard_shogi"]["position_count"] == 10
    assert "no cross-game" in fixture["dual_standard_summary"]["comparison"]
    assert all(row["deterministic"] and row["overshoot"] == 0 for row in fixture["fixed_node"])
    for row in fixture["fixed_node"]:
        assert len(row["repeats"]) == 2
        assert row["repeats"][0]["action"] == row["repeats"][1]["action"]
        assert row["repeats"][0]["score"] == row["repeats"][1]["score"]
        assert row["repeats"][0]["pv"] == row["repeats"][1]["pv"]
