"""F86I pre-registration and candidate construction contracts."""

import json
from pathlib import Path

from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "f86i_reversibility_rescue" / "manifest.json"
SAMPLES = ("V4-2", "V4-3", "V4-4", "V4-5", "V5-2", "V5-3", "V5-4", "V5-5")


def _load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_f86i_manifest_is_preregistered_for_all_eight_frozen_samples():
    payload = _load()
    assert payload["status"] == "PRE_REGISTERED_EXPERIMENTAL_CANDIDATE"
    assert payload["candidate_profile"] == "ORTHO4_PLUS_REVERSE_CLOSED_ORDINARY"
    assert [row["sample_id"] for row in payload["entries"]] == list(SAMPLES)
    assert payload["dynamic_budget"] == {
        "games_per_sample": 2,
        "max_ply": 32,
        "pairing": ["A/B", "B/A"],
        "real_games": 16,
    }
    assert payload["result_driven_replacement_forbidden"] is True
    assert payload["default_generator_changed"] is False


def test_f86i_candidate_changes_are_exact_and_fingerprints_bind():
    payload = _load()
    for entry in payload["entries"]:
        candidate = ruleset_from_dict(entry["candidate_ruleset"])
        compiled = compile_ruleset(candidate)
        assert compiled.ruleset_fingerprint == entry["candidate_ruleset_fingerprint"]
        anchors = [piece for piece in candidate.piece_types if piece.is_anchor]
        assert len(anchors) == 1
        assert [(atom.offset) for atom in anchors[0].movement_atoms] == [
            (1, 0), (-1, 0), (0, 1), (0, -1)
        ]
        for piece_type in candidate.piece_types:
            if piece_type.is_anchor:
                continue
            atoms = set(piece_type.movement_atoms)
            for atom in piece_type.movement_atoms:
                if hasattr(atom, "offset"):
                    reverse = type(atom)((-atom.offset[0], -atom.offset[1]))
                else:
                    reverse = type(atom)((-atom.direction[0], -atom.direction[1]), atom.max_steps)
                assert reverse in atoms


def test_f86i_tapes_are_exactly_preregistered_and_32_values_long():
    payload = _load()
    by_sample = {row["sample_id"]: row for row in payload["entries"]}
    assert by_sample["V4-3"]["policy_tapes"]["A"]["seed"] == 8624301
    assert by_sample["V4-3"]["policy_tapes"]["B"]["seed"] == 8624302
    assert by_sample["V5-3"]["policy_tapes"]["A"]["seed"] == 8625301
    assert by_sample["V5-3"]["policy_tapes"]["B"]["seed"] == 8625302
    for row in payload["entries"]:
        for tape in row["policy_tapes"].values():
            assert len(tape["uniforms"]) == 32
            assert all(0.0 <= value < 1.0 for value in tape["uniforms"])

