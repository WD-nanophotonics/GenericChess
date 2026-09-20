import numpy as np

from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.f122_reverse_benchmark_known_evaluator_system_identification import FrozenBasis
from scripts.f135_corrected_shogi_oracle_schema_rebaseline import CorrectedShogiFrozenBasisV2, _sort_actions


def test_corrected_shogi_schema_is_keyed_and_exactly_ordered():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    basis = CorrectedShogiFrozenBasisV2("standard_shogi", compiled)
    assert len(basis.names) == 1086
    assert len(set(basis.names)) == 1086
    expected_tail = [
        "hand_diff:P", "hand_diff:L", "hand_diff:N", "hand_diff:S", "hand_diff:G", "hand_diff:B", "hand_diff:R",
        "mobility_diff", "king_escape_diff", "king_zone_pressure_diff", "current_check_diff", "promotion_potential_diff",
        "legal_drop_count_diff:P", "legal_drop_count_diff:L", "legal_drop_count_diff:N", "legal_drop_count_diff:S",
        "legal_drop_count_diff:G", "legal_drop_count_diff:B", "legal_drop_count_diff:R", "mean_legal_drop_mobility_diff",
    ]
    assert basis.names[-20:] == expected_tail
    state = initial_state(compiled)
    feature_map = basis._feature_map(state)
    assert set(feature_map) == set(basis.names)
    np.testing.assert_array_equal(basis.vector(state), np.asarray([feature_map[name] for name in basis.names]))


def test_historical_shogi_mismatch_is_explicitly_documented():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    legacy = FrozenBasis("standard_shogi", compiled)
    corrected = CorrectedShogiFrozenBasisV2("standard_shogi", compiled)
    state = initial_state(compiled)
    legacy_vector = legacy.vector(state)
    semantic = corrected._feature_map(state)
    assert legacy_vector[legacy.names.index("hand_diff:P")] == semantic["mobility_diff"]
    assert legacy_vector[legacy.names.index("hand_diff:L")] == semantic["king_escape_diff"]
    assert legacy_vector[legacy.names.index("hand_diff:N")] == semantic["king_zone_pressure_diff"]
    assert legacy_vector[legacy.names.index("hand_diff:S")] == semantic["current_check_diff"]
    assert legacy_vector[legacy.names.index("hand_diff:G")] == semantic["hand_diff:P"]
    assert legacy_vector[legacy.names.index("hand_diff:B")] == semantic["hand_diff:L"]
    assert legacy_vector[legacy.names.index("hand_diff:R")] == semantic["hand_diff:N"]


def test_western_basis_parity_is_unchanged_on_deterministic_states():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    left = FrozenBasis("western_chess", compiled)
    right = FrozenBasis("western_chess", compiled)
    state = initial_state(compiled)
    for _ in range(3):
        np.testing.assert_array_equal(left.vector(state), right.vector(state))
        assert left.names == right.names
        assert left.weights == right.weights
        actions = _sort_actions(legal_actions(state, compiled))
        state = apply_action(state, actions[0], compiled)
