"""F86L diagnostic-only transport support analysis for the F86K V4-3 templates."""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict

try:
    from scripts.f86i_reversibility_rescue import _candidate_static_census, _reverse_atom
    from scripts.f86k_backward_rank_partial_reversibility import (
        _owner_relative_rank,
        _source_rows,
    )
except ModuleNotFoundError:
    from f86i_reversibility_rescue import _candidate_static_census, _reverse_atom
    from f86k_backward_rank_partial_reversibility import _owner_relative_rank, _source_rows


SAMPLE_ID = "V4-3"
F86K_MANIFEST = "artifacts/f86k_backward_rank_partial_reversibility/manifest.json"
F86I_MANIFEST = "artifacts/f86i_reversibility_rescue/manifest.json"
MAX_CENSUS_CHECKS = 256


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _atom_key(atom) -> tuple:
    if isinstance(atom, LeapAtom):
        return ("LEAP", tuple(atom.offset))
    return ("RAY", tuple(atom.direction), atom.max_steps)


def _atom_payload(atom) -> dict[str, Any]:
    if isinstance(atom, LeapAtom):
        return {"kind": "LEAP", "offset": list(atom.offset)}
    return {"kind": "RAY", "direction": list(atom.direction), "max_steps": atom.max_steps}


def _square_payload(index: int, board_size: int) -> list[int]:
    return [index % board_size, index // board_size]


def _adjacency(compiled, type_id: str, owner: int) -> tuple[tuple[int, ...], ...]:
    n = compiled.board_size
    return tuple(
        tuple(sorted(target.rank * n + target.file for target in compiled.empty_mobility[type_id][owner][source]))
        for source in range(n * n)
    )


def _scc(adjacency: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], dict[int, int]]:
    index = 0
    stack: list[int] = []
    on_stack: set[int] = set()
    indices: dict[int, int] = {}
    low: dict[int, int] = {}
    components: list[tuple[int, ...]] = []

    def visit(node: int) -> None:
        nonlocal index
        indices[node] = index
        low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in adjacency[node]:
            if target not in indices:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], indices[target])
        if low[node] == indices[node]:
            component = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            components.append(tuple(sorted(component)))

    for node in range(len(adjacency)):
        if node not in indices:
            visit(node)
    components.sort(key=lambda component: component[0])
    ids = {node: component_id for component_id, component in enumerate(components) for node in component}
    return tuple(components), ids


def _reachable(adjacency: tuple[tuple[int, ...], ...], source: int) -> tuple[int, ...]:
    visited = {source}
    queue = [source]
    while queue:
        current = queue.pop(0)
        for target in adjacency[current]:
            if target not in visited:
                visited.add(target)
                queue.append(target)
    return tuple(sorted(visited))


def _opening_rows(compiled, *, all_owners: bool = True) -> list[dict[str, Any]]:
    anchor_type = next(piece_type.type_id for piece_type in compiled.piece_types if piece_type.is_anchor)
    rows = []
    ordinal_by_type: dict[tuple[int, str], int] = {}
    for index, piece in enumerate(compiled.initial_position.board):
        if piece is None or piece.current_type_id == anchor_type:
            continue
        if not all_owners and piece.owner != 0:
            continue
        key = (piece.owner, piece.current_type_id)
        ordinal_by_type[key] = ordinal_by_type.get(key, 0) + 1
        rows.append({
            "source_id": f"{piece.current_type_id}@o{piece.owner}#{ordinal_by_type[key]}",
            "type_id": piece.current_type_id,
            "owner": piece.owner,
            "square_index": index,
        })
    return rows


def _graph_diagnostics(compiled) -> list[dict[str, Any]]:
    n = compiled.board_size
    rows = []
    for opening in _opening_rows(compiled):
        adjacency = _adjacency(compiled, opening["type_id"], opening["owner"])
        components, component_ids = _scc(adjacency)
        reachable = _reachable(adjacency, opening["square_index"])
        files = [index % n for index in reachable]
        ranks = [_owner_relative_rank(index, opening["owner"], n) for index in reachable]
        rows.append({
            "source_id": opening["source_id"],
            "type_id": opening["type_id"],
            "owner": opening["owner"],
            "opening_square": _square_payload(opening["square_index"], n),
            "reachable_squares": [_square_payload(index, n) for index in reachable],
            "scc_component_id": component_ids[opening["square_index"]],
            "scc_component_size": len(components[component_ids[opening["square_index"]]]),
            "reachable_file_range": [min(files), max(files)] if files else None,
            "reachable_owner_relative_rank_range": [min(ranks), max(ranks)] if ranks else None,
            "reachable_file_owner_relative_rank_footprint": sorted({
                (index % n, _owner_relative_rank(index, opening["owner"], n))
                for index in reachable
            }),
        })
    return rows


