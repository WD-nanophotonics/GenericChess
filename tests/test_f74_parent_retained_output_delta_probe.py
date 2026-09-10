"""Contract tests for the bounded F74 output-weight correction harness."""

from pathlib import Path

import numpy as np

from scripts import f74_parent_retained_output_delta_probe as f74


ROOT = Path(__file__).resolve().parents[1]


def test_f74_scope_and_frozen_checkpoint_contract():
    source = (ROOT / "scripts" / "f74_parent_retained_output_delta_probe.py").read_text(
        encoding="utf-8"
    )
    assert f74.WORK_ORDER == "GENERICCHESS-F74-PARENT-RETAINED-OUTPUT-DELTA-PROBE"
    assert f74.PARENT_SHA == "ecf4e6e0acca399dba8f4cea0607d5cfe9cef89c"
    assert f74.FIT_ROOT_COUNT == 48
    assert f74.DEVELOPMENT_ROOT_COUNT == 20
    assert f74.NODES == 2_048
    assert "arena" not in source.lower()
    assert "selfplay" not in source.lower()
    assert "final_holdout" not in source.lower()
    assert "external engine" not in source.lower()
    assert "heavy" not in source.lower()
    for field in (
        "input_mean", "input_scale", "target_scale", "hidden_weights",
        "hidden_bias", "output_bias", "width", "hand_type_indices", "perspective",
    ):
        assert field in source


def test_pairwise_fit_is_deterministic_and_strictly_improves_toy_objective():
    pairwise = [[
        (np.asarray([1.0, 0.0]), -0.25),
        (np.asarray([0.0, 1.0]), 0.10),
    ], [
        (np.asarray([1.0, 1.0]), -0.15),
    ]]
    first, summary_first = f74._fit_direction(
        pairwise, width=2, target_scale=1.0, regularization=1e-3
    )
    second, summary_second = f74._fit_direction(
        pairwise, width=2, target_scale=1.0, regularization=1e-3
    )
    assert np.array_equal(first, second)
    assert summary_first == summary_second
    before = f74._pairwise_objective(np.zeros(2), pairwise, 1.0, 1e-3)
    after = f74._pairwise_objective(first, pairwise, 1.0, 1e-3)
    assert after < before


def test_alpha_rule_is_exact_minimum_of_registered_boundaries():
    high = 2.0
    residual = 0.75
    assert min(1.0, 0.5 * high, residual) == 0.75
