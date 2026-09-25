from __future__ import annotations

from fractions import Fraction
from types import SimpleNamespace

import pytest

from generic_chess.core.coordinates import BoardShape
from generic_chess.core.pieces import Piece
from generic_chess.rules.ir import CompiledSemanticSupport, SemanticTypeMetadata
from scripts.audit_static_material_v2h_rule_support_source_prior import (
    _conditional_mean,
    _reachable_nodes,
    _support_by_type,
    audit,
)


def test_rule_support_reachability_is_seeded_and_directed_across_type_changes() -> None:
    graph = {
        ("P", 0): {("P", 1), ("Q", 2)},
        ("P", 1): set(),
        ("Q", 2): {("Q", 3)},
        ("Q", 3): set(),
        ("R", 4): set(),
    }
    assert _reachable_nodes(graph, {("P", 0)}) == {
        ("P", 0), ("P", 1), ("Q", 2), ("Q", 3),
    }
    assert _reachable_nodes(graph, {("R", 4)}) == {("R", 4)}


def test_conditional_mean_is_exact_and_rejects_invalid_support() -> None:
    values = [Fraction(1), Fraction(2), Fraction(100)]
    assert _conditional_mean(values, [0, 1]) == Fraction(3, 2)
    with pytest.raises(RuntimeError):
        _conditional_mean(values, [])
    with pytest.raises(RuntimeError):
        _conditional_mean(values, [0, 0])


def test_rectangular_support_seed_indices_use_shape_width_and_keep_owner() -> None:
    shape = BoardShape(9, 10)
    rows = [[None for _ in range(shape.width)] for _ in range(shape.height)]
    rows[0][0] = Piece(0, "P", "P")
    rows[0][8] = Piece(1, "P", "P")
    rows[9][0] = Piece(0, "P", "P")
    rows[9][8] = Piece(1, "P", "P")
    mask = (False,) * shape.area
    support = CompiledSemanticSupport(
        board_size=None,
        initial_position=tuple(tuple(row) for row in rows),
        type_metadata={"P": SemanticTypeMetadata("P", False, False)},
        drop_allowed={"P": (mask, mask)},
        board_width=shape.width,
        board_height=shape.height,
    )
    compiled = SimpleNamespace(support=support)
    topology = {
        "P": {
            "coverage_complete": True,
            "unsupported_semantics": False,
            "owner_graphs": {
                str(owner): {"directed_edges": [], "directed_edge_rows": []}
                for owner in (0, 1)
            },
            "type_transition_event_ledger": [],
        }
    }

    owner0, evidence0 = _support_by_type(compiled, ["P"], topology, 0)
    owner1, evidence1 = _support_by_type(compiled, ["P"], topology, 1)

    assert support.board_shape == shape
    assert support.board_area == 90
    assert support.board_size is None
    assert owner0["P"] == [0, 81]  # (0, 0), (0, 9)
    assert owner1["P"] == [8, 89]  # (8, 0), (8, 9)
    assert evidence0["initial_seed_nodes"] == [["P", 0], ["P", 81]]
    assert evidence1["initial_seed_nodes"] == [["P", 8], ["P", 89]]
    assert set(owner0["P"]).isdisjoint(owner1["P"])


def test_complete_pre_reference_candidate_reconstructs_full_and_restricted_types() -> None:
    candidate = audit()
    assert candidate["classification"] == "STATIC_MATERIAL_RULE_SUPPORT_CONDITIONED_SOURCE_PRIOR_COMPLETE"
    assert candidate["human_reference_imported"] is False
    assert candidate["human_validation_performed"] is False
    assert candidate["games_played"] == 0
    assert candidate["coverage_complete"] is True
    assert candidate["reconstruction_complete"] is True
    assert candidate["support_gates_pass"] is True
    assert candidate["rulesets"]["western_chess"]["types"]["P"]["b_support_exact"] == "23945/13392"
    assert candidate["rulesets"]["standard_shogi"]["types"]["L"]["b_support_exact"] == "19728450347/5917542400"
    assert candidate["rulesets"]["standard_shogi"]["types"]["N"]["b_support_exact"] == "2519/1260"
    assert candidate["rulesets"]["standard_shogi"]["types"]["P"]["b_support_exact"] == "1559/1280"
    for ruleset in candidate["rulesets"].values():
        for row in ruleset["types"].values():
            assert row["component_sum_exact"] is True
            assert row["source_coverage_complete"] is True
            if not row["restricted_support"]:
                assert row["full_support_reproduces_v2d"] is True
