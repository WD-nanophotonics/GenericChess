"""Fail-closed contracts for Western qualification-control Stage-1."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.f94_r5_western_qualification_stage1_executor as executor


def _payload():
    return executor.load_frozen_prep()


def _game(owner: int, seed: int, *, fallback: bool = False, horizon: bool = False, depth: bool = False):
    return SimpleNamespace(
        pair=0,
        child_owner=owner,
        result="max_ply" if horizon else "checkmate",
        winner=None,
        plies=17,
        actions=(),
        opening_position_key=f"opening-{seed}-{owner}",
        final_position_key=f"final-{seed}-{owner}",
        declaration_id=f"decl-{seed}-{owner}",
        search_metrics=(
            {"engine_role": "child", "completed_depth": 12 if depth else 3, "used_fallback": fallback},
            {"engine_role": "parent", "completed_depth": 3, "used_fallback": fallback},
        ),
    )


def _runner(*, score: float = 0.75, fallback_pair: tuple[int, int] | None = None, fail_seed: int | None = None):
    def run(*args, **kwargs):
        config = args[4]
        seed = config.opening_seed
        if fail_seed == seed:
            raise RuntimeError("synthetic operational failure")
        assert config.pairs == 6
        assert config.opening_count == 6
        pairs = []
        for index in range(6):
            fallback = fallback_pair == (seed, index)
            owner0 = _game(0, seed * 10 + index, fallback=fallback)
            owner1 = _game(1, seed * 10 + index, fallback=fallback)
            owner0.pair = index
            owner1.pair = index
            pairs.append(SimpleNamespace(pair=index, child_pair_score=score, game_child_owner0=owner0, game_child_owner1=owner1))
        return SimpleNamespace(pairs=tuple(pairs))

    return run


def _run(tmp_path, runner, *, native_compiler=None):
    return executor.run_stage1(
        prep_path=executor.PREP_PATH,
        output=tmp_path / "result.json",
        arena_runner=runner,
        native_compiler=native_compiler or (lambda compiled: object()),
    )


def test_frozen_stage1_prep_has_exact_disjoint_shape():
    payload = _payload()
    assert payload["tape_seeds"] == [9701, 9702, 9703]
    assert payload["disallowed_tape_seeds"] == [9401, 9402, 9403, 9501, 9502, 9503, 9601, 9602, 9603]
    assert [row["opening_count"] for row in payload["opening_corpora"]] == [6, 6, 6]
    assert payload["budgets"]["arena_pairs"] == 18
    assert payload["budgets"]["arena_games"] == 36
    assert payload["budgets"]["action_traces"] == 36
    assert payload["bootstrap"]["resamples"] == 10_000


def test_bootstrap_is_deterministic_and_uses_only_stage1_scores():
    scores = [0.75] * 18
    first = executor.percentile_bootstrap_mean(scores)
    second = executor.percentile_bootstrap_mean(scores)
    assert first == second
    assert first["lower"] == pytest.approx(0.75)
    assert first["upper"] == pytest.approx(0.75)


def test_executor_runs_exact_three_invocations_and_shape(tmp_path):
    calls = []
    native_objects = []

    def native(compiled):
        native_objects.append(compiled)
        return object()

    def runner(*args, **kwargs):
        calls.append(args[0])
        return _runner()(*args, **kwargs)

    result = _run(tmp_path, runner, native_compiler=native)
    assert len(calls) == 3
    assert len(native_objects) == 1
    assert result["status"] == "STAGE1_RESULT_COMPLETE"
    assert result["derived_compute"] == {"arena_invocations": 3, "arena_pairs": 18, "arena_games": 36, "action_traces": 36}
    assert result["direction"] == "STABLE_POSITIVE_CONTROL"
    assert result["pooled_pair_count"] == 18
    assert all(row["pair_count"] == 6 for row in result["tape_results"])
    assert result["control_only"] is True
    assert result["stage_1_authorized"] is False


def test_fallback_is_unresolved_before_positive_classification(tmp_path):
    result = _run(tmp_path, _runner(fallback_pair=(9701, 0)))
    assert result["status"] == "STAGE1_RESULT_COMPLETE"
    assert result["direction"] == "OPERATIONALLY_UNRESOLVED"


def test_operational_failure_is_incomplete_and_unresolved(tmp_path):
    result = _run(tmp_path, _runner(fail_seed=9702))
    assert result["status"] == "STAGE1_RESULT_INCOMPLETE"
    assert result["direction"] == "OPERATIONALLY_UNRESOLVED"
    assert result["derived_compute"] == {"arena_invocations": 2, "arena_pairs": 6, "arena_games": 12, "action_traces": 12}


def test_old_tape_seed_is_rejected_before_native_compile(monkeypatch):
    payload = _payload()
    payload["tape_seeds"] = [9601, 9702, 9703]
    payload["prep_fingerprint"] = executor._prep_fingerprint(payload)
    with pytest.raises(RuntimeError, match="Stage-1 tape identity"):
        executor._validate_prep_identity(payload, executor.ROOT)


def test_opening_identity_is_validated_before_runner(tmp_path, monkeypatch):
    payload = _payload()
    payload["opening_corpora"][1]["openings"][2]["final_position_key"] = "tampered"
    monkeypatch.setattr(executor, "load_frozen_prep", lambda *args, **kwargs: payload)
    calls = []
    with pytest.raises(RuntimeError, match="opening final-position identity"):
        _run(tmp_path, lambda *args, **kwargs: calls.append(args))
    assert calls == []
