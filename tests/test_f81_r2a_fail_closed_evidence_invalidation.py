"""Contract tests for F81-R2A canonical evidence invalidation."""

from pathlib import Path

from scripts import f81_r2a_fail_closed_evidence_invalidation as f81r2a


ROOT = Path(__file__).resolve().parents[1]


def test_f81_r2a_is_zero_compute_and_fail_closed():
    source = (ROOT / "scripts" / "f81_r2a_fail_closed_evidence_invalidation.py").read_text(encoding="utf-8")
    assert f81r2a.WORK_ORDER == "GENERICCHESS-F81-R2A-FAIL-CLOSED-EVIDENCE-INVALIDATION"
    assert "run_arena" not in source
    assert "heavy" not in source.lower()
    assert "PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMATION_UNRESOLVED" in source
    assert "INVALIDATED_BY_TIME_BUDGET_CAP_CONTRACT_MISMATCH" in source


def test_f81_r2a_binds_clean_pairs_and_gen1_authority():
    source = (ROOT / "scripts" / "f81_r2a_fail_closed_evidence_invalidation.py").read_text(encoding="utf-8")
    assert "retained_clean_pair_indices" in source
    assert "pending_rerun_pair_indices" in source
    assert "retained_clean_game_count" in source
    assert "champion_after" in source
    assert f81r2a.PARENT_SHA in source
