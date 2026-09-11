"""F86F bounded ordinary-piece mate-capacity census contracts."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86f_mate_capacity"


def _load(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_f86f_census_covers_four_frozen_cells_without_truncation():
    payload = _load("census.json")
    profiles = payload["profiles"]
    assert len(profiles) == 4
    assert {(row["sample_id"], row["cell"]) for row in profiles} == {
        (sample, cell) for sample in ("V4-3", "V5-3") for cell in ("ORTHO4_CURRENT", "FULL8_CURRENT")
    }
    assert payload["total_checked_position_count"] == 1593
    assert payload["total_candidate_position_count"] == 1593
    assert payload["total_checked_position_count"] <= 8192
    assert payload["any_truncation"] is False
    assert all(row["checked_position_count"] <= 2048 for row in profiles)
    assert all(row["truncation"] is False for row in profiles)


def test_f86f_geometric_and_engine_results_are_recorded_exactly():
    payload = _load("census.json")
    by_key = {(row["sample_id"], row["cell"]): row for row in payload["profiles"]}
    assert by_key[("V4-3", "ORTHO4_CURRENT")]["geometric_full_net_anchor_fraction"] == 5 / 16
    assert by_key[("V4-3", "ORTHO4_CURRENT")]["engine_validated_mate_exists"] is True
    assert by_key[("V4-3", "FULL8_CURRENT")]["geometric_full_net_anchor_fraction"] == 1 / 16
    assert by_key[("V4-3", "FULL8_CURRENT")]["engine_validated_mate_exists"] is False
    assert by_key[("V5-3", "ORTHO4_CURRENT")]["geometric_full_net_anchor_fraction"] == 7 / 25
    assert by_key[("V5-3", "ORTHO4_CURRENT")]["engine_validated_mate_exists"] is True
    assert by_key[("V5-3", "FULL8_CURRENT")]["geometric_full_net_anchor_fraction"] == 1 / 25
    assert by_key[("V5-3", "FULL8_CURRENT")]["engine_validated_mate_exists"] is True
    examples = _load("examples.json")["examples"]
    assert len(examples) == 9
    assert all(len(example["ordinary"]) == 3 for example in examples)


def test_f86f_scope_and_routing_are_fail_closed():
    payload = _load("census.json")
    assert payload["routing"]["labels"] == ["STRIPPED_ANCHOR_MATE_CAPACITY_EXISTS"]
    assert payload["real_games"] == 0
    assert payload["teacher_search_compute"] == 0
    assert payload["f85_actual_compute"] == 0
    assert payload["default_generator_changed"] is False
    assert payload["no_ruleset_replacement"] is True
