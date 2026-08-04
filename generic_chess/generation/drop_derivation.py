"""Default per-square drop-mask derivation."""

from __future__ import annotations

from ..core.coordinates import index_to_square
from ..core.movement import MovementAtom, empty_mobility


def derive_drop_mask(n: int, player: int, atoms: tuple[MovementAtom, ...]) -> tuple[bool, ...]:
    """A drop is allowed on ``x`` iff the base type has mobility from ``x``."""
    return tuple(
        bool(empty_mobility(n, player, index_to_square(idx, n), atoms)) for idx in range(n * n)
    )
