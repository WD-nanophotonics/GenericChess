"""Static and smoke contracts for F62 Gen1 -> Gen2 repeatability."""

from pathlib import Path

import pytest

from generic_chess.native import native_available
from scripts import f59_action_spectrum_diagnosis as f59
from scripts import f62_learned_champion_repeatability as f62


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not native_available(), reason="native extension is not built")
def test_f62_durable_gen1_reconstructs_exact_accepted_champion():
    compiled, _native, _profile = f59._ruleset(f62.LABEL)
    gen1, row = f62._load_gen1(compiled)
    assert gen1.checkpoint_id == f62.GEN1_ID
    assert row["candidate_id"] == f62.GEN1_CANDIDATE
    assert row["perspective"] == "successor_root_q"


@pytest.mark.skipif(not native_available(), reason="native extension is not built")
def test_f62_fresh_sources_keep_groups_inside_frozen_splits():
    compiled, _native, _profile = f59._ruleset(f62.LABEL)
    records, provenance = f62._fresh_records(compiled, smoke=True)
    assert provenance["root_count"] == 3
    assert provenance["source_group_count"] == 3
    assert provenance["position_overlap_count"] == 0
    assert provenance["source_group_overlap_count"] == 0
    assert {record["source_split"] for record in records} == {
        "fit", "development", "final_holdout"
    }
    groups = {
        split: set(provenance["split_source_groups"][split])
        for split in ("fit", "development", "final_holdout")
    }
    assert not groups["fit"] & groups["development"]
    assert not groups["fit"] & groups["final_holdout"]
    assert not groups["development"] & groups["final_holdout"]


def test_f62_contract_freezes_one_mechanism_and_fresh_stage_seeds():
    source = (ROOT / "scripts" / "f62_learned_champion_repeatability.py").read_text(
        encoding="utf-8"
    )
    assert f62.TRAINING_SEED == 59012
    assert f62.ROOT_COUNT == 96
    assert f62.SOURCE_GROUP_COUNT * f62.ROOTS_PER_GROUP == f62.ROOT_COUNT
    assert f62.DATA_OPENING_SEED >= 630000
    assert f62.DATA_CORPUS_SEED >= 630000
    assert len({f62.DATA_OPENING_SEED, f62.DATA_CORPUS_SEED, f62.VALIDATION_SEED,
                *(seed for _pairs, seed in f62.ARENA_STAGES)}) == 6
    assert "teacher_metrics_are_diagnostic_only" in source
    assert "PAIRWISE_RANKING" in source
    assert "capture_search_metrics=True" in source
    assert "REPEATABLE_AUTONOMOUS_STRENGTH_IMPROVEMENT_SIGNAL" in source
    assert f62.WORK_ORDER_PARENT_SHA == (
        "750b0617f925cf7dd3c233330c18cd96327410a2"
    )
    assert set(f62._code_provenance()) >= {
        "scripts/f62_learned_champion_repeatability.py",
        "generic_chess/learning/arena.py",
        "docs/architecture/GENERICCHESS_F61_MODEL_PARAMS.json",
    }
