"""Audit rule-only directed lifetime reachability for physical board tokens."""

from __future__ import annotations

from collections import deque
from fractions import Fraction
import hashlib
import heapq
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset

TOPOLOGY_RAW = ROOT / ".generic_chess_flow/static-material-domain-fragmentation-topology.json"
TOPOLOGY_FREEZE = ROOT / ".generic_chess_flow/static-material-domain-fragmentation-freeze.json"
CAPABILITY_RAW = ROOT / ".generic_chess_flow/static-material-domain-conditional-capability.json"
CAPABILITY_FREEZE = ROOT / ".generic_chess_flow/static-material-domain-conditional-capability-freeze.json"
V2C_RAW = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-board.json"
V2C_FREEZE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-freeze.json"
V2D_RAW = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json"
V2D_FREEZE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-freeze.json"
OUTPUT = ROOT / ".generic_chess_flow/static-material-v2f-lifetime-reachability.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _fraction(value: str | Fraction) -> Fraction:
    if isinstance(value, Fraction):
        return value
    numerator, denominator = value.split("/", 1)
    return Fraction(int(numerator), int(denominator))


def _fstr(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _verify_freeze(path: Path, *, candidate: Path | None = None) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"Required freeze is unavailable: {path.name}")
    freeze = json.loads(path.read_text(encoding="utf-8"))
    if freeze.get("human_metrics_computed") is True or freeze.get("reference_data_read") is True:
        raise RuntimeError(f"Baseline freeze is not pre-reference: {path.name}")
    if freeze.get("human_reference_read") is True or freeze.get("human_validation_performed") is True:
        raise RuntimeError(f"Baseline freeze records human-reference access: {path.name}")
    for relative, expected in freeze.get("sha256", {}).items():
        source = ROOT / relative
        if not source.is_file() or _sha(source) != expected:
            raise RuntimeError(f"Frozen input hash mismatch for {path.name}: {relative}")
    if candidate is not None:
        expected = freeze.get("topology_candidate_sha256", freeze.get("candidate_sha256"))
        if expected and _sha(candidate) != expected:
            raise RuntimeError(f"Frozen candidate digest mismatch for {candidate.name}")
    return freeze


def _load_frozen_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    topology_freeze = _verify_freeze(TOPOLOGY_FREEZE, candidate=TOPOLOGY_RAW)
    capability_freeze = _verify_freeze(CAPABILITY_FREEZE, candidate=CAPABILITY_RAW)
    v2c_freeze = _verify_freeze(V2C_FREEZE, candidate=V2C_RAW)
    v2d_freeze = _verify_freeze(V2D_FREEZE, candidate=V2D_RAW)
    if topology_freeze.get("human_reference_read") is not False:
        raise RuntimeError("ADR-128 topology is not certified pre-reference")
    if capability_freeze.get("reference_data_read") is not False:
        raise RuntimeError("ADR-129 capability decomposition is not certified pre-reference")

    topology = json.loads(TOPOLOGY_RAW.read_text(encoding="utf-8"))
    capability = json.loads(CAPABILITY_RAW.read_text(encoding="utf-8"))
    if topology.get("coverage_complete") is not True:
        raise RuntimeError("Frozen ADR-128 topology coverage is incomplete")
    required_false = (
        "human_reference_imported", "v2d_residuals_imported", "material_formula_modified",
        "v2e_transition_value_used", "transport_efficiency_used", "piece_specific_logic",
        "game_specific_logic",
    )
    if any(topology.get(key) is not False for key in required_false):
        raise RuntimeError("ADR-128 topology has a forbidden input or score modification")
    capability_false = (
        "human_reference_imported", "v2d_residuals_imported", "material_formula_modified",
        "score_validation_performed", "v2e_transition_value_used", "transport_efficiency_used",
        "transition_bearing_domain_payoff_assigned", "piece_specific_logic", "game_specific_logic",
    )
    if any(capability.get(key) is not False for key in capability_false):
        raise RuntimeError("ADR-129 capability input crosses the diagnostic boundary")
    if capability.get("coverage_complete") is not True or capability.get("reconstruction_complete") is not True:
        raise RuntimeError("Frozen ADR-129 source-capability coverage/reconstruction is incomplete")

    input_paths = {
        "v2c_freeze": V2C_FREEZE, "v2c_candidate": V2C_RAW,
        "v2d_freeze": V2D_FREEZE, "v2d_candidate": V2D_RAW,
        "adr128_freeze": TOPOLOGY_FREEZE, "adr128_candidate": TOPOLOGY_RAW,
        "adr129_freeze": CAPABILITY_FREEZE, "adr129_candidate": CAPABILITY_RAW,
    }
    input_sha = {key: _sha(path) for key, path in input_paths.items()}
    expected_adr129_inputs = capability.get("input_sha256", {})
    expected_adapted = {
        "v2c_freeze": expected_adr129_inputs.get("v2c_freeze"),
        "v2c_candidate": expected_adr129_inputs.get("v2c_candidate"),
        "v2d_freeze": expected_adr129_inputs.get("v2d_freeze"),
        "v2d_candidate": expected_adr129_inputs.get("v2d_candidate"),
        "adr128_freeze": expected_adr129_inputs.get("topology_freeze"),
        "adr128_candidate": expected_adr129_inputs.get("topology_candidate"),
    }
    if any(input_sha[key] != value for key, value in expected_adapted.items()):
        raise RuntimeError("ADR-129's frozen upstream input digests do not match current files")
    return topology, capability, input_sha


