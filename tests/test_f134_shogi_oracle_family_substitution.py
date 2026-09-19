from __future__ import annotations

import numpy as np

from scripts.f134_shogi_oracle_family_substitution import FAMILIES, _report, _weighted_metrics


def test_family_set_is_frozen():
    assert FAMILIES == ("material_board", "piece_square", "mobility", "king_safety", "hand_inventory", "promotion", "drop_opportunity", "other")


def test_weighted_metrics_perfect_prediction():
    target = np.asarray([1.0, 2.0, 4.0])
    weights = np.asarray([1.0, 2.0, 1.0])
    report = _weighted_metrics(target, target.copy(), weights, 1.0)
    assert report["weighted_rmse"] == 0.0
    assert report["r2"] == 1.0
    assert report["pearson"] == 1.0
    assert report["spearman"] == 1.0


def test_exact_action_report_is_perfect():
    rows = []
    predictions = []
    for root_index, values in enumerate(((0.0, 10.0), (4.0, 2.0))):
        for action_index, value in enumerate(values):
            rows.append({"split": "holdout", "root_identity": f"root-{root_index}", "q": value, "v_star": 100.0, "weight": 0.5})
            predictions.append(value - 100.0)
    report = _report(rows, np.asarray(predictions), 1.0)
    assert report["top1"] == 1.0
    assert report["pairwise"] == 1.0
    assert report["mean_regret"] == 0.0
    assert report["t1_rmse"] == 0.0
