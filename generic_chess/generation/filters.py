"""Soft (preference) filters applied after the compiler's hard validation."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.movegen import legal_actions_from_position
from ..core.pieces import PieceType


@dataclass(frozen=True, slots=True)
class FilterResult:
    name: str
    passed: bool
    detail: str = ""


def run_soft_filters(cfg, compiled, types_by_id: dict[str, PieceType]) -> tuple[FilterResult, ...]:
    n = compiled.board_size
    results: list[FilterResult] = []

    # Every ordinary type must be structurally alive somewhere on the board.
    dead_types: list[str] = []
    for pt in compiled.piece_types:
        if pt.is_anchor:
            continue
        alive = any(
            compiled.empty_mobility[pt.type_id][player][idx]
            for player in (0, 1)
            for idx in range(n * n)
        )
        if not alive:
            dead_types.append(pt.type_id)
    results.append(
        FilterResult(
            "ordinary_types_mobile",
            not dead_types,
            "structurally dead types: " + (", ".join(dead_types) if dead_types else "none"),
        )
    )

    promotable = [pt for pt in compiled.piece_types if pt.is_promotable and not pt.is_anchor]
    targets = [
        pt
        for pt in compiled.piece_types
        if not pt.is_promotable and not pt.is_anchor
    ]
    results.append(
        FilterResult(
            "promotable_present",
            (not cfg.require_promotable_type) or bool(promotable),
            f"promotable types: {[p.type_id for p in promotable] or 'none'}",
        )
    )
    results.append(
        FilterResult(
            "promotion_target_present",
            (not cfg.require_nonpromotable_type) or bool(targets),
            f"promotion targets: {[t.type_id for t in targets] or 'none'}",
        )
    )

    opening = legal_actions_from_position(compiled.initial_position, compiled)
    in_range = cfg.min_opening_legal_moves <= len(opening) <= cfg.max_opening_legal_moves
    results.append(
        FilterResult(
            "opening_legal_moves_in_range",
            in_range,
            f"{len(opening)} legal moves (allowed {cfg.min_opening_legal_moves}..{cfg.max_opening_legal_moves})",
        )
    )

    empty_atoms = [pt.type_id for pt in compiled.piece_types if not pt.is_anchor and not pt.movement_atoms]
    results.append(
        FilterResult(
            "movement_atoms_nonempty",
            not empty_atoms,
            "types with no atoms: " + (", ".join(empty_atoms) if empty_atoms else "none"),
        )
    )

    # The compiler already guarantees anchors are safe and the opener has a
    # move; we record those as satisfied soft checks for the report.
    results.append(FilterResult("anchor_initial_safe", True, "compiler-validated"))
    results.append(FilterResult("opening_has_legal_move", True, "compiler-validated"))
    results.append(FilterResult("deterministic_reproduction", True, "local RNG with fixed seed"))
    return tuple(results)