def build_augmented_graph(
    area: int,
    current_types: list[str],
    pieces: dict[str, Any],
    owner: int,
) -> tuple[dict[tuple[str, int], tuple[tuple[str, int], ...]], dict[str, Any]]:
    """Combine frozen type-preserving edges and positive-mass transition events."""
    type_set = set(current_types)
    if type_set != set(pieces):
        raise RuntimeError("Compiled non-anchor type set differs from frozen ADR-128/ADR-129 types")
    adjacency: dict[tuple[str, int], set[tuple[str, int]]] = {
        (type_id, square): set() for type_id in current_types for square in range(area)
    }
    transition_edges: set[tuple[str, int, str, int]] = set()
    transition_ledger: list[dict[str, Any]] = []

    for type_id in current_types:
        piece = pieces[type_id]
        if piece.get("coverage_complete") is not True or piece.get("unsupported_semantics"):
            raise RuntimeError(f"Frozen intrinsic topology is incomplete for type {type_id}")
        graph = piece["owner_graphs"][str(owner)]
        edges = graph["directed_edges"]
        if edges != [list(edge) for edge in sorted({tuple(edge) for edge in edges})]:
            raise RuntimeError(f"Noncanonical frozen directed edges: {type_id}/{owner}")
        rows = graph["directed_edge_rows"]
        if any(row.get("event_probability_positive") is not True
               or sum(row.get("witness_empty_own_enemy_counts", ())) != area - 1
               for row in rows):
            raise RuntimeError(f"Frozen type-preserving edge lacks a positive-mass witness: {type_id}/{owner}")
        if {(row["source"], row["target"]) for row in rows} != {tuple(edge) for edge in edges}:
            raise RuntimeError(f"Frozen edge ledger and edge list disagree: {type_id}/{owner}")
        for source, target in edges:
            if not (0 <= source < area and 0 <= target < area):
                raise RuntimeError(f"Out-of-board type-preserving edge: {type_id}/{owner}")
            adjacency[(type_id, source)].add((type_id, target))

        for event in piece["type_transition_event_ledger"]:
            if int(event["owner"]) != owner:
                continue
            if event.get("event_probability_positive") is False:
                continue
            if event.get("event_probability_positive") is not True:
                raise RuntimeError(f"Transition ledger lacks a positive-mass decision: {type_id}/{owner}")
            witness = event.get("witness_empty_own_enemy_counts", ())
            if len(witness) != 3 or sum(witness) != area - 1:
                raise RuntimeError(f"Transition event lacks a frozen V2C source-conditioned witness: {type_id}/{owner}")
            source, target = int(event["source_square"]), int(event["target_square"])
            if not (0 <= source < area and 0 <= target < area):
                raise RuntimeError(f"Out-of-board transition event: {type_id}/{owner}")
            destinations = tuple(sorted(set(event.get("destination_types", ()))))
            if not destinations or any(destination not in type_set for destination in destinations):
                raise RuntimeError(f"Transition destination is missing or not a non-anchor graph node: {type_id}/{owner}")
            if bool(event.get("optional")) == bool(event.get("forced")):
                raise RuntimeError(f"Transition optional/forced ledger is inconsistent: {type_id}/{owner}")
            for destination in destinations:
                if destination == type_id:
                    raise RuntimeError("Transition ledger improperly lists the unchanged current type as a transition")
                adjacency[(type_id, source)].add((destination, target))
                transition_edges.add((type_id, source, destination, target))
            transition_ledger.append({
                "source_type": type_id, "owner": owner, "source_square": source,
                "target_square": target, "destination_types": list(destinations),
                "target_outcome": event["target_outcome"], "forced": bool(event["forced"]),
                "optional": bool(event["optional"]),
                "semantic_patterns": event["semantic_patterns"],
                "witness_empty_own_enemy_counts": event["witness_empty_own_enemy_counts"],
            })

    frozen_transition_edges = {(source, square, destination, target)
                               for type_id in current_types
                               for event in pieces[type_id]["type_transition_event_ledger"]
                               if int(event["owner"]) == owner and event.get("event_probability_positive") is True
                               for source, square, destination, target in (
                                   (type_id, int(event["source_square"]), destination,
                                    int(event["target_square"]))
                                   for destination in event["destination_types"])}
    if transition_edges != frozen_transition_edges:
        raise RuntimeError("Augmented graph transition edges differ from the frozen event ledger")
    ordered = {node: tuple(sorted(targets)) for node, targets in adjacency.items()}
    return ordered, {"transition_edges": [list(row) for row in sorted(transition_edges)],
                     "transition_event_ledger": transition_ledger}


