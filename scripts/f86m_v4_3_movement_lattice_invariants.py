"""F86M final static V4-3 lattice, component, and matching diagnosis."""

from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import has_legal_action
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict

try:
    from scripts.f86i_reversibility_rescue import (
        _attack_masks,
        _build_position,
        _iter_placements,
        _ordinary_multiset,
        _zone_mask,
    )
    from scripts.f86l_mate_template_transport_support import (
        _adjacency,
        _atom_payload,
        _max_matching,
        _opening_rows,
        _reachable,
        _scc,
        _square_payload,
    )
except ModuleNotFoundError:
    from f86i_reversibility_rescue import _attack_masks, _build_position, _iter_placements, _ordinary_multiset, _zone_mask
    from f86l_mate_template_transport_support import _adjacency, _atom_payload, _max_matching, _opening_rows, _reachable, _scc, _square_payload


SAMPLE_ID = "V4-3"
F86K_MANIFEST = "artifacts/f86k_backward_rank_partial_reversibility/manifest.json"
F86I_MANIFEST = "artifacts/f86i_reversibility_rescue/manifest.json"
F86K_CAP = 256
F86I_CAP = 512
TOTAL_CAP = 768


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _bounded_census(compiled, cap: int, label: str) -> dict[str, Any]:
    n = compiled.board_size
    type_ids = _ordinary_multiset(compiled)
    templates: dict[tuple[int, tuple[tuple[str, int], ...]], set[int]] = {}
    candidate_count = 0
    validated_count = 0
    truncated = False
    for defender_anchor in range(n * n):
        zone = _zone_mask(compiled, defender_anchor)
        masks = _attack_masks(compiled, type_ids, zone)
        for placement in _iter_placements(type_ids, n, defender_anchor, masks):
            coverage = 0
            for type_id, square_index in placement:
                coverage |= masks[type_id][square_index]
            if coverage & zone != zone:
                continue
            occupied = {defender_anchor, *(square_index for _type_id, square_index in placement)}
            for attacker_anchor in range(n * n):
                if attacker_anchor in occupied:
                    continue
                if candidate_count >= cap:
                    truncated = True
                    break
                candidate_count += 1
                position = _build_position(compiled, defender_anchor, attacker_anchor, placement)
                if is_in_check(position, 0, compiled):
                    continue
                if not is_in_check(position, 1, compiled):
                    continue
                if has_legal_action(position, compiled):
                    continue
                validated_count += 1
                templates.setdefault((defender_anchor, tuple(sorted(placement))), set()).add(attacker_anchor)
            if truncated:
                break
        if truncated:
            break
    rows = []
    for ordinal, (key, targets) in enumerate(sorted(templates.items()), start=1):
        defender_anchor, placement = key
        rows.append({
            "template_id": f"{label}-T{ordinal:04d}",
            "sample_id": SAMPLE_ID,
            "defender_anchor": [defender_anchor % n, defender_anchor // n],
            "ordinary": [
                {"type_id": type_id, "square": [square % n, square // n]}
                for type_id, square in placement
            ],
            "allowed_attacker_anchor_squares": [
                [square % n, square // n] for square in sorted(targets)
            ],
        })
    return {
        "label": label,
        "candidate_position_count": candidate_count,
        "validated_position_count": validated_count,
        "validated_template_count": len(rows),
        "truncation": truncated,
        "templates": rows,
    }


def _generator_vectors(compiled, type_id: str) -> list[tuple[int, int]]:
    piece_type = next(piece for piece in compiled.piece_types if piece.type_id == type_id)
    vectors = []
    for atom in piece_type.movement_atoms:
        if isinstance(atom, LeapAtom):
            vectors.append(tuple(atom.offset))
        else:
            vectors.append(tuple(atom.direction))
    return sorted(set(vectors))


def _gcd_many(values: list[int]) -> int:
    result = 0
    for value in values:
        result = __import__("math").gcd(result, abs(value))
    return result


def _lattice_info(compiled, type_id: str) -> dict[str, Any]:
    vectors = _generator_vectors(compiled, type_id)
    nonzero = [vector for vector in vectors if vector != (0, 0)]
    coordinate_gcd = _gcd_many([value for vector in nonzero for value in vector])
    determinants = [
        left[0] * right[1] - left[1] * right[0]
        for left, right in itertools.combinations(nonzero, 2)
    ]
    index = _gcd_many(determinants)
    if not nonzero:
        rank = 0
    elif index:
        rank = 2
    else:
        rank = 1
    invariant = None
    if rank == 1:
        dx, dy = nonzero[0]
        invariant = {
            "kind": "rank_one_linear_invariant",
            "expression": f"{-dy}*file+{dx}*rank",
            "modulus": None,
            "meaning": "constant on the infinite movement lattice",
        }
    elif rank == 2 and index > 1:
        coefficients = None
        for a in range(index):
            for b in range(index):
                if (a, b) == (0, 0):
                    continue
                if all((a * dx + b * dy) % index == 0 for dx, dy in nonzero):
                    coefficients = (a, b)
                    break
            if coefficients is not None:
                break
        invariant = {
            "kind": "finite_residue_invariant",
            "expression": f"{coefficients[0]}*file+{coefficients[1]}*rank mod {index}" if coefficients else None,
            "coefficients": list(coefficients) if coefficients else None,
            "modulus": index,
        }
    smith = None
    if rank == 2:
        smith = [coordinate_gcd or 1, index // (coordinate_gcd or 1)]
    return {
        "type_id": type_id,
        "displacement_generators": [list(vector) for vector in vectors],
        "integer_lattice_rank": rank,
        "lattice_index": index if rank == 2 else None,
        "smith_invariant_factors": smith,
        "residue_or_invariant": invariant,
    }


def _component_info(compiled, type_id: str) -> dict[str, Any]:
    adjacency = _adjacency(compiled, type_id, 0)
    components, component_ids = _scc(adjacency)
    opening = [row for row in _opening_rows(compiled, all_owners=False) if row["type_id"] == type_id]
    return {
        "type_id": type_id,
        "component_count": len(components),
        "component_sizes": [len(component) for component in components],
        "opening_piece_components": [
            {"source_id": row["source_id"], "component_id": component_ids[row["square_index"]]}
            for row in opening
        ],
    }


def _owner0_sources(compiled) -> dict[str, list[dict[str, Any]]]:
    return {
        type_id: [row for row in _opening_rows(compiled, all_owners=False) if row["type_id"] == type_id]
        for type_id in sorted({row["type_id"] for row in _opening_rows(compiled, all_owners=False)})
    }


def _membership(lattice: dict[str, Any], source_index: int, target_index: int, n: int) -> bool:
    dx = target_index % n - source_index % n
    dy = target_index // n - source_index // n
    invariant = lattice["residue_or_invariant"]
    if lattice["integer_lattice_rank"] == 1:
        generator = lattice["displacement_generators"][0]
        return generator[0] * dy - generator[1] * dx == 0
    if lattice["integer_lattice_rank"] == 2 and lattice["lattice_index"]:
        a, b = invariant["coefficients"]
        return (a * dx + b * dy) % invariant["modulus"] == 0
    return True


def _invariant_value(lattice: dict[str, Any], index: int, n: int) -> int | None:
    invariant = lattice["residue_or_invariant"]
    if not invariant:
        return None
    file = index % n
    rank = index // n
    if invariant.get("coefficients"):
        a, b = invariant["coefficients"]
        return (a * file + b * rank) % invariant["modulus"]
    expression = invariant["expression"]
    if expression is not None:
        dx, dy = lattice["displacement_generators"][0]
        return -dy * file + dx * rank
    return None


def _match_edges(compiled, templates, lattice_by_type):
    n = compiled.board_size
    sources_by_type = _owner0_sources(compiled)
    graph_by_type = {
        type_id: _adjacency(compiled, type_id, 0)
        for type_id in sorted({type_id for template in templates for type_id, _square in [(item["type_id"], item["square"]) for item in template["ordinary"]]})
    }
    components_by_type = {
        type_id: _scc(graph_by_type[type_id])[1]
        for type_id in graph_by_type
    }
    all_rows = []
    for template in templates:
        targets_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in template["ordinary"]:
            type_id = item["type_id"]
            square = item["square"]
            targets_by_type[type_id].append({
                "target_id": f"{type_id}#target{len(targets_by_type[type_id]) + 1}",
                "type_id": type_id,
                "square_index": square[1] * n + square[0],
            })
        by_type = {}
        matching_sizes = {"lattice": 0, "component": 0, "final": 0}
        target_count = 0
        for type_id in sorted(targets_by_type):
            sources = sources_by_type.get(type_id, [])
            adjacency = graph_by_type[type_id]
            component_ids = components_by_type[type_id]
            reach = {source["source_id"]: set(_reachable(adjacency, source["square_index"])) for source in sources}
            lattice_edges = {source["source_id"]: {
                target["square_index"] for target in targets_by_type[type_id]
                if _membership(lattice_by_type[type_id], source["square_index"], target["square_index"], n)
            } for source in sources}
            component_edges = {source["source_id"]: {
                target["square_index"] for target in targets_by_type[type_id]
                if component_ids[source["square_index"]] == component_ids[target["square_index"]]
            } for source in sources}
            final_edges = {source["source_id"]: reach[source["source_id"]].intersection({target["square_index"] for target in targets_by_type[type_id]}) for source in sources}

            def stage_match(edge_sets):
                stage_sources = [dict(source) for source in sources]
                stage_targets = [dict(target) for target in targets_by_type[type_id]]
                return _max_matching(stage_sources, stage_targets, edge_sets)

            stage_results = {
                "lattice": stage_match(lattice_edges),
                "component": stage_match(component_edges),
                "final": stage_match(final_edges),
            }
            for stage, result in stage_results.items():
                matching_sizes[stage] += result["maximum_matching_size"]
            target_count += len(targets_by_type[type_id])
            target_rows = []
            for target in targets_by_type[type_id]:
                target_index = target["square_index"]
                source_edge_details = []
                for source in sources:
                    source_index = source["square_index"]
                    source_edge_details.append({
                        "source_id": source["source_id"],
                        "source_square": _square_payload(source_index, n),
                        "source_component_id": component_ids[source_index],
                        "source_invariant_value": _invariant_value(lattice_by_type[type_id], source_index, n),
                        "target_id": target["target_id"],
                        "target_square": _square_payload(target_index, n),
                        "target_component_id": component_ids[target_index],
                        "target_invariant_value": _invariant_value(lattice_by_type[type_id], target_index, n),
                        "delta_file": target_index % n - source_index % n,
                        "delta_rank": target_index // n - source_index // n,
                        "lattice_membership": _membership(lattice_by_type[type_id], source_index, target_index, n),
                        "finite_board_reachable": target_index in reach[source["source_id"]],
                    })
                target_rows.append({
                    "target_id": target["target_id"],
                    "target_square": _square_payload(target_index, n),
                    "target_component_id": component_ids[target_index],
                    "target_invariant_value": _invariant_value(lattice_by_type[type_id], target_index, n),
                    "lattice_reachable_source_ids": [source["source_id"] for source in sources if target_index in lattice_edges[source["source_id"]]],
                    "component_reachable_source_ids": [source["source_id"] for source in sources if target_index in component_edges[source["source_id"]]],
                    "final_reachable_source_ids": [source["source_id"] for source in sources if target_index in final_edges[source["source_id"]]],
                    "source_target_edge_details": source_edge_details,
                })
            by_type[type_id] = {
                "source_ids": [source["source_id"] for source in sources],
                "target_rows": target_rows,
                "matching_sizes": {stage: result["maximum_matching_size"] for stage, result in stage_results.items()},
                "hall_deficiency_final": len(targets_by_type[type_id]) - stage_results["final"]["maximum_matching_size"],
            }
        if matching_sizes["lattice"] < target_count:
            primary = "LATTICE_INVARIANT_OBSTRUCTION"
        elif matching_sizes["component"] < target_count:
            primary = "FINITE_BOARD_COMPONENT_OBSTRUCTION"
        elif matching_sizes["final"] < target_count:
            primary = "DUPLICATE_MATCHING_HALL_OBSTRUCTION"
        else:
            primary = "COMPLETE_TYPE_PRESERVING_MATCHING"
        all_rows.append({
            "template_id": template["template_id"],
            "ordinary": template["ordinary"],
            "by_type": by_type,
            "matching_sizes": matching_sizes,
            "hall_deficiency_final": target_count - matching_sizes["final"],
            "failure_mechanism": primary,
        })
    return all_rows


def _batch_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = defaultdict(int)
    for row in rows:
        counts[row["failure_mechanism"]] += 1
    return {
        "template_count": len(rows),
        "templates_blocked_at_lattice_level": counts["LATTICE_INVARIANT_OBSTRUCTION"],
        "templates_passing_lattice_but_blocked_by_finite_board": counts["FINITE_BOARD_COMPONENT_OBSTRUCTION"],
        "templates_whose_only_remaining_failure_is_duplicate_hall": counts["DUPLICATE_MATCHING_HALL_OBSTRUCTION"],
        "templates_with_complete_ordinary_assignment": counts["COMPLETE_TYPE_PRESERVING_MATCHING"],
        "failure_mechanism_counts": dict(sorted(counts.items())),
    }


def _coverage_indicators(compiled, ordinary_types: list[str]) -> dict[str, Any]:
    n = compiled.board_size
    sources = _owner0_sources(compiled)
    rows = {}
    for type_id in ordinary_types:
        adjacency = _adjacency(compiled, type_id, 0)
        reachable_by_source = {
            source["source_id"]: set(_reachable(adjacency, source["square_index"]))
            for source in sources.get(type_id, [])
        }
        union = set().union(*reachable_by_source.values()) if reachable_by_source else set()
        components = _scc(adjacency)[1]
        rows[type_id] = {
            "opening_source_count": len(reachable_by_source),
            "opening_source_reachable_board_fraction": len(union) / (n * n) if union else 0.0,
            "same_type_source_union_square_count": len(union),
            "same_type_source_component_diversity": len({components[source["square_index"]] for source in sources.get(type_id, [])}),
            "opening_source_pairwise_union_overlap": {
                "pairs": len(list(itertools.combinations(reachable_by_source, 2))),
                "overlap_counts": [
                    len(reachable_by_source[left].intersection(reachable_by_source[right]))
                    for left, right in itertools.combinations(sorted(reachable_by_source), 2)
                ],
            },
        }
    return rows


def run(root: Path, output: Path) -> dict[str, Any]:
    f86k_manifest = _load_json(root, F86K_MANIFEST)
    f86i_manifest = _load_json(root, F86I_MANIFEST)
    f86k_entry = next(row for row in f86k_manifest["entries"] if row["sample_id"] == SAMPLE_ID)
    f86i_entry = next(row for row in f86i_manifest["entries"] if row["sample_id"] == SAMPLE_ID)
    f86k_compiled = compile_ruleset(ruleset_from_dict(f86k_entry["candidate_ruleset"]))
    f86i_compiled = compile_ruleset(ruleset_from_dict(f86i_entry["candidate_ruleset"]))
    if f86k_compiled.ruleset_fingerprint != f86k_entry["candidate_ruleset_fingerprint"]:
        raise RuntimeError("F86K fingerprint drift")
    if f86i_compiled.ruleset_fingerprint != f86i_entry["candidate_ruleset_fingerprint"]:
        raise RuntimeError("F86I fingerprint drift")

    f86k_census = _bounded_census(f86k_compiled, F86K_CAP, "F86K")
    f86i_census = _bounded_census(f86i_compiled, F86I_CAP, "F86I")
    if f86k_census["candidate_position_count"] + f86i_census["candidate_position_count"] > TOTAL_CAP:
        raise RuntimeError("F86M total census cap exceeded")
    if (f86k_census["candidate_position_count"], f86k_census["validated_position_count"], f86k_census["validated_template_count"], f86k_census["truncation"]) != (156, 111, 12, False):
        raise RuntimeError("F86K census authority drift")
    if (f86i_census["candidate_position_count"], f86i_census["validated_position_count"], f86i_census["validated_template_count"], f86i_census["truncation"]) != (504, 398, 40, False):
        raise RuntimeError("F86I census authority drift")

    ordinary_types = sorted({piece.type_id for piece in f86i_compiled.piece_types if not piece.is_anchor})
    lattice = [_lattice_info(f86i_compiled, type_id) for type_id in ordinary_types]
    components = [_component_info(f86i_compiled, type_id) for type_id in ordinary_types]
    lattice_by_type = {row["type_id"]: row for row in lattice}
    f86k_matching = _match_edges(f86i_compiled, f86k_census["templates"], lattice_by_type)
    f86i_matching = _match_edges(f86i_compiled, f86i_census["templates"], lattice_by_type)

    routes = []
    summaries = {"F86K": _batch_summary(f86k_matching), "F86I": _batch_summary(f86i_matching)}
    for label, summary in summaries.items():
        if summary["templates_blocked_at_lattice_level"] > max(summary["templates_passing_lattice_but_blocked_by_finite_board"], summary["templates_whose_only_remaining_failure_is_duplicate_hall"], summary["templates_with_complete_ordinary_assignment"]):
            route = "MOVEMENT_LATTICE_INVARIANTS_DOMINATE_V4_3_TRANSPORT_FAILURE"
        elif summary["templates_passing_lattice_but_blocked_by_finite_board"] > max(summary["templates_whose_only_remaining_failure_is_duplicate_hall"], summary["templates_with_complete_ordinary_assignment"]):
            route = "FINITE_BOARD_COMPONENT_GEOMETRY_DOMINATES_V4_3_TRANSPORT_FAILURE"
        elif summary["templates_whose_only_remaining_failure_is_duplicate_hall"] > summary["templates_with_complete_ordinary_assignment"]:
            route = "MATERIAL_ASSIGNMENT_HALL_CONSTRAINT_DOMINATES_V4_3_TRANSPORT_FAILURE"
        else:
            route = "V4_3_TRANSPORT_FAILURE_IS_MULTI_MECHANISM"
        routes.append({"batch": label, "routing": route})
    if len({row["routing"] for row in routes}) == 1:
        primary_route = routes[0]["routing"]
    else:
        primary_route = "V4_3_TRANSPORT_FAILURE_IS_MULTI_MECHANISM"

    payload = {
        "schema_version": 1,
        "status": "F86M_STATIC_DIAGNOSTIC_ZERO_DYNAMIC_COMPUTE",
        "sample_id": SAMPLE_ID,
        "baseline": "26005ae40f834a7180e8ad7a6b0dee8e2f478ce3",
        "fingerprints": {
            "f86k_candidate": f86k_entry["candidate_ruleset_fingerprint"],
            "f86i_full_closure_candidate": f86i_entry["candidate_ruleset_fingerprint"],
        },
        "hard_caps": {
            "f86k_checks": F86K_CAP,
            "f86i_checks": F86I_CAP,
            "total_checks": TOTAL_CAP,
            "execution_time_enforced": True,
        },
        "census": {
            "F86K": {key: f86k_census[key] for key in ("candidate_position_count", "validated_position_count", "validated_template_count", "truncation")},
            "F86I": {key: f86i_census[key] for key in ("candidate_position_count", "validated_position_count", "validated_template_count", "truncation")},
            "total_candidate_checks": f86k_census["candidate_position_count"] + f86i_census["candidate_position_count"],
        },
        "movement_lattice": lattice,
        "finite_board_components": components,
        "coverage_indicators": _coverage_indicators(f86i_compiled, ordinary_types),
        "matching": {"F86K": f86k_matching, "F86I": f86i_matching},
        "batch_summaries": summaries,
        "routing": {"per_batch": routes, "primary": primary_route},
        "diagnostic_indicators": {
            "opening_source_reachable_board_fraction": "reported per source in matching evidence",
            "same_type_source_union_coverage": "reported per target type in matching evidence",
            "source_component_diversity": "reported in finite_board_components",
            "mate_target_hall_capacity": "reported per template in matching evidence",
        },
        "dynamic": {"real_games": 0, "tactical_nodes": 0, "bfs_expansions": 0, "teacher_search_training": 0, "f85_actual_compute": 0},
        "default_generator_changed": False,
    }
    _write_json(output, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("artifacts/f86m_v4_3_movement_lattice_invariants/diagnosis.json"))
    args = parser.parse_args()
    payload = run(args.root, args.output)
    print(json.dumps({"status": payload["status"], "primary_route": payload["routing"]["primary"], "total_checks": payload["census"]["total_candidate_checks"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
