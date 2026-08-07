"""RuleSet compilation: validation plus precomputed movement tables.

The compiler never rejects rules because they are "unfun"; it only checks
that the rules are complete, self-consistent and executable.  Symmetry,
inventory balance and aesthetics are Generator concerns.
"""

from __future__ import annotations

from math import gcd
from typing import Any, Mapping

from ..core.attacks import is_in_check
from ..core.coordinates import (
    Square,
    index_to_square,
    is_forward,
    square_to_index,
)
from ..core.movement import LeapAtom, RayAtom, MovementAtom
from ..core.movegen import legal_actions_from_position
from ..core.pieces import Piece, PieceType
from ..core.position import Hands, Position
from .compiled import CompiledRuleSet
from .schema import RuleSet, compute_fingerprint, ruleset_from_dict
from .serialization import deserialize_ruleset, serialize_ruleset
from .validation import RuleValidationError, ValidationIssue


def _is_forward_target(sq: Square, target: Square, player: int) -> bool:
    return is_forward(sq, target, player)


def _build_tables(ruleset: RuleSet) -> dict[str, Any]:
    """Precompute all geometry tables on an empty board."""
    n = ruleset.board_size
    leap_targets: dict[str, Any] = {}
    ray_paths: dict[str, Any] = {}
    empty_mobility: dict[str, Any] = {}
    empty_forward_mobility: dict[str, Any] = {}

    for pt in ruleset.piece_types:
        per_player_leap: list[Any] = []
        per_player_ray: list[Any] = []
        per_player_mob: list[Any] = []
        per_player_fwd: list[Any] = []
        for player in (0, 1):
            per_square_leap: list[Any] = []
            per_square_ray: list[Any] = []
            per_square_mob: list[Any] = []
            per_square_fwd: list[Any] = []
            for idx in range(n * n):
                sq = index_to_square(idx, n)
                atom_leap: list[tuple[Square, ...]] = []
                atom_ray: list[tuple[Square, ...]] = []
                seen: set[Square] = set()
                mob: list[Square] = []
                for atom in pt.movement_atoms:
                    targets = _atom_targets(n, player, sq, atom)
                    if isinstance(atom, LeapAtom):
                        atom_leap.append(targets)
                        atom_ray.append(())
                    else:
                        atom_leap.append(())
                        atom_ray.append(targets)
                    for tgt in targets:
                        if tgt not in seen:
                            seen.add(tgt)
                            mob.append(tgt)
                per_square_leap.append(tuple(atom_leap))
                per_square_ray.append(tuple(atom_ray))
                per_square_mob.append(tuple(mob))
                per_square_fwd.append(
                    tuple(t for t in mob if _is_forward_target(sq, t, player))
                )
            per_player_leap.append(tuple(per_square_leap))
            per_player_ray.append(tuple(per_square_ray))
            per_player_mob.append(tuple(per_square_mob))
            per_player_fwd.append(tuple(per_square_fwd))
        leap_targets[pt.type_id] = tuple(per_player_leap)
        ray_paths[pt.type_id] = tuple(per_player_ray)
        empty_mobility[pt.type_id] = tuple(per_player_mob)
        empty_forward_mobility[pt.type_id] = tuple(per_player_fwd)

    return {
        "leap_targets": leap_targets,
        "ray_paths": ray_paths,
        "empty_mobility": empty_mobility,
        "empty_forward_mobility": empty_forward_mobility,
    }


def _atom_targets(
    n: int, player: int, square: Square, atom: MovementAtom
) -> tuple[Square, ...]:
    if isinstance(atom, LeapAtom):
        df, dr = atom.offset
        if player == 1:
            df, dr = -df, -dr
        nf, nr = square.file + df, square.rank + dr
        if 0 <= nf < n and 0 <= nr < n:
            return (Square(nf, nr),)
        return ()
    df, dr = atom.direction
    if player == 1:
        df, dr = -df, -dr
    path: list[Square] = []
    cur = square
    steps = 0
    while atom.max_steps is None or steps < atom.max_steps:
        nf, nr = cur.file + df, cur.rank + dr
        if not (0 <= nf < n and 0 <= nr < n):
            break
        nxt = Square(nf, nr)
        path.append(nxt)
        cur = nxt
        steps += 1
    return tuple(path)


