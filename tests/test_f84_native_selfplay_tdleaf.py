from dataclasses import asdict

from generic_chess.learning.selfplay import SelfPlayConfig
from generic_chess.learning.tdleaf import TDLeafConfig
from scripts.f84_native_selfplay_tdleaf import WORK_ORDER


def test_f84_uses_default_native_learning_parameters_for_one_game():
    config = SelfPlayConfig(games=1, seed=840401)
    assert WORK_ORDER == "F84_NATIVE_SELFPLAY_TDLEAF_SINGLE_UPDATE"
    assert asdict(config) == {
        "games": 1,
        "nodes_per_move": 3000,
        "max_depth": 12,
        "seed": 840401,
        "epsilon": 0.10,
        "tt_megabytes": 8,
        "max_plies": None,
    }
    assert asdict(TDLeafConfig()) == {"gamma": 1.0, "lambd": 0.7, "alpha": None, "value_scale": None}
