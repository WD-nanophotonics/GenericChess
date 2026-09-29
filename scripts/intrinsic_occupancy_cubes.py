"""Exact local occupancy cubes for a path-count predicate.

This is a semantic primitive, not a material-value formula. The cubes
can be passed to the V2C finite-population union measure.
"""

from __future__ import annotations

from itertools import combinations
from math import comb

from scripts.audit_static_semantic_material_prior_v2d import resolve_removed_square


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


def empty_exact_guard_cube(guard, *, owner: int, source: int, target: int,
                           path: tuple[int, ...], board_shape) -> tuple | None:
    """Encode an exact any-piece count-zero guard, or fail closed.

    None means its referenced square is off the board and the action
    event is impossible. Typed or owner-specific guards are unsupported.
    """
    refs = guard.spatial.refs
    if not (guard.aggregation == "count" and guard.owner == "any"
            and guard.type_ref.kind == "any" and guard.promoted == "any"
            and guard.location == "board" and guard.spatial.kind == "exact"
            and len(refs) == 1 and guard.subject_ref == refs[0]
            and guard.comparison == "eq" and guard.value == 0):
        raise ValueError("unsupported exact occupancy guard")
    ref = refs[0]
    if ref.kind not in ("source", "target", "path_step", "fixed",
                        "offset_from_source", "offset_from_target"):
        raise ValueError("unsupported exact guard square reference")
    square = resolve_removed_square(ref, owner=owner, source=source,
                                    target=target, path=path, board_shape=board_shape)
    return None if square is None else ((square, ("empty",)),)


def square_zone_guard_holds(compiled, guard, *, owner: int, source: int,
                            target: int, path: tuple[int, ...]) -> bool:
    """Evaluate an intrinsic compiled square-zone guard exactly."""
    if guard.spatial.kind != "zone" or guard.relation not in ("inside", "outside"):
        raise ValueError("unsupported square-zone guard")
    shape = compiled.support.board_shape
    square = resolve_removed_square(guard.square_ref, owner=owner,
                                    source=source, target=target, path=path,
                                    board_shape=shape)
    zone = compiled.ir.zones.get(guard.spatial.zone_id)
    if zone is None:
        raise ValueError("missing compiled square zone")
    if square is None:
        return False
    zone_squares = set(zone.squares)
    if guard.owner_relative and owner == 1:
        zone_squares = {(shape.height - 1 - index // shape.width) * shape.width
                        + (shape.width - 1 - index % shape.width)
                        for index in zone_squares}
    return (square in zone_squares) == (guard.relation == "inside")
