"""Contract tests for the pre-registered F82 C2 repeatability harness."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

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


def test_materialized_candidate_descriptor_is_self_consistent():
    descriptor_path = ROOT / "artifacts/f82_c2_repeatability/c2_candidate_descriptor.json"
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    assert descriptor["candidate_checkpoint_id"] == "86f026ef85d60e600bc1bd6bc7b7285f11e5ce7e6528911b2ea361a489dc5983"
    assert descriptor["candidate_model_sha256"] == "b2308bea76ba55a533b95036f9b0ca37265c15d772ce5fbd14f7b6b098677e95"
    assert c2.stable_sha256({k: v for k, v in descriptor.items() if k != "descriptor_sha256"}) == descriptor["descriptor_sha256"]
    assert descriptor["candidate_checkpoint"]["compact_nonlinear"] == descriptor["compact_model"]


def test_materialization_mismatch_writes_nothing(tmp_path, monkeypatch):
    source = ROOT / "artifacts/f82_c2_repeatability/c2_candidate_result.json"
    artifact = tmp_path / source.name
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["candidate_model_sha256"] = "0" * 64
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    descriptor = tmp_path / "descriptor.json"
    monkeypatch.setattr(c2, "CANDIDATE_DESCRIPTOR", descriptor)
    allocation = json.loads(ALLOCATION.read_text(encoding="utf-8"))
    with pytest.raises(RuntimeError, match="candidate_model_sha256"):
        c2.materialize_candidate(allocation, artifact)
    assert not descriptor.exists()
    assert json.loads(artifact.read_text(encoding="utf-8"))["candidate_model_sha256"] == "0" * 64


def test_arena2_uses_only_registered_corpus_and_exact_caps(monkeypatch, tmp_path):
    allocation = json.loads(ALLOCATION.read_text(encoding="utf-8"))
    artifact = json.loads((ROOT / "artifacts/f82_c2_repeatability/c2_candidate_result.json").read_text(encoding="utf-8"))
    captured = {}

    def fake_runner(compiled, native, parent, candidate, config, **kwargs):
        captured.update(config=config, caps=kwargs["caps"], openings=kwargs["openings"], stage_id=kwargs["stage_id"], pause_requested=kwargs["pause_requested"])
        return SimpleNamespace(status="COMPLETE", completed_games=4, completed_pairs=2, total_games=4, reason=None)

    monkeypatch.setattr(c2, "run_arena_game_resumable", fake_runner)
    monkeypatch.setattr(c2, "ARENA2_RESULT_PATH", tmp_path / "arena2.json")
    monkeypatch.setattr(c2, "ARENA2_PROGRESS", tmp_path / "progress")
    result = c2.run_arena2(allocation, ROOT / "artifacts/f82_c2_repeatability/c2_candidate_result.json")
    assert result["status"] == "COMPLETE"
    assert captured["stage_id"] == "f82-c2-arena2"
    assert callable(captured.get("pause_requested"))
    assert captured["config"].pairs == 2
    assert captured["config"].nodes_per_move == 512
    assert captured["config"].max_depth == 12
    assert captured["caps"].per_game_nodes == 262144
    assert captured["caps"].per_game_plies == 512
    assert captured["caps"].per_game_wall_seconds == 7200
    assert captured["caps"].max_stage_games == 4
    assert captured["caps"].max_concurrent_games == 1
    assert captured["caps"].stage_wall_seconds == 7200
    assert captured["caps"].logical_cpu_count == 4
    assert len(captured["openings"].openings) == 2
    assert captured["openings"].corpus_id == allocation["selection_and_strength_corpora"]["Arena2"]["corpus_id"]
    assert artifact["candidate_descriptor_path"]
