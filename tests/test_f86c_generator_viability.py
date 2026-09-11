"""F86C frozen-population viability artifact contracts."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86c_generator_viability"


def _load(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_f86c_preserves_all_eight_preregistered_seeds():
    payload = _load("rulesets.json")
    rows = payload["sample"]
    assert [(row["sample_id"], row["board_size"], row["seed"], row["ordinary_count"]) for row in rows] == [
        ("V4-2", 4, 861401, 2),
        ("V4-3", 4, 861402, 3),
        ("V4-4", 4, 861403, 4),
        ("V4-5", 4, 861404, 5),
        ("V5-2", 5, 861501, 2),
        ("V5-3", 5, 861502, 3),
        ("V5-4", 5, 861503, 4),
        ("V5-5", 5, 861504, 5),
    ]
    assert all(row["generation_status"] == "OK" for row in rows)
    assert all(len(row["ruleset_fingerprint"]) == 64 for row in rows)


def test_f86c_stays_within_viability_probe_budget():
    payload = _load("results.json")
    assert payload["generated_ruleset_count"] == 8
    assert payload["generation_failure_count"] == 0
    assert payload["played_game_count"] == 16
    assert len(payload["quality_games"]) == 16
    assert payload["tactical_probe_position_count"] == 8
    assert payload["tactical_probe_nodes"] <= 2048
    assert payload["f85_actual_compute"] == 0
    assert payload["routing"] == "GENERATOR_DISTRIBUTION_STALEMATE_DOMINATED"
