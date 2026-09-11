"""F86N transport-aware signed movement sampler, static-only and bounded."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any

from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import has_legal_action
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict, ruleset_to_dict

try:
    from scripts.f86h_static_mate_template_kinematic_reachability import _analyze_cell
    from scripts.f86i_reversibility_rescue import (
        SAMPLES,
        _attack_masks,
        _build_position,
        _iter_placements,
        _ordinary_multiset,
        _orthogonal_anchor_atoms,
        _zone_mask,
        _static_mechanism,
    )
    from scripts.f86m_v4_3_movement_lattice_invariants import _component_info, _lattice_info
except ModuleNotFoundError:
    from f86h_static_mate_template_kinematic_reachability import _analyze_cell
    from f86i_reversibility_rescue import SAMPLES, _attack_masks, _build_position, _iter_placements, _ordinary_multiset, _orthogonal_anchor_atoms, _zone_mask, _static_mechanism
    from f86m_v4_3_movement_lattice_invariants import _component_info, _lattice_info


PROFILE = "TRANSPORT_AWARE_SIGNED_MOVEMENT_SAMPLER_PREFLIGHT"
SOURCE_ARTIFACT = "artifacts/f86c_generator_viability/rulesets.json"
STATIC_CAP_PER_CELL = 2048
STATIC_CAP_TOTAL = 4096
MAX_ATTEMPTS = 4096
LEAP_SLOT_COUNT = 2
LEAP_INCLUDE_PROBABILITY = 0.70
RAY_INCLUDE_PROBABILITY = 0.55
RAY_MAX_STEPS = (1, 2, None)

LEGACY_LEAPS = ((1, 0), (0, 1), (1, 1), (2, 1), (1, 2), (-1, 1))
LEGACY_RAYS = ((1, 0), (0, 1), (1, 1), (-1, 1))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _unique(items):
    return tuple(dict.fromkeys(items))


def _reverse_leap(offset):
    return (-offset[0], -offset[1])


def _reverse_ray(direction):
    return (-direction[0], -direction[1])


SIGNED_LEAP_POOL = _unique(LEGACY_LEAPS + tuple(_reverse_leap(offset) for offset in LEGACY_LEAPS))
SIGNED_RAY_POOL = _unique(LEGACY_RAYS + tuple(_reverse_ray(direction) for direction in LEGACY_RAYS))


def _sample_atoms(rng: random.Random) -> tuple[LeapAtom | RayAtom, ...]:
    atoms = []
    for _ in range(LEAP_SLOT_COUNT):
        if rng.random() < LEAP_INCLUDE_PROBABILITY:
            atoms.append(LeapAtom(rng.choice(SIGNED_LEAP_POOL)))
    if rng.random() < RAY_INCLUDE_PROBABILITY:
        atoms.append(RayAtom(rng.choice(SIGNED_RAY_POOL), rng.choice(RAY_MAX_STEPS)))
    if not atoms:
        atoms.append(LeapAtom(rng.choice(SIGNED_LEAP_POOL)))
    return _unique(atoms)


def _candidate_ruleset(source, movement_seed: int, attempt: int):
    rng = random.Random(movement_seed + attempt)
    piece_types = []
    for piece_type in source.piece_types:
        if piece_type.is_anchor:
            atoms = _orthogonal_anchor_atoms()
        else:
            atoms = _sample_atoms(rng)
        piece_types.append(replace(piece_type, movement_atoms=tuple(atoms)))
    candidate = replace(
        source,
        piece_types=tuple(piece_types),
        metadata={
            **source.metadata,
            "candidate_profile": PROFILE,
            "source_generator": "f86c-minimal",
            "experimental_candidate": True,
            "movement_sampling_seed": movement_seed,
            "movement_sampling_attempt": attempt,
        },
    )
    return candidate


def _source_rows(root: Path) -> dict[str, dict[str, Any]]:
    payload = _load_json(root, SOURCE_ARTIFACT)
    rows = {row["sample_id"]: row for row in payload["sample"]}
    if set(rows) != {sample_id for sample_id, _, _ in SAMPLES}:
        raise RuntimeError("F86C source artifact does not contain all eight frozen samples")
    return rows


def _movement_seed(source_seed: int) -> int:
    return source_seed * 10 + 9


def _owner_relative_rank(index: int, owner: int, n: int) -> int:
    rank = index // n
    return rank if owner == 0 else n - 1 - rank


def _opening_sources(compiled) -> dict[str, list[dict[str, Any]]]:
    anchor = next(piece.type_id for piece in compiled.piece_types if piece.is_anchor)
    ordinals: dict[str, int] = defaultdict(int)
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, piece in enumerate(compiled.initial_position.board):
        if piece is None or piece.owner != 0 or piece.current_type_id == anchor:
            continue
        ordinals[piece.current_type_id] += 1
        rows[piece.current_type_id].append({
            "source_id": f"{piece.current_type_id}@o0#{ordinals[piece.current_type_id]}",
            "type_id": piece.current_type_id,
            "owner": 0,
            "square_index": index,
        })
    return dict(rows)


def _graph_profile(compiled, type_id: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    n = compiled.board_size
    adjacency = {
        source: {
            target.rank * n + target.file
            for target in compiled.empty_mobility[type_id][0][source]
        }
        for source in range(n * n)
    }
    edges = sum(len(targets) for targets in adjacency.values())
    reverse_edges = sum(int(source in adjacency[target]) for source, targets in adjacency.items() for target in targets)
    sinks = sum(not targets for targets in adjacency.values())
    # The compact SCC calculation is sufficient for the static profile.
    index = 0
    stack: list[int] = []
    on_stack: set[int] = set()
    indices: dict[int, int] = {}
    low: dict[int, int] = {}
    components: list[list[int]] = []

    def visit(node: int):
        nonlocal index
        indices[node] = index
        low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(adjacency[node]):
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
            components.append(component)

    for node in range(n * n):
        if node not in indices:
            visit(node)
    component_ids = {node: component_id for component_id, component in enumerate(components) for node in component}
    source_rows = []
    for source in sources:
        start = source["square_index"]
        reached = {start}
        queue = [start]
        while queue:
            current = queue.pop(0)
            for target in adjacency[current]:
                if target not in reached:
                    reached.add(target)
                    queue.append(target)
        source_rank = _owner_relative_rank(start, 0, n)
        ranks = [_owner_relative_rank(target, 0, n) for target in reached]
        source_rows.append({
            "source_id": source["source_id"],
            "opening_square": [start % n, start // n],
            "reachable_board_fraction": len(reached) / (n * n),
            "can_reach_higher_owner_relative_rank": any(rank > source_rank for rank in ranks),
            "can_reach_lower_owner_relative_rank": any(rank < source_rank for rank in ranks),
            "scc_component_id": component_ids[start],
            "scc_component_size": len(components[component_ids[start]]),
        })
    return {
        "type_id": type_id,
        "used_in_opening": bool(sources),
        "movement_lattice": _lattice_info(compiled, type_id),
        "directed_sink_fraction": sinks / (n * n),
        "direct_reverse_edge_fraction": reverse_edges / edges if edges else 0.0,
        "nontrivial_scc_fraction": sum(len(component) for component in components if len(component) > 1) / (n * n),
        "opening_sources": source_rows,
    }


def _backbone_predicate(compiled) -> dict[str, Any]:
    sources = _opening_sources(compiled)
    profile_rows = [_graph_profile(compiled, type_id, sources.get(type_id, [])) for type_id in sorted(sources)]
    candidates = []
    for row in profile_rows:
        lattice = row["movement_lattice"]
        opening_ok = any(source["scc_component_size"] > 1 and source["can_reach_higher_owner_relative_rank"] and source["can_reach_lower_owner_relative_rank"] for source in row["opening_sources"])
        eligible = lattice["integer_lattice_rank"] == 2 and lattice["lattice_index"] == 1 and opening_ok
        candidates.append({"type_id": row["type_id"], "eligible": eligible, "opening_source_count": len(row["opening_sources"])})
    backbone = next((row["type_id"] for row in candidates if row["eligible"]), None)
    return {
        "profile": profile_rows,
        "eligible_types": candidates,
        "backbone_type": backbone,
        "passes": backbone is not None,
    }


def _material_profile(compiled, predicate: dict[str, Any]) -> dict[str, Any]:
    sources = _opening_sources(compiled)
    n = compiled.board_size
    union = set()
    for row in predicate["profile"]:
        for source in row["opening_sources"]:
            # Recompute only this small union for durable material coverage.
            for target in compiled.empty_mobility[row["type_id"]][0][source["opening_square"][1] * n + source["opening_square"][0]]:
                union.add(target.rank * n + target.file)
    total_pieces = sum(len(rows) for rows in sources.values())
    rank1 = sum(len(row["opening_sources"]) for row in predicate["profile"] if row["movement_lattice"]["integer_lattice_rank"] == 1)
    high_index = sum(len(row["opening_sources"]) for row in predicate["profile"] if row["movement_lattice"]["integer_lattice_rank"] == 2 and row["movement_lattice"]["lattice_index"] != 1)
    index1 = sum(len(row["opening_sources"]) for row in predicate["profile"] if row["movement_lattice"]["integer_lattice_rank"] == 2 and row["movement_lattice"]["lattice_index"] == 1)
    source_union = {
        row["type_id"]: len({
            target.rank * n + target.file
            for source in sources.get(row["type_id"], [])
            for target in compiled.empty_mobility[row["type_id"]][0][source["square_index"]]
        })
        for row in predicate["profile"]
    }
    return {
        "backbone_type": predicate["backbone_type"],
        "opening_source_union_board_coverage": len(union) / (n * n) if union else 0.0,
        "same_type_source_union_square_counts": source_union,
        "component_diversity_by_type": {
            row["type_id"]: len({source["scc_component_id"] for source in row["opening_sources"]})
            for row in predicate["profile"]
        },
        "opening_material_piece_count": total_pieces,
        "opening_material_rank1_piece_count": rank1,
        "opening_material_rank1_piece_fraction": rank1 / total_pieces if total_pieces else 0.0,
        "opening_material_index_gt1_rank2_piece_count": high_index,
        "opening_material_index_gt1_rank2_piece_fraction": high_index / total_pieces if total_pieces else 0.0,
        "opening_material_index1_rank2_piece_count": index1,
        "opening_material_index1_rank2_piece_fraction": index1 / total_pieces if total_pieces else 0.0,
    }


def _bounded_census(sample_id: str, compiled, cap: int) -> dict[str, Any]:
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
                if is_in_check(position, 0, compiled) or not is_in_check(position, 1, compiled) or has_legal_action(position, compiled):
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
            "template_id": f"T{ordinal:04d}",
            "sample_id": sample_id,
            "defender_anchor": [defender_anchor % n, defender_anchor // n],
            "ordinary": [{"type_id": type_id, "square": [square % n, square // n]} for type_id, square in placement],
            "allowed_attacker_anchor_squares": [[square % n, square // n] for square in sorted(targets)],
        })
    census = {
        "sample_id": sample_id,
        "cell": "CANDIDATE",
        "candidate_position_count": candidate_count,
        "validated_position_count": validated_count,
        "validated_template_count": len(rows),
        "truncation": truncated,
        "templates": rows,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
    }
    kinematic = _analyze_cell(sample_id, "CANDIDATE", compiled, census, rows)
    return {"census": census, "kinematic": kinematic}


def build_manifest(root: Path, output: Path) -> dict[str, Any]:
    source_rows = _source_rows(root)
    entries = []
    for sample_id, board_size, source_seed in SAMPLES:
        row = source_rows[sample_id]
        source = ruleset_from_dict(row["ruleset"])
        source_compiled = compile_ruleset(source)
        if source_compiled.ruleset_fingerprint != row["ruleset_fingerprint"]:
            raise RuntimeError(f"source fingerprint mismatch for {sample_id}")
        entries.append({
            "sample_id": sample_id,
            "board_size": board_size,
            "ordinary_count": row["ordinary_count"],
            "source_seed": source_seed,
            "movement_rng_seed": _movement_seed(source_seed),
            "source_ruleset_fingerprint": source_compiled.ruleset_fingerprint,
            "source_ruleset": row["ruleset"],
        })
    payload = {
        "schema_version": 1,
        "status": "PRE_REGISTERED_STATIC_EXPERIMENTAL_CANDIDATE",
        "candidate_profile": PROFILE,
        "source_artifact": SOURCE_ARTIFACT,
        "source_sample_ids": [sample_id for sample_id, _, _ in SAMPLES],
        "entries": entries,
        "signed_movement_pool": {
            "legacy_leaps": [list(offset) for offset in LEGACY_LEAPS],
            "signed_leaps": [list(offset) for offset in SIGNED_LEAP_POOL],
            "legacy_rays": [list(direction) for direction in LEGACY_RAYS],
            "signed_rays": [list(direction) for direction in SIGNED_RAY_POOL],
            "ray_max_steps": list(RAY_MAX_STEPS),
            "reverse_ray_preserves_max_steps": True,
        },
        "sampler": {
            "leap_slot_count": LEAP_SLOT_COUNT,
            "leap_include_probability": LEAP_INCLUDE_PROBABILITY,
            "ray_include_probability": RAY_INCLUDE_PROBABILITY,
            "fallback": "one_signed_leap",
            "dedupe": True,
            "ordering": "sample_order_after_source_type_order",
            "retry_algorithm": "seed_plus_attempt_random_mt19937",
            "max_attempts": MAX_ATTEMPTS,
            "result_driven_replacement_forbidden": True,
        },
        "backbone_predicate": {
            "requires_opening_type": True,
            "requires_integer_lattice_rank": 2,
            "requires_lattice_index": 1,
            "requires_source_higher_and_lower_rank_reachability": True,
            "requires_source_nontrivial_scc": True,
            "piece_type_index1_not_required_globally": True,
        },
        "static_budget": {
            "targeted_cells": ["V4-3", "V5-3"],
            "candidate_checks_per_cell": STATIC_CAP_PER_CELL,
            "candidate_checks_total_cap": STATIC_CAP_TOTAL,
        },
        "dynamic_budget": {"real_games": 0, "tactical_nodes": 0, "bfs_expansions": 0, "teacher_search_training": 0, "f85_actual_compute": 0},
        "default_generator_changed": False,
    }
    _write_json(output, payload)
    return payload


def _load_manifest(root: Path) -> dict[str, Any]:
    payload = _load_json(root, "artifacts/f86n_transport_aware_signed_sampler/manifest.json")
    if payload["candidate_profile"] != PROFILE or payload["status"] != "PRE_REGISTERED_STATIC_EXPERIMENTAL_CANDIDATE":
        raise RuntimeError("F86N manifest profile mismatch")
    return payload


def _generate_entry(entry: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    source = ruleset_from_dict(entry["source_ruleset"])
    accepted = None
    accepted_attempt = None
    last_candidate = None
    for attempt in range(MAX_ATTEMPTS):
        candidate = _candidate_ruleset(source, entry["movement_rng_seed"], attempt)
        try:
            compiled = compile_ruleset(candidate)
        except Exception:
            continue
        last_candidate = compiled
        predicate = _backbone_predicate(compiled)
        if predicate["passes"]:
            accepted = (candidate, compiled, predicate)
            accepted_attempt = attempt
            break
    if accepted is None:
        return {
            "sample_id": entry["sample_id"],
            "board_size": entry["board_size"],
            "source_seed": entry["source_seed"],
            "movement_rng_seed": entry["movement_rng_seed"],
            "accepted_attempt": None,
            "attempts_used": MAX_ATTEMPTS,
            "source_ruleset_fingerprint": entry["source_ruleset_fingerprint"],
            "candidate_ruleset_fingerprint": None,
            "candidate_ruleset": None,
            "sampling_status": "STRUCTURAL_PREDICATE_UNAVAILABLE",
            "backbone_type": None,
            "failure_reason": "NO_ATTEMPT_SATISFIED_MATERIAL_LEVEL_TRANSPORT_BACKBONE_PREDICATE",
            "backbone_predicate": None,
            "material_profile": None,
        }, None
    candidate, compiled, predicate = accepted
    return {
        "sample_id": entry["sample_id"],
        "board_size": entry["board_size"],
        "source_seed": entry["source_seed"],
        "movement_rng_seed": entry["movement_rng_seed"],
        "accepted_attempt": accepted_attempt,
        "attempts_used": accepted_attempt + 1,
        "sampling_status": "ACCEPTED_STRUCTURAL_BACKBONE",
        "source_ruleset_fingerprint": entry["source_ruleset_fingerprint"],
        "candidate_ruleset_fingerprint": compiled.ruleset_fingerprint,
        "candidate_ruleset": ruleset_to_dict(candidate),
        "backbone_predicate": predicate,
        "backbone_type": predicate["backbone_type"],
        "material_profile": _material_profile(compiled, predicate),
    }, compiled


def run(root: Path, output: Path) -> dict[str, Any]:
    manifest = _load_manifest(root)
    static = []
    candidates = []
    compiled_by_sample = {}
    for entry in manifest["entries"]:
        result, compiled = _generate_entry(entry)
        candidates.append(result)
        if compiled is None:
            static.append({
                "sample_id": result["sample_id"],
                "sampling_status": result["sampling_status"],
                "attempts_used": result["attempts_used"],
                "candidate_ruleset_fingerprint": None,
                "backbone_type": None,
                "material_profile": None,
            })
            continue
        compiled_by_sample[result["sample_id"]] = compiled
        mechanism = _static_mechanism(compiled)
        static.append({
            "sample_id": result["sample_id"],
            "candidate_ruleset_fingerprint": result["candidate_ruleset_fingerprint"],
            "accepted_attempt": result["accepted_attempt"],
            "backbone_type": result["backbone_predicate"]["backbone_type"],
            "material_profile": result["material_profile"],
            "mechanism": {
                "ordinary_sink_fraction": mechanism["ordinary_sink_fraction"],
                "ordinary_direct_reverse_edge_fraction": mechanism["ordinary_direct_reverse_edge_fraction"],
                "ordinary_nontrivial_scc_vertex_fraction": mechanism["ordinary_nontrivial_scc_vertex_fraction"],
                "ordinary_all_monotone_dag": mechanism["ordinary_all_monotone_dag"],
            },
        })

    targeted = []
    for sample_id in ("V4-3", "V5-3"):
        compiled = compiled_by_sample[sample_id]
        result = _bounded_census(sample_id, compiled, STATIC_CAP_PER_CELL)
        census = result["census"]
        kinematic = result["kinematic"]
        targeted.append({
            "sample_id": sample_id,
            "candidate_ruleset_fingerprint": compiled.ruleset_fingerprint,
            "candidate_position_count": census["candidate_position_count"],
            "validated_position_count": census["validated_position_count"],
            "validated_template_count": census["validated_template_count"],
            "truncation": census["truncation"],
            "ordinary_assignment_reachable_count": kinematic["ordinary_assignment_reachable_count"],
            "joint_kinematically_reachable_count": kinematic["joint_kinematically_reachable_count"],
            "minimum_optimistic_ply_lower_bound": kinematic["minimum_optimistic_ply_lower_bound"],
        })
    total_checks = sum(row["candidate_position_count"] for row in targeted)
    if total_checks > STATIC_CAP_TOTAL:
        raise RuntimeError("F86N total static cap exceeded")
    routes = []
    for row in targeted:
        if row["joint_kinematically_reachable_count"] > 0:
            route = "TRANSPORT_AWARE_SIGNED_SAMPLER_STATIC_WITNESS_EXISTS"
        elif row["truncation"]:
            route = "MATE_CAPACITY_UNRESOLVED_DUE_TO_CENSUS_CAP"
        else:
            route = "TRANSPORT_AWARE_SIGNED_SAMPLER_INSUFFICIENT_KINEMATICALLY"
        routes.append({"sample_id": row["sample_id"], "routing": route})
    payload = {
        "schema_version": 1,
        "status": "F86N_STATIC_PREFLIGHT_ZERO_DYNAMIC_COMPUTE",
        "candidate_profile": PROFILE,
        "manifest": "artifacts/f86n_transport_aware_signed_sampler/manifest.json",
        "candidates": candidates,
        "sampling_summary": {
            "accepted_count": sum(row["sampling_status"] == "ACCEPTED_STRUCTURAL_BACKBONE" for row in candidates),
            "structural_predicate_unavailable_count": sum(row["sampling_status"] == "STRUCTURAL_PREDICATE_UNAVAILABLE" for row in candidates),
            "max_attempts": MAX_ATTEMPTS,
        },
        "static": static,
        "targeted_static_mate_capacity": targeted,
        "routing": {"static": routes, "dynamic": "NOT_RUN_BY_STATIC_PREFLIGHT"},
        "static_candidate_checks": {
            "V4-3": next(row["candidate_position_count"] for row in targeted if row["sample_id"] == "V4-3"),
            "V5-3": next(row["candidate_position_count"] for row in targeted if row["sample_id"] == "V5-3"),
            "total": total_checks,
            "per_cell_cap": STATIC_CAP_PER_CELL,
            "total_cap": STATIC_CAP_TOTAL,
        },
        "dynamic": {"real_games": 0, "tactical_nodes": 0, "bfs_expansions": 0, "teacher_search_training": 0, "f85_actual_compute": 0},
        "default_generator_changed": False,
    }
    _write_json(output, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--prep", action="store_true")
    parser.add_argument("--manifest-output", type=Path, default=Path("artifacts/f86n_transport_aware_signed_sampler/manifest.json"))
    parser.add_argument("--result-output", type=Path, default=Path("artifacts/f86n_transport_aware_signed_sampler/results.json"))
    args = parser.parse_args()
    if args.prep:
        payload = build_manifest(args.root, args.manifest_output)
        print(json.dumps({"status": payload["status"], "sample_count": len(payload["entries"])}, sort_keys=True))
    else:
        payload = run(args.root, args.result_output)
        print(json.dumps({"status": payload["status"], "static_checks": payload["static_candidate_checks"]["total"], "dynamic_games": payload["dynamic"]["real_games"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
