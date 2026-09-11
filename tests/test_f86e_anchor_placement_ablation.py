"""F86E corrected-diagnostic and placement-ablation artifact contracts."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86e_anchor_placement_ablation"

SAMPLES = {"V4-3", "V5-3"}
NEW_CELLS = {"ORTHO4_CURRENT", "ORTHO4_HOME", "FULL8_HOME"}
ALL_CELLS = {"LEGACY_CURRENT", "FULL8_CURRENT", *NEW_CELLS}

LEGACY_FINGERPRINTS = {
    "V4-3": "7e2ff9e15c2a0d1be5faa8c6697f22e488976a2d2ae9f077b85c6e71f95ff400",
    "V5-3": "d6e47a6fe19ab20538a1ec9539597b5765d0211cb608b15c262613a86e635297",
}

FULL8_FINGERPRINTS = {
    "V4-3": "7511327e944c195de71de536f818e8a2028136d4b04123937596f4dce46bda62",
    "V5-3": "8d77e9671449b2d6952aa7c80c898d7e390eff0fa534ac8be6d55e7f055ec1d8",
}


def _load(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_f86e_static_preflight_uses_corrected_direction_and_far_edge_metrics():
    payload = _load("static_diagnostics.json")
    rows = payload["rows"]
    assert len(rows) == 10
    assert {(row["sample_id"], row["cell"]) for row in rows} == {(sample, cell) for sample in SAMPLES for cell in ALL_CELLS}
    legacy = {row["sample_id"]: row for row in rows if row["cell"] == "LEGACY_CURRENT"}
    full8 = {row["sample_id"]: row for row in rows if row["cell"] == "FULL8_CURRENT"}
    assert {sample: row["ruleset_fingerprint"] for sample, row in legacy.items()} == LEGACY_FINGERPRINTS
    assert {sample: row["ruleset_fingerprint"] for sample, row in full8.items()} == FULL8_FINGERPRINTS
    for row in rows:
        diagnostics = row["diagnostics"]
        assert "forward_only_atom_fraction" not in diagnostics
        assert {
            "non_backward_atom_fraction",
            "strict_forward_atom_fraction",
            "horizontal_atom_fraction",
        } <= diagnostics.keys()
        for metric in diagnostics["type_metrics"]:
            assert 0.0 <= metric["non_backward_atom_fraction"] <= 1.0
            assert 0.0 <= metric["strict_forward_atom_fraction"] <= 1.0
            assert 0.0 <= metric["horizontal_atom_fraction"] <= 1.0
            assert abs(
                metric["non_backward_atom_fraction"]
                - metric["strict_forward_atom_fraction"]
                - metric["horizontal_atom_fraction"]
            ) <= 1e-12 or metric["has_backward_atom"]
            assert {owner["owner"] for owner in metric["owner_metrics"]} == {0, 1}
            assert all(0.0 <= owner["far_edge_sink_fraction"] <= 1.0 for owner in metric["owner_metrics"])


def test_f86e_serializes_only_the_three_new_cells_and_valid_placements():
    payload = _load("counterfactual_rulesets.json")
    rows = payload["rows"]
    assert len(rows) == 6
    assert {(row["sample_id"], row["cell"]) for row in rows} == {(sample, cell) for sample in SAMPLES for cell in NEW_CELLS}
    assert all(row["placement_valid"] is True for row in rows)
    assert all(row["ruleset"]["metadata"]["f86e_cell"] == row["cell"] for row in rows)
    assert all(len(row["ruleset_fingerprint"]) == 64 for row in rows)


def test_f86e_results_account_for_exact_scoped_work_and_routing():
    payload = _load("results.json")
    assert payload["played_game_count"] == 12
    assert len(payload["quality_games"]) == 12
    assert {row["cell"] for row in payload["quality_games"]} == NEW_CELLS
    assert all(sum(row["cell"] == cell for row in payload["quality_games"]) == 4 for cell in NEW_CELLS)
    assert payload["invalid_cells"] == []
    assert payload["tactical_probe_position_count"] == 6
    assert payload["tactical_probe_nodes"] <= 6 * 256
    assert set(payload["by_cell"]) == NEW_CELLS
    assert payload["routing"] == [
        "FULL8_ESCAPE_CAPACITY_TOO_HIGH",
        "ANCHOR_PLACEMENT_INTERACTION_OBSERVED",
        "MATE_CAPACITY_REMAINS_LIMITING",
    ]
    assert payload["default_generator_changed"] is False
    assert payload["no_seed_replacement"] is True
    assert payload["f85_actual_compute"] == 0
