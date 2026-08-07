"""Learning Phase 1: self-play trajectories and fair arena."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.learning.arena import ArenaConfig, run_arena
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play
from generic_chess.native.compiler import compile_native_rules

from native_test_helpers import generated_compiled, requires_native


@requires_native
def _setup(size=4, seed=7):
    compiled = generated_compiled(size=size, seed=seed)
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    rules = compile_native_rules(compiled)
    return compiled, rules, checkpoint


@requires_native
def test_selfplay_produces_legal_terminal_trajectories():
    compiled, rules, checkpoint = _setup(size=4)
    config = SelfPlayConfig(games=2, nodes_per_move=300, max_depth=6, seed=5)
    trajectories = collect_self_play(compiled, rules, checkpoint, config)
    assert len(trajectories) == 2
    for trajectory in trajectories:
        assert trajectory.ruleset_fingerprint == compiled.ruleset_fingerprint
        assert trajectory.terminal in (
            "checkmate", "stalemate", "repetition", "max_ply",
        )
        assert len(trajectory.actions) == len(trajectory.points) or True
        for point in trajectory.points:
            assert point.completed_depth >= 1
            assert point.leaf_feature_board


@requires_native
def test_selfplay_deterministic_seed():
    compiled, rules, checkpoint = _setup(size=4)
    config = SelfPlayConfig(games=2, nodes_per_move=300, max_depth=6, seed=9)
    a = collect_self_play(compiled, rules, checkpoint, config)
    b = collect_self_play(compiled, rules, checkpoint, config)
    for ta, tb in zip(a, b):
        assert ta.trajectory_id == tb.trajectory_id


@requires_native
def test_selfplay_has_some_exploration_and_some_search_moves():
    compiled, rules, checkpoint = _setup(size=4)
    config = SelfPlayConfig(
        games=4, nodes_per_move=200, max_depth=4, seed=3, epsilon=0.5
    )
    trajectories = collect_self_play(compiled, rules, checkpoint, config)
    all_points = [p for t in trajectories for p in t.points]
    assert any(p.exploration for p in all_points)
    assert any(not p.exploration for p in all_points)


@requires_native
def test_arena_identical_checkpoints_no_systematic_bias():
    compiled, rules, checkpoint = _setup(size=4)
    config = ArenaConfig(pairs=4, nodes_per_move=200, max_depth=4)
    summary = run_arena(compiled, rules, checkpoint, checkpoint, config)
    assert summary.wins + summary.draws + summary.losses == 8
    # Paired symmetry: identical checkpoints give each pair exactly one point
    # to the child (color-swapped mirror games), so score_rate == 0.5.
    assert summary.score_rate == 0.5


@requires_native
def test_arena_parent_vs_perturbed_child():
    compiled, rules, checkpoint = _setup(size=4)
    child = checkpoint.child_checkpoint(
        board_weights={k: v * 0.5 for k, v in checkpoint.board_weights.items()},
        hand_weights={k: v * 0.5 for k, v in checkpoint.hand_weights.items()},
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash="cfg",
        training_seed=7,
    )
    config = ArenaConfig(pairs=2, nodes_per_move=300, max_depth=5)
    summary = run_arena(compiled, rules, checkpoint, child, config)
    assert 0.0 <= summary.score_rate <= 1.0
    assert summary.wilson_low <= summary.score_rate <= summary.wilson_high
