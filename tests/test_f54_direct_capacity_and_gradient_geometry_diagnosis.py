import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from f54_direct_capacity_and_gradient_geometry_diagnosis import (  # noqa: E402
    DIAGNOSTIC_FRACTION,
    _metrics,
    _ridge_fit,
)


def test_f54_ridge_recovers_regularized_linear_residual_direction():
    features = np.asarray([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    target = np.asarray([2.0, -1.0, 1.0])
    beta = _ridge_fit(features, target, alpha=1e-9)
    assert beta == pytest.approx([2.0, -1.0], abs=1e-5)


def test_f54_metrics_reports_perfect_value_fit():
    values = np.asarray([0.0, 1.0, -2.0])
    assert _metrics(values, values)["mse"] == pytest.approx(0.0)
    assert _metrics(values, values)["correlation"] == pytest.approx(1.0)


def test_f54_reuses_common_frozen_diagnostic_magnitude():
    assert DIAGNOSTIC_FRACTION == 0.0005
