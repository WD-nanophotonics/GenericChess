import json
from types import SimpleNamespace

import pytest

import scripts.f94_r5_pilot_executor as executor
import scripts.f94_r5_pilot_prep as prep


def _game(owner: int):
    return SimpleNamespace(
        pair=0,
        child_owner=owner,
        result="draw",
        winner=None,
        plies=7,
        actions=(),
        opening_position_key=f"open-{owner}",
        final_position_key=f"final-{owner}",
        declaration_id=None,
        search_metrics=(
            {"engine_role": "child", "completed_depth": 3, "used_fallback": False},
            {"engine_role": "parent", "completed_depth": 2, "used_fallback": False},
        ),
    )


def _summary(*_args, **_kwargs):
    return SimpleNamespace(
        pairs=(SimpleNamespace(
            child_pair_score=0.75,
            game_child_owner0=_game(0),
            game_child_owner1=_game(1),
        ),)
    )


def _prep(tmp_path):
    return prep.build_prep(output=tmp_path / "pilot-prep.json")


def _patterned_runner(*, horizon=None, depth=None, score=0.75):
    horizon = horizon or {}
    depth = depth or {}

    def game(owner, seed):
        return SimpleNamespace(
            pair=0,
            child_owner=owner,
            result="max_ply" if owner in horizon.get(seed, set()) else "draw",
            winner=None,
            plies=7,
            actions=(),
            opening_position_key=f"open-{seed}-{owner}",
            final_position_key=f"final-{seed}-{owner}",
            declaration_id=f"decl-{seed}-{owner}",
            search_metrics=(
                {"engine_role": "child", "completed_depth": 12 if owner in depth.get(seed, set()) else 3, "used_fallback": False},
                {"engine_role": "parent", "completed_depth": 2, "used_fallback": False},
            ),
        )

    def runner(*args, **kwargs):
        seed = args[4].opening_seed
        return SimpleNamespace(pairs=(SimpleNamespace(
            child_pair_score=score,
            game_child_owner0=game(0, seed),
            game_child_owner1=game(1, seed),
        ),))

    return runner


def test_pilot_prep_is_disjoint_and_non_poolable(tmp_path):
    payload = prep.build_prep(output=tmp_path / "pilot-prep.json")
    source = __import__("json").loads(prep.SOURCE_PREP_PATH.read_text(encoding="utf-8"))
    assert payload["non_poolable_with_r2_r3_r5"] is True
    assert set(payload["pilot_tape_seeds"]).isdisjoint(source["budgets"]["tape_seeds"])
    source_opening_seeds = {
        seed
        for row in source["candidates"]
        for corpus in row["opening_corpora"]
        for seed in corpus["opening_seeds"]
    }
    pilot_opening_seeds = {
        opening["selected_opening_seed"]
        for row in payload["candidates"]
        for opening in row["opening_corpora"]
    }
    assert pilot_opening_seeds.isdisjoint(source_opening_seeds)
    assert payload["budgets"]["arena_games"] == 12
    assert payload["boundary_control"]["compute"] == 0


def test_pilot_loader_rejects_prep_tamper(tmp_path):
    payload = _prep(tmp_path)
    tampered = tmp_path / "prep.json"
    payload["pilot_tape_seeds"][0] = 9599
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="fingerprint|tape identity"):
        executor.load_frozen_prep(prep_path=tampered)


def test_pilot_executor_is_exactly_six_pairs_and_non_authoritative(tmp_path):
    calls = []

    def runner(*args, **kwargs):
        calls.append(args[4])
        return _summary()

    output = tmp_path / "pilot-result.json"
    pilot_prep = tmp_path / "pilot-prep.json"
    prep.build_prep(output=pilot_prep)
    result = executor.run_pilot(prep_path=pilot_prep, output=output, arena_runner=runner)
    assert len(calls) == 6
    assert result["status"] == "PILOT_RESULT_COMPLETE"
    assert result["derived_compute"] == {
        "arena_invocations": 6,
        "arena_pairs": 6,
        "arena_games": 12,
        "action_traces": 12,
        "boundary_arena_invocations": 0,
    }
    assert result["not_layer_d_authority"] is True
    assert result["observed_not_poolable"] is True
    boundary = next(row for row in result["candidates"] if row["name"] == prep.BOUNDARY_NAME)
    assert boundary["status"] == "PREREQUISITE_A_C_NOT_PASS"
    ready = [row for row in result["candidates"] if row["name"] != prep.BOUNDARY_NAME]
    assert all(row["arena_invocations"] == 3 for row in ready)
    assert all(len(row["tape_results"]) == 3 for row in ready)
    assert all(row["action_traces"] == 6 for row in ready)
    assert output.is_file()


@pytest.mark.parametrize(
    ("horizon", "depth", "expected"),
    [
        ({9501: {0}}, {}, "POSITIVE_DIRECTION"),
        ({9501: {0, 1}, 9502: {0}}, {}, "HORIZON_CENSORED"),
        ({}, {9501: {0}}, "POSITIVE_DIRECTION"),
        ({}, {9501: {0, 1}, 9502: {0}}, "DEPTH_CENSORED"),
    ],
)
def test_pilot_candidate_censoring_is_pooled_across_tapes(tmp_path, horizon, depth, expected):
    pilot_prep = tmp_path / "pilot-prep.json"
    prep.build_prep(output=pilot_prep)
    result = executor.run_pilot(
        prep_path=pilot_prep,
        output=tmp_path / "pilot-result.json",
        arena_runner=_patterned_runner(horizon=horizon, depth=depth),
    )
    candidate = next(row for row in result["candidates"] if row["name"] != prep.BOUNDARY_NAME)
    assert candidate["direction"] == expected
    pooled = candidate["pooled_censoring"]
    if horizon:
        assert pooled["strongest_vs_weakest_horizon"]["fraction"] == pytest.approx(
            sum(len(owners) for owners in horizon.values()) / 6
        )
    if depth:
        assert pooled["child_depth_ceiling"]["fraction"] == pytest.approx(
            sum(len(owners) for owners in depth.values()) / 6
        )


def test_pilot_evaluator_identity_rejected_before_native_compile(tmp_path, monkeypatch):
    pilot_prep = tmp_path / "pilot-prep.json"
    prep.build_prep(output=pilot_prep)
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
        executor.run_pilot(
            prep_path=pilot_prep,
            output=tmp_path / "pilot-result.json",
            arena_runner=_summary,
        )


def test_pilot_prep_protocol_provenance_points_to_pilot_implementation(tmp_path):
    payload = _prep(tmp_path)
    protocol_sha = payload["protocol_source_sha"]
    assert payload["source_sandbox_sha"] == protocol_sha
    subprocess = __import__("subprocess")
    shown = subprocess.check_output(
        ["git", "show", f"{protocol_sha}:scripts/f94_r5_pilot_executor.py"],
        cwd=prep.ROOT,
        text=True,
    )
    assert "pooled_depth_hits" in shown
