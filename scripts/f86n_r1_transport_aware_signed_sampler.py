"""F86N-R1 fresh PREP-boundary-safe transport-aware sampler."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any

from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict, ruleset_to_dict
from generic_chess.core.movement import LeapAtom, RayAtom

try:
    from scripts.f86n_transport_aware_signed_sampler import (
        MAX_ATTEMPTS,
        PROFILE as LEGACY_PROFILE,
        SIGNED_LEAP_POOL,
        SIGNED_RAY_POOL,
        RAY_MAX_STEPS,
        LEAP_SLOT_COUNT,
        LEAP_INCLUDE_PROBABILITY,
        RAY_INCLUDE_PROBABILITY,
        _sample_atoms,
        _source_rows,
        _orthogonal_anchor_atoms,
        _bounded_census,
        _static_mechanism,
    )
    from scripts.f86m_v4_3_movement_lattice_invariants import _lattice_info
except ModuleNotFoundError:
    from f86n_transport_aware_signed_sampler import MAX_ATTEMPTS, PROFILE as LEGACY_PROFILE, SIGNED_LEAP_POOL, SIGNED_RAY_POOL, RAY_MAX_STEPS, LEAP_SLOT_COUNT, LEAP_INCLUDE_PROBABILITY, RAY_INCLUDE_PROBABILITY, _sample_atoms, _source_rows, _orthogonal_anchor_atoms, _bounded_census, _static_mechanism
    from f86m_v4_3_movement_lattice_invariants import _lattice_info


PROFILE = "TRANSPORT_AWARE_SIGNED_MOVEMENT_SAMPLER_PREFLIGHT_R1"
SOURCE_ARTIFACT = "artifacts/f86c_generator_viability/rulesets.json"
STATIC_CAP_PER_CELL = 2048
STATIC_CAP_TOTAL = 4096


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _movement_seed(sample_id: str, source_fingerprint: str) -> int:
    token = f"F86N-R1|{sample_id}|{source_fingerprint}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(token).digest()[:8], "big")


def _candidate_ruleset(source, movement_seed: int, attempt: int):
    import random

    rng = random.Random(movement_seed + attempt)
    piece_types = []
    for piece_type in source.piece_types:
        atoms = _orthogonal_anchor_atoms() if piece_type.is_anchor else _sample_atoms(rng)
        piece_types.append(replace(piece_type, movement_atoms=tuple(atoms)))
    return replace(
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
            "square_index": index,
        })
    return dict(rows)


def _graph(compiled, type_id: str):
    n = compiled.board_size
    return tuple(tuple(sorted(target.rank * n + target.file for target in compiled.empty_mobility[type_id][0][source])) for source in range(n * n))


def _scc(adjacency):
    index = 0
    stack = []
    on_stack = set()
    indices = {}
    low = {}
    components = []

    def visit(node):
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
    return components, ids


def _reachable(adjacency, source):
    reached = {source}
    queue = [source]
    while queue:
        current = queue.pop(0)
        for target in adjacency[current]:
            if target not in reached:
                reached.add(target)
                queue.append(target)
    return reached


def _type_profile(compiled, type_id: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    n = compiled.board_size
    adjacency = _graph(compiled, type_id)
    components, component_ids = _scc(adjacency)
    edges = sum(len(targets) for targets in adjacency)
    reverse_edges = sum(int(source in adjacency[target]) for source, targets in enumerate(adjacency) for target in targets)
    sinks = sum(not targets for targets in adjacency)
    source_rows = []
    for source in sources:
        reached = _reachable(adjacency, source["square_index"])
        component = components[component_ids[source["square_index"]]]
        files = [index % n for index in component]
        ranks = [index // n for index in component]
        source_rows.append({
            "source_id": source["source_id"],
            "opening_square": [source["square_index"] % n, source["square_index"] // n],
            "reachable_set_size": len(reached),
            "reachable_board_fraction": len(reached) / (n * n),
            "scc_component_id": component_ids[source["square_index"]],
            "scc_component_size": len(component),
            "scc_file_span": [min(files), max(files)],
            "scc_owner_relative_rank_span": [min(ranks), max(ranks)],
        })
    union = set().union(*(_reachable(adjacency, source["square_index"]) for source in sources)) if sources else set()
    return {
        "type_id": type_id,
        "used_in_opening": bool(sources),
        "movement_lattice": _lattice_info(compiled, type_id),
        "directed_sink_fraction": sinks / (n * n),
        "direct_reverse_edge_fraction": reverse_edges / edges if edges else 0.0,
        "nontrivial_scc_fraction": sum(len(component) for component in components if len(component) > 1) / (n * n),
        "transitive_source_union_square_count": len(union),
        "transitive_source_union_board_fraction": len(union) / (n * n) if union else 0.0,
        "source_component_diversity": len({row["scc_component_id"] for row in source_rows}),
        "source_pairwise_reachable_overlap": [
            len(_reachable(adjacency, left["square_index"]).intersection(_reachable(adjacency, right["square_index"])))
            for index, left in enumerate(sources) for right in sources[index + 1:]
        ],
        "opening_sources": source_rows,
    }


def _backbone_predicate(compiled) -> dict[str, Any]:
    sources = _opening_sources(compiled)
    profiles = []
    eligible = []
    for type_id in sorted(sources):
        row = _type_profile(compiled, type_id, sources[type_id])
        profiles.append(row)
        lattice = row["movement_lattice"]
        witnesses = [
            source for source in row["opening_sources"]
            if source["scc_component_size"] > 1
            and source["scc_file_span"][1] > source["scc_file_span"][0]
            and source["scc_owner_relative_rank_span"][1] > source["scc_owner_relative_rank_span"][0]
        ]
        eligible.append({"type_id": type_id, "eligible": lattice["integer_lattice_rank"] == 2 and lattice["lattice_index"] == 1 and bool(witnesses), "witnesses": witnesses})
    backbone = next((row for row in eligible if row["eligible"]), None)
    return {
        "profile": profiles,
        "eligible_types": eligible,
        "backbone_type": backbone["type_id"] if backbone else None,
        "backbone_witness": backbone["witnesses"][0] if backbone else None,
        "passes": backbone is not None,
    }


def _material_profile(compiled, predicate: dict[str, Any]) -> dict[str, Any]:
    total = sum(len(row["opening_sources"]) for row in predicate["profile"])
    rank1 = sum(len(row["opening_sources"]) for row in predicate["profile"] if row["movement_lattice"]["integer_lattice_rank"] == 1)
    high = sum(len(row["opening_sources"]) for row in predicate["profile"] if row["movement_lattice"]["integer_lattice_rank"] == 2 and row["movement_lattice"]["lattice_index"] != 1)
    index1 = sum(len(row["opening_sources"]) for row in predicate["profile"] if row["movement_lattice"]["integer_lattice_rank"] == 2 and row["movement_lattice"]["lattice_index"] == 1)
    union = set()
    sources = _opening_sources(compiled)
    n = compiled.board_size
    same_type = {}
    for row in predicate["profile"]:
        adjacency = _graph(compiled, row["type_id"])
        type_union = set()
        for source in sources.get(row["type_id"], []):
            type_union.update(_reachable(adjacency, source["square_index"]))
        union.update(type_union)
        same_type[row["type_id"]] = len(type_union)
    return {
        "backbone_type": predicate["backbone_type"],
        "backbone_witness": predicate["backbone_witness"],
        "aggregate_transitive_source_union_square_count": len(union),
        "aggregate_transitive_source_union_board_fraction": len(union) / (n * n) if union else 0.0,
        "opening_material_piece_count": total,
        "opening_material_rank1_piece_count": rank1,
        "opening_material_rank1_piece_fraction": rank1 / total if total else 0.0,
        "opening_material_index_gt1_rank2_piece_count": high,
        "opening_material_index_gt1_rank2_piece_fraction": high / total if total else 0.0,
        "opening_material_index1_rank2_piece_count": index1,
        "opening_material_index1_rank2_piece_fraction": index1 / total if total else 0.0,
        "same_type_transitive_union_square_counts": same_type,
        "component_diversity_by_type": {row["type_id"]: row["source_component_diversity"] for row in predicate["profile"]},
    }


def _select_candidate(source, sample_id: str, source_fingerprint: str):
    seed = _movement_seed(sample_id, source_fingerprint)
    for attempt in range(MAX_ATTEMPTS):
        candidate = _candidate_ruleset(source, seed, attempt)
        try:
            compiled = compile_ruleset(candidate)
        except Exception:
            continue
        predicate = _backbone_predicate(compiled)
        if predicate["passes"]:
            return {
                "sample_id": sample_id,
                "movement_rng_seed": seed,
                "accepted_attempt": attempt,
                "attempts_used": attempt + 1,
                "source_ruleset_fingerprint": source_fingerprint,
                "candidate_ruleset_fingerprint": compiled.ruleset_fingerprint,
                "candidate_ruleset": ruleset_to_dict(candidate),
                "sampling_status": "ACCEPTED_STRUCTURAL_BACKBONE",
                "backbone_predicate": predicate,
                "material_profile": _material_profile(compiled, predicate),
            }
    return {
        "sample_id": sample_id,
        "movement_rng_seed": seed,
        "accepted_attempt": None,
        "attempts_used": MAX_ATTEMPTS,
        "source_ruleset_fingerprint": source_fingerprint,
        "candidate_ruleset_fingerprint": None,
        "candidate_ruleset": None,
        "sampling_status": "TRANSPORT_BACKBONE_SAMPLER_INFEASIBLE_ON_FROZEN_COHORT",
    }


def build_manifest(root: Path, output: Path) -> dict[str, Any]:
    rows = _source_rows(root)
    entries = []
    for sample_id, board_size, source_seed in __import__("scripts.f86i_reversibility_rescue", fromlist=["SAMPLES"]).SAMPLES:
        source = ruleset_from_dict(rows[sample_id]["ruleset"])
        source_fp = compile_ruleset(source).ruleset_fingerprint
        entry = _select_candidate(source, sample_id, source_fp)
        if entry["sampling_status"] != "ACCEPTED_STRUCTURAL_BACKBONE":
            raise RuntimeError(f"TRANSPORT_BACKBONE_SAMPLER_INFEASIBLE_ON_FROZEN_COHORT:{sample_id}")
        entry.update({"board_size": board_size, "ordinary_count": rows[sample_id]["ordinary_count"], "source_seed": source_seed, "source_ruleset": rows[sample_id]["ruleset"]})
        entries.append(entry)
    payload = {
        "schema_version": 1,
        "status": "PRE_REGISTERED_STATIC_FROZEN_CANDIDATES",
        "candidate_profile": PROFILE,
        "source_artifact": SOURCE_ARTIFACT,
        "source_sample_ids": [entry["sample_id"] for entry in entries],
        "entries": entries,
        "signed_movement_pool": {"signed_leaps": [list(vector) for vector in SIGNED_LEAP_POOL], "signed_rays": [list(vector) for vector in SIGNED_RAY_POOL], "ray_max_steps": list(RAY_MAX_STEPS), "reverse_ray_preserves_max_steps": True},
        "sampler": {"leap_slot_count": LEAP_SLOT_COUNT, "leap_include_probability": LEAP_INCLUDE_PROBABILITY, "ray_include_probability": RAY_INCLUDE_PROBABILITY, "dedupe": True, "fallback": "one_signed_leap", "max_attempts": MAX_ATTEMPTS, "seed_algorithm": "first_64_bits_big_endian_sha256_F86N-R1_sample_id_source_fingerprint", "result_driven_replacement_forbidden": True},
        "backbone_predicate": {"requires_opening_type": True, "requires_integer_lattice_rank": 2, "requires_lattice_index": 1, "requires_source_nontrivial_scc": True, "requires_scc_two_file_span": True, "requires_scc_two_owner_relative_rank_span": True, "piece_type_index1_not_required_globally": True},
        "static_budget": {"targeted_cells": ["V4-3", "V5-3"], "candidate_checks_per_cell": STATIC_CAP_PER_CELL, "candidate_checks_total_cap": STATIC_CAP_TOTAL},
        "dynamic_budget": {"real_games": 0, "tactical_nodes": 0, "bfs_expansions": 0, "teacher_search_training": 0, "f85_actual_compute": 0},
        "default_generator_changed": False,
    }
    _write_json(output, payload)
    return payload


def _load_manifest(root: Path) -> dict[str, Any]:
    payload = _load_json(root, "artifacts/f86n_r1_transport_aware_signed_sampler/manifest.json")
    if payload["status"] != "PRE_REGISTERED_STATIC_FROZEN_CANDIDATES" or payload["candidate_profile"] != PROFILE:
        raise RuntimeError("F86N-R1 frozen PREP manifest mismatch")
    if len(payload["entries"]) != 8 or any(entry["candidate_ruleset"] is None for entry in payload["entries"]):
        raise RuntimeError("F86N-R1 PREP does not freeze all eight candidates")
    return payload


def run(root: Path, output: Path) -> dict[str, Any]:
    manifest = _load_manifest(root)
    static = []
    compiled_by_sample = {}
    for entry in manifest["entries"]:
        compiled = compile_ruleset(ruleset_from_dict(entry["candidate_ruleset"]))
        if compiled.ruleset_fingerprint != entry["candidate_ruleset_fingerprint"]:
            raise RuntimeError(f"F86N-R1 candidate fingerprint drift:{entry['sample_id']}")
        compiled_by_sample[entry["sample_id"]] = compiled
        mechanism = _static_mechanism(compiled)
        static.append({"sample_id": entry["sample_id"], "candidate_ruleset_fingerprint": entry["candidate_ruleset_fingerprint"], "accepted_attempt": entry["accepted_attempt"], "backbone_type": entry["backbone_predicate"]["backbone_type"], "backbone_witness": entry["backbone_predicate"]["backbone_witness"], "material_profile": entry["material_profile"], "mechanism": {"ordinary_sink_fraction": mechanism["ordinary_sink_fraction"], "ordinary_direct_reverse_edge_fraction": mechanism["ordinary_direct_reverse_edge_fraction"], "ordinary_nontrivial_scc_vertex_fraction": mechanism["ordinary_nontrivial_scc_vertex_fraction"], "ordinary_all_monotone_dag": mechanism["ordinary_all_monotone_dag"]}})
    targeted = []
    for sample_id in ("V4-3", "V5-3"):
        result = _bounded_census(sample_id, compiled_by_sample[sample_id], STATIC_CAP_PER_CELL)
        census = result["census"]
        kinematic = result["kinematic"]
        targeted.append({"sample_id": sample_id, "candidate_ruleset_fingerprint": compiled_by_sample[sample_id].ruleset_fingerprint, "candidate_position_count": census["candidate_position_count"], "validated_position_count": census["validated_position_count"], "validated_template_count": census["validated_template_count"], "truncation": census["truncation"], "ordinary_assignment_reachable_count": kinematic["ordinary_assignment_reachable_count"], "joint_kinematically_reachable_count": kinematic["joint_kinematically_reachable_count"], "minimum_optimistic_ply_lower_bound": kinematic["minimum_optimistic_ply_lower_bound"]})
    total = sum(row["candidate_position_count"] for row in targeted)
    if total > STATIC_CAP_TOTAL:
        raise RuntimeError("F86N-R1 static total cap exceeded")
    routes = []
    for row in targeted:
        if row["joint_kinematically_reachable_count"] > 0:
            route = "TRANSPORT_AWARE_SIGNED_SAMPLER_STATIC_WITNESS_EXISTS"
        elif row["truncation"]:
            route = "MATE_CAPACITY_UNRESOLVED_DUE_TO_CENSUS_CAP"
        else:
            route = "TRANSPORT_AWARE_SIGNED_SAMPLER_INSUFFICIENT_KINEMATICALLY"
        routes.append({"sample_id": row["sample_id"], "routing": route})
    payload = {"schema_version": 1, "status": "F86N_R1_STATIC_PREFLIGHT_ZERO_DYNAMIC_COMPUTE", "candidate_profile": PROFILE, "manifest": "artifacts/f86n_r1_transport_aware_signed_sampler/manifest.json", "static": static, "targeted_static_mate_capacity": targeted, "routing": {"static": routes, "dynamic": "NOT_RUN_BY_STATIC_PREFLIGHT"}, "static_candidate_checks": {"V4-3": targeted[0]["candidate_position_count"], "V5-3": targeted[1]["candidate_position_count"], "total": total, "per_cell_cap": STATIC_CAP_PER_CELL, "total_cap": STATIC_CAP_TOTAL}, "dynamic": {"real_games": 0, "tactical_nodes": 0, "bfs_expansions": 0, "teacher_search_training": 0, "f85_actual_compute": 0}, "default_generator_changed": False}
    _write_json(output, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--prep", action="store_true")
    parser.add_argument("--manifest-output", type=Path, default=Path("artifacts/f86n_r1_transport_aware_signed_sampler/manifest.json"))
    parser.add_argument("--result-output", type=Path, default=Path("artifacts/f86n_r1_transport_aware_signed_sampler/results.json"))
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