def _source_rows_by_type(compiled) -> dict[str, list[dict[str, Any]]]:
    return {
        type_id: rows
        for type_id in sorted({row["type_id"] for row in _opening_rows(compiled, all_owners=False)})
        for rows in [[row for row in _opening_rows(compiled, all_owners=False) if row["type_id"] == type_id]]
    }


def _max_matching(sources: list[dict[str, Any]], targets: list[dict[str, Any]], reachability: dict[str, set[int]]) -> dict[str, Any]:
    target_to_source: dict[str, str] = {}

    def visit(source_id: str, seen: set[str]) -> bool:
        for target in targets:
            target_id = target["target_id"]
            if target_id in seen or target["square_index"] not in reachability[source_id]:
                continue
            seen.add(target_id)
            prior = target_to_source.get(target_id)
            if prior is None or visit(prior, seen):
                target_to_source[target_id] = source_id
                return True
        return False

    for source in sources:
        visit(source["source_id"], set())
    source_to_target = {source_id: target_id for target_id, source_id in target_to_source.items()}
    return {
        "target_to_source": target_to_source,
        "source_to_target": source_to_target,
        "maximum_matching_size": len(target_to_source),
    }


def _failure_reason(target_index: int, target_type: str, sources: list[dict[str, Any]], reachability: dict[str, set[int]], board_size: int, owner: int) -> str:
    target_file = target_index % board_size
    target_rank = _owner_relative_rank(target_index, owner, board_size)
    rank_possible = any(
        any(_owner_relative_rank(index, source["owner"], board_size) == target_rank for index in reachability[source["source_id"]])
        for source in sources
    )
    file_possible = any(
        any(index % board_size == target_file for index in reachability[source["source_id"]])
        for source in sources
    )
    if not rank_possible and not file_possible:
        return "rank_and_file_or_component_obstruction"
    if not rank_possible:
        return "rank_obstruction"
    return "file_or_component_obstruction"