def _bfs(graph: dict[tuple[str, int], tuple[tuple[str, int], ...]],
         start: tuple[str, int], *, same_type_only: str | None = None) -> dict[tuple[str, int], int]:
    distances = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if same_type_only is not None and neighbor[0] != same_type_only:
                continue
            if neighbor not in distances:
                distances[neighbor] = distances[node] + 1
                queue.append(neighbor)
    return distances


def _transition_depths(graph: dict[tuple[str, int], tuple[tuple[str, int], ...]],
                       start: tuple[str, int]) -> dict[str, int]:
    """Minimum number of type changes (not plies) along any graph path."""
    distances = {start: 0}
    queue: list[tuple[int, tuple[str, int]]] = [(0, start)]
    while queue:
        depth, node = heapq.heappop(queue)
        if depth != distances[node]:
            continue
        for neighbor in graph[node]:
            next_depth = depth + (neighbor[0] != node[0])
            if next_depth < distances.get(neighbor, 1 << 30):
                distances[neighbor] = next_depth
                heapq.heappush(queue, (next_depth, neighbor))
    by_type: dict[str, int] = {}
    for (type_id, _square), depth in distances.items():
        by_type[type_id] = min(depth, by_type.get(type_id, depth))
    return dict(sorted(by_type.items()))


def summarize_source(
    graph: dict[tuple[str, int], tuple[tuple[str, int], ...]],
    start_type: str,
    source_square: int,
    area: int,
) -> dict[str, Any]:
    start = (start_type, source_square)
    distances = _bfs(graph, start)
    same_type_distances = _bfs(graph, start, same_type_only=start_type)
    reached_nodes = sorted(distances)
    reached_squares = sorted({square for _type, square in reached_nodes})
    same_type_squares = sorted({square for _type, square in same_type_distances})
    transition_only_squares = sorted(set(reached_squares) - set(same_type_squares))
    board_hops: dict[int, int] = {}
    for (_type, square), distance in distances.items():
        board_hops[square] = min(distance, board_hops.get(square, distance))
    return {
        "source_square": source_square,
        "reachable_node_count": len(reached_nodes),
        "reachable_node_sha256": _canonical_sha([list(node) for node in reached_nodes]),
        "reachable_board_square_count": len(reached_squares),
        "reachable_board_squares": reached_squares,
        "q_exact": _fstr(Fraction(len(reached_squares), area)),
        "reachable_current_types": sorted({type_id for type_id, _square in reached_nodes}),
        "minimum_transition_depth_by_reachable_type": _transition_depths(graph, start),
        "minimum_graph_hop_distance_by_board_square": [[square, board_hops[square]] for square in reached_squares],
        "reachable_without_type_change_squares": same_type_squares,
        "reachable_only_after_type_change_squares": transition_only_squares,
    }


def _component_membership(piece: dict[str, Any], owner: int) -> tuple[list[list[int]], dict[int, int]]:
    components = piece["owner_graphs"][str(owner)]["component_membership"]
    membership = {square: index for index, component in enumerate(components) for square in component}
    if sorted(membership) != list(range(sum(len(row) for row in components))):
        raise RuntimeError(f"ADR-128 weak components do not partition the board for owner {owner}")
    return components, membership


