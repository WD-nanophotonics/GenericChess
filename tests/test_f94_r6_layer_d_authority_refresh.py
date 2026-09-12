from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts import f94_r6_layer_d_authority_refresh_executor as executor
from generic_chess.learning.arena import ArenaGameResult, ArenaPairResult
from scripts.f94_r6_layer_d_authority_refresh_prep import (
    BUDGET_LADDER,
    GAMES_PER_MATCHUP,
    INVOCATIONS_PER_CONTROL,
    MATCHUPS,
    PAIRS_PER_MATCHUP,
    PAIRS_PER_TAPE,
    TAPE_SEEDS,
    TOTAL_GAMES,
    TOTAL_INVOCATIONS,
    TOTAL_PAIRS,
    TOTAL_TRACES,
    TRACES_PER_MATCHUP,
    build_prep,
)


def test_exact_r6_accounting_and_fixed_ladder(tmp_path: Path):
    payload = build_prep(output=tmp_path / "prep.json")
    assert tuple(payload["budget_ladder"]) == BUDGET_LADDER == (256, 1024, 4096)
    assert len(payload["controls"]) == 2
    assert len(payload["matchups"]) == 3
    assert all(row["pairs_per_tape"] == PAIRS_PER_TAPE for row in payload["matchups"])
    assert all(row["pair_count"] == PAIRS_PER_MATCHUP for row in payload["matchups"])
    assert all(row["game_count"] == GAMES_PER_MATCHUP == TRACES_PER_MATCHUP for row in payload["matchups"])
    assert payload["budgets"]["invocations_per_control"] == INVOCATIONS_PER_CONTROL == 9
    assert payload["budgets"]["total_invocations"] == TOTAL_INVOCATIONS == 18
    assert payload["budgets"]["total_pairs"] == TOTAL_PAIRS == 108
    assert payload["budgets"]["total_games"] == TOTAL_GAMES == TOTAL_TRACES == 216
    assert tuple(payload["tape_seeds"]) == TAPE_SEEDS
    assert payload["fixed_sample_authority"] is True


def test_all_openings_are_prevalidated_before_runner(tmp_path: Path):
    payload = build_prep(output=tmp_path / "prep.json")
    broken = copy.deepcopy(payload)
    broken["controls"][1]["opening_corpora"][0]["openings"][0]["final_position_key"] = "tampered"
    with pytest.raises(RuntimeError, match="opening identity"):
        executor.validated_openings(broken)


def test_matchup_ci_and_tape_means_are_independent():
    scores = [0.75] * 18
    bootstrap = executor.percentile_bootstrap_mean(scores, seed=123, resamples=200)
    assert executor.classify_matchup(scores=scores, tape_means=[0.75, 0.76, 0.77], statuses=[], depth_fraction=0, horizon_fraction=0, bootstrap=bootstrap) == "PASS"
    assert executor.classify_matchup(scores=scores, tape_means=[0.75, 0.50, 0.77], statuses=[], depth_fraction=0, horizon_fraction=0, bootstrap=bootstrap) == "DEFER_NONMONOTONE_OR_UNCERTAIN"
    assert bootstrap["sample_count"] == 18


def test_adjacent_budget_nonmonotone_defers():
    scores = [0.7] * 18
    bootstrap = executor.percentile_bootstrap_mean(scores, seed=456, resamples=200)
    assert executor.classify_matchup(scores=scores, tape_means=[0.7, 0.7, 0.7], statuses=[], depth_fraction=0, horizon_fraction=0, bootstrap=bootstrap) == "PASS"
    low = executor.percentile_bootstrap_mean([0.45] * 18, seed=457, resamples=200)
    assert executor.classify_matchup(scores=[0.45] * 18, tape_means=[0.45, 0.45, 0.45], statuses=[], depth_fraction=0, horizon_fraction=0, bootstrap=low) == "DEFER_NONMONOTONE_OR_UNCERTAIN"


def test_depth_and_horizon_boundaries_are_censored():
    bootstrap = executor.percentile_bootstrap_mean([0.8] * 18, seed=1, resamples=100)
    kwargs = dict(scores=[0.8] * 18, tape_means=[0.8, 0.8, 0.8], statuses=[], bootstrap=bootstrap)
    assert executor.classify_matchup(**kwargs, depth_fraction=0.5, horizon_fraction=0) == "DEFER_DEPTH_CENSORED"
    assert executor.classify_matchup(**kwargs, depth_fraction=0, horizon_fraction=0.5, strongest_vs_weakest=True) == "DEFER_HORIZON_CENSORED"


def test_operational_and_evidence_precedence():
    bootstrap = executor.percentile_bootstrap_mean([0.9] * 18, seed=2, resamples=100)
    kwargs = dict(scores=[0.9] * 18, tape_means=[0.9, 0.9, 0.9], depth_fraction=0, horizon_fraction=0, bootstrap=bootstrap)
    assert executor.classify_matchup(**kwargs, statuses=["FALLBACK"]) == "DEFER"
    assert executor.classify_matchup(**kwargs, statuses=["EVIDENCE_INTEGRITY_FAILURE"]) == "DEFER"


