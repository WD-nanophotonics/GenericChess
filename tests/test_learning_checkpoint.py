"""Learning Phase 1: checkpoint, trajectory serialization, determinism."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.serialization import stable_sha256
from generic_chess.learning.trajectory import (
    TrainingPoint,
    TrainingTrajectory,
)

from native_test_helpers import generated_compiled


def _checkpoint(compiled, generation=0, parent=None, seed=7):
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    return LearnableMaterialCheckpoint.from_profile(
        compiled,
        profile,
        training_seed=seed,
        generation=generation,
        parent_checkpoint_id=parent,
    )


def test_checkpoint_id_is_deterministic_and_sha256():
    compiled = generated_compiled(size=4)
    a = _checkpoint(compiled)
    b = _checkpoint(compiled)
    assert a.checkpoint_id == b.checkpoint_id
    assert len(a.checkpoint_id) == 64
    assert a.checkpoint_id != stable_sha256({"different": True})


def test_checkpoint_roundtrip_and_wrong_ruleset_rejected():
    compiled = generated_compiled(size=4)
    cp = _checkpoint(compiled)
    data = cp.to_dict()
    restored = LearnableMaterialCheckpoint.from_dict(data)
    assert restored.to_dict() == data
    assert restored.checkpoint_id == cp.checkpoint_id
    other = generated_compiled(size=6, seed=11)
    with pytest.raises(ValueError):
        restored.validate_ruleset(other)
    restored.validate_ruleset(compiled)


def test_generation_chain():
    compiled = generated_compiled(size=4)
    g0 = _checkpoint(compiled, generation=0)
    g1 = g0.child_checkpoint(
        board_weights={k: v + 1 for k, v in g0.board_weights.items()},
        hand_weights={k: v + 1 for k, v in g0.hand_weights.items()},
        games_seen_delta=8,
        positions_seen_delta=40,
        training_updates_delta=1,
        training_config_hash="cfg",
        training_seed=7,
    )
    assert g1.generation == 1
    assert g1.parent_checkpoint_id == g0.checkpoint_id
    assert g1.games_seen == 8
    g2 = g1.child_checkpoint(
        board_weights={k: v + 1 for k, v in g1.board_weights.items()},
        hand_weights={k: v + 1 for k, v in g1.hand_weights.items()},
        games_seen_delta=4,
        positions_seen_delta=20,
        training_updates_delta=1,
        training_config_hash="cfg",
        training_seed=7,
    )
    assert g2.parent_checkpoint_id == g1.checkpoint_id
    assert g2.generation == 2
    assert g2.games_seen == 12
    # Save/load Gen1 then continue to Gen2.
    restored = LearnableMaterialCheckpoint.from_dict(g1.to_dict())
    g2b = restored.child_checkpoint(
        board_weights={k: v + 1 for k, v in restored.board_weights.items()},
        hand_weights={k: v + 1 for k, v in restored.hand_weights.items()},
        games_seen_delta=4,
        positions_seen_delta=20,
        training_updates_delta=1,
        training_config_hash="cfg",
        training_seed=7,
    )
    assert g2b.checkpoint_id == g2.checkpoint_id


def test_trajectory_roundtrip_and_feature_equality():
    trajectory = TrainingTrajectory(
        ruleset_fingerprint="fp",
        generation=0,
        game_seed=3,
        initial_position_key="init",
        actions=(),
        search_nodes=100,
        search_max_depth=6,
        terminal="checkmate",
        winner=0,
        type_ids=("P", "Q"),
        points=(
            TrainingPoint(
                ply=0,
                root_position_key="r0",
                action=None,
                exploration=False,
                pv=(),
                leaf_position_key="l0",
                leaf_feature_board=(1, 0),
                leaf_feature_hand=(0, 1),
                leaf_value=0.3,
                completed_depth=2,
            ),
        ),
    )
    restored = TrainingTrajectory.from_dict(trajectory.to_dict())
    assert restored.to_dict() == trajectory.to_dict()
    assert restored.trajectory_id == trajectory.trajectory_id
    features = restored.leaf_features_at(restored.points[0])
    assert features.board_counts == (1, 0)
    assert features.hand_counts == (0, 1)
