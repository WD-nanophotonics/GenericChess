"""Default per-square promotion-zone derivation."""

from __future__ import annotations

from ..core.coordinates import Square, index_to_square
from ..core.movement import MovementAtom, empty_forward_mobility, empty_mobility


def derive_promotion_data(
    n: int, player: int, atoms: tuple[MovementAtom, ...]
) -> tuple[frozenset[tuple[Square, Square]], frozenset[Square]]:
    """Derive ``(promotion_allowed, promotion_forced)`` masks.

    A square belongs to the promotion zone when the piece has no forward
    destinations from it on an empty board.  A move ending in the zone allows
    promotion.  If the piece has *no* empty-board mobility at the destination,
    promotion there is forced.
    """
    zone: set[Square] = set()
    forced: set[Square] = set()
    for idx in range(n * n):
        sq = index_to_square(idx, n)
        if not empty_forward_mobility(n, player, sq, atoms):
            zone.add(sq)
        if not empty_mobility(n, player, sq, atoms):
            forced.add(sq)

    allowed: set[tuple[Square, Square]] = set()
    for idx in range(n * n):
        from_sq = index_to_square(idx, n)
        for to_sq in empty_mobility(n, player, from_sq, atoms):
            if to_sq in zone:
                allowed.add((from_sq, to_sq))
    return frozenset(allowed), frozenset(forced)
