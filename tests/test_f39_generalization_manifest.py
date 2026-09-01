import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f39_generalization_manifest.json"


def test_f39_manifest_freezes_inputs_rules_and_production_scope():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload = {key: value for key, value in data.items() if key != "manifest_sha256"}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(canonical.encode()).hexdigest() == data["manifest_sha256"]
    assert data["kind"] == "F39_EVALUATOR_REENTRY_GENERALIZATION_DIAGNOSIS"
    assert data["rank_protocol"]["material_normalized_margin_delta"] == 0.01
    assert data["rank_protocol"]["material_deterministic_rank_delta"] == 3
    assert data["component_search_protocol"]["only_missing_counterfactuals"] == ["R37A", "R37B"]
    assert all(data["constraints"].values())
    for binding in data["inputs"].values():
        assert hashlib.sha256((ROOT / binding["path"]).read_bytes()).hexdigest() == binding["sha256"]
    assert subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode == 0
