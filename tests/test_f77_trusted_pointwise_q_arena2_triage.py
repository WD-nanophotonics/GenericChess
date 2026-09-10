"""Contract tests for the F77 two-pair Arena2 triage."""

import json
from pathlib import Path

from scripts import f77_trusted_pointwise_q_arena2_triage as f77


ROOT = Path(__file__).resolve().parents[1]


def test_f77_scope_and_candidate_identity_contract():
    source = (ROOT / "scripts" / "f77_trusted_pointwise_q_arena2_triage.py").read_text(
        encoding="utf-8"
    )
    assert f77.WORK_ORDER == "GENERICCHESS-F77-TRUSTED-POINTWISE-Q-ARENA2-STRENGTH-TRIAGE"
    assert f77.PARENT_SHA == "2eac3d2ac36519dfaab2b2cd6a6112d9404b5c00"
    assert f77.GEN1_ID == "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
    assert f77.R2_ID == "fb3d3113b7044de6ebbf17352d7e34f0713618afbaae6eb792ebb515b09f30db"
    assert f77.OPENING_SEED == 770501
    assert f77.OPENING_COUNT == 8
    assert f77.PAIRS == 2
    assert f77.NODES == 512
    assert "run_arena_game_resumable" in source
    assert "generate_arena_openings" in source
    assert "capture_search_metrics=True" in source
    assert "root_window_pruning" in source
    assert "selfplay" not in source.lower()
    assert "external engine" not in source.lower()
    assert "heavy" not in source.lower()


def test_f77_uses_new_corpus_and_first_two_openings_only():
    source = (ROOT / "scripts" / "f77_trusted_pointwise_q_arena2_triage.py").read_text(
        encoding="utf-8"
    )
    assert f77.OPENINGS_PATH != f77.F75_OPENINGS
    assert "f75_overlap_count" in source
    assert "opening_count=OPENING_COUNT" in source
    assert "pairs=PAIRS" in source
    assert "max_stage_games=4" in source


def test_f77_r2_descriptor_is_durable_input():
    payload = json.loads(f77.R2_DESCRIPTOR.read_text(encoding="utf-8"))
    assert payload["child_checkpoint_id"] == f77.R2_ID
    assert payload["canonical_training_config_hash"]
    assert len(payload["final_output_weights"]) == 32


def test_f77_frozen_corpus_is_unique_and_disjoint_from_prior_corpora():
    payload = json.loads(
        (ROOT / "artifacts" / "f77_trusted_pointwise_q_arena" / "openings.json").read_text(
            encoding="utf-8"
        )
    )
    keys = [opening["final_position_key"] for opening in payload["corpus"]["openings"]]
    assert payload["corpus"]["seed"] == f77.OPENING_SEED
    assert len(keys) == f77.OPENING_COUNT
    assert len(set(keys)) == f77.OPENING_COUNT
    assert payload["f62_overlap_count"] == 0
    assert payload["f75_overlap_count"] == 0
