import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generic_chess.learning.material import LearnableMaterialCheckpoint

from f52_block_preconditioned_td_child_and_arena import (
    HOLDOUT_OFFSET,
    PRECONDITION_FRACTION,
    _holdout_records,
    precondition_td_direction,
)


def test_f52_uses_a_disjoint_holdout_after_f51_prefix():
    records = _holdout_records("A_CANONICAL_WESTERN_CHESS", 16)
    assert len(records) == 16
    assert HOLDOUT_OFFSET == 16


def test_f52_preserves_zero_gradient_blocks_and_scales_nonzero_block():
    parent = LearnableMaterialCheckpoint(
        ruleset_fingerprint="ruleset",
        evaluation_profile_version="profile",
        board_weights={"P": 10.0, "N": 20.0},
        hand_weights={"P": 5.0, "N": 5.0},
        dynamic_weights={"mobility": 2.0, "promotion_potential": 3.0, "anchor_safety": 5.0},
        reference_median=10.0,
        value_scale=40.0,
        w_max=1000.0,
    )
    direction = {
        "board": {"P": 3.0, "N": 4.0},
        "hand": {"P": 0.0, "N": 0.0},
        "dynamic": {"mobility": -2.0, "promotion_potential": 0.0, "anchor_safety": 0.0},
    }
    child = precondition_td_direction(parent, direction)
    board_delta = {
        key: child.board_weights[key] - parent.board_weights[key]
        for key in parent.board_weights
    }
    assert abs(sum(value * value for value in board_delta.values()) ** 0.5 - PRECONDITION_FRACTION * 10.0 * 5.0 ** 0.5) < 1e-9
    assert child.hand_weights == parent.hand_weights
    assert child.dynamic_weights["promotion_potential"] == parent.dynamic_weights["promotion_potential"]
    assert child.dynamic_weights["anchor_safety"] == parent.dynamic_weights["anchor_safety"]


def test_f52_child_is_a_new_checkpoint_with_parent_chain():
    parent = LearnableMaterialCheckpoint(
        ruleset_fingerprint="ruleset",
        evaluation_profile_version="profile",
        board_weights={"P": 10.0},
        hand_weights={"P": 5.0},
        dynamic_weights={"mobility": 2.0, "promotion_potential": 3.0, "anchor_safety": 5.0},
        reference_median=10.0,
        value_scale=40.0,
        w_max=1000.0,
    )
    child = precondition_td_direction(
        parent,
        {"board": {"P": 1.0}, "hand": {}, "dynamic": {}},
    )
    assert child.parent_checkpoint_id == parent.checkpoint_id
    assert child.generation == parent.generation + 1
    assert child.checkpoint_id != parent.checkpoint_id
