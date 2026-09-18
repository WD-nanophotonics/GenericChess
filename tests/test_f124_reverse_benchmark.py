from __future__ import annotations

import numpy as np

from scripts.f124_reverse_benchmark_stable_convex_solver import _pcg


def test_pcg_converges_from_zero_on_regularized_normal_system():
    design = np.asarray([[0.0, 1.0], [1.0, 1.0], [2.0, 1.0]], dtype=np.float64)
    target = np.asarray([0.0, 1.0, 2.0], dtype=np.float64)
    pack = {
        "design": {"train": design},
        "target": {"train": target},
    }

    model, trace = _pcg(pack)
    hessian = design.T @ design / len(design)
    hessian[0, 0] += 1e-6
    rhs = design.T @ target / len(design)

    np.testing.assert_allclose(hessian @ model, rhs, rtol=0.0, atol=1e-10)
    assert trace["iterations"] > 0
    assert trace["relative_residual"] <= 1e-10
    assert trace["iterations"] <= 4 * design.shape[1]
