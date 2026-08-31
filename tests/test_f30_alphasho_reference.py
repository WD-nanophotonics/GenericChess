import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_f30_audit_contract_is_read_only_and_bounded():
    source = (ROOT / "scripts" / "audit_f30_alphasho_reference.py").read_text(encoding="utf-8")
    assert "safe.directory={ALPHASHO_ROOT}" in source
    assert "FROZEN_BUDGETS = (128, 256, 512, 1024, 2048)" in source
    assert "REFERENCE_SECONDS = 0.50" in source
    assert "ALPHASHO_PAIRED_BENCHMARK_COMPLETE" in source
    assert "git config" not in source
    assert "write_text" in source


def test_f30_frozen_descriptor_and_reference_contract():
    fixture = json.loads((ROOT / "tests" / "fixtures" / "f25_standard_shogi_position_descriptors.json").read_text(encoding="utf-8"))
    assert fixture["source_commit"] == "3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38"
    assert len(fixture["positions"]) == 10
    assert all(row["sfen"].endswith(" b - 13") for row in fixture["positions"])


def test_f30_recorded_benchmark_is_complete_and_no_technical_failures():
    result = json.loads((ROOT / "tests" / "fixtures" / "f30_alphasho_reference_benchmark.json").read_text(encoding="utf-8"))
    assert result["status"] == "PASS"
    assert all(result["flags"].values())
    assert len(result["historical_replay"]["runs"]) == 50
    assert sum(len(row["repeats"]) for row in result["historical_replay"]["runs"]) == 100
    assert result["historical_replay"]["all_deterministic"] is True
    assert result["fresh_alphasho"]["complete"] is True
    assert result["fresh_generic_chess"]["complete"] is True
    assert result["paired_benchmark"]["complete"] is True
    assert result["paired_benchmark"]["technical_failures"] == 0
    assert len(result["paired_benchmark"]["games"]) == 20
