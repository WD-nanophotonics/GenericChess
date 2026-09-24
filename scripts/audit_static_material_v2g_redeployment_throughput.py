"""Build the frozen rule-derived semantic redeployment-throughput candidate."""

from __future__ import annotations

from collections import Counter, deque
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_static_material_v2f_lifetime_reachability import (
    CAPABILITY_FREEZE,
    CAPABILITY_RAW,
    TOPOLOGY_FREEZE,
    TOPOLOGY_RAW,
    V2C_FREEZE,
    V2C_RAW,
    V2D_FREEZE,
    V2D_RAW,
    _canonical_sha,
    _fraction,
    _load_frozen_inputs,
    _sha,
    _validate_capability_reconstruction,
    build_augmented_graph,
)

LIFETIME_RAW = ROOT / ".generic_chess_flow/static-material-v2f-lifetime-reachability.json"
LIFETIME_FREEZE = ROOT / ".generic_chess_flow/static-material-v2f-lifetime-reachability-freeze.json"
OUTPUT = ROOT / ".generic_chess_flow/static-material-v2g-redeployment-throughput.json"


def _fstr(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _verify_manifest(path: Path, manifest: dict[str, Any]) -> None:
    for relative, expected in manifest.get("sha256", {}).items():
        source = ROOT / relative
        if not source.is_file() or _sha(source) != expected:
            raise RuntimeError(f"Frozen source hash mismatch: {path.name}: {relative}")


def _load_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    topology, capability, upstream_sha = _load_frozen_inputs()
    if not LIFETIME_RAW.is_file() or not LIFETIME_FREEZE.is_file():
        raise RuntimeError("Frozen ADR-130 lifetime graph is unavailable")
    lifetime = json.loads(LIFETIME_RAW.read_text(encoding="utf-8"))
    lifetime_freeze = json.loads(LIFETIME_FREEZE.read_text(encoding="utf-8"))
    _verify_manifest(LIFETIME_FREEZE, lifetime_freeze)
    if _sha(LIFETIME_RAW) != lifetime_freeze.get("candidate_sha256"):
        raise RuntimeError("ADR-130 candidate SHA differs from its pre-reference freeze")
    if lifetime_freeze.get("reference_data_read") is not False or lifetime_freeze.get("human_validation_performed") is not False:
        raise RuntimeError("ADR-130 was not frozen before human-reference access")
    if (lifetime_freeze.get("material_formula_modified") is not False
            or lifetime_freeze.get("material_candidate_created") is not False):
        raise RuntimeError("ADR-130 contains a material-score candidate")
    if any(lifetime.get(key) is not False for key in (
        "human_reference_imported", "human_validation_performed", "material_formula_modified",
        "material_candidate_created", "context_weight_used", "v2e_transition_value_used",
        "transport_efficiency_used", "piece_specific_logic", "game_specific_logic",
    )):
        raise RuntimeError("ADR-130 raw diagnostic violates its score/reference boundary")
    if lifetime.get("classification") != "STATIC_MATERIAL_LIFETIME_REACHABILITY_DIAGNOSTIC_COMPLETE":
        raise RuntimeError("ADR-130 is not complete")
    if lifetime_freeze.get("candidate_sha256") != _sha(LIFETIME_RAW):
        raise RuntimeError("ADR-130 freeze does not bind the candidate bytes")
    if lifetime.get("input_sha256") != upstream_sha:
        raise RuntimeError("ADR-130 frozen upstream inputs differ from current source files")
    return ({"topology": topology, "lifetime": lifetime}, capability, {
        **upstream_sha,
        "adr130_freeze": _sha(LIFETIME_FREEZE),
        "adr130_candidate": _sha(LIFETIME_RAW),
    })


def shortest_distances(
    graph: dict[tuple[str, int], tuple[tuple[str, int], ...]],
    start: tuple[str, int],
) -> dict[tuple[str, int], int]:
    """Unit-cost directed shortest paths; one semantic own action per edge."""
    distance = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in distance:
                distance[neighbor] = distance[node] + 1
                queue.append(neighbor)
    return distance


def select_target_service(
    start_type: str,
    source_square: int,
    target_square: int,
    distances: dict[tuple[str, int], int],
    capability: dict[tuple[str, int], Fraction],
) -> dict[str, Any]:
    """Select max destination capability/action rate for one distinct target."""
    if source_square == target_square:
        raise ValueError("The target ensemble excludes the source square")
    choices = []
    for (result_type, square), distance in distances.items():
        if square != target_square or distance < 1:
            continue
        local_b = capability[(result_type, square)]
        choices.append((local_b / distance, result_type, distance, local_b))
    if not choices:
        return {
            "serviceable": False,
            "minimum_hop_count": None,
            "selected_result_type": None,
            "selected_distance": None,
            "destination_b_exact": None,
            "W_exact": "0/1",
            "cooptimal_result_types": [],
        }
    best_rate = max(row[0] for row in choices)
    cooptimal = sorted((row for row in choices if row[0] == best_rate),
                       key=lambda row: (row[2], row[1]))
    selected = cooptimal[0]
    return {
        "serviceable": True,
        "minimum_hop_count": min(row[2] for row in choices),
        "selected_result_type": selected[1],
        "selected_distance": selected[2],
        "destination_b_exact": _fstr(selected[3]),
        "W_exact": _fstr(best_rate),
        "cooptimal_result_types": sorted({row[1] for row in cooptimal}),
    }


def _distance_digest(distances: dict[tuple[str, int], int]) -> str:
    return _canonical_sha([[type_id, square, distance]
                           for (type_id, square), distance in sorted(distances.items())])


def _owner_type_score(
    area: int,
    type_id: str,
    graph: dict[tuple[str, int], tuple[tuple[str, int], ...]],
    capability_by_node: dict[tuple[str, int], Fraction],
    source_rows: list[dict[str, Any]],
    lifetime_source_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if (len(source_rows) != area or len(lifetime_source_rows) != area
            or [int(row["source_square"]) for row in source_rows] != list(range(area))
            or [int(row["source_square"]) for row in lifetime_source_rows] != list(range(area))):
        raise RuntimeError(f"Frozen capability/reachability source table is incomplete: {type_id}")
    tasks_per_source = area - 1
    reachable_target_count = unreachable_target_count = 0
    minimum_hop_sum = selected_distance_sum = selected_b_sum = reciprocal_distance_sum = Fraction(0)
    selected_rate_sum = Fraction(0)
    selected_type_counts: Counter[str] = Counter()
    changed_type_count = 0
    source_task_rows = []
    for source_row, lifetime_row in zip(source_rows, lifetime_source_rows):
        source_square = int(source_row["source_square"])
        if (_fraction(source_row["u_exact"]) + _fraction(source_row["c_exact"])
                != _fraction(source_row["b_exact"])):
            raise RuntimeError(f"Frozen ADR-129 source capability b != u+c: {type_id}/{source_square}")
        start = (type_id, source_square)
        distances = shortest_distances(graph, start)
        if len(distances) != int(lifetime_row["reachable_node_count"]):
            raise RuntimeError(f"ADR-130 reachable node count differs from reconstructed graph: {type_id}/{source_square}")
        reachable_node_digest = _canonical_sha([list(node) for node in sorted(distances)])
        if reachable_node_digest != lifetime_row.get("reachable_node_sha256"):
            raise RuntimeError(f"ADR-130 reachable node digest differs: {type_id}/{source_square}")
        task_rows = []
        for target_square in range(area):
            if target_square == source_square:
                continue
            selection = select_target_service(type_id, source_square, target_square, distances, capability_by_node)
            # Compact fixed-position row: target, serviceability, min hop,
            # selected type, selected distance, destination b, W, co-optimal IDs.
            task_rows.append([
                target_square, selection["serviceable"], selection["minimum_hop_count"],
                selection["selected_result_type"], selection["selected_distance"],
                selection["destination_b_exact"], selection["W_exact"],
                selection["cooptimal_result_types"],
            ])
            if not selection["serviceable"]:
                unreachable_target_count += 1
                continue
            reachable_target_count += 1
            minimum_hop_sum += int(selection["minimum_hop_count"])
            selected_distance_sum += int(selection["selected_distance"])
            selected_b_sum += _fraction(selection["destination_b_exact"])
            inverse_distance = Fraction(1, int(selection["selected_distance"]))
            reciprocal_distance_sum += inverse_distance
            selected_rate_sum += _fraction(selection["W_exact"])
            selected_type = selection["selected_result_type"]
            selected_type_counts[selected_type] += 1
            changed_type_count += selected_type != type_id
        source_task_rows.append({
            "source_square": source_square,
            "source_u_exact": source_row["u_exact"],
            "source_c_exact": source_row["c_exact"],
            "source_b_exact": source_row["b_exact"],
            "source_lifetime_q_exact": lifetime_row["q_exact"],
            "shortest_path_distance_sha256": _distance_digest(distances),
            "reachable_node_count": len(distances),
            "target_tasks": task_rows,
        })

    total_targets = area * tasks_per_source
    if reachable_target_count + unreachable_target_count != total_targets:
        raise RuntimeError(f"Target task count mismatch: {type_id}")
    return {
        "serviceable_target_count": reachable_target_count,
        "unreachable_target_count": unreachable_target_count,
        "target_task_count": total_targets,
        "sum_W_exact": _fstr(selected_rate_sum),
        "owner_mean_M_exact": _fstr(selected_rate_sum / total_targets),
        "unreachable_distinct_target_fraction_exact": _fstr(Fraction(unreachable_target_count, total_targets)),
        "fraction_selected_state_changes_type_among_serviceable_exact": _fstr(
            Fraction(changed_type_count, reachable_target_count) if reachable_target_count else Fraction(0)),
        "fraction_selected_state_changes_type_among_all_targets_exact": _fstr(
            Fraction(changed_type_count, total_targets)),
        "mean_finite_minimum_hops_to_target_exact": _fstr(
            minimum_hop_sum / reachable_target_count if reachable_target_count else Fraction(0)),
        "mean_selected_route_action_count_exact": _fstr(
            selected_distance_sum / reachable_target_count if reachable_target_count else Fraction(0)),
        "mean_selected_destination_capability_exact": _fstr(
            selected_b_sum / reachable_target_count if reachable_target_count else Fraction(0)),
        "mean_reciprocal_selected_distance_exact": _fstr(
            reciprocal_distance_sum / reachable_target_count if reachable_target_count else Fraction(0)),
        "selected_result_type_frequency_count": dict(sorted(selected_type_counts.items())),
        "selected_result_type_frequency_exact": {
            result_type: _fstr(Fraction(count, reachable_target_count))
            for result_type, count in sorted(selected_type_counts.items())
        } if reachable_target_count else {},
        "source_tasks": source_task_rows,
    }


def audit() -> dict[str, Any]:
    inputs, capability, input_sha = _load_inputs()
    topology = inputs["topology"]
    lifetime = inputs["lifetime"]
    v2d = json.loads(V2D_RAW.read_text(encoding="utf-8"))
    compiled_sets = {
        "western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
        "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset()),
    }
    result: dict[str, Any] = {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_PRIOR_V2G_REDEPLOYMENT_THROUGHPUT_PRE_REFERENCE_CANDIDATE",
        "classification": "STATIC_MATERIAL_PRIOR_V2G_REDEPLOYMENT_THROUGHPUT_PRE_REFERENCE_FROZEN",
        "human_reference_imported": False,
        "human_validation_performed": False,
        "free_material_coefficient": False,
        "context_weight_used": False,
        "distance_exponent": 1,
        "distance_exponent_is_rate_identity": True,
        "v2e_transition_value_used": False,
        "adr124_transport_cost_used": False,
        "density_scan_used": False,
        "piece_specific_logic": False,
        "game_specific_logic": False,
        "production_evaluator_modified": False,
        "score_validation_performed": False,
        "formula": "M(t)=(1/(2*A*(A-1)))*sum_o,sum_s,sum_{v!=s} max_{reachable r at v} b(o,r,v)/d((t,s),(r,v)); unreachable targets contribute zero",
        "service_model_boundary": (
            "Optimistic structural potential only: semantic reachability and shortest own-action counts do not guarantee control of opponent occupancy, joint executability of a full route in one game, survival, strategic safety, or realized deployment. Destination b is latent local capability at arrival, not a move already performed."
        ),
        "deterministic_tie_break": "Co-optimal states have identical W; report one by shortest distance then lexical current-type ID. This tie-break does not alter M and selected-type frequencies are diagnostic only.",
        "source_target_task_row_schema": [
            "target_square", "serviceable", "minimum_hop_count", "selected_result_type",
            "selected_distance", "destination_b_exact", "W_exact", "cooptimal_result_types",
        ],
        "input_sha256": input_sha,
        "rulesets": {},
    }

    for ruleset, compiled in compiled_sets.items():
        area = compiled.support.board_size ** 2
        current_types = sorted(type_id for type_id, metadata in compiled.support.type_metadata.items()
                               if not metadata.is_anchor)
        topology_ruleset = topology["rulesets"][ruleset]
        capability_ruleset = capability["rulesets"][ruleset]
        lifetime_ruleset = lifetime["rulesets"][ruleset]
        v2d_ruleset = v2d["rulesets"][ruleset]
        _validate_capability_reconstruction(capability_ruleset, v2d_ruleset, area, ruleset)
        if set(current_types) != set(lifetime_ruleset["types"]):
            raise RuntimeError(f"Non-anchor current type set differs from frozen ADR-130: {ruleset}")
        owner_graphs = {}
        for owner in (0, 1):
            graph, transition_data = build_augmented_graph(
                area, current_types,
                {type_id: topology_ruleset["pieces"][type_id] for type_id in current_types}, owner)
            graph_edges = [[source_type, source_square, target_type, target_square]
                           for (source_type, source_square), neighbors in sorted(graph.items())
                           for target_type, target_square in neighbors]
            graph_sha = _canonical_sha(graph_edges)
            expected_hashes = {
                lifetime_ruleset["types"][type_id]["owner_graphs"][str(owner)]["graph_sha256"]
                for type_id in current_types
            }
            if expected_hashes != {graph_sha}:
                raise RuntimeError(f"ADR-130 augmented graph SHA reproduction failed: {ruleset}/{owner}")
            owner_graphs[str(owner)] = {
                "graph": graph,
                "graph_sha256": graph_sha,
                "transition_data": transition_data,
            }

        capability_by_owner_type = {}
        for type_id in current_types:
            cap_type = capability_ruleset["types"][type_id]
            for owner in (0, 1):
                rows = cap_type["owner_graphs"][str(owner)]["source_rows"]
                capability_by_owner_type[(owner, type_id)] = {
                    (type_id, int(row["source_square"])): _fraction(row["b_exact"])
                    for row in rows
                }

        ruleset_result: dict[str, Any] = {
            "board_area": area,
            "non_anchor_current_types": current_types,
            "anchor_types_excluded": sorted(type_id for type_id, metadata in
                                             compiled.support.type_metadata.items() if metadata.is_anchor),
            "types": {},
        }
        for type_id in current_types:
            capability_type = capability_ruleset["types"][type_id]
            lifetime_type = lifetime_ruleset["types"][type_id]
            owner_results = {}
            total_sum_w = Fraction(0)
            total_serviceable = total_unreachable = 0
            total_changed = 0
            total_min_hops = total_selected_hops = Fraction(0)
            total_selected_b = total_inverse_d = Fraction(0)
            type_counts: Counter[str] = Counter()
            q_sum = Fraction(0)
            for owner in (0, 1):
                owner_key = str(owner)
                graph_info = owner_graphs[owner_key]
                cap_sources = capability_type["owner_graphs"][owner_key]["source_rows"]
                q_sources = lifetime_type["owner_graphs"][owner_key]["source_summaries"]
                owner_result = _owner_type_score(
                    area, type_id, graph_info["graph"],
                    {**{node: b for (own, typ), table in capability_by_owner_type.items()
                        if own == owner for node, b in table.items()}},
                    cap_sources, q_sources,
                )
                # _owner_type_score requires all resulting-type destination b values.
                # The merged owner map above is complete for this ruleset.
                owner_result["augmented_graph_sha256"] = graph_info["graph_sha256"]
                owner_result["transition_edges_for_start_type"] = [
                    edge for edge in graph_info["transition_data"]["transition_edges"] if edge[0] == type_id]
                owner_result["transition_edge_count_for_start_type"] = len(
                    owner_result["transition_edges_for_start_type"])
                owner_result["transition_event_ledger_for_start_type"] = [
                    row for row in graph_info["transition_data"]["transition_event_ledger"]
                    if row["source_type"] == type_id]
                owner_results[owner_key] = owner_result
                total_sum_w += _fraction(owner_result["sum_W_exact"])
                total_serviceable += owner_result["serviceable_target_count"]
                total_unreachable += owner_result["unreachable_target_count"]
                total_changed += int(_fraction(owner_result[
                    "fraction_selected_state_changes_type_among_all_targets_exact"])
                    * owner_result["target_task_count"])
                total_min_hops += (_fraction(owner_result["mean_finite_minimum_hops_to_target_exact"])
                                   * owner_result["serviceable_target_count"])
                total_selected_hops += (_fraction(owner_result["mean_selected_route_action_count_exact"])
                                        * owner_result["serviceable_target_count"])
                total_selected_b += (_fraction(owner_result["mean_selected_destination_capability_exact"])
                                     * owner_result["serviceable_target_count"])
                total_inverse_d += (_fraction(owner_result["mean_reciprocal_selected_distance_exact"])
                                    * owner_result["serviceable_target_count"])
                type_counts.update(owner_result["selected_result_type_frequency_count"])
                q_sum += sum((_fraction(row["q_exact"]) for row in q_sources), Fraction(0)) / area

            total_tasks = 2 * area * (area - 1)
            m_value = total_sum_w / total_tasks
            b0 = _fraction(capability_type["b0_exact"])
            serviceable_denominator = total_serviceable
            type_result = {
                "frozen_v2d_b0_exact": capability_type["b0_exact"],
                "adr130_mean_lifetime_reachable_board_fraction_exact": _fstr(q_sum / 2),
                "mean_finite_minimum_hops_to_requested_target_exact": _fstr(
                    total_min_hops / serviceable_denominator if serviceable_denominator else Fraction(0)),
                "mean_selected_route_action_count_exact": _fstr(
                    total_selected_hops / serviceable_denominator if serviceable_denominator else Fraction(0)),
                "unreachable_distinct_target_fraction_exact": _fstr(Fraction(total_unreachable, total_tasks)),
                "fraction_selected_state_changes_type_among_serviceable_exact": _fstr(
                    Fraction(total_changed, serviceable_denominator) if serviceable_denominator else Fraction(0)),
                "fraction_selected_state_changes_type_among_all_targets_exact": _fstr(
                    Fraction(total_changed, total_tasks)),
                "mean_selected_destination_capability_exact": _fstr(
                    total_selected_b / serviceable_denominator if serviceable_denominator else Fraction(0)),
                "mean_reciprocal_selected_distance_exact": _fstr(
                    total_inverse_d / serviceable_denominator if serviceable_denominator else Fraction(0)),
                "serviceable_target_count": total_serviceable,
                "target_task_count": total_tasks,
                "M_exact": _fstr(m_value),
                "selected_result_type_frequency_count_diagnostic_only": dict(sorted(type_counts.items())),
                "selected_result_type_frequency_exact_diagnostic_only": {
                    key: _fstr(Fraction(count, total_serviceable))
                    for key, count in sorted(type_counts.items())
                } if total_serviceable else {},
                "owner_graphs": owner_results,
                "owner_augmented_graph_sha256": {
                    owner: owner_graphs[owner]["graph_sha256"] for owner in ("0", "1")
                },
                "type_transition_event_ledger": {
                    owner: lifetime_type["owner_graphs"][owner]["transition_event_ledger_for_type"]
                    for owner in ("0", "1")
                },
                "excluded_drop_ledger": lifetime_type["excluded_drop_ledger"],
                "excluded_history_ledger": lifetime_type["excluded_history_ledger"],
                "excluded_dynamic_legality_ledger": lifetime_type["excluded_dynamic_legality_ledger"],
            }
            if m_value < 0 or b0 < 0:
                raise RuntimeError(f"Negative frozen capability or V2G score: {ruleset}/{type_id}")
            ruleset_result["types"][type_id] = type_result
        result["rulesets"][ruleset] = ruleset_result
    return result


def main() -> int:
    result = audit()
    OUTPUT.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate": str(OUTPUT), "candidate_sha256": _sha(OUTPUT),
        "classification": result["classification"],
        "rulesets": {key: len(value["types"]) for key, value in result["rulesets"].items()},
        "human_validation_performed": result["human_validation_performed"],
        "free_material_coefficient": result["free_material_coefficient"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
