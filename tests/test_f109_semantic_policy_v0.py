import numpy as np
import pytest

from generic_chess.core.semantic_executor import semantic_engine_for, semantic_public_actions
from generic_chess.learning.policy import (
    ACTION_FEATURE_WIDTH,
    SemanticPolicyExample,
    SemanticPolicyV0,
    fit_semantic_policy_v0,
    policy_target_from_q,
    semantic_action_features,
    semantic_state_feature_vector,
)
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.ai.limits import SearchLimits


def _western_root():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    position = GameSession(compiled).state.position
    actions = semantic_public_actions(semantic_engine_for(compiled), position)
    return compiled, position, actions


def test_f109_action_encoding_is_fixed_numeric_and_semantic():
    compiled, position, actions = _western_root()
    encoded = [semantic_action_features(compiled, position, action) for action in actions]
    assert encoded
    assert all(vector.shape == (ACTION_FEATURE_WIDTH,) for vector in encoded)
    assert all(vector.dtype == np.float64 for vector in encoded)
    assert all(np.all(np.isfinite(vector)) for vector in encoded)
    # The source text of a pattern/geometry identity cannot affect the vector.
    first = actions[0]
    renamed = type(first)(
        pattern_id="unrelated_label",
        geometry_id="another_label",
        actor_type_id=first.actor_type_id,
        from_square=first.from_square,
        to_square=first.to_square,
        promotion_target_id=first.promotion_target_id,
    )
    with pytest.raises(ValueError):
        semantic_action_features(compiled, position, renamed)


def test_f109_q_target_uses_complete_vector_and_iqr_scale():
    target = policy_target_from_q((0.0, 1.0, 2.0, 10.0))
    assert target.shape == (4,)
    assert np.isclose(np.sum(target), 1.0)
    assert target[-1] > target[-2] > target[0]
    assert np.all(policy_target_from_q((3.0, 3.0, 3.0)) > 0.0)


def test_f109_policy_training_is_deterministic_and_roundtrips_exactly():
    examples = (
        SemanticPolicyExample(
            state=(0.0, 1.0, 0.5),
            actions=((1.0,) + (0.0,) * 23, (0.0, 1.0) + (0.0,) * 22),
            target=(0.8, 0.2),
        ),
        SemanticPolicyExample(
            state=(1.0, 0.0, -0.5),
            actions=((0.0, 1.0) + (0.0,) * 22, (1.0,) + (0.0,) * 23),
            target=(0.3, 0.7),
        ),
    )
    kwargs = dict(ruleset_fingerprint="fingerprint", corpus_config={"games": 8}, seed=1090111)
    model_a = fit_semantic_policy_v0(examples, **kwargs)
    model_b = fit_semantic_policy_v0(examples, **kwargs)
    assert model_a.to_dict() == model_b.to_dict()
    restored = SemanticPolicyV0.from_dict(model_a.to_dict())
    state = examples[0].state
    actions = examples[0].actions
    assert np.array_equal(model_a.logits(state, actions), restored.logits(state, actions))
    assert restored.computed_model_sha256 == model_a.to_dict()["model_sha256"]


def test_f109_policy_training_rejects_partial_or_wrong_hyperparameter_contract():
    example = SemanticPolicyExample(
        state=(0.0,), actions=((0.0,) * ACTION_FEATURE_WIDTH,), target=(1.0,)
    )
    with pytest.raises(ValueError, match="400 Adam steps"):
        fit_semantic_policy_v0((example,), ruleset_fingerprint="x", corpus_config={}, seed=1, steps=1)
    with pytest.raises(ValueError, match="every legal action"):
        SemanticPolicyExample(
            state=(0.0,), actions=((0.0,) * ACTION_FEATURE_WIDTH, (0.0,) * ACTION_FEATURE_WIDTH), target=(1.0,)
        ).arrays()


def test_f109_native_policy_fixed_depth_and_state_inference_metrics():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    native_rules = compile_native_semantic_rules(compiled)
    session = GameSession(compiled)
    state = semantic_state_feature_vector(session.state.position, compiled, (0, 0, 0))
    example = SemanticPolicyExample(
        state=tuple(state),
        actions=(tuple(np.zeros(ACTION_FEATURE_WIDTH)), tuple(np.zeros(ACTION_FEATURE_WIDTH))),
        target=(0.5, 0.5),
    )
    model = fit_semantic_policy_v0(
        (example,), ruleset_fingerprint=compiled.ruleset_fingerprint,
        corpus_config={}, seed=1090111,
        hand_type_indices=tuple(range(len(compiled._legacy_compiled.piece_types))),
    )
    engine = SemanticSearchEngine(compiled, native_rules, tt_megabytes=0, policy=model)
    shallow = engine.search(
        session, SearchLimits(max_depth=1, max_nodes=100, quiescence_max_depth=0,
                              quiescence_hard_max_depth=0)
    )
    assert shallow.policy_ordering is True
    assert shallow.policy_nodes == 0
    deep = engine.search(
        session, SearchLimits(max_depth=2, max_nodes=1000, quiescence_max_depth=0,
                              quiescence_hard_max_depth=0)
    )
    assert deep.policy_nodes > 0
    assert deep.policy_state_inferences == deep.policy_nodes
    assert deep.policy_actions_scored > 0
