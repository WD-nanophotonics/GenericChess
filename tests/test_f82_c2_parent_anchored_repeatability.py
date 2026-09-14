"""Contract tests for the pre-registered F82 C2 repeatability harness."""

import json
from pathlib import Path

from scripts import f82_c2_parent_anchored_repeatability as c2


ROOT = Path(__file__).resolve().parents[1]
ALLOCATION = ROOT / "artifacts/f82_c2_repeatability/c2_allocation_manifest.json"


def test_c2_allocation_is_frozen_and_disjoint():
    payload = json.loads(ALLOCATION.read_text(encoding="utf-8"))
    assert payload["status"] == "PRE_REGISTERED_AWAITING_COMPUTE_APPROVAL"
    assert payload["parent"]["checkpoint_id"] == c2.PARENT_CHECKPOINT_ID
    assert payload["parent"]["model_sha256"] == c2.PARENT_MODEL_SHA
    assert payload["training"]["root_count"] == 36
    assert payload["training"]["sealed_history_excluded"] is True
    corpora = payload["selection_and_strength_corpora"]
    assert [corpora[name]["pairs"] for name in ("Arena2", "Arena4", "Arena8", "fresh_final_confirmation")] == [2, 4, 8, 8]
    keys = [key for item in corpora.values() for key in item["final_position_keys"]]
    assert len(keys) == len(set(keys)) == 22
    assert not set(keys) & set(payload["training"]["root_position_keys"])


def test_c2_protocol_and_resource_envelope_are_explicit():
    payload = json.loads(ALLOCATION.read_text(encoding="utf-8"))
    optimizer = payload["optimizer"]
    assert optimizer["family"] == "PARENT_ANCHORED_FULL_RESIDUAL"
    assert optimizer["optimizer"] == "Adam"
    assert optimizer["batching"] == "full_batch"
    assert optimizer["steps"] == 100
    assert optimizer["learning_rate"] == 0.001
    assert optimizer["proximal_coefficient"] == 0.001
    assert optimizer["parent_anchoring"] is True
    assert optimizer["one_candidate"] is True
    assert optimizer["allowed_trainable_fields"] == ["hidden_weights", "hidden_bias", "output_weights"]
    envelope = payload["resource_envelope"]
    assert envelope["total_arena_games"] == 44
    assert envelope["max_concurrent_games"] == 1
    assert envelope["logical_cpu_count"] == 4
    assert envelope["per_game_nodes"] == 262144
    assert envelope["per_game_plies"] == 512
    assert envelope["stage_wall_seconds"] == 3600


def test_prep_does_not_start_arena_or_admit_sealed_corpora():
    source = (ROOT / "scripts/f82_c2_parent_anchored_repeatability.py").read_text(encoding="utf-8")
    assert "--precompute-only" in source
    assert "first_safe_alpha_only" in source
    assert "sealed_corpora_are_diagnostic_only" in source
    assert "F62" in source and "F75" in source
    assert "run_fit_and_write_result" in source