def _owner_type_diagnostic(
    area: int,
    type_id: str,
    types: list[str],
    pieces: dict[str, Any],
    source_rows: list[dict[str, Any]],
    owner: int,
) -> tuple[dict[str, Any], Fraction]:
    graph, transition_data = build_augmented_graph(area, types, pieces, owner)
    piece = pieces[type_id]
    components, component_of = _component_membership(piece, owner)
    if len(source_rows) != area or [int(row["source_square"]) for row in source_rows] != list(range(area)):
        raise RuntimeError(f"ADR-129 source b table is incomplete: {type_id}/{owner}")

    source_summaries: list[dict[str, Any]] = []
    transition_reachable_start_squares: set[int] = set()
    transition_sources_reachable_from: dict[str, set[int]] = {}
    b_weighted_q = Fraction(0)
    for source_row in source_rows:
        summary = summarize_source(graph, type_id, int(source_row["source_square"]), area)
        summary["u_exact"] = source_row["u_exact"]
        summary["c_exact"] = source_row["c_exact"]
        summary["b_exact"] = source_row["b_exact"]
        if _fraction(source_row["u_exact"]) + _fraction(source_row["c_exact"]) != _fraction(source_row["b_exact"]):
            raise RuntimeError(f"ADR-129 source b != u+c: {type_id}/{owner}/{source_row['source_square']}")
        if summary["reachable_current_types"] != [type_id]:
            transition_reachable_start_squares.add(int(source_row["source_square"]))
        b_weighted_q += _fraction(source_row["b_exact"]) * _fraction(summary["q_exact"])
        source_summaries.append(summary)
        reached_nodes = set(_bfs(graph, (type_id, int(source_row["source_square"]))))
        for event in transition_data["transition_event_ledger"]:
            if event["source_type"] == type_id and (type_id, event["source_square"]) in reached_nodes:
                for destination in event["destination_types"]:
                    transition_sources_reachable_from.setdefault(destination, set()).add(
                        int(source_row["source_square"]))

    terminal = not piece["type_transition_event_ledger"]
    if terminal:
        for summary in source_summaries:
            if summary["reachable_current_types"] != [type_id]:
                raise RuntimeError(f"Terminal type acquired a foreign current type: {type_id}/{owner}")
            source_square = summary["source_square"]
            if any(component_of[square] != component_of[source_square]
                   for square in summary["reachable_board_squares"]):
                raise RuntimeError(f"Terminal directed reachability crossed ADR-128 weak domain: {type_id}/{owner}")
        for source, target in piece["owner_graphs"][str(owner)]["directed_edges"]:
            if component_of[source] != component_of[target]:
                raise RuntimeError(f"Terminal edge crosses an ADR-128 weak domain: {type_id}/{owner}")

    type_edges = [edge for edge in transition_data["transition_edges"] if edge[0] == type_id]
    type_preserving = [[source, target] for source, target in piece["owner_graphs"][str(owner)]["directed_edges"]]
    owner_result = {
        "graph_node_count": len(graph),
        "graph_edge_count": sum(len(neighbors) for neighbors in graph.values()),
        "graph_sha256": _canonical_sha([
            [source_type, source_square, target_type, target_square]
            for (source_type, source_square), neighbors in sorted(graph.items())
            for target_type, target_square in neighbors
        ]),
        "type_outgoing_edge_sha256": _canonical_sha([
            [source_type, source_square, target_type, target_square]
            for source_type, source_square, target_type, target_square in
            sorted((source_type, source_square, target_type, target_square)
                    for (source_type, source_square), neighbors in graph.items()
                    for target_type, target_square in neighbors if source_type == type_id)
        ]),
        "type_preserving_edge_count": len(type_preserving),
        "transition_edge_count": len(type_edges),
        "transition_edges": [edge for edge in transition_data["transition_edges"] if edge[0] == type_id],
        "adr128_weak_component_sizes": [len(component) for component in components],
        "transition_event_ledger_for_type": [row for row in transition_data["transition_event_ledger"]
                                              if row["source_type"] == type_id],
        "source_summaries": source_summaries,
        "transition_start_source_squares": sorted(transition_reachable_start_squares),
        "fraction_start_sources_reaching_type_change_exact": _fstr(
            Fraction(len(transition_reachable_start_squares), area)),
        "transition_event_source_squares_reachable_from": {
            destination: sorted(squares)
            for destination, squares in sorted(transition_sources_reachable_from.items())
        },
        "mean_pre_transition_reachable_board_fraction_exact": _fstr(
            sum((_fraction_row_count(row["reachable_without_type_change_squares"], area)
                 for row in source_summaries), Fraction(0)) / area),
        "mean_lifetime_reachable_board_fraction_exact": _fstr(
            sum((_fraction(row["q_exact"]) for row in source_summaries), Fraction(0)) / area),
        "mean_transition_only_board_square_count_exact": _fstr(
            Fraction(sum(len(row["reachable_only_after_type_change_squares"])
                         for row in source_summaries), area)),
        "transition_only_board_squares_union": sorted({square for row in source_summaries
                                                        for square in row["reachable_only_after_type_change_squares"]}),
        "terminal_current_type": terminal,
    }
    return owner_result, b_weighted_q / area


