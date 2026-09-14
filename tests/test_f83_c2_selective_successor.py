import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_selective_successor_descriptor_is_self_consistent():
    descriptor_path = ROOT / "artifacts/f83_c2_selective_successor/successor_candidate_descriptor.json"
    result_path = ROOT / "artifacts/f83_c2_selective_successor/successor_candidate_result.json"
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(json.dumps({k: v for k, v in descriptor.items() if k != "descriptor_sha256"}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert digest == descriptor["descriptor_sha256"]
    assert result["candidate_descriptor_sha256"] == descriptor["descriptor_sha256"]
    assert result["status"] == "SUCCESSOR_READY_FOR_APPROVED_ARENA"
    assert result["selection"]["preserved_decisions_and_margins"] is True
    assert result["selection"]["preserved_root_count"] == 24
    assert result["selection"]["corrected_root_count"] == 12


def test_selective_successor_is_parent_anchored_and_teacher_bound():
    result = json.loads((ROOT / "artifacts/f83_c2_selective_successor/successor_candidate_result.json").read_text(encoding="utf-8"))
    assert result["parent_checkpoint_id"] == "86f026ef85d60e600bc1bd6bc7b7285f11e5ce7e6528911b2ea361a489dc5983"
    assert result["parent_model_sha256"] == "b2308bea76ba55a533b95036f9b0ca37265c15d772ce5fbd14f7b6b098677e95"
    assert result["teacher_evidence_sha256"] == "c0a5e69f5d3345bbf4ab699d67b14b0fcbad745003ca17ac5beec3a1f4fbb4c2"
