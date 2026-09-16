from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import f90_complete_alpha05_arena8 as f90


def test_f90_contract_freezes_alpha05_and_registered_arena8():
    assert f90.WORK_ORDER == "GENERICCHESS_F90_ALPHA05_ARENA8"
    assert f90.ARENA8_CORPUS_ID == "7446aa7fed2e7712941c914785a9db3dc51e9e07350fdbe4cfb7b0c629453755"
    assert f90.ARENA8_OPENING_INDICES == tuple(range(8))
    assert f90.ALPHA05_ID == "0b318ea0a719971634abbc443e3334dfcef4a017d94d4dfd01c8a6ca69954316"


def test_f90_runner_uses_bounded_eight_pair_contract_and_aggregates(
        monkeypatch, tmp_path):
    progress = tmp_path / "progress"
    result = tmp_path / "result.json"
    corpus = SimpleNamespace(
        corpus_id=f90.ARENA8_CORPUS_ID,
        seed=820801,
        min_plies=2,
        max_plies=6,
        openings=tuple(SimpleNamespace(index=index) for index in range(8)),
    )
    parent = SimpleNamespace(checkpoint_id=f90.PARENT_ID)
    candidate = SimpleNamespace(checkpoint_id=f90.ALPHA05_ID)
    metadata = {"candidate_model_sha256": f90.ALPHA05_MODEL_SHA256}
    seen = {}

    monkeypatch.setattr(
        f90, "_load_context",
        lambda: ({"registered": True}, "compiled", "native", parent,
                  candidate, corpus, metadata),
    )

    def fake_run(_compiled, _native, _parent, _candidate, config, *, progress_dir,
                 openings, execution_caps, identity_caps, stage_id, max_pairs,
                 **_kwargs):
        seen.update(config=config, openings=openings, caps=execution_caps,
                    identity_caps=identity_caps, stage_id=stage_id,
                    max_pairs=max_pairs)
        for pair_index in range(8):
            for owner in (0, 1):
                path = Path(progress_dir) / f"game-{pair_index:06d}-owner-{owner}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({
                    "game": {"winner": owner, "result": "checkmate", "plies": 100 + pair_index},
                }), encoding="utf-8")
        summary = SimpleNamespace(
            pair_scores=(1.0, 0.5, 0.0, 0.5, 1.0, 0.5, 0.0, 0.5),
            mean_pair_score=0.5, game_wins=8, game_draws=0, game_losses=8,
        )
        return SimpleNamespace(
            status="COMPLETE", reason=None, completed_games=16,
            completed_pairs=8, total_games=16, summary=summary,
        )

    monkeypatch.setattr(f90, "run_arena_game_resumable", fake_run)
    output = f90.run(progress, result)

    assert seen["stage_id"] == "f90-complete-alpha05-arena8"
    assert seen["max_pairs"] == 8
    assert seen["config"].pairs == 8
    assert seen["config"].opening_count == 8
    assert seen["config"].nodes_per_move == 512
    assert seen["config"].parent_nodes_per_move == 512
    assert seen["config"].child_nodes_per_move == 512
    assert seen["config"].max_depth == 12
    assert seen["config"].tt_megabytes == 8
    assert seen["config"].tt_reset_each_move is True
    assert seen["caps"].per_game_nodes == 262144
    assert seen["caps"].per_game_plies == 512
    assert seen["caps"].max_stage_games == 16
    assert seen["caps"].max_concurrent_games == 2
    assert output["opening_indices"] == list(range(8))
    assert output["completed_games"] == 16
    assert len(output["games"]) == 16
    assert output["games"][0]["plies"] == 100
    assert output["games"][-1]["plies"] == 107
    assert output["historical_f89_arena4_context"]["pooled"] is False
    assert json.loads(result.read_text(encoding="utf-8"))["status"] == "COMPLETE"


def test_f90_output_separates_opening_max_plies_from_game_cap(
        monkeypatch, tmp_path):
    progress = tmp_path / "progress"
    result = tmp_path / "result.json"
    corpus = SimpleNamespace(
        corpus_id=f90.ARENA8_CORPUS_ID,
        seed=820801,
        min_plies=2,
        max_plies=6,
        openings=tuple(SimpleNamespace(index=index) for index in range(8)),
    )
    parent = SimpleNamespace(checkpoint_id=f90.PARENT_ID)
    candidate = SimpleNamespace(checkpoint_id=f90.ALPHA05_ID)
    metadata = {"candidate_model_sha256": f90.ALPHA05_MODEL_SHA256}
    monkeypatch.setattr(
        f90, "_load_context",
        lambda: ({}, "compiled", "native", parent, candidate, corpus, metadata),
    )
    monkeypatch.setattr(
        f90,
        "run_arena_game_resumable",
        lambda *_args, **_kwargs: SimpleNamespace(
            status="INCOMPLETE", reason="per_game_wall_seconds",
            completed_games=2, completed_pairs=1, total_games=16,
            summary=None,
        ),
    )
    progress.mkdir()
    for owner, plies, searched_nodes in ((0, 79, 40448), (1, 84, 43008)):
        (progress / f"partial-game-000001-owner-{owner}.json").write_text(
            json.dumps({
                "status": "partial",
                "plies": plies,
                "searched_nodes": searched_nodes,
            }),
            encoding="utf-8",
        )

    output = f90.run(progress, result)

    assert output["config"]["max_plies"] == 6
    assert output["execution_caps"]["per_game_plies"] == 512
    assert output["completed_games"] == 2
    assert output["status"] == "INCOMPLETE"
    assert output["reason"] == "per_game_wall_seconds"
    assert output["resumable_partial_games"] == [
        {
            "pair_index": 1,
            "opening_index": 1,
            "child_owner": 0,
            "plies": 79,
            "searched_nodes": 40448,
            "status": "partial",
            "resumable": True,
        },
        {
            "pair_index": 1,
            "opening_index": 1,
            "child_owner": 1,
            "plies": 84,
            "searched_nodes": 43008,
            "status": "partial",
            "resumable": True,
        },
    ]
    assert output["continuation"] == {
        "terminal_games_are_immutable": True,
        "resume_partial_games": True,
        "partial_game_count": 2,
    }


def test_f90_progress_games_reads_nested_completed_game_fields(tmp_path):
    progress = tmp_path / "progress"
    progress.mkdir()
    (progress / "game-000007-owner-1.json").write_text(json.dumps({
        "schema": "generic-chess-arena-game-progress-v1",
        "status": "completed",
        "game": {"winner": 1, "result": "checkmate", "plies": 49},
    }), encoding="utf-8")

    assert f90._progress_games(progress) == [{
        "pair_index": 7,
        "opening_index": 7,
        "child_owner": 1,
        "winner": 1,
        "result": "checkmate",
        "plies": 49,
        "completed": True,
        "truncated": False,
    }]