def _basic_validation(ruleset: RuleSet) -> list[ValidationIssue]:
    """Structural validation that does not need compiled tables."""
    issues: list[ValidationIssue] = []
    n = ruleset.board_size

    if not isinstance(n, int) or n < 3:
        issues.append(
            ValidationIssue("BOARD_SIZE_TOO_SMALL", "board_size", "board_size must be an integer >= 3")
        )

    if ruleset.schema_version != 1:
        issues.append(
            ValidationIssue(
                "SCHEMA_VERSION_UNSUPPORTED",
                "schema_version",
                f"schema_version must be 1, got {ruleset.schema_version!r}",
            )
        )

    if not ruleset.piece_types:
        issues.append(ValidationIssue("NO_PIECE_TYPES", "piece_types", "at least one piece type is required"))

    type_ids: set[str] = set()
    anchor_ids: set[str] = set()
    promotable_ids: set[str] = set()
    types_by_id: dict[str, PieceType] = {}
    for i, pt in enumerate(ruleset.piece_types):
        path = f"piece_types[{i}]"
        if not isinstance(pt.type_id, str) or not pt.type_id:
            issues.append(ValidationIssue("TYPE_ID_INVALID", f"{path}.type_id", "type_id must be a non-empty string"))
        elif pt.type_id in type_ids:
            issues.append(ValidationIssue("TYPE_ID_DUPLICATE", f"{path}.type_id", f"duplicate type_id {pt.type_id!r}"))
        type_ids.add(pt.type_id)
        types_by_id[pt.type_id] = pt

        if pt.is_anchor:
            anchor_ids.add(pt.type_id)
            if pt.is_promotable:
                issues.append(ValidationIssue("ANCHOR_IS_PROMOTABLE", f"{path}.is_promotable", "anchors cannot be promotable"))
            if pt.promotion_target_ids:
                issues.append(ValidationIssue("ANCHOR_HAS_PROMOTION_TARGETS", f"{path}.promotion_target_ids", "anchors cannot have promotion targets"))

        if pt.is_promotable:
            promotable_ids.add(pt.type_id)
            if not pt.promotion_target_ids:
                issues.append(ValidationIssue("PROMOTABLE_WITHOUT_TARGETS", f"{path}.promotion_target_ids", "promotable types need at least one promotion target"))

        for j, atom in enumerate(pt.movement_atoms):
            apath = f"{path}.movement_atoms[{j}]"
            if isinstance(atom, LeapAtom):
                if atom.offset == (0, 0):
                    issues.append(ValidationIssue("ATOM_ZERO_OFFSET", f"{apath}.offset", "leap offset must be non-zero"))
            elif isinstance(atom, RayAtom):
                if atom.direction == (0, 0):
                    issues.append(ValidationIssue("ATOM_ZERO_DIRECTION", f"{apath}.direction", "ray direction must be non-zero"))
                elif gcd(abs(atom.direction[0]), abs(atom.direction[1])) != 1:
                    issues.append(ValidationIssue("RAY_DIRECTION_NOT_PRIMITIVE", f"{apath}.direction", "ray direction must be a primitive integer vector (gcd == 1)"))
                if atom.max_steps is not None and (not isinstance(atom.max_steps, int) or atom.max_steps < 1):
                    issues.append(ValidationIssue("RAY_MAX_STEPS_INVALID", f"{apath}.max_steps", "max_steps must be None or a positive integer"))
            else:
                issues.append(ValidationIssue("ATOM_KIND_INVALID", apath, f"unknown movement atom {atom!r}"))

    # Promotion target references (after all types are known).
    for i, pt in enumerate(ruleset.piece_types):
        path = f"piece_types[{i}]"
        for k, tgt in enumerate(pt.promotion_target_ids):
            tpath = f"{path}.promotion_target_ids[{k}]"
            if tgt not in type_ids:
                issues.append(ValidationIssue("PROMOTION_TARGET_NOT_FOUND", tpath, f"promotion target {tgt!r} is not a defined type"))
            elif tgt in anchor_ids:
                issues.append(ValidationIssue("PROMOTION_TARGET_IS_ANCHOR", tpath, f"promotion target {tgt!r} is an anchor"))

    # Initial position shape and cell consistency.
    rows = ruleset.initial_position
    if len(rows) != n or any(len(row) != n for row in rows):
        issues.append(ValidationIssue("INITIAL_POSITION_BAD_DIMENSIONS", "initial_position", f"initial_position must be {n} rows of {n} cells"))

    anchor_count = {0: 0, 1: 0}
    entity_count = 0
    for r, row in enumerate(rows):
        for f, cell in enumerate(row):
            if cell is None:
                continue
            entity_count += 1
            path = f"initial_position[{r}][{f}]"
            owner_ok = cell.owner in (0, 1)
            if not owner_ok:
                issues.append(ValidationIssue("ILLEGAL_OWNER", f"{path}.owner", f"owner must be 0 or 1, got {cell.owner!r}"))
            if cell.base_type_id not in type_ids:
                issues.append(ValidationIssue("CELL_TYPE_NOT_FOUND", f"{path}.base_type_id", f"base type {cell.base_type_id!r} is not a defined type"))
                continue
            base = types_by_id[cell.base_type_id]
            if base.is_anchor:
                if owner_ok:
                    anchor_count[cell.owner] += 1
                if cell.promoted or cell.current_type_id != cell.base_type_id:
                    issues.append(ValidationIssue("ANCHOR_STATE_INVALID", path, "anchors must be unpromoted with current_type_id == base_type_id"))
            if cell.promoted:
                if cell.current_type_id not in base.promotion_target_ids:
                    issues.append(ValidationIssue("CELL_PROMOTION_INCONSISTENT", path, f"promoted piece's current_type_id {cell.current_type_id!r} is not in promotion targets of {cell.base_type_id!r}"))
            else:
                if cell.current_type_id != cell.base_type_id:
                    issues.append(ValidationIssue("CELL_PROMOTION_INCONSISTENT", path, "unpromoted pieces must have current_type_id == base_type_id"))

    for player in (0, 1):
        if anchor_count[player] != 1:
            issues.append(ValidationIssue("ANCHOR_COUNT", "initial_position", f"each side needs exactly one anchor on the board; player {player} has {anchor_count[player]}"))

    # Drop masks: exactly one mask per non-anchor type, per player, n*n bools.
    non_anchor_ids = type_ids - anchor_ids
    if set(ruleset.drop_allowed) != non_anchor_ids:
        missing = sorted(non_anchor_ids - set(ruleset.drop_allowed))
        extra = sorted(set(ruleset.drop_allowed) - non_anchor_ids)
        issues.append(ValidationIssue("DROP_MASK_INVALID_SET", "drop_allowed", f"drop_allowed must cover exactly the non-anchor types; missing={missing} extra={extra}"))
    for tid, masks in ruleset.drop_allowed.items():
        if len(masks) != 2:
            issues.append(ValidationIssue("DROP_MASK_BAD_SHAPE", f"drop_allowed[{tid}]", "drop masks need one entry per player"))
            continue
        for player, mask in enumerate(masks):
            if len(mask) != n * n or not all(isinstance(b, bool) for b in mask):
                issues.append(ValidationIssue("DROP_MASK_BAD_SHAPE", f"drop_allowed[{tid}][{player}]", f"drop mask must be {n*n} booleans"))

    # Promotion masks: exactly one per promotable type, bounds-valid squares.
    if set(ruleset.promotion_allowed) != promotable_ids or set(ruleset.promotion_forced) != promotable_ids:
        issues.append(ValidationIssue("PROMOTION_MASK_INVALID_SET", "promotion_allowed", "promotion masks must exist exactly for the promotable types"))
    for tid in promotable_ids:
        for name, masks in (("promotion_allowed", ruleset.promotion_allowed.get(tid, ())), ("promotion_forced", ruleset.promotion_forced.get(tid, ()))):
            path = f"{name}[{tid}]"
            if len(masks) != 2:
                issues.append(ValidationIssue("PROMOTION_MASK_BAD_SHAPE", path, "promotion masks need one entry per player"))
                continue
            for player, entries in enumerate(masks):
                if name == "promotion_allowed":
                    for (fsq, tsq) in entries:
                        if not (0 <= fsq.file < n and 0 <= fsq.rank < n and 0 <= tsq.file < n and 0 <= tsq.rank < n):
                            issues.append(ValidationIssue("PROMOTION_MASK_OUT_OF_BOUNDS", f"{path}[{player}]", f"promotion pair ({fsq}, {tsq}) is out of bounds"))
                else:
                    for sq in entries:
                        if not (0 <= sq.file < n and 0 <= sq.rank < n):
                            issues.append(ValidationIssue("PROMOTION_MASK_OUT_OF_BOUNDS", f"{path}[{player}]", f"forced square {sq} is out of bounds"))

    if not isinstance(ruleset.repetition_limit, int) or ruleset.repetition_limit < 1:
        issues.append(ValidationIssue("REPETITION_LIMIT_INVALID", "repetition_limit", "repetition_limit must be a positive integer"))
    if not isinstance(ruleset.max_ply, int) or ruleset.max_ply < 1:
        issues.append(ValidationIssue("MAX_PLY_INVALID", "max_ply", "max_ply must be a positive integer"))
    if ruleset.stalemate_result != "draw":
        issues.append(ValidationIssue("STALEMATE_RESULT_UNSUPPORTED", "stalemate_result", "v0 only supports stalemate_result == 'draw'"))

    return issues


