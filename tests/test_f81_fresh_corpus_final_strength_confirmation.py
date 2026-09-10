"""Contract tests for the F81 fresh-corpus final confirmation harness."""

from pathlib import Path

from scripts import f81_fresh_corpus_final_strength_confirmation as f81


ROOT = Path(__file__).resolve().parents[1]


def test_f81_scope_and_fresh_corpus_contract():
    source = (ROOT / "scripts" / "f81_fresh_corpus_final_strength_confirmation.py").read_text(encoding="utf-8")
    assert f81.WORK_ORDER == "GENERICCHESS-F81-FRESH-CORPUS-FINAL-STRENGTH-CONFIRMATION"
    assert f81.BASELINE_SHA == "2513742e72258e9b6a20c5760c9f467de2b05891"
    assert f81.OPENING_SEED == 810501
    assert f81.OPENING_COUNT == 8
    assert f81.PAIRS == 8
    assert "generate_arena_openings" in source
    assert "F78_OPENINGS" in source
    assert "f78_results.json" not in source
    assert "_adam_fit" not in source
    assert "self-play" not in source.lower()
    assert "external engine" not in source.lower()


def test_f81_final_arena_configuration_and_cap_contract():
    source = (ROOT / "scripts" / "f81_fresh_corpus_final_strength_confirmation.py").read_text(encoding="utf-8")
    assert "workers=4" in source
    assert "max_concurrent_games=4" in source
    assert "per_game_nodes=262144" in source
    assert "per_game_plies=512" in source
    assert "max_stage_games=16" in source
    assert "if first.status == \"COMPLETE\":" in source
    assert "_validate_checkpointed_games" in source
    assert "no early" not in source.lower()


def test_f81_candidate_and_prior_evidence_are_fixed():
    source = (ROOT / "scripts" / "f81_fresh_corpus_final_strength_confirmation.py").read_text(encoding="utf-8")
    assert f81.PARENT_SHA == "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
    assert f81.CHILD_SHA == "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
    assert f81.CANDIDATE_MODEL_SHA == "b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6"
    assert f81.F80_EVIDENCE_SHA == "438ddec64d1225488900f3a823fa0fd8a52a9dd60942b39d1f9f32dcb3b0ead0"
    assert f81.F80_REPORT_SHA == "e992fb9f7804d48878b3eb71a309d95f3979f8b55a775ecded9e6bff6ffcfd4b"
    assert f81.F79_EVIDENCE_SHA == "888864459718cbc1d81cd0e4d1f9e3cae5e1eb116b9c3d05ca2f559e35fb9477"
    assert "_validate_prior_evidence" in source
    assert "champion_before" in source
    assert "champion_after" in source
