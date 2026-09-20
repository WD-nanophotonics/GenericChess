import numpy as np

from scripts.f139_corrected_shogi_rank_complete_a1 import BASELINE, F138_COUNTS, _rank_complete


def test_f139_baseline_and_dimension_contract():
    assert BASELINE == "ca19e3257b51cb6bdce6eb49e5692f51c1c15ce2"
    assert F138_COUNTS == {"candidate": 6125, "inspected": 37066, "trajectories": 342, "selected": 25}


def test_f139_rank_completion_adds_only_independent_rows():
    design = np.asarray([[0.0, 0.0, 1.0], [1.0, 0.0, 1.0]], dtype=np.float64)
    pack = {
        "design": {"train": design},
        "feature_mean": np.zeros(2),
        "feature_scale": np.ones(2),
        "active": np.asarray([True, True]),
    }
    candidates = [
        {"features": [0.0, 1.0], "identity": "b", "trajectory": 1, "ply": 1},
        {"features": [0.0, 1.0], "identity": "a", "trajectory": 1, "ply": 1},
    ]
    selected, capacity = _rank_complete(pack, candidates, 3)
    assert len(selected) == 1
    assert selected[0]["identity"] == "a"
    assert capacity["attainable_rank"] == 3