def _build_initial_position(ruleset: RuleSet, fingerprint: str) -> Position:
    flat = tuple(cell for row in ruleset.initial_position for cell in row)
    return Position(
        board=flat,
        hands=(Hands.empty(), Hands.empty()),
        side_to_move=0,
        ruleset_fingerprint=fingerprint,
    )


def _position_validation(compiled: CompiledRuleSet) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    pos = compiled.initial_position
    for player in (0, 1):
        if is_in_check(pos, player, compiled):
            issues.append(
                ValidationIssue(
                    "INITIAL_ANCHOR_ATTACKED",
                    "initial_position",
                    f"player {player}'s anchor is attacked at the initial position",
                )
            )
    if not legal_actions_from_position(pos, compiled):
        issues.append(
            ValidationIssue(
                "INITIAL_NO_LEGAL_MOVE",
                "initial_position",
                "the side to move has no legal action at the initial position",
            )
        )
    return issues


def compile_ruleset(
    rule_definition: RuleSet | Mapping[str, Any],
    *,
    allow_semantic_actions: bool = False,
) -> CompiledRuleSet:
    """Validate and compile a RuleSet (or its JSON dict form).

    Rulesets that use the additive ``semantic_actions`` DSL are **not**
    executable by the legacy Core: the legacy compiler refuses them
    (fail-closed) unless ``allow_semantic_actions=True`` is passed by the
    semantic-IR compiler for table/geometry inspection.
    """
    ruleset = rule_definition if isinstance(rule_definition, RuleSet) else ruleset_from_dict(rule_definition)
    if ruleset.semantic_actions and not allow_semantic_actions:
        raise RuleValidationError(
            [
                ValidationIssue(
                    "SEMANTIC_ACTIONS_NOT_LEGACY_EXECUTABLE",
                    "ruleset.semantic_actions",
                    "semantic actions require compile_semantic_ruleset; the "
                    "legacy Core executor must not silently ignore them",
                )
            ]
        )

    issues = _basic_validation(ruleset)
    if issues:
        raise RuleValidationError(issues)

    tables = _build_tables(ruleset)
    fingerprint = compute_fingerprint(ruleset)
    types_by_id = {pt.type_id: pt for pt in ruleset.piece_types}
    initial_position = _build_initial_position(ruleset, fingerprint)
    entity_count = sum(1 for cell in initial_position.board if cell is not None)

    compiled = CompiledRuleSet(
        ruleset_fingerprint=fingerprint,
        board_size=ruleset.board_size,
        piece_types=ruleset.piece_types,
        types_by_id=types_by_id,
        initial_position=initial_position,
        initial_entity_count=entity_count,
        leap_targets=tables["leap_targets"],
        ray_paths=tables["ray_paths"],
        empty_mobility=tables["empty_mobility"],
        empty_forward_mobility=tables["empty_forward_mobility"],
        drop_allowed=ruleset.drop_allowed,
        promotion_allowed=ruleset.promotion_allowed,
        promotion_forced=ruleset.promotion_forced,
        repetition_limit=ruleset.repetition_limit,
        max_ply=ruleset.max_ply,
        stalemate_result=ruleset.stalemate_result,
    )

    issues = _position_validation(compiled)
    if issues:
        raise RuleValidationError(issues)

    # Round-trip rule equivalence: the fingerprint must survive serialization.
    round_tripped = deserialize_ruleset(serialize_ruleset(ruleset))
    if compute_fingerprint(round_tripped) != fingerprint:
        raise RuleValidationError(
            [
                ValidationIssue(
                    "ROUNDTRIP_FINGERPRINT_MISMATCH",
                    "ruleset",
                    "serialization round-trip changed the semantic fingerprint",
                )
            ]
        )

    return compiled


