"""H44A freezes the four structural-capability diagnosis families."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f44_structural_capability_manifest.json"
sys.path.insert(0, str(ROOT / "scripts"))

from repository_provenance import require_migrated_binding  # noqa: E402


def test_h44a_manifest_is_frozen_and_inputs_match():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    expected = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert expected == data["manifest_sha256"]
    assert data["baseline"]["f43_r1_sha"] == "7166a743911926156de75825cd02c7c622aaa172"
    assert list(data["families"]) == [
        "S44-A_ENDPOINT_CONTROL_SEMANTICS",
        "S44-B_CONDITIONAL_CAPABILITY_RESERVE",
        "S44-C_CHANNEL_DIVERSITY_CONCENTRATION",
        "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY",
    ]
    assert all(data["constraints"].values())
    for name, binding in data["input_files"].items():
        require_migrated_binding(ROOT, "F44", "tests/fixtures/f44_structural_capability_manifest.json", name, data["baseline"]["f43_r1_sha"], binding["path"], binding["sha256"])


def test_h44a_freezes_independence_gates_and_boundary_mapping():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert set(data["independence_predicates"]) == {
        "A_matched_synthetic_collision",
        "B_executable_information_discarded",
        "correlation_only_is_insufficient",
        "western_only_correlation_is_insufficient",
    }
    assert set(data["classification_mapping"]) == {
        "ENDPOINT_CONTROL_INFORMATION_MISSING",
        "CONDITIONAL_CAPABILITY_INFORMATION_MISSING",
        "CHANNEL_DIVERSITY_INFORMATION_MISSING",
        "DENSITY_PROFILE_INFORMATION_MISSING",
        "MULTIPLE_STRUCTURAL_INFORMATION_GAPS",
        "CROSS_RULESET_STRUCTURAL_CONFLICT",
        "STRUCTURAL_DIAGNOSIS_INSUFFICIENT",
    }
