"""H42A freezes the F42 diagnosis protocol before alternatives run."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f42_capability_prior_manifest.json"
sys.path.insert(0, str(ROOT / "scripts"))

from repository_provenance import require_migrated_binding  # noqa: E402


def test_h42a_manifest_is_frozen_and_inputs_match():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    actual = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert actual == data["manifest_sha256"]
    assert data["baseline"]["sandbox_sha"] == "fa9a9c334fce331a5059f05a3e261e1fd85fbc7c"
    assert data["work_order"] == "GENERICCHESS-F42-SEMANTIC-CAPABILITY-PRIOR-DIAGNOSIS"
    assert data["constraints"]["DIAGNOSIS_ONLY"] is True
    assert data["constraints"]["PRODUCTION_DIFF_ZERO"] is True
    assert len(data["diagnostic_variants"]) == 9
    assert len(data["synthetic_control_families"]) == 5
    for name, binding in data["input_files"].items():
        require_migrated_binding(ROOT, "F42", "tests/fixtures/f42_capability_prior_manifest.json", name, data["baseline"]["sandbox_sha"], binding["path"], binding["sha256"])
