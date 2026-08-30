"""RuleSet compilation: validation plus precomputed movement tables.

The compiler never rejects rules because they are "unfun"; it only checks
that the rules are complete, self-consistent and executable.  Symmetry,
inventory balance and aesthetics are Generator concerns.
"""

from __future__ import annotations

from dataclasses import replace
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
    if ruleset.repetition_policy not in ("draw", "continuous_check_loss"):
        issues.append(ValidationIssue("REPETITION_POLICY_UNSUPPORTED", "repetition_policy", "unsupported repetition policy"))
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
        repetition_policy=ruleset.repetition_policy,
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


def _geometry_paths_from_atom(
    compiled: CompiledRuleSet, tid: str, atom_index: int
) -> dict[str, dict[int, tuple[int, ...]]]:
    """Canonical per-(owner, source) ordered paths for a legacy atom,
    projected from the single compiler lowering (the same tables the legacy
    Core uses)."""
    n = compiled.board_size
    out: dict[str, dict[int, tuple[int, ...]]] = {}
    for owner in (0, 1):
        per_source: dict[int, tuple[int, ...]] = {}
        for idx in range(n * n):
            leap = compiled.leap_targets[tid][owner][idx][atom_index]
            ray = compiled.ray_paths[tid][owner][idx][atom_index]
            if leap:
                per_source[idx] = (leap[0].rank * n + leap[0].file,)
            elif ray:
                per_source[idx] = tuple(s.rank * n + s.file for s in ray)
            else:
                per_source[idx] = ()
        out[str(owner)] = per_source
    return out


def build_legacy_geometry_catalog(
    compiled: CompiledRuleSet,
) -> tuple[dict[str, Any], dict[tuple[str, int], str]]:
    """Deterministic geometry catalog for legacy movement atoms.

    geometry ids are allocated in (sorted type_id, atom_index) order; each
    geometry keeps its atom identity (``atom_source``) so no executor ever
    needs to re-read movement atoms.
    """
    from .ir import CompiledGeometry

    catalog: dict[str, CompiledGeometry] = {}
    legacy_ids: dict[tuple[str, int], str] = {}
    counter = 0
    for tid in sorted(compiled.types_by_id):
        pt = compiled.types_by_id[tid]
        for atom_index, atom in enumerate(pt.movement_atoms):
            gid = f"g{counter}"
            counter += 1
            is_ray = isinstance(atom, RayAtom)
            catalog[gid] = CompiledGeometry(
                geometry_id=gid,
                kind="ray" if is_ray else "leap",
                owner_relative=True,
                offset=None if is_ray else atom.offset,
                direction=atom.direction if is_ray else None,
                min_steps=1 if is_ray else None,
                max_steps=atom.max_steps if is_ray else None,
                atom_source=(tid, atom_index),
                paths=_geometry_paths_from_atom(compiled, tid, atom_index),
            )
            legacy_ids[(tid, atom_index)] = gid
    return catalog, legacy_ids


def _explicit_geometry_path(
    n: int, spec, owner: int, source: int
) -> tuple[int, ...]:
    """Ordered path for an explicit leap/ray spec (owner-relative canonical)."""
    from ..core.coordinates import Square, index_to_square, square_to_index

    src = index_to_square(source, n)
    if spec.kind == "leap":
        df, dr = spec.offset
        if owner == 1 and spec.owner_relative:
            df, dr = -df, -dr
        target = Square(src.file + df, src.rank + dr)
        if not (0 <= target.file < n and 0 <= target.rank < n):
            return ()
        return (square_to_index(target, n),)
    # ray
    df, dr = spec.direction
    if owner == 1 and spec.owner_relative:
        df, dr = -df, -dr
    cur = src
    path: list[int] = []
    max_steps = spec.max_steps if spec.max_steps is not None else n * n
    for step in range(1, max_steps + 1):
        nxt = Square(cur.file + df, cur.rank + dr)
        if not (0 <= nxt.file < n and 0 <= nxt.rank < n):
            break
        path.append(square_to_index(nxt, n))
        cur = nxt
    return tuple(path)


