"""Movement atoms -> geometry model (the renderer's input)."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.movement import LeapAtom, RayAtom
from ..core.pieces import PieceType


KING_DIRS = frozenset(
    (df, dr) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)
)


@dataclass(frozen=True, slots=True)
class Branch:
    """One rendered branch: an owner-adjusted direction, kind and leap span."""

    vector: tuple[int, int]
    kind: str  # "ray" | "leap"
    span: int  # max(|df|, |dr|) for leaps; 0 for rays


@dataclass(frozen=True, slots=True)
class GeometryModel:
    """Renderable geometry for one piece type and owner.

    ``kind`` is derived purely from geometry (never from type ids):
    * ``king`` - all eight single-step leaps (rounded square ring)
    * ``pawn`` - exactly one forward single-step leap (directional wedge)
    * ``generic`` - anything else (branch rendering with arrowheads/round caps)
    * ``empty`` - no movement atoms (center marker only)
    """

    kind: str
    branches: tuple[Branch, ...]


def _rotate(v: tuple[int, int]) -> tuple[int, int]:
    return (-v[0], -v[1])


def _collect_relative(piece_type: PieceType) -> tuple[Branch, ...]:
    merged: dict[tuple[int, int], Branch] = {}
    for atom in piece_type.movement_atoms:
        if isinstance(atom, LeapAtom):
            v = atom.offset
            span = max(abs(v[0]), abs(v[1]))
            cur = merged.get(v)
            if cur is None or (cur.kind == "leap" and span > cur.span):
                merged[v] = Branch(v, "leap", span)
        elif isinstance(atom, RayAtom):
            v = atom.direction
            merged[v] = Branch(v, "ray", 0)
    return tuple(merged.values())


def _detect_kind(rel: tuple[Branch, ...]) -> str:
    if not rel:
        return "empty"
    vectors = {b.vector for b in rel}
    if vectors == KING_DIRS and all(b.kind == "leap" and b.span == 1 for b in rel):
        return "king"
    if len(rel) == 1:
        b = rel[0]
        if b.kind == "leap" and b.span == 1 and b.vector == (0, 1):
            return "pawn"
    return "generic"


def build_geometry(piece_type: PieceType, owner: int | None) -> GeometryModel:
    """Build the geometry model for ``piece_type``.

    The category is detected on the owner-relative atoms; branch vectors are
    then rotated 180 degrees for ``owner=1`` so the icon matches the piece's
    on-board forward direction.  ``owner=None`` keeps the relative frame.
    """
    rel = _collect_relative(piece_type)
    kind = _detect_kind(rel)
    if owner == 1:
        branches = tuple(Branch(_rotate(b.vector), b.kind, b.span) for b in rel)
    else:
        branches = rel
    return GeometryModel(kind=kind, branches=branches)
