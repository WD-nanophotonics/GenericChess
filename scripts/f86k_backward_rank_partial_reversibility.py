"""F86K backward-rank targeted partial reversibility, static-only and bounded."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict, ruleset_to_dict

try:
    from scripts.f86i_reversibility_rescue import (
        SAMPLES,
        STATIC_CAP_PER_CELL,
        STATIC_CAP_TOTAL,
        _candidate_static_census,
        _orthogonal_anchor_atoms,
        _source_rows,
        _static_mechanism,
    )
except ModuleNotFoundError:
    from f86i_reversibility_rescue import (
        SAMPLES,
        STATIC_CAP_PER_CELL,
        STATIC_CAP_TOTAL,
        _candidate_static_census,
        _orthogonal_anchor_atoms,
        _source_rows,
        _static_mechanism,
    )


PROFILE = "ORTHO4_PLUS_FIRST_STRICT_FORWARD_REVERSE_ORDINARY"
SOURCE_ARTIFACT = "artifacts/f86c_generator_viability/rulesets.json"
F86I_MANIFEST = "artifacts/f86i_reversibility_rescue/manifest.json"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _reverse_atom(atom):
    if isinstance(atom, LeapAtom):
        return LeapAtom((-atom.offset[0], -atom.offset[1]))
    return RayAtom((-atom.direction[0], -atom.direction[1]), atom.max_steps)


def _strict_forward(atom) -> bool:
    vector = atom.offset if isinstance(atom, LeapAtom) else atom.direction
    return vector[1] > 0


def _atom_payload(atom) -> dict[str, Any]:
    if isinstance(atom, LeapAtom):
        return {"kind": "LEAP", "offset": list(atom.offset)}
    return {"kind": "RAY", "direction": list(atom.direction), "max_steps": atom.max_steps}


def _candidate_ruleset(source):
    piece_types = []
    selections: dict[str, dict[str, Any]] = {}
    for piece_type in source.piece_types:
        if piece_type.is_anchor:
            piece_types.append(replace(piece_type, movement_atoms=_orthogonal_anchor_atoms()))
            continue
        atoms = list(piece_type.movement_atoms)
        selected_index = next((index for index, atom in enumerate(atoms) if _strict_forward(atom)), None)
        if selected_index is None:
            selections[piece_type.type_id] = {
                "status": "NO_STRICT_FORWARD_SOURCE_ATOM",
                "selected_atom_index": None,
                "selected_atom": None,
                "reverse_atom": None,
                "reverse_present_before": False,
                "reverse_added": False,
            }
            piece_types.append(piece_type)
            continue
        selected = atoms[selected_index]
        reverse = _reverse_atom(selected)
        reverse_present = reverse in atoms
        if not reverse_present:
            atoms.append(reverse)
        selections[piece_type.type_id] = {
            "status": "SELECTED_STRICT_FORWARD_SOURCE_ATOM",
            "selected_atom_index": selected_index,
            "selected_atom": _atom_payload(selected),
            "reverse_atom": _atom_payload(reverse),
            "reverse_present_before": reverse_present,
            "reverse_added": not reverse_present,
        }
        piece_types.append(replace(piece_type, movement_atoms=tuple(atoms)))
    candidate = replace(
        source,
        piece_types=tuple(piece_types),
        metadata={
            **source.metadata,
            "candidate_profile": PROFILE,
            "source_generator": "f86c-minimal",
            "experimental_candidate": True,
        },
    )
    return candidate, selections


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _load_f86i_fingerprints(root: Path) -> dict[str, str]:
    manifest = _load_json(root, F86I_MANIFEST)
    if manifest["candidate_profile"] != "ORTHO4_PLUS_REVERSE_CLOSED_ORDINARY":
        raise RuntimeError("F86I manifest profile mismatch")
    return {
        entry["sample_id"]: entry["candidate_ruleset_fingerprint"]
        for entry in manifest["entries"]
    }


def _entry(sample_id: str, board_size: int, source_seed: int, source_row: dict[str, Any], f86i_fingerprints: dict[str, str]) -> dict[str, Any]:
    source = ruleset_from_dict(source_row["ruleset"])
    source_compiled = compile_ruleset(source)
    if source_compiled.ruleset_fingerprint != source_row["ruleset_fingerprint"]:
        raise RuntimeError(f"source fingerprint mismatch for {sample_id}")
    candidate, selections = _candidate_ruleset(source)
    candidate_compiled = compile_ruleset(candidate)
    f86i_fingerprint = f86i_fingerprints[sample_id]
    return {
        "sample_id": sample_id,
        "board_size": board_size,
        "ordinary_count": source_row["ordinary_count"],
        "source_seed": source_seed,
        "source_ruleset_fingerprint": source_compiled.ruleset_fingerprint,
        "source_ruleset": source_row["ruleset"],
        "candidate_profile": PROFILE,
        "candidate_ruleset_fingerprint": candidate_compiled.ruleset_fingerprint,
        "candidate_ruleset": ruleset_to_dict(candidate),
        "f86i_full_closure_candidate_fingerprint": f86i_fingerprint,
        "collapse_to_f86i_full_closure": candidate_compiled.ruleset_fingerprint == f86i_fingerprint,
        "fingerprint_binding": {
            "source": source_compiled.ruleset_fingerprint,
            "candidate": candidate_compiled.ruleset_fingerprint,
            "f86i_full_closure_candidate": f86i_fingerprint,
        },
        "movement_transform": {
            "anchor": "fixed_ortho4_leaps_(1,0),(-1,0),(0,1),(0,-1)",
            "ordinary": "append_reverse_of_first_strict_forward_source_atom_only",
            "strict_forward": "LEAP offset[1] > 0; RAY direction[1] > 0",
            "no_strict_forward": "record_NO_STRICT_FORWARD_SOURCE_ATOM_and_add_no_family",
            "dedupe": True,
            "ordering": "original_atoms_then_selected_reverse_atom",
        },
        "per_type_selection": selections,
    }


def build_manifest(root: Path, output: Path) -> dict[str, Any]:
    source_rows = _source_rows(root)
    f86i_fingerprints = _load_f86i_fingerprints(root)
    entries = [
        _entry(sample_id, board_size, source_seed, source_rows[sample_id], f86i_fingerprints)
        for sample_id, board_size, source_seed in SAMPLES
    ]
    payload = {
        "schema_version": 1,
        "status": "PRE_REGISTERED_STATIC_EXPERIMENTAL_CANDIDATE",
        "candidate_profile": PROFILE,
        "source_artifact": SOURCE_ARTIFACT,
        "f86i_comparison_manifest": F86I_MANIFEST,
        "source_sample_ids": [sample_id for sample_id, _, _ in SAMPLES],
        "entries": entries,
        "static_budget": {
            "candidate_checks_per_cell": STATIC_CAP_PER_CELL,
            "candidate_checks_total_cap": STATIC_CAP_TOTAL,
            "targeted_cells": ["V4-3", "V5-3"],
        },
        "dynamic_budget": {"real_games": 0, "max_ply": 0},
        "default_generator_changed": False,
        "result_driven_replacement_forbidden": True,
    }
    _write_json(output, payload)
    return payload


def _load_manifest(root: Path) -> dict[str, Any]:
    manifest = _load_json(root, "artifacts/f86k_backward_rank_partial_reversibility/manifest.json")
    if manifest["candidate_profile"] != PROFILE or manifest["status"] != "PRE_REGISTERED_STATIC_EXPERIMENTAL_CANDIDATE":
        raise RuntimeError("F86K manifest is not the pre-registered candidate")
    return manifest


def _owner_relative_rank(square_index: int, owner: int, board_size: int) -> int:
    rank = square_index // board_size
    return rank if owner == 0 else board_size - 1 - rank


def _backward_rank_diagnostics(compiled) -> dict[str, Any]:
    n = compiled.board_size
    anchor_type = next(piece_type.type_id for piece_type in compiled.piece_types if piece_type.is_anchor)
    ordinary_types = [piece_type.type_id for piece_type in compiled.piece_types if not piece_type.is_anchor]
    type_rows = []
    for type_id in sorted(ordinary_types):
        backward_edge = False
        for owner in (0, 1):
            for source in range(n * n):
                source_rank = _owner_relative_rank(source, owner, n)
                backward_edge |= any(
                    _owner_relative_rank(target.rank * n + target.file, owner, n) < source_rank
                    for target in compiled.empty_mobility[type_id][owner][source]
                )
        type_rows.append({"type_id": type_id, "can_reach_lower_owner_relative_rank": backward_edge})

    opening_rows = []
    for index, piece in enumerate(compiled.initial_position.board):
        if piece is None or piece.current_type_id == anchor_type:
            continue
        owner = piece.owner
        source_rank = _owner_relative_rank(index, owner, n)
        visited = {index}
        queue = [index]
        while queue:
            current = queue.pop(0)
            for target in compiled.empty_mobility[piece.current_type_id][owner][current]:
                target_index = target.rank * n + target.file
                if target_index not in visited:
                    visited.add(target_index)
                    queue.append(target_index)
        lower = sorted(
            target for target in visited
            if _owner_relative_rank(target, owner, n) < source_rank
        )
        opening_rows.append({
            "owner": owner,
            "type_id": piece.current_type_id,
            "source_square": [index % n, index // n],
            "source_owner_relative_rank": source_rank,
            "can_reach_lower_owner_relative_rank": bool(lower),
        })
    lower_count = sum(row["can_reach_lower_owner_relative_rank"] for row in opening_rows)
    return {
        "owner_relative_rank_definition": "owner 0 rank=board rank; owner 1 rank=board_size-1-board rank",
        "backward_capable_ordinary_type_count": sum(row["can_reach_lower_owner_relative_rank"] for row in type_rows),
        "ordinary_type_count": len(type_rows),
        "backward_capable_ordinary_type_fraction": (
            sum(row["can_reach_lower_owner_relative_rank"] for row in type_rows) / len(type_rows)
            if type_rows else 0.0
        ),
        "backward_capable_ordinary_types": type_rows,
        "opening_ordinary_piece_count": len(opening_rows),
        "opening_ordinary_pieces_reaching_lower_owner_relative_rank": lower_count,
        "opening_ordinary_piece_lower_rank_fraction": lower_count / len(opening_rows) if opening_rows else 0.0,
        "opening_ordinary_piece_diagnostics": opening_rows,
    }


def _targeted_route(row: dict[str, Any]) -> str:
    if row["joint_kinematically_reachable_count"] > 0:
        return "BACKWARD_RANK_RESCUE_STATIC_WITNESS_EXISTS"
    if row["truncation"]:
        return "MATE_CAPACITY_UNRESOLVED_DUE_TO_CENSUS_CAP"
    return "BACKWARD_RANK_RESCUE_INSUFFICIENT_KINEMATICALLY"


def run(root: Path, output: Path) -> dict[str, Any]:
    manifest = _load_manifest(root)
    entries = []
    for entry in manifest["entries"]:
        compiled = compile_ruleset(ruleset_from_dict(entry["candidate_ruleset"]))
        if compiled.ruleset_fingerprint != entry["candidate_ruleset_fingerprint"]:
            raise RuntimeError(f"candidate fingerprint mismatch for {entry['sample_id']}")
        entries.append((entry, compiled))

    static = []
    for entry, compiled in entries:
        mechanism = _static_mechanism(compiled)
        static.append({
            "sample_id": entry["sample_id"],
            "board_size": entry["board_size"],
            "source_seed": entry["source_seed"],
            "candidate_ruleset_fingerprint": entry["candidate_ruleset_fingerprint"],
            "source_ruleset_fingerprint": entry["source_ruleset_fingerprint"],
            "collapse_to_f86i_full_closure": entry["collapse_to_f86i_full_closure"],
            "per_type_selection": entry["per_type_selection"],
            "mechanism": {
                "ordinary_sink_fraction": mechanism["ordinary_sink_fraction"],
                "ordinary_direct_reverse_edge_fraction": mechanism["ordinary_direct_reverse_edge_fraction"],
                "ordinary_nontrivial_scc_vertex_fraction": mechanism["ordinary_nontrivial_scc_vertex_fraction"],
                "ordinary_all_monotone_dag": mechanism["ordinary_all_monotone_dag"],
            },
            "backward_rank": _backward_rank_diagnostics(compiled),
        })

    targeted = []
    for entry, compiled in entries:
        if entry["sample_id"] not in {"V4-3", "V5-3"}:
            continue
        result = _candidate_static_census(entry["sample_id"], compiled)
        census = result["census"]
        kinematic = result["kinematic"]
        targeted.append({
            "sample_id": entry["sample_id"],
            "cell": "CANDIDATE_BACKWARD_RANK",
            "ruleset_fingerprint": compiled.ruleset_fingerprint,
            "candidate_position_count": census["candidate_position_count"],
            "validated_position_count": census["validated_position_count"],
            "validated_template_count": census["validated_template_count"],
            "truncation": census["truncation"],
            "ordinary_assignment_reachable_count": kinematic["ordinary_assignment_reachable_count"],
            "joint_kinematically_reachable_count": kinematic["joint_kinematically_reachable_count"],
            "minimum_optimistic_ply_lower_bound": kinematic["minimum_optimistic_ply_lower_bound"],
        })

    payload = {
        "schema_version": 1,
        "status": "F86K_STATIC_ONLY_ZERO_DYNAMIC_COMPUTE",
        "candidate_profile": PROFILE,
        "manifest": "artifacts/f86k_backward_rank_partial_reversibility/manifest.json",
        "ruleset_fingerprints": {
            row["sample_id"]: {
                "source": row["source_ruleset_fingerprint"],
                "candidate_backward_rank": row["candidate_ruleset_fingerprint"],
                "f86i_full_closure": next(
                    entry["f86i_full_closure_candidate_fingerprint"]
                    for entry in manifest["entries"] if entry["sample_id"] == row["sample_id"]
                ),
            }
            for row in static
        },
        "static": static,
        "targeted_static_mate_capacity": targeted,
        "routing": {
            "mechanism": "BACKWARD_RANK_PARTIAL_REVERSIBILITY_WITH_STRICT_FORWARD_SOURCE_SELECTION",
            "static": [{"sample_id": row["sample_id"], "routing": _targeted_route(row)} for row in targeted],
            "dynamic": "NOT_RUN_BY_CHEAP_STATIC_FIRST_GATE",
        },
        "static_candidate_checks": {
            "V4-3": next(row["candidate_position_count"] for row in targeted if row["sample_id"] == "V4-3"),
            "V5-3": next(row["candidate_position_count"] for row in targeted if row["sample_id"] == "V5-3"),
            "total": sum(row["candidate_position_count"] for row in targeted),
            "per_cell_cap": STATIC_CAP_PER_CELL,
            "total_cap": STATIC_CAP_TOTAL,
        },
        "dynamic": {"real_games": 0, "policy_trajectories": 0},
        "tactical_probe_nodes": 0,
        "bfs_expansions": 0,
        "teacher_search_compute": 0,
        "f85_actual_compute": 0,
        "default_generator_changed": False,
    }
    _write_json(output, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--prep", action="store_true")
    parser.add_argument("--manifest-output", type=Path, default=Path("artifacts/f86k_backward_rank_partial_reversibility/manifest.json"))
    parser.add_argument("--result-output", type=Path, default=Path("artifacts/f86k_backward_rank_partial_reversibility/results.json"))
    args = parser.parse_args()
    if args.prep:
        payload = build_manifest(args.root, args.manifest_output)
        print(json.dumps({"status": payload["status"], "sample_count": len(payload["entries"])}, sort_keys=True))
    else:
        payload = run(args.root, args.result_output)
        print(json.dumps({"status": payload["status"], "static_candidate_checks": payload["static_candidate_checks"]["total"], "dynamic_games": payload["dynamic"]["real_games"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
