from __future__ import annotations

import numpy as np

from scripts.f132_shogi_action_residual_causal_decomposition import _family, _rank, _summary


def test_f132_assigns_every_f122_feature_family_without_invented_names():
    names = (
        "material_diff:P",
        "occupancy_diff:P:0:0",
        "mobility_diff",
        "king_escape_diff",
        "hand_diff:P",
        "promotion_potential_diff",
        "legal_drop_count_diff:P",
        "mean_legal_drop_mobility_diff",
        "unclassified_feature",
    )
    assert [_family(name) for name in names] == [
        "material_board", "piece_square", "mobility", "king_safety",
        "hand_inventory", "promotion", "drop_opportunity", "drop_opportunity", "other",
    ]


def test_f132_diagnostics_are_deterministic_for_a_toy_residual():
    target = np.asarray([0.0, 1.0, 2.0])
    predicted = np.asarray([0.1, 0.9, 2.2])
    summary = _summary(predicted, target, np.ones(3))
    assert np.isclose(summary["rmse"], np.sqrt((0.01 + 0.01 + 0.04) / 3.0))
    assert -1.0 <= summary["pearson_predicted_vs_true"] <= 1.0
    assert _rank([0.1, 0.9, 2.2], [0.0, 1.0, 2.0])[0] == 1
