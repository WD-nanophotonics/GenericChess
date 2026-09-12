from pathlib import Path

import pytest

import scripts.f94_r5_result_executor as executor


def _summary(*_args, **_kwargs):
    games = []
    for pair in range(6):
        for owner in (0, 1):
            games.append({"pair_index": pair, "child_owner": owner, "termination_status": "draw", "actual_plies": 7, "opening_position_key": f"o{pair}", "final_position_key": f"f{pair}-{owner}", "actions": [], "search_metrics": [{"engine_role": "child", "completed_depth": 3}, {"engine_role": "parent", "completed_depth": 2}]})
    return {"pair_scores": [0.75] * 6, "games": games}


def test_r5_loader_rejects_prep_byte_tamper_before_execution(tmp_path):
    tampered = tmp_path / "prep.json"
    tampered.write_bytes(executor.PREP_PATH.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="byte SHA256"):
        executor.load_frozen_prep(prep_path=tampered)


def test_r5_executor_runs_exact_ready_shape_and_short_circuits_boundary():
    calls = []
    def runner(*args, **kwargs):
        calls.append(args[4])
        return _summary()
    result = executor.run_result(arena_runner=runner, native_compiler=lambda compiled: object())
    assert len(calls) == 18
    assert result["derived_compute"] == {"arena_invocations": 18, "arena_pairs": 108, "arena_games": 216, "action_traces": 216, "strongest_vs_weakest_games": 72, "boundary_arena_invocations": 0}
    assert result["result_sandbox_sha"]
    assert result["result_executor_sha256"]
    ready = [row for row in result["candidates"] if row["name"] != "F86N-R1 boundary V4-3"]
    assert all(len(row["result"]["behavior_descriptors"]["action_trace_contract"]["value"]["action_traces"]) == 108 for row in ready)
    assert all(row["result"]["behavior_descriptors"]["action_trace_contract"]["value"]["strongest_vs_weakest_pooled_horizon"]["games"] == 36 for row in ready)
