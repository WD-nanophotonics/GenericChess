from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path

from scripts.audit_static_material_v2f_lifetime_reachability import (
    _canonical_sha,
    _fraction,
    _transition_depths,
    audit,
    build_augmented_graph,
    summarize_source,
)
from scripts.freeze_static_material_v2f_lifetime_reachability import freeze

ROOT = Path(__file__).resolve().parents[1]


def _event(owner: int, source: int, target: int, destination: str, *, area: int,
           forced: bool, positive: bool = True) -> dict:
    return {
        "owner": owner,
        "source_square": source,
        "target_square": target,
        "destination_types": [destination],
        "target_outcome": "empty",
        "forced": forced,
        "optional": not forced,
        "event_probability_positive": positive,
        "semantic_patterns": ["synthetic executable transition"],
        "witness_empty_own_enemy_counts": [1, 1, area - 3],
    }


def _piece(area: int, edges_by_owner: dict[int, list[tuple[int, int]]],
           transitions_by_owner: dict[int, list[dict]]) -> dict:
    owner_graphs = {}
    for owner in (0, 1):
        edges = sorted(set(edges_by_owner.get(owner, [])))
        owner_graphs[str(owner)] = {
            "directed_edges": [list(edge) for edge in edges],
            "directed_edge_rows": [
                {"source": source, "target": target,
                 "event_probability_positive": True,
                 "witness_empty_own_enemy_counts": [1, 1, area - 3]}
                for source, target in edges
            ],
            "component_membership": [list(range(area))],
        }
    return {
        "coverage_complete": True,
        "unsupported_semantics": [],
        "owner_graphs": owner_graphs,
        "type_transition_event_ledger": [
            event for owner in (0, 1) for event in transitions_by_owner.get(owner, [])
        ],
    }


def _diagonal_edges(width: int) -> list[tuple[int, int]]:
    edges = []
    for row in range(width):
        for col in range(width):
            source = row * width + col
            for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
                nr, nc = row + dr, col + dc
                if 0 <= nr < width and 0 <= nc < width:
                    edges.append((source, nr * width + nc))
    return edges


def test_optional_and_forced_transitions_keep_only_executable_branches() -> None:
    area = 4
    pieces = {
        "A": _piece(area, {0: [(0, 1), (1, 2)]}, {
            0: [
                _event(0, 1, 2, "B", area=area, forced=False),
                _event(0, 2, 3, "B", area=area, forced=True),
                _event(0, 0, 3, "B", area=area, forced=True, positive=False),
            ],
        }),
        "B": _piece(area, {0: [(0, 1), (1, 2), (2, 3)]}, {}),
    }
    graph, ledger = build_augmented_graph(area, ["A", "B"], pieces, 0)
    assert ("A", 2) in graph[("A", 1)]  # optional stay branch
    assert ("B", 2) in graph[("A", 1)]  # optional transformed branch
    assert ("A", 3) not in graph[("A", 2)]  # forced event has no same-type branch
    assert ("B", 3) in graph[("A", 2)]
    assert ("B", 3) not in graph[("A", 0)]  # zero-probability event is excluded
    assert len(ledger["transition_edges"]) == 2


def test_directed_reachability_never_invents_reverse_edges() -> None:
    area = 4
    pieces = {"A": _piece(area, {0: [(0, 1), (1, 2)]}, {})}
    graph, _ = build_augmented_graph(area, ["A"], pieces, 0)
    forward = summarize_source(graph, "A", 0, area)
    backward = summarize_source(graph, "A", 2, area)
    assert forward["reachable_board_squares"] == [0, 1, 2]
    assert backward["reachable_board_squares"] == [2]
    assert forward["q_exact"] == "3/4"
    assert backward["q_exact"] == "1/4"


