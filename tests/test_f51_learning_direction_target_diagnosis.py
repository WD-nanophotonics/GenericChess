"""F51 direction normalization contracts."""

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from f50_generic_learnable_evaluator import WEIGHTS
from f51_learning_direction_target_diagnosis import (
    _action_key,
    _cosine,
    _direction,
    _scaled_direction_checkpoint,
)
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


def _parent():
    ruleset = build_western_chess_ruleset()
    compiled = compile_semantic_ruleset(ruleset)
    profile = build_ruleset_profile(compile_ruleset_for_execution(ruleset), EvaluationConfig())
    return LearnableMaterialCheckpoint.from_profile(compiled, profile, dynamic_weights=dict(WEIGHTS))


def test_td_direction_is_scaled_by_block_norm_not_tiny_natural_step():
    parent = _parent()
    child = replace(parent, dynamic_weights={
        key: value + delta
        for key, value, delta in (("mobility", 2.0, -0.002), ("promotion_potential", 3.0, 0.0001), ("anchor_safety", 5.0, -0.0008))
    })
    direction = _direction(parent, child)
    candidate = _scaled_direction_checkpoint(parent, direction, 0.05)
    actual_norm = sum((candidate.dynamic_weights[name] - parent.dynamic_weights[name]) ** 2 for name in WEIGHTS) ** 0.5
    expected_norm = 0.05 * sum(value * value for value in parent.dynamic_weights.values()) ** 0.5
    assert abs(actual_norm - expected_norm) < 1e-12
    assert actual_norm > sum(value * value for value in direction["dynamic"].values()) ** 0.5


def test_cosine_reports_alignment_and_zero_vectors_as_none():
    assert _cosine([1.0, 0.0], [2.0, 0.0]) == 1.0
    assert _cosine([1.0, 0.0], [-2.0, 0.0]) == -1.0
    assert _cosine([0.0], [1.0]) is None


def test_action_key_normalizes_teacher_json_and_candidate_dict():
    action = {"to": [1, 2], "from": [0, 0], "kind": "semantic_board"}
    assert _action_key(action) == _action_key('{"kind":"semantic_board","from":[0,0],"to":[1,2]}')
    assert _action_key(action) != _action_key('{"kind":"semantic_board","from":[0,0],"to":[1,3]}')