def _build_explicit_geometry(
    compiled: CompiledRuleSet, spec, gid: str
):
    from .ir import CompiledGeometry

    if spec.kind == "drop":
        return CompiledGeometry(geometry_id=gid, kind="drop")
    n = compiled.board_size
    paths: dict[str, dict[int, tuple[int, ...]]] = {}
    for owner in (0, 1):
        per_source = {idx: _explicit_geometry_path(n, spec, owner, idx) for idx in range(n * n)}
        paths[str(owner)] = per_source
    return CompiledGeometry(
        geometry_id=gid,
        kind=spec.kind,
        owner_relative=spec.owner_relative,
        offset=spec.offset,
        direction=spec.direction,
        min_steps=spec.min_steps,
        max_steps=spec.max_steps,
        paths=paths,
    )


def lower_legacy_to_ir(compiled: CompiledRuleSet):
    """Lower an existing legacy compiled ruleset into the v2 production IR."""
    from .ir import (
        CompiledEffect,
        CompiledGeometry,
        CompiledInvariant,
        CompiledMovePattern,
        CompiledPathPredicate,
        CompiledSemanticIR,
        CompiledSquareRef,
        CompiledTargetPredicate,
        CompiledTypeRef,
        SemanticCapabilities,
    )

    geometry, legacy_ids = build_legacy_geometry_catalog(compiled)
    patterns: list[CompiledMovePattern] = []
    pattern_counter = 0
    for (tid, atom_index), gid in sorted(legacy_ids.items(), key=lambda kv: kv[1]):
        is_ray = geometry[gid].kind == "ray"
        path = (CompiledPathPredicate("path_clear"),) if is_ray else ()
        for family in ("quiet", "capture"):
            target = (
                CompiledTargetPredicate("target_empty")
                if family == "quiet"
                else CompiledTargetPredicate("target_enemy")
            )
            effects = (
                (
                    CompiledEffect(
                        "remove",
                        square_ref=CompiledSquareRef("target"),
                        disposition="capture_to_hand",
                        piece_owner="opponent",
                    ),
                    CompiledEffect(
                        "move",
                        from_ref=CompiledSquareRef("source"),
                        to_ref=CompiledSquareRef("target"),
                    ),
                )
                if family == "capture"
                else (
                    CompiledEffect(
                        "move",
                        from_ref=CompiledSquareRef("source"),
                        to_ref=CompiledSquareRef("target"),
                    ),
                )
            )
            patterns.append(
                CompiledMovePattern(
                    pattern_id=f"legacy_{pattern_counter:03d}",
                    name=f"legacy_{tid}_{family}_{atom_index}",
                    type_ids=(tid,),
                    geometry_ids=(gid,),
                    target=target,
                    path=path,
                    effects=effects,
                    invariants=(CompiledInvariant("own_anchor_safe"),),
                    promotion_mode="inherit_compiled_masks",
                    composition="augment",
                    cost_class="C1",
                    stratum="S3",
                )
            )
            pattern_counter += 1

    drop_gid = f"g{len(geometry)}"
    geometry[drop_gid] = CompiledGeometry(geometry_id=drop_gid, kind="drop")
    for tid in sorted(compiled.drop_allowed):
        patterns.append(
            CompiledMovePattern(
                pattern_id=f"legacy_{pattern_counter:03d}",
                name=f"legacy_{tid}_drop",
                type_ids=(tid,),
                geometry_ids=(drop_gid,),
                target=CompiledTargetPredicate("target_empty"),
                effects=(
                    CompiledEffect(
                        "remove_from_hand",
                        piece_type_ref=CompiledTypeRef("explicit", tid),
                    ),
                    CompiledEffect(
                        "place",
                        to_ref=CompiledSquareRef("target"),
                        piece_type_ref=CompiledTypeRef("explicit", tid),
                    ),
                ),
                invariants=(CompiledInvariant("own_anchor_safe"),),
                composition="augment",
                cost_class="C1",
                stratum="S3",
            )
        )
        pattern_counter += 1
    return CompiledSemanticIR(
        ir_version=2,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        geometry=geometry,
        patterns=tuple(patterns),
        capabilities=SemanticCapabilities(
            legacy_core_executable=True,
            new_ir_core_executable=False,
            native_executable=True,
        ),
    )


