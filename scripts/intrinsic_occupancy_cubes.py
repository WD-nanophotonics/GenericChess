"""Exact local occupancy cubes for a path-count predicate.

This is a semantic primitive, not a material-value formula. The cubes
can be passed to the V2C finite-population union measure.
"""

from __future__ import annotations

from itertools import combinations
from math import comb


def path_count_eq_cubes(path: tuple[int, ...], count: int, *,
                        owner_filter: str = "any", max_cubes: int = 256) -> tuple[tuple, ...]:
    """Return disjoint cubes for exactly `count` occupied path squares.

    Only the RuleSet `owner_filter=any` meaning (own or enemy) is covered.
    Other filters must be modeled separately rather than silently relaxed.
    """
    if owner_filter != "any":
        raise ValueError(f"unsupported path-count owner filter: {owner_filter}")
    if count < 0 or max_cubes < 1 or len(set(path)) != len(path) or any(s < 0 for s in path):
        raise ValueError("invalid path-count event")
    if count > len(path):
        return ()
    if comb(len(path), count) > max_cubes:
        raise ValueError("path-count cube budget exceeded")
    squares = tuple(sorted(path))
    cubes = []
    for occupied_tuple in combinations(squares, count):
        occupied = set(occupied_tuple)
        cubes.append(tuple((square, ("enemy", "own") if square in occupied else ("empty",))
                           for square in squares))
    return tuple(cubes)


def intersect_cubes(left: tuple, right: tuple) -> tuple | None:
    """Conjoin two occupancy cubes; return None for an impossible overlap."""
    constraints: dict[int, set[str]] = {}
    for square, labels in (*left, *right):
        allowed = set(labels)
        if square in constraints:
            allowed &= constraints[square]
        if not allowed:
            return None
        constraints[square] = allowed
    return tuple((square, tuple(sorted(labels))) for square, labels in sorted(constraints.items()))
