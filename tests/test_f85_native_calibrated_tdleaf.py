from dataclasses import asdict

from generic_chess.learning.selfplay import SelfPlayConfig
from generic_chess.learning.tdleaf import TDLeafConfig
from scripts.f85_native_calibrated_tdleaf import WORK_ORDER


def test_f85_contract_is_single_bounded_trajectory_and_calibrated_update():
    assert WORK_ORDER == "F85_NATIVE_CALIBRATED_TDLEAF_SINGLE_UPDATE"
    assert asdict(SelfPlayConfig(games=1, nodes_per_move=512, max_depth=12, seed=840401, epsilon=0.10, tt_megabytes=8, max_plies=64)) == {
        "games": 1, "nodes_per_move": 512, "max_depth": 12, "seed": 840401,
        "epsilon": 0.10, "tt_megabytes": 8, "max_plies": 64,
    }
    assert asdict(TDLeafConfig()) == {"gamma": 1.0, "lambd": 0.7, "alpha": None, "value_scale": None}
    calibrated = TDLeafConfig(gamma=1.0, lambd=0.7, alpha=1.0, value_scale=None)
    assert calibrated.gamma == 1.0 and calibrated.lambd == 0.7 and calibrated.value_scale is None


def test_f85_artifact_if_present_records_calibration_and_change():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    path = root / "artifacts/f85_native_calibrated_tdleaf/successor_candidate_result.json"
    if not path.is_file():
        import pytest
        pytest.skip("approved Heavy evidence is intentionally transient")
    result = json.loads(path.read_text(encoding="utf-8"))
    assert result["behavior_changed"] is True
    assert result["trajectory_terminal"] == "ongoing"
    assert result["trajectory_truncated"] is True
    assert result["calibrated_alpha"] >= result["nominal_alpha"]
    assert result["measured_nominal_l2"] > 0
