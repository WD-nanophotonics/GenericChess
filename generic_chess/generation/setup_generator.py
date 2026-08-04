"""Initial-position construction: player 0 layout + strict 180° player 1 copy."""

from __future__ import annotations

import random

from ..core.pieces import Piece
from .presets import bilateral_random, classic_like, free_random


def _rotate_player1(rows: tuple[tuple[Piece | None, ...], ...], n: int):
    rotated = [[None] * n for _ in range(n)]
    for rank in range(n):
        for file in range(n):
            cell = rows[n - 1 - rank][n - 1 - file]
            if cell is not None:
                rotated[rank][file] = Piece(
                    owner=1,
                    base_type_id=cell.base_type_id,
                    current_type_id=cell.current_type_id,
                    promoted=cell.promoted,
                )
    return tuple(tuple(r) for r in rotated)


def build_initial_setup(
    rng: random.Random, preset: str, n: int, ordinary_ids: tuple[str, ...]
) -> tuple[tuple[Piece | None, ...], ...]:
    """Full n x n initial position: player 0 layout and rotated player 1 side."""
    if preset == "classic_like":
        p0 = classic_like(rng, n, ordinary_ids)
    elif preset == "bilateral_random":
        p0 = bilateral_random(rng, n, ordinary_ids)
    elif preset == "free_random":
        p0 = free_random(rng, n, ordinary_ids)
    else:
        raise ValueError(f"unknown setup_preset {preset!r}")

    p1 = _rotate_player1(p0, n)
    merged: list[tuple[Piece | None, ...]] = []
    for rank in range(n):
        row: list[Piece | None] = []
        for file in range(n):
            cell = p0[rank][file]
            if cell is not None and cell.owner == 0:
                row.append(cell)
            elif p1[rank][file] is not None:
                row.append(p1[rank][file])
            else:
                row.append(None)
        merged.append(tuple(row))
    return tuple(merged)
