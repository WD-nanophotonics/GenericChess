"""Contract tests for the F80-R1 extended-cap Arena8 rerun."""

from pathlib import Path

from scripts import f80_r1_extended_ply_frozen_arena8 as f80r1


ROOT = Path(__file__).resolve().parents[1]


def test_f80_r1_scope_and_extended_caps():
    source = (ROOT / "scripts" / "f80_r1_extended_ply_frozen_arena8.py").read_text(encoding="utf-8")
    assert f80r1.WORK_ORDER == "GENERICCHESS-F80-R1-EXTENDED-PLY-FROZEN-ARENA8"
    assert f80r1.BASELINE_SHA == "f4fc8411079e25fe1cfeab1c9be79535881e4274"
    assert f80r1.SOURCE_OPENING_INDICES == (4, 5, 6, 7)
    assert f80r1.NODES == 512
    assert "per_game_plies=512" in source
    assert "per_game_nodes=262144" in source
    assert "workers=2" in source
    assert "max_concurrent_games=2" in source
    assert "generate_arena_openings" not in source
    assert "_normalize_existing_cap_result" not in source
    assert "early-stop" not in source.lower()
    assert "self-play" not in source.lower()


def test_incomplete_path_validates_checkpoints_without_second_mutating_runner():
    source = (ROOT / "scripts" / "f80_r1_extended_ply_frozen_arena8.py").read_text(encoding="utf-8")
    assert source.count("run_arena_game_resumable(") == 2
    assert 'if first.status == "COMPLETE":' in source
    assert "_validate_checkpointed_games" in source
    assert "checkpoint_validation" in source


def test_f80_r1_consumes_durable_arena4_prefix_only():
    source = (ROOT / "scripts" / "f80_r1_extended_ply_frozen_arena8.py").read_text(encoding="utf-8")
    assert "arena4_strength_evidence.json" in source
    assert "888864459718cbc1d81cd0e4d1f9e3cae5e1eb116b9c3d05ca2f559e35fb9477" in source
    assert "f80-incremental-frozen-arena8" not in source
    assert "local_to_source_index" in source
