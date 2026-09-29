"""Compose one compiled intrinsic board-action candidate into physical events.

This is a local semantic audit. It deliberately returns no material score.
Unmodeled transition or guard semantics raise rather than become zero mass.
"""

from __future__ import annotations

from scripts.audit_static_semantic_material_prior_v2a import SUPPORTED_TARGETS
from scripts.audit_static_semantic_material_prior_v2d import resolve_removed_square
from scripts.intrinsic_occupancy_cubes import (
    empty_exact_guard_cube, intersect_cubes, path_count_eq_cubes,
    square_zone_guard_holds,
)


def _conjoin(cubes: tuple[tuple, ...], constraint: tuple[tuple, ...]) -> tuple[tuple, ...]:
    return tuple(merged for cube in cubes
                 if (merged := intersect_cubes(cube, constraint)) is not None)


def event_cubes_for_candidate(compiled, pattern, *, type_id: str, owner: int,
                              source: int, target: int, path: tuple[int, ...]) -> dict[tuple, tuple]:
    """Map physical event identity to exact occupancy cubes for one candidate.

    Covers type-preserving board moves, including off-target opponent
    removal, path counts, exact-empty guards, and deterministic zones.
    Dynamic own-anchor safety is recorded by the caller as an exclusion.
    """
    if type_id not in pattern.type_ids or pattern.promotion_mode != "none":
        raise ValueError("type transition or wrong source type is unsupported")
    if pattern.slot_guards or pattern.postconditions:
        raise ValueError("history or postcondition is unsupported")
    if any(inv.kind != "own_anchor_safe" for inv in pattern.invariants):
        raise ValueError("unsupported dynamic invariant")
    moves = [effect for effect in pattern.effects if effect.kind == "move"]
    if (len(moves) != 1 or moves[0].from_ref is None or moves[0].to_ref is None
            or moves[0].from_ref.kind != "source" or moves[0].to_ref.kind != "target"):
        raise ValueError("action is not one source-to-target board move")
    if any(effect.kind not in ("move", "remove") for effect in pattern.effects):
        raise ValueError("unsupported physical effect")
    if pattern.target.kind not in SUPPORTED_TARGETS:
        raise ValueError("unsupported target predicate")
    if not all(square_zone_guard_holds(compiled, guard, owner=owner,
                                       source=source, target=target, path=path)
               for guard in pattern.square_zone_guards):
        return {}

    cubes: tuple[tuple, ...] = ((),)
    for predicate in pattern.path:
        if predicate.kind == "path_clear":
            cubes = _conjoin(cubes, tuple((square, ("empty",)) for square in path))
        elif predicate.kind == "path_count_eq":
            branches = path_count_eq_cubes(path, predicate.count,
                                           owner_filter=predicate.owner_filter)
            cubes = tuple(merged for cube in cubes for branch in branches
                          if (merged := intersect_cubes(cube, branch)) is not None)
        else:
            raise ValueError("unsupported path predicate")
    for guard in pattern.guards:
        condition = empty_exact_guard_cube(guard, owner=owner, source=source,
                                           target=target, path=path,
                                           board_shape=compiled.support.board_shape)
        if condition is None:
            return {}
        cubes = _conjoin(cubes, condition)

    removals = []
    for effect in pattern.effects:
        if effect.kind != "remove":
            continue
        if effect.piece_owner != "opponent" or effect.disposition not in (
                "remove_from_game", "capture_to_hand") or effect.square_ref is None:
            raise ValueError("unsupported removal effect")
        square = resolve_removed_square(effect.square_ref, owner=owner,
                                        source=source, target=target, path=path,
                                        board_shape=compiled.support.board_shape)
        if square is None or square == source:
            raise ValueError("unresolved or source-square removal")
        removals.append((square, effect.disposition))
        cubes = _conjoin(cubes, ((square, ("enemy",)),))
    physical_removals = tuple(sorted(set(removals)))
    if not cubes:
        return {}

    events = {}
    for state in sorted(SUPPORTED_TARGETS[pattern.target.kind]):
        if state == "enemy" and not any(square == target for square, _ in physical_removals):
            raise ValueError("enemy target without opponent removal")
        event_cubes = _conjoin(cubes, ((target, (state,)),))
        if event_cubes:
            key = (owner, type_id, source, target, state, physical_removals, type_id)
            events[key] = tuple(sorted(set(event_cubes)))
    return events
