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
            if cell.owner not in (0, 1):
                issues.append(ValidationIssue("ILLEGAL_OWNER", f"{path}.owner", f"owner must be 0 or 1, got {cell.owner!r}"))
            if cell.base_type_id not in type_ids:
                issues.append(ValidationIssue("CELL_TYPE_NOT_FOUND", f"{path}.base_type_id", f"base type {cell.base_type_id!r} is not a defined type"))
                continue
            base = types_by_id[cell.base_type_id]
            if base.is_anchor:
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


def compile_ruleset(rule_definition: RuleSet | Mapping[str, Any]) -> CompiledRuleSet:
    """Validate and compile a RuleSet (or its JSON dict form)."""
    ruleset = rule_definition if isinstance(rule_definition, RuleSet) else ruleset_from_dict(rule_definition)

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
