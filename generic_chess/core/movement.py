"""Movement atoms: the two primitive move kinds used by every piece.

``LeapAtom`` checks only the destination square and ignores intermediate
squares.  ``RayAtom`` walks a path in order, stopping at the first occupied
square (or after ``max_steps``).  Ray directions must be primitive integer
vectors (``gcd(abs(df), abs(dr)) == 1``) to avoid ambiguity such as whether
``(2, 2)`` skips ``(1, 1)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd

from .coordinates import Offset, Player, Square, add_offset, is_forward, relative_to_absolute


@dataclass(frozen=True, slots=True)
class LeapAtom:
    """A jump of exactly ``offset`` (relative, never ``(0, 0)``)."""

    offset: Offset


@dataclass(frozen=True, slots=True)
class RayAtom:
    """A sliding move along primitive direction ``direction``.

    ``max_steps`` bounds the number of destination squares; ``None`` means
    unbounded (bounded only by the board edge).
    """

    direction: Offset
    max_steps: int | None = None


MovementAtom = LeapAtom | RayAtom


def atom_targets(n: int, player: Player, square: Square, atom: MovementAtom) -> tuple[Square, ...]:
    """Destinations of one atom from ``square`` on an empty board.

    For a leap this is zero or one square; for a ray it is the ordered path
    up to the board edge / ``max_steps``.
    """
    if isinstance(atom, LeapAtom):
        tgt = add_offset(square, relative_to_absolute(atom.offset, player), n)
        return (tgt,) if tgt is not None else ()
    direction = relative_to_absolute(atom.direction, player)
    path: list[Square] = []
    cur = square
    steps = 0
    while atom.max_steps is None or steps < atom.max_steps:
        nxt = add_offset(cur, direction, n)
        if nxt is None:
            break
        path.append(nxt)
        cur = nxt
        steps += 1
    return tuple(path)


def empty_mobility(
    n: int, player: Player, square: Square, atoms: tuple[MovementAtom, ...]
) -> tuple[Square, ...]:
    """All destinations reachable on an empty board (deduplicated)."""
    seen: set[Square] = set()
    result: list[Square] = []
    for atom in atoms:
        for tgt in atom_targets(n, player, square, atom):
            if tgt not in seen:
                seen.add(tgt)
                result.append(tgt)
    return tuple(result)


def empty_forward_mobility(
    n: int, player: Player, square: Square, atoms: tuple[MovementAtom, ...]
) -> tuple[Square, ...]:
    """The subset of ``empty_mobility`` that advances for ``player``."""
    return tuple(
        tgt for tgt in empty_mobility(n, player, square, atoms) if is_forward(square, tgt, player)
    )


def is_primitive_direction(direction: Offset) -> bool:
    df, dr = direction
    return (df, dr) != (0, 0) and gcd(abs(df), abs(dr)) == 1
