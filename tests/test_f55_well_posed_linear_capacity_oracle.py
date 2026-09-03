import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from f55_well_posed_linear_capacity_oracle import (  # noqa: E402
    ALPHA_GRID,
    CV_FOLDS,
    MATE_BAND_NATIVE_THRESHOLD,
    _conditioning,
    _cv_select_alpha,
    _ridge_svd,
    _training_scale,
)


def test_f55_svd_ridge_handles_singular_design_without_gram_inverse():
    features = np.asarray([[1.0, 2.0], [2.0, 4.0], [3.0, 6.0]])
    target = np.asarray([1.0, 2.0, 3.0])
    beta = _ridge_svd(features, target, alpha=1e-6)
    assert np.all(np.isfinite(beta))
    assert features @ beta == pytest.approx(target, abs=1e-5)


def test_f55_training_scale_freezes_constant_coordinates():
    features = np.asarray([[1.0, 0.0], [2.0, 0.0], [3.0, 0.0]])
    active, scale, _std = _training_scale(features)
    assert active.tolist() == [True, False]
    assert scale.tolist() == pytest.approx([np.sqrt(14 / 3)])


def test_f55_alpha_selection_is_training_only_and_deterministic():
    features = np.asarray([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 1.0], [1.0, 2.0], [2.0, 2.0], [3.0, 1.0], [1.0, 3.0]])
    target = np.asarray([1.0, -1.0, 0.0, 1.0, -1.0, 0.0, 2.0, -2.0])
    selected_a, rows_a = _cv_select_alpha(features, target)
    selected_b, rows_b = _cv_select_alpha(features, target)
    assert selected_a == selected_b
    assert rows_a == rows_b
    assert selected_a in ALPHA_GRID
    assert len(rows_a) == len(ALPHA_GRID)
    assert CV_FOLDS == 4


def test_f55_conditioning_reports_rank_and_scaling_contract():
    report = _conditioning(np.asarray([[1.0, 2.0], [2.0, 4.0], [3.0, 6.0]]))
    assert report["rank"] == 1
    assert report["condition_number"] is None


def test_f55_mate_band_is_native_score_contract():
    assert MATE_BAND_NATIVE_THRESHOLD == 90_000_000
