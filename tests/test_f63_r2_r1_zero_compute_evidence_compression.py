"""Contracts for the F63-R2-R1 evidence-only compression pass."""

import inspect

from scripts import f63_r2_r1_zero_compute_evidence_compression as compression


def test_evidence_pass_is_bound_to_the_current_work_order_and_parent():
    assert compression.SEEDS == (59011, 59012, 59013)
    assert compression.RESULT_PATH.name == "evidence_compression.json"
    assert compression.REPORT_PATH.name.endswith("ZERO_COMPUTE_CLOSEOUT.md")


def test_action_identity_is_canonical_and_reproducible():
    action = {"to": [4, 7], "from": [3, 8], "actor_type_id": "G"}
    assert compression._action_key(action) == (
        '{"actor_type_id":"G","from":[3,8],"to":[4,7]}'
    )
    assert compression._action_key(action) == compression._action_key(
        {"actor_type_id": "G", "to": [4, 7], "from": [3, 8]}
    )


def test_fingerprint_path_does_not_start_search_or_arena_work():
    source = inspect.getsource(compression._fingerprint)
    assert "_root_search" not in source
    assert "run_arena" not in source
    assert "_load_f62_training_summary" in source
