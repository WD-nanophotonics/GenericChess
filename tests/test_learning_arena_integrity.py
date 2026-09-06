"""Learning Phase 1.5: arena measurement integrity gates."""

from dataclasses import asdict, replace
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.learning.arena import (
    ArenaConfig,
    ArenaExecutionError,
    ArenaGameResult,
    ArenaPairResult,
    run_arena,
    run_arena_resumable,
    _trusted_search_elapsed,
)
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.native.compiler import compile_native_rules

from native_test_helpers import generated_compiled, requires_native


@requires_native
def _setup(size=4):
    compiled = generated_compiled(size=size)
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    child = checkpoint.child_checkpoint(
        board_weights={k: v * 1.1 for k, v in checkpoint.board_weights.items()},
        hand_weights={k: v * 1.1 for k, v in checkpoint.hand_weights.items()},
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash="cfg",
        training_seed=7,
    )
    rules = compile_native_rules(compiled)
    return compiled, rules, checkpoint, child


@requires_native
def test_fresh_engine_per_game(monkeypatch):
    compiled, rules, checkpoint, child = _setup()
    from generic_chess.learning import arena as arena_module

    counter = {"n": 0}
    real = arena_module._engine_for

    def counting_engine_for(*args, **kwargs):
        counter["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(arena_module, "_engine_for", counting_engine_for)
    config = ArenaConfig(pairs=2, nodes_per_move=200, max_depth=4)
    run_arena(compiled, rules, checkpoint, child, config)
    # 2 pairs x 2 games x 2 checkpoints = 8 fresh engines.
    assert counter["n"] == 8


@requires_native
def test_pair_games_share_opening_and_swap_colors():
    compiled, rules, checkpoint, child = _setup()
    openings = generate_arena_openings(compiled, count=3, seed=314159)
    config = ArenaConfig(pairs=3, nodes_per_move=200, max_depth=4)
    summary = run_arena(
        compiled, rules, checkpoint, child, config, openings=openings
    )
    for pair in summary.pairs:
        a = pair.game_child_owner0
        b = pair.game_child_owner1
        assert a.opening_position_key == b.opening_position_key
        assert a.opening_id == b.opening_id
        assert a.child_owner == 0
        assert b.child_owner == 1
        assert pair.opening_id == openings.openings[pair.pair_index].final_position_key


@requires_native
def test_search_telemetry_captures_and_replays_every_decision(tmp_path):
    compiled, rules, checkpoint, child = _setup()
    config = ArenaConfig(pairs=1, nodes_per_move=200, max_depth=4)
    progress = tmp_path / "telemetry"
    summary = run_arena_resumable(
        compiled,
        rules,
        checkpoint,
        child,
        config,
        progress_dir=progress,
        capture_search_metrics=True,
    )
    for game in (
        summary.pairs[0].game_child_owner0,
        summary.pairs[0].game_child_owner1,
    ):
        assert len(game.search_metrics) in (game.plies, game.plies + 1)
        assert all(metric["nodes"] <= config.nodes_per_move for metric in game.search_metrics)
        assert all(metric["completed_depth"] >= 0 for metric in game.search_metrics)
        assert all(metric["termination_reason"] for metric in game.search_metrics)
        assert all(metric["nps"] is None or metric["nps"] > 0 for metric in game.search_metrics)
        assert all(
            metric["elapsed_source"] in ("native", "wall_fallback")
            for metric in game.search_metrics
        )
    resumed = run_arena_resumable(
        compiled,
        rules,
        checkpoint,
        child,
        config,
        progress_dir=progress,
        capture_search_metrics=True,
    )
    assert resumed == summary


def test_search_telemetry_rejects_unsigned_elapsed_underflow_shape():
    elapsed, source = _trusted_search_elapsed(18_446_742_229.0, 0.25)
    assert elapsed == 0.25
    assert source == "wall_fallback"
    elapsed, source = _trusted_search_elapsed(0.24, 0.25)
    assert elapsed == 0.24
    assert source == "native"


@requires_native
def test_identical_checkpoint_every_pair_score_exactly_half():
    compiled, rules, checkpoint, _child = _setup()
    config = ArenaConfig(pairs=4, nodes_per_move=200, max_depth=4)
    summary = run_arena(compiled, rules, checkpoint, checkpoint, config)
    assert all(s == 0.5 for s in summary.pair_scores)
    assert summary.mean_pair_score == 0.5
    assert summary.child_better_pairs == 0
    assert summary.child_worse_pairs == 0


@requires_native
def test_reverse_complement_sums_to_one():
    compiled, rules, checkpoint, child = _setup()
    openings = generate_arena_openings(compiled, count=3, seed=314159)
    config = ArenaConfig(pairs=3, nodes_per_move=200, max_depth=4)
    ab = run_arena(compiled, rules, checkpoint, child, config, openings=openings)
    ba = run_arena(compiled, rules, child, checkpoint, config, openings=openings)
    for pa, pb in zip(ab.pairs, ba.pairs):
        assert pa.child_pair_score + pb.child_pair_score == pytest.approx(1.0)


@requires_native
def test_deterministic_rerun():
    compiled, rules, checkpoint, child = _setup()
    openings = generate_arena_openings(compiled, count=3, seed=314159)
    config = ArenaConfig(pairs=3, nodes_per_move=200, max_depth=4)
    r1 = run_arena(compiled, rules, checkpoint, child, config, openings=openings)
    r2 = run_arena(compiled, rules, checkpoint, child, config, openings=openings)
    assert r1.pair_scores == r2.pair_scores
    for p1, p2 in zip(r1.pairs, r2.pairs):
        g1 = p1.game_child_owner0
        g2 = p2.game_child_owner0
        assert g1.actions == g2.actions
        assert g1.winner == g2.winner


@requires_native
def test_engine_failure_is_not_a_draw(monkeypatch):
    compiled, rules, checkpoint, child = _setup()
    from generic_chess.learning import arena as arena_module

    class BrokenResult:
        action = None
        termination_reason = "internal_error"

    class BrokenEngine:
        def __init__(self, *a, **k):
            pass

        def search(self, *a, **k):
            return BrokenResult()

    monkeypatch.setattr(arena_module, "NativeSearchEngine", BrokenEngine)
    config = ArenaConfig(pairs=1, nodes_per_move=200, max_depth=4)
    with pytest.raises(ArenaExecutionError):
        run_arena(compiled, rules, checkpoint, child, config)


def _synthetic_pair(index: int) -> ArenaPairResult:
    def game(owner: int, winner: int | None) -> ArenaGameResult:
        return ArenaGameResult(
            pair=index,
            opening_id=f"opening-{index}",
            opening_position_key=f"position-{index}",
            child_owner=owner,
            winner=winner,
            result="draw" if winner is None else "win",
            plies=index + owner,
            actions=(),
            final_position_key=f"final-{index}-{owner}",
        )
    return ArenaPairResult(
        pair_index=index,
        opening_id=f"opening-{index}",
        game_child_owner0=game(0, None if index % 2 else 0),
        game_child_owner1=game(1, None if index % 2 else 0),
    )


def _synthetic_resumable_inputs(monkeypatch, *, pairs=4, workers=1):
    from generic_chess.learning import arena as arena_module

    openings = SimpleNamespace(
        openings=tuple(
            SimpleNamespace(index=index, final_position_key=f"opening-{index}")
            for index in range(pairs)
        ),
        to_dict=lambda: {
            "openings": [
                {"index": index, "final_position_key": f"opening-{index}", "actions": []}
                for index in range(pairs)
            ]
        },
    )
    monkeypatch.setattr(
        arena_module, "_prepare_arena", lambda *_args, **_kwargs: openings
    )
    monkeypatch.setattr(
        arena_module, "_validate_replayed_game", lambda *_args, **_kwargs: None
    )
    compiled = SimpleNamespace(ruleset_fingerprint="rules-v1")
    parent = SimpleNamespace(checkpoint_id="parent-v1")
    child = SimpleNamespace(checkpoint_id="child-v1")
    config = ArenaConfig(
        pairs=pairs, nodes_per_move=17, max_depth=3, tt_megabytes=2,
        opening_seed=91, opening_count=pairs, min_plies=1, max_plies=2,
        workers=workers,
    )
    return arena_module, compiled, parent, child, config, openings


def test_resumable_arena_interrupts_then_executes_only_missing_pairs(
    monkeypatch, tmp_path
):
    arena_module, compiled, parent, child, config, openings = (
        _synthetic_resumable_inputs(monkeypatch)
    )
    calls = []

    def interrupted(*args):
        index = args[-1]
        calls.append(index)
        if index == 2:
            raise RuntimeError("simulated interruption")
        return _synthetic_pair(index)

    monkeypatch.setattr(arena_module, "_play_pair", interrupted)
    with pytest.raises(RuntimeError, match="simulated interruption"):
        run_arena_resumable(
            compiled, None, parent, child, config,
            progress_dir=tmp_path / "resume", openings=openings,
        )
    assert calls == [0, 1, 2]

    resumed_calls = []
    monkeypatch.setattr(
        arena_module, "_play_pair",
        lambda *args: resumed_calls.append(args[-1]) or _synthetic_pair(args[-1]),
    )
    resumed = run_arena_resumable(
        compiled, None, parent, child, config,
        progress_dir=tmp_path / "resume", openings=openings,
    )
    uninterrupted = run_arena_resumable(
        compiled, None, parent, child, config,
        progress_dir=tmp_path / "fresh", openings=openings,
    )

    assert resumed_calls[:2] == [2, 3]
    assert resumed == uninterrupted


def test_resumable_arena_rejects_identity_mismatch_corruption_and_half_pair(
    monkeypatch, tmp_path
):
    arena_module, compiled, parent, child, config, openings = (
        _synthetic_resumable_inputs(monkeypatch, pairs=1)
    )
    monkeypatch.setattr(
        arena_module, "_play_pair", lambda *args: _synthetic_pair(args[-1])
    )
    identity_dir = tmp_path / "identity"
    run_arena_resumable(
        compiled, None, parent, child, config,
        progress_dir=identity_dir, openings=openings,
    )
    manifest = json.loads(
        (identity_dir / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["identity"]["config"] == asdict(config)
    assert manifest["identity"]["ordered_openings"] == openings.to_dict()["openings"]
    with pytest.raises(ArenaExecutionError, match="identity"):
        run_arena_resumable(
            compiled, None, parent, child,
            replace(config, nodes_per_move=config.nodes_per_move + 1),
            progress_dir=identity_dir, openings=openings,
        )

    corrupt_dir = tmp_path / "corrupt"
    run_arena_resumable(
        compiled, None, parent, child, config,
        progress_dir=corrupt_dir, openings=openings,
    )
    (corrupt_dir / "pair-000000.json").write_text("{bad", encoding="utf-8")
    with pytest.raises(ArenaExecutionError, match="corrupt"):
        run_arena_resumable(
            compiled, None, parent, child, config,
            progress_dir=corrupt_dir, openings=openings,
        )

    half_dir = tmp_path / "half"
    run_arena_resumable(
        compiled, None, parent, child, config,
        progress_dir=half_dir, openings=openings,
    )
    pair_path = half_dir / "pair-000000.json"
    payload = json.loads(pair_path.read_text(encoding="utf-8"))
    del payload["game_child_owner1"]
    pair_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ArenaExecutionError, match="corrupt"):
        run_arena_resumable(
            compiled, None, parent, child, config,
            progress_dir=half_dir, openings=openings,
        )


def test_resumable_arena_concurrent_completion_order_is_deterministic(
    monkeypatch, tmp_path
):
    import time

    arena_module, compiled, parent, child, config, openings = (
        _synthetic_resumable_inputs(monkeypatch, pairs=6, workers=4)
    )

    def out_of_order(*args):
        index = args[-1]
        time.sleep((config.pairs - index) * 0.002)
        return _synthetic_pair(index)

    monkeypatch.setattr(arena_module, "_play_pair", out_of_order)
    first = run_arena_resumable(
        compiled, None, parent, child, config,
        progress_dir=tmp_path / "first", openings=openings,
    )
    second = run_arena_resumable(
        compiled, None, parent, child, config,
        progress_dir=tmp_path / "second", openings=openings,
    )
    assert first == second
    assert [pair.pair_index for pair in first.pairs] == list(range(config.pairs))


@requires_native
def test_resumable_arena_rejects_semantically_corrupted_game_by_replay(tmp_path):
    compiled, rules, checkpoint, child = _setup()
    config = ArenaConfig(pairs=1, nodes_per_move=200, max_depth=4)
    progress = tmp_path / "semantic-corruption"
    run_arena_resumable(
        compiled, rules, checkpoint, child, config, progress_dir=progress
    )
    pair_path = progress / "pair-000000.json"
    payload = json.loads(pair_path.read_text(encoding="utf-8"))
    game = payload["game_child_owner0"]
    game["final_position_key"] = "corrupted-final-position"
    pair_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ArenaExecutionError, match="does not replay"):
        run_arena_resumable(
            compiled, rules, checkpoint, child, config, progress_dir=progress
        )
