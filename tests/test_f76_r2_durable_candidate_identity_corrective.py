"""Contract tests for the F76-R2 durable candidate identity repair."""

import json
from pathlib import Path

from generic_chess.learning.nonlinear import CompactNonlinearResidual
from scripts import f76_r2_durable_candidate_identity_corrective as r2


ROOT = Path(__file__).resolve().parents[1]


def test_r2_scope_and_identity_repair_contract():
    source = (ROOT / "scripts" / "f76_r2_durable_candidate_identity_corrective.py").read_text(
        encoding="utf-8"
    )
    assert r2.WORK_ORDER == "GENERICCHESS-F76-R2-DURABLE-CANDIDATE-IDENTITY-CORRECTIVE"
    assert r2.PARENT_SHA == "0a77db47c59b6f792b035d1e08f5e915e385d208"
    assert r2.R1_ID == "140daa82ba60d5dee82a9212a679834f3c19919c43bf30704feb51c87fd1c324"
    assert r2.R1_ACTUAL_TRAINING_HASH == "ee3d16b950c0f20ac8b49d936dd567116fc4b9383f25ccd4896a6389ed167d43"
    assert r2.CANDIDATE_PATH != r2.R1_DESCRIPTOR
    assert "canonical_training_identity" in source
    assert "evaluator_equal = old_r1.compact_nonlinear == new_candidate.compact_nonlinear" in source
    assert "search_parity = _search_parity" in source
    assert "POINTWISE_OUTPUT_DELTA_DURABLE_IDENTITY_REPAIRED" in source


def test_previous_r1_descriptor_hash_is_distinct_from_actual_checkpoint_hash():
    payload = json.loads(r2.R1_DESCRIPTOR.read_text(encoding="utf-8"))
    assert payload["child_checkpoint_id"] == r2.R1_ID
    assert payload["training_config_hash"] != r2.R1_ACTUAL_TRAINING_HASH


def test_r2_artifact_is_separate_and_contains_canonical_identity():
    payload = json.loads(
        (ROOT / "artifacts" / "f76_r2_trusted_pointwise_q" / "candidate.json").read_text(
            encoding="utf-8"
        )
    )
    identity = payload["canonical_training_identity"]
    assert payload["source_commit"] == r2.PARENT_SHA
    assert identity["work_order"] == r2.WORK_ORDER
    assert identity["parent_checkpoint_id"] == r2.GEN1_ID
    assert identity["f62_stage_sha256"] == r2.F62_STAGE_SHA
    assert identity["f62_records_sha256"] == r2.F62_RECORDS_SHA
    assert len(identity["trusted_root_indices"]) == 34
    assert payload["canonical_training_config_hash"]
    assert payload["child_checkpoint_id"] != r2.R1_ID
    assert len(payload["final_output_weights"]) == 32


def test_r2_descriptor_round_trips_exact_checkpoint_and_r1_evaluator_payload():
    r2_payload = json.loads(
        (ROOT / "artifacts" / "f76_r2_trusted_pointwise_q" / "candidate.json").read_text(
            encoding="utf-8"
        )
    )
    r1_payload = json.loads(r2.R1_DESCRIPTOR.read_text(encoding="utf-8"))
    compiled, _native, _profile = r2.f59._ruleset(r2.LABEL)
    gen1 = r2.f76._load_gen1(compiled)
    model = CompactNonlinearResidual.from_dict({
        **gen1.compact_nonlinear,
        "output_weights": r2_payload["final_output_weights"],
    })
    assert model.to_dict() == {
        **gen1.compact_nonlinear,
        "output_weights": r1_payload["final_output_weights"],
    }
    assert r2.f76.stable_sha256(model.to_dict()) == r2_payload["candidate_model_sha256"]
    assert r2.f76.stable_sha256(r2_payload["canonical_training_identity"]) == r2_payload["canonical_training_config_hash"]
    rebuilt = r2._build_checkpoint(gen1, model, r2_payload["canonical_training_config_hash"])
    assert rebuilt.checkpoint_id == r2_payload["child_checkpoint_id"]