# ================================================================ semantic IR


def build_geometry_metadata(compiled: CompiledRuleSet) -> dict:
    """Canonical geometry lowering (Design A): per (type, owner, source)
    ordered leap targets and ray path segments, projected from the single
    compiler lowering that also feeds the legacy execution tables."""
    n = compiled.board_size
    out: dict[str, Any] = {"schema": "geometry_v1", "squares": n * n, "types": {}}
    for tid, _pt in compiled.types_by_id.items():
        leaps: dict[str, Any] = {}
        rays: dict[str, Any] = {}
        for owner in (0, 1):
            owner_leaps: dict[int, list[list[int]]] = {}
            owner_rays: dict[int, list[list[int]]] = {}
            for idx in range(n * n):
                owner_leaps[idx] = [
                    [sq.rank * n + sq.file for sq in atom_targets]
                    for atom_targets in compiled.leap_targets[tid][owner][idx]
                ]
                owner_rays[idx] = [
                    [sq.rank * n + sq.file for sq in path]
                    for path in compiled.ray_paths[tid][owner][idx]
                ]
            leaps[str(owner)] = owner_leaps
            rays[str(owner)] = owner_rays
        out["types"][tid] = {"leap_targets": leaps, "ray_paths": rays}
    return out


def lower_legacy_to_ir(compiled: CompiledRuleSet):
    """Lower an existing legacy compiled ruleset into the production IR.

    Legacy semantics are *described* (quiet/capture patterns with
    ``path_clear``, drop templates, ``own_anchor_safe`` invariant) while the
    legacy tables remain the runtime authority; promotion stays under the
    compiled masks (``promotion_variants=compiled_masks``).
    """
    from .ir import (
        CompiledEffect,
        CompiledInvariant,
        CompiledMovePattern,
        CompiledPathPredicate,
        CompiledSemanticIR,
        CompiledTargetPredicate,
        SemanticCapabilities,
    )

    patterns: list[CompiledMovePattern] = []
    for tid, pt in compiled.types_by_id.items():
        if pt.is_anchor:
            continue
        for atom in pt.movement_atoms:
            is_ray = isinstance(atom, RayAtom)
            path = (CompiledPathPredicate("path_clear"),) if is_ray else ()
            geometry = ("ray",) if is_ray else ("leap",)
            patterns.append(
                CompiledMovePattern(
                    name=f"legacy_{tid}_quiet",
                    type_ids=(tid,),
                    geometry=geometry,
                    target=CompiledTargetPredicate("target_empty"),
                    path=path,
                    effects=(CompiledEffect("move"),),
                    invariants=(CompiledInvariant("own_anchor_safe"),),
                    cost_class="C1",
                    stratum="S3",
                    promotion_variants="compiled_masks",
                )
            )
            patterns.append(
                CompiledMovePattern(
                    name=f"legacy_{tid}_capture",
                    type_ids=(tid,),
                    geometry=geometry,
                    target=CompiledTargetPredicate("target_enemy"),
                    path=path,
                    effects=(CompiledEffect("remove", "target"), CompiledEffect("move")),
                    invariants=(CompiledInvariant("own_anchor_safe"),),
                    cost_class="C1",
                    stratum="S3",
                    promotion_variants="compiled_masks",
                )
            )
        if tid in compiled.drop_allowed:
            patterns.append(
                CompiledMovePattern(
                    name=f"legacy_{tid}_drop",
                    type_ids=(tid,),
                    geometry=("drop",),
                    target=CompiledTargetPredicate("target_empty"),
                    effects=(
                        CompiledEffect("remove_from_hand"),
                        CompiledEffect("place"),
                    ),
                    invariants=(CompiledInvariant("own_anchor_safe"),),
                    cost_class="C1",
                    stratum="S3",
                )
            )
    capabilities = SemanticCapabilities(
        legacy_core_executable=True,
        new_ir_core_executable=False,
        native_executable=True,
    )
    return CompiledSemanticIR(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        geometry_metadata=build_geometry_metadata(compiled),
        patterns=tuple(patterns),
        capabilities=capabilities,
    )


