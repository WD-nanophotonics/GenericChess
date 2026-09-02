"""H46A integrity tests; no observed reducer or classification is frozen."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f46_density_profile_manifest.json"


def test_h46a_is_frozen_and_pre_result():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    assert hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == data["manifest_sha256"]
    assert data["baseline"]["f45_sha"] == "b0fc4d2da1a6cb0b818b713305dce84cef3e8e6e"
    assert "observed_result" not in data
    assert len(data["reducer_definitions"]) == 4


def test_h46a_binds_frozen_controls_and_mapping():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert set(data["f44_f45_evidence_bindings"]) == {"f44_density", "f45_discrimination", "f45_orientation", "f45_placement", "f45_selection"}
    assert data["density_points"] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert set(data["qualification_mapping"]) == {"DENSITY_PROFILE_CANDIDATE_SUPPORTED", "MULTIPLE_DENSITY_PROFILE_CANDIDATES", "DENSITY_PROFILE_CROSS_RULESET_CONFLICT", "DENSITY_PROFILE_REDUCTION_INSUFFICIENT", "DENSITY_PROFILE_REDUCTION_MISMATCH", "MIXED_OR_UNRESOLVED"}


def test_h46a_is_published_as_its_own_pre_execution_checkpoint():
    assert subprocess.run(["git", "merge-base", "--is-ancestor", "b0fc4d2", "HEAD"], cwd=ROOT).returncode == 0
