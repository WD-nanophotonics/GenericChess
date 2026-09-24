from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path

from scripts.audit_static_material_v2g_redeployment_throughput import (
    _fraction,
    audit,
    select_target_service,
    shortest_distances,
)
from scripts.freeze_static_material_v2g_redeployment_throughput import freeze

ROOT = Path(__file__).resolve().parents[1]


def test_unreachable_distinct_target_contributes_zero() -> None:
    selection = select_target_service("A", 0, 2, {("A", 0): 0}, {})
    assert selection == {
        "serviceable": False,
        "minimum_hop_count": None,
        "selected_result_type": None,
        "selected_distance": None,
        "destination_b_exact": None,
        "W_exact": "0/1",
        "cooptimal_result_types": [],
    }


def test_one_action_delivers_b_and_two_actions_deliver_b_over_two() -> None:
    caps = {("A", 1): Fraction(8), ("A", 2): Fraction(8)}
    one = select_target_service("A", 0, 1, {("A", 0): 0, ("A", 1): 1}, caps)
    two = select_target_service("A", 0, 2, {("A", 0): 0, ("A", 1): 1, ("A", 2): 2}, caps)
    assert one["W_exact"] == "8/1"
    assert one["selected_distance"] == 1
    assert two["W_exact"] == "4/1"
    assert two["selected_distance"] == 2


def test_max_rate_prefers_one_action_over_two_for_equal_capability() -> None:
    distances = {("A", 0): 0, ("A", 5): 1, ("B", 5): 2}
    caps = {("A", 5): Fraction(6), ("B", 5): Fraction(6)}
    selected = select_target_service("A", 0, 5, distances, caps)
    assert selected["W_exact"] == "6/1"
    assert selected["selected_result_type"] == "A"
    assert selected["cooptimal_result_types"] == ["A"]


def test_equal_distance_prefers_larger_destination_capability() -> None:
    distances = {("A", 0): 0, ("B", 4): 2, ("C", 4): 2}
    caps = {("B", 4): Fraction(5), ("C", 4): Fraction(7)}
    selected = select_target_service("A", 0, 4, distances, caps)
    assert selected["selected_result_type"] == "C"
    assert selected["destination_b_exact"] == "7/1"
    assert selected["W_exact"] == "7/2"


def test_longer_route_wins_when_its_destination_capability_rate_is_higher() -> None:
    distances = {("A", 0): 0, ("B", 3): 1, ("C", 3): 2}
    caps = {("B", 3): Fraction(3), ("C", 3): Fraction(8)}
    selected = select_target_service("A", 0, 3, distances, caps)
    assert selected["selected_result_type"] == "C"
    assert selected["selected_distance"] == 2
    assert selected["W_exact"] == "4/1"


def test_directed_shortest_paths_handle_cycles_and_do_not_invent_reverse_service() -> None:
    graph = {
        ("A", 0): (("A", 1),),
        ("A", 1): (("B", 2),),
        ("B", 2): (("A", 1), ("B", 3)),
        ("B", 3): (),
    }
    forward = shortest_distances(graph, ("A", 0))
    backward = shortest_distances(graph, ("B", 3))
    assert forward[("B", 3)] == 3
    assert forward[("B", 2)] == 2
    assert backward == {("B", 3): 0}


def test_optional_and_forced_transition_graph_branches_are_respected() -> None:
    from scripts.audit_static_material_v2f_lifetime_reachability import build_augmented_graph

    area = 4

    def piece(edges: list[tuple[int, int]], ledger: list[dict]) -> dict:
        return {
            "coverage_complete": True,
            "unsupported_semantics": [],
            "owner_graphs": {
                str(owner): {
                    "directed_edges": [list(edge) for edge in edges],
                    "directed_edge_rows": [
                        {"source": source, "target": target, "event_probability_positive": True,
                         "witness_empty_own_enemy_counts": [0, 0, area - 1]}
                        for source, target in edges
                    ],
                }
                for owner in (0, 1)
            },
            "type_transition_event_ledger": ledger,
        }

    optional = {
        "owner": 0, "source_square": 0, "target_square": 1,
        "destination_types": ["B"], "target_outcome": "empty",
        "forced": False, "optional": True, "event_probability_positive": True,
        "semantic_patterns": ["optional synthetic branch"],
        "witness_empty_own_enemy_counts": [0, 0, area - 1],
    }
    forced = {**optional, "source_square": 1, "target_square": 2,
              "forced": True, "optional": False, "semantic_patterns": ["forced synthetic branch"]}
    pieces = {
        "A": piece([(0, 1)], [optional, forced]),
        "B": piece([(1, 2), (2, 3)], []),
    }
    graph, _ = build_augmented_graph(area, ["A", "B"], pieces, 0)
    assert ("A", 1) in graph[("A", 0)]
    assert ("B", 1) in graph[("A", 0)]
    assert ("B", 2) in graph[("A", 1)]
    assert ("A", 2) not in graph[("A", 1)]


