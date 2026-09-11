from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.f86s_f86n_r1_joint_witness_confinement import _route, build_prep


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "f86s_f86n_r1_joint_witness_confinement"


def _load(name: str):
    return json.loads((ARTIFACT / name).read_text(encoding="utf-8"))


def test_f86s_prep_freezes_authority_and_caps():
    manifest = _load("manifest.json")
    assert manifest["status"] == "PRE_REGISTERED_F86S_F86N_R1_JOINT_WITNESS_CONFINEMENT"
    assert manifest["baseline_commit"] == "453dac15fc5b0568d285615c142f572a0dc6a233"
    assert manifest["f86n_r1_manifest_blob"] == "adba41fa02a6e44459d3692ba232bf564c4450c7"
    assert manifest["f86n_r1_result_blob"] == "d7f7e7648255e009a1544908a75e7d49ee4a8e72"
    assert manifest["f86r_result_blob"] == "c0de094522a8660750221d9fa948cfd79a5c00cf"
    assert manifest["static_budget"] == {
        "candidate_checks_per_cell": 2048,
        "candidate_checks_total_cap": 4096,
        "new_games": 0,
        "new_movement_candidates": 0,
    }


def test_f86s_prep_reproduction_is_byte_identical(tmp_path):
    current = (ARTIFACT / "manifest.json").read_bytes()
    rebuilt_path = tmp_path / "manifest.json"
    build_prep(ROOT, rebuilt_path)
    assert rebuilt_path.read_bytes() == current
    assert hashlib.sha256(current).hexdigest() == hashlib.sha256(rebuilt_path.read_bytes()).hexdigest()


def test_f86s_exact_census_and_witness_counts():
    summary = _load("summary.json")
    assert summary["static_candidate_checks"] == {
        "V4-3": 1296,
        "V5-3": 2048,
        "total": 3344,
        "per_cell_cap": 2048,
        "total_cap": 4096,
    }
    assert summary["joint_witness_counts"] == {"V4-3": 2, "V5-3": 21}
    targeted = {row["sample_id"]: row for row in summary["targeted_static_mate_capacity"]}
    assert targeted["V4-3"]["validated_position_count"] == 1166
    assert targeted["V4-3"]["validated_template_count"] == 108
    assert targeted["V4-3"]["truncation"] is False
    assert targeted["V5-3"]["validated_position_count"] == 1592
    assert targeted["V5-3"]["validated_template_count"] == 90
    assert targeted["V5-3"]["truncation"] is True
    assert targeted["V5-3"]["witness_status"] == "OBSERVED_UNDER_TRUNCATED_CENSUS"


def test_f86s_witness_profiles_are_exact_mates_and_routes_are_sample_dependent():
    summary = _load("summary.json")
    witnesses = _load("witnesses.json")["witnesses"]
    assert len(witnesses) == 23
    assert {row["sample_id"] for row in witnesses} == {"V4-3", "V5-3"}
    assert all(row["exact_checkmate_confinement"]["validated_exact_checkmate"] for row in witnesses)
    assert all(row["exact_checkmate_confinement"]["legal_defender_reply_count"] == 0 for row in witnesses)
    assert summary["routing"] == {
        "by_sample": {
            "V4-3": "STATIC_VS_DYNAMIC_CONFINEMENT_DIFFERENCE_IS_MULTI_FACTOR",
            "V5-3": "STATIC_MATE_WITNESSES_HAVE_STRICTLY_STRONGER_NEIGHBOR_ATTACK_COVERAGE",
        },
        "overall": "CONFINEMENT_GAP_IS_SAMPLE_DEPENDENT",
    }


def test_f86s_route_requires_serialized_dynamic_occupancy_evidence():
    static = {
        "anchor_neighborhood_coverage_distribution": {"2": 1, "3": 1},
        "friendly_occupied_neighbor_distribution": {"0": 2},
        "enemy_occupied_neighbor_distribution": {"1": 1, "2": 1},
        "checker_multiplicity_distribution": {"1": 2},
    }
    dynamic = {
        "anchor_neighborhood_coverage_distribution": {"2": 1},
        "breaking_reply_mechanism_counts": {"ANCHOR_FLIGHT": 2},
        "checker_multiplicity_distribution": {"1": 1},
        "occupancy_evidence_available": False,
    }
    assert _route(static, dynamic) == "STATIC_VS_DYNAMIC_CONFINEMENT_DIFFERENCE_IS_MULTI_FACTOR"
    dynamic["occupancy_evidence_available"] = True
    assert _route(static, dynamic) == "STATIC_MATE_CONFINEMENT_DEPENDS_ON_OCCUPANCY_STRUCTURE"


def test_f86s_compute_accounting_is_zero_for_prohibited_work():
    summary = _load("summary.json")
    assert all(value == 0 for value in summary["compute_accounting"].values())
