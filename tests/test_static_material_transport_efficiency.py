from dataclasses import replace
import ast
from fractions import Fraction
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_semantic_ruleset
from scripts.static_material_transport_efficiency import audit_type_transport, graph_metrics, opportunity_cost
from tests.test_static_semantic_material_prior_v2a import _synthetic


def test_disconnected_graph_has_zero_efficiency_and_unreachable_pairs():
    result = graph_metrics(3, {0: {}})
    assert result["global_transport_efficiency_exact"] == "0/1"
    assert result["unweighted_reachable_fraction_exact"] == "0/1"
    assert result["unreachable_ordered_pair_fraction"] == 1.0


def test_complete_one_move_graph_has_unit_efficiency_and_cost():
    edges = {(source, target): Fraction(1) for source in range(3) for target in range(3) if source != target}
    result = graph_metrics(3, {0: edges})
    assert result["global_transport_efficiency_exact"] == "1/1"
    assert result["weighted_mean_finite_transport_cost"] == 1.0
    assert result["mean_finite_hop_distance"] == 1.0


def test_edge_probability_cost_and_two_edge_route_are_exact_and_additive():
    assert opportunity_cost(Fraction(1)) == Fraction(1)
    assert opportunity_cost(Fraction(1, 2)) == Fraction(2)
    assert opportunity_cost(Fraction(1, 4)) == Fraction(4)
    result = graph_metrics(3, {0: {(0, 1): Fraction(1, 2), (1, 2): Fraction(1, 4)}})
    assert result["reachable_ordered_pair_count"] == 3
    assert result["weighted_mean_finite_transport_cost"] == 4.0  # (2 + 4 + 6) / 3
    assert result["mean_finite_hop_distance"] == 4 / 3
    assert result["global_transport_efficiency_exact"] == "11/72"


def test_adding_edge_cannot_reduce_reachability_or_global_efficiency():
    base = {(0, 1): Fraction(1, 2), (1, 2): Fraction(1, 4)}
    expanded = {**base, (2, 0): Fraction(1, 2)}
    before = graph_metrics(3, {0: base})
    after = graph_metrics(3, {0: expanded})
    assert after["unweighted_reachable_fraction"] >= before["unweighted_reachable_fraction"]
    assert after["global_transport_efficiency"] >= before["global_transport_efficiency"]
    assert before["directed_edge_count"] <= after["directed_edge_count"]


def test_removing_an_edge_cannot_increase_direct_edge_set():
    before = {(0, 1): Fraction(1), (1, 0): Fraction(1), (1, 2): Fraction(1)}
    after = dict(before)
    del after[(1, 2)]
    assert set(after) <= set(before)
    assert graph_metrics(3, {0: after})["directed_edge_count"] <= graph_metrics(3, {0: before})["directed_edge_count"]


def test_capture_only_action_contributes_occupancy_weighted_transport_edges():
    _rules, compiled = _synthetic(relations=("enemy",))
    result = audit_type_transport(compiled, "X")
    assert result["coverage"] == "COMPLETE"
    assert result["metrics"]["directed_edge_count"] > 0
    probabilities = [Fraction(row["probability"]) for owner_rows in result["owner_edges"].values() for row in owner_rows]
    assert probabilities and all(Fraction(0) < value < 1 for value in probabilities)
    for owner_rows in result["owner_edges"].values():
        for edge in owner_rows:
            assert Fraction(edge["cost"]) == 1 / Fraction(edge["probability"])


def test_type_rename_and_owner_mirror_leave_average_efficiency_unchanged():
    rules, compiled = _synthetic()
    baseline = audit_type_transport(compiled, "X")["metrics"]["global_transport_efficiency_exact"]
    renamed_types = tuple(replace(row, type_id="Y") if row.type_id == "X" else row for row in rules.piece_types)
    renamed_actions = tuple(replace(row, type_ids=("Y",)) for row in rules.semantic_actions)
    renamed = compile_semantic_ruleset(replace(
        rules, piece_types=renamed_types, semantic_actions=renamed_actions,
        drop_allowed={"Y": rules.drop_allowed["X"]},
    ))
    assert audit_type_transport(renamed, "Y")["metrics"]["global_transport_efficiency_exact"] == baseline
    mirrored_position = tuple(tuple(
        replace(piece, owner=1 - piece.owner) if piece is not None else None for piece in row
    ) for row in rules.initial_position)
    mirrored = compile_semantic_ruleset(replace(rules, initial_position=mirrored_position))
    assert audit_type_transport(mirrored, "X")["metrics"]["global_transport_efficiency_exact"] == baseline


def test_chess_promotion_and_dynamic_legality_are_ledgered_not_graph_edges():
    from generic_chess.rules.western_chess import build_western_chess_ruleset

    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    pawn = audit_type_transport(compiled, "P")
    assert pawn["coverage"] == "COMPLETE"
    assert pawn["ledger"]["dynamic_positional_legality"]
    assert pawn["ledger"]["type_transition_edges_excluded"]
    assert all(not row["included_in_graph"] for row in pawn["ledger"]["type_transition_edges_excluded"])
    assert all(not row["included_in_graph"] for row in pawn["ledger"]["dynamic_positional_legality"])


def test_feature_builder_does_not_import_human_values_or_residuals():
    from scripts import static_material_transport_efficiency as feature

    source = Path(feature.__file__).read_text(encoding="utf-8").lower()
    assert "f40_material_prior_audit" not in source
    assert "v2b-validation" not in source
    modules = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
    assert not any("validate_static_material" in name or name.startswith("tests.fixtures") for name in modules)
