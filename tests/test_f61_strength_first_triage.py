"""Static contracts for the F61 strength-first triage evidence."""

import json
from pathlib import Path


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


def test_f61_runner_has_conditional_four_pair_extension():
    source = (ROOT / "scripts" / "f61_strength_first_triage.py").read_text(encoding="utf-8")
    assert "first_decision_divergence" in source
    assert "not_clearly_bad_after_4_pairs" in source
    assert "catastrophic_4_pair_loss" in source
    assert "arena_extension_8_pairs" in source
    assert "arena_confirmation_32_pairs" in source
