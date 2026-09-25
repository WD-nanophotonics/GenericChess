"""Standalone exact occupancy-cube representation for one-screen events."""

from __future__ import annotations

from typing import TypeAlias


Cube: TypeAlias = tuple[tuple[int, tuple[str, ...]], ...]
EventSet: TypeAlias = tuple[Cube, ...]

def path_count_one_cubes(
    path: tuple[int, ...],
    target: int,
    *,
    predicate_kind: str = "path_count_eq",
    count: int = 1,
    owner_filter: str = "any",
) -> EventSet:
    """Build disjoint cubes for exactly one occupied path index and enemy target.

    This intentionally supports only the generic path_count_eq(1), any-owner
    case. Unsupported semantics and ambiguous index sets fail closed.
    """
    if (
        predicate_kind != "path_count_eq"
        or type(count) is not int
        or count != 1
        or owner_filter != "any"
    ):
        raise ValueError("only path_count_eq(1) with owner_filter='any' is supported")
    if any(not isinstance(index, int) or isinstance(index, bool) for index in (*path, target)):
        raise ValueError("path and target indices must be integers")
    if not path:
        raise ValueError("path must contain at least one index")
    if len(set(path)) != len(path):
        raise ValueError("path indices must be unique")
    if target in path:
        raise ValueError("target index must not overlap the path")

    cubes = []
    for occupied in path:
        restrictions = {index: ("empty",) for index in path if index != occupied}
        restrictions[occupied] = ("enemy", "own")
        restrictions[target] = ("enemy",)
        cubes.append(tuple(sorted(restrictions.items())))
    return tuple(cubes)


def cubes_are_pairwise_disjoint(cubes: EventSet) -> bool:
    """Return whether no assignment can satisfy two distinct cubes."""
    for left_index, left in enumerate(cubes):
        left_constraints = dict(left)
        for right in cubes[left_index + 1:]:
            right_constraints = dict(right)
            if all(
                set(left_constraints[index]) & set(right_constraints[index])
                for index in left_constraints.keys() & right_constraints.keys()
            ):
                return False
    return True
