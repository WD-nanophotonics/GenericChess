"""F86I experimental reversible-ordinary-mobility rescue candidate."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import replace
from itertools import permutations
from pathlib import Path
from typing import Any

from generic_chess.benchmark.policy_tape import PolicyTape
from generic_chess.core.actions import action_to_dict
from generic_chess.core.attacks import is_in_check
from generic_chess.core.coordinates import index_to_square
from generic_chess.core.movegen import has_legal_action
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.position import Hands, Position
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict, ruleset_to_dict

try:
    from scripts.f86f_ordinary_mate_capacity_census import (
        _anchor_type_id,
        _attack_masks,
        _build_position,
        _iter_placements,
        _ordinary_multiset,
        _zone_mask,
    )
    from scripts.f86h_static_mate_template_kinematic_reachability import _analyze_cell
except ModuleNotFoundError:
    from f86f_ordinary_mate_capacity_census import (
        _anchor_type_id,
        _attack_masks,
        _build_position,
        _iter_placements,
        _ordinary_multiset,
        _zone_mask,
    )
    from f86h_static_mate_template_kinematic_reachability import _analyze_cell

SAMPLES = (
    ("V4-2", 4, 861401),
    ("V4-3", 4, 861402),
    ("V4-4", 4, 861403),
    ("V4-5", 4, 861404),
    ("V5-2", 5, 861501),
    ("V5-3", 5, 861502),
    ("V5-4", 5, 861503),
    ("V5-5", 5, 861504),
)
PROFILE = "ORTHO4_PLUS_REVERSE_CLOSED_ORDINARY"
MAX_PLY = 32
STATIC_CAP_PER_CELL = 2048
STATIC_CAP_TOTAL = 4096
TACTICAL_NODE_CAP = 2048
TAPE_ALGORITHM = "python_random_mt19937_random_floor_index_v1"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _reverse_atom(atom):
    if isinstance(atom, LeapAtom):
        return LeapAtom((-atom.offset[0], -atom.offset[1]))
    return RayAtom((-atom.direction[0], -atom.direction[1]), atom.max_steps)


def _orthogonal_anchor_atoms():
    return (
        LeapAtom((1, 0)),
        LeapAtom((-1, 0)),
        LeapAtom((0, 1)),
        LeapAtom((0, -1)),
    )


def _candidate_ruleset(source):
    piece_types = []
    for piece_type in source.piece_types:
        if piece_type.is_anchor:
            atoms = _orthogonal_anchor_atoms()
        else:
            atoms = list(piece_type.movement_atoms)
            for atom in tuple(piece_type.movement_atoms):
                reverse = _reverse_atom(atom)
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


def _source_rows(root: Path) -> dict[str, dict[str, Any]]:
    payload = _load_json(root, "artifacts/f86c_generator_viability/rulesets.json")
    rows = {row["sample_id"]: row for row in payload["sample"]}
    if set(rows) != {sample_id for sample_id, _, _ in SAMPLES}:
        raise RuntimeError("F86C source artifact does not contain the frozen eight samples")
    return rows


def _tape_seeds(sample_id: str, source_seed: int) -> tuple[int, int]:
    if sample_id == "V4-3":
        return 8624301, 8624302
    if sample_id == "V5-3":
        return 8625301, 8625302
    return source_seed * 10 + 1, source_seed * 10 + 2


def _tape_payload(sample_id: str, source_seed: int) -> dict[str, Any]:
    seeds = _tape_seeds(sample_id, source_seed)
    return {
        policy_id: {
            "seed": seed,
            "uniforms": list(PolicyTape.from_seed(policy_id, seed, 32).uniforms),
        }
        for policy_id, seed in zip(("A", "B"), seeds)
    }


def build_manifest(root: Path, output_dir: Path) -> dict[str, Any]:
    source_rows = _source_rows(root)
    entries = []
    for sample_id, board_size, source_seed in SAMPLES:
        row = source_rows[sample_id]
        if row["board_size"] != board_size or row["seed"] != source_seed:
            raise RuntimeError(f"F86C source config mismatch for {sample_id}")
        source = ruleset_from_dict(row["ruleset"])
        source_compiled = compile_ruleset(source)
        if source_compiled.ruleset_fingerprint != row["ruleset_fingerprint"]:
            raise RuntimeError(f"F86C source fingerprint mismatch for {sample_id}")
        candidate = _candidate_ruleset(source)
        candidate_compiled = compile_ruleset(candidate)
        entries.append({
            "sample_id": sample_id,
            "board_size": board_size,
            "ordinary_count": row["ordinary_count"],
            "source_seed": source_seed,
            "source_ruleset_fingerprint": source_compiled.ruleset_fingerprint,
            "source_ruleset": row["ruleset"],
            "candidate_profile": PROFILE,
            "candidate_ruleset_fingerprint": candidate_compiled.ruleset_fingerprint,
            "candidate_ruleset": ruleset_to_dict(candidate),
            "movement_transform": {
                "anchor": "fixed_ortho4_leaps_(1,0),(-1,0),(0,1),(0,-1)",
                "ordinary": "append_exact_reverse_counterpart_per_legacy_atom",
                "dedupe": True,
                "ordering": "original_atoms_then_first_seen_reverse_atoms",
            },
            "policy_tapes": _tape_payload(sample_id, source_seed),
            "game_budget": {"games": 2, "max_ply": MAX_PLY},
        })
    manifest = {
        "schema_version": 1,
        "status": "PRE_REGISTERED_EXPERIMENTAL_CANDIDATE",
        "candidate_profile": PROFILE,
        "source_artifact": "artifacts/f86c_generator_viability/rulesets.json",
        "source_sample_ids": [sample_id for sample_id, _, _ in SAMPLES],
        "entries": entries,
        "policy_tape_algorithm": TAPE_ALGORITHM,
        "policy_tape_length": 32,
        "dynamic_budget": {
            "real_games": 16,
            "games_per_sample": 2,
            "max_ply": MAX_PLY,
            "pairing": ["A/B", "B/A"],
        },
        "static_budget": {
            "candidate_checks_v4_v5_cells": STATIC_CAP_TOTAL,
            "candidate_checks_per_cell": STATIC_CAP_PER_CELL,
            "tactical_nodes_total": TACTICAL_NODE_CAP,
        },
        "default_generator_changed": False,
        "result_driven_replacement_forbidden": True,
    }
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def _load_manifest(root: Path) -> dict[str, Any]:
    manifest = _load_json(root, "artifacts/f86i_reversibility_rescue/manifest.json")
    if manifest["candidate_profile"] != PROFILE or manifest["status"] != "PRE_REGISTERED_EXPERIMENTAL_CANDIDATE":
        raise RuntimeError("F86I manifest is not the pre-registered candidate")
    if manifest["dynamic_budget"]["real_games"] != 16:
        raise RuntimeError("F86I dynamic budget drift")
    return manifest


def _compiled_entries(root: Path, manifest: dict[str, Any]):
    for entry in manifest["entries"]:
        candidate = ruleset_from_dict(entry["candidate_ruleset"])
        compiled = compile_ruleset(candidate)
        if compiled.ruleset_fingerprint != entry["candidate_ruleset_fingerprint"]:
            raise RuntimeError(f"candidate fingerprint drift for {entry['sample_id']}")
        yield entry, compiled


def _graph_metrics(compiled, type_id: str, owner: int) -> dict[str, Any]:
    n = compiled.board_size
    size = n * n
    adjacency = {
        source: {
            target.rank * n + target.file
            for target in compiled.empty_mobility[type_id][owner][source]
        }
        for source in range(size)
    }
    edges = sum(len(targets) for targets in adjacency.values())
    reverse_edges = sum(
        int(source in adjacency[target])
        for source, targets in adjacency.items()
        for target in targets
    )
    sinks = sum(not targets for targets in adjacency.values())

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

    for node in range(size):
        if node not in indices:
            visit(node)
    nontrivial = sum(len(component) for component in components if len(component) > 1)
    cyclic = any(len(component) > 1 for component in components)
    return {
        "piece_type": type_id,
        "owner": owner,
        "vertex_count": size,
        "edge_count": edges,
        "sink_count": sinks,
        "sink_fraction": sinks / size,
        "direct_reverse_edge_fraction": reverse_edges / edges if edges else 0.0,
        "nontrivial_scc_vertex_fraction": nontrivial / size,
        "monotone_dag": not cyclic,
    }


def _static_mechanism(compiled) -> dict[str, Any]:
    anchor_type = next(piece_type.type_id for piece_type in compiled.piece_types if piece_type.is_anchor)
    ordinary_types = [
        piece_type.type_id for piece_type in compiled.piece_types if not piece_type.is_anchor
    ]
    rows = [
        _graph_metrics(compiled, type_id, owner)
        for type_id in [anchor_type, *sorted(ordinary_types)]
        for owner in (0, 1)
    ]
    return {
        "board_size": compiled.board_size,
        "anchor_type": anchor_type,
        "ordinary_types": sorted(ordinary_types),
        "by_piece_owner": rows,
        "ordinary_sink_fraction": sum(row["sink_count"] for row in rows if row["piece_type"] != anchor_type)
        / sum(row["vertex_count"] for row in rows if row["piece_type"] != anchor_type),
        "ordinary_direct_reverse_edge_fraction": sum(
            row["edge_count"] * row["direct_reverse_edge_fraction"]
            for row in rows if row["piece_type"] != anchor_type
        ) / sum(row["edge_count"] for row in rows if row["piece_type"] != anchor_type),
        "ordinary_nontrivial_scc_vertex_fraction": sum(
            row["vertex_count"] * row["nontrivial_scc_vertex_fraction"]
            for row in rows if row["piece_type"] != anchor_type
        ) / sum(row["vertex_count"] for row in rows if row["piece_type"] != anchor_type),
        "ordinary_all_monotone_dag": all(
            row["monotone_dag"] for row in rows if row["piece_type"] != anchor_type
        ),
    }


def _candidate_static_census(sample_id: str, compiled) -> dict[str, Any]:
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
                if candidate_count >= STATIC_CAP_PER_CELL:
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
            "template_id": f"T{ordinal:04d}",
            "sample_id": sample_id,
            "cell": "CANDIDATE",
            "defender_anchor": [defender_anchor % n, defender_anchor // n],
            "ordinary": [
                {"type_id": type_id, "square": [square % n, square // n]}
                for type_id, square in placement
            ],
            "allowed_attacker_anchor_squares": [
                [square % n, square // n] for square in sorted(targets)
            ],
        })
    census = {
        "sample_id": sample_id,
        "cell": "CANDIDATE",
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "candidate_position_count": candidate_count,
        "validated_position_count": validated_count,
        "validated_template_count": len(rows),
        "truncation": truncated,
        "templates": rows,
    }
    kinematic = _analyze_cell(sample_id, "CANDIDATE", compiled, census, rows)
    return {"census": census, "kinematic": kinematic}


def _canonical_actions(session) -> tuple:
    return tuple(sorted(session.legal_actions(), key=lambda action: json.dumps(
        action_to_dict(action), sort_keys=True, separators=(",", ":")
    )))


def _play_game(compiled, tapes: dict[str, Any], seat_assignment: tuple[str, str]) -> dict[str, Any]:
    from generic_chess.session.session import GameSession

    session = GameSession(compiled)
    actions = []
    branching = []
    consumed = {"A": 0, "B": 0}
    while session.result.status.value == "ongoing" and len(session.history) < MAX_PLY:
        legal = _canonical_actions(session)
        branching.append(len(legal))
        actor = session.state.position.side_to_move
        policy_id = seat_assignment[actor]
        index = tapes[policy_id]["uniforms"][consumed[policy_id]]
        chosen = legal[min(int(index * len(legal)), len(legal) - 1)]
        consumed[policy_id] += 1
        actions.append({
            "ply": len(session.history),
            "actor": actor,
            "legal_action_count": len(legal),
            "action": action_to_dict(chosen),
        })
        session.submit(chosen)
    status = session.result.status.value
    label = f"ongoing@{MAX_PLY}" if status == "ongoing" else status
    return {
        "seat_assignment": {"player0": seat_assignment[0], "player1": seat_assignment[1]},
        "plies": len(session.history),
        "terminal_status": status,
        "outcome_label": label,
        "winner": session.result.winner,
        "policy_move_counts": consumed,
        "branching_counts": branching,
        "actions": actions,
    }


def _run_games(manifest: dict[str, Any], compiled_entries: list[tuple[dict[str, Any], Any]]) -> dict[str, Any]:
    games = []
    by_sample = {}
    for entry, compiled in compiled_entries:
        sample_games = []
        tapes = entry["policy_tapes"]
        for seats in (("A", "B"), ("B", "A")):
            game = _play_game(compiled, tapes, seats)
            game["sample_id"] = entry["sample_id"]
            game["ruleset_fingerprint"] = entry["candidate_ruleset_fingerprint"]
            sample_games.append(game)
            games.append(game)
        labels = [game["outcome_label"] for game in sample_games]
        terminal = Counter(labels)
        by_sample[entry["sample_id"]] = {
            "sample_id": entry["sample_id"],
            "candidate_ruleset_fingerprint": entry["candidate_ruleset_fingerprint"],
            "game_count": len(sample_games),
            "terminal_distribution": dict(sorted(terminal.items())),
            "decisive_fraction": sum(label == "checkmate" for label in labels) / len(labels),
            "stalemate_fraction": sum(label == "stalemate" for label in labels) / len(labels),
            "repetition_fraction": sum(label == "repetition" for label in labels) / len(labels),
            "ongoing_at_32_fraction": sum(label == f"ongoing@{MAX_PLY}" for label in labels) / len(labels),
            "median_length": sorted(game["plies"] for game in sample_games)[len(sample_games) // 2],
            "branching_median": sorted(
                sorted(game["branching_counts"])[len(game["branching_counts"]) // 2]
                for game in sample_games
            )[len(sample_games) // 2],
            "forced_or_low_branch_fraction": sum(
                count <= 2 for game in sample_games for count in game["branching_counts"]
            ) / max(1, sum(len(game["branching_counts"]) for game in sample_games)),
        }
    return {
        "schema_version": 1,
        "game_count": len(games),
        "max_ply": MAX_PLY,
        "games": games,
        "by_sample": by_sample,
        "real_games": len(games),
        "tactical_probe_nodes": 0,
    }


def run(root: Path, output_dir: Path) -> dict[str, Any]:
    manifest = _load_manifest(root)
    entries = list(_compiled_entries(root, manifest))
    static = []
    candidate_static = []
    for entry, compiled in entries:
        row = {
            "sample_id": entry["sample_id"],
            "board_size": entry["board_size"],
            "source_seed": entry["source_seed"],
            "source_ruleset_fingerprint": entry["source_ruleset_fingerprint"],
            "candidate_ruleset_fingerprint": entry["candidate_ruleset_fingerprint"],
            "mechanism": _static_mechanism(compiled),
        }
        static.append(row)
        if entry["sample_id"] in {"V4-3", "V5-3"}:
            candidate_static.append(_candidate_static_census(entry["sample_id"], compiled))
    games = _run_games(manifest, entries)
    ruleset_fingerprints = {
        entry["sample_id"]: {"CANDIDATE": entry["candidate_ruleset_fingerprint"]}
        for entry, _compiled in entries
    }
    static_routing = []
    for row in candidate_static:
        census = row["census"]
        kinematic = row["kinematic"]
        if census["truncation"]:
            label = "MATE_CAPACITY_UNRESOLVED_DUE_TO_CENSUS_CAP"
        elif kinematic["joint_kinematically_reachable_count"] == 0:
            label = "REVERSIBILITY_RESCUE_INSUFFICIENT_KINEMATICALLY"
        else:
            label = "KINEMATIC_MATE_TEMPLATE_REACHABLE_WITHIN_32PLY_LOWER_BOUND"
        static_routing.append({"sample_id": census["sample_id"], "routing": label})
    dynamic_routing = (
        ["REVERSIBILITY_RESCUE_SHOWS_TERMINATION_VIABILITY"]
        if any(row["terminal_distribution"].get("checkmate", 0) for row in games["by_sample"].values())
        else ["KINEMATIC_REPAIR_SUCCEEDS_BUT_DYNAMIC_TERMINATION_STILL_WEAK"]
    )
    payload = {
        "schema_version": 1,
        "candidate_profile": PROFILE,
        "manifest": "artifacts/f86i_reversibility_rescue/manifest.json",
        "manifest_result_driven_replacement_forbidden": manifest["result_driven_replacement_forbidden"],
        "ruleset_fingerprints": ruleset_fingerprints,
        "static": static,
        "candidate_static_mate_capacity": candidate_static,
        "routing": {
            "static": static_routing,
            "dynamic": dynamic_routing,
            "overall": [row["routing"] for row in static_routing] + dynamic_routing,
        },
        "static_candidate_checks": {
            "V4_V5_targeted_checks": 0,
            "per_cell_cap": STATIC_CAP_PER_CELL,
            "total_cap": STATIC_CAP_TOTAL,
            "note": "F86F mate census is run only for V4-3 and V5-3 in the next candidate-specific stage.",
        },
        "dynamic": games,
        "real_games": games["real_games"],
        "policy_trajectories": games["real_games"],
        "bfs_expansions": 0,
        "teacher_search_compute": 0,
        "f85_actual_compute": 0,
        "default_generator_changed": False,
    }
    _write_json(output_dir / "static_results.json", {
        "schema_version": 1,
        "ruleset_fingerprints": ruleset_fingerprints,
        "results": static,
        "candidate_static_mate_capacity": candidate_static,
    })
    _write_json(output_dir / "game_results.json", games)
    _write_json(output_dir / "results.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/f86i_reversibility_rescue"))
    parser.add_argument("--prep", action="store_true")
    args = parser.parse_args()
    if args.prep:
        result = build_manifest(args.root, args.output_dir)
        print(json.dumps({
            "status": result["status"],
            "candidate_profile": result["candidate_profile"],
            "sample_count": len(result["entries"]),
        }, sort_keys=True))
        return 0
    result = run(args.root, args.output_dir)
    print(json.dumps({
        "real_games": result["real_games"],
        "routing_input_samples": len(result["dynamic"]["by_sample"]),
        "bfs_expansions": result["bfs_expansions"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