def test_terminal_checker_colour_mover_stays_in_its_weak_domain() -> None:
    area = 16
    edges = _diagonal_edges(4)
    pieces = {"D": _piece(area, {0: edges, 1: edges}, {})}
    graph, _ = build_augmented_graph(area, ["D"], pieces, 0)
    even = summarize_source(graph, "D", 0, area)
    odd = summarize_source(graph, "D", 1, area)
    assert even["q_exact"] == "1/2"
    assert odd["q_exact"] == "1/2"
    assert all(sum(divmod(square, 4)) % 2 == 0 for square in even["reachable_board_squares"])
    assert all(sum(divmod(square, 4)) % 2 == 1 for square in odd["reachable_board_squares"])
    assert even["reachable_current_types"] == ["D"]


def test_transition_adds_cross_domain_access_only_from_sources_that_can_reach_it() -> None:
    area = 16
    diagonal = _diagonal_edges(4)
    fully_connected = [(source, target) for source in range(area) for target in range(area)]
    pieces = {
        "D": _piece(area, {0: diagonal, 1: diagonal}, {
            0: [_event(0, 0, 5, "F", area=area, forced=True)],
            1: [_event(1, 0, 5, "F", area=area, forced=True)],
        }),
        "F": _piece(area, {0: fully_connected, 1: fully_connected}, {}),
    }
    graph, _ = build_augmented_graph(area, ["D", "F"], pieces, 0)
    source_can_reach = summarize_source(graph, "D", 0, area)
    source_cannot_reach = summarize_source(graph, "D", 1, area)
    assert source_can_reach["q_exact"] == "1/1"
    assert source_can_reach["reachable_current_types"] == ["D", "F"]
    assert source_cannot_reach["q_exact"] == "1/2"
    assert source_cannot_reach["reachable_current_types"] == ["D"]
    expected_new_squares = [square for square in range(area)
                            if sum(divmod(square, 4)) % 2 == 1]
    assert source_can_reach["reachable_only_after_type_change_squares"] == expected_new_squares
    assert source_cannot_reach["reachable_only_after_type_change_squares"] == []


def test_unreachable_transition_does_not_affect_source_and_type_cycles_terminate() -> None:
    area = 5
    pieces = {
        "A": _piece(area, {0: [(0, 1)]}, {0: [_event(0, 4, 4, "B", area=area, forced=True)]}),
        "B": _piece(area, {}, {0: [_event(0, 4, 3, "A", area=area, forced=True)]}),
    }
    graph, _ = build_augmented_graph(area, ["A", "B"], pieces, 0)
    summary = summarize_source(graph, "A", 0, area)
    assert summary["reachable_current_types"] == ["A"]
    assert summary["q_exact"] == "2/5"
    assert len(_transition_depths(graph, ("A", 0))) == 1
    cycle_summary = summarize_source(graph, "A", 4, area)
    assert cycle_summary["reachable_current_types"] == ["A", "B"]
    assert cycle_summary["minimum_transition_depth_by_reachable_type"] == {"A": 0, "B": 1}


def test_piece_identifier_rename_and_owner_mirror_preserve_numeric_results() -> None:
    area = 4
    forward_edges = [(0, 1), (1, 2)]
    full_edges = [(source, target) for source in range(area) for target in range(area)]
    original = {
        "A": _piece(area, {0: forward_edges, 1: forward_edges}, {
            0: [_event(0, 1, 2, "B", area=area, forced=True)],
            1: [_event(1, 1, 2, "B", area=area, forced=True)],
        }),
        "B": _piece(area, {0: full_edges, 1: full_edges}, {}),
    }
    renamed = {
        "X": _piece(area, {0: forward_edges, 1: forward_edges}, {
            0: [_event(0, 1, 2, "Y", area=area, forced=True)],
            1: [_event(1, 1, 2, "Y", area=area, forced=True)],
        }),
        "Y": _piece(area, {0: full_edges, 1: full_edges}, {}),
    }
    q_values = []
    for owner in (0, 1):
        graph_a, _ = build_augmented_graph(area, ["A", "B"], original, owner)
        graph_b, _ = build_augmented_graph(area, ["X", "Y"], renamed, owner)
        a = summarize_source(graph_a, "A", 0, area)
        b = summarize_source(graph_b, "X", 0, area)
        q_values.append(_fraction(a["q_exact"]))
        assert a["q_exact"] == b["q_exact"]
        assert a["reachable_board_squares"] == b["reachable_board_squares"]
        assert a["minimum_graph_hop_distance_by_board_square"] == b["minimum_graph_hop_distance_by_board_square"]
        assert len(graph_a) == len(graph_b)
    assert q_values[0] == q_values[1] == Fraction(1)


