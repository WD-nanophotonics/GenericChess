"""Presentation adapters: movement summaries and read-only movement preview."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.coordinates import Square, square_to_index
from ..core.movement import LeapAtom, RayAtom
from ..core.pieces import PieceType
from ..core.position import Position

if TYPE_CHECKING:
    from ..rules.compiled import CompiledRuleSet


def owner_label(owner: int | None) -> str:
    """Human-facing owner label (visual convention: 0 = White/先手, 1 = Black/后手)."""
    if owner == 0:
        return "White / Player 0 (先手)"
    if owner == 1:
        return "Black / Player 1 (後手)"
    return "—"


def _direction_word(df: int, dr: int) -> str:
    parts = []
    if dr > 0:
        parts.append("forward")
    elif dr < 0:
        parts.append("backward")
    if df > 0:
        parts.append("right")
    elif df < 0:
        parts.append("left")
    return "-".join(parts) if parts else "sideways"


def describe_atom(atom) -> str:
    if isinstance(atom, RayAtom):
        df, dr = atom.direction
        dist = "unlimited" if atom.max_steps is None else f"max {atom.max_steps} squares"
        return f"{_direction_word(df, dr)} ray, {dist}, blocked by pieces"
    if isinstance(atom, LeapAtom):
        df, dr = atom.offset
        span = max(abs(df), abs(dr))
        return f"{_direction_word(df, dr)} leap, exactly {span} square{'s' if span != 1 else ''}"
    return f"unknown atom {atom!r}"


def movement_summary(piece_type: PieceType) -> tuple[str, ...]:
    """Human-readable one-line-per-atom movement description."""
    return tuple(describe_atom(a) for a in piece_type.movement_atoms)


def reachable_squares(position: Position, square: Square, compiled: "CompiledRuleSet") -> tuple[Square, ...]:
    """Read-only candidate squares for the piece on ``square``.

    Used only for *movement preview* of non-actionable pieces; it is not legal
    move generation and never considers side to move or self-check.
    """
    n = compiled.board_size
    idx = square_to_index(square, n)
    piece = position.board[idx]
    if piece is None:
        return ()
    owner = piece.owner
    tid = piece.current_type_id
    atoms = compiled.types_by_id[tid].movement_atoms
    leap_row = compiled.leap_targets[tid][owner][idx]
    ray_row = compiled.ray_paths[tid][owner][idx]
    candidates: list[Square] = []
    seen: set[Square] = set()

    def add(target: Square) -> None:
        if target not in seen:
            seen.add(target)
            candidates.append(target)

    for a_idx, atom in enumerate(atoms):
        if isinstance(atom, LeapAtom):
            for target in leap_row[a_idx]:
                occupant = position.board[square_to_index(target, n)]
                if occupant is None or occupant.owner != owner:
                    add(target)
        else:
            for target in ray_row[a_idx]:
                occupant = position.board[square_to_index(target, n)]
                if occupant is None:
                    add(target)
                    continue
                if occupant.owner != owner:
                    add(target)
                    break
                break  # friendly blocker: not reachable, stop
    return tuple(candidates)
