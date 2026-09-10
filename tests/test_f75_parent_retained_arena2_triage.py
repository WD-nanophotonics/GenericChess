"""Contract tests for the bounded F75 Arena2 triage harness."""

import json
from pathlib import Path

from scripts import f75_parent_retained_arena2_triage as f75


ROOT = Path(__file__).resolve().parents[1]


def test_f75_scope_and_bounded_arena_contract():
    source = (ROOT / "scripts" / "f75_parent_retained_arena2_triage.py").read_text(
        encoding="utf-8"
    )
    assert f75.WORK_ORDER == "GENERICCHESS-F75-PARENT-RETAINED-ARENA2-STRENGTH-TRIAGE"
    assert f75.PARENT_SHA == "ec8167a056bac3206a39809abc4a13343c0a838c"
    assert f75.GEN1_ID == "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
    assert f75.F74_CHILD_ID == "bafabe1a6eeedf30b0ebe34109e5c4efdad87fc434edf8e75e9030e958bca0bb"
    assert f75.OPENING_SEED == 750501
    assert f75.OPENING_COUNT == 8
    assert f75.PAIRS == 2
    assert f75.NODES == 512
    assert "run_arena_game_resumable" in source
    assert "capture_search_metrics=True" in source
    assert "root_window_pruning" in source
    assert "selfplay" not in source.lower()
    assert "external engine" not in source.lower()
    assert "heavy" not in source.lower()


def test_durable_candidate_descriptor_contains_only_registered_payload():
    payload = json.loads(
        (ROOT / "artifacts" / "f75_parent_retained_arena" / "candidate.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(payload) == {
        "schema", "source_commit", "parent_checkpoint_id", "child_checkpoint_id",
        "alpha", "raw_delta", "final_output_weights", "training_config_hash",
        "frozen_model_identity", "candidate_model_sha256",
    }
    assert payload["parent_checkpoint_id"] == f75.GEN1_ID
    assert payload["child_checkpoint_id"] == f75.F74_CHILD_ID
    assert payload["source_commit"] == f75.F74_SOURCE_SHA
    assert payload["alpha"] == 1.0
    assert len(payload["raw_delta"]) == 32
    assert len(payload["final_output_weights"]) == 32


def test_durable_opening_corpus_is_unique_and_disjoint_from_f62_roots():
    payload = json.loads(
        (ROOT / "artifacts" / "f75_parent_retained_arena" / "openings.json").read_text(
            encoding="utf-8"
        )
    )
    openings = payload["corpus"]["openings"]
    final_keys = [opening["final_position_key"] for opening in openings]
    assert payload["corpus_id"] == "b4fa3ed5cfcc8432fb5f7fde8e003b1a801f10f6e91093463c99df1ed9204ad1"
    assert payload["corpus"]["seed"] == f75.OPENING_SEED
    assert len(openings) == f75.OPENING_COUNT
    assert len(set(final_keys)) == f75.OPENING_COUNT
    assert payload["f62_overlap_count"] == 0
