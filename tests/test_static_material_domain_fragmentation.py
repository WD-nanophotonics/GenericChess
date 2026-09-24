from fractions import Fraction
from itertools import combinations
from dataclasses import replace
from itertools import product
from pathlib import Path

from generic_chess.rules.compiler import compile_semantic_ruleset
from scripts.audit_static_material_domain_fragmentation import (
    _cube_feasible,
    _type_topology,
    audit_topology,
    component_statistics,
)
from scripts import audit_static_material_domain_fragmentation as candidate
from scripts.audit_static_semantic_material_prior_v2c import (
    _token_state_ledger,
    finite_population_union_probability,
)
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from tests.test_static_semantic_material_prior_v2c import _synthetic_with_optional_tokens


def test_component_statistics_connected_equal_unequal_and_monotonicity():
    complete = [(a, b) for a in range(4) for b in range(4) if a != b]
    assert component_statistics(4, complete)["same_domain_probability_d_exact"] == "1/1"
    assert component_statistics(4, complete)["fragmentation_f_exact"] == "0/1"

    equal = [(0, 1), (2, 3)]
    result = component_statistics(4, equal)
    assert result["component_sizes"] == [2, 2]
    assert result["same_domain_probability_d_exact"] == "1/2"
    assert result["fragmentation_f_exact"] == "1/2"

    unequal = [(0, 1), (1, 2)]
    assert component_statistics(5, unequal)["same_domain_probability_d_exact"] == "11/25"

    before_merge = component_statistics(5, [(0, 1), (3, 4)])
    after_merge = component_statistics(5, [(0, 1), (1, 2), (3, 4)])
    assert Fraction(after_merge["fragmentation_f_exact"]) <= Fraction(before_merge["fragmentation_f_exact"])
    before_split = component_statistics(4, [(0, 1), (1, 2), (2, 3)])
    after_split = component_statistics(4, [(0, 1), (2, 3)])
    assert Fraction(after_split["fragmentation_f_exact"]) >= Fraction(before_split["fragmentation_f_exact"])


def test_direction_reversal_renaming_and_owner_mirroring_preserve_component_metrics():
    edges = [(0, 1), (2, 1), (3, 4)]
    expected = component_statistics(5, edges)
    assert component_statistics(5, [(b, a) for a, b in edges]) == expected
    renamed = [(a + 10, b + 10) for a, b in edges]
    renamed_normalized = [(a - 10, b - 10) for a, b in renamed]
    assert component_statistics(5, renamed_normalized) == expected

    owners = [component_statistics(5, edges), component_statistics(5, [(4, 3), (2, 3)])]
    mirror = [component_statistics(5, [(b, a) for a, b in row]) for row in (edges, [(4, 3), (2, 3)])]
    mean = lambda rows: sum(Fraction(row["fragmentation_f_exact"]) for row in rows) / len(rows)
    assert mean(owners) == mean(mirror)


def test_cube_positive_witness_matches_exact_finite_population_mass():
    labels = ("empty", "own", "enemy")
    allowed_sets = [frozenset(combo) for width in range(1, 4)
                    for combo in combinations(labels, width)]
    cubes = [tuple((square, allowed) for square, allowed in enumerate(choice))
             for choice in product(allowed_sets, repeat=3)]
    count_sets = [(empty, own, 3 - empty - own)
                  for empty in range(4) for own in range(4 - empty)]
    for counts in count_sets:
        for cube in cubes:
            exact = finite_population_union_probability([cube], empty_count=counts[0],
                own_count=counts[1], enemy_count=counts[2])
            assert _cube_feasible(cube, counts) == (exact > 0)
    impossible = ((0, frozenset({"enemy"})), (1, frozenset({"enemy"})))
    assert not _cube_feasible(impossible, (1, 1, 0))


def test_geometry_recovers_checker_color_and_connected_orthogonal_domains():
    diagonal = _synthetic_with_optional_tokens(
        shapes=((1, 1), (-1, 1), (1, -1), (-1, -1)),
        relations=("empty", "enemy", "empty", "enemy"),
    )
    diagonal_compiled = compile_semantic_ruleset(diagonal)
    diagonal_ledger = _token_state_ledger(diagonal_compiled)
    diagonal_topology = _type_topology(diagonal_compiled, "X", diagonal_ledger)
    assert diagonal_topology["coverage_complete"]
    assert all(row["component_sizes"] == [32, 32]
               for row in diagonal_topology["owner_graphs"].values())

    orthogonal = _synthetic_with_optional_tokens(
        shapes=((1, 0), (-1, 0), (0, 1), (0, -1)),
        relations=("empty", "enemy", "empty", "enemy"),
    )
    orthogonal_compiled = compile_semantic_ruleset(orthogonal)
    orthogonal_ledger = _token_state_ledger(orthogonal_compiled)
    orthogonal_topology = _type_topology(orthogonal_compiled, "X", orthogonal_ledger)
    assert orthogonal_topology["coverage_complete"]
    assert all(row["component_sizes"] == [64]
               for row in orthogonal_topology["owner_graphs"].values())