def _fraction_row_count(squares: list[int], area: int) -> Fraction:
    return Fraction(len(squares), area)


def _validate_capability_reconstruction(
    capability_ruleset: dict[str, Any],
    v2d_ruleset: dict[str, Any],
    area: int,
    ruleset: str,
) -> None:
    if set(capability_ruleset["types"]) != set(v2d_ruleset["ledger"]):
        raise RuntimeError(f"ADR-129 and frozen V2D type sets differ: {ruleset}")
    for type_id, capability_type in capability_ruleset["types"].items():
        baseline = v2d_ruleset["ledger"][type_id]
        expected_u = _fraction(baseline["v2c_u_exact"])
        expected_c = _fraction(baseline["capture_affordance_exact"])
        expected_b = _fraction(baseline["v2d_m_exact"])
        if (_fraction(capability_type["u_exact"]) != expected_u
                or _fraction(capability_type["c_exact"]) != expected_c
                or _fraction(capability_type["b0_exact"]) != expected_b
                or expected_u + expected_c != expected_b):
            raise RuntimeError(f"ADR-129 does not reproduce frozen V2D: {ruleset}/{type_id}")
        owner_totals = {"u": Fraction(0), "c": Fraction(0), "b": Fraction(0)}
        for owner in ("0", "1"):
            owner_row = capability_type["owner_graphs"][owner]
            sources = owner_row["source_rows"]
            if len(sources) != area or [int(row["source_square"]) for row in sources] != list(range(area)):
                raise RuntimeError(f"ADR-129 owner/source table is incomplete: {ruleset}/{type_id}/{owner}")
            local = {
                "u": sum((_fraction(row["u_exact"]) for row in sources), Fraction(0)) / area,
                "c": sum((_fraction(row["c_exact"]) for row in sources), Fraction(0)) / area,
                "b": sum((_fraction(row["b_exact"]) for row in sources), Fraction(0)) / area,
            }
            for row in sources:
                if _fraction(row["u_exact"]) + _fraction(row["c_exact"]) != _fraction(row["b_exact"]):
                    raise RuntimeError(f"ADR-129 source b != u+c: {ruleset}/{type_id}/{owner}/{row['source_square']}")
            if (local["u"] != _fraction(owner_row["u_owner_average_exact"])
                    or local["c"] != _fraction(owner_row["c_owner_average_exact"])
                    or local["b"] != _fraction(owner_row["b0_owner_average_exact"])):
                raise RuntimeError(f"ADR-129 owner source average mismatch: {ruleset}/{type_id}/{owner}")
            for key in local:
                owner_totals[key] += local[key] / 2
        if (owner_totals["u"] != expected_u or owner_totals["c"] != expected_c
                or owner_totals["b"] != expected_b):
            raise RuntimeError(f"ADR-129 exact source reconstruction mismatch: {ruleset}/{type_id}")