def compile_semantic_ir(compiled: CompiledRuleSet):
    """Public alias: lower a legacy compiled ruleset to the v2 production IR."""
    return lower_legacy_to_ir(compiled)


def _build_semantic_support(compiled: CompiledRuleSet):
    from .ir import CompiledSemanticSupport, SemanticTypeMetadata

    n = compiled.board_size
    board = compiled.initial_position.board
    rows = tuple(tuple(board[r * n : (r + 1) * n]) for r in range(n))
    type_metadata = {
        tid: SemanticTypeMetadata(
            type_id=tid,
            is_anchor=pt.is_anchor,
            is_promotable=pt.is_promotable,
            promotion_target_ids=tuple(pt.promotion_target_ids),
        )
        for tid, pt in compiled.types_by_id.items()
    }
    return CompiledSemanticSupport(
        board_size=n,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        initial_position=rows,
        type_metadata=type_metadata,
        drop_allowed=compiled.drop_allowed,
        promotion_allowed=compiled.promotion_allowed,
        promotion_forced=compiled.promotion_forced,
        empty_mobility=compiled.empty_mobility,
        repetition_limit=compiled.repetition_limit,
        repetition_policy=compiled.repetition_policy,
        max_ply=compiled.max_ply,
        stalemate_result=compiled.stalemate_result,
    )


def _resolve_square_ref(ref, slot_ids_by_name):
    from .ir import CompiledSquareRef

    return CompiledSquareRef(
        kind=ref.kind,
        square=ref.square,
        offset=ref.offset,
        owner_relative=ref.owner_relative,
        step=ref.step,
        slot_id=slot_ids_by_name.get(ref.slot_name) if ref.slot_name else None,
    )


def _resolve_type_ref(ref, type_ids):
    from .ir import CompiledTypeRef

    if ref.kind == "explicit" and ref.type_id not in type_ids:
        raise RuleValidationError(
            [ValidationIssue("SEMANTIC_TYPE_UNKNOWN", "type_ref", ref.type_id)]
        )
    return CompiledTypeRef(kind=ref.kind, type_id=ref.type_id)


def _resolve_spatial(sel, slot_ids_by_name, zone_ids_by_set):
    from .ir import CompiledSpatialSelector

    zone_id = zone_ids_by_set.get(tuple(sorted(sel.zone_squares))) if sel.kind == "zone" else None
    return CompiledSpatialSelector(
        kind=sel.kind,
        refs=tuple(_resolve_square_ref(r, slot_ids_by_name) for r in sel.refs),
        zone_id=zone_id,
    )


def _pattern_components(pattern) -> list[str]:
    components = (
        ["geometry"] * len(pattern.geometry_ids)
        + [pattern.target.kind]
        + [pp.kind for pp in pattern.path]
        + ["state_guard"] * len(pattern.guards)
        + ["slot_guard"] * len(pattern.slot_guards)
        + [i.kind for i in pattern.invariants]
        + [pc.kind for pc in pattern.postconditions]
        + [e.kind for e in pattern.effects]
    )
    return components


def _assign_stratum_cost(pattern):
    from . import ir as ir_module
    from .schema import SEMANTIC_STRATA

    components = _pattern_components(pattern)
    stratum = max(SEMANTIC_STRATA.index(ir_module._component_stratum(c)) for c in components)
    cost = max(ir_module.COST_CLASSES.index(ir_module.cost_class_of(c)) for c in components)
    return SEMANTIC_STRATA[stratum], ir_module.COST_CLASSES[cost]