def test_piece_id_rename_and_owner_mirror_leave_topology_invariant():
    rules = _synthetic_with_optional_tokens(
        shapes=((1, 1), (-1, 1), (1, -1), (-1, -1)),
        relations=("empty", "enemy", "empty", "enemy"),
    )

    def topology(value, type_id="X"):
        compiled = compile_semantic_ruleset(value)
        return _type_topology(compiled, type_id, _token_state_ledger(compiled))

    original = topology(rules)
    renamed_types = tuple(replace(row, type_id="Y") if row.type_id == "X" else row
                          for row in rules.piece_types)
    renamed_actions = tuple(replace(row, type_ids=tuple("Y" if tid == "X" else tid
                                                        for tid in row.type_ids))
                            for row in rules.semantic_actions)
    renamed_position = tuple(tuple(
        replace(piece, base_type_id="Y", current_type_id="Y")
        if piece is not None and piece.current_type_id == "X" else piece for piece in row
    ) for row in rules.initial_position)
    renamed = topology(replace(rules, piece_types=renamed_types, semantic_actions=renamed_actions,
                               initial_position=renamed_position,
                               drop_allowed={"Y": rules.drop_allowed["X"]}), "Y")
    assert {owner: row["directed_edges"] for owner, row in original["owner_graphs"].items()} == {
        owner: row["directed_edges"] for owner, row in renamed["owner_graphs"].items()}

    mirrored_position = tuple(tuple(
        replace(piece, owner=1 - piece.owner) if piece is not None else None for piece in row
    ) for row in rules.initial_position)
    mirrored = topology(replace(rules, initial_position=mirrored_position))
    assert original["owner_graphs"]["0"]["directed_edges"] == mirrored["owner_graphs"]["1"]["directed_edges"]
    assert original["owner_graphs"]["1"]["directed_edges"] == mirrored["owner_graphs"]["0"]["directed_edges"]
    assert original["owner_averaged"] == mirrored["owner_averaged"]


def test_capture_edges_count_with_nonzero_occupancy_and_impossible_cubes_do_not():
    rules = _synthetic_with_optional_tokens(shapes=((1, 0), (0, 1)),
                                             relations=("empty", "enemy"))
    compiled = compile_semantic_ruleset(rules)
    ledger = _token_state_ledger(compiled)
    result = _type_topology(compiled, "X", ledger)
    assert result["coverage_complete"]
    assert any(row["target_outcomes"] == ["enemy"]
               for graph in result["owner_graphs"].values()
               for row in graph["directed_edge_rows"])


def test_frozen_candidate_flags_and_transition_drop_history_dynamic_ledgers():
    result = audit_topology()
    assert result["coverage_complete"]
    assert result["human_reference_imported"] is False
    assert result["v2d_residuals_imported"] is False
    assert result["material_formula_modified"] is False
    assert result["v2e_transition_value_used"] is False
    assert result["transport_efficiency_used"] is False
    assert result["piece_specific_logic"] is False
    assert result["game_specific_logic"] is False
    chess = result["rulesets"]["western_chess"]["pieces"]
    shogi = result["rulesets"]["standard_shogi"]["pieces"]
    assert chess["P"]["type_transition_event_ledger"]
    assert chess["P"]["excluded_history_ledger"]
    assert chess["P"]["excluded_dynamic_legality_ledger"]
    assert shogi["P"]["excluded_drop_ledger"]
    candidate_source = Path(candidate.__file__).read_text(encoding="utf-8")
    assert "static-semantic-material-prior-v2d-human-validation" not in candidate_source

    chess_rules = compile_semantic_ruleset(build_western_chess_ruleset())
    chess_pawn = _type_topology(chess_rules, "P", _token_state_ledger(chess_rules))
    historical_patterns = {row["pattern"] for row in chess_pawn["excluded_history_ledger"]}
    assert historical_patterns
    assert not any(row["semantic_patterns"] and historical_patterns.intersection(row["semantic_patterns"])
                   for graph in chess_pawn["owner_graphs"].values()
                   for row in graph["directed_edge_rows"])
    shogi_rules = compile_semantic_ruleset(build_standard_shogi_ruleset())
    shogi_pawn = _type_topology(shogi_rules, "P", _token_state_ledger(shogi_rules))
    shogi_pawn_edges = {tuple(edge) for graph in shogi_pawn["owner_graphs"].values()
                        for edge in graph["directed_edges"]}
    transitions = shogi_pawn["type_transition_event_ledger"]
    forced_pairs = {(row["source_square"], row["target_square"])
                    for row in transitions if row["forced"]}
    optional_pairs = {(row["source_square"], row["target_square"])
                      for row in transitions if row["optional"]}
    assert forced_pairs and optional_pairs
    assert forced_pairs.isdisjoint(shogi_pawn_edges)
    assert optional_pairs <= shogi_pawn_edges
    drop_patterns = {row["pattern"] for row in shogi_pawn["excluded_drop_ledger"]}
    assert drop_patterns
    assert not any(drop_patterns.intersection(row["semantic_patterns"])
                   for graph in shogi_pawn["owner_graphs"].values()
                   for row in graph["directed_edge_rows"])
