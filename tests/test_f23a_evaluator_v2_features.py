"""Permanent contracts for the F23A audit-only evaluator probe."""

from __future__ import annotations

import pytest

from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import PieceType
from generic_chess.rules.compiler import compile_ruleset
from scripts.audit_f23a_evaluator_v2_features import (
    FAMILY_NAMES,
    Probe,
    _compile_context,
    _imports,
    evaluator_components,
    recover_f22_fixture,
)
from conftest import make_ruleset, make_state


def _renamed_rook_ruleset(type_ids: tuple[str, str]):
    anchor_id, rook_id = type_ids
    anchor_atoms = tuple(
        LeapAtom((df, dr))
        for df in (-1, 0, 1)
        for dr in (-1, 0, 1)
        if (df, dr) != (0, 0)
    )
    return make_ruleset(
        4,
        [
            PieceType(anchor_id, anchor_id, anchor_atoms, is_anchor=True),
            PieceType(
                rook_id,
                rook_id,
                (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0))),
            ),
        ],
        lines=[
            "..." + anchor_id.lower(),
            "." + rook_id.lower() + "..",
            ".." + rook_id + ".",
            anchor_id + "...",
        ],
    )


def test_f23a_recovers_exact_f22_partition_and_references():
    fixture = recover_f22_fixture()
    assert [row["name"] for row in fixture["corpus"]["positions"]] == [
        f"iteration-000086-game-00000{i}-ply12" for i in range(1, 10)
    ] + ["iteration-000086-game-000010-ply12"]
    assert fixture["provenance"]["references"]["iteration-000086-game-000001-ply12"] == "3g4e"
    assert fixture["provenance"]["references"]["iteration-000086-game-000009-ply12"] == "8h4d"
    assert len(fixture["controls"]) == 2
    assert len(fixture["failures"]) == 8


def test_f23a_v1_decomposition_parity_and_feature_determinism():
    m = _imports()
    ruleset = _renamed_rook_ruleset(("K", "R"))
    compiled = compile_ruleset(ruleset)
    state = make_state(compiled, ["...k", ".r..", "....", "K..."])
    probe = Probe(compiled, m)
    components, direct = evaluator_components(probe, state, state.position.side_to_move)
    assert components["total"] == direct
    first, _elapsed, _cost = probe.feature_vector(state, 0)
    second, _elapsed, _cost = probe.feature_vector(state, 0)
    assert tuple(first) == FAMILY_NAMES
    assert first == second


def test_f23a_features_are_type_name_invariant():
    m = _imports()
    compiled_a = compile_ruleset(_renamed_rook_ruleset(("K", "R")))
    compiled_b = compile_ruleset(_renamed_rook_ruleset(("A", "B")))
    state_a = make_state(compiled_a, ["...k", ".r..", "....", "K..."])
    state_b = make_state(compiled_b, ["...a", ".b..", "....", "A..."])
    values_a, _elapsed, _cost = Probe(compiled_a, m).feature_vector(state_a, 0)
    values_b, _elapsed, _cost = Probe(compiled_b, m).feature_vector(state_b, 0)
    assert values_a == pytest.approx(values_b)
