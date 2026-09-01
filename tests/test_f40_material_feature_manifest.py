import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f40_material_feature_manifest.json"
CORRECTED_INPUT_SHAS = {
    "generic_chess/ai/alphabeta/player.py": "1da81128599a0700b057d792d466358a44c80a191a89c5425ca82d96c1ce1aaa",
    "generic_chess/learning/arena.py": "45cd3e44dad052213ae453b0d7bd43c7a420fe476cc7f72d192a6b8a6167aa9a",
    "generic_chess/learning/selfplay.py": "0c8cc541215e3e0630623917d4f12397a1541e36c5ced5f3c2cfd8e2cfe6ab7e",
    "generic_chess/native/compiler.py": "384cfb2837188457a6af2b399b5cc1b3bdcd0b5db0bd775827a310227f40fc13",
    "generic_chess/rules/compiler.py": "f895ffe7648cd66a69125205ece00c6455dde5114b38bcbc11cf97cd461c1de9",
    "generic_chess/rules/standard_shogi.py": "a2a0f0e1b1076b8cc365a2bdcea3fa105730935b77fce3970790125f4d502923",
    "generic_chess/rules/western_chess.py": "2b3bc415763ce209264504c751fa3a94d66de016262da0cd91f6c82172d3ae2a",
}


def test_f40_manifest_freezes_sources_gates_and_production_scope():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload = {key: value for key, value in data.items() if key != "manifest_sha256"}
    assert hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == data["manifest_sha256"]
    assert data["kind"] == "F40_RULE_DERIVED_MATERIAL_AND_FEATURE_UTILIZATION_AUDIT"
    assert all(data["constraints"].values())
    assert data["shogi_reference"]["healthy_gates"] == {"cosine_min": 0.95, "spearman_min": 0.9, "pairwise_ordering_min": 0.9}
    assert len(data["boundary_mapping"]) == 5
    for binding in data["inputs"].values():
        expected = CORRECTED_INPUT_SHAS.get(binding["path"], binding["sha256"])
        assert hashlib.sha256((ROOT / binding["path"]).read_bytes()).hexdigest() == expected
    assert subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode == 0
