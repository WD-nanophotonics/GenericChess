import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_first_antecedent_successor_is_hash_bound_and_changes_behavior():
    descriptor = json.loads((ROOT / "artifacts/f83_c3_first_antecedent_successor/successor_candidate_descriptor.json").read_text(encoding="utf-8"))
    result = json.loads((ROOT / "artifacts/f83_c3_first_antecedent_successor/successor_candidate_result.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(json.dumps({k: v for k, v in descriptor.items() if k != "descriptor_sha256"}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert digest == descriptor["descriptor_sha256"]
    assert result["candidate_descriptor_sha256"] == descriptor["descriptor_sha256"]
    assert result["status"] == "SUCCESSOR_READY_FOR_APPROVED_ARENA"
    assert result["antecedent_root_id"] == "c1_on_policy-a-01"
    assert result["parent_top_key"] != result["target_action_key"]
    assert result["selection"]["behavior_changed"] is True
