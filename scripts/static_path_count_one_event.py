"""Standalone exact occupancy-cube representation for one-screen events."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeAlias

from generic_chess.rules.ir import geometry_candidates


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


def compiled_path_count_one_cubes(
    pattern: Any,
    geometries: Mapping[str, Any],
    *,
    owner: str,
    source: int,
    target: int,
    board_area: int,
) -> EventSet:
    """Translate one compiled semantic candidate into exact occupancy cubes.

    Only a single path_count_eq(1), any-owner predicate, an enemy endpoint, and
    ray geometry are accepted. All coordinates must be distinct in-board
    indices and the requested (source, target) pair must resolve to one
    compiled geometry candidate.
    """
    if not isinstance(board_area, int) or isinstance(board_area, bool) or board_area <= 0:
        raise ValueError("board_area must be a positive integer")
    indices = (source, target)
    if any(not isinstance(index, int) or isinstance(index, bool) for index in indices):
        raise ValueError("source and target indices must be integers")
    if any(index < 0 or index >= board_area for index in indices):
        raise ValueError("source and target indices must be within board_area")
    if source == target:
        raise ValueError("source and target indices must differ")
    if getattr(getattr(pattern, "target", None), "kind", None) != "target_enemy":
        raise ValueError("only enemy-target patterns are supported")

    predicates = getattr(pattern, "path", None)
    if not isinstance(predicates, tuple) or len(predicates) != 1:
        raise ValueError("exactly one compiled path predicate is required")
    predicate = predicates[0]
    if (
        getattr(predicate, "kind", None) != "path_count_eq"
        or type(getattr(predicate, "count", None)) is not int
        or getattr(predicate, "count", None) != 1
        or getattr(predicate, "owner_filter", None) != "any"
    ):
        raise ValueError("only path_count_eq(1) with owner_filter='any' is supported")

    geometry_ids = getattr(pattern, "geometry_ids", None)
    if not isinstance(geometry_ids, tuple) or not geometry_ids:
        raise ValueError("compiled pattern must reference geometry")
    matches: list[tuple[int, ...]] = []
    for geometry_id in geometry_ids:
        geometry = geometries.get(geometry_id)
        if geometry is None or getattr(geometry, "kind", None) != "ray":
            raise ValueError("all referenced geometries must be available rays")
        paths_by_owner = getattr(geometry, "paths", None)
        if not isinstance(paths_by_owner, Mapping) or owner not in paths_by_owner:
            raise ValueError("owner has no compiled ray paths")
        sources = paths_by_owner[owner]
        if not isinstance(sources, Mapping) or source not in sources:
            raise ValueError("source has no compiled ray path")
        candidates = geometry_candidates(geometry, owner, source)
        for candidate_target, path in candidates:
            if (
                not isinstance(candidate_target, int)
                or isinstance(candidate_target, bool)
                or candidate_target < 0
                or candidate_target >= board_area
                or not isinstance(path, tuple)
                or any(
                    not isinstance(index, int)
                    or isinstance(index, bool)
                    or index < 0
                    or index >= board_area
                    for index in path
                )
                or source in path
                or candidate_target in path
                or len(set(path)) != len(path)
            ):
                raise ValueError("compiled ray candidate contains malformed indices")
            if candidate_target == target:
                matches.append(path)

    if len(matches) != 1:
        raise ValueError("source and target must resolve to exactly one ray candidate")
    path = matches[0]

    return path_count_one_cubes(
        path,
        target,
        predicate_kind=predicate.kind,
        count=predicate.count,
        owner_filter=predicate.owner_filter,
    )


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