def compile_semantic_ir(compiled: CompiledRuleSet):
    """Public alias: lower a legacy compiled ruleset to the production IR."""
    return lower_legacy_to_ir(compiled)


def compile_semantic_ruleset(ruleset: RuleSet | Mapping[str, Any]):
    """Compile a RuleSet that uses the semantic DSL into the production IR.

    The resulting :class:`CompiledSemanticRuleset` is NOT executable by the
    legacy Core or native 0.3.0 (capabilities are false); it exists for
    IR inspection and as the Phase 1.9B-2 reference-executor input.
    """
    from . import ir as ir_module
    from .ir import (
        CompiledAuxSlot,
        CompiledEffect,
        CompiledInvariant,
        CompiledMovePattern,
        CompiledPathPredicate,
        CompiledPieceSelector,
        CompiledPostcondition,
        CompiledSemanticIR,
        CompiledSemanticRuleset,
        CompiledSlotGuard,
        CompiledStatePredicate,
        CompiledTargetPredicate,
        SemanticCapabilities,
        validate_ir,
    )
    from .schema import MAX_SEMANTIC_AUX_SLOTS, SEMANTIC_STRATA

    if not isinstance(ruleset, RuleSet):
        ruleset = ruleset_from_dict(ruleset)
    if not ruleset.semantic_actions:
        raise RuleValidationError(
            [
                ValidationIssue(
                    "NO_SEMANTIC_ACTIONS",
                    "ruleset.semantic_actions",
                    "compile_semantic_ruleset requires at least one semantic action",
                )
            ]
        )
    legacy = compile_ruleset(ruleset, allow_semantic_actions=True)

    # Deterministic aux-slot allocation: sorted by slot name.
    aux_by_name: dict[str, Any] = {}
    for action in ruleset.semantic_actions:
        for aux in action.aux_state:
            if aux.name in aux_by_name and aux_by_name[aux.name] != aux:
                raise RuleValidationError(
                    [
                        ValidationIssue(
                            "AUX_SLOT_CONFLICT",
                            f"ruleset.semantic_actions aux_state {aux.name}",
                            "duplicate aux state name with different definition",
                        )
                    ]
                )
            aux_by_name.setdefault(aux.name, aux)
    if len(aux_by_name) > MAX_SEMANTIC_AUX_SLOTS:
        raise RuleValidationError(
            [
                ValidationIssue(
                    "AUX_SLOTS_TOO_MANY",
                    "ruleset.semantic_actions",
                    f"at most {MAX_SEMANTIC_AUX_SLOTS} aux slots per ruleset",
                )
            ]
        )
    slot_ids = {name: i for i, name in enumerate(sorted(aux_by_name))}
    compiled_slots = tuple(
        CompiledAuxSlot(slot_ids[name], aux_by_name[name].kind, aux_by_name[name].lifetime)
        for name in sorted(aux_by_name)
    )

    patterns: list[CompiledMovePattern] = []
    contains_path = contains_guard = contains_compound = contains_post = False
    for action in ruleset.semantic_actions:
        for tid in action.type_ids:
            if tid not in legacy.types_by_id:
                raise RuleValidationError(
                    [
                        ValidationIssue(
                            "SEMANTIC_TYPE_UNKNOWN",
                            f"ruleset.semantic_actions {action.name} type_ids",
                            f"unknown type id {tid!r}",
                        )
                    ]
                )
        if action.path_constraints:
            contains_path = True
        if action.state_guards or action.slot_guards:
            contains_guard = True
        if len(action.effects) > 1:
            contains_compound = True
        if action.postconditions:
            contains_post = True

        effects = []
        for effect in action.effects:
            slot_id = slot_ids.get(effect.slot_name) if effect.slot_name else None
            if effect.slot_name and slot_id is None:
                raise RuleValidationError(
                    [
                        ValidationIssue(
                            "EFFECT_SLOT_UNKNOWN",
                            f"ruleset.semantic_actions {action.name} effects",
                            f"unknown slot name {effect.slot_name!r}",
                        )
                    ]
                )
            effects.append(
                CompiledEffect(effect.kind, effect.square_ref, slot_id, effect.type_id)
            )
        slot_guards = []
        for guard in action.slot_guards:
            if guard.slot_name not in slot_ids:
                raise RuleValidationError(
                    [
                        ValidationIssue(
                            "SLOT_GUARD_UNKNOWN",
                            f"ruleset.semantic_actions {action.name} slot_guards",
                            f"unknown slot name {guard.slot_name!r}",
                        )
                    ]
                )
            slot_guards.append(
                CompiledSlotGuard(slot_ids[guard.slot_name], guard.comparison, guard.value)
            )
        guards = tuple(
            CompiledStatePredicate(
                aggregation=g.aggregation,
                selector=CompiledPieceSelector(
                    owner=g.owner,
                    type_mode=g.type_mode,
                    promoted=g.promoted,
                    location=g.location,
                    spatial=g.spatial,
                    spatial_ref=g.spatial_ref,
                ),
                comparison=g.comparison,
                value=g.value,
            )
            for g in action.state_guards
        )
        path = tuple(
            CompiledPathPredicate(
                kind=c.kind,
                count=c.count,
                lo=c.lo,
                hi=c.hi,
                owner_filter=c.owner_filter,
            )
            for c in action.path_constraints
        )
        invariants = tuple(
            CompiledInvariant(i.kind, i.square_refs) for i in action.invariants
        )
        postconditions = tuple(
            CompiledPostcondition(p.kind, p.max_stratum) for p in action.postconditions
        )

        components = (
            list(action.geometry)
            + [action.target_relation]
            + [c.kind for c in action.path_constraints]
            + ["state_guard"] * len(action.state_guards)
            + ["slot_guard"] * len(action.slot_guards)
            + [i.kind for i in action.invariants]
            + [p.kind for p in action.postconditions]
            + [e.kind for e in action.effects]
        )
        stratum = max(SEMANTIC_STRATA.index(ir_module._component_stratum(c)) for c in components)
        cost = max(ir_module.COST_CLASSES.index(ir_module.cost_class_of(c)) for c in components)
        patterns.append(
            CompiledMovePattern(
                name=action.name,
                type_ids=action.type_ids,
                geometry=action.geometry,
                target=CompiledTargetPredicate(f"target_{action.target_relation}"),
                path=path,
                guards=guards,
                slot_guards=tuple(slot_guards),
                effects=tuple(effects),
                invariants=invariants,
                postconditions=postconditions,
                cost_class=ir_module.COST_CLASSES[cost],
                stratum=SEMANTIC_STRATA[stratum],
            )
        )

    capabilities = SemanticCapabilities(
        legacy_core_executable=False,
        new_ir_core_executable=False,
        native_executable=False,
        contains_path_predicate=contains_path,
        contains_state_guard=contains_guard,
        contains_aux_state=bool(aux_by_name),
        contains_compound_effect=contains_compound,
        contains_postcondition=contains_post,
    )
    ir = CompiledSemanticIR(
        ruleset_fingerprint=legacy.ruleset_fingerprint,
        geometry_metadata=build_geometry_metadata(legacy),
        patterns=tuple(patterns),
        aux_slots=compiled_slots,
        capabilities=capabilities,
    )
    errors = validate_ir(ir)
    if errors:
        raise RuleValidationError(
            [ValidationIssue("IR_INVALID", "ir", "; ".join(errors))]
        )
    return CompiledSemanticRuleset(ir=ir, _legacy_compiled=legacy)
