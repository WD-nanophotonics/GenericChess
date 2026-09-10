"""Clean-checkout provenance and statistic reconstruction for F79-R2."""

import hashlib
import json
from pathlib import Path

from generic_chess.learning.statistics import bootstrap_pair_mean_ci
from scripts import f79_r1_incremental_frozen_arena4 as f79r1


ROOT = Path(__file__).resolve().parents[1]
F78 = ROOT / "artifacts" / "f78_parent_anchored_full_residual" / "arena2_strength_evidence.json"
F79 = ROOT / "artifacts" / "f79_parent_anchored_full_residual" / "arena4_strength_evidence.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_tracked_source_report_hashes_and_artifact_link_are_exact():
    f78 = json.loads(F78.read_text(encoding="utf-8"))
    f79 = json.loads(F79.read_text(encoding="utf-8"))
    assert f78["source_report_sha256"] == _sha(ROOT / f78["source_report_path"])
    assert f79["source_report_sha256"] == _sha(ROOT / f79["source_report_path"])
    assert f79["f78_evidence_sha256"] == _sha(ROOT / f79["f78_evidence_path"])
    assert f78["source_opening_indices"] == [0, 1]
    assert f79["prefix_source_opening_indices"] == [0, 1]
    assert f79["incremental_source_opening_indices"] == [2, 3]
    assert set(f79["prefix_source_opening_indices"]).isdisjoint(f79["incremental_source_opening_indices"])


def test_combined_arena4_statistics_are_recomputed_from_tracked_evidence():
    f78 = json.loads(F78.read_text(encoding="utf-8"))
    f79 = json.loads(F79.read_text(encoding="utf-8"))
    scores = f78["pair_scores"] + f79["incremental_pair_scores"]
    assert scores == f79["combined_pair_scores"]
    assert sum(scores) / len(scores) == f79["combined_mean_pair_score"]
    assert sum(score > 0.5 for score in scores) == f79["combined_child_better_pairs"]
    assert sum(score == 0.5 for score in scores) == f79["combined_tied_pairs"]
    assert sum(score < 0.5 for score in scores) == f79["combined_child_worse_pairs"]
    low, high = bootstrap_pair_mean_ci(scores)
    assert [low, high] == [f79["combined_bootstrap_low"], f79["combined_bootstrap_high"]]
    assert [f78["game_wins"] + f79["incremental_game_wins"], f78["game_draws"] + f79["incremental_game_draws"], f78["game_losses"] + f79["incremental_game_losses"]] == [f79["combined_game_wins"], f79["combined_game_draws"], f79["combined_game_losses"]]
    assert f79["combined_completed_games"] == 8
    assert f79["combined_completed_pairs"] == 4
    assert f79["classification"] == "PARENT_ANCHORED_FULL_RESIDUAL_ARENA4_SURVIVES"


def test_r1_clean_checkout_no_longer_depends_on_ignored_runtime_prefix():
    source = (ROOT / "scripts" / "f79_r1_incremental_frozen_arena4.py").read_text(encoding="utf-8")
    assert "F78_EVIDENCE" in source
    assert "F78_RESULT" not in source
    assert "f78_results.json" not in source
    assert "generic_chess_flow" in source
    assert not hasattr(f79r1, "F78_RESULT")