def test_historical_samples_cannot_enter_bootstrap_and_boundary_is_zero(tmp_path: Path):
    payload = build_prep(output=tmp_path / "prep.json")
    assert payload["bootstrap"]["historical_pools_enter_bootstrap"] is False
    assert all(value is False for value in payload["historical_exclusions"].values())
    assert payload["boundary"]["layer_d_compute_invocations"] == 0
    assert payload["layer_d_compute_authorized"] is False


def _metric(role: str, budget: int, *, depth: object = 8, fallback: object = False) -> dict:
    return {"engine_role": role, "completed_depth": depth, "used_fallback": fallback, "nodes_budget": budget}


def test_search_telemetry_empty_fails_closed():
    game = {"search_metrics": ()}
    with pytest.raises(RuntimeError, match="search_metrics"):
        executor._validate_search_telemetry(game, parent_budget=256, child_budget=1024)


@pytest.mark.parametrize("bad", [
    [{"engine_role": "spectator", "completed_depth": 8, "used_fallback": False, "nodes_budget": 1024}],
    [{"engine_role": "child", "used_fallback": False, "nodes_budget": 1024}],
    [{"engine_role": "child", "completed_depth": 8, "nodes_budget": 1024}],
    [{"engine_role": "child", "completed_depth": 8, "used_fallback": False, "nodes_budget": 999}],
])
def test_search_telemetry_malformed_fails_closed(bad):
    with pytest.raises(RuntimeError, match="evidence-integrity"):
        executor._validate_search_telemetry({"search_metrics": bad}, parent_budget=256, child_budget=1024)


def test_search_telemetry_requires_both_roles_and_validates_budgets():
    assert len(executor._validate_search_telemetry({"search_metrics": [_metric("child", 1024), _metric("parent", 256)]}, parent_budget=256, child_budget=1024)) == 2
    with pytest.raises(RuntimeError, match="role-aware"):
        executor._validate_search_telemetry({"search_metrics": [_metric("child", 1024)]}, parent_budget=256, child_budget=1024)


def test_western_runtime_guards_fail_closed(monkeypatch):
    monkeypatch.setattr(executor, "compute_fingerprint", lambda _: "drift")
    with pytest.raises(RuntimeError, match="production Western"):
        executor._validate_western_runtime_guards()
    monkeypatch.setattr(executor, "compute_fingerprint", lambda obj: executor.PRODUCTION_RULESET_FINGERPRINT if obj.repetition_limit == 100000 else executor.QUALIFICATION_RULESET_FINGERPRINT)
    monkeypatch.setattr(executor, "builtin_ruleset_names", lambda: (executor.QUALIFICATION_CONTROL_NAME,))
    with pytest.raises(RuntimeError, match="non-public"):
        executor._validate_western_runtime_guards()


def test_western_runtime_guard_rejects_gameplay_delta_drift(monkeypatch):
    original = executor.ruleset_to_dict
    def drifted(ruleset, include_metadata=True):
        row = original(ruleset, include_metadata=include_metadata)
        if ruleset.repetition_limit == 5:
            row = dict(row); row["max_ply"] = 999
        return row
    monkeypatch.setattr(executor, "ruleset_to_dict", drifted)
    with pytest.raises(RuntimeError, match="gameplay delta"):
        executor._validate_western_runtime_guards()


def test_production_shaped_arena_result_shape_and_exact_accounting(monkeypatch, tmp_path: Path):
    payload = executor.load_frozen_prep()
    openings = executor.validated_openings(payload)
    calls = []
    def fake_native(_compiled):
        return object()
    def fake_runner(_compiled, _native, _checkpoint_parent, _checkpoint_child, config, *, openings, capture_search_metrics):
        calls.append(config)
        pairs = []
        for index, opening in enumerate(openings.openings):
            metrics = (_metric("child", config.child_nodes_per_move or config.nodes_per_move), _metric("parent", config.parent_nodes_per_move or config.nodes_per_move))
            game0 = ArenaGameResult(index, opening.final_position_key, opening.final_position_key, 0, 0, "checkmate", 0, (), opening.final_position_key, search_metrics=metrics)
            game1 = ArenaGameResult(index, opening.final_position_key, opening.final_position_key, 1, 1, "checkmate", 0, (), opening.final_position_key, search_metrics=metrics)
            pairs.append(ArenaPairResult(index, opening.final_position_key, game0, game1))
        return type("Summary", (), {"pairs": tuple(pairs)})()
    result = executor.run_r6(output=tmp_path / "result.json", arena_runner=fake_runner, native_compiler=fake_native)
    assert len(calls) == 18
    assert result["status"] == "R6_RESULT_COMPLETE"
    assert result["derived_compute"] == {"arena_invocations": 18, "arena_pairs": 108, "arena_games": 216, "action_traces": 216}
    for control in result["controls"].values():
        assert control["classification"] == "STABLE_MONOTONE_POSITIVE"
        for matchup in control["matchups"]:
            assert matchup["bootstrap"]["sample_count"] == 18
            assert all(game["trace_hashes"] for tape in matchup["tape_results"] for pair in tape["pairs"] for game in [pair])
    assert result["boundary"]["layer_d_compute_invocations"] == 0
