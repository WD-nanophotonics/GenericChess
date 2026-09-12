from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from scripts.f94_r6_result_aggregate import (
    EXPECTED_RESULT_SHA256,
    PREP_PATH,
    _progress_directory,
    _telemetry_censoring,
    aggregate,
    _attribution,
)
from generic_chess.learning.serialization import stable_sha256


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / ".generic_chess_flow/f94-r6-layer-d-authority-refresh-result.json"
PROGRESS = ROOT / ".generic_chess_flow/f94-r6-progress"


def test_aggregate_is_deterministic_and_preserves_exact_sample():
    first = aggregate(RESULT, PROGRESS)
    second = aggregate(RESULT, PROGRESS)
    assert first == second
    assert first["source_result_sha256"] == EXPECTED_RESULT_SHA256
    assert first["source_result_path"] == ".generic_chess_flow/f94-r6-layer-d-authority-refresh-result.json"
    assert len(first["progress_evidence_sha256"]) == 64
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
    assert _attribution([0.49, 0.7, 0.8], 0.6)["descriptive_attribution"] == "NONMONOTONE"
    assert _attribution([0.6, 0.7, 0.8], 0.4)["descriptive_attribution"] == "UNDERPOWERED_OR_UNCERTAIN"
    assert _attribution([0.49, 0.7, 0.8], 0.4)["descriptive_attribution"] == "BOTH"
    assert _attribution([0.6, 0.7, 0.8], 0.6)["descriptive_attribution"] == "NONE"


def test_actual_western_matchup_is_descriptively_both():
    payload = aggregate(RESULT, PROGRESS)
    matchup = payload["controls"]["western_chess_qualification_control_v1"]["matchups"][1]
    assert matchup["classifier_output"] == "DEFER_NONMONOTONE_OR_UNCERTAIN"
    assert matchup["descriptive_attribution"] == {
        "any_tape_mean_le_half": True,
        "bootstrap_lower_le_half": True,
        "depth_censored": False,
        "horizon_censored": False,
        "descriptive_attribution": "BOTH",
        "authority": "descriptive_only",
    }


def test_aggregate_rejects_result_sha_mismatch(tmp_path: Path):
    tampered = tmp_path / "result.json"
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    payload["authority"] = "tampered"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="source SHA mismatch"):
        aggregate(tampered, PROGRESS)


def test_aggregate_fails_closed_when_progress_evidence_is_missing(tmp_path: Path):
    with pytest.raises(RuntimeError, match="missing or extra invocation directories"):
        aggregate(RESULT, tmp_path)


def test_progress_directory_rejects_wrong_identity_suffix(tmp_path: Path):
    wrong = tmp_path / "western_chess_qualification_control_v1-1024_vs_256-9801-deadbeefdeadbeef"
    wrong.mkdir()
    with pytest.raises(RuntimeError, match="directory identity mismatch"):
        _progress_directory(
            tmp_path, "western_chess_qualification_control_v1", "1024_vs_256", 9801,
            experiment="GENERICCHESS-F94-R6-LAYER-D-AUTHORITY-REFRESH-V1",
            protocol_source_sha="protocol", prep_fingerprint="prep",
        )


def test_progress_manifest_config_drift_fails_closed(tmp_path: Path, monkeypatch):
    import scripts.f94_r6_result_aggregate as aggregate_module

    source_dir = next(PROGRESS.glob("western_chess_qualification_control_v1-1024_vs_256-9801-*"))
    manifest = json.loads((source_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["identity"]["config"]["workers"] = 99
    manifest["identity_sha256"] = stable_sha256(manifest["identity"])
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(aggregate_module, "_progress_directory", lambda *args, **kwargs: tmp_path)
    source = json.loads(RESULT.read_text(encoding="utf-8"))
    prep = json.loads(PREP_PATH.read_text(encoding="utf-8"))
    tape = source["controls"]["western_chess_qualification_control_v1"]["matchups"][0]["tape_results"][0]
    with pytest.raises(RuntimeError, match="budget/telemetry mismatch"):
        _telemetry_censoring(
            tmp_path, "western_chess_qualification_control_v1", "1024_vs_256", [tape],
            result=source, prep=prep,
        )


@pytest.mark.parametrize("mutation, pattern", [
    (lambda payload: payload.update(schema="tampered"), "schema/identity mismatch"),
    (lambda payload: payload.update(identity_sha256="tampered"), "schema/identity mismatch"),
    (lambda payload: payload["game_child_owner0"].update(child_owner=1), "schema/identity mismatch"),
    (lambda payload: payload["game_child_owner0"].update(opening_position_key="tampered"), "schema/identity mismatch"),
])
def test_pair_checkpoint_integrity_is_fail_closed(tmp_path: Path, monkeypatch, mutation, pattern):
    import scripts.f94_r6_result_aggregate as aggregate_module

    source_dir = next(PROGRESS.glob("western_chess_qualification_control_v1-1024_vs_256-9801-*"))
    target = tmp_path / source_dir.name
    shutil.copytree(source_dir, target)
    pair_path = target / "pair-000000.json"
    payload = json.loads(pair_path.read_text(encoding="utf-8"))
    mutation(payload)
    pair_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(aggregate_module, "_progress_directory", lambda *args, **kwargs: target)
    source = json.loads(RESULT.read_text(encoding="utf-8"))
    prep = json.loads(PREP_PATH.read_text(encoding="utf-8"))
    tape = source["controls"]["western_chess_qualification_control_v1"]["matchups"][0]["tape_results"][0]
    with pytest.raises(RuntimeError, match=pattern):
        _telemetry_censoring(
            target, "western_chess_qualification_control_v1", "1024_vs_256", [tape],
            result=source, prep=prep,
        )
