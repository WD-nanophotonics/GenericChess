"""Contract tests for the zero-compute F82 adoption protocol."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADOPTION = ROOT / "artifacts" / "f82_champion_adoption" / "champion.json"
F78_CANDIDATE = ROOT / "artifacts" / "f78_parent_anchored_full_residual" / "candidate.json"
F78_OPENINGS = ROOT / "artifacts" / "f78_parent_anchored_full_residual" / "openings.json"
F75_OPENINGS = ROOT / "artifacts" / "f75_parent_retained_arena" / "openings.json"
F77_OPENINGS = ROOT / "artifacts" / "f77_trusted_pointwise_q_arena" / "openings.json"
F81_OPENINGS = ROOT / "artifacts" / "f81_final_confirmation" / "openings.json"
F81_EVIDENCE = ROOT / "artifacts" / "f81_final_confirmation" / "final_strength_evidence.json"
F81_BOUND = ROOT / "artifacts" / "f81_final_confirmation" / "final_decision_bound.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_f82_adopts_exact_c1_and_binds_f81_authority():
    adoption = json.loads(ADOPTION.read_text(encoding="utf-8"))
    candidate = json.loads(F78_CANDIDATE.read_text(encoding="utf-8"))
    evidence = json.loads(F81_EVIDENCE.read_text(encoding="utf-8"))

    assert adoption["status"] == "C1_CHAMPION_ADOPTED_REPEATABILITY_PROTOCOL_FROZEN"
    assert adoption["previous_champion"] == "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
    assert adoption["adopted_champion"] == candidate["child_checkpoint_id"] == "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
    assert adoption["model_sha256"] == candidate["candidate_model_sha256"] == "b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6"
    assert _sha(F78_CANDIDATE) == adoption["source_f78_candidate"]["content_sha256"]
    assert _sha(F81_EVIDENCE) == adoption["source_f81_canonical_evidence"]["content_sha256"]
    assert _sha(F81_BOUND) == adoption["source_f81_final_decision_bound"]["content_sha256"]
    assert evidence["classification"] == adoption["source_f81_canonical_evidence"]["classification"]
    assert evidence["confirmation_method"] == adoption["source_f81_canonical_evidence"]["confirmation_method"]


def test_f82_seals_history_and_freezes_one_candidate_protocol():
    adoption = json.loads(ADOPTION.read_text(encoding="utf-8"))
    corpora = adoption["sealed_historical_corpora"]
    paths = {entry.get("path"): entry for entry in corpora if entry.get("path")}

    assert paths[str(F78_OPENINGS.relative_to(ROOT)).replace("\\", "/")]["content_sha256"] == _sha(F78_OPENINGS)
    assert paths[str(F75_OPENINGS.relative_to(ROOT)).replace("\\", "/")]["content_sha256"] == _sha(F75_OPENINGS)
    assert paths[str(F77_OPENINGS.relative_to(ROOT)).replace("\\", "/")]["content_sha256"] == _sha(F77_OPENINGS)
    f81 = paths["artifacts/f81_final_confirmation/openings.json"]
    assert f81["content_sha256"] == _sha(F81_OPENINGS)
    assert f81["corpus_id"] == "67b9dafc51a618645c3328228c30a8744cc8f988395a7d54d382b65276dc935c"
    assert "final-evaluation history only" in f81["reuse"]
    assert "never C2 training or candidate selection" in f81["reuse"]
    f62 = next(entry for entry in corpora if entry["label"] == "F62 historical strength evidence")
    assert f62["f62_stage_identity_sha256"] == "e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70"
    assert f62["f62_records_sha256"] == "b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61"

    protocol = adoption["c2_protocol"]
    assert protocol["parent_checkpoint_id"] == adoption["adopted_champion"]
    assert protocol["mechanism_family"] == "PARENT_ANCHORED_FULL_RESIDUAL"
    assert protocol["frozen_fields"] == [
        "input_mean", "input_scale", "target_scale", "output_bias", "width",
        "hand_binding", "perspective", "ruleset_native_scale", "board_weights",
        "hand_weights", "dynamic_weights", "spatial_weights", "control_weights",
    ]
    assert protocol["allowed_trainable_fields"] == ["hidden_weights", "hidden_bias", "output_weights"]
    assert protocol["optimizer_family"] == {
        "optimizer": "Adam", "batching": "full_batch", "steps": 100,
        "learning_rate": 0.001, "proximal_coefficient": 0.001,
        "parent_anchoring": True, "backtracking_safety_sequence": "same_registered_F78_family",
    }
    assert protocol["one_candidate_rule"] is True
    assert protocol["strength_authority"] == ["bounded_correctness_safety", "Arena2", "Arena4", "Arena8", "fresh_final_confirmation"]
    assert ".generic_chess_flow" not in ADOPTION.read_text(encoding="utf-8")
