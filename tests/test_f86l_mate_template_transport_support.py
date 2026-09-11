"""F86L diagnostic-only transport-support contracts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSIS = ROOT / "artifacts/f86l_mate_template_transport_support/diagnosis.json"


def _load():
    return json.loads(DIAGNOSIS.read_text(encoding="utf-8"))


def test_f86l_reproduces_authorized_v4_3_census_exactly():
    payload = _load()
    assert payload["sample_id"] == "V4-3"
    assert payload["authorized_census"] == {
        "candidate_checks": 156,
        "validated_positions": 111,
        "validated_templates": 12,
        "truncation": False,
        "cap": 256,
    }


def test_f86l_keeps_opening_graphs_and_duplicate_matching_evidence():
    payload = _load()
    assert len(payload["opening_piece_graphs"]) == 6
    assert len(payload["template_matching"]) == 12
    assert all("reachable_squares" in row and "scc_component_id" in row for row in payload["opening_piece_graphs"])
    assert all("hall_deficiency" in row and "by_type" in row for row in payload["template_matching"])
    assert all(row["complete_type_preserving_matching"] is False for row in payload["template_matching"])


def test_f86l_full_closure_reference_is_authority_consistent():
    payload = _load()
    assert payload["full_closure_reference"]["complete_template_count"] == 0
    assert payload["minimum_atom_support"]["minimum_added_reverse_atom_count"] is None
    assert len(payload["all_support_set_counterfactuals"]) == 7
    assert all(row["newly_assignment_reachable_template_count"] == 0 for row in payload["all_support_set_counterfactuals"])
    assert payload["interpretation"] == {
        "f86i_authority_v4_3_full_closure_complete_templates": 0,
        "same_batch_full_closure_complete_templates": 0,
        "authority_consistent": True,
        "meaning": "reverse closure does not restore V4-3 kinematic mate transport",
    }
    assert payload["routing"] == "REVERSE_CLOSURE_INSUFFICIENT_FOR_V4_3_KINEMATIC_MATE_TRANSPORT"


def test_f86l_is_diagnostic_only_with_no_expanded_compute():
    payload = _load()
    assert payload["dynamic"] == {
        "real_games": 0,
        "tactical_nodes": 0,
        "bfs_expansions": 0,
        "teacher_search_training": 0,
        "f85_actual_compute": 0,
    }
    assert payload["default_generator_changed"] is False
