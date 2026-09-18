from __future__ import annotations

import numpy as np

from scripts.f123_reverse_benchmark_identifiability_optimizer_diagnosis import (
    _adam,
    _matched_ridge,
    _minimum_norm,
)


def _pack(design: np.ndarray, target: np.ndarray) -> dict:
    left_vectors, singular_values, vt = np.linalg.svd(design, full_matrices=False)
    tolerance = np.finfo(np.float64).eps * max(design.shape) * singular_values[0]
    retained = singular_values > tolerance
    return {
        "design": {"train": design, "dev": design, "holdout": design},
        "target": {"train": target, "dev": target, "holdout": target},
        "oracle": {"train": target, "dev": target, "holdout": target},
        "target_mean": 0.0,
        "target_std": 1.0,
        "singular_values": singular_values,
        "left_vectors": left_vectors,
        "vt": vt,
        "retained": retained,
    }


def test_minimum_norm_solves_rank_deficient_system_with_minimum_parameter_norm():
    design = np.asarray([[1.0, 1.0], [2.0, 2.0]])
    target = np.asarray([1.0, 2.0])
    model = _minimum_norm(_pack(design, target))

    np.testing.assert_allclose(design @ model, target)
    np.testing.assert_allclose(model, np.asarray([0.5, 0.5]))


def test_matched_ridge_uses_mean_loss_lambda_convention_and_leaves_intercept_unregularized():
    design = np.asarray([[0.0, 1.0], [1.0, 1.0], [2.0, 1.0]])
    target = np.asarray([0.0, 1.0, 2.0])
    pack = _pack(design, target)
    model = _matched_ridge(pack)

    gram = design.T @ design / len(design)
    gram[0, 0] += 1e-6
    expected = np.linalg.solve(gram, design.T @ target / len(design))
    np.testing.assert_allclose(model, expected)


def test_adam_emits_all_required_2k_checkpoints():
    design = np.asarray([[0.0, 1.0], [1.0, 1.0], [2.0, 1.0]])
    target = np.asarray([0.0, 1.0, 2.0])
    _, trace = _adam(_pack(design, target), seed=1220111, steps=2000, zero_init=False)

    assert list(trace) == ["0", "10", "100", "500", "1000", "2000"]
    assert trace["2000"]["objective"] < trace["0"]["objective"]
    assert all("gradient_l2" in checkpoint for checkpoint in trace.values())
