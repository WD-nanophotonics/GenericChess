"""Freeze and independently audit V2G before reading human references."""

from __future__ import annotations

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
from scripts.audit_static_material_v2f_lifetime_reachability import _canonical_sha, _fraction
from scripts.audit_static_material_v2g_redeployment_throughput import (
    LIFETIME_FREEZE,
    LIFETIME_RAW,
    OUTPUT as RAW,
    _load_inputs,
    _sha,
    audit,
    select_target_service,
    shortest_distances,
)
from scripts.audit_static_material_v2f_lifetime_reachability import build_augmented_graph

FREEZE = ROOT / ".generic_chess_flow/static-material-v2g-redeployment-throughput-freeze.json"
FILES = (
    "docs/architecture/ADR-131-static-material-redeployment-throughput.md",
    "scripts/audit_static_material_v2g_redeployment_throughput.py",
    "scripts/freeze_static_material_v2g_redeployment_throughput.py",
    "scripts/validate_static_material_v2g_redeployment_throughput.py",
    "tests/test_static_material_v2g_redeployment_throughput.py",
    ".generic_chess_flow/static-semantic-material-prior-v2c-freeze.json",
    ".generic_chess_flow/static-semantic-material-prior-v2c-board.json",
    ".generic_chess_flow/static-semantic-material-prior-v2d-freeze.json",
    ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json",
    ".generic_chess_flow/static-material-domain-fragmentation-freeze.json",
    ".generic_chess_flow/static-material-domain-fragmentation-topology.json",
    ".generic_chess_flow/static-material-domain-conditional-capability-freeze.json",
    ".generic_chess_flow/static-material-domain-conditional-capability.json",
    ".generic_chess_flow/static-material-v2f-lifetime-reachability-freeze.json",
    ".generic_chess_flow/static-material-v2f-lifetime-reachability.json",
)


def _verify_candidate(candidate: dict[str, Any]) -> None:
    replay = audit()
    if candidate != replay:
        raise RuntimeError("V2G raw candidate differs from deterministic frozen-input recomputation")
    required_false = (
        "human_reference_imported", "human_validation_performed", "free_material_coefficient",
        "context_weight_used", "v2e_transition_value_used", "adr124_transport_cost_used",
        "density_scan_used", "piece_specific_logic", "game_specific_logic",
        "production_evaluator_modified", "score_validation_performed",
    )
    if any(candidate.get(key) is not False for key in required_false):
        raise RuntimeError("V2G candidate violates its pre-reference/no-score boundary")
    if candidate.get("distance_exponent") != 1 or candidate.get("distance_exponent_is_rate_identity") is not True:
        raise RuntimeError("V2G candidate distance rate is not the preregistered 1/d identity")
    if candidate.get("classification") != "STATIC_MATERIAL_PRIOR_V2G_REDEPLOYMENT_THROUGHPUT_PRE_REFERENCE_FROZEN":
        raise RuntimeError("V2G candidate is not complete and pre-reference")


