"""Compose one compiled intrinsic board-action candidate into physical events.

This is a local semantic audit. It deliberately returns no material score.
Unmodeled transition or guard semantics raise rather than become zero mass.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from generic_chess.rules.ir import geometry_candidates
from scripts.audit_static_semantic_material_prior_v2 import (
    _is_history_conditional, _promotion_forced, _promotion_targets,
)
from scripts.audit_static_semantic_material_prior_v2a import (
    SUPPORTED_TARGETS, _simple_source_guard_supported, _source_guards_hold,
)
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

    Covers board moves, including off-target opponent removal, path
    counts, exact-empty guards, deterministic zones and promotion choices.
    Dynamic own-anchor safety is recorded by the caller as an exclusion.
    """
    if type_id not in pattern.type_ids:
        raise ValueError("wrong source type")
    if pattern.promotion_mode not in ("none", "inherit_compiled_masks", "explicit"):
        raise ValueError("unknown promotion mode")
    if pattern.slot_guards or pattern.postconditions:
        raise ValueError("history or postcondition is unsupported")
    if any(inv.kind != "own_anchor_safe" for inv in pattern.invariants):
        raise ValueError("unsupported dynamic invariant")
    moves = [effect for effect in pattern.effects if effect.kind == "move"]
    if (len(moves) != 1 or moves[0].from_ref is None or moves[0].to_ref is None
            or moves[0].from_ref.kind != "source" or moves[0].to_ref.kind != "target"):
        raise ValueError("action is not one source-to-target board move")
    if any(effect.kind not in ("move", "remove", "set_token", "clear_token")
           for effect in pattern.effects):
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
        if _simple_source_guard_supported(guard):
            source_guard = _source_guards_hold(
                compiled, replace(pattern, guards=(guard,)), type_id, owner, source)
            if source_guard is None:
                raise ValueError("source guard could not be resolved")
            if not source_guard:
                return {}
            continue
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

    if pattern.promotion_mode == "none":
        resulting_types = (type_id,)
    elif pattern.promotion_mode == "explicit":
        if pattern.explicit_promotion_type is None:
            raise ValueError("explicit promotion lacks resulting type")
        resulting_types = (pattern.explicit_promotion_type,)
    else:
        promoted = _promotion_targets(compiled, type_id, owner, source, target)
        forced = bool(promoted) and _promotion_forced(compiled, type_id, owner, target)
        resulting_types = tuple(sorted(set((() if forced else (type_id,)) + promoted)))
    if not resulting_types or any(result not in compiled.support.type_metadata
                                  for result in resulting_types):
        raise ValueError("invalid resulting type")

    events = {}
    for state in sorted(SUPPORTED_TARGETS[pattern.target.kind]):
        if state == "enemy" and not any(square == target for square, _ in physical_removals):
            raise ValueError("enemy target without opponent removal")
        event_cubes = _conjoin(cubes, ((target, (state,)),))
        for result_type in resulting_types:
            if event_cubes:
                key = (owner, type_id, source, target, state,
                       physical_removals, result_type)
                events[key] = tuple(sorted(set(event_cubes)))
    return events


def collect_intrinsic_board_events(compiled, type_id: str, *,
                                   max_candidates: int = 100_000) -> dict:
    """Union duplicate physical descriptions for one board-mode current type.

    Excluded held/history/dynamic semantics and unsupported intrinsic
    patterns remain visible. No event probabilities or values are computed.
    """
    if max_candidates < 1:
        raise ValueError("candidate budget must be positive")
    area = compiled.support.board_shape.area
    groups: dict[tuple, set[tuple]] = defaultdict(set)
    unsupported: set[tuple[str, str]] = set()
    excluded_held: set[str] = set()
    excluded_disabled_drop: set[str] = set()
    excluded_history: set[str] = set()
    excluded_dynamic: set[tuple[str, str]] = set()
    excluded_auxiliary_effects: set[tuple[str, str]] = set()
    candidate_count = 0
    allowed_drop_squares = sum(sum(mask) for mask in
                               compiled.support.drop_allowed.get(type_id, ())[:2])
    for pattern in compiled.ir.patterns:
        if type_id not in pattern.type_ids:
            continue
        for invariant in pattern.invariants:
            if invariant.kind == "own_anchor_safe":
                excluded_dynamic.add((pattern.name, invariant.kind))
        for effect in pattern.effects:
            if effect.kind in ("set_token", "clear_token"):
                excluded_auxiliary_effects.add((pattern.name, effect.kind))
        if _is_history_conditional(pattern):
            excluded_history.add(pattern.name)
            continue
        for geometry_id in pattern.geometry_ids:
            geometry = compiled.ir.geometry[geometry_id]
            if geometry.kind == "drop":
                (excluded_held if allowed_drop_squares else excluded_disabled_drop).add(pattern.name)
                continue
            if geometry.kind not in ("leap", "ray"):
                unsupported.add((pattern.name, f"unsupported_geometry:{geometry.kind}"))
                continue
            for owner in (0, 1):
                for source in range(area):
                    for target, path in geometry_candidates(geometry, str(owner), source):
                        candidate_count += 1
                        if candidate_count > max_candidates:
                            raise RuntimeError("intrinsic candidate budget exceeded")
                        try:
                            events = event_cubes_for_candidate(
                                compiled, pattern, type_id=type_id, owner=owner,
                                source=source, target=target, path=path)
                        except ValueError as error:
                            unsupported.add((pattern.name, str(error)))
                            continue
                        for key, cubes in events.items():
                            groups[key].update(cubes)
    return {
        "events": {key: tuple(sorted(cubes)) for key, cubes in sorted(groups.items())},
        "candidate_count": candidate_count,
        "unsupported_intrinsic": tuple(sorted(unsupported)),
        "excluded_held": tuple(sorted(excluded_held)),
        "excluded_disabled_drop": tuple(sorted(excluded_disabled_drop)),
        "allowed_drop_squares": allowed_drop_squares,
        "excluded_history": tuple(sorted(excluded_history)),
        "excluded_dynamic": tuple(sorted(excluded_dynamic)),
        "excluded_auxiliary_effects": tuple(sorted(excluded_auxiliary_effects)),
        "coverage_complete": not unsupported,
    }


