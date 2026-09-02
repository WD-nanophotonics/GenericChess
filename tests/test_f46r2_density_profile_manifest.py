"""H46R2A integrity tests for the corrected F46 gate protocol."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f46r2_density_profile_manifest.json"


def test_h46r2a_freezes_correct_reference_and_complete_gates():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    assert hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == data["manifest_sha256"]
    assert data["density_points"] == [0.0, 0.125, 0.25, 0.375, 0.5]
    assert data["shogi_reference"]["representation"].startswith("accepted current normalized")
    assert "observed_result" not in data


def test_h46r2a_freezes_four_reducers_and_six_classifications():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(data["reducer_definitions"]) == 4
    assert "min_le_harmonic_le_geometric_le_arithmetic" in data["algebra_gates"]
    assert "F44_blocker_witness" in data["semantic_qualification_gates"]
    assert len(data["qualification_mapping"]) == 6


def test_h46r2a_is_anchored_after_published_first_pass():
    assert subprocess.run(["git", "merge-base", "--is-ancestor", "6eed502", "HEAD"], cwd=ROOT).returncode == 0
