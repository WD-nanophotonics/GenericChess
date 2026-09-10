"""Contract tests for the F81-R1 eight-lane final confirmation harness."""

from pathlib import Path

from scripts import f81_r1_eight_lane_final_strength_confirmation as f81r1


ROOT = Path(__file__).resolve().parents[1]


def test_f81_r1_uses_frozen_neutral_corpus_and_fixed_identity():
    source = (ROOT / "scripts" / "f81_r1_eight_lane_final_strength_confirmation.py").read_text(encoding="utf-8")
    assert f81r1.WORK_ORDER == "GENERICCHESS-F81-R1-EIGHT-LANE-FRESH-CORPUS-FINAL-CONFIRMATION"
    assert f81r1.BASELINE_SHA == "ef9a165ddebc8206e61327c196dc0baec2b9bd75"
    assert f81r1.CORPUS_ID == "67b9dafc51a618645c3328228c30a8744cc8f988395a7d54d382b65276dc935c"
    assert "generate_arena_openings" not in source
    assert "f81-fresh-corpus-final-strength-confirmation" not in source
    assert "candidate mutation" not in source.lower()
    assert "self-play" not in source.lower()
    assert "external engine" not in source.lower()


def test_f81_r1_uses_eight_lanes_and_preserves_caps():
    source = (ROOT / "scripts" / "f81_r1_eight_lane_final_strength_confirmation.py").read_text(encoding="utf-8")
    assert "workers=8" in source
    assert "max_concurrent_games=8" in source
    assert "per_game_nodes=262144" in source
    assert "per_game_plies=512" in source
    assert "max_stage_games=16" in source
    assert "if first.status == \"COMPLETE\":" in source
    assert "_validate_checkpointed_games" in source
    assert "ARTIFACT_PATH" in source


def test_f81_r1_prior_evidence_and_output_gate_are_fixed():
    source = (ROOT / "scripts" / "f81_r1_eight_lane_final_strength_confirmation.py").read_text(encoding="utf-8")
    assert f81r1.PARENT_SHA == "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
    assert f81r1.CHILD_SHA == "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
    assert f81r1.CANDIDATE_MODEL_SHA == "b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6"
    assert "final_strength_evidence.json" in source
    assert "champion_before" in source
    assert "champion_after" in source
