"""Learning Phase 1.5: arena measurement integrity gates."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.learning.arena import (
    ArenaConfig,
    ArenaExecutionError,
    run_arena,
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
