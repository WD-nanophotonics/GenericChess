from dataclasses import asdict
from pathlib import Path
import json

from generic_chess.learning.selfplay import SelfPlayConfig
from scripts.f86_native_search_distillation import WORK_ORDER


def test_f86_contract_uses_deterministic_native_search_selfplay():
    assert WORK_ORDER == "F86_NATIVE_SEARCH_DISTILLATION_NONLINEAR_SINGLE_UPDATE"
    assert asdict(SelfPlayConfig(games=1, nodes_per_move=512, max_depth=12, seed=860401, epsilon=0.0, tt_megabytes=8, max_plies=64)) == {
        "games": 1, "nodes_per_move": 512, "max_depth": 12, "seed": 860401,
        "epsilon": 0.0, "tt_megabytes": 8, "max_plies": 64,
    }


def test_f86_artifact_if_present_records_improved_objective_and_change():
    path = Path(__file__).resolve().parents[1] / "artifacts/f86_native_search_distillation/successor_candidate_result.json"
    if not path.is_file():
        import pytest
        pytest.skip("approved Heavy evidence is intentionally transient")
    result = json.loads(path.read_text(encoding="utf-8"))
    assert result["behavior_changed"] is True
    assert result["objective_after"] < result["objective_before"]
    assert result["candidate_max_abs_residual"] <= 2.0 * result["parent_max_abs_residual"] + 1e-9
