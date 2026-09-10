"""Contract tests for the F79 frozen F78 candidate Arena4 harness."""

import json
from pathlib import Path

from generic_chess.learning.nonlinear import CompactNonlinearResidual
from scripts import f79_parent_anchored_full_residual_arena4 as f79


ROOT = Path(__file__).resolve().parents[1]


def test_f79_scope_is_frozen_and_does_not_retrain_or_generate():
    source = (ROOT / "scripts" / "f79_parent_anchored_full_residual_arena4.py").read_text(encoding="utf-8")
    assert f79.WORK_ORDER == "GENERICCHESS-F79-PARENT-ANCHORED-FULL-RESIDUAL-ARENA4"
    assert f79.BASELINE_SHA == "322121b5f987439d5606e93b7974067ad88b1a6c"
    assert f79.PARENT_SHA == "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
    assert f79.CHILD_SHA == "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
    assert "generate_arena_openings" not in source
    assert "_adam_fit" not in source
    assert "self-play" not in source.lower()
    assert "external engine" not in source.lower()
    assert "heavy" not in source.lower()


def test_f79_arena_contract_is_four_pairs_and_reproduces_f78_prefix():
    source = (ROOT / "scripts" / "f79_parent_anchored_full_residual_arena4.py").read_text(encoding="utf-8")
    assert f79.PAIRS == 4
    assert f79.OPENING_SEED == 780501
    assert f79.OPENING_COUNT == 8
    assert f79.F78_FIRST_TWO_PAIR_SCORES == [0.5, 1.0]
    assert f79.NODES == 512
    assert f79.MAX_DEPTH == 12
    assert f79.TT_MEGABYTES == 8
    assert "stage_id=\"f79-arena4\"" in source
    assert "max_stage_games=8" in source
    assert "capture_search_metrics=True" in source
    assert "root_window_pruning" in source


def test_f79_uses_only_the_f78_candidate_and_corpus():
    candidate = json.loads(f79.F78_CANDIDATE.read_text(encoding="utf-8"))
    openings = json.loads(f79.F78_OPENINGS.read_text(encoding="utf-8"))
    assert candidate["child_checkpoint_id"] == f79.CHILD_SHA
    assert candidate["candidate_model_sha256"] == f79.stable_sha256(candidate["final_compact_nonlinear"])
    assert len(CompactNonlinearResidual.from_dict(candidate["final_compact_nonlinear"]).hidden_weights) == 32
    assert openings["corpus_id"] == f79.CORPUS_ID
    assert openings["corpus"]["seed"] == f79.OPENING_SEED
    assert len(openings["corpus"]["openings"]) == f79.OPENING_COUNT