def test_type_rename_owner_mirror_and_common_scale_preserve_numeric_score() -> None:
    graph = {
        ("A", 0): (("A", 1),),
        ("A", 1): (("A", 2),),
        ("A", 2): (),
    }
    caps = {("A", 0): Fraction(2), ("A", 1): Fraction(3), ("A", 2): Fraction(6)}
    renamed_graph = {(f"X{typ}", sq): tuple((f"X{next_type}", target) for next_type, target in edges)
                     for (typ, sq), edges in graph.items()}
    renamed_caps = {(f"X{typ}", sq): value for (typ, sq), value in caps.items()}

    def score(g: dict, type_id: str, capability: dict) -> Fraction:
        total = Fraction(0)
        for source in range(3):
            distances = shortest_distances(g, (type_id, source))
            for target in range(3):
                if source == target:
                    continue
                total += _fraction(select_target_service(type_id, source, target, distances, capability)["W_exact"])
        return total / (3 * 2)

    base = score(graph, "A", caps)
    assert score(renamed_graph, "XA", renamed_caps) == base
    mirrored_owner_average = (score(graph, "A", caps) + score(graph, "A", caps)) / 2
    assert mirrored_owner_average == base
    assert score(graph, "A", {node: value * 5 for node, value in caps.items()}) == base * 5


def test_real_frozen_candidate_preserves_every_selected_target_and_exact_m() -> None:
    candidate = audit()
    assert candidate["classification"] == "STATIC_MATERIAL_PRIOR_V2G_REDEPLOYMENT_THROUGHPUT_PRE_REFERENCE_FROZEN"
    assert candidate["human_reference_imported"] is False
    assert candidate["human_validation_performed"] is False
    assert candidate["free_material_coefficient"] is False
    assert candidate["context_weight_used"] is False
    assert candidate["distance_exponent"] == 1
    assert candidate["distance_exponent_is_rate_identity"] is True
    assert candidate["service_model_boundary"]
    assert "destination_b_exact" in candidate["source_target_task_row_schema"]

    for ruleset, ruleset_row in candidate["rulesets"].items():
        area = ruleset_row["board_area"]
        for type_id, type_row in ruleset_row["types"].items():
            owner_sums = Fraction(0)
            owner_task_count = 0
            for owner, owner_row in type_row["owner_graphs"].items():
                assert len(owner_row["source_tasks"]) == area
                for source in owner_row["source_tasks"]:
                    targets = source["target_tasks"]
                    assert len(targets) == area - 1
                    assert all(target[0] != source["source_square"] for target in targets)
                    for target in targets:
                        if target[1]:
                            assert target[3] is not None and target[4] >= 1
                            assert _fraction(target[6]) >= 0
                        else:
                            assert target[3] is None and target[4] is None and target[6] == "0/1"
                owner_sums += _fraction(owner_row["sum_W_exact"])
                owner_task_count += owner_row["target_task_count"]
            assert owner_task_count == 2 * area * (area - 1)
            assert _fraction(type_row["M_exact"]) == owner_sums / owner_task_count
            assert (_fraction(type_row["owner_graphs"]["0"]["owner_mean_M_exact"])
                    == _fraction(type_row["owner_graphs"]["1"]["owner_mean_M_exact"]))


def test_pre_reference_freeze_recomputes_formula_and_input_hashes() -> None:
    frozen = freeze()
    assert frozen["classification"] == "STATIC_MATERIAL_PRIOR_V2G_REDEPLOYMENT_THROUGHPUT_PRE_REFERENCE_FROZEN"
    assert frozen["reference_data_read"] is False
    assert frozen["all_source_target_rows_recomputed_exactly"] is True
    assert frozen["all_frozen_graph_hashes_reproduced"] is True
    assert frozen["all_source_local_capability_reconstructed"] is True
