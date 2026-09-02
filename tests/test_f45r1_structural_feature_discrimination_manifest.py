"""H45R1A integrity tests; this protocol is published before corrective code."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f45r1_structural_feature_discrimination_manifest.json"


def test_h45r1a_manifest_is_frozen_without_an_expected_observed_result():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    expected = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert expected == data["manifest_sha256"]
    assert data["baseline"]["scientific_f45_sha"] == "1f4fc5f1dc12675e6bafcf1992245441d36104f5"
    assert data["baseline"]["first_pass_f45_sha"] == "e6c90819388cb056ad669b246ed22b209484c46e"
    assert "DENSITY_PROFILE_FEATURE_PRIMARY" in data["classification_mapping"]
    assert "observed_result" not in data
    assert data["prohibited_operations"][0] == "freeze observed classification as expected result"
    assert data["families"]["surviving"] == [
        "S44-A_ENDPOINT_CONTROL_SEMANTICS",
        "S44-B_CONDITIONAL_CAPABILITY_RESERVE",
        "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY",
    ]


def test_h45r1a_freezes_derivation_algorithms_and_all_mappings():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert set(data["placement_predicates"]) == {
        "STATIC_MATERIAL_ADMISSIBLE",
        "DYNAMIC_EVALUATOR_ADMISSIBLE",
        "ALREADY_EQUIVALENTLY_CONSUMED",
        "DIAGNOSTIC_ONLY_NOT_ADMISSIBLE",
        "UNRESOLVED",
    }
    assert data["minimum_subset_algorithm"]["tie"].startswith("unresolved")
    assert data["minimum_subset_algorithm"]["no_numeric_fit"] is True
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


def test_h45r1a_is_an_ancestor_of_corrective_execution():
    assert subprocess.run(["git", "merge-base", "--is-ancestor", "8940031", "HEAD"], cwd=ROOT).returncode == 0
    parent = subprocess.check_output(["git", "show", "-s", "--format=%P", "8940031"], cwd=ROOT, text=True).strip()
    assert parent.startswith("e6c90819388cb056ad669b246ed22b209484c46e")