def freeze() -> dict[str, Any]:
    if not RAW.is_file():
        raise RuntimeError("V2G raw candidate is missing")
    candidate = json.loads(RAW.read_text(encoding="utf-8"))
    _verify_candidate(candidate)
    inputs, capability, input_sha = _load_inputs()
    if candidate.get("input_sha256") != input_sha:
        raise RuntimeError("V2G candidate input SHA manifest mismatch")
    topology = inputs["topology"]

    compiled_sets = {
        "western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
        "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset()),
    }
    ruleset_manifest: dict[str, Any] = {}
    for ruleset, compiled in compiled_sets.items():
        area = compiled.support.board_size ** 2
        types = sorted(type_id for type_id, metadata in compiled.support.type_metadata.items()
                       if not metadata.is_anchor)
        topology_pieces = inputs["topology"]["rulesets"][ruleset]["pieces"]
        cap_types = capability["rulesets"][ruleset]["types"]
        candidate_ruleset = candidate["rulesets"][ruleset]
        if set(candidate_ruleset["types"]) != set(types):
            raise RuntimeError(f"V2G candidate non-anchor type set mismatch: {ruleset}")

        cap_by_owner = {}
        for owner in (0, 1):
            cap_by_owner[owner] = {
                (type_id, int(source["source_square"])): _fraction(source["b_exact"])
                for type_id in types
                for source in cap_types[type_id]["owner_graphs"][str(owner)]["source_rows"]
            }
        graph_manifest = {}
        for owner in (0, 1):
            graph, transition_data = build_augmented_graph(
                area, types, {type_id: topology_pieces[type_id] for type_id in types}, owner)
            graph_edges = [[source_type, source_square, target_type, target_square]
                           for (source_type, source_square), neighbors in sorted(graph.items())
                           for target_type, target_square in neighbors]
            graph_sha = _canonical_sha(graph_edges)
            graph_manifest[str(owner)] = {
                "graph_sha256": graph_sha,
                "graph_node_count": len(graph),
                "graph_edge_count": len(graph_edges),
                "transition_edge_sha256": _canonical_sha(transition_data["transition_edges"]),
            }
            expected_130_hashes = {
                inputs["lifetime"]["rulesets"][ruleset]["types"][type_id]["owner_graphs"][str(owner)]["graph_sha256"]
                for type_id in types
            }
            if expected_130_hashes != {graph_sha}:
                raise RuntimeError(f"ADR-130 graph hash differs from rebuilt service graph: {ruleset}/{owner}")

        type_manifest = {}
        total_targets = 0
        for type_id in types:
            type_result = candidate_ruleset["types"][type_id]
            type_caps = cap_types[type_id]
            owner_manifest = {}
            total_sum_w = Fraction(0)
            total_task_count = 0
            for owner in (0, 1):
                owner_key = str(owner)
                owner_result = type_result["owner_graphs"][owner_key]
                source_rows = type_caps["owner_graphs"][owner_key]["source_rows"]
                source_tasks = owner_result["source_tasks"]
                if len(source_tasks) != area or len(source_rows) != area:
                    raise RuntimeError(f"V2G source table coverage mismatch: {ruleset}/{type_id}/{owner}")
                graph, transition_data = build_augmented_graph(
                    area, types, {key: topology_pieces[key] for key in types}, owner)
                if owner_result["augmented_graph_sha256"] != graph_manifest[owner_key]["graph_sha256"]:
                    raise RuntimeError(f"Candidate graph hash mismatch: {ruleset}/{type_id}/{owner}")
                owner_sum = Fraction(0)
                serviced = unreachable = 0
                min_hops = selected_hops = selected_b = reciprocal_d = Fraction(0)
                changed = 0
                selected_types: dict[str, int] = {}
                for source_row, source_task in zip(source_rows, source_tasks):
                    source = int(source_row["source_square"])
                    if source_task["source_square"] != source or _fraction(source_task["source_b_exact"]) != _fraction(source_row["b_exact"]):
                        raise RuntimeError(f"V2G source binding differs from ADR-129: {ruleset}/{type_id}/{owner}/{source}")
                    distances = shortest_distances(graph, (type_id, source))
                    path_digest = _canonical_sha([[typ, square, distance]
                                                  for (typ, square), distance in sorted(distances.items())])
                    if (source_task["shortest_path_distance_sha256"] != path_digest
                            or source_task["reachable_node_count"] != len(distances)):
                        raise RuntimeError(f"V2G shortest-path digest mismatch: {ruleset}/{type_id}/{owner}/{source}")
                    stored_targets = source_task["target_tasks"]
                    expected_targets = [square for square in range(area) if square != source]
                    if (len(stored_targets) != area - 1
                            or [row[0] for row in stored_targets] != expected_targets):
                        raise RuntimeError(f"V2G distinct target enumeration mismatch: {ruleset}/{type_id}/{owner}/{source}")
                    for task_row in stored_targets:
                        target = int(task_row[0])
                        selected = select_target_service(type_id, source, target, distances, cap_by_owner[owner])
                        expected_row = [
                            target, selected["serviceable"], selected["minimum_hop_count"],
                            selected["selected_result_type"], selected["selected_distance"],
                            selected["destination_b_exact"], selected["W_exact"],
                            selected["cooptimal_result_types"],
                        ]
                        if task_row != expected_row:
                            raise RuntimeError(f"V2G target selection mismatch: {ruleset}/{type_id}/{owner}/{source}/{target}")
                        owner_sum += _fraction(selected["W_exact"])
                        if not selected["serviceable"]:
                            unreachable += 1
                            continue
                        serviced += 1
                        min_hops += int(selected["minimum_hop_count"])
                        distance = int(selected["selected_distance"])
                        selected_hops += distance
                        selected_b += _fraction(selected["destination_b_exact"])
                        reciprocal_d += Fraction(1, distance)
                        changed += selected["selected_result_type"] != type_id
                        key = selected["selected_result_type"]
                        selected_types[key] = selected_types.get(key, 0) + 1

                task_count = area * (area - 1)
                if (owner_result["sum_W_exact"] != _fstr(owner_sum)
                        or _fraction(owner_result["owner_mean_M_exact"]) != owner_sum / task_count
                        or owner_result["serviceable_target_count"] != serviced
                        or owner_result["unreachable_target_count"] != unreachable
                        or owner_result["target_task_count"] != task_count):
                    raise RuntimeError(f"V2G owner aggregate mismatch: {ruleset}/{type_id}/{owner}")
                if (_fraction(owner_result["unreachable_distinct_target_fraction_exact"])
                        != Fraction(unreachable, task_count)
                        or _fraction(owner_result["mean_finite_minimum_hops_to_target_exact"])
                        != (min_hops / serviced if serviced else Fraction(0))
                        or _fraction(owner_result["mean_selected_route_action_count_exact"])
                        != (selected_hops / serviced if serviced else Fraction(0))
                        or _fraction(owner_result["mean_selected_destination_capability_exact"])
                        != (selected_b / serviced if serviced else Fraction(0))
                        or _fraction(owner_result["mean_reciprocal_selected_distance_exact"])
                        != (reciprocal_d / serviced if serviced else Fraction(0))):
                    raise RuntimeError(f"V2G owner diagnostic aggregate mismatch: {ruleset}/{type_id}/{owner}")
                actual_transition_edges = [edge for edge in transition_data["transition_edges"] if edge[0] == type_id]
                if owner_result["transition_edges_for_start_type"] != actual_transition_edges:
                    raise RuntimeError(f"V2G outgoing transition evidence mismatch: {ruleset}/{type_id}/{owner}")
                owner_manifest[owner_key] = {
                    "sum_W_exact": _fstr(owner_sum),
                    "owner_mean_M_exact": _fstr(owner_sum / task_count),
                    "source_target_task_count": task_count,
                    "serviceable_target_count": serviced,
                    "unreachable_target_count": unreachable,
                    "source_target_table_sha256": _canonical_sha(source_tasks),
                    "selected_result_type_frequency_count": dict(sorted(selected_types.items())),
                    "outgoing_transition_edge_count": len(actual_transition_edges),
                }
                total_sum_w += owner_sum
                total_task_count += task_count
                total_targets += task_count
            if (_fraction(type_result["M_exact"]) != total_sum_w / total_task_count
                    or total_task_count != 2 * area * (area - 1)):
                raise RuntimeError(f"V2G owner/source/target score denominator mismatch: {ruleset}/{type_id}")
            type_manifest[type_id] = {
                "frozen_v2d_b0_exact": type_result["frozen_v2d_b0_exact"],
                "M_exact": type_result["M_exact"],
                "unreachable_distinct_target_fraction_exact": type_result[
                    "unreachable_distinct_target_fraction_exact"],
                "mean_finite_minimum_hops_to_requested_target_exact": type_result[
                    "mean_finite_minimum_hops_to_requested_target_exact"],
                "mean_selected_destination_capability_exact": type_result[
                    "mean_selected_destination_capability_exact"],
                "mean_reciprocal_selected_distance_exact": type_result[
                    "mean_reciprocal_selected_distance_exact"],
                "owner_augmented_graph_sha256": type_result["owner_augmented_graph_sha256"],
                "owners": owner_manifest,
            }
        ruleset_manifest[ruleset] = {
            "board_area": area,
            "non_anchor_current_types": types,
            "owner_graphs": graph_manifest,
            "total_target_task_count": total_targets,
            "types": type_manifest,
        }

    output = {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_PRIOR_V2G_REDEPLOYMENT_THROUGHPUT_PRE_REFERENCE_FREEZE",
        "classification": candidate["classification"],
        "candidate_sha256": _sha(RAW),
        "reference_data_read": False,
        "human_validation_performed": False,
        "free_material_coefficient": False,
        "context_weight_used": False,
        "distance_exponent": 1,
        "distance_exponent_is_rate_identity": True,
        "all_frozen_graph_hashes_reproduced": True,
        "all_source_local_capability_reconstructed": True,
        "all_source_target_rows_recomputed_exactly": True,
        "input_sha256": candidate["input_sha256"],
        "sha256": {relative: _sha(ROOT / relative) for relative in FILES},
        "rulesets": ruleset_manifest,
    }
    FREEZE.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _fstr(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def main() -> int:
    result = freeze()
    print(json.dumps({
        "freeze": str(FREEZE), "candidate_sha256": result["candidate_sha256"],
        "classification": result["classification"],
        "rulesets": {key: len(value["types"]) for key, value in result["rulesets"].items()},
        "target_tasks": {key: value["total_target_task_count"] for key, value in result["rulesets"].items()},
        "reference_data_read": result["reference_data_read"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
