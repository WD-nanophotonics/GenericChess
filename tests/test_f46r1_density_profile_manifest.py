"""H46R1A integrity tests for the corrected density protocol freeze."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f46r1_density_profile_manifest.json"


def test_h46r1a_corrects_points_and_is_pre_result():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    assert hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == data["manifest_sha256"]
    assert data["density_points"] == [0.0, 0.125, 0.25, 0.375, 0.5]
    assert data["density_weights"] == [0.25, 0.2, 0.2, 0.18, 0.17]
    assert "observed_result" not in data


def test_h46r1a_has_all_reducer_gates_and_mapping():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(data["reducer_definitions"]) == 4
    assert len(data["structural_gates"]) == 11
    assert len(data["qualification_mapping"]) == 6


def test_h46r1a_is_anchored_to_published_h46a_before_execution():
    assert subprocess.run(["git", "merge-base", "--is-ancestor", "fbcf61d", "HEAD"], cwd=ROOT).returncode == 0
