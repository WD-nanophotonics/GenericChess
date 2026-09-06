"""Static contracts for the F61 strength-first triage evidence."""

import json
from pathlib import Path

from generic_chess.learning.serialization import stable_sha256
from scripts import f61_r2_fresh_strength as r2


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / ".generic_chess_flow" / "f61-strength-first-triage" / "f61_results.json"
MODELS = ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json"


def test_f61_result_records_behavioral_gate_and_first_divergence():
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    assert payload["teacher_metrics_are_diagnostic_only"] is True
    assert payload["arena_gate"] == "actual_parent_child_behavior_only"
    assert payload["best_candidate_id"] == "F60_D2_MEDIAN_DEVELOPMENT_SEED"
    for candidate in payload["candidates"]:
        validation = candidate["search_validation"]
        first = validation.get("first_decision_divergence")
        if first is None:
            first = next(
                (row for row in validation["rows"] if row["decision_changed"]),
                None,
            )
        if validation["decision_changes"]:
            assert first is not None
            assert first["decision_changed"] is True


def test_f61_model_artifact_preserves_exact_candidate_parameters():
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    models = json.loads(MODELS.read_text(encoding="utf-8"))
    assert models["f60_result_sha256"] == payload["f60_result_sha256"]
    assert {row["candidate_id"] for row in models["candidates"]} == {
        row["candidate_id"] for row in payload["candidates"]
    }
    for row in models["candidates"]:
        source = next(c for c in payload["candidates"] if c["candidate_id"] == row["candidate_id"])
        assert row["model_sha256"] == source["model_sha256"]
        assert row["model"] == source["model"]
        assert row["perspective"] == "owner0"
        assert row["old_model_sha256"] == stable_sha256(row["model"])
        assert row["old_checkpoint_id"] == row["checkpoint_id"]


def test_f61_corrected_durable_models_have_reconstructed_identities():
    models = json.loads(MODELS.read_text(encoding="utf-8"))
    parent = r2.f59._parent(r2.f59.LABELS[1])
    assert models["schema"] == "generic-chess-f61-model-params-v2"
    assert parent.checkpoint_id == models["parent_checkpoint_id"]
    for row in models["corrected_candidates"]:
        checkpoint = r2._candidate_checkpoint(parent, row)
        assert row["perspective"] == "successor_root_q"
        assert row["model"]["perspective"] == "successor_root_q"
        assert row["corrected_model_sha256"] == stable_sha256(row["model"])
        assert row["model_sha256"] == row["corrected_model_sha256"]
        assert row["checkpoint_id"] == row["corrected_checkpoint_id"]
        assert checkpoint.checkpoint_id == row["corrected_checkpoint_id"]
        assert checkpoint.checkpoint_id == r2.EXPECTED_CORRECTED_IDS[row["candidate_id"]]

    d0 = next(
        row for row in models["corrected_candidates"]
        if row["candidate_id"] == "F60_D0_PAIRWISE_SEED_59012"
    )
    assert d0["corrected_checkpoint_id"] == (
        "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
    )


def test_f61_runner_has_conditional_four_pair_extension():
    source = (ROOT / "scripts" / "f61_strength_first_triage.py").read_text(encoding="utf-8")
    assert "first_decision_divergence" in source
    assert "not_clearly_bad_after_4_pairs" in source
    assert "catastrophic_4_pair_loss" in source
    assert "arena_extension_8_pairs" in source
    assert "arena_confirmation_32_pairs" in source
