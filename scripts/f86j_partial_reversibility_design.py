"""F86J controlled partial-reversibility design, static-only and bounded."""

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


PROFILE = "ORTHO4_PLUS_FIRST_ATOM_REVERSE_ORDINARY"
SOURCE_ARTIFACT = "artifacts/f86c_generator_viability/rulesets.json"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _reverse_atom(atom):
    if isinstance(atom, LeapAtom):
        return LeapAtom((-atom.offset[0], -atom.offset[1]))
    return RayAtom((-atom.direction[0], -atom.direction[1]), atom.max_steps)


def _candidate_ruleset(source):
    piece_types = []
    for piece_type in source.piece_types:
        if piece_type.is_anchor:
            atoms = _orthogonal_anchor_atoms()
        else:
            atoms = list(piece_type.movement_atoms)
            if atoms:
                reverse = _reverse_atom(atoms[0])
                if reverse not in atoms:
                    atoms.append(reverse)
        piece_types.append(replace(piece_type, movement_atoms=tuple(atoms)))
    return replace(
        source,
        piece_types=tuple(piece_types),
        metadata={
            **source.metadata,
            "candidate_profile": PROFILE,
            "source_generator": "f86c-minimal",
            "experimental_candidate": True,
        },
    )


def _entry(sample_id: str, board_size: int, source_seed: int, source_row: dict[str, Any]) -> dict[str, Any]:
    source = ruleset_from_dict(source_row["ruleset"])
    source_compiled = compile_ruleset(source)
    if source_compiled.ruleset_fingerprint != source_row["ruleset_fingerprint"]:
        raise RuntimeError(f"source fingerprint mismatch for {sample_id}")
    candidate = _candidate_ruleset(source)
    candidate_compiled = compile_ruleset(candidate)
    source_atoms = sum(
        len(piece.movement_atoms) for piece in source.piece_types if not piece.is_anchor
    )
    candidate_atoms = sum(
        len(piece.movement_atoms) for piece in candidate.piece_types if not piece.is_anchor
    )
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
        "movement_transform": {
            "anchor": "fixed_ortho4_leaps_(1,0),(-1,0),(0,1),(0,-1)",
            "ordinary": "append_reverse_counterpart_only_for_each_type_first_atom",
            "dedupe": True,
            "ordering": "original_atoms_then_selected_reverse_atoms",
            "selected_atom_rule": "first_atom_in_frozen_source_order_per_ordinary_type",
        },
        "atom_counts": {
            "ordinary_source": source_atoms,
            "ordinary_candidate": candidate_atoms,
            "reverse_atoms_added": candidate_atoms - source_atoms,
        },
    }


def build_manifest(root: Path, output: Path) -> dict[str, Any]:
    source_rows = _source_rows(root)
    entries = [
        _entry(sample_id, board_size, source_seed, source_rows[sample_id])
        for sample_id, board_size, source_seed in SAMPLES
    ]
    payload = {
        "schema_version": 1,
        "status": "PRE_REGISTERED_STATIC_EXPERIMENTAL_CANDIDATE",
        "candidate_profile": PROFILE,
        "source_artifact": SOURCE_ARTIFACT,
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
    payload = json.loads(
        (root / "artifacts/f86j_partial_reversibility_design/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    if payload["candidate_profile"] != PROFILE:
        raise RuntimeError("F86J manifest profile mismatch")
    return payload


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
            "atom_counts": entry["atom_counts"],
            "mechanism": {
                "ordinary_sink_fraction": mechanism["ordinary_sink_fraction"],
                "ordinary_direct_reverse_edge_fraction": mechanism["ordinary_direct_reverse_edge_fraction"],
                "ordinary_nontrivial_scc_vertex_fraction": mechanism["ordinary_nontrivial_scc_vertex_fraction"],
                "ordinary_all_monotone_dag": mechanism["ordinary_all_monotone_dag"],
            },
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
            "cell": "CANDIDATE_PARTIAL",
            "ruleset_fingerprint": compiled.ruleset_fingerprint,
            "candidate_position_count": census["candidate_position_count"],
            "validated_position_count": census["validated_position_count"],
            "validated_template_count": census["validated_template_count"],
            "truncation": census["truncation"],
            "ordinary_assignment_reachable_count": kinematic["ordinary_assignment_reachable_count"],
            "joint_kinematically_reachable_count": kinematic["joint_kinematically_reachable_count"],
            "minimum_optimistic_ply_lower_bound": kinematic["minimum_optimistic_ply_lower_bound"],
        })
    fingerprints = {
        row["sample_id"]: {"CANDIDATE_PARTIAL": row["candidate_ruleset_fingerprint"]}
        for row in static
    }
    payload = {
        "schema_version": 1,
        "status": "F86J_STATIC_ONLY_ZERO_DYNAMIC_COMPUTE",
        "candidate_profile": PROFILE,
        "manifest": "artifacts/f86j_partial_reversibility_design/manifest.json",
        "ruleset_fingerprints": fingerprints,
        "static": static,
        "targeted_static_mate_capacity": targeted,
        "static_candidate_checks": {
            "V4-3": targeted[0]["candidate_position_count"],
            "V5-3": targeted[1]["candidate_position_count"],
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
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=Path("artifacts/f86j_partial_reversibility_design/manifest.json"),
    )
    parser.add_argument(
        "--result-output",
        type=Path,
        default=Path("artifacts/f86j_partial_reversibility_design/results.json"),
    )
    args = parser.parse_args()
    if args.prep:
        payload = build_manifest(args.root, args.manifest_output)
        print(json.dumps({"status": payload["status"], "sample_count": len(payload["entries"])}, sort_keys=True))
    else:
        payload = run(args.root, args.result_output)
        print(json.dumps({
            "status": payload["status"],
            "static_candidate_checks": payload["static_candidate_checks"]["total"],
            "dynamic_games": payload["dynamic"]["real_games"],
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
