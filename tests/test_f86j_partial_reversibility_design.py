"""F86J preregistration contracts for controlled partial reversibility."""

import json
from pathlib import Path

from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "f86j_partial_reversibility_design" / "manifest.json"
SAMPLES = ("V4-2", "V4-3", "V4-4", "V4-5", "V5-2", "V5-3", "V5-4", "V5-5")


def _load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_f86j_manifest_is_static_only_and_freezes_all_eight_samples():
    payload = _load()
    assert payload["status"] == "PRE_REGISTERED_STATIC_EXPERIMENTAL_CANDIDATE"
    assert payload["candidate_profile"] == "ORTHO4_PLUS_FIRST_ATOM_REVERSE_ORDINARY"
    assert [row["sample_id"] for row in payload["entries"]] == list(SAMPLES)
    assert payload["dynamic_budget"] == {"real_games": 0, "max_ply": 0}
    assert payload["static_budget"] == {
        "candidate_checks_per_cell": 2048,
        "candidate_checks_total_cap": 4096,
        "targeted_cells": ["V4-3", "V5-3"],
    }
    assert payload["default_generator_changed"] is False
    assert payload["result_driven_replacement_forbidden"] is True


def test_f86j_transform_preserves_source_prefix_and_reverses_only_first_atom_per_type():
    payload = _load()
    full_reverse_closed = []
    for entry in payload["entries"]:
        source = ruleset_from_dict(entry["source_ruleset"])
        candidate = ruleset_from_dict(entry["candidate_ruleset"])
        assert compile_ruleset(candidate).ruleset_fingerprint == entry["candidate_ruleset_fingerprint"]
        anchors = [piece for piece in candidate.piece_types if piece.is_anchor]
        assert len(anchors) == 1
        assert [atom.offset for atom in anchors[0].movement_atoms] == [
            (1, 0), (-1, 0), (0, 1), (0, -1)
        ]
        candidate_is_closed = True
        for source_piece, candidate_piece in zip(source.piece_types, candidate.piece_types):
            if source_piece.is_anchor:
                continue
            source_atoms = tuple(source_piece.movement_atoms)
            candidate_atoms = tuple(candidate_piece.movement_atoms)
            assert candidate_atoms[: len(source_atoms)] == source_atoms
            assert len(candidate_atoms) - len(source_atoms) <= 1
            if source_atoms:
                assert type(candidate_atoms[-1]) is type(source_atoms[0])
                assert candidate_atoms[-1] == (
                    type(source_atoms[0])(
                        (-source_atoms[0].offset[0], -source_atoms[0].offset[1])
                    )
                    if hasattr(source_atoms[0], "offset")
                    else type(source_atoms[0])(
                        (-source_atoms[0].direction[0], -source_atoms[0].direction[1]),
                        source_atoms[0].max_steps,
                    )
                ) if len(candidate_atoms) > len(source_atoms) else True
            atom_set = set(candidate_atoms)
            if any(
                (
                    type(atom)((-atom.offset[0], -atom.offset[1]))
                    if hasattr(atom, "offset")
                    else type(atom)((-atom.direction[0], -atom.direction[1]), atom.max_steps)
                ) not in atom_set
                for atom in candidate_atoms
            ):
                candidate_is_closed = False
        full_reverse_closed.append(candidate_is_closed)
    assert not all(full_reverse_closed)
