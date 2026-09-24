"""Rule-derived same-type transport efficiency under the frozen V2B measure."""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
import heapq
import json
from pathlib import Path
import sys
from typing import Any
from collections import deque

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import geometry_candidates
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_static_semantic_material_prior_v2a import (
    SUPPORTED_PATH_PREDICATES,
    SUPPORTED_TARGETS,
    _inventory_bound,
    _intrinsic_unsupported,
    _is_history_conditional,
    _make_cube,
    _promotion_forced,
    _promotion_targets,
    _source_guards_hold,
    _with_target,
    evaluate_density_polynomial,
    union_probability_polynomial,
)


def _fraction(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def opportunity_cost(probability: Fraction) -> Fraction:
    if not (Fraction(0) < probability <= Fraction(1)):
        raise ValueError("edge probability must be in (0,1]")
    return 1 / probability


def graph_metrics(
    square_count: int,
    owner_edges: dict[int, dict[tuple[int, int], Fraction]],
) -> dict[str, Any]:
    """Compute exact reciprocal shortest-path efficiency and diagnostics."""
    if square_count < 2 or not owner_edges:
        raise ValueError("transport graph needs at least two squares and one owner")
    possible = len(owner_edges) * square_count * (square_count - 1)
    efficiency_sum = Fraction(0)
    reachable = 0
    finite_hops: list[int] = []
    finite_costs: list[Fraction] = []
    direct_mass = Fraction(0)
    directed_edges = 0
    asymmetric_directions = 0

    for edges in owner_edges.values():
        adjacency: list[list[tuple[int, Fraction]]] = [[] for _ in range(square_count)]
        for (source, target), probability in edges.items():
            if not (0 <= source < square_count and 0 <= target < square_count) or source == target:
                raise ValueError("transport edges must connect distinct valid squares")
            if not (Fraction(0) < probability <= Fraction(1)):
                raise ValueError("edge probability must be in (0,1]")
            adjacency[source].append((target, opportunity_cost(probability)))
            direct_mass += probability
            directed_edges += 1
        for (source, target) in edges:
            if (target, source) not in edges:
                asymmetric_directions += 1

        for source in range(square_count):
            distances: list[Fraction | None] = [None] * square_count
            hops = [0] * square_count
            distances[source] = Fraction(0)
            pending: list[tuple[Fraction, int, int]] = [(Fraction(0), 0, source)]
            while pending:
                cost, hop_count, current = heapq.heappop(pending)
                if distances[current] != cost or hops[current] != hop_count:
                    continue
                for target, edge_cost in adjacency[current]:
                    candidate = cost + edge_cost
                    if distances[target] is None or candidate < distances[target]:
                        distances[target] = candidate
                        hops[target] = hop_count + 1
                        heapq.heappush(pending, (candidate, hop_count + 1, target))
            unweighted_hops: list[int | None] = [None] * square_count
            unweighted_hops[source] = 0
            breadth_first = deque([source])
            while breadth_first:
                current = breadth_first.popleft()
                for target, _cost in adjacency[current]:
                    if unweighted_hops[target] is None:
                        unweighted_hops[target] = unweighted_hops[current] + 1
                        breadth_first.append(target)
            for target, distance in enumerate(distances):
                if target == source or distance is None:
                    continue
                reachable += 1
                finite_costs.append(distance)
                finite_hops.append(unweighted_hops[target])
                efficiency_sum += 1 / distance

    return {
        "ordered_pair_count": possible,
        "reachable_ordered_pair_count": reachable,
        "unweighted_reachable_fraction": float(Fraction(reachable, possible)),
        "unweighted_reachable_fraction_exact": _fraction(Fraction(reachable, possible)),
        "unreachable_ordered_pair_fraction": float(Fraction(possible - reachable, possible)),
        "mean_finite_hop_distance": (sum(finite_hops) / len(finite_hops)) if finite_hops else 0.0,
        "weighted_mean_finite_transport_cost": float(sum(finite_costs, Fraction(0)) / len(finite_costs)) if finite_costs else 0.0,
        "global_transport_efficiency": float(efficiency_sum / possible),
        "global_transport_efficiency_exact": _fraction(efficiency_sum / possible),
        "one_move_direct_spatial_mass": float(direct_mass / (len(owner_edges) * square_count)),
        "directed_edge_count": directed_edges,
        "directional_asymmetry_count": asymmetric_directions,
    }


def audit_type_transport(compiled: Any, type_id: str, rho_max: Fraction | None = None) -> dict[str, Any]:
    inventory = _inventory_bound(compiled)
    if not inventory["complete"]:
        return {"coverage": "INCONCLUSIVE", "inventory_bound": inventory}
    if rho_max is None:
        rho_max = Fraction(*map(int, inventory["rho_max"].split("/")))
    square_count = inventory["board_square_count"]
    grouped_cubes: dict[tuple[int, int, int], list[tuple]] = defaultdict(list)
    unsupported: list[dict[str, Any]] = []
    history_rows: list[dict[str, Any]] = []
    held_rows: list[dict[str, Any]] = []
    dynamic_rows: set[tuple[str, str]] = set()
    transition_edges: set[tuple[int, int, int, str, bool]] = set()
    source_candidate_count = 0
    source_restricted_candidate_count = 0

    for pattern in compiled.ir.patterns:
        if type_id not in pattern.type_ids:
            continue
        for geometry_id in pattern.geometry_ids:
            geometry = compiled.ir.geometry[geometry_id]
            if geometry.kind == "drop":
                held_rows.append({"pattern": pattern.name, "kind": "held/drop", "ledgered_only": True})
                continue
            if _is_history_conditional(pattern):
                history_rows.append({"pattern": pattern.name, "geometry": geometry.kind, "ledgered_only": True})
                continue
            reasons = _intrinsic_unsupported(pattern, geometry)
            dynamic = {inv.kind for inv in pattern.invariants} & {"own_anchor_safe", "squares_not_attacked"}
            dynamic_rows.update((pattern.name, kind) for kind in dynamic)
            if reasons:
                unsupported.append({"pattern": pattern.name, "geometry": geometry.kind, "reasons": reasons})
                continue

            path_kinds = {pred.kind for pred in pattern.path}
            if path_kinds - SUPPORTED_PATH_PREDICATES:
                unsupported.append({"pattern": pattern.name, "geometry": geometry.kind,
                                    "reasons": ["path_predicate_not_exactly_modeled"]})
                continue
            clear_path = geometry.kind == "ray" or "path_clear" in path_kinds
            for owner in (0, 1):
                for source in range(square_count):
                    guard_holds = _source_guards_hold(compiled, pattern, type_id, owner, source)
                    if guard_holds is None:
                        unsupported.append({"pattern": pattern.name, "geometry": geometry.kind,
                                            "reasons": ["source_guard_evaluation_incomplete"]})
                        continue
                    for target, path in geometry_candidates(geometry, str(owner), source):
                        source_candidate_count += 1
                        if not guard_holds:
                            source_restricted_candidate_count += 1
                            continue
                        for state in sorted(SUPPORTED_TARGETS[pattern.target.kind]):
                            relation = {"empty": "target_empty", "enemy": "target_enemy",
                                        "own": "target_friendly"}[state]
                            cube = _with_target(_make_cube(path, relation, clear_path=clear_path), target)
                            promoted = _promotion_targets(compiled, type_id, owner, source, target) if pattern.promotion_mode != "none" else ()
                            forced = bool(promoted) and _promotion_forced(compiled, type_id, owner, target)
                            for final_type in promoted:
                                transition_edges.add((owner, source, target, final_type, forced))
                            if not forced:
                                grouped_cubes[(owner, source, target)].append(cube)

    owner_edges: dict[int, dict[tuple[int, int], Fraction]] = {0: {}, 1: {}}
    for (owner, source, target), cubes in grouped_cubes.items():
        polynomial = union_probability_polynomial(cubes)
        probability = evaluate_density_polynomial(polynomial, rho_max)
        if probability > 0:
            owner_edges[owner][(source, target)] = probability
    metrics = graph_metrics(square_count, owner_edges)
    return {
        "type_id": type_id,
        "coverage": "COMPLETE" if not unsupported else "INCONCLUSIVE",
        "rho_max": _fraction(rho_max),
        "metrics": metrics,
        "owner_edges": {
            str(owner): [
                {"source": source, "target": target, "probability": _fraction(probability),
                 "cost": _fraction(opportunity_cost(probability))}
                for (source, target), probability in sorted(edges.items())
            ]
            for owner, edges in owner_edges.items()
        },
        "ledger": {
            "source_candidate_count": source_candidate_count,
            "source_restricted_candidate_count": source_restricted_candidate_count,
            "dynamic_positional_legality": [
                {"pattern": pattern, "invariant": kind, "included_in_graph": False}
                for pattern, kind in sorted(dynamic_rows)
            ],
            "held_drop": held_rows,
            "history_auxiliary": history_rows,
            "type_transition_edges_excluded": [
                {"owner": owner, "source": source, "target": target,
                 "destination_type": destination_type, "forced": forced, "included_in_graph": False}
                for owner, source, target, destination_type, forced in sorted(transition_edges)
            ],
            "unsupported_intrinsic_semantics": unsupported,
        },
    }


def audit_benchmarks() -> dict[str, Any]:
    rulesets = {
        "western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
        "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset()),
    }
    result: dict[str, Any] = {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_TRANSPORT_EFFICIENCY_PRE_REFERENCE_FEATURE",
        "human_reference_imported": False,
        "v2b_residuals_imported": False,
        "density_source": "compiled initial conserved-token inventory and board area; frozen V2B rho_max",
        "edge_cost_interpretation": "expected independent opportunity samples under the fixed local V2B occupancy measure; not real-game moves or time",
        "rulesets": {},
    }
    for name, compiled in rulesets.items():
        inventory = _inventory_bound(compiled)
        rho_max = Fraction(*map(int, inventory["rho_max"].split("/")))
        types = sorted(
            type_id for type_id, metadata in compiled.support.type_metadata.items()
            if not metadata.is_anchor
        )
        rows = {type_id: audit_type_transport(compiled, type_id, rho_max) for type_id in types}
        result["rulesets"][name] = {
            "inventory_bound": inventory,
            "coverage_complete": all(row["coverage"] == "COMPLETE" for row in rows.values()),
            "type_order": types,
            "types": rows,
        }
    result["classification"] = (
        "STATIC_MATERIAL_TRANSPORT_FEATURE_READY_FOR_FROZEN_RESIDUAL_COMPARISON"
        if all(row["coverage_complete"] for row in result["rulesets"].values())
        else "STATIC_MATERIAL_TRANSPORT_FEATURE_INCONCLUSIVE"
    )
    return result


def main() -> int:
    result = audit_benchmarks()
    output = ROOT / ".generic_chess_flow" / "static-material-transport-efficiency-raw.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "classification": result["classification"],
                      "coverage": {name: row["coverage_complete"] for name, row in result["rulesets"].items()}},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
