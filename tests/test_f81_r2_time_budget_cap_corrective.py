"""Contract tests for the F81-R2 audit and cap corrective."""

from pathlib import Path

from scripts import f81_r2_time_budget_cap_corrective as f81r2


ROOT = Path(__file__).resolve().parents[1]


def test_f81_r2_audit_is_zero_compute_and_fixed_scope():
    source = (ROOT / "scripts" / "f81_r2_time_budget_cap_corrective.py").read_text(encoding="utf-8")
    assert f81r2.WORK_ORDER == "GENERICCHESS-F81-R2-TIME-BUDGET-CAP-CORRECTIVE"
    assert f81r2.BASELINE_SHA == "55c7bbcccb21d78d0398e0deecbfd5301e059392"
    assert "run_arena_game_resumable" not in source
    assert "generate_arena_openings" not in source
    assert "CAP_LIKE_REASONS" in source
    assert "time_budget" in source


def test_f81_r2_audit_requires_all_frozen_games_and_tracks_provenance():
    source = (ROOT / "scripts" / "f81_r2_time_budget_cap_corrective.py").read_text(encoding="utf-8")
    assert "expected exactly sixteen F81-R1 game files" in source
    assert "progress_sha256" in source
    assert "contaminated_pair_indices" in source
    assert "root_window_pruning" in source
    assert "termination_reason_counts" in source
    assert "f81_r1_time_cap_audit.json" in source
