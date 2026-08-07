"""Learning Phase 1: checkpoint/material baseline equality and quantization."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.native_compat import evaluate_native_reference
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.learning.features import linear_value, material_features
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_rules

from native_test_helpers import generated_compiled, make_state, requires_native


def _setup():
    compiled = generated_compiled(size=4)
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    checkpoint = LearnableMaterialCheckpoint.from_profile(compiled, profile)
    return compiled, profile, checkpoint


def test_gen0_matches_native_compatible_evaluator():
    compiled, profile, checkpoint = _setup()
    state = make_state(compiled, compiled.initial_position)
    features = material_features(
        state.position,
        tuple(sorted(
            pt.type_id for pt in compiled.piece_types if not pt.is_anchor
        )),
        perspective=0,
    )
    v = linear_value(
        features, checkpoint.board_weights, checkpoint.hand_weights
    )
    reference = evaluate_native_reference(state, compiled, profile)
    assert abs(v - reference) < 1e-6


@requires_native
def test_quantized_native_matches_baseline():
    compiled, profile, checkpoint = _setup()
    rules = compile_native_rules(compiled)
    board = checkpoint.quantized_board(rules.type_ids)
    hand = checkpoint.quantized_hand(rules.type_ids)
    for tid, expected in profile.board_value_by_type.items():
        assert board[rules.type_map[tid]] == expected
    for tid, expected in profile.hand_value_by_base_type.items():
        assert hand[rules.type_map[tid]] == expected


def test_anchor_weights_zero_and_not_learnable():
    compiled, profile, checkpoint = _setup()
    anchor_ids = {
        pt.type_id for pt in compiled.piece_types if pt.is_anchor
    }
    assert anchor_ids
    for tid in anchor_ids:
        assert tid not in checkpoint.board_weights
        assert tid not in checkpoint.hand_weights
        assert checkpoint.native_board_value(tid) == 0


def test_normalization_keeps_median():
    compiled, profile, checkpoint = _setup()
    checkpoint2 = LearnableMaterialCheckpoint(
        ruleset_fingerprint=checkpoint.ruleset_fingerprint,
        evaluation_profile_version=checkpoint.evaluation_profile_version,
        generation=1,
        parent_checkpoint_id=checkpoint.checkpoint_id,
        created_at=checkpoint.created_at,
        board_weights={k: v * 2.0 for k, v in checkpoint.board_weights.items()},
        hand_weights={k: v * 2.0 for k, v in checkpoint.hand_weights.items()},
        value_scale=checkpoint.value_scale,
        w_max=checkpoint.w_max,
    )
    checkpoint2.normalize_and_clip()
    values = list(checkpoint2.board_weights.values())
    med = sorted(abs(v) for v in values)[len(values) // 2]
    assert abs(med - checkpoint.value_scale / 4.0) < 1e-6


def test_normalization_rejects_collapse():
    from generic_chess.learning.material import LearningNumericalError

    compiled, profile, checkpoint = _setup()
    checkpoint2 = LearnableMaterialCheckpoint(
        ruleset_fingerprint=checkpoint.ruleset_fingerprint,
        evaluation_profile_version=checkpoint.evaluation_profile_version,
        generation=1,
        parent_checkpoint_id=None,
        created_at=checkpoint.created_at,
        board_weights={k: 0.0 for k in checkpoint.board_weights},
        hand_weights={k: 0.0 for k in checkpoint.hand_weights},
        value_scale=checkpoint.value_scale,
        w_max=checkpoint.w_max,
    )
    with pytest.raises(LearningNumericalError):
        checkpoint2.normalize_and_clip()
