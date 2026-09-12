"""Injected-runner contracts for the qualification-only Western executor."""

from __future__ import annotations

from types import SimpleNamespace
import json

import pytest

import scripts.f94_r5_western_qualification_executor as executor
import scripts.f94_r5_western_qualification_prep as prep
from scripts.f94_r5_western_qualification_control import QUALIFICATION_RULESET_FINGERPRINT


def _game(owner: int, seed: int, *, horizon=False, depth=False):
    return SimpleNamespace(
        pair=0,
        child_owner=owner,
        result="max_ply" if horizon else "draw",
        winner=None,
        plies=7,
        actions=(),
        opening_position_key=f"open-{seed}-{owner}",
        final_position_key=f"final-{seed}-{owner}",
        declaration_id=f"decl-{seed}-{owner}",
        search_metrics=(
            {"engine_role": "child", "completed_depth": 12 if depth else 3, "used_fallback": False},
            {"engine_role": "parent", "completed_depth": 2, "used_fallback": False},
        ),
    )


def _runner(*, horizon=(), depth=(), score=0.75):
    def run(*args, **kwargs):
        seed = args[4].opening_seed
        return SimpleNamespace(
            pairs=(SimpleNamespace(
                child_pair_score=score,
                game_child_owner0=_game(0, seed, horizon=0 in horizon, depth=0 in depth),
                game_child_owner1=_game(1, seed, horizon=1 in horizon, depth=1 in depth),
            ),)
        )

    return run


def test_loader_rejects_prep_tamper(tmp_path):
    payload = prep.build_prep(output=tmp_path / "prep.json")
    payload["qualification_control"]["repetition_limit"] = 6
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="fingerprint|identity"):
        executor.load_frozen_prep(prep_path=tampered)


def test_executor_is_exactly_three_pairs_and_non_authoritative(tmp_path):
    calls = []
    prep_path = tmp_path / "prep.json"
    prep.build_prep(output=prep_path)

    def runner(*args, **kwargs):
        calls.append(args[4])
        return _runner()(*args, **kwargs)

    result = executor.run_qualification_control(
        prep_path=prep_path,
        output=tmp_path / "result.json",
        arena_runner=runner,
        native_compiler=lambda compiled: object(),
    )
    assert len(calls) == 3
    assert result["status"] == "QUALIFICATION_CONTROL_RESULT_COMPLETE"
    assert result["derived_compute"] == {
        "arena_invocations": 3,
        "arena_pairs": 3,
        "arena_games": 6,
        "action_traces": 6,
    }
    assert result["qualification_control"]["qualification_ruleset_fingerprint"] == QUALIFICATION_RULESET_FINGERPRINT
    assert result["control_only"] is True
    assert result["not_layer_d_authority"] is True
    assert result["observed_not_poolable"] is True


def test_executor_pools_censor_descriptors(tmp_path):
    prep_path = tmp_path / "prep.json"
    prep.build_prep(output=prep_path)
    result = executor.run_qualification_control(
        prep_path=prep_path,
        output=tmp_path / "result.json",
        arena_runner=_runner(horizon=(0, 1), depth=()),
        native_compiler=lambda compiled: object(),
    )
    assert result["direction"] == "HORIZON_CENSORED"
    assert result["pooled_censoring"]["strongest_vs_weakest_horizon"] == {
        "max_ply_hits": 6,
        "games": 6,
        "fraction": pytest.approx(1.0),
    }
    assert result["pooled_censoring"]["child_depth_ceiling"]["fraction"] == pytest.approx(0.0)


def test_executor_rejects_evaluator_mismatch_before_native_compile(tmp_path, monkeypatch):
    prep_path = tmp_path / "prep.json"
    prep.build_prep(output=prep_path)
    original = executor.LearnableMaterialCheckpoint.from_profile

    def mismatch(cls, compiled, profile, **kwargs):
        checkpoint = original(compiled, profile, **kwargs)
        return SimpleNamespace(
            checkpoint_id=checkpoint.checkpoint_id,
            ruleset_fingerprint=checkpoint.ruleset_fingerprint,
            evaluator_version="mismatch",
        )

    monkeypatch.setattr(executor.LearnableMaterialCheckpoint, "from_profile", classmethod(mismatch))
    monkeypatch.setattr(executor, "compile_native_semantic_rules", lambda *_args: pytest.fail("native compile must not run"))
    with pytest.raises(RuntimeError, match="evaluator identity mismatch"):
        executor.run_qualification_control(
            prep_path=prep_path,
            output=tmp_path / "result.json",
            arena_runner=_runner(),
        )
