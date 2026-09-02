"""H45A integrity tests for the F45 discrimination boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f45_structural_feature_discrimination_manifest.json"


def test_h45a_manifest_is_frozen_and_self_consistent():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    expected = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert expected == data["manifest_sha256"]
    assert data["baseline"]["f44_sha"] == "1f4fc5f1dc12675e6bafcf1992245441d36104f5"
    assert data["families"]["surviving"] == [
        "S44-A_ENDPOINT_CONTROL_SEMANTICS",
        "S44-B_CONDITIONAL_CAPABILITY_RESERVE",
        "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY",
    ]
    assert data["families"]["negative_independence_control"] == "S44-C_CHANNEL_DIVERSITY_CONCENTRATION"
    assert all(data["prohibited_operations"])


def test_h45a_binds_f44_evidence_and_required_predicates():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert set(data["f44_evidence_bindings"]) == {"structural", "endpoint", "conditional", "channel_negative_control", "density", "synthetic", "selection"}
    assert set(data["consumer_placement_predicates"]) == {"endpoint", "conditional", "density"}
    assert set(data["residual_obligations"]) == {"R1_pawn_anchor", "R2_knight_vs_ray", "R3_cross_rule_consistency"}
    assert set(data["classification_mapping"]) == {
        "ENDPOINT_CONTROL_FEATURE_PRIMARY",
        "CONDITIONAL_CAPABILITY_FEATURE_PRIMARY",
        "DENSITY_PROFILE_FEATURE_PRIMARY",
        "ENDPOINT_DENSITY_COMPOSITE_REQUIRED",
        "STATIC_DYNAMIC_STRUCTURAL_COMPOSITE_REQUIRED",
        "STRUCTURAL_INFORMATION_ALREADY_CONSUMED",
        "STRUCTURAL_FEATURE_DISCRIMINATION_INSUFFICIENT",
        "CROSS_RULESET_STRUCTURAL_CONFLICT",
    }
