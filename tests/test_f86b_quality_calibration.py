"""F86B durable calibration-artifact contract tests."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86b_quality_calibration"


def _load(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_f86b_freezes_the_three_mandated_rulesets():
    payload = _load("rulesets.json")
    rows = payload["sample"]
    assert [(row["sample_id"], row["board_size"], row["seed"], row["ordinary_count"]) for row in rows] == [
        ("G4-A", 4, 860401, 2),
        ("G4-B", 4, 860402, 3),
        ("G5-A", 5, 860501, 3),
    ]
    assert all(len(row["ruleset_fingerprint"]) == 64 for row in rows)
    assert all(row["ruleset"]["metadata"]["generator"] == "f86a-minimal" for row in rows)


def test_f86b_results_account_for_bounded_work_only():
    payload = _load("results.json")
    assert payload["generated_ruleset_count"] == 3
    assert payload["quality_policy_pair_count"] == 6
    assert payload["quality_played_game_count"] == 12
    assert payload["tactical_probe_position_count"] == 3
    assert payload["tactical_probe_nodes"] <= 3 * 256
    assert payload["ladder"]["pair_count"] == 3
    assert payload["ladder"]["played_game_count"] == 6
    assert payload["f85_actual_compute"] == 0
    assert all(row["classification"] == "UNRESOLVED" for row in payload["quality"])
