"""F86K preregistration and bounded static-result contracts."""

import json
from pathlib import Path

import pytest

from generic_chess.core.movement import LeapAtom
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from scripts.f86k_backward_rank_partial_reversibility import _targeted_route

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts/f86k_backward_rank_partial_reversibility/manifest.json"
SAMPLES = ("V4-2", "V4-3", "V4-4", "V4-5", "V5-2", "V5-3", "V5-4", "V5-5")


def _load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_f86k_manifest_is_static_only_and_binds_all_eight_samples_to_f86i():
    payload = _load()
    assert payload["candidate_profile"] == "ORTHO4_PLUS_FIRST_STRICT_FORWARD_REVERSE_ORDINARY"
    assert [row["sample_id"] for row in payload["entries"]] == list(SAMPLES)
    assert payload["dynamic_budget"] == {"real_games": 0, "max_ply": 0}
    assert payload["static_budget"] == {
        "candidate_checks_per_cell": 2048,
        "candidate_checks_total_cap": 4096,
        "targeted_cells": ["V4-3", "V5-3"],
    }
    assert payload["default_generator_changed"] is False
    assert all(row["fingerprint_binding"]["candidate"] == row["candidate_ruleset_fingerprint"] for row in payload["entries"])
    assert all("f86i_full_closure_candidate_fingerprint" in row for row in payload["entries"])


def test_f86k_selects_first_strict_forward_atom_and_preserves_prefix():
    payload = _load()
    for entry in payload["entries"]:
        source = ruleset_from_dict(entry["source_ruleset"])
        candidate = ruleset_from_dict(entry["candidate_ruleset"])
        assert compile_ruleset(candidate).ruleset_fingerprint == entry["candidate_ruleset_fingerprint"]
        for source_piece, candidate_piece in zip(source.piece_types, candidate.piece_types):
            if source_piece.is_anchor:
                assert [atom.offset for atom in candidate_piece.movement_atoms] == [(1, 0), (-1, 0), (0, 1), (0, -1)]
                continue
            source_atoms = tuple(source_piece.movement_atoms)
            candidate_atoms = tuple(candidate_piece.movement_atoms)
            assert candidate_atoms[: len(source_atoms)] == source_atoms
            selection = entry["per_type_selection"][source_piece.type_id]
            selected = next((atom for atom in source_atoms if (atom.offset if isinstance(atom, LeapAtom) else atom.direction)[1] > 0), None)
            if selected is None:
                assert selection["status"] == "NO_STRICT_FORWARD_SOURCE_ATOM"
                assert candidate_atoms == source_atoms
            else:
                assert selection["status"] == "SELECTED_STRICT_FORWARD_SOURCE_ATOM"
                reverse = type(selected)((-selected.offset[0], -selected.offset[1])) if isinstance(selected, LeapAtom) else type(selected)((-selected.direction[0], -selected.direction[1]), selected.max_steps)
                assert reverse in candidate_atoms
                assert len(candidate_atoms) - len(source_atoms) <= 1


def test_f86k_routing_is_witness_first_then_truncation_then_failure():
    assert _targeted_route({"truncation": True, "joint_kinematically_reachable_count": 1}) == "BACKWARD_RANK_RESCUE_STATIC_WITNESS_EXISTS"
    assert _targeted_route({"truncation": True, "joint_kinematically_reachable_count": 0}) == "MATE_CAPACITY_UNRESOLVED_DUE_TO_CENSUS_CAP"
    assert _targeted_route({"truncation": False, "joint_kinematically_reachable_count": 0}) == "BACKWARD_RANK_RESCUE_INSUFFICIENT_KINEMATICALLY"


def test_f86k_result_is_static_only_and_bounded():
    result_path = ROOT / "artifacts/f86k_backward_rank_partial_reversibility/results.json"
    if not result_path.exists():
        pytest.skip("F86K result gate runs after the independently published prep checkpoint")
    results = json.loads(result_path.read_text(encoding="utf-8"))
    assert results["status"] == "F86K_STATIC_ONLY_ZERO_DYNAMIC_COMPUTE"
    assert results["dynamic"] == {"real_games": 0, "policy_trajectories": 0}
    assert results["tactical_probe_nodes"] == 0
    assert results["bfs_expansions"] == 0
    assert results["teacher_search_compute"] == 0
    assert results["f85_actual_compute"] == 0
    assert results["static_candidate_checks"]["total"] <= 4096
    assert all("backward_rank" in row for row in results["static"])