def test_real_frozen_chess_and_shogi_diagnostic_reconstructs_every_source() -> None:
    candidate = audit()
    assert candidate["classification"] == "STATIC_MATERIAL_LIFETIME_REACHABILITY_DIAGNOSTIC_COMPLETE"
    assert candidate["human_reference_imported"] is False
    assert candidate["human_validation_performed"] is False
    assert candidate["material_formula_modified"] is False
    assert candidate["material_candidate_created"] is False
    assert candidate["context_weight_used"] is False

    capability = json.loads((ROOT / ".generic_chess_flow/static-material-domain-conditional-capability.json").read_text())
    for ruleset, ruleset_result in candidate["rulesets"].items():
        assert "K" in ruleset_result["anchor_types_excluded_from_augmented_graph"]
        for type_id, type_result in ruleset_result["types"].items():
            frozen_type = capability["rulesets"][ruleset]["types"][type_id]
            q_weighted = Fraction(0)
            area = ruleset_result["board_area"]
            for owner in ("0", "1"):
                owner_result = type_result["owner_graphs"][owner]
                source_rows = frozen_type["owner_graphs"][owner]["source_rows"]
                assert len(owner_result["source_summaries"]) == area
                assert [row["source_square"] for row in owner_result["source_summaries"]] == list(range(area))
                assert len(owner_result["transition_event_ledger_for_type"]) == len(
                    [row for row in owner_result["transition_event_ledger_for_type"]
                     if row["owner"] == int(owner)])
                for source_row, summary in zip(source_rows, owner_result["source_summaries"]):
                    assert _fraction(source_row["b_exact"]) == (
                        _fraction(source_row["u_exact"]) + _fraction(source_row["c_exact"]))
                    assert len(summary["reachable_board_squares"]) == summary["reachable_board_square_count"]
                    assert _fraction(summary["q_exact"]) == Fraction(summary["reachable_board_square_count"], area)
                    assert (set(summary["reachable_without_type_change_squares"])
                            | set(summary["reachable_only_after_type_change_squares"])) == set(
                                summary["reachable_board_squares"])
                    q_weighted += _fraction(source_row["b_exact"]) * _fraction(summary["q_exact"])
                assert owner_result["graph_node_count"] == area * len(ruleset_result["non_anchor_current_types"])
            assert _fraction(type_result["q_cap_exact"]) == q_weighted / (2 * area)
            if type_result["terminal_current_type"]:
                assert _fraction(type_result["q_cap_exact"]) == _fraction(type_result["adr129_same_weak_domain_j_exact"])
                assert _fraction(type_result["q_cap_minus_adr129_j_exact"]) == 0
            else:
                assert type_result["adr129_same_weak_domain_j_exact"] is None
                assert type_result["q_cap_minus_adr129_j_exact"] is None

    assert set(candidate["rulesets"]["western_chess"]["types"]) == {"B", "N", "P", "Q", "R"}
    assert set(candidate["rulesets"]["standard_shogi"]["types"]) == {
        "B", "G", "L", "N", "P", "R", "S", "TB", "TL", "TN", "TP", "TR", "TS"
    }


def test_pre_reference_freeze_replays_graph_and_exact_q_cap() -> None:
    frozen = freeze()
    assert frozen["classification"] == "STATIC_MATERIAL_LIFETIME_REACHABILITY_DIAGNOSTIC_COMPLETE"
    assert frozen["reference_data_read"] is False
    assert frozen["material_formula_modified"] is False
    assert frozen["all_frozen_v2d_source_capabilities_reconstructed_exactly"] is True
    assert frozen["all_augmented_source_reachability_recomputed_exactly"] is True
    assert frozen["terminal_q_cap_and_adr129_j_differences_recomputed_exactly"] is True
