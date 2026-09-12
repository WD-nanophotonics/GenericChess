from pathlib import Path
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
    tampered = tmp_path / "prep.json"
    tampered.write_bytes(executor.PREP_PATH.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="SHA256|fingerprint"):
        executor.load_frozen_prep(prep_path=tampered)


def test_pilot_executor_is_exactly_six_pairs_and_non_authoritative(tmp_path):
    calls = []

    def runner(*args, **kwargs):
        calls.append(args[4])
        return _summary()

    output = tmp_path / "pilot-result.json"
    result = executor.run_pilot(output=output, arena_runner=runner)
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
