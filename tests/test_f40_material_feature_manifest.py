import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f40_material_feature_manifest.json"


def test_f40_manifest_freezes_sources_gates_and_production_scope():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload = {key: value for key, value in data.items() if key != "manifest_sha256"}
    assert hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == data["manifest_sha256"]
    assert data["kind"] == "F40_RULE_DERIVED_MATERIAL_AND_FEATURE_UTILIZATION_AUDIT"
    assert all(data["constraints"].values())
    assert data["shogi_reference"]["healthy_gates"] == {"cosine_min": 0.95, "spearman_min": 0.9, "pairwise_ordering_min": 0.9}
    assert len(data["boundary_mapping"]) == 5
    for binding in data["inputs"].values():
        assert hashlib.sha256((ROOT / binding["path"]).read_bytes()).hexdigest() == binding["sha256"]
    assert subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode == 0
