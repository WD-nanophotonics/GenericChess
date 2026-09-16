from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import f89_complete_alpha05_arena4 as f89


def test_f89_contract_freezes_alpha05_and_registered_arena4():
    assert f89.WORK_ORDER == "GENERICCHESS_F89_ALPHA05_ARENA4"
    assert f89.ARENA4_CORPUS_ID == "593652dd655ddc67f38d9a194b9b2a44f7eef3e28d22a83c5f01abeb35b971a1"
    assert f89.ARENA4_OPENING_INDICES == (0, 1, 2, 3)
    assert f89.ALPHA05_ID == "0b318ea0a719971634abbc443e3334dfcef4a017d94d4dfd01c8a6ca69954316"


def test_f89_runner_uses_bounded_four_pair_contract_and_aggregates(
        monkeypatch, tmp_path):
    progress = tmp_path / "progress"
    result = tmp_path / "result.json"
    corpus = SimpleNamespace(
        corpus_id=f89.ARENA4_CORPUS_ID,
        seed=820401,
        min_plies=2,
        max_plies=6,
        openings=tuple(SimpleNamespace(index=index) for index in range(4)),
    )
    parent = SimpleNamespace(checkpoint_id=f89.PARENT_ID)
    candidate = SimpleNamespace(checkpoint_id=f89.ALPHA05_ID)
    metadata = {"candidate_model_sha256": f89.ALPHA05_MODEL_SHA256}
    seen = {}

    monkeypatch.setattr(
        f89, "_load_context",
        lambda: ({"registered": True}, "compiled", "native", parent,
                 candidate, corpus, metadata),
    )

    def fake_run(_compiled, _native, _parent, _candidate, config, *, progress_dir,
                 openings, execution_caps, identity_caps, stage_id, max_pairs,
                 **_kwargs):
        seen.update(config=config, openings=openings, caps=execution_caps,
                    identity_caps=identity_caps, stage_id=stage_id,
                    max_pairs=max_pairs)
        for pair_index in range(4):
            for owner in (0, 1):
                path = Path(progress_dir) / f"game-{pair_index:06d}-owner-{owner}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({
                    "game": {
                        "winner": owner, "result": "checkmate", "plies": 100 + pair_index,
                    },
                }), encoding="utf-8")
        summary = SimpleNamespace(
            pair_scores=(1.0, 0.5, 0.0, 0.5), mean_pair_score=0.5,
            game_wins=4, game_draws=0, game_losses=4,
        )
        return SimpleNamespace(
            status="COMPLETE", reason=None, completed_games=8,
            completed_pairs=4, total_games=8, summary=summary,
        )

    monkeypatch.setattr(f89, "run_arena_game_resumable", fake_run)
    output = f89.run(progress, result)

    assert seen["stage_id"] == "f89-complete-alpha05-arena4"
    assert seen["max_pairs"] == 4
    assert seen["config"].pairs == 4
    assert seen["config"].opening_count == 4
    assert seen["config"].nodes_per_move == 512
    assert seen["config"].parent_nodes_per_move == 512
    assert seen["config"].child_nodes_per_move == 512
    assert seen["config"].max_depth == 12
    assert seen["config"].tt_megabytes == 8
    assert seen["config"].tt_reset_each_move is True
    assert seen["caps"].per_game_nodes == 262144
    assert seen["caps"].per_game_plies == 512
    assert seen["caps"].max_concurrent_games == 2
    assert output["opening_indices"] == [0, 1, 2, 3]
    assert output["completed_games"] == 8
    assert len(output["games"]) == 8
    assert output["games"][0]["winner"] == 0
    assert output["games"][0]["result"] == "checkmate"
    assert output["games"][0]["plies"] == 100
    assert output["historical_raw_f87_arena4_context"]["pooled"] is False
    assert json.loads(result.read_text(encoding="utf-8"))["status"] == "COMPLETE"


def test_f89_progress_games_reads_nested_completed_game_fields(tmp_path):
    progress = tmp_path / "progress"
    progress.mkdir()
    (progress / "game-000000-owner-0.json").write_text(json.dumps({
        "schema": "generic-chess-arena-game-progress-v1",
        "status": "completed",
        "game": {"winner": 1, "result": "checkmate", "plies": 277},
    }), encoding="utf-8")

    assert f89._progress_games(progress) == [{
        "pair_index": 0,
        "opening_index": 0,
        "child_owner": 0,
        "winner": 1,
        "result": "checkmate",
        "plies": 277,
        "completed": True,
        "truncated": False,
    }]
