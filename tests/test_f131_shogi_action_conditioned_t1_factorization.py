from __future__ import annotations

import numpy as np

from scripts.f131_shogi_action_conditioned_t1_factorization import (
    FEATURE_NAMES,
    _microtests,
    action_features,
)
from generic_chess.core.semantic_executor import semantic_engine_for, semantic_public_actions
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


def test_f131_action_feature_contract_is_exactly_42_and_genericity_passes():
    assert len(FEATURE_NAMES) == 42
    assert _microtests()["pass"]


def test_f131_action_features_are_finite_for_a_complete_legal_action_set():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    state = initial_state(compiled)
    actions = semantic_public_actions(semantic_engine_for(compiled), state.position)
    vectors = np.asarray([action_features(state, action, compiled) for action in actions])
    assert vectors.shape == (len(actions), 42)
    assert np.all(np.isfinite(vectors))
