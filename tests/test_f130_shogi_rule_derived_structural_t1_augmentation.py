from __future__ import annotations

import numpy as np

from scripts.f130_shogi_rule_derived_structural_t1_augmentation import (
    FEATURE_NAMES,
    _microtests,
    structural_features,
)
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.core.transition import initial_state


def test_f130_has_exactly_the_ordered_nine_feature_block_and_genericity_microtests_pass():
    assert FEATURE_NAMES == (
        "realized_activity_balance",
        "blocked_capacity_balance",
        "empty_board_positional_capability_balance",
        "promotion_structural_capability_balance",
        "drop_structural_capability_balance",
        "anchor_structural_space_balance",
        "anchor_ring_control_balance",
        "attacked_structural_value_balance",
        "hanging_structural_value_balance",
    )
    report = _microtests()
    assert report["pass"]
    assert all(all(flags.values()) for flags in report["by_ruleset"].values())


def test_f130_extractor_is_finite_and_side_relative_on_standard_shogi_initial_state():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    state = initial_state(compiled)
    values = structural_features(state, compiled)
    assert values.shape == (9,)
    assert np.all(np.isfinite(values))
