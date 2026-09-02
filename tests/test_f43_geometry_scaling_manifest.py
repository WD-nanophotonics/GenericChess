"""H43A freezes the F43 geometry-scaling prototype before alternatives."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f43_geometry_scaling_manifest.json"
sys.path.insert(0, str(ROOT / "scripts"))

from repository_provenance import require_migrated_binding  # noqa: E402


def test_h43a_manifest_is_frozen_and_inputs_match():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    expected = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert expected == data["manifest_sha256"]
    assert data["baseline"]["f42_sha"] == "6504a45dff2e1a726feb94d6aa83ac5128e0985d"
    assert list(data["transforms"]) == ["G43-0_LINEAR_CONTROL", "G43-1_PER_GEOMETRY_LOG", "G43-2_PER_SOURCE_LOG", "G43-3_HIERARCHICAL_LOG"]
    assert all(data["constraints"].values())
    for name, binding in data["input_files"].items():
        require_migrated_binding(ROOT, "F43", "tests/fixtures/f43_geometry_scaling_manifest.json", name, data["baseline"]["f42_sha"], binding["path"], binding["sha256"])
