"""Fail-closed contracts for the Western qualification executor."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.f94_r5_western_qualification_executor as executor
from scripts.f94_r5_western_qualification_control import QUALIFICATION_RULESET_FINGERPRINT


def _frozen_payload():
    return json.loads(executor.PREP_PATH.read_text(encoding="utf-8"))


def _game(owner: int, seed: int, *, horizon=False, depth=False, fallback=False):
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
            {"engine_role": "child", "completed_depth": 12 if depth else 3, "used_fallback": fallback},
            {"engine_role": "parent", "completed_depth": 2, "used_fallback": fallback},
        ),
    )


def _runner(*, horizon_by_seed=None, depth_by_seed=None, score_by_seed=None, fallback_by_seed=None, failure_seed=None):
    horizon_by_seed = horizon_by_seed or {}
    depth_by_seed = depth_by_seed or {}
    score_by_seed = score_by_seed or {}
    fallback_by_seed = fallback_by_seed or set()

    def run(*args, **kwargs):
        seed = args[4].opening_seed
        if seed == failure_seed:
            raise RuntimeError("synthetic operational failure")
        horizon = horizon_by_seed.get(seed, set())
        depth = depth_by_seed.get(seed, set())
        fallback = seed in fallback_by_seed
        return SimpleNamespace(
            pairs=(SimpleNamespace(
                child_pair_score=score_by_seed.get(seed, 0.75),
                game_child_owner0=_game(0, seed, horizon=0 in horizon, depth=0 in depth, fallback=fallback),
                game_child_owner1=_game(1, seed, horizon=1 in horizon, depth=1 in depth, fallback=fallback),
            ),)
        )

    return run


def _run(tmp_path, runner, *, native_compiler=None):
    return executor.run_qualification_control(
        prep_path=executor.PREP_PATH,
        output=tmp_path / "result.json",
        arena_runner=runner,
        native_compiler=native_compiler or (lambda compiled: object()),
    )


def test_loader_rejects_whitespace_byte_tamper(tmp_path):
    tampered = tmp_path / "prep.json"
    tampered.write_bytes(executor.PREP_PATH.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="byte SHA256"):
        executor._validate_frozen_prep_bytes(tampered)


def test_loader_rejects_protocol_sha_tamper():
    payload = _frozen_payload()
    payload["protocol_source_sha"] = "0" * 40
    with pytest.raises(RuntimeError, match="protocol/source SHA"):
        executor._validate_prep_identity(payload, executor.ROOT)


def test_loader_rejects_non_frozen_path_even_when_bytes_match(tmp_path):
    copied = tmp_path / Path(executor.FROZEN_PREP_ARTIFACT).name
    copied.write_bytes(executor.PREP_PATH.read_bytes())
    with pytest.raises(RuntimeError, match="frozen artifact"):
        executor.load_frozen_prep(prep_path=copied)


def test_production_delta_and_catalog_guards_run_before_native(tmp_path, monkeypatch):
    native_calls = []
    original = executor.build_western_chess_ruleset
    monkeypatch.setattr(executor, "build_western_chess_ruleset", lambda: replace(original(), max_ply=999))
    with pytest.raises(RuntimeError, match="production Western fingerprint"):
        _run(tmp_path, _runner(), native_compiler=lambda compiled: native_calls.append(compiled))
    assert native_calls == []

    monkeypatch.setattr(executor, "build_western_chess_ruleset", original)
    monkeypatch.setattr(executor, "builtin_ruleset_names", lambda: ("western_chess", "standard_shogi", "western_chess_qualification_control_v1"))
    with pytest.raises(RuntimeError, match="must not be public"):
        _run(tmp_path, _runner(), native_compiler=lambda compiled: native_calls.append(compiled))
    assert native_calls == []

    monkeypatch.setattr(executor, "builtin_ruleset_names", lambda: ("western_chess", "standard_shogi"))
    monkeypatch.setattr(executor, "compute_fingerprint", lambda _: executor.PRODUCTION_RULESET_FINGERPRINT)
    monkeypatch.setattr(executor, "build_western_chess_ruleset", lambda: replace(original(), max_ply=999))
    with pytest.raises(RuntimeError, match="gameplay delta"):
        _run(tmp_path, _runner(), native_compiler=lambda compiled: native_calls.append(compiled))
    assert native_calls == []


def test_all_openings_validate_before_runner_when_row_two_is_tampered(tmp_path, monkeypatch):
    payload = _frozen_payload()
    payload["opening_corpora"][1]["corpus_id"] = "tampered"
    monkeypatch.setattr(executor, "load_frozen_prep", lambda *args, **kwargs: payload)
    calls = []
    with pytest.raises(RuntimeError, match="opening corpus identity"):
        _run(tmp_path, lambda *args, **kwargs: calls.append(args))
    assert calls == []


def test_all_openings_validate_before_runner_when_row_three_opening_is_tampered(tmp_path, monkeypatch):
    payload = _frozen_payload()
    payload["opening_corpora"][2]["selected_final_position_key"] = "tampered"
    monkeypatch.setattr(executor, "load_frozen_prep", lambda *args, **kwargs: payload)
    calls = []
    with pytest.raises(RuntimeError, match="final-position identity"):
        _run(tmp_path, lambda *args, **kwargs: calls.append(args))
    assert calls == []


def test_executor_uses_one_executable_object_and_exact_shape(tmp_path):
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
    assert len(native_objects) == 1 and all(item is calls[0] for item in native_objects)
    assert result["status"] == "QUALIFICATION_CONTROL_RESULT_COMPLETE"
    assert result["derived_compute"] == {"arena_invocations": 3, "arena_pairs": 3, "arena_games": 6, "action_traces": 6}
    assert result["qualification_control"]["qualification_ruleset_fingerprint"] == QUALIFICATION_RULESET_FINGERPRINT
    assert result["control_only"] is True
    assert result["not_layer_d_authority"] is True
    assert result["observed_not_poolable"] is True
    assert result["p0_observations_pooled"] is False
    assert result["r2_observations_pooled"] is False
    assert result["r3_observations_pooled"] is False
    assert result["r5_observations_pooled"] is False


def test_pooled_horizon_one_of_six_is_not_censored(tmp_path):
    result = _run(tmp_path, _runner(horizon_by_seed={9601: {0}}))
    assert result["direction"] == "POSITIVE_DIRECTION"
    assert result["pooled_censoring"]["strongest_vs_weakest_horizon"] == {"max_ply_hits": 1, "games": 6, "fraction": pytest.approx(1 / 6)}


def test_pooled_horizon_three_of_six_is_censored(tmp_path):
    result = _run(tmp_path, _runner(horizon_by_seed={9601: {0}, 9602: {0}, 9603: {0}}))
    assert result["direction"] == "HORIZON_CENSORED"
    assert result["pooled_censoring"]["strongest_vs_weakest_horizon"]["fraction"] == pytest.approx(3 / 6)


def test_pooled_depth_one_of_six_is_not_censored(tmp_path):
    result = _run(tmp_path, _runner(depth_by_seed={9601: {0}}))
    assert result["direction"] == "POSITIVE_DIRECTION"
    assert result["pooled_censoring"]["child_depth_ceiling"]["fraction"] == pytest.approx(1 / 6)


def test_pooled_depth_three_of_six_is_censored(tmp_path):
    result = _run(tmp_path, _runner(depth_by_seed={9601: {0}, 9602: {0}, 9603: {0}}))
    assert result["direction"] == "DEPTH_CENSORED"
    assert result["pooled_censoring"]["child_depth_ceiling"]["fraction"] == pytest.approx(3 / 6)


@pytest.mark.parametrize(
    ("scores", "expected"),
    [
        ({9601: 0.75, 9602: 0.75, 9603: 0.75}, "POSITIVE_DIRECTION"),
        ({9601: 0.25, 9602: 0.25, 9603: 0.25}, "NEGATIVE_DIRECTION"),
        ({9601: 0.75, 9602: 0.25, 9603: 0.5}, "MIXED_OR_UNCERTAIN"),
    ],
)
def test_three_tape_direction_classification(tmp_path, scores, expected):
    assert _run(tmp_path, _runner(score_by_seed=scores))["direction"] == expected


def test_fallback_precedes_direction(tmp_path):
    result = _run(tmp_path, _runner(fallback_by_seed={9601}, score_by_seed={9601: 0.75, 9602: 0.25, 9603: 0.25}))
    assert result["direction"] == "FALLBACK"


def test_operational_failure_is_incomplete_and_unresolved(tmp_path):
    result = _run(tmp_path, _runner(failure_seed=9602))
    assert result["status"] == "QUALIFICATION_CONTROL_RESULT_INCOMPLETE"
    assert result["direction"] == "OPERATIONALLY_UNRESOLVED"
    assert result["derived_compute"]["arena_invocations"] == 2


def test_all_traces_and_result_provenance_are_complete(tmp_path):
    result = _run(tmp_path, _runner())
    assert all(
        game["opening_position_key"] and game["final_position_key"] and game["actions"] is not None and game["action_trace_sha256"]
        for row in result["tape_results"]
        for game in row["games"]
    )
    assert result["protocol_source_sha"] == executor.FROZEN_PROTOCOL_SHA
    assert result["source_sandbox_sha"] == executor.FROZEN_PROTOCOL_SHA
    assert result["prep_byte_sha256"] == executor.FROZEN_PREP_SHA256
    assert result["result_executor_path"] == "scripts/f94_r5_western_qualification_executor.py"
    expected_executor_sha = hashlib.sha256(Path(executor.__file__).read_bytes()).hexdigest()
    assert result["result_executor_sha256"] == expected_executor_sha


def test_evaluator_mismatch_rejected_before_native_compile(tmp_path, monkeypatch):
    original = executor.LearnableMaterialCheckpoint.from_profile

    def mismatch(cls, compiled, profile, **kwargs):
        checkpoint = original(compiled, profile, **kwargs)
        return SimpleNamespace(checkpoint_id=checkpoint.checkpoint_id, ruleset_fingerprint=checkpoint.ruleset_fingerprint, evaluator_version="mismatch")

    native_calls = []
    monkeypatch.setattr(executor.LearnableMaterialCheckpoint, "from_profile", classmethod(mismatch))
    with pytest.raises(RuntimeError, match="evaluator identity mismatch"):
        _run(tmp_path, _runner(), native_compiler=lambda compiled: native_calls.append(compiled))
    assert native_calls == []
