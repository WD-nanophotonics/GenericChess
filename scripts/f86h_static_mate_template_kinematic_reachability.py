"""F86H static mate-template optimistic kinematic reachability probe."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import permutations
from pathlib import Path
from typing import Any

from generic_chess.core.attacks import is_in_check
from generic_chess.core.coordinates import index_to_square
from generic_chess.core.movegen import has_legal_action
from generic_chess.core.position import Position
from generic_chess.rules.compiler import compile_ruleset
try:
    from scripts.f86f_ordinary_mate_capacity_census import (
        CELLS,
        SAMPLES,
        _anchor_type_id,
        _attack_masks,
        _build_position,
        _iter_placements,
        _load_rulesets,
        _ordinary_multiset,
        _zone_mask,
    )
except ModuleNotFoundError:
    from f86f_ordinary_mate_capacity_census import (
        CELLS,
        SAMPLES,
        _anchor_type_id,
        _attack_masks,
        _build_position,
        _iter_placements,
        _load_rulesets,
        _ordinary_multiset,
        _zone_mask,
    )


CAP_PER_CELL = 2048
TOTAL_CAP = 8192
PLY_HORIZONS = (8, 16, 32)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _square_payload(index: int, board_size: int) -> list[int]:
    return [index % board_size, index // board_size]


def _sorted_targets(compiled, type_id: str, owner: int, source_index: int) -> tuple[int, ...]:
    return tuple(
        sorted(
            target.rank * compiled.board_size + target.file
            for target in compiled.empty_mobility[type_id][owner][source_index]
        )
    )


def _all_pairs_shortest_paths(compiled, type_id: str, owner: int) -> tuple[tuple[int | None, ...], ...]:
    size = compiled.board_size * compiled.board_size
    adjacency = tuple(_sorted_targets(compiled, type_id, owner, source) for source in range(size))
    distances: list[tuple[int | None, ...]] = []
    for source in range(size):
        row: list[int | None] = [None] * size
        row[source] = 0
        queue = [source]
        for current in queue:
            for target in adjacency[current]:
                if row[target] is None:
                    row[target] = row[current] + 1
                    queue.append(target)
        distances.append(tuple(row))
    return tuple(distances)


def _shortest_path(
    compiled,
    type_id: str,
    owner: int,
    source: int,
    target: int,
    distances: tuple[tuple[int | None, ...], ...],
) -> list[int] | None:
    if distances[source][target] is None:
        return None
    path = [source]
    current = source
    while current != target:
        options = [
            candidate
            for candidate in _sorted_targets(compiled, type_id, owner, current)
            if distances[candidate][target] is not None
            and distances[candidate][target] == distances[current][target] - 1
        ]
        if not options:
            raise RuntimeError("shortest-path reconstruction lost a graph edge")
        current = options[0]
        path.append(current)
    return path


def _anchor_index(position: Position, owner: int, compiled) -> int:
    anchor_type = _anchor_type_id(compiled)
    return next(
        index
        for index, piece in enumerate(position.board)
        if piece is not None
        and piece.owner == owner
        and piece.current_type_id == anchor_type
    )


def _opening_pieces(compiled) -> tuple[tuple[str, int], ...]:
    anchor_type = _anchor_type_id(compiled)
    return tuple(
        (piece.current_type_id, index)
        for index, piece in enumerate(compiled.initial_position.board)
        if piece is not None
        and piece.owner == 0
        and piece.current_type_id != anchor_type
    )


def _type_assignment(
    compiled,
    opening_pieces: tuple[tuple[str, int], ...],
    template_ordinary: tuple[tuple[str, int], ...],
    distances_by_type: dict[tuple[str, int], tuple[tuple[int | None, ...], ...]],
) -> dict[str, Any]:
    by_type_source: dict[str, list[int]] = {}
    by_type_target: dict[str, list[int]] = {}
    for type_id, source in opening_pieces:
        by_type_source.setdefault(type_id, []).append(source)
    for type_id, target in template_ordinary:
        by_type_target.setdefault(type_id, []).append(target)

    assignment_rows: list[dict[str, Any]] = []
    total = 0
    for type_id in sorted(by_type_source):
        sources = tuple(sorted(by_type_source[type_id]))
        targets = tuple(sorted(by_type_target.get(type_id, ())))
        if len(sources) != len(targets):
            return {
                "reachable": False,
                "unreachable_details": [{
                    "reason": "type_count_mismatch",
                    "type_id": type_id,
                    "source_count": len(sources),
                    "target_count": len(targets),
                }],
            }
        distances = distances_by_type[(type_id, 0)]
        candidates = []
        for ordered_targets in permutations(targets):
            legs = [distances[source][target] for source, target in zip(sources, ordered_targets)]
            if any(distance is None for distance in legs):
                continue
            candidates.append((sum(legs), tuple(ordered_targets), tuple(legs)))
        if not candidates:
            return {
                "reachable": False,
                "unreachable_details": [{
                    "reason": "ordinary_movement_graph_unreachable",
                    "type_id": type_id,
                    "target_squares": [_square_payload(target, compiled.board_size) for target in targets],
                }],
            }
        _, ordered_targets, legs = min(candidates, key=lambda item: (item[0], item[1]))
        total += sum(legs)
        assignment_rows.extend(
            {
                "type_id": type_id,
                "source_square": _square_payload(source, compiled.board_size),
                "target_square": _square_payload(target, compiled.board_size),
                "distance": distance,
                "path": [
                    _square_payload(square, compiled.board_size)
                    for square in _shortest_path(compiled, type_id, 0, source, target, distances)
                ],
            }
            for source, target, distance in zip(sources, ordered_targets, legs)
        )
    return {
        "reachable": True,
        "minimum_ordinary_move_count": total,
        "assignment": assignment_rows,
        "unreachable_details": [],
    }


def _mirror_symmetry(compiled) -> dict[str, Any]:
    n = compiled.board_size
    size = n * n

    def rotate(index: int) -> int:
        square = index_to_square(index, n)
        return (n - 1 - square.rank) * n + (n - 1 - square.file)

    board_ok = True
    for index, piece in enumerate(compiled.initial_position.board):
        mirrored_index = rotate(index)
        mirrored = compiled.initial_position.board[mirrored_index]
        if piece is None:
            board_ok &= mirrored is None
        else:
            board_ok &= mirrored is not None
            board_ok &= (
                mirrored.owner == 1 - piece.owner
                and mirrored.base_type_id == piece.base_type_id
                and mirrored.current_type_id == piece.current_type_id
                and mirrored.promoted == piece.promoted
            )
    mobility_ok = True
    checked = 0
    for piece_type in compiled.piece_types:
        for owner in (0, 1):
            for source in range(size):
                checked += 1
                left = {
                    rotate(target.rank * n + target.file)
                    for target in compiled.empty_mobility[piece_type.type_id][owner][source]
                }
                right = {
                    target.rank * n + target.file
                    for target in compiled.empty_mobility[piece_type.type_id][1 - owner][rotate(source)]
                }
                mobility_ok &= left == right
    return {
        "board_owner_swap_180_rotation": board_ok,
        "empty_mobility_owner_swap_180_rotation": mobility_ok,
        "mobility_pairs_checked": checked,
        "holds": board_ok and mobility_ok,
    }


def _enumerate_validated_templates(
    sample_id: str,
    cell: str,
    compiled,
    authority_profile: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    n = compiled.board_size
    type_ids = _ordinary_multiset(compiled)
    templates: dict[tuple[int, tuple[tuple[str, int], ...]], set[int]] = {}
    candidate_count = 0
    checked_count = 0
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
                if candidate_count >= CAP_PER_CELL:
                    truncated = True
                    break
                candidate_count += 1
                checked_count += 1
                position = _build_position(compiled, defender_anchor, attacker_anchor, placement)
                if is_in_check(position, 0, compiled):
                    continue
                if not is_in_check(position, 1, compiled):
                    continue
                if has_legal_action(position, compiled):
                    continue
                key = (defender_anchor, tuple(sorted(placement)))
                templates.setdefault(key, set()).add(attacker_anchor)
            if truncated:
                break
        if truncated:
            break

    expected_count = sum(
        int(value)
        for value in authority_profile[
            "full_material_validated_mate_position_count_by_attacker_count"
        ].values()
    )
    actual_count = sum(len(targets) for targets in templates.values())
    if truncated or checked_count != authority_profile["checked_position_count"]:
        raise RuntimeError(
            f"{sample_id}:{cell} F86F census boundary changed: "
            f"checked={checked_count} expected={authority_profile['checked_position_count']} "
            f"truncated={truncated}"
        )
    if actual_count != expected_count:
        raise RuntimeError(
            f"{sample_id}:{cell} validated mate count changed: "
            f"actual={actual_count} expected={expected_count}"
        )

    rows = []
    for ordinal, (key, targets) in enumerate(sorted(templates.items()), start=1):
        defender_anchor, placement = key
        rows.append({
            "template_id": f"T{ordinal:04d}",
            "sample_id": sample_id,
            "cell": cell,
            "defender_anchor": _square_payload(defender_anchor, n),
            "ordinary": [
                {"type_id": type_id, "square": _square_payload(square, n)}
                for type_id, square in placement
            ],
            "allowed_attacker_anchor_squares": [
                _square_payload(square, n) for square in sorted(targets)
            ],
        })
    return {
        "sample_id": sample_id,
        "cell": cell,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "validated_position_count": actual_count,
        "validated_template_count": len(rows),
        "candidate_position_count": candidate_count,
        "checked_position_count": checked_count,
        "authority_validated_count": expected_count,
        "truncation": truncated,
        "templates": rows,
    }, rows


def _analyze_cell(
    sample_id: str,
    cell: str,
    compiled,
    census_cell: dict[str, Any],
    template_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    n = compiled.board_size
    opening_pieces = _opening_pieces(compiled)
    opening_anchor = {
        owner: _anchor_index(compiled.initial_position, owner, compiled)
        for owner in (0, 1)
    }
    type_ids = sorted({type_id for type_id, _ in opening_pieces})
    distances_by_type = {
        (type_id, owner): _all_pairs_shortest_paths(compiled, type_id, owner)
        for type_id in type_ids
        for owner in (0, 1)
    }
    anchor_type = _anchor_type_id(compiled)
    distances_by_type.update({
        (anchor_type, owner): _all_pairs_shortest_paths(compiled, anchor_type, owner)
        for owner in (0, 1)
    })
    symmetry = _mirror_symmetry(compiled)
    template_results = []
    for template in template_rows:
        ordinary = tuple(
            (item["type_id"], item["square"][1] * n + item["square"][0])
            for item in template["ordinary"]
        )
        assignment = _type_assignment(compiled, opening_pieces, ordinary, distances_by_type)
        target_rows = []
        for target_payload in template["allowed_attacker_anchor_squares"]:
            target = target_payload[1] * n + target_payload[0]
            attacker_distance = distances_by_type[(anchor_type, 0)][opening_anchor[0]][target]
            defender_distance = distances_by_type[(anchor_type, 1)][opening_anchor[1]][
                template["defender_anchor"][1] * n + template["defender_anchor"][0]
            ]
            unreachable = list(assignment["unreachable_details"])
            if attacker_distance is None:
                unreachable.append({
                    "reason": "attacker_anchor_movement_graph_unreachable",
                    "target_square": target_payload,
                })
            if defender_distance is None:
                unreachable.append({
                    "reason": "defender_anchor_movement_graph_unreachable",
                    "target_square": template["defender_anchor"],
                })
            both_anchors = attacker_distance is not None and defender_distance is not None
            joint = assignment["reachable"] and both_anchors
            target_result = {
                "attacker_anchor_target": target_payload,
                "ordinary_assignment_reachable": assignment["reachable"],
                "both_anchors_reachable": both_anchors,
                "joint_kinematically_reachable": joint,
                "attacker_anchor_distance": attacker_distance,
                "defender_anchor_distance": defender_distance,
                "unreachable_details": unreachable,
            }
            if joint:
                ordinary_moves = assignment["minimum_ordinary_move_count"]
                a = ordinary_moves + attacker_distance
                d = defender_distance
                target_result["minimum_ordinary_move_count"] = ordinary_moves
                target_result["optimistic_attacker_action_count"] = a
                target_result["optimistic_defender_action_count"] = d
                target_result["optimistic_ply_lower_bound"] = max(2 * a - 1, 2 * d)
            target_rows.append(target_result)

        joint_targets = [
            row for row in target_rows if row["joint_kinematically_reachable"]
        ]
        best_target = min(
            joint_targets,
            key=lambda row: (
                row["optimistic_ply_lower_bound"],
                row["attacker_anchor_target"][1],
                row["attacker_anchor_target"][0],
            ),
            default=None,
        )
        template_results.append({
            "template_id": template["template_id"],
            "defender_anchor": template["defender_anchor"],
            "ordinary": template["ordinary"],
            "allowed_attacker_anchor_squares": template["allowed_attacker_anchor_squares"],
            "ordinary_assignment_reachable": assignment["reachable"],
            "ordinary_assignment": assignment.get("assignment", []),
            "ordinary_assignment_move_count": assignment.get("minimum_ordinary_move_count"),
            "target_results": target_rows,
            "best_joint_target": best_target,
        })

    total_templates = len(template_results)
    ordinary_reachable = sum(row["ordinary_assignment_reachable"] for row in template_results)
    both_anchor_reachable = sum(
        any(target["both_anchors_reachable"] for target in row["target_results"])
        for row in template_results
    )
    joint_reachable = sum(bool(row["best_joint_target"]) for row in template_results)
    lower_bounds = [
        row["best_joint_target"]["optimistic_ply_lower_bound"]
        for row in template_results
        if row["best_joint_target"]
    ]
    target_rows_all = [
        target
        for row in template_results
        for target in row["target_results"]
    ]
    unreachable_details = [
        {
            "template_id": row["template_id"],
            "attacker_anchor_target": target["attacker_anchor_target"],
            "details": target["unreachable_details"],
        }
        for row in template_results
        for target in row["target_results"]
        if target["unreachable_details"]
    ]
    return {
        "sample_id": sample_id,
        "cell": cell,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "validated_template_count": total_templates,
        "validated_position_count": census_cell["validated_position_count"],
        "ordinary_assignment_reachable_count": ordinary_reachable,
        "ordinary_assignment_reachable_fraction": ordinary_reachable / total_templates if total_templates else None,
        "both_anchors_reachable_count": both_anchor_reachable,
        "both_anchors_reachable_fraction": both_anchor_reachable / total_templates if total_templates else None,
        "joint_kinematically_reachable_count": joint_reachable,
        "joint_kinematically_reachable_fraction": joint_reachable / total_templates if total_templates else None,
        "minimum_optimistic_ply_lower_bound": min(lower_bounds) if lower_bounds else None,
        "minimum_ordinary_move_count": min(
            (row["ordinary_assignment_move_count"] for row in template_results
             if row["ordinary_assignment_move_count"] is not None),
            default=None,
        ),
        "minimum_attacker_anchor_movement": min(
            (row["attacker_anchor_distance"] for row in target_rows_all
             if row["attacker_anchor_distance"] is not None),
            default=None,
        ),
        "minimum_defender_anchor_movement": min(
            (row["defender_anchor_distance"] for row in target_rows_all
             if row["defender_anchor_distance"] is not None),
            default=None,
        ),
        "templates_with_lower_bound_leq_8": sum(bound <= 8 for bound in lower_bounds),
        "templates_with_lower_bound_leq_16": sum(bound <= 16 for bound in lower_bounds),
        "templates_with_lower_bound_leq_32": sum(bound <= 32 for bound in lower_bounds),
        "graph_unreachable_template_count": total_templates - joint_reachable,
        "graph_unreachable_reason_counts": dict(sorted(Counter(
            detail["reason"]
            for row in unreachable_details
            for detail in row["details"]
        ).items())),
        "graph_unreachable_details": unreachable_details,
        "symmetry": symmetry,
        "canonical_shortest_path_witnesses": [
            {
                "template_id": row["template_id"],
                "target": row["best_joint_target"]["attacker_anchor_target"],
                "ordinary_assignment": row["ordinary_assignment"],
            }
            for row in template_results
            if row["best_joint_target"]
        ],
        "template_results": template_results,
    }


def run(output_dir: Path, root: Path) -> dict[str, Any]:
    rulesets = _load_rulesets(root)
    authority = _load_json(root, "artifacts/f86f_mate_capacity/census.json")
    authority_by_key = {(row["sample_id"], row["cell"]): row for row in authority["profiles"]}
    template_cells = []
    template_rows_by_key = {}
    for sample_id in SAMPLES:
        for cell in CELLS:
            compiled = compile_ruleset(rulesets[(sample_id, cell)])
            summary, rows = _enumerate_validated_templates(
                sample_id, cell, compiled, authority_by_key[(sample_id, cell)]
            )
            template_cells.append(summary)
            template_rows_by_key[(sample_id, cell)] = rows

    results = []
    for sample_id in SAMPLES:
        for cell in CELLS:
            compiled = compile_ruleset(rulesets[(sample_id, cell)])
            results.append(_analyze_cell(
                sample_id,
                cell,
                compiled,
                next(row for row in template_cells if row["sample_id"] == sample_id and row["cell"] == cell),
                template_rows_by_key[(sample_id, cell)],
            ))

    routing = []
    for result in results:
        if result["validated_template_count"] == 0:
            routing.append("NO_VALIDATED_STATIC_MATE_TEMPLATE")
        elif result["joint_kinematically_reachable_count"] == 0:
            routing.append("STATIC_MATE_TEMPLATES_KINEMATICALLY_UNREACHABLE_FROM_OPENING")
        elif result["minimum_optimistic_ply_lower_bound"] > 32:
            routing.append("KINEMATIC_MATE_TEMPLATE_OUTSIDE_32PLY_HORIZON")
        else:
            routing.append("KINEMATIC_MATE_TEMPLATE_REACHABLE_WITHIN_32PLY_LOWER_BOUND")

    payload = {
        "schema_version": 1,
        "sample_ids": list(SAMPLES),
        "cell_names": list(CELLS),
        "ruleset_fingerprints": {
            row["sample_id"]: {row["cell"]: row["ruleset_fingerprint"]}
            for row in template_cells
        },
        "static_census_authority": "artifacts/f86f_mate_capacity/census.json",
        "static_candidate_checks_per_cell_cap": CAP_PER_CELL,
        "static_candidate_checks_total_cap": TOTAL_CAP,
        "total_static_candidate_checks": sum(row["checked_position_count"] for row in template_cells),
        "real_games": 0,
        "policy_trajectories": 0,
        "bfs_expansions": 0,
        "teacher_search_compute": 0,
        "default_generator_changed": False,
        "f85_actual_compute": 0,
        "routing": routing,
        "results": results,
    }
    templates_payload = {
        "schema_version": 1,
        "sample_ids": list(SAMPLES),
        "cell_names": list(CELLS),
        "ruleset_fingerprints": payload["ruleset_fingerprints"],
        "movement_graph": {
            "definition": "directed edges from compiled empty_mobility[type_id][owner][source] to target",
            "occupancy_ignored": True,
            "check_legality_ignored": True,
            "turn_interaction_ignored": True,
            "captures_ignored": True,
        },
        "cells": template_cells,
    }
    _write_json(output_dir / "templates.json", templates_payload)
    _write_json(output_dir / "results.json", payload)
    return {"templates": templates_payload, "results": payload}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/f86h_kinematic_mate_reachability"))
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = run(args.output_dir, args.root)
    print(json.dumps({
        "total_static_candidate_checks": result["results"]["total_static_candidate_checks"],
        "routing": result["results"]["routing"],
        "validated_template_counts": [
            row["validated_template_count"] for row in result["results"]["results"]
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