def compile_semantic_ruleset(ruleset: RuleSet | Mapping[str, Any]):
    """Compile a semantic-DSL RuleSet into the v2 production IR.

    The normalized pattern set is the final action template set
    (legacy - replaced + augment + replacements); an executor consumes only
    this IR and never the high-level RuleSet.  Capabilities remain
    fail-closed (nothing executes yet).
    """
    from . import ir as ir_module
    from .ir import (
        CompiledAuxSlot,
        CompiledEffect,
        CompiledGeometry,
        CompiledInvariant,
        CompiledMovePattern,
        CompiledPathPredicate,
        CompiledPostcondition,
        CompiledSemanticIR,
        CompiledSemanticRuleset,
        CompiledSlotGuard,
        CompiledSquareRef,
        CompiledStatePredicate,
        CompiledTargetPredicate,
        CompiledTransitionTrigger,
        CompiledTypeRef,
        CompiledZone,
        SemanticCapabilities,
        validate_executable_completeness,
        validate_ir,
    )
    from .schema import MAX_SEMANTIC_AUX_SLOTS, SEMANTIC_STRATA

    if not isinstance(ruleset, RuleSet):
        ruleset = ruleset_from_dict(ruleset)
    if not ruleset.semantic_actions:
        raise RuleValidationError(
            [ValidationIssue("NO_SEMANTIC_ACTIONS", "ruleset.semantic_actions", "empty")]
        )
    for action in ruleset.semantic_actions:
        for guard in action.state_guards:
            if guard.location == "hand":
                raise RuleValidationError(
                    [
                        ValidationIssue(
                            "HAND_PREDICATE_UNSUPPORTED",
                            f"ruleset.semantic_actions {action.name} state_guards",
                            "location=hand state predicates are fail-closed "
                            "in the B-2 reference executor (no hand-query "
                            "contract yet)",
                        )
                    ]
                )
    legacy = compile_ruleset(ruleset, allow_semantic_actions=True)
    type_ids = tuple(sorted(legacy.types_by_id))

    # --- geometry catalog: legacy atoms first, then explicit shapes.
    geometry, legacy_ids = build_legacy_geometry_catalog(legacy)
    drop_gid = f"g{len(geometry)}"
    geometry[drop_gid] = CompiledGeometry(geometry_id=drop_gid, kind="drop")
    next_gid = len(geometry)
    action_geometry_ids: dict[int, tuple[str, ...]] = {}
    for action_index, action in enumerate(ruleset.semantic_actions):
        spec = action.geometry
        if spec.kind == "legacy_atoms":
            gids = []
            for tid in action.type_ids:
                if tid not in legacy.types_by_id:
                    raise RuleValidationError(
                        [ValidationIssue("SEMANTIC_TYPE_UNKNOWN", "type_ids", tid)]
                    )
                pt = legacy.types_by_id[tid]
                for atom_index, atom in enumerate(pt.movement_atoms):
                    is_ray = isinstance(atom, RayAtom)
                    if spec.atom_kind is None or (
                        (spec.atom_kind == "ray") == is_ray
                    ):
                        gids.append(legacy_ids[(tid, atom_index)])
            if not gids:
                raise RuleValidationError(
                    [
                        ValidationIssue(
                            "SEMANTIC_GEOMETRY_NO_ATOMS",
                            f"semantic_actions[{action_index}].geometry",
                            "legacy_atoms matched no atoms",
                        )
                    ]
                )
            action_geometry_ids[action_index] = tuple(sorted(gids))
        else:
            gid = f"g{next_gid}"
            next_gid += 1
            geometry[gid] = _build_explicit_geometry(legacy, spec, gid)
            action_geometry_ids[action_index] = (gid,)

    # --- zones (deterministic: sorted square sets).
    zone_sets: list[tuple[tuple[int, int], ...]] = []
    zone_ids_by_set: dict[tuple[tuple[int, int], ...], str] = {}
    for action in ruleset.semantic_actions:
        for guard in action.state_guards:
            if guard.spatial.kind != "zone":
                continue
            key = tuple(sorted(guard.spatial.zone_squares))
            if key not in zone_ids_by_set:
                zone_ids_by_set[key] = f"z{len(zone_sets)}"
                zone_sets.append(key)
    zones = {
        zid: CompiledZone(zid, tuple(sq[1] * legacy.board_size + sq[0] for sq in squares))
        for squares, zid in sorted(zone_ids_by_set.items(), key=lambda kv: kv[1])
    }

    # --- aux slots (deterministic: sorted by name).
    aux_by_name: dict[str, Any] = {}
    for action in ruleset.semantic_actions:
        for aux in action.aux_state:
            if aux.name in aux_by_name and aux_by_name[aux.name] != aux:
                raise RuleValidationError(
                    [ValidationIssue("AUX_SLOT_CONFLICT", "aux_state", aux.name)]
                )
            aux_by_name.setdefault(aux.name, aux)
    if len(aux_by_name) > MAX_SEMANTIC_AUX_SLOTS:
        raise RuleValidationError(
            [ValidationIssue("AUX_SLOTS_TOO_MANY", "aux_state", str(len(aux_by_name)))]
        )
    slot_ids_by_name = {name: i for i, name in enumerate(sorted(aux_by_name))}
    compiled_slots = []
    for name in sorted(aux_by_name):
        aux = aux_by_name[name]
        if aux.value_kind == "bool":
            initial = 1 if aux.initial == 1 else 0
        else:
            initial = aux.initial  # square tuple or None
        compiled_slots.append(
            CompiledAuxSlot(
                slot_id=slot_ids_by_name[name],
                value_kind=aux.value_kind,
                scope=aux.scope,
                lifetime=aux.lifetime,
                initial=initial,
            )
        )
    compiled_slots = tuple(compiled_slots)

    # --- legacy baseline patterns (for composition).
    legacy_ir = lower_legacy_to_ir(legacy)
    legacy_patterns = list(legacy_ir.patterns)
    replaced: set[str] = set()
    semantic_patterns: list[CompiledMovePattern] = []
    contains_path = contains_guard = contains_compound = contains_post = contains_trigger = False

    for action_index, action in enumerate(ruleset.semantic_actions):
        for tid in action.type_ids:
            if tid not in legacy.types_by_id:
                raise RuleValidationError(
                    [ValidationIssue("SEMANTIC_TYPE_UNKNOWN", "type_ids", tid)]
                )
        if action.path_constraints:
            contains_path = True
        if action.state_guards or action.slot_guards:
            contains_guard = True
        if len(action.effects) > 1:
            contains_compound = True
        if action.postconditions:
            contains_post = True
        if action.triggers:
            contains_trigger = True

        gids = action_geometry_ids[action_index]
        # --- composition resolution.
        composition = action.composition
        replaced_ids: tuple[str, ...] = ()
        if composition == "replace_legacy":
            selector = action.replace_selector
            if selector is None:
                raise RuleValidationError(
                    [ValidationIssue("REPLACE_NO_SELECTOR", "replace_selector", action.name)]
                )
            def _family_ok(gid: str) -> bool:
                kind = geometry[gid].kind
                if selector.action_family == "drop":
                    return kind == "drop"
                return kind in ("leap", "ray")

            matched = [
                p.pattern_id
                for p in legacy_patterns
                if set(p.type_ids) & set(selector.type_ids)
                and any(_family_ok(g) for g in p.geometry_ids)
                and p.target.kind == f"target_{selector.target_relation}"
                and (
                    selector.geometry_kind is None
                    or any(geometry[g].kind == selector.geometry_kind for g in p.geometry_ids)
                )
            ]
            matched = list(dict.fromkeys(matched))
            if not matched and not selector.replace_all_matching:
                raise RuleValidationError(
                    [
                        ValidationIssue(
                            "REPLACE_ZERO_MATCH",
                            f"semantic_actions[{action_index}]",
                            "replace selector matched no legacy pattern",
                        )
                    ]
                )
            if len(matched) > 1 and not selector.replace_all_matching:
                raise RuleValidationError(
                    [
                        ValidationIssue(
                            "REPLACE_AMBIGUOUS",
                            f"semantic_actions[{action_index}]",
                            f"replace selector matched {len(matched)} patterns; "
                            "set replace_all_matching=True",
                        )
                    ]
                )
            replaced.update(matched)
            replaced_ids = tuple(matched)

        # --- effects.
        effects = []
        for effect in action.effects:
            slot_id = slot_ids_by_name.get(effect.slot_name) if effect.slot_name else None
            if effect.slot_name and slot_id is None:
                raise RuleValidationError(
                    [ValidationIssue("EFFECT_SLOT_UNKNOWN", "effects", effect.slot_name)]
                )
            from_ref = (
                _resolve_square_ref(effect.from_ref, slot_ids_by_name)
                if effect.from_ref
                else None
            )
            to_ref = (
                _resolve_square_ref(effect.to_ref, slot_ids_by_name)
                if effect.to_ref
                else None
            )
            square_ref = (
                _resolve_square_ref(effect.square_ref, slot_ids_by_name)
                if effect.square_ref
                else None
            )
            piece_type_ref = (
                _resolve_type_ref(effect.piece_type_ref, type_ids)
                if effect.piece_type_ref
                else None
            )
            type_ref = (
                _resolve_type_ref(effect.type_ref, type_ids)
                if effect.type_ref
                else None
            )
            disposition = effect.disposition
            if effect.kind == "remove" and disposition is None:
                disposition = "capture_to_hand"
            effects.append(
                CompiledEffect(
                    kind=effect.kind,
                    from_ref=from_ref,
                    to_ref=to_ref,
                    square_ref=square_ref,
                    piece_owner=effect.piece_owner,
                    piece_type_ref=piece_type_ref,
                    disposition=disposition,
                    slot_id=slot_id,
                    type_ref=type_ref,
                    count=effect.count,
                    value=effect.value,
                )
            )

        # --- guards / slot guards / path / invariants / postconditions.
        guards = tuple(
            CompiledStatePredicate(
                aggregation=g.aggregation,
                owner=g.owner,
                type_ref=_resolve_type_ref(g.type_ref, type_ids),
                compare_field=g.compare_field,
                promoted=g.promoted,
                location=g.location,
                spatial=_resolve_spatial(g.spatial, slot_ids_by_name, zone_ids_by_set),
                comparison=g.comparison,
                value=g.value,
                subject_ref=(
                    _resolve_square_ref(g.subject_ref, slot_ids_by_name)
                    if g.subject_ref is not None
                    else None
                ),
            )
            for g in action.state_guards
        )
        slot_guards = []
        for sg in action.slot_guards:
            if sg.slot_name not in slot_ids_by_name:
                raise RuleValidationError(
                    [ValidationIssue("SLOT_GUARD_UNKNOWN", "slot_guards", sg.slot_name)]
                )
            slot_guards.append(
                CompiledSlotGuard(
                    slot_id=slot_ids_by_name[sg.slot_name],
                    comparison=sg.comparison,
                    value=sg.value,
                    square_ref=(
                        _resolve_square_ref(sg.square_ref, slot_ids_by_name)
                        if sg.square_ref
                        else None
                    ),
                )
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
            CompiledInvariant(
                i.kind,
                tuple(_resolve_square_ref(r, slot_ids_by_name) for r in i.square_refs),
            )
            for i in action.invariants
        )
        postconditions = tuple(
            CompiledPostcondition(p.kind, p.max_stratum) for p in action.postconditions
        )

        pattern = CompiledMovePattern(
            pattern_id=f"sem_{action_index:02d}_{action.name}",
            name=action.name,
            type_ids=action.type_ids,
            geometry_ids=gids,
            target=CompiledTargetPredicate(f"target_{action.target_relation}"),
            path=path,
            guards=guards,
            slot_guards=tuple(slot_guards),
            effects=tuple(effects),
            invariants=invariants,
            postconditions=postconditions,
            promotion_mode=action.promotion_mode,
            explicit_promotion_type=action.explicit_promotion_type,
            composition=composition,
            replaced_pattern_ids=replaced_ids,
            cost_class="C1",
            stratum="S0",
        )
        stratum, cost = _assign_stratum_cost(pattern)
        pattern = CompiledMovePattern(
            pattern_id=pattern.pattern_id,
            name=pattern.name,
            type_ids=pattern.type_ids,
            geometry_ids=pattern.geometry_ids,
            target=pattern.target,
            path=pattern.path,
            guards=pattern.guards,
            slot_guards=pattern.slot_guards,
            effects=pattern.effects,
            invariants=pattern.invariants,
            postconditions=pattern.postconditions,
            promotion_mode=pattern.promotion_mode,
            explicit_promotion_type=pattern.explicit_promotion_type,
            composition=pattern.composition,
            replaced_pattern_ids=pattern.replaced_pattern_ids,
            cost_class=cost,
            stratum=stratum,
        )
        semantic_patterns.append(pattern)

    triggers = tuple(
        CompiledTransitionTrigger(
            slot_id=slot_ids_by_name[t.slot_name],
            event=t.event,
            square_ref=_resolve_square_ref(t.square_ref, slot_ids_by_name),
            owner=t.owner,
        )
        for action in ruleset.semantic_actions
        for t in action.triggers
    )
    for trigger in triggers:
        if trigger.slot_id not in slot_ids_by_name.values():
            raise RuleValidationError(
                [ValidationIssue("TRIGGER_SLOT_UNKNOWN", "triggers", str(trigger.slot_id))]
            )

    normalized = [
        p for p in legacy_patterns if p.pattern_id not in replaced
    ] + semantic_patterns
    capabilities = SemanticCapabilities(
        legacy_core_executable=False,
        # Phase 1.9B-3: the Python reference executor implements the bounded
        # S4 post-action probe, and IR/schema validation already rejects any
        # unsupported postcondition kind or probe stratum > S3 at compile
        # time.  A successful compile therefore implies every emitted
        # postcondition is B-3 supported, so the S4 fail-closed gate is
        # retired (ADR-016 section 13; spec R2 supersession).
        new_ir_core_executable=True,
        native_executable=False,
        contains_path_predicate=contains_path,
        contains_state_guard=contains_guard,
        contains_aux_state=bool(aux_by_name),
        contains_compound_effect=contains_compound,
        contains_postcondition=contains_post,
        contains_transition_trigger=contains_trigger,
    )
    ir = CompiledSemanticIR(
        ir_version=2,
        ruleset_fingerprint=legacy.ruleset_fingerprint,
        geometry=geometry,
        zones=zones,
        patterns=tuple(normalized),
        aux_slots=compiled_slots,
        triggers=triggers,
        capabilities=capabilities,
    )
    errors = validate_ir(ir)
    errors.extend(validate_executable_completeness(ir, type_ids))
    if errors:
        raise RuleValidationError(
            [ValidationIssue("IR_INVALID", "ir", "; ".join(errors))]
        )
    support = _build_semantic_support(legacy)
    # Native execution is a per-ruleset capability, derived from the exact
    # lowered payload rather than a global promise.  Any lowering/shape
    # failure remains fail-closed while Python IR compilation stays usable.
    try:
        from ..native.compiler import build_semantic_compile_payload

        _, native_report = build_semantic_compile_payload(
            CompiledSemanticRuleset(ir=ir, _legacy_compiled=legacy, support=support)
        )
        if native_report.native_executable:
            ir = replace(
                ir,
                capabilities=replace(ir.capabilities, native_executable=True),
            )
    except Exception:
        pass
    return CompiledSemanticRuleset(ir=ir, _legacy_compiled=legacy, support=support)
