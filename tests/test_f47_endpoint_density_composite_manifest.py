"""H47A integrity tests for the frozen F47 endpoint-density protocol."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f47_endpoint_density_composite_manifest.json"


def _manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_h47a_is_hashed_pre_result_and_anchored_to_f46():
    data = _manifest()
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    assert hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == data["manifest_sha256"]
    assert data["baseline"]["sandbox_sha"] == "979c7e026442e9dbb479658d0a770daefd15da85"
    assert data["baseline"]["f46_sha"] == data["baseline"]["sandbox_sha"]
    assert "observed_result" not in data
    assert subprocess.run(["git", "merge-base", "--is-ancestor", data["baseline"]["sandbox_sha"], "HEAD"], cwd=ROOT).returncode == 0


def test_h47a_freezes_endpoint_definition_and_five_variants():
    data = _manifest()
    endpoint = data["endpoint_completion"]
    assert endpoint["attack_only"] == "target_enemy AND NOT target_empty"
    assert endpoint["split_attack_control_gap"] == "clear * (1 - density / 2) for attack-only candidates, zero otherwise"
    assert endpoint["completed_contribution"]["attack_only"].endswith("= clear")
    assert len(data["variants"]) == 5
    assert data["density_points"] == [0.0, 0.125, 0.25, 0.375, 0.5]
    assert data["density_weights"] == [0.25, 0.2, 0.2, 0.18, 0.17]


def test_h47a_freezes_gates_mapping_and_prohibitions():
    data = _manifest()
    assert len(data["structural_gates"]) == 16
    assert len(data["no_drift_gates"]) == 12
    assert len(data["classification_mapping"]) == 7
    assert data["tie_policy"].startswith("all seven selector paths")
    assert "production evaluator integration" in data["prohibited_operations"]
    assert "F48 execution" in data["prohibited_operations"]
