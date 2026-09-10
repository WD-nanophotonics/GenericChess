"""Contract tests for the F78 parent-anchored full-residual candidate."""

from pathlib import Path

import json

from generic_chess.learning.nonlinear import CompactNonlinearResidual
from scripts import f78_parent_anchored_full_residual_arena2 as f78


ROOT = Path(__file__).resolve().parents[1]


def test_f78_scope_and_fixed_optimizer_contract():
    source = (ROOT / "scripts" / "f78_parent_anchored_full_residual_arena2.py").read_text(
        encoding="utf-8"
    )
    assert f78.WORK_ORDER == "GENERICCHESS-F78-PARENT-ANCHORED-FULL-RESIDUAL-PAIRWISE-ARENA2"
    assert f78.PARENT_SHA == "f4424c7cb31f4487c8342dad6530fa72cd7ab769"
    assert f78.GEN1_ID == "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
    assert f78.TRUSTED_ROOT_COUNT == 34
    assert f78.ADAM_STEPS == 100
    assert f78.LEARNING_RATE == 0.001
    assert f78.PROXIMAL_COEFFICIENT == 0.001
    assert f78.BACKTRACKING_ALPHAS == (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625, 0.0078125)
    assert "replace(parent_model" in source
    assert "np.random" not in source
    assert "seed sweep" not in source.lower()
    assert "external engine" not in source.lower()
    assert "self-play" not in source.lower()
    assert "heavy" not in source.lower()


def test_f78_arena_contract_uses_new_corpus_and_exact_two_pairs():
    source = (ROOT / "scripts" / "f78_parent_anchored_full_residual_arena2.py").read_text(
        encoding="utf-8"
    )
    assert f78.OPENING_SEED == 780501
    assert f78.OPENING_COUNT == 8
    assert f78.PAIRS == 2
    assert f78.NODES == 512
    assert f78.MAX_DEPTH == 12
    assert f78.TT_MEGABYTES == 8
    assert "run_arena_game_resumable" in source
    assert "capture_search_metrics=True" in source
    assert "f75_overlap_count" in source
    assert "f77_overlap_count" in source
    assert "max_stage_games=4" in source


def test_f78_candidate_artifact_round_trips_checkpoint_identity():
    payload = json.loads(
        (ROOT / "artifacts" / "f78_parent_anchored_full_residual" / "candidate.json").read_text(
            encoding="utf-8"
        )
    )
    identity = payload["canonical_training_identity"]
    assert payload["source_commit"] == f78.PARENT_SHA
    assert payload["child_checkpoint_id"] == "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
    assert payload["training_config_hash"] == f78.stable_sha256(identity)
    assert len(payload["final_compact_nonlinear"]["hidden_weights"]) == 32
    assert len(payload["final_compact_nonlinear"]["hidden_bias"]) == 32
    assert len(payload["final_compact_nonlinear"]["output_weights"]) == 32
    compiled, _native, _profile = f78.f59._ruleset(f78.LABEL)
    gen1 = f78._load_gen1(compiled)
    model = CompactNonlinearResidual.from_dict(payload["final_compact_nonlinear"])
    assert f78.stable_sha256(model.to_dict()) == payload["candidate_model_sha256"]
    rebuilt = f78._make_candidate(gen1, model, identity)[0]
    assert rebuilt.checkpoint_id == payload["child_checkpoint_id"]


def test_f78_corpus_has_no_prior_arena_or_fit_overlap():
    payload = json.loads(
        (ROOT / "artifacts" / "f78_parent_anchored_full_residual" / "openings.json").read_text(
            encoding="utf-8"
        )
    )
    keys = [opening["final_position_key"] for opening in payload["corpus"]["openings"]]
    assert payload["corpus"]["seed"] == f78.OPENING_SEED
    assert len(set(keys)) == f78.OPENING_COUNT
    assert payload["f62_overlap_count"] == 0
    assert payload["f75_overlap_count"] == 0
    assert payload["f77_overlap_count"] == 0
