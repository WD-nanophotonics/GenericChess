from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.f94_r6_result_aggregate import (
    EXPECTED_RESULT_SHA256,
    aggregate,
    _attribution,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / ".generic_chess_flow/f94-r6-layer-d-authority-refresh-result.json"
PROGRESS = ROOT / ".generic_chess_flow/f94-r6-progress"


def test_aggregate_is_deterministic_and_preserves_exact_sample():
    first = aggregate(RESULT, PROGRESS)
    second = aggregate(RESULT, PROGRESS)
    assert first == second
    assert first["source_result_sha256"] == EXPECTED_RESULT_SHA256
    assert first["derived_compute"] == {
        "arena_invocations": 18,
        "arena_pairs": 108,
        "arena_games": 216,
        "action_traces": 216,
    }
    assert sum(
        len(matchup["pair_scores"])
        for control in first["controls"].values()
        for matchup in control["matchups"]
    ) == 108
    for control in first["controls"].values():
        assert len(control["matchups"]) == 3
        for matchup in control["matchups"]:
            assert len(matchup["pair_scores"]) == 18
            assert all(
                tape["recomputed_mean_pair_score"] == pytest.approx(tape["mean_pair_score"])
                for tape in matchup["tape_summaries"]
            )
            assert set(matchup["bootstrap"]) >= {"mean", "lower", "upper", "seed", "resamples", "sample_count"}


def test_aggregate_censoring_counts_are_descriptive_runtime_evidence():
    payload = aggregate(RESULT, PROGRESS)
    for control in payload["controls"].values():
        for matchup in control["matchups"]:
            depth = matchup["censoring"]
            assert depth["hits"] >= 0
            assert depth["count"] > 0
            assert depth["fraction"] == pytest.approx(depth["hits"] / depth["count"])
            horizon = depth["strongest_vs_weakest_horizon"]
            if matchup["name"] == "4096_vs_256":
                assert horizon["games"] == 36
            else:
                assert horizon == {"hits": 0, "games": 0, "fraction": 0.0}


def test_descriptive_attribution_never_changes_classifier():
    assert _attribution([0.49, 0.7, 0.8], 0.4)["descriptive_attribution"] == "NONMONOTONE"
    assert _attribution([0.6, 0.7, 0.8], 0.4)["descriptive_attribution"] == "UNDERPOWERED_OR_UNCERTAIN"
    assert _attribution([0.6, 0.7, 0.8], 0.6)["descriptive_attribution"] == "NONE"


def test_aggregate_rejects_result_sha_mismatch(tmp_path: Path):
    tampered = tmp_path / "result.json"
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    payload["authority"] = "tampered"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="source SHA mismatch"):
        aggregate(tampered, PROGRESS)
