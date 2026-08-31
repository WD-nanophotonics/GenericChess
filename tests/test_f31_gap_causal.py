import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_f31_manifest_contract_is_audit_only():
    source = (ROOT / "scripts" / "audit_f31_gap_causal.py").read_text(encoding="utf-8")
    assert "NO_TUNING_FROM_RESULTS" in source
    assert "static_and_qsearch" in source
    assert "fixed_node_matrix" in source
    assert "IMPORTED_HISTORY_PREFIX_UNAVAILABLE" in source
    assert "F32_CAPABILITY_SCOPED_NATIVE_LEGALITY_REENABLEMENT" in source
    assert "git config" not in source


def test_f31_evidence_is_optional_before_stage_b_and_bound_afterwards():
    paths = [ROOT / "tests" / "fixtures" / name for name in ("f31_causal_manifest.json", "f31_causal_diagnosis.json")]
    if not all(path.is_file() for path in paths):
        pytest.skip("F31 Stage B evidence is generated after manifest freeze")
    manifest = json.loads(paths[0].read_text(encoding="utf-8"))
    result = json.loads(paths[1].read_text(encoding="utf-8"))
    assert result["manifest_sha256"] == manifest["manifest_sha256"]
    assert all(result["flags"].values())
    assert result["production_changed"] is False
