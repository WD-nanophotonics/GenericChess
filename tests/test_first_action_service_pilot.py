from fractions import Fraction

import pytest

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_static_semantic_material_prior_v2c import (
    _token_state_ledger, finite_population_union_probability,
)
from scripts.first_action_service_pilot import (
    audit_first_action_service, canonical_occupancy_cubes,
    hand_target_empty_probability,
    reachable_board_square_count,
)


def test_toy_graph_distinguishes_first_action_service_from_source_product():
    base = {(0, "T", 0): {(0, "T", 1), (0, "T", 2)},
            (0, "T", 1): {(0, "T", 3)}, (0, "T", 2): set(), (0, "T", 3): set()}
    both_routes = {node: set(edges) for node, edges in base.items()}
    both_routes[(0, "T", 2)].add((0, "T", 3))
    one_route = base
    for graph, expected in ((both_routes, Fraction(1)),
                            (one_route, Fraction(3, 4))):
        assert reachable_board_square_count(graph, (0, "T", 0)) == 4
        first_action_service = sum(reachable_board_square_count(graph, successor)
                                   for successor in graph[(0, "T", 0)]) / 4
        assert first_action_service == expected


def test_canonical_square_renaming_preserves_finite_population_event():
    left = (((10, ("empty",)), (12, ("enemy",))),
            ((10, ("enemy",)), (12, ("empty",))))
    right = (((42, ("empty",)), (99, ("enemy",))),
             ((42, ("enemy",)), (99, ("empty",))))
    assert canonical_occupancy_cubes(left) == canonical_occupancy_cubes(right)
    assert finite_population_union_probability(left, empty_count=2,
                                               own_count=1, enemy_count=1) == finite_population_union_probability(
        canonical_occupancy_cubes(left), empty_count=2, own_count=1, enemy_count=1)


def test_hand_conditioning_is_derived_from_shogi_inventory():
    shogi = _token_state_ledger(compile_semantic_ruleset(build_standard_shogi_ruleset()))
    assert hand_target_empty_probability(shogi) == Fraction(121, 162)
    chess = _token_state_ledger(compile_semantic_ruleset(build_western_chess_ruleset()))
    with pytest.raises(ValueError, match="symmetric owner model"):
        hand_target_empty_probability(chess)


def test_prereference_chess_and_shogi_vectors_are_exact_and_owner_symmetric():
    for builder, expected_pawn in (
        (build_western_chess_ruleset, Fraction(102061, 83328)),
        (build_standard_shogi_ruleset, Fraction(31, 32)),
    ):
        result = audit_first_action_service(compile_semantic_ruleset(builder()),
                                            max_seconds=60)
        assert result["raw_board"]["P"] == expected_pawn
        assert result["positive_board_events"] > 0
        assert result["occupancy_probability_cache_size"] < result["positive_board_events"]
        assert all(owner0 == owner1 for owner0, owner1 in
                   result["raw_board_by_owner"].values())
        assert max(result["normalized_board"][type_id] for type_id in
                   ("B", "N", "P", "Q", "R") if type_id in result["normalized_board"]) == 1
