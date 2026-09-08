"""Bounded protocol tests for F63-R1 game-atomic arena progress."""

from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from generic_chess.learning.arena import (
    ArenaConfig,
    ArenaExecutionCaps,
    ArenaExecutionError,
    ArenaGameResult,
    arena_decision_bound,
    run_arena_game_resumable,
)


def _inputs(monkeypatch, *, pairs=4, workers=1):
    from generic_chess.learning import arena as arena_module

    openings = SimpleNamespace(
        openings=tuple(
            SimpleNamespace(
                index=index,
                final_position_key=f"opening-{index}",
            )
            for index in range(pairs)
        ),
        to_dict=lambda: {
            "openings": [
                {
                    "index": index,
                    "opening_seed": 100 + index,
                    "target_plies": 1,
                    "actions": [],
                    "final_position_key": f"opening-{index}",
                }
                for index in range(pairs)
            ]
        },
    )
    compiled = SimpleNamespace(ruleset_fingerprint="rules-v1")
    parent = SimpleNamespace(checkpoint_id="parent-v1")
    child = SimpleNamespace(checkpoint_id="child-v1")
    config = ArenaConfig(
        pairs=pairs, nodes_per_move=17, max_depth=3, tt_megabytes=2,
        opening_count=pairs, min_plies=1, max_plies=2, workers=workers,
    )
    monkeypatch.setattr(
        arena_module, "_prepare_arena", lambda *_args, **_kwargs: openings
    )
    monkeypatch.setattr(
        arena_module, "_validate_replayed_game", lambda *_args, **_kwargs: None
    )
    return arena_module, compiled, parent, child, config, openings


def _game(pair, owner):
    return ArenaGameResult(
        pair=pair,
        opening_id=f"opening-{pair}",
        opening_position_key=f"opening-{pair}",
        child_owner=owner,
        winner=owner,
        result="win",
        plies=0,
        actions=(),
        final_position_key=f"final-{pair}-{owner}",
    )


def test_single_game_is_persisted_and_partial_pair_has_no_statistics(
    monkeypatch, tmp_path
):
    arena_module, compiled, parent, child, config, _openings = _inputs(
        monkeypatch, pairs=1
    )
    calls = []

    def stop_after_first(*args, **kwargs):
        owner = kwargs["child_owner"]
        calls.append(owner)
        if owner == 1:
            raise RuntimeError("crash between games")
        return _game(0, owner)

    monkeypatch.setattr(arena_module, "_play_one_game", stop_after_first)
    progress = tmp_path / "partial"
    with pytest.raises(RuntimeError, match="crash between games"):
        run_arena_game_resumable(
            compiled, None, parent, child, config, progress_dir=progress
        )
    assert calls == [0, 1]
    game_path = progress / "game-000000-owner-0.json"
    payload = json.loads(game_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "generic-chess-arena-game-progress-v1"
    assert payload["game_identity"]["node_budgets"] == {"parent": 17, "child": 17}

    monkeypatch.setattr(
        arena_module, "_play_one_game",
        lambda *args, **kwargs: _game(0, kwargs["child_owner"]),
    )
    resumed = run_arena_game_resumable(
        compiled, None, parent, child, config, progress_dir=progress
    )
    assert resumed.status == "COMPLETE"
    assert resumed.completed_games == 2
    assert resumed.completed_pairs == 1
    assert resumed.summary is not None
    assert resumed.summary.pair_count == 1
    assert resumed.summary.pair_scores == (1.0,)


def test_out_of_order_game_completion_is_deterministic_and_lanes_are_bounded(
    monkeypatch, tmp_path
):
    import time

    arena_module, compiled, parent, child, config, _openings = _inputs(
        monkeypatch, pairs=4, workers=99
    )

    def out_of_order(*args, **kwargs):
        pair = kwargs["opening"].index
        time.sleep((8 - pair) * 0.001)
        return _game(pair, kwargs["child_owner"])

    monkeypatch.setattr(arena_module, "_play_one_game", out_of_order)
    first = run_arena_game_resumable(
        compiled, None, parent, child, config,
        progress_dir=tmp_path / "first",
        execution_caps=ArenaExecutionCaps(logical_cpu_count=64),
    )
    second = run_arena_game_resumable(
        compiled, None, parent, child, config,
        progress_dir=tmp_path / "second",
        execution_caps=ArenaExecutionCaps(logical_cpu_count=64),
    )
    assert first == second
    assert first.effective_game_lanes == 8
    assert [p.pair_index for p in first.summary.pairs] == list(range(4))


def test_pause_then_resume_does_not_launch_new_games(monkeypatch, tmp_path):
    arena_module, compiled, parent, child, config, _openings = _inputs(
        monkeypatch, pairs=2, workers=2
    )
    calls = []
    monkeypatch.setattr(
        arena_module,
        "_play_one_game",
        lambda *args, **kwargs: calls.append(kwargs["child_owner"]) or _game(
            kwargs["opening"].index, kwargs["child_owner"]
        ),
    )
    progress = tmp_path / "pause"
    paused = run_arena_game_resumable(
        compiled, None, parent, child, config, progress_dir=progress,
        pause_requested=lambda: True,
    )
    assert paused.status == "PAUSED"
    assert paused.completed_games == 0
    assert calls == []
    resumed = run_arena_game_resumable(
        compiled, None, parent, child, config, progress_dir=progress,
        pause_requested=lambda: False,
    )
    assert resumed.status == "COMPLETE"
    assert len(calls) == 4


def test_hard_game_cap_is_incomplete_not_a_draw(monkeypatch, tmp_path):
    arena_module, compiled, parent, child, config, _openings = _inputs(
        monkeypatch, pairs=1
    )
    monkeypatch.setattr(
        arena_module, "_play_one_game",
        lambda *args, **kwargs: _game(0, kwargs["child_owner"]),
    )
    result = run_arena_game_resumable(
        compiled, None, parent, child, config,
        progress_dir=tmp_path / "cap",
        execution_caps=ArenaExecutionCaps(max_stage_games=1),
    )
    assert result.status == "INCOMPLETE"
    assert result.reason == "max_stage_games"
    assert result.completed_games == 1
    assert result.completed_pairs == 0
    assert result.summary is None


def test_decision_bound_locks_f63_seven_of_eight_regression():
    bound = arena_decision_bound(
        [1.0, 0.5, 0.0, 1.0, 1.0, 0.5, 0.75], 8
    )
    assert bound.completed_total == pytest.approx(4.75)
    assert bound.worst_final_mean == pytest.approx(0.59375)
    assert (
        bound.worst_better_pairs,
        bound.worst_tied_pairs,
        bound.worst_worse_pairs,
    ) == (4, 2, 2)
    assert bound.decision_sufficient is True
    assert bound.strength_estimate_complete is False


def test_game_progress_rejects_wrong_owner_or_stale_identity(monkeypatch, tmp_path):
    arena_module, compiled, parent, child, config, _openings = _inputs(
        monkeypatch, pairs=1
    )
    monkeypatch.setattr(
        arena_module, "_play_one_game",
        lambda *args, **kwargs: _game(0, kwargs["child_owner"]),
    )
    progress = tmp_path / "reject"
    run_arena_game_resumable(
        compiled, None, parent, child, config, progress_dir=progress
    )
    path = progress / "game-000000-owner-0.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["game_identity"]["child_owner"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ArenaExecutionError, match="corrupt"):
        run_arena_game_resumable(
            compiled, None, parent, child, config, progress_dir=progress
        )
