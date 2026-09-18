"""Focused invariants for the F122 benchmark-only harness."""

from __future__ import annotations

import numpy as np

from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset

from scripts.f122_reverse_benchmark_known_evaluator_system_identification import (
    FrozenBasis,
    _fit,
    _rankdata,
)


def test_f122_frozen_basis_is_deterministic_for_both_canonical_rulesets():
    for family, builder in (
        ("western_chess", build_western_chess_ruleset),
        ("standard_shogi", build_standard_shogi_ruleset),
    ):
        compiled = compile_semantic_ruleset(builder())
        first = FrozenBasis(family, compiled)
        second = FrozenBasis(family, compiled)
        state = initial_state(compiled)
        vector = first.vector(state)
        assert len(vector) == len(first.names) == len(first.weights)
        assert first.oracle_weight_sha256 == second.oracle_weight_sha256
        assert np.array_equal(vector, second.vector(state))
        assert legal_actions(state, compiled)


def test_f122_fit_drops_constant_train_features_and_keeps_closed_form_diagnostic():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    basis = FrozenBasis("western_chess", compiled)
    rng = np.random.default_rng(1220999)
    raw = rng.normal(size=(4500, len(basis.names)))
    raw[:, 0] = 3.0
    weights = np.arange(len(basis.names), dtype=np.float64) / 11.0
    rows = [
        {"identity": str(index), "features": row.tolist(), "oracle": float(row @ weights)}
        for index, row in enumerate(raw)
    ]
    fit = _fit(rows, basis, 1220111)
    assert basis.names[0] in fit["constant_feature_names"]
    assert fit["adam_model"].shape == fit["closed_model"].shape
    assert fit["adam_model"].shape[0] == len(basis.names)  # only the intercept is added
    assert fit["random_model"].shape == fit["adam_model"].shape
    assert fit["random_seed"] == 1221111
    assert np.isfinite(fit["closed_predict"]((raw[-750:] - fit["mean"]) / fit["scale"])).all()


def test_f122_rankdata_uses_average_ranks_for_ties():
    assert np.array_equal(_rankdata(np.asarray([3.0, 1.0, 1.0, 4.0])), np.asarray([3.0, 1.5, 1.5, 4.0]))


def test_f122_child_feature_vector_is_available_after_a_legal_transition():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    basis = FrozenBasis("standard_shogi", compiled)
    state = initial_state(compiled)
    action = legal_actions(state, compiled)[0]
    child = apply_action(state, action, compiled)
    assert basis.vector(child).shape == basis.vector(state).shape
    assert np.isfinite(basis.oracle(basis.vector(child)))
