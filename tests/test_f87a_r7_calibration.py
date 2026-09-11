import json
from pathlib import Path

from scripts.f87a_r7_calibration import (
    BASELINE_SHA,
    MATCHUPS,
    NODE_CAP,
    run,
)


ROOT = Path(__file__).resolve().parents[1]


def test_f87a_r7_calibration_is_bounded_and_has_route_split(tmp_path):
    result = run(tmp_path)
    saved = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert result == saved
    assert result["baseline_sha"] == BASELINE_SHA
    assert result["expected_game_count"] == 8
    assert result["played_game_count"] <= result["expected_game_count"]
    assert result["actual_search_nodes"] <= NODE_CAP
    assert result["resolved_game_count"] == 8
    assert result["censored_game_count"] == 0
    assert result["resolved_pair_count"] == 4
    assert result["censored_pair_count"] == 0
    assert result["route"] in {"PROCEED_WEIGHT_UPDATE_CALIBRATION", "RETURN_T1_ACTION_SPECTRUM_REGRET"}
    assert result["external_engine_used"] is False
    assert set(result["matchup_scores"]) == {
        f"{stronger}_score_vs_{weaker}" for weaker, stronger in MATCHUPS
    }
    assert all(summary["status"] == "RESOLVED" for summary in result["matchup_scores"].values())
