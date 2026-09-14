"""Regression guard for the R27 Arena resource-bound propagation."""

import json
from types import SimpleNamespace

from generic_chess.learning.arena import ArenaConfig, ArenaGameResult, run_arena_game_resumable
from scripts.f61_calibrated_seed3_confirm import _arena_caps


def test_r27_caps_are_persisted_in_manifest(monkeypatch, tmp_path):
    from generic_chess.learning import arena as arena_module

    openings = SimpleNamespace(
        openings=(SimpleNamespace(index=0, final_position_key="opening-0"),),
        to_dict=lambda: {"openings": [{"index": 0, "opening_seed": 100, "target_plies": 1, "actions": [], "final_position_key": "opening-0"}]},
    )
    compiled = SimpleNamespace(ruleset_fingerprint="rules-v1")
    parent = SimpleNamespace(checkpoint_id="parent-v1")
    child = SimpleNamespace(checkpoint_id="child-v1")
    config = ArenaConfig(pairs=1, nodes_per_move=17, max_depth=3, tt_megabytes=2, opening_count=1, min_plies=1, max_plies=2, workers=1)
    monkeypatch.setattr(arena_module, "_prepare_arena", lambda *_args, **_kwargs: openings)
    monkeypatch.setattr(arena_module, "_validate_replayed_game", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        arena_module,
        "_play_one_game",
        lambda *args, **kwargs: ArenaGameResult(
            pair=0, opening_id="opening-0", opening_position_key="opening-0",
            child_owner=kwargs["child_owner"], winner=kwargs["child_owner"],
            result="win", plies=0, actions=(), final_position_key="final",
        ),
    )
    progress = tmp_path / "r27-caps"
    result = run_arena_game_resumable(
        compiled,
        None,
        parent,
        child,
        config,
        progress_dir=progress,
        execution_caps=_arena_caps(),
    )
    assert result.status == "COMPLETE"
    identity = json.loads((progress / "manifest.json").read_text(encoding="utf-8"))["identity"]
    assert identity["execution_caps"] == {
        "per_game_wall_seconds": 3600.0,
        "per_game_nodes": 400000,
        "per_game_plies": 200,
        "max_stage_games": 6,
        "max_concurrent_games": 1,
        "stage_wall_seconds": 18000.0,
        "logical_cpu_count": 2,
    }
