"""H42A freezes the F42 diagnosis protocol before alternatives run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f42_capability_prior_manifest.json"


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
    for binding in data["input_files"].values():
        actual_input = hashlib.sha256((ROOT / binding["path"]).read_bytes()).hexdigest()
        assert actual_input == binding["sha256"]

