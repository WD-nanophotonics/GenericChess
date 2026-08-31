import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "tests" / "fixtures" / "f33r1_retention_gate_results.json"
H33A_MANIFEST = ROOT / "tests" / "fixtures" / "f33_check_discovery_manifest.json"
H33A_RESULT = ROOT / "tests" / "fixtures" / "f33_check_discovery_audit.json"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_f33r1_repeated_retention_gate_contract():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "PASS"
    assert result["production_changed"] is False
    assert result["retained_candidate"] == "NONE"
    assert result["next_boundary"] == "F34_QUIESCENCE_BUDGET_ARCHITECTURE"
    assert result["h33a_manifest_sha256"] == "14de91028470b9bf4d3a8933a73912fa1e0b2567fb70ca106e0a284d778378bf"
    assert result["h33a_result_sha256"] == "e65300346bb7be48bcf933a163d25f5700fe7c2b93efc5b577b491eee973f25c"
    assert json.loads(H33A_MANIFEST.read_text(encoding="utf-8"))["manifest_sha256"] == result["h33a_manifest_sha256"]
    assert _sha(H33A_RESULT) == result["h33a_result_sha256"]
    assert result["gates"]["candidate_b_repeated_fixed_node_performance_gate"] is True
    assert result["gates"]["candidate_a_repeated_fallback_performance_gate"] is False
    assert result["gates"]["candidate_b_structural_gate"] is True
    assert result["gates"]["candidate_b_complete_accessibility_gate"] is False
    for variant in ("BASELINE", "CANDIDATE_A_POST_PUSH_GAVE_CHECK", "CANDIDATE_B_SEMANTIC_PREVIEW"):
        for budget in ("512", "2048"):
            for row in result["matrix"]["fixed_node"][variant][budget].values():
                assert len(row["repetitions"]) == 3
                assert row["summary"]["parity_integrity"] is True
