"""F86E corrected mobility diagnostics and Anchor/placement ablation."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from statistics import median
from typing import Any

from generic_chess.benchmark.game_quality import measure_game_quality
from generic_chess.benchmark.minimal_generator import MinimalGeneratedGame
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import RuleSet, ruleset_from_dict, ruleset_to_dict


SAMPLES = ("V4-3", "V5-3")
NEW_CELLS = ("ORTHO4_CURRENT", "ORTHO4_HOME", "FULL8_HOME")
ALL_CELLS = ("LEGACY_CURRENT", "FULL8_CURRENT", *NEW_CELLS)
ORTHO4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
FULL8 = (
    (1, 0), (-1, 0), (0, 1), (0, -1),
    (1, 1), (1, -1), (-1, 1), (-1, -1),
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _scc_sizes(edges: list[list[int]]) -> list[int]:
    index = 0
    stack: list[int] = []
    on_stack: set[int] = set()
    indices: dict[int, int] = {}
    low: dict[int, int] = {}
    sizes: list[int] = []

    def visit(node: int) -> None:
        nonlocal index
        indices[node] = index
        low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in edges[node]:
            if target not in indices:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], indices[target])
        if low[node] == indices[node]:
            size = 0
            while True:
                current = stack.pop()
                on_stack.remove(current)
                size += 1
                if current == node:
                    break
            sizes.append(size)

    for node in range(len(edges)):
        if node not in indices:
            visit(node)
    return sizes


def _type_diagnostic(compiled, type_id: str, owner: int) -> dict[str, Any]:
    n = compiled.board_size
    mobility = compiled.empty_mobility[type_id][owner]
    edges = [[target.rank * n + target.file for target in mobility[square]] for square in range(n * n)]
    out_degrees = [len(row) for row in edges]
    sinks = [index for index, degree in enumerate(out_degrees) if degree == 0]
    scc_sizes = _scc_sizes(edges)
    total_edges = sum(out_degrees)
    reverse_edges = sum(
        1
        for source, targets in enumerate(edges)
        for target in targets
        if source in edges[target]
    )
    far_rank = n - 1 if owner == 0 else 0
    return {
        "owner": owner,
        "average_out_degree": total_edges / (n * n),
        "sink_square_fraction": len(sinks) / (n * n),
        "largest_scc_fraction": max(scc_sizes) / (n * n) if scc_sizes else 0.0,
        "nontrivial_scc_square_fraction": sum(size for size in scc_sizes if size > 1) / (n * n),
        "direct_reversible_edge_fraction": reverse_edges / total_edges if total_edges else 0.0,
        "far_edge_sink_fraction": sum(index // n == far_rank for index in sinks) / len(sinks) if sinks else 0.0,
    }


def static_diagnostics(compiled) -> dict[str, Any]:
    """Return corrected atom-direction and owner-relative graph diagnostics."""
    rows = []
    for piece_type in compiled.piece_types:
        owner_rows = [_type_diagnostic(compiled, piece_type.type_id, owner) for owner in (0, 1)]
        atoms = piece_type.movement_atoms
        ranks = [atom.offset[1] if isinstance(atom, LeapAtom) else atom.direction[1] for atom in atoms]
        values = {
            key: sum(row[key] for row in owner_rows) / len(owner_rows)
            for key in owner_rows[0]
            if key != "owner"
        }
        values.update({
            "type_id": piece_type.type_id,
            "is_anchor": piece_type.is_anchor,
            "has_backward_atom": any(rank < 0 for rank in ranks),
            "non_backward_atom_fraction": sum(rank >= 0 for rank in ranks) / len(ranks),
            "strict_forward_atom_fraction": sum(rank > 0 for rank in ranks) / len(ranks),
            "horizontal_atom_fraction": sum(rank == 0 for rank in ranks) / len(ranks),
            "owner_metrics": owner_rows,
        })
        rows.append(values)
    non_anchor = [row for row in rows if not row["is_anchor"]]
    return {
        "board_size": compiled.board_size,
        "type_metrics": rows,
        "anchor": next(row for row in rows if row["is_anchor"]),
        "ordinary_mean_sink_fraction": sum(row["sink_square_fraction"] for row in non_anchor) / len(non_anchor),
        "ordinary_max_sink_fraction": max(row["sink_square_fraction"] for row in non_anchor),
        "ordinary_mean_reversibility": sum(row["direct_reversible_edge_fraction"] for row in non_anchor) / len(non_anchor),
        "ordinary_nontrivial_scc_fraction": max(row["nontrivial_scc_square_fraction"] for row in non_anchor),
        "has_backward_atom": any(row["has_backward_atom"] for row in rows),
        "non_backward_atom_fraction": sum(row["non_backward_atom_fraction"] for row in rows) / len(rows),
        "strict_forward_atom_fraction": sum(row["strict_forward_atom_fraction"] for row in rows) / len(rows),
        "horizontal_atom_fraction": sum(row["horizontal_atom_fraction"] for row in rows) / len(rows),
        "monotone_mobility_dag": all(
            not row["has_backward_atom"] and row["nontrivial_scc_square_fraction"] == 0.0
            for row in rows
        ),
    }


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _load_frozen(root: Path) -> dict[str, tuple[int, int, RuleSet]]:
    payload = _load_json(root, "artifacts/f86c_generator_viability/rulesets.json")
    return {
        row["sample_id"]: (row["seed"], row["ordinary_count"], ruleset_from_dict(row["ruleset"]))
        for row in payload["sample"]
        if row["sample_id"] in SAMPLES
    }


def _load_full8_current(root: Path) -> dict[str, RuleSet]:
    payload = _load_json(root, "artifacts/f86d_mobility_ablation/counterfactual_rulesets.json")
    return {
        row["sample_id"]: ruleset_from_dict(row["ruleset"])
        for row in payload["rows"]
        if row["sample_id"] in SAMPLES and row["profile"] == "A_FULL_ANCHOR"
    }


def _load_reference_quality(root: Path, sample_id: str, profile: str) -> dict[str, Any]:
    if profile == "LEGACY_CURRENT":
        payload = _load_json(root, "artifacts/f86c_generator_viability/results.json")
        row = next(item for item in payload["quality"] if item["sample_id"] == sample_id)
    else:
        payload = _load_json(root, "artifacts/f86d_mobility_ablation/results.json")
        row = next(item for item in payload["by_profile"]["A_FULL_ANCHOR"]["profiles"] if item["sample_id"] == sample_id)
    return {"sample_id": sample_id, "profile": profile, **row}


def _anchor_atoms(offsets: tuple[tuple[int, int], ...]) -> tuple[LeapAtom, ...]:
    return tuple(LeapAtom(offset) for offset in offsets)


def _replace_anchor(ruleset: RuleSet, offsets: tuple[tuple[int, int], ...], cell: str) -> RuleSet:
    piece_types = tuple(
        replace(piece_type, movement_atoms=_anchor_atoms(offsets)) if piece_type.is_anchor else piece_type
        for piece_type in ruleset.piece_types
    )
    return replace(ruleset, piece_types=piece_types, metadata={**ruleset.metadata, "f86e_cell": cell})


def _rotate(square: Square, n: int) -> Square:
    return Square(n - 1 - square.file, n - 1 - square.rank)


def _home_placement(ruleset: RuleSet, cell: str) -> RuleSet:
    n = ruleset.board_size
    owner_zero = [
        (file, rank, piece)
        for rank, row in enumerate(ruleset.initial_position)
        for file, piece in enumerate(row)
        if piece is not None and piece.owner == 0
    ]
    anchors = [(file, rank, piece) for file, rank, piece in owner_zero if any(
        item.is_anchor and item.type_id == piece.base_type_id for item in ruleset.piece_types
    )]
    ordinary = [item for item in owner_zero if item not in anchors]
    if len(anchors) != 1:
        raise ValueError(f"{cell}: expected one owner-0 Anchor")
    center_file = n // 2 - 1 if n % 2 == 0 else n // 2
    central_files = sorted(range(n), key=lambda file: (abs(file - (n - 1) / 2), file))[:len(ordinary)]
    ordinary.sort(key=lambda item: (item[2].base_type_id, item[1], item[0]))
    p0: list[Piece | None] = [None] * (n * n)
    anchor = anchors[0][2]
    p0[center_file] = Piece(0, anchor.base_type_id, anchor.current_type_id, anchor.promoted)
    for file, (_old_file, _old_rank, piece) in zip(central_files, ordinary):
        index = n + file
        if p0[index] is not None:
            raise ValueError(f"{cell}: home placement collision")
        p0[index] = Piece(0, piece.base_type_id, piece.current_type_id, piece.promoted)
    board = list(p0)
    for index, piece in enumerate(p0):
        if piece is None:
            continue
        square = Square(index % n, index // n)
        rotated = _rotate(square, n)
        target = rotated.rank * n + rotated.file
        board[target] = Piece(1, piece.base_type_id, piece.current_type_id, piece.promoted)
    rows = tuple(tuple(board[rank * n : (rank + 1) * n]) for rank in range(n))
    return replace(
        ruleset,
        initial_position=rows,
        metadata={**ruleset.metadata, "f86e_cell": cell, "f86e_placement": "HOME"},
    )


def _cell_rulesets(root: Path) -> dict[str, dict[str, RuleSet]]:
    frozen = _load_frozen(root)
    full8 = _load_full8_current(root)
    result: dict[str, dict[str, RuleSet]] = {}
    for sample_id in SAMPLES:
        legacy = frozen[sample_id][2]
        full8_current = full8[sample_id]
        ortho_current = _replace_anchor(legacy, ORTHO4, "ORTHO4_CURRENT")
        result[sample_id] = {
            "LEGACY_CURRENT": legacy,
            "FULL8_CURRENT": full8_current,
            "ORTHO4_CURRENT": ortho_current,
            "ORTHO4_HOME": _home_placement(ortho_current, "ORTHO4_HOME"),
            "FULL8_HOME": _home_placement(full8_current, "FULL8_HOME"),
        }
    return result


def _terminal_counts(games: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for game in games:
        counts[game["terminal_status"]] = counts.get(game["terminal_status"], 0) + 1
    return counts


def _summarize_cell(quality: list[dict[str, Any]], games: list[dict[str, Any]]) -> dict[str, Any]:
    terminal = _terminal_counts(games)
    total = len(games)
    branchings = [count for game in games for count in game["branching_sequence"]]
    lengths = [game["plies"] for game in games]
    return {
        "played_game_count": total,
        "decisive_fraction": terminal.get("checkmate", 0) / total if total else None,
        "checkmate_count": terminal.get("checkmate", 0),
        "stalemate_fraction": terminal.get("stalemate", 0) / total if total else None,
        "stalemate_count": terminal.get("stalemate", 0),
        "ongoing_at_32_fraction": terminal.get("ongoing", 0) / total if total else None,
        "ongoing_at_32_count": terminal.get("ongoing", 0),
        "repetition_fraction": terminal.get("repetition", 0) / total if total else None,
        "terminal_distribution": terminal,
        "median_game_length": float(median(lengths)) if lengths else None,
        "median_branching": float(median(branchings)) if branchings else None,
        "forced_move_fraction": sum(count == 1 for count in branchings) / len(branchings) if branchings else 0.0,
        "branching_collapse_fraction": sum(count <= 2 for count in branchings) / len(branchings) if branchings else 0.0,
        "opening_anchor_legal_counts": [row["opening_mobility_by_type"].get("K", 0) for row in quality],
        "quality_profiles": quality,
    }


def _reference_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    terminal: dict[str, int] = {}
    lengths = []
    branchings = []
    opening_anchor = []
    for row in rows:
        for status, count in row["terminal_distribution"].items():
            terminal[status] = terminal.get(status, 0) + count
        lengths.extend(row["trajectory_lengths"])
        branchings.extend(row["branching_counts"])
        opening_anchor.append(row["opening_mobility_by_type"].get("K", 0))
    total = sum(terminal.values())
    return {
        "played_game_count": total,
        "decisive_fraction": terminal.get("checkmate", 0) / total if total else None,
        "checkmate_count": terminal.get("checkmate", 0),
        "stalemate_fraction": terminal.get("stalemate", 0) / total if total else None,
        "stalemate_count": terminal.get("stalemate", 0),
        "ongoing_at_32_fraction": terminal.get("ongoing", 0) / total if total else None,
        "ongoing_at_32_count": terminal.get("ongoing", 0),
        "repetition_fraction": terminal.get("repetition", 0) / total if total else None,
        "terminal_distribution": terminal,
        "median_game_length": float(median(lengths)) if lengths else None,
        "median_branching": float(median(branchings)) if branchings else None,
        "forced_move_fraction": sum(count == 1 for count in branchings) / len(branchings) if branchings else 0.0,
        "branching_collapse_fraction": sum(count <= 2 for count in branchings) / len(branchings) if branchings else 0.0,
        "opening_anchor_legal_counts": opening_anchor,
        "quality_profiles": rows,
    }


def _route(by_cell: dict[str, dict[str, Any]], references: dict[str, dict[str, Any]]) -> list[str]:
    routes: list[str] = []
    ortho = by_cell["ORTHO4_CURRENT"]
    full8 = references["FULL8_CURRENT"]
    if (
        ortho["stalemate_fraction"] <= full8["stalemate_fraction"]
        and (
            ortho["decisive_fraction"] > full8["decisive_fraction"]
            or ortho["ongoing_at_32_fraction"] < full8["ongoing_at_32_fraction"]
        )
    ):
        routes.append("FULL8_ESCAPE_CAPACITY_TOO_HIGH")
    placement_effects = []
    for current, home in (("ORTHO4_CURRENT", "ORTHO4_HOME"), ("FULL8_CURRENT", "FULL8_HOME")):
        before = by_cell[current] if current in by_cell else references[current]
        after = by_cell[home]
        placement_effects.append((before, after))
        if (
            after["stalemate_fraction"] < before["stalemate_fraction"]
            or after["ongoing_at_32_fraction"] < before["ongoing_at_32_fraction"]
        ) and after["decisive_fraction"] > before["decisive_fraction"]:
            routes.append("PLACEMENT_MATERIALLY_AFFECTS_TERMINATION")
    if len(placement_effects) == 2:
        ortho_delta = tuple(placement_effects[0][1][key] - placement_effects[0][0][key] for key in ("stalemate_fraction", "ongoing_at_32_fraction", "decisive_fraction"))
        full8_delta = tuple(placement_effects[1][1][key] - placement_effects[1][0][key] for key in ("stalemate_fraction", "ongoing_at_32_fraction", "decisive_fraction"))
        if ortho_delta != full8_delta:
            routes.append("ANCHOR_PLACEMENT_INTERACTION_OBSERVED")
    reversible = [by_cell[name] for name in NEW_CELLS] + [references["FULL8_CURRENT"]]
    if all(row["decisive_fraction"] == 0.0 for row in reversible) and all(
        row["stalemate_fraction"] + row["ongoing_at_32_fraction"] >= 0.75 for row in reversible
    ):
        routes.append("MATE_CAPACITY_REMAINS_LIMITING")
    return routes or ["MOBILITY_PLACEMENT_EFFECT_INSUFFICIENT"]


def run(output_dir: Path, root: Path) -> dict[str, Any]:
    rulesets = _cell_rulesets(root)
    static_rows = []
    serialized_new = []
    compiled_cells: dict[str, dict[str, Any]] = {}
    for sample_id in SAMPLES:
        compiled_cells[sample_id] = {}
        for cell in ALL_CELLS:
            ruleset = rulesets[sample_id][cell]
            compiled = compile_ruleset(ruleset)
            compiled_cells[sample_id][cell] = compiled
            static_rows.append({
                "sample_id": sample_id,
                "cell": cell,
                "ruleset_fingerprint": compiled.ruleset_fingerprint,
                "diagnostics": static_diagnostics(compiled),
                "placement": "CURRENT" if cell.endswith("CURRENT") else "HOME",
                "valid": True,
            })
            if cell in NEW_CELLS:
                seed, ordinary_count, _base = _load_frozen(root)[sample_id]
                serialized_new.append({
                    "sample_id": sample_id,
                    "cell": cell,
                    "seed": seed,
                    "ordinary_count": ordinary_count,
                    "ruleset_fingerprint": compiled.ruleset_fingerprint,
                    "ruleset": ruleset_to_dict(ruleset),
                    "placement_valid": True,
                })
    _write_json(output_dir / "static_diagnostics.json", {"schema_version": 1, "rows": static_rows})
    _write_json(output_dir / "counterfactual_rulesets.json", {"schema_version": 1, "rows": serialized_new})

    # Only these three new cells run games. LEGACY_CURRENT and FULL8_CURRENT
    # are direct references to the already accepted F86C/F86D artifacts.
    games: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    invalid_cells: list[dict[str, Any]] = []
    frozen = _load_frozen(root)
    for sample_id in SAMPLES:
        seed, ordinary_count, _base = frozen[sample_id]
        for cell_index, cell in enumerate(NEW_CELLS):
            ruleset = rulesets[sample_id][cell]
            compiled = compiled_cells[sample_id][cell]
            game = MinimalGeneratedGame(seed, ruleset.board_size, ordinary_count, ruleset, compiled)
            raw_games: list[dict[str, Any]] = []
            quality = measure_game_quality(
                game,
                trajectory_count=1,
                max_ply=32,
                seed=seed + 9000 + cell_index * 100,
                raw_games=raw_games,
            )
            profiles.append({"sample_id": sample_id, "cell": cell, **quality.to_dict()})
            games.extend({"sample_id": sample_id, "cell": cell, **row} for row in raw_games)

    references = {}
    for profile in ("LEGACY_CURRENT", "FULL8_CURRENT"):
        references[profile] = _reference_summary([
            _load_reference_quality(root, sample_id, profile) for sample_id in SAMPLES
        ])
    by_cell = {
        cell: _summarize_cell(
            [row for row in profiles if row["cell"] == cell],
            [row for row in games if row["cell"] == cell],
        )
        for cell in NEW_CELLS
    }
    results = {
        "schema_version": 1,
        "sample_ids": list(SAMPLES),
        "cell_names": list(ALL_CELLS),
        "new_cell_names": list(NEW_CELLS),
        "reference_profiles": references,
        "profiles": profiles,
        "quality_games": games,
        "invalid_cells": invalid_cells,
        "played_game_count": len(games),
        "tactical_probe_position_count": len(profiles),
        "tactical_probe_nodes": sum(row["tactical_probe_nodes"] for row in profiles),
        "by_cell": by_cell,
        "routing": _route(by_cell, {**references, "ORTHO4_CURRENT": by_cell["ORTHO4_CURRENT"]}),
        "default_generator_changed": False,
        "no_seed_replacement": True,
        "f85_actual_compute": 0,
    }
    _write_json(output_dir / "results.json", results)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/f86e_anchor_placement_ablation"))
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = run(args.output_dir, args.root)
    print(json.dumps({key: result[key] for key in (
        "played_game_count", "tactical_probe_position_count", "tactical_probe_nodes", "routing",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