def _template_analysis(compiled, template: dict[str, Any], opening_sources: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    n = compiled.board_size
    by_type: dict[str, dict[str, Any]] = {}
    total_targets = 0
    total_matching = 0
    failure_categories: list[str] = []
    targets_by_type: dict[str, list[dict[str, Any]]] = {}
    for item in template["ordinary"]:
        type_id = item["type_id"]
        square = item["square"]
        index = square[1] * n + square[0]
        targets_by_type.setdefault(type_id, []).append({
            "target_id": f"{type_id}#target{len(targets_by_type.get(type_id, [])) + 1}",
            "type_id": type_id,
            "square_index": index,
        })
    for type_id in sorted(targets_by_type):
        sources = opening_sources.get(type_id, [])
        reachability = {
            source["source_id"]: set(_reachable(_adjacency(compiled, type_id, source["owner"]), source["square_index"]))
            for source in sources
        }
        matching = _max_matching(sources, targets_by_type[type_id], reachability)
        target_rows = []
        for target in targets_by_type[type_id]:
            target_id = target["target_id"]
            reachable_sources = [
                source["source_id"] for source in sources
                if target["square_index"] in reachability[source["source_id"]]
            ]
            unreachable_sources = [source["source_id"] for source in sources if source["source_id"] not in reachable_sources]
            edges = []
            for source_id in reachable_sources:
                source = next(source for source in sources if source["source_id"] == source_id)
                edges.append({
                    "source_id": source_id,
                    "delta_file": target["square_index"] % n - source["square_index"] % n,
                    "delta_owner_relative_rank": _owner_relative_rank(target["square_index"], source["owner"], n) - _owner_relative_rank(source["square_index"], source["owner"], n),
                })
            matched_source = matching["target_to_source"].get(target_id)
            row = {
                "target_id": target_id,
                "target_square": _square_payload(target["square_index"], n),
                "reachable_source_ids": reachable_sources,
                "unreachable_source_ids": unreachable_sources,
                "source_target_displacements": edges,
                "matched_source_id": matched_source,
            }
            if matched_source is None:
                row["failure_reason"] = _failure_reason(target["square_index"], type_id, sources, reachability, n, sources[0]["owner"] if sources else 0)
                failure_categories.append(row["failure_reason"])
            target_rows.append(row)
        total_targets += len(targets_by_type[type_id])
        total_matching += matching["maximum_matching_size"]
        by_type[type_id] = {
            "opening_source_ids": [source["source_id"] for source in sources],
            "target_rows": target_rows,
            "maximum_matching_size": matching["maximum_matching_size"],
            "hall_deficiency": len(targets_by_type[type_id]) - matching["maximum_matching_size"],
            "complete_type_preserving_matching": matching["maximum_matching_size"] == len(targets_by_type[type_id]),
        }
    return {
        "template_id": template["template_id"],
        "defender_anchor": template["defender_anchor"],
        "ordinary": template["ordinary"],
        "by_type": by_type,
        "maximum_matching_size": total_matching,
        "hall_deficiency": total_targets - total_matching,
        "complete_type_preserving_matching": total_matching == total_targets,
        "failure_categories": sorted(set(failure_categories)),
    }


def _template_set_analysis(compiled, templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    opening_sources = _source_rows_by_type(compiled)
    return [_template_analysis(compiled, template, opening_sources) for template in templates]


def _missing_reverse_atoms(source, candidate) -> list[dict[str, Any]]:
    candidate_by_type = {piece.type_id: piece for piece in candidate.piece_types}
    missing = []
    for piece in source.piece_types:
        if piece.is_anchor:
            continue
        candidate_piece = candidate_by_type[piece.type_id]
        candidate_atoms = set(candidate_piece.movement_atoms)
        for source_atom in piece.movement_atoms:
            reverse = _reverse_atom(source_atom)
            if reverse not in candidate_atoms:
                missing.append({
                    "type_id": piece.type_id,
                    "source_atom": _atom_payload(source_atom),
                    "reverse_atom": _atom_payload(reverse),
                    "source_atom_key": _atom_key(source_atom),
                })
    return missing


def _counterfactual_ruleset(candidate, support: tuple[dict[str, Any], ...]):
    additions = {(row["type_id"], row["source_atom_key"]): row for row in support}
    piece_types = []
    for piece in candidate.piece_types:
        atoms = list(piece.movement_atoms)
        for (type_id, _source_key), row in additions.items():
            if type_id != piece.type_id:
                continue
            reverse = _reverse_atom(
                LeapAtom(tuple(row["source_atom"]["offset"]))
                if row["source_atom"]["kind"] == "LEAP"
                else RayAtom(tuple(row["source_atom"]["direction"]), row["source_atom"]["max_steps"])
            )
            if reverse not in atoms:
                atoms.append(reverse)
        piece_types.append(replace(piece, movement_atoms=tuple(atoms)))
    return replace(candidate, piece_types=tuple(piece_types))


def _opening_target_reachability(compiled, templates: list[dict[str, Any]]) -> dict[str, Any]:
    opening_sources = _source_rows_by_type(compiled)
    targets = [
        (item["type_id"], item["square"][1] * compiled.board_size + item["square"][0])
        for template in templates for item in template["ordinary"]
    ]
    by_type = {}
    for type_id in sorted(opening_sources):
        sources = opening_sources[type_id]
        reach = {
            source["source_id"]: set(_reachable(_adjacency(compiled, type_id, source["owner"]), source["square_index"]))
            for source in sources
        }
        required = {index for target_type, index in targets if target_type == type_id}
        by_type[type_id] = {
            "opening_reachable_square_union_count": len(set().union(*reach.values())) if reach else 0,
            "required_target_square_count": len(required),
            "required_target_squares_reachable": sum(any(index in values for values in reach.values()) for index in required),
        }
    return by_type


def _component_stats(compiled, type_ids: set[str]) -> dict[str, dict[str, int]]:
    stats = {}
    for type_id in sorted(type_ids):
        adjacency = _adjacency(compiled, type_id, 0)
        components, _component_ids = _scc(adjacency)
        nontrivial = [component for component in components if len(component) > 1]
        stats[type_id] = {
            "component_count": len(components),
            "nontrivial_component_count": len(nontrivial),
            "nontrivial_scc_vertex_count": sum(len(component) for component in nontrivial),
            "nontrivial_scc_pair_count": sum(len(component) * (len(component) - 1) // 2 for component in nontrivial),
        }
    return stats


def _counterfactual_summary(base, support, templates, base_analysis, full_analysis) -> dict[str, Any]:
    counterfactual = compile_ruleset(_counterfactual_ruleset(base, support))
    cf_graph = _opening_target_reachability(counterfactual, templates)
    base_graph = _opening_target_reachability(compile_ruleset(base), templates)
    cf_analysis = _template_set_analysis(counterfactual, templates)
    complete_base = {row["template_id"] for row in base_analysis if row["complete_type_preserving_matching"]}
    complete_cf = {row["template_id"] for row in cf_analysis if row["complete_type_preserving_matching"]}
    gains = {}
    for type_id, row in cf_graph.items():
        gains[type_id] = {
            "opening_reachable_square_gain": row["opening_reachable_square_union_count"] - base_graph[type_id]["opening_reachable_square_union_count"],
            "newly_reachable_required_mate_target_count": row["required_target_squares_reachable"] - base_graph[type_id]["required_target_squares_reachable"],
        }
    affected_types = {row["type_id"] for row in support}
    base_components = _component_stats(compile_ruleset(base), affected_types)
    counterfactual_components = _component_stats(counterfactual, affected_types)
    component_deltas = {
        type_id: {
            "base": base_components[type_id],
            "counterfactual": counterfactual_components[type_id],
            "delta_nontrivial_scc_vertex_count": counterfactual_components[type_id]["nontrivial_scc_vertex_count"] - base_components[type_id]["nontrivial_scc_vertex_count"],
            "delta_nontrivial_scc_pair_count": counterfactual_components[type_id]["nontrivial_scc_pair_count"] - base_components[type_id]["nontrivial_scc_pair_count"],
        }
        for type_id in sorted(affected_types)
    }
    return {
        "support": [
            {"type_id": row["type_id"], "source_atom": row["source_atom"], "reverse_atom": row["reverse_atom"]}
            for row in support
        ],
        "candidate_ruleset_fingerprint": counterfactual.ruleset_fingerprint,
        "opening_reachable_square_gain_by_type": gains,
        "newly_connected_scc_component": component_deltas,
        "newly_assignment_reachable_template_ids": sorted(complete_cf - complete_base),
        "newly_assignment_reachable_template_count": len(complete_cf - complete_base),
        "complete_type_preserving_matching_exists": bool(complete_cf),
        "full_closure_reference_template_ids": sorted(
            row["template_id"] for row in full_analysis if row["complete_type_preserving_matching"]
        ),
        "full_closure_reference_template_count": sum(row["complete_type_preserving_matching"] for row in full_analysis),
    }


def _transport_route(full_reference_template_count: int, minimum_support_count: int | None, missing_reverse_count: int) -> str:
    if full_reference_template_count == 0:
        return "REVERSE_CLOSURE_INSUFFICIENT_FOR_V4_3_KINEMATIC_MATE_TRANSPORT"
    if minimum_support_count is not None and minimum_support_count < missing_reverse_count:
        return "MINIMAL_TRANSPORT_SUPPORT_BELOW_FULL_CLOSURE_EXISTS"
    if minimum_support_count == missing_reverse_count:
        return "FULL_REVERSE_CLOSURE_REQUIRED_BY_CURRENT_V4_3_TEMPLATE_SET"
    return "CURRENT_TEMPLATE_TRANSPORT_DIAGNOSIS_INCONSISTENT"


def _load_context(root: Path):
    f86k_manifest = _load_json(root, F86K_MANIFEST)
    entry = next(row for row in f86k_manifest["entries"] if row["sample_id"] == SAMPLE_ID)
    source = ruleset_from_dict(entry["source_ruleset"])
    candidate = ruleset_from_dict(entry["candidate_ruleset"])
    if compile_ruleset(candidate).ruleset_fingerprint != entry["candidate_ruleset_fingerprint"]:
        raise RuntimeError("F86K candidate fingerprint drift")
    return entry, source, candidate


def run(root: Path, output: Path) -> dict[str, Any]:
    entry, source, candidate = _load_context(root)
    candidate_compiled = compile_ruleset(candidate)
    census_result = _candidate_static_census(SAMPLE_ID, candidate_compiled)
    census = census_result["census"]
    if census["candidate_position_count"] > MAX_CENSUS_CHECKS:
        raise RuntimeError("F86L V4-3 census exceeded the authorized check cap")
    if (census["candidate_position_count"], census["validated_position_count"], census["validated_template_count"]) != (156, 111, 12):
        raise RuntimeError("F86K V4-3 census was not reproduced exactly")
    templates = census["templates"]
    base_analysis = _template_set_analysis(candidate_compiled, templates)
    f86i_manifest = _load_json(root, F86I_MANIFEST)
    f86i_entry = next(row for row in f86i_manifest["entries"] if row["sample_id"] == SAMPLE_ID)
    full_compiled = compile_ruleset(ruleset_from_dict(f86i_entry["candidate_ruleset"]))
    full_analysis = _template_set_analysis(full_compiled, templates)
    missing = _missing_reverse_atoms(source, candidate)
    singletons = []
    for row in missing:
        singletons.append(_counterfactual_summary(candidate, (row,), templates, base_analysis, full_analysis))

    support_summaries = []
    for size in range(1, len(missing) + 1):
        for indexes in itertools.combinations(range(len(missing)), size):
            support = tuple(missing[index] for index in indexes)
            support_summaries.append(_counterfactual_summary(candidate, support, templates, base_analysis, full_analysis))
    successful = [row for row in support_summaries if row["complete_type_preserving_matching_exists"]]
    if successful:
        minimum_count = min(len(row["support"]) for row in successful)
        minimum_supports = [row for row in successful if len(row["support"]) == minimum_count]
    else:
        minimum_count = None
        minimum_supports = []

    full_reference_templates = sorted(row["template_id"] for row in full_analysis if row["complete_type_preserving_matching"])
    routing = _transport_route(len(full_reference_templates), minimum_count, len(missing))

    payload = {
        "schema_version": 1,
        "status": "F86L_STATIC_DIAGNOSTIC_ZERO_DYNAMIC_COMPUTE",
        "sample_id": SAMPLE_ID,
        "f86k_manifest": F86K_MANIFEST,
        "f86k_candidate_fingerprint": entry["candidate_ruleset_fingerprint"],
        "f86i_full_closure_fingerprint": f86i_entry["candidate_ruleset_fingerprint"],
        "authorized_census": {
            "candidate_checks": census["candidate_position_count"],
            "validated_positions": census["validated_position_count"],
            "validated_templates": census["validated_template_count"],
            "truncation": census["truncation"],
            "cap": MAX_CENSUS_CHECKS,
        },
        "opening_piece_graphs": _graph_diagnostics(candidate_compiled),
        "template_matching": base_analysis,
        "missing_reverse_atoms": missing,
        "single_missing_reverse_atom_counterfactuals": singletons,
        "full_closure_reference": {
            "complete_template_ids": full_reference_templates,
            "complete_template_count": len(full_reference_templates),
            "template_matching": full_analysis,
        },
        "minimum_atom_support": {
            "minimum_added_reverse_atom_count": minimum_count,
            "all_parallel_minimum_support_sets": minimum_supports,
            "equals_f86i_full_closure": bool(minimum_supports and minimum_count == len(missing)),
        },
        "all_support_set_counterfactuals": support_summaries,
        "routing": routing,
        "dynamic": {"real_games": 0, "tactical_nodes": 0, "bfs_expansions": 0, "teacher_search_training": 0, "f85_actual_compute": 0},
        "default_generator_changed": False,
    }
    _write_json(output, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("artifacts/f86l_mate_template_transport_support/diagnosis.json"))
    args = parser.parse_args()
    payload = run(args.root, args.output)
    print(json.dumps({"status": payload["status"], "routing": payload["routing"], "templates": payload["authorized_census"]["validated_templates"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