def collect_intrinsic_held_drop_events(compiled, type_id: str, *,
                                       max_targets: int = 1_000) -> dict:
    """Record hand-to-board drop options under compiled square masks.

    State guards, postconditions and dynamic safety are explicit
    exclusions; the returned occupancy cubes are coarse intrinsic events.
    No hand-conditioned occupancy probability is assigned here.
    """
    if max_targets < 1:
        raise ValueError("drop target budget must be positive")
    masks = compiled.support.drop_allowed.get(type_id, ())[:2]
    area = compiled.support.board_shape.area
    if len(masks) != 2 or any(len(mask) != area for mask in masks):
        raise ValueError("incomplete compiled drop masks")
    promoted_types = {target for metadata in compiled.support.type_metadata.values()
                      for target in metadata.promotion_target_ids}
    events = {}
    unsupported: set[tuple[str, str]] = set()
    excluded_constraints: set[tuple[str, str]] = set()
    excluded_dynamic: set[tuple[str, str]] = set()
    disabled_patterns: set[str] = set()
    target_count = 0
    for pattern in compiled.ir.patterns:
        if type_id not in pattern.type_ids:
            continue
        for geometry_id in pattern.geometry_ids:
            geometry = compiled.ir.geometry[geometry_id]
            if geometry.kind != "drop":
                continue
            if not any(any(mask) for mask in masks):
                disabled_patterns.add(pattern.name)
                continue
            if pattern.target.kind != "target_empty" or pattern.promotion_mode != "none":
                unsupported.add((pattern.name, "drop_target_or_transition_unsupported"))
                continue
            if pattern.path or pattern.slot_guards or pattern.square_zone_guards:
                unsupported.add((pattern.name, "drop_path_history_or_zone_unsupported"))
                continue
            effects = tuple(effect.kind for effect in pattern.effects)
            if sorted(effects) != ["place", "remove_from_hand"]:
                unsupported.add((pattern.name, "drop_effect_pair_unsupported"))
                continue
            valid_refs = all(
                effect.piece_type_ref is not None and (
                    (effect.piece_type_ref.kind == "explicit"
                     and effect.piece_type_ref.type_id == type_id)
                    or (effect.piece_type_ref.kind == "action_base"
                        and type_id not in promoted_types))
                for effect in pattern.effects)
            place = next(effect for effect in pattern.effects if effect.kind == "place")
            if not valid_refs or place.to_ref is None or place.to_ref.kind != "target":
                unsupported.add((pattern.name, "drop_type_or_destination_unsupported"))
                continue
            for guard in pattern.guards:
                excluded_constraints.add((pattern.name, f"state_guard:{guard.spatial.kind}"))
            for postcondition in pattern.postconditions:
                excluded_constraints.add((pattern.name, f"postcondition:{postcondition.kind}"))
            bad_invariant = False
            for invariant in pattern.invariants:
                if invariant.kind == "own_anchor_safe":
                    excluded_dynamic.add((pattern.name, invariant.kind))
                else:
                    unsupported.add((pattern.name, f"invariant:{invariant.kind}"))
                    bad_invariant = True
            if bad_invariant:
                continue
            for owner, mask in enumerate(masks):
                for target, allowed in enumerate(mask):
                    if not allowed:
                        continue
                    target_count += 1
                    if target_count > max_targets:
                        raise RuntimeError("held drop target budget exceeded")
                    key = (owner, type_id, "hand", target, "empty", (), type_id)
                    events[key] = (((target, ("empty",)),),)
    return {
        "events": dict(sorted(events.items())),
        "target_count": target_count,
        "unsupported_intrinsic": tuple(sorted(unsupported)),
        "excluded_state_constraints": tuple(sorted(excluded_constraints)),
        "excluded_dynamic": tuple(sorted(excluded_dynamic)),
        "disabled_patterns": tuple(sorted(disabled_patterns)),
        "coarse_coverage_complete": not unsupported,
        "full_legality_modeled": not unsupported and not excluded_constraints and not excluded_dynamic,
    }
