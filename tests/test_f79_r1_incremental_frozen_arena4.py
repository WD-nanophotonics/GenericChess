"""Contract tests for the reduced F79-R1 frozen incremental Arena4 stage."""

import json
from pathlib import Path

from scripts import f79_r1_incremental_frozen_arena4 as f79r1


ROOT = Path(__file__).resolve().parents[1]


def test_f79_r1_scope_and_reduced_budget():
    source = (ROOT / "scripts" / "f79_r1_incremental_frozen_arena4.py").read_text(encoding="utf-8")
    assert f79r1.WORK_ORDER == "GENERICCHESS-F79-R1-INCREMENTAL-FROZEN-ARENA4"
    assert f79r1.BASELINE_SHA == "b40be3aad27c157877dbffaa7d7b2c5e50fa2c82"
    assert f79r1.SOURCE_OPENING_INDICES == (2, 3)
    assert f79r1.PAIRS == 2
    assert f79r1.OPENING_COUNT == 2
    assert f79r1.NODES == 512
    assert f79r1.MAX_DEPTH == 12
    assert f79r1.TT_MEGABYTES == 8
    assert "generate_arena_openings" not in source
    assert "_adam_fit" not in source
    assert "self-play" not in source.lower()
    assert "external engine" not in source.lower()
    assert "heavy" not in source.lower()


def test_f79_r1_reuses_the_audited_f78_prefix_and_frozen_corpus():
    payload = json.loads(f79r1.F78_RESULT.read_text(encoding="utf-8"))
    assert payload["arena"]["summary"]["pair_scores"] == [0.5, 1.0]
    openings = json.loads(f79r1.F78_OPENINGS.read_text(encoding="utf-8"))
    assert openings["corpus_id"] == "2923f457e56454520f89c682614b3b10d07da974f03040bfc6c3a831ab41da48"
    assert len(openings["corpus"]["openings"]) == 8
    assert "source_opening_indices" in (ROOT / "scripts" / "f79_r1_incremental_frozen_arena4.py").read_text(encoding="utf-8")


def test_f79_r1_has_no_candidate_or_opening_outputs():
    source = (ROOT / "scripts" / "f79_r1_incremental_frozen_arena4.py").read_text(encoding="utf-8")
    assert "candidate.json" not in source
    assert "generate_arena_openings" not in source
    assert 'stage_id="f79-r1-incremental-arena4"' in source
    assert "max_stage_games=4" in source
    assert "max_concurrent_games=1" in source
