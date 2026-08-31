import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_f30r1_manifest_and_protocol_contract():
    source = (ROOT / "scripts" / "audit_f30r1_alphasho_reference.py").read_text(encoding="utf-8")
    assert "IMPORTED_HISTORY_PREFIX_UNAVAILABLE" in source
    assert "TIMES = (0.50, 2.00)" in source
    assert "persistent_player_per_game" in source
    assert "BENCHMARK_PLY_CAP" in source
    assert "git config" not in source


def test_f30r1_evidence_is_manifest_bound_and_complete():
    if not all((ROOT / "tests" / "fixtures" / name).is_file() for name in ("f30r1_benchmark_manifest.json", "f30r1_fresh_move_reference.json", "f30r1_paired_match.json")):
        pytest.skip("R1 evidence is generated after the pre-run manifest freeze")
    manifest = json.loads((ROOT / "tests" / "fixtures" / "f30r1_benchmark_manifest.json").read_text(encoding="utf-8"))
    fresh = json.loads((ROOT / "tests" / "fixtures" / "f30r1_fresh_move_reference.json").read_text(encoding="utf-8"))
    paired = json.loads((ROOT / "tests" / "fixtures" / "f30r1_paired_match.json").read_text(encoding="utf-8"))
    assert manifest["kind"] == "F30_R1_PRE_RUN_MANIFEST"
    assert fresh["manifest_sha256"] == manifest["manifest_sha256"]
    assert paired["manifest_sha256"] == manifest["manifest_sha256"]
    assert all(fresh["alphasho"][str(seconds)]["complete"] and fresh["generic_chess"][str(seconds)]["complete"] for seconds in (0.5, 2.0))
    assert paired["complete"] is True
    assert paired["technical_failures"] == 0
    assert len(paired["games"]) == 20
    assert all(len(game["events"]) > 0 for game in paired["games"])
