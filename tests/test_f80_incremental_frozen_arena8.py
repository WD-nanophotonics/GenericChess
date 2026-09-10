"""Contract tests for the F80 remaining-opening Arena8 stage."""

import json
from pathlib import Path

from scripts import f80_incremental_frozen_arena8 as f80


ROOT = Path(__file__).resolve().parents[1]


def test_f80_scope_and_remaining_openings_contract():
    source = (ROOT / "scripts" / "f80_incremental_frozen_arena8.py").read_text(encoding="utf-8")
    assert f80.WORK_ORDER == "GENERICCHESS-F80-INCREMENTAL-FROZEN-ARENA8"
    assert f80.BASELINE_SHA == "afbc265c282c4fff091db959b931d6515a9662dc"
    assert f80.SOURCE_OPENING_INDICES == (4, 5, 6, 7)
    assert f80.PAIRS == 4
    assert f80.OPENING_COUNT == 4
    assert f80.NODES == 512
    assert f80.MAX_DEPTH == 12
    assert f80.TT_MEGABYTES == 8
    assert "generate_arena_openings" not in source
    assert "_adam_fit" not in source
    assert "self-play" not in source.lower()
    assert "external engine" not in source.lower()
    assert "early-stop" not in source.lower()


def test_f80_uses_durable_arena4_prefix_and_two_lanes():
    source = (ROOT / "scripts" / "f80_incremental_frozen_arena8.py").read_text(encoding="utf-8")
    prefix = json.loads(f80.F79_EVIDENCE.read_text(encoding="utf-8"))
    assert prefix["combined_pair_scores"] == [0.5, 1.0, 0.5, 0.5]
    assert prefix["classification"] == "PARENT_ANCHORED_FULL_RESIDUAL_ARENA4_SURVIVES"
    assert "workers=2" in source
    assert "max_concurrent_games=2" in source
    assert "effective game lanes did not equal two" in source
    assert 'stage_id="f80-incremental-arena8"' in source
    assert "max_stage_games=8" in source


def test_f80_has_no_candidate_or_opening_generation_outputs():
    source = (ROOT / "scripts" / "f80_incremental_frozen_arena8.py").read_text(encoding="utf-8")
    assert "candidate.json" not in source
    assert "openings.json" not in source
    assert "F78_OPENINGS" in source
    assert "local_to_source_index" in source
