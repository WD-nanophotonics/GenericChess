"""Initial-setup layout generators (player 0 side only; P1 is a 180° copy)."""

from __future__ import annotations

import random

from ..core.pieces import Piece


def _piece(owner: int, tid: str) -> Piece:
    return Piece(owner=owner, base_type_id=tid, current_type_id=tid, promoted=False)


def classic_like(
    rng: random.Random, n: int, ordinary_ids: tuple[str, ...]
) -> tuple[tuple[Piece | None, ...], ...]:
    """Fill relative ranks 0 and 1: back rank pairs + anchor (+ companion)."""
    pair_ids = [tid for tid in ordinary_ids if tid not in ("P", "X")]
    back: list[Piece | None] = [None] * n
    if n % 2 == 0:
        center = n // 2 - 1
        back[center] = _piece(0, "K")
        back[center + 1] = _piece(0, "X")
        outer_pairs = center
    else:
        back[n // 2] = _piece(0, "K")
        outer_pairs = n // 2
    for i in range(outer_pairs):
        back[i] = _piece(0, pair_ids[i])
        back[n - 1 - i] = _piece(0, pair_ids[i])
    front = [_piece(0, "P") for _ in range(n)]
    rows = [[None] * n for _ in range(n)]
    rows[0] = back
    rows[1] = front
    return tuple(tuple(r) for r in rows)


def bilateral_random(
    rng: random.Random, n: int, ordinary_ids: tuple[str, ...]
) -> tuple[tuple[Piece | None, ...], ...]:
    """Both ranks filled in left/right file pairs; central anchor exception."""
    ordinary = [tid for tid in ordinary_ids if tid != "K"]
    back: list[Piece | None] = [None] * n
    front: list[Piece | None] = [None] * n
    if n % 2 == 0:
        for i in range(n // 2 - 1):
            tid = rng.choice(ordinary)
            back[i] = _piece(0, tid)
            back[n - 1 - i] = _piece(0, tid)
        back[n // 2 - 1] = _piece(0, "K")
        back[n // 2] = _piece(0, rng.choice(ordinary))
        for i in range(n // 2):
            tid = rng.choice(ordinary)
            front[i] = _piece(0, tid)
            front[n - 1 - i] = _piece(0, tid)
    else:
        for i in range(n // 2):
            tid = rng.choice(ordinary)
            back[i] = _piece(0, tid)
            back[n - 1 - i] = _piece(0, tid)
        back[n // 2] = _piece(0, "K")
        for i in range(n // 2):
            tid = rng.choice(ordinary)
            front[i] = _piece(0, tid)
            front[n - 1 - i] = _piece(0, tid)
        front[n // 2] = _piece(0, rng.choice(ordinary))
    rows = [[None] * n for _ in range(n)]
    rows[0] = back
    rows[1] = front
    return tuple(tuple(r) for r in rows)


def free_random(
    rng: random.Random, n: int, ordinary_ids: tuple[str, ...]
) -> tuple[tuple[Piece | None, ...], ...]:
    """Player 0's 2n slots freely assigned (no internal symmetry required)."""
    ordinary = [tid for tid in ordinary_ids if tid != "K"]
    slots: list[tuple[int, int]] = [(rank, file) for rank in (0, 1) for file in range(n)]
    k_pos = rng.randrange(len(slots))
    rows = [[None] * n for _ in range(n)]
    for i, (rank, file) in enumerate(slots):
        tid = "K" if i == k_pos else rng.choice(ordinary)
        rows[rank][file] = _piece(0, tid)
    return tuple(tuple(r) for r in rows)
