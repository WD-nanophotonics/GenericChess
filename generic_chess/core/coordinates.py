"""Absolute board coordinates and player-relative conversions.

Convention:

* ``Square(file, rank)`` with ``0 <= file < n``, ``0 <= rank < n``.
* Player 0 advances toward absolute ``+rank``.
* Player 1 advances toward absolute ``-rank``.
* Movement atoms are expressed in the owner's relative frame ``(df, dr)``.
  Conversion to absolute displacement: player 0 keeps ``(df, dr)``,
  player 1 rotates it by 180 degrees to ``(-df, -dr)``.
"""

from __future__ import annotations

from dataclasses import dataclass

Player = int  # 0 or 1
Offset = tuple[int, int]


@dataclass(frozen=True, slots=True, order=True)
class Square:
    """An absolute board square.

    ``file`` runs 0..n-1 left to right; ``rank`` runs 0..n-1 bottom to top.
    """

    file: int
    rank: int

    def __str__(self) -> str:
        return square_str(self)


def square_str(sq: Square) -> str:
    """Human-readable square name, e.g. ``e4`` (files a-z, ranks 1-based)."""
    if 0 <= sq.file < 26:
        return f"{chr(ord('a') + sq.file)}{sq.rank + 1}"
    return f"f{sq.file}r{sq.rank}"


def in_bounds(sq: Square, n: int) -> bool:
    return 0 <= sq.file < n and 0 <= sq.rank < n


def add_offset(sq: Square, offset: Offset, n: int) -> Square | None:
    """Return ``sq + offset`` or ``None`` when the result leaves the board."""
    nf = sq.file + offset[0]
    nr = sq.rank + offset[1]
    if 0 <= nf < n and 0 <= nr < n:
        return Square(nf, nr)
    return None


def square_to_index(sq: Square, n: int) -> int:
    """Row-major index: ``rank * n + file`` (rank 0 is the first row)."""
    return sq.rank * n + sq.file


def index_to_square(idx: int, n: int) -> Square:
    return Square(idx % n, idx // n)


def offset_between(a: Square, b: Square) -> Offset:
    """Absolute displacement from ``a`` to ``b``."""
    return (b.file - a.file, b.rank - a.rank)


def relative_to_absolute(offset: Offset, player: Player) -> Offset:
    """Convert an owner-relative displacement to an absolute one."""
    if player == 0:
        return offset
    return (-offset[0], -offset[1])


def absolute_to_relative(offset: Offset, player: Player) -> Offset:
    """Convert an absolute displacement to the owner-relative frame."""
    return relative_to_absolute(offset, player)


def rotate_offset(offset: Offset) -> Offset:
    """180-degree rotation of a relative offset."""
    return (-offset[0], -offset[1])


def rotate_square(sq: Square, n: int) -> Square:
    """180-degree rotation of an absolute square on an n x n board."""
    return Square(n - 1 - sq.file, n - 1 - sq.rank)


def is_forward(sq: Square, target: Square, player: Player) -> bool:
    """True when moving from ``sq`` to ``target`` advances for ``player``."""
    if player == 0:
        return target.rank > sq.rank
    return target.rank < sq.rank


def is_forward_relative(offset: Offset, player: Player) -> bool:
    """True when a *owner-relative* offset advances for ``player``.

    Movement atoms are expressed in the owner's frame, so ``dr > 0`` is
    forward for both players (player 1's forward is absolute ``-rank`` after
    the 180-degree rotation applied by :func:`relative_to_absolute`).
    """
    return offset[1] > 0
