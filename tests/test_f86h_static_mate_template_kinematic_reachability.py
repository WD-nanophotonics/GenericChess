"""F86H static mate-template kinematic reachability contracts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86h_kinematic_mate_reachability"


def _load(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_f86h_reuses_four_frozen_cells_and_f86f_validated_counts():
    results = _load("results.json")
    assert results["total_static_candidate_checks"] == 1593
    assert results["total_static_candidate_checks"] <= 8192
    assert results["real_games"] == 0
    assert results["policy_trajectories"] == 0
    assert results["bfs_expansions"] == 0
    assert results["teacher_search_compute"] == 0
    by_key = {(row["sample_id"], row["cell"]): row for row in results["results"]}
    assert len(by_key) == 4
    assert [by_key[key]["validated_position_count"] for key in (
        ("V4-3", "ORTHO4_CURRENT"),
        ("V4-3", "FULL8_CURRENT"),
        ("V5-3", "ORTHO4_CURRENT"),
        ("V5-3", "FULL8_CURRENT"),
    )] == [89, 0, 1262, 37]
    assert [by_key[key]["validated_template_count"] for key in (
        ("V4-3", "ORTHO4_CURRENT"),
        ("V4-3", "FULL8_CURRENT"),
        ("V5-3", "ORTHO4_CURRENT"),
        ("V5-3", "FULL8_CURRENT"),
    )] == [10, 0, 67, 2]
    assert all(row["symmetry"]["holds"] for row in by_key.values())


def test_f86h_graph_and_assignment_results_are_fail_closed():
    results = _load("results.json")
    assert results["routing"] == [
        "STATIC_MATE_TEMPLATES_KINEMATICALLY_UNREACHABLE_FROM_OPENING",
        "NO_VALIDATED_STATIC_MATE_TEMPLATE",
        "STATIC_MATE_TEMPLATES_KINEMATICALLY_UNREACHABLE_FROM_OPENING",
        "STATIC_MATE_TEMPLATES_KINEMATICALLY_UNREACHABLE_FROM_OPENING",
    ]
    assert all(
        row["ordinary_assignment_reachable_count"] == 0
        and row["joint_kinematically_reachable_count"] == 0
        and row["minimum_optimistic_ply_lower_bound"] is None
        for row in results["results"]
        if row["validated_template_count"]
    )
    assert results["results"][1]["validated_template_count"] == 0


def test_f86h_templates_are_normalized_and_graph_definition_is_optimistic():
    templates = _load("templates.json")
    assert templates["movement_graph"] == {
        "captures_ignored": True,
        "check_legality_ignored": True,
        "definition": (
            "directed edges from compiled empty_mobility[type_id][owner][source] "
            "to target"
        ),
        "occupancy_ignored": True,
        "turn_interaction_ignored": True,
    }
    total = 0
    for cell in templates["cells"]:
        total += cell["validated_template_count"]
        assert cell["validated_position_count"] == cell["authority_validated_count"]
        assert cell["truncation"] is False
        for template in cell["templates"]:
            assert template["ordinary"]
            assert template["allowed_attacker_anchor_squares"]
    assert total == 79

