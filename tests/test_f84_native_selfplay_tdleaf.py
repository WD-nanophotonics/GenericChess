from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from generic_chess.learning.selfplay import SelfPlayConfig
from generic_chess.learning.tdleaf import TDLeafConfig
from scripts.f84_native_selfplay_tdleaf import WORK_ORDER

ROOT = Path(__file__).resolve().parents[1]


def test_f84_uses_default_native_learning_parameters_for_one_game():
    config = SelfPlayConfig(games=1, nodes_per_move=512, max_depth=12, seed=840401, epsilon=0.10, tt_megabytes=8, max_plies=64)
    assert WORK_ORDER == "F84_NATIVE_SELFPLAY_TDLEAF_SINGLE_UPDATE"
    assert asdict(config) == {
        "games": 1,
        "nodes_per_move": 512,
        "max_depth": 12,
        "seed": 840401,
        "epsilon": 0.10,
        "tt_megabytes": 8,
        "max_plies": 64,
    }
    assert asdict(TDLeafConfig()) == {"gamma": 1.0, "lambd": 0.7, "alpha": None, "value_scale": None}


def test_f84_stage_a_artifact_records_explicit_cutoff_bootstrap_and_change():
    if not (ROOT / "artifacts/f84_native_selfplay_tdleaf/successor_candidate_descriptor.json").is_file():
        import pytest
        pytest.skip("approved Heavy evidence is intentionally transient")
    descriptor = json.loads((ROOT / "artifacts/f84_native_selfplay_tdleaf/successor_candidate_descriptor.json").read_text(encoding="utf-8"))
    result = json.loads((ROOT / "artifacts/f84_native_selfplay_tdleaf/successor_candidate_result.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(json.dumps({k: v for k, v in descriptor.items() if k != "descriptor_sha256"}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert digest == descriptor["descriptor_sha256"]
    assert result["candidate_descriptor_sha256"] == descriptor["descriptor_sha256"]
    assert result["behavior_changed"] is True
    assert result["trajectory_truncated"] is True
    assert result["trajectory_terminal"] == "ongoing"
    assert result["trajectory_bootstrap_value"] == descriptor["trajectory_bootstrap_value"]
    assert result["trajectory_points"] == result["positions_seen"] == 64
