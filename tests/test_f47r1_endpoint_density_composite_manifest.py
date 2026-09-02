"""H47R1A integrity tests for corrected F47 provenance and gate mechanics."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f47r1_endpoint_density_composite_manifest.json"


def test_h47r1a_hashes_all_accepted_stage_bindings_and_is_pre_result():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    assert hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == data["manifest_sha256"]
    assert "observed_result" not in data
    for binding in data["provenance_bindings"].values():
        assert (ROOT / binding["path"]).is_file()
        assert (ROOT / binding["protocol_path"]).is_file()
        assert hashlib.sha256((ROOT / binding["path"]).read_bytes()).hexdigest() == binding["sha256"]
        assert hashlib.sha256((ROOT / binding["protocol_path"]).read_bytes()).hexdigest() == binding["protocol_sha256"]


def test_h47r1a_preserves_frozen_formula_variants_and_mappings():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["endpoint_completion"]["attack_only"] == "target_enemy AND NOT target_empty"
    assert data["endpoint_completion"]["split_attack_control_gap"] == "clear * (1 - density / 2) for attack-only candidates, zero otherwise"
    assert len(data["variants"]) == 5
    assert data["density_points"] == [0.0, 0.125, 0.25, 0.375, 0.5]
    assert data["density_weights"] == [0.25, 0.2, 0.2, 0.18, 0.17]
    assert len(data["classification_mapping"]) == 7
    assert len(data["shogi_gates"]) == 4


def test_h47r1a_is_anchored_after_h47a_and_f47_candidate():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert subprocess.run(["git", "merge-base", "--is-ancestor", data["baseline"]["immediate_f47_sha"], "HEAD"], cwd=ROOT).returncode == 0
    assert subprocess.run(["git", "merge-base", "--is-ancestor", data["baseline"]["h47a_sha"], "HEAD"], cwd=ROOT).returncode == 0