def audit() -> dict[str, Any]:
    topology, capability, input_sha = _load_frozen_inputs()
    v2d = json.loads(V2D_RAW.read_text(encoding="utf-8"))
    compiled_sets = {
        "western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
        "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset()),
    }
    output: dict[str, Any] = {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_LIFETIME_REACHABILITY_PRE_REFERENCE_DIAGNOSTIC",
        "classification": "STATIC_MATERIAL_LIFETIME_REACHABILITY_DIAGNOSTIC_COMPLETE",
        "human_reference_imported": False,
        "human_validation_performed": False,
        "material_formula_modified": False,
        "material_candidate_created": False,
        "context_weight_used": False,
        "v2e_transition_value_used": False,
        "transport_efficiency_used": False,
        "piece_specific_logic": False,
        "game_specific_logic": False,
        "positive_probability_source": "frozen corrected V2C finite-population event model as encoded in ADR-128 positive-mass witnesses and transition ledger",
        "reachability_interpretation": "rule-topology only; graph hops are not real plies, survival probabilities, or deployment probabilities",
        "q_cap_name": "lifetime_reachability_joint_capability_diagnostic",
        "q_cap_scope": "exact random-target reachability expectation only; not a material value or score candidate",
        "input_sha256": input_sha,
        "rulesets": {},
    }

    for ruleset, compiled in compiled_sets.items():
        topology_ruleset = topology["rulesets"][ruleset]
        capability_ruleset = capability["rulesets"][ruleset]
        v2d_ruleset = v2d["rulesets"][ruleset]
        area = compiled.support.board_size ** 2
        _validate_capability_reconstruction(capability_ruleset, v2d_ruleset, area, ruleset)
        compiled_types = sorted(compiled.support.type_metadata)
        current_types = sorted(type_id for type_id, metadata in compiled.support.type_metadata.items()
                               if not metadata.is_anchor)
        if (set(compiled_types) != set(topology_ruleset["pieces"])
                or set(compiled_types) != set(capability_ruleset["types"])):
            raise RuntimeError(f"Compiled, ADR-128 and ADR-129 type sets differ: {ruleset}")
        ruleset_result: dict[str, Any] = {
            "board_area": area,
            "non_anchor_current_types": current_types,
            "anchor_types_excluded_from_augmented_graph": sorted(
                type_id for type_id, metadata in compiled.support.type_metadata.items() if metadata.is_anchor),
            "types": {},
        }
        for type_id in current_types:
            topology_piece = topology_ruleset["pieces"][type_id]
            capability_type = capability_ruleset["types"][type_id]
            type_result: dict[str, Any] = {
                "terminal_current_type": not bool(topology_piece["has_outgoing_type_transition"]),
                "frozen_v2d_u_exact": capability_type["u_exact"],
                "frozen_v2d_c_exact": capability_type["c_exact"],
                "frozen_v2d_b0_exact": capability_type["b0_exact"],
                "outgoing_destination_current_types": topology_piece["outgoing_type_transition_types"],
                "excluded_drop_ledger": topology_piece["excluded_drop_ledger"],
                "excluded_history_ledger": topology_piece["excluded_history_ledger"],
                "excluded_dynamic_legality_ledger": topology_piece["excluded_dynamic_legality_ledger"],
                "owner_graphs": {},
            }
            weighted_bq = Fraction(0)
            for owner in (0, 1):
                source_rows = capability_type["owner_graphs"][str(owner)]["source_rows"]
                owner_result, owner_bq = _owner_type_diagnostic(
                    area, type_id, current_types,
                    {current_type: topology_ruleset["pieces"][current_type] for current_type in current_types},
                    source_rows, owner)
                if owner_result["terminal_current_type"] != type_result["terminal_current_type"]:
                    raise RuntimeError(f"Transition classification differs between ADR-128 and assembled graph: {ruleset}/{type_id}")
                type_result["owner_graphs"][str(owner)] = owner_result
                weighted_bq += owner_bq
            q_cap = weighted_bq / 2
            type_result["q_cap_exact"] = _fstr(q_cap)
            type_result["source_u_c_b_sha256_by_owner"] = {
                owner: _canonical_sha(capability_type["owner_graphs"][owner]["source_rows"])
                for owner in ("0", "1")
            }
            if type_result["terminal_current_type"]:
                j_exact = capability_type["j_exact"]
                type_result["adr129_same_weak_domain_j_exact"] = j_exact
                type_result["q_cap_minus_adr129_j_exact"] = _fstr(q_cap - _fraction(j_exact))
                type_result["terminal_crosscheck_scope"] = "directed reachable board set compared descriptively with ADR-128 weak domains and ADR-129 J"
            else:
                type_result["adr129_same_weak_domain_j_exact"] = None
                type_result["q_cap_minus_adr129_j_exact"] = None
                type_result["terminal_crosscheck_scope"] = "NOT_APPLICABLE_TRANSITION_BEARING_TYPE"
            ruleset_result["types"][type_id] = type_result

        output["rulesets"][ruleset] = ruleset_result
    return output


def main() -> int:
    result = audit()
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate": str(OUTPUT), "candidate_sha256": _sha(OUTPUT),
        "classification": result["classification"],
        "rulesets": {key: len(value["types"]) for key, value in result["rulesets"].items()},
        "human_validation_performed": False, "material_candidate_created": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
