"""F86M final static lattice/component diagnosis contracts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSIS = ROOT / "artifacts/f86m_v4_3_movement_lattice_invariants/diagnosis.json"


def _load():
    return json.loads(DIAGNOSIS.read_text(encoding="utf-8"))


def test_f86m_reproduces_both_authority_censuses_under_execution_caps():
    payload = _load()
    assert payload["hard_caps"] == {
        "f86k_checks": 256,
        "f86i_checks": 512,
        "total_checks": 768,
        "execution_time_enforced": True,
    }
    assert payload["census"] == {
        "F86K": {
            "candidate_position_count": 156,
            "validated_position_count": 111,
            "validated_template_count": 12,
            "truncation": False,
        },
        "F86I": {
            "candidate_position_count": 504,
            "validated_position_count": 398,
            "validated_template_count": 40,
            "truncation": False,
        },
        "total_candidate_checks": 660,
    }


def test_f86m_computes_expected_full_closure_lattice_signatures():
    payload = _load()
    rows = {row["type_id"]: row for row in payload["movement_lattice"]}
    assert rows["P0"]["integer_lattice_rank"] == 1
    assert rows["P0"]["residue_or_invariant"]["kind"] == "rank_one_linear_invariant"
    assert rows["P1"]["integer_lattice_rank"] == 2
    assert rows["P1"]["lattice_index"] == 2
    assert rows["P1"]["residue_or_invariant"]["modulus"] == 2
    assert rows["P2"]["integer_lattice_rank"] == 2
    assert rows["P2"]["lattice_index"] == 3
    assert rows["P2"]["residue_or_invariant"]["modulus"] == 3


def test_f86m_decomposes_all_templates_at_lattice_level():
    payload = _load()
    for label, expected in (("F86K", 12), ("F86I", 40)):
        summary = payload["batch_summaries"][label]
        assert summary["template_count"] == expected
        assert summary["templates_blocked_at_lattice_level"] == expected
        assert summary["templates_passing_lattice_but_blocked_by_finite_board"] == 0
        assert summary["templates_whose_only_remaining_failure_is_duplicate_hall"] == 0
        assert summary["templates_with_complete_ordinary_assignment"] == 0
    assert payload["routing"]["primary"] == "MOVEMENT_LATTICE_INVARIANTS_DOMINATE_V4_3_TRANSPORT_FAILURE"
    assert payload["matching"]["F86K"][0]["by_type"]["P0"]["target_rows"][0]["source_target_edge_details"]


def test_f86m_is_diagnostic_only():
    payload = _load()
    assert payload["dynamic"] == {
        "real_games": 0,
        "tactical_nodes": 0,
        "bfs_expansions": 0,
        "teacher_search_training": 0,
        "f85_actual_compute": 0,
    }
    assert payload["default_generator_changed"] is False
