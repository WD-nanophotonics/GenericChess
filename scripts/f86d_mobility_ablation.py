"""F86D static mobility diagnostics and bounded counterfactual ablation."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from generic_chess.benchmark.game_quality import measure_game_quality
from generic_chess.benchmark.minimal_generator import MinimalGeneratedGame
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import RuleSet, ruleset_from_dict, ruleset_to_dict


PROFILES = ("A_FULL_ANCHOR", "B_BIDIRECTIONAL_ORDINARY", "C_FULL_ANCHOR_PLUS_BIDIRECTIONAL")
GAME_SAMPLE_IDS = ("V4-3", "V5-3")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _reverse_atoms(atoms):
    out = list(atoms)
    for atom in atoms:
        if isinstance(atom, LeapAtom):
            reverse = LeapAtom((-atom.offset[0], -atom.offset[1]))
        else:
            reverse = RayAtom((-atom.direction[0], -atom.direction[1]), atom.max_steps)
        if reverse not in out:
            out.append(reverse)
    return tuple(out)


def _full_anchor_atoms():
    return tuple(LeapAtom(offset) for offset in (
        (1, 0), (-1, 0), (0, 1), (0, -1),
        (1, 1), (1, -1), (-1, 1), (-1, -1),
    ))


def _counterfactual(base: RuleSet, profile: str) -> RuleSet:
    full_anchor = profile in ("A_FULL_ANCHOR", "C_FULL_ANCHOR_PLUS_BIDIRECTIONAL")
    bidirectional_ordinary = profile in ("B_BIDIRECTIONAL_ORDINARY", "C_FULL_ANCHOR_PLUS_BIDIRECTIONAL")
    types = []
    for piece_type in base.piece_types:
        atoms = piece_type.movement_atoms
        if piece_type.is_anchor and full_anchor:
            atoms = _full_anchor_atoms()
        elif not piece_type.is_anchor and bidirectional_ordinary:
            atoms = _reverse_atoms(atoms)
        types.append(replace(piece_type, movement_atoms=atoms))
    return replace(
        base,
        piece_types=tuple(types),
        metadata={**base.metadata, "f86d_profile": profile},
    )


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
    return {
        "owner": owner,
        "average_out_degree": total_edges / (n * n),
        "sink_square_fraction": len(sinks) / (n * n),
        "largest_scc_fraction": max(scc_sizes) / (n * n) if scc_sizes else 0.0,
        "nontrivial_scc_square_fraction": sum(size for size in scc_sizes if size > 1) / (n * n),
        "direct_reversible_edge_fraction": reverse_edges / total_edges if total_edges else 0.0,
        "far_edge_sink_fraction": sum(index // n in (0, n - 1) for index in sinks) / len(sinks) if sinks else 0.0,
    }


def static_diagnostics(compiled) -> dict[str, Any]:
    rows = []
    for piece_type in compiled.piece_types:
        owner_rows = [_type_diagnostic(compiled, piece_type.type_id, owner) for owner in (0, 1)]
        atoms = piece_type.movement_atoms
        backward = [
            atom.offset[1] < 0 if isinstance(atom, LeapAtom) else atom.direction[1] < 0
            for atom in atoms
        ]
        values = {
            key: sum(row[key] for row in owner_rows) / len(owner_rows)
            for key in owner_rows[0]
            if key != "owner"
        }
        values.update({
            "type_id": piece_type.type_id,
            "is_anchor": piece_type.is_anchor,
            "has_backward_atom": any(backward),
            "forward_only_atom_fraction": sum(not item for item in backward) / len(backward),
            "owner_metrics": owner_rows,
        })
        rows.append(values)
    non_anchor = [row for row in rows if not row["is_anchor"]]
    all_rows = rows
    return {
        "board_size": compiled.board_size,
        "type_metrics": rows,
        "anchor": next(row for row in rows if row["is_anchor"]),
        "ordinary_mean_sink_fraction": sum(row["sink_square_fraction"] for row in non_anchor) / len(non_anchor),
        "ordinary_max_sink_fraction": max(row["sink_square_fraction"] for row in non_anchor),
        "ordinary_mean_reversibility": sum(row["direct_reversible_edge_fraction"] for row in non_anchor) / len(non_anchor),
        "ordinary_nontrivial_scc_fraction": max(row["nontrivial_scc_square_fraction"] for row in non_anchor),
        "has_backward_atom": any(row["has_backward_atom"] for row in all_rows),
        "forward_only_atom_fraction": sum(row["forward_only_atom_fraction"] for row in all_rows) / len(all_rows),
        "monotone_mobility_dag": all(
            not row["has_backward_atom"] and row["nontrivial_scc_square_fraction"] == 0.0
            for row in all_rows
        ),
    }


def _load_f86c_rulesets(root: Path):
    payload = json.loads((root / "artifacts/f86c_generator_viability/rulesets.json").read_text(encoding="utf-8"))
    return {
        row["sample_id"]: (row["seed"], row["ordinary_count"], ruleset_from_dict(row["ruleset"]))
        for row in payload["sample"]
    }


def _load_f86c_quality(root: Path):
    payload = json.loads((root / "artifacts/f86c_generator_viability/results.json").read_text(encoding="utf-8"))
    return {row["sample_id"]: row for row in payload["quality"]}


def run(output_dir: Path, root: Path) -> dict[str, object]:
    frozen = _load_f86c_rulesets(root)
    legacy_quality = _load_f86c_quality(root)
    static_rows = []
    counterfactual_rows = []
    games = []
    for sample_id, (seed, ordinary_count, base) in frozen.items():
        base_compiled = compile_ruleset(base)
        static_rows.append({"sample_id": sample_id, "profile": "LEGACY", "ruleset_fingerprint": base_compiled.ruleset_fingerprint, "diagnostics": static_diagnostics(base_compiled)})
        for profile in PROFILES:
            ruleset = _counterfactual(base, profile)
            compiled = compile_ruleset(ruleset)
            static_rows.append({"sample_id": sample_id, "profile": profile, "ruleset_fingerprint": compiled.ruleset_fingerprint, "diagnostics": static_diagnostics(compiled)})
            counterfactual_rows.append({
                "sample_id": sample_id,
                "profile": profile,
                "seed": seed,
                "ordinary_count": ordinary_count,
                "ruleset_fingerprint": compiled.ruleset_fingerprint,
                "ruleset": ruleset_to_dict(ruleset),
            })
    _write_json(output_dir / "static_diagnostics.json", {"schema_version": 1, "rows": static_rows})
    _write_json(output_dir / "counterfactual_rulesets.json", {"schema_version": 1, "rows": counterfactual_rows})

    profiles = [
        {"sample_id": sample_id, "profile": "LEGACY", **legacy_quality[sample_id]}
        for sample_id in GAME_SAMPLE_IDS
    ]
    for sample_id in GAME_SAMPLE_IDS:
        seed, ordinary_count, base = frozen[sample_id]
        for profile in PROFILES:
            ruleset = _counterfactual(base, profile)
            game = MinimalGeneratedGame(seed, ruleset.board_size, ordinary_count, ruleset, compile_ruleset(ruleset))
            raw_games: list[dict[str, object]] = []
            quality = measure_game_quality(game, trajectory_count=1, max_ply=32, seed=seed + 3000, raw_games=raw_games)
            profiles.append({"sample_id": sample_id, "profile": profile, **quality.to_dict()})
            games.extend({"sample_id": sample_id, "profile": profile, **row} for row in raw_games)
    by_profile = {}
    for profile in ("LEGACY",) + PROFILES:
        rows = [row for row in profiles if row["profile"] == profile]
        stalemates = sum(row["terminal_distribution"].get("stalemate", 0) for row in rows)
        total = sum(row["played_game_count"] for row in rows)
        by_profile[profile] = {
            "played_game_count": total,
            "stalemate_fraction": stalemates / total if total else 0.0,
            "decisive_fraction": sum(
                row["terminal_distribution"].get("checkmate", 0) for row in rows
            ) / total if total else 0.0,
            "profiles": rows,
        }
    legacy_stale = by_profile["LEGACY"]["stalemate_fraction"]
    improvements = {name: legacy_stale - by_profile[name]["stalemate_fraction"] for name in PROFILES}
    best = max(improvements, key=improvements.get)
    if improvements[best] >= 0.5 and best == "A_FULL_ANCHOR":
        routing = "ANCHOR_MOBILITY_PRIMARY_CAUSE"
    elif improvements[best] >= 0.5 and best == "B_BIDIRECTIONAL_ORDINARY":
        routing = "ORDINARY_MONOTONE_MOBILITY_PRIMARY_CAUSE"
    elif improvements[best] >= 0.5:
        routing = "JOINT_MONOTONE_MOBILITY_CAUSE"
    else:
        routing = "MOBILITY_HYPOTHESIS_INSUFFICIENT"
    results = {
        "schema_version": 1,
        "sample_ids": list(GAME_SAMPLE_IDS),
        "profile_names": ["LEGACY", *PROFILES],
        "profiles": profiles,
        "quality_games": games,
        "played_game_count": len(games),
        "tactical_probe_position_count": len(GAME_SAMPLE_IDS) * len(PROFILES),
        "tactical_probe_nodes": sum(row["tactical_probe_nodes"] for row in profiles if row["profile"] != "LEGACY"),
        "by_profile": by_profile,
        "stalemate_improvements_vs_legacy": improvements,
        "routing": routing,
        "default_generator_changed": False,
        "f85_actual_compute": 0,
    }
    _write_json(output_dir / "results.json", results)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/f86d_mobility_ablation"))
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = run(args.output_dir, args.root)
    print(json.dumps({key: result[key] for key in (
        "played_game_count", "tactical_probe_position_count", "tactical_probe_nodes", "routing",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
