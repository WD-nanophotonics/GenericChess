"""RuleSet compilation: validation plus precomputed movement tables.

The compiler never rejects rules because they are "unfun"; it only checks
that the rules are complete, self-consistent and executable.  Symmetry,
inventory balance and aesthetics are Generator concerns.
"""

from __future__ import annotations

from dataclasses import replace
from math import gcd
from types import MappingProxyType
from typing import Any, Mapping

from ..core.attacks import is_in_check
from ..core.coordinates import (
    BoardShape,
    Square,
    index_to_square,
    is_forward,
    square_to_index,
)
from ..core.movement import LeapAtom, RayAtom, MovementAtom
from ..core.movegen import legal_actions_from_position
from ..core.pieces import Piece, PieceType
from ..core.position import Hands, Position
from .compiled import (
    CompiledAutomaticAdjudication,
    CompiledConsecutiveActionAdjudication,
    CompiledGeometryCarrier,
    CompiledNoProgressDraw,
    CompiledRepeatedCycleTargetCondition,
    CompiledRuleSet,
)
from .schema import (
    AUTOMATIC_ADJUDICATION_OUTCOMES,
    AUTOMATIC_ADJUDICATION_POLICIES,
    CONSECUTIVE_ACTION_CLASSES,
    CONSECUTIVE_ACTION_OUTCOMES,
    DISPOSITIONS,
    RuleSet,
    RuleConsecutiveActionAdjudication,
    RuleInitialSetupOption,
    RuleNoProgressDraw,
    RuleRepeatedCycleTargetCondition,
    compute_fingerprint,
    ruleset_from_dict,
)
from .serialization import deserialize_ruleset, serialize_ruleset
from .validation import RuleValidationError, ValidationIssue


def _is_forward_target(sq: Square, target: Square, player: int) -> bool:
    return is_forward(sq, target, player)


def _build_tables(ruleset: RuleSet) -> dict[str, Any]:
    """Precompute all geometry tables on an empty board."""
    shape = ruleset.board_shape
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
            for idx in range(shape.area):
                sq = index_to_square(idx, shape)
                atom_leap: list[tuple[Square, ...]] = []
                atom_ray: list[tuple[Square, ...]] = []
                seen: set[Square] = set()
                mob: list[Square] = []
                for atom in pt.movement_atoms:
                    targets = _atom_targets(shape, player, sq, atom)
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
    n: int | BoardShape, player: int, square: Square, atom: MovementAtom
) -> tuple[Square, ...]:
    shape = n if isinstance(n, BoardShape) else BoardShape(n, n)
    if isinstance(atom, LeapAtom):
        df, dr = atom.offset
        if player == 1:
            df, dr = -df, -dr
        nf, nr = square.file + df, square.rank + dr
        if 0 <= nf < shape.width and 0 <= nr < shape.height:
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
        if not (0 <= nf < shape.width and 0 <= nr < shape.height):
            break
        nxt = Square(nf, nr)
        path.append(nxt)
        cur = nxt
        steps += 1
    return tuple(path)


def _basic_validation(ruleset: RuleSet) -> list[ValidationIssue]:
    """Structural validation that does not need compiled tables."""
    issues: list[ValidationIssue] = []
    shape = ruleset.board_shape

    if not isinstance(ruleset.pass_enabled, bool):
        issues.append(
            ValidationIssue("PASS_POLICY_INVALID", "pass_enabled", "expected a boolean")
        )

    if shape.width < 3 or shape.height < 3:
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
    if len(rows) != shape.height or any(len(row) != shape.width for row in rows):
        issues.append(ValidationIssue("INITIAL_POSITION_BAD_DIMENSIONS", "initial_position", f"initial_position must be {shape.height} rows of {shape.width} cells"))

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

    if not isinstance(ruleset.initial_setup_options, tuple):
        issues.append(
            ValidationIssue(
                "INITIAL_SETUP_OPTIONS_INVALID",
                "initial_setup_options",
                "must be an immutable tuple",
            )
        )
        setup_options = ()
    else:
        setup_options = ruleset.initial_setup_options
    setup_keys: set[str] = set()
    seen_setup_positions = [ruleset.initial_position]
    default_inventory = tuple(sorted(
        (
            (p.owner, p.base_type_id, p.current_type_id, p.promoted)
            for row in ruleset.initial_position
            for p in row
            if isinstance(p, Piece)
        ),
        key=repr,
    ))
    for index, option in enumerate(setup_options):
        option_path = f"initial_setup_options[{index}]"
        if not isinstance(option, RuleInitialSetupOption):
            issues.append(
                ValidationIssue(
                    "INITIAL_SETUP_OPTION_INVALID", option_path,
                    "expected a RuleInitialSetupOption",
                )
            )
            continue
        key = option.setup_key
        if not isinstance(key, str) or not key or key.strip() != key:
            issues.append(
                ValidationIssue(
                    "INITIAL_SETUP_KEY_INVALID", f"{option_path}.setup_key",
                    "setup key must be a non-empty, trimmed string",
                )
            )
        elif key in setup_keys:
            issues.append(
                ValidationIssue(
                    "INITIAL_SETUP_KEY_DUPLICATE", f"{option_path}.setup_key",
                    f"duplicate setup key {key!r}",
                )
            )
        else:
            setup_keys.add(key)
        if not isinstance(option.position, tuple) or any(
            not isinstance(row, tuple) for row in option.position
        ):
            issues.append(
                ValidationIssue(
                    "INITIAL_SETUP_POSITION_INVALID", f"{option_path}.position",
                    "position must be an immutable tuple of rows",
                )
            )
            continue
        if any(
            cell is not None and not isinstance(cell, Piece)
            for row in option.position
            for cell in row
        ):
            issues.append(
                ValidationIssue(
                    "INITIAL_SETUP_POSITION_INVALID", f"{option_path}.position",
                    "each cell must be a Piece or None",
                )
            )
            continue
        option_inventory = tuple(sorted(
            (
                (p.owner, p.base_type_id, p.current_type_id, p.promoted)
                for row in option.position
                for p in row
                if p is not None
            ),
            key=repr,
        ))
        if option_inventory != default_inventory:
            issues.append(
                ValidationIssue(
                    "INITIAL_SETUP_INVENTORY_MISMATCH", f"{option_path}.position",
                    "setup options must preserve the default piece inventory",
                )
            )
        if any(option.position == existing for existing in seen_setup_positions):
            issues.append(
                ValidationIssue(
                    "INITIAL_SETUP_POSITION_DUPLICATE", f"{option_path}.position",
                    "setup position duplicates another declared position",
                )
            )
        else:
            seen_setup_positions.append(option.position)
        candidate = replace(
            ruleset, initial_position=option.position, initial_setup_options=()
        )
        for candidate_issue in _basic_validation(candidate):
            if candidate_issue.path == "initial_position" or candidate_issue.path.startswith(
                "initial_position["
            ):
                path_suffix = candidate_issue.path[len("initial_position"):]
                issues.append(
                    ValidationIssue(
                        candidate_issue.code,
                        f"{option_path}{path_suffix}",
                        candidate_issue.message,
                    )
                )

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
            if len(mask) != shape.area or not all(isinstance(b, bool) for b in mask):
                issues.append(ValidationIssue("DROP_MASK_BAD_SHAPE", f"drop_allowed[{tid}][{player}]", f"drop mask must be {shape.area} booleans"))

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
                        if not (0 <= fsq.file < shape.width and 0 <= fsq.rank < shape.height and 0 <= tsq.file < shape.width and 0 <= tsq.rank < shape.height):
                            issues.append(ValidationIssue("PROMOTION_MASK_OUT_OF_BOUNDS", f"{path}[{player}]", f"promotion pair ({fsq}, {tsq}) is out of bounds"))
                else:
                    for sq in entries:
                        if not (0 <= sq.file < shape.width and 0 <= sq.rank < shape.height):
                            issues.append(ValidationIssue("PROMOTION_MASK_OUT_OF_BOUNDS", f"{path}[{player}]", f"forced square {sq} is out of bounds"))

    if not isinstance(ruleset.repetition_limit, int) or ruleset.repetition_limit < 1:
        issues.append(ValidationIssue("REPETITION_LIMIT_INVALID", "repetition_limit", "repetition_limit must be a positive integer"))
    if ruleset.repetition_policy not in ("draw", "continuous_check_loss"):
        issues.append(ValidationIssue("REPETITION_POLICY_UNSUPPORTED", "repetition_policy", "unsupported repetition policy"))
    if not isinstance(ruleset.max_ply, int) or ruleset.max_ply < 1:
        issues.append(ValidationIssue("MAX_PLY_INVALID", "max_ply", "max_ply must be a positive integer"))
    if ruleset.stalemate_result not in ("draw", "loss"):
        issues.append(ValidationIssue("STALEMATE_RESULT_INVALID", "stalemate_result", "expected 'draw' or 'loss'"))
    if ruleset.capture_disposition not in DISPOSITIONS:
        issues.append(
            ValidationIssue(
                "CAPTURE_DISPOSITION_INVALID",
                "capture_disposition",
                f"expected one of {DISPOSITIONS}, got {ruleset.capture_disposition!r}",
            )
        )

    return issues


def _build_initial_position(
    ruleset: RuleSet,
    fingerprint: str,
    rows: tuple[tuple[Piece | None, ...], ...] | None = None,
) -> Position:
    rows = ruleset.initial_position if rows is None else rows
    flat = tuple(cell for row in rows for cell in row)
    return Position(
        board=flat,
        hands=(Hands.empty(), Hands.empty()),
        side_to_move=0,
        ruleset_fingerprint=fingerprint,
    )


def _build_initial_setup_positions(ruleset: RuleSet, fingerprint: str):
    return MappingProxyType(
        {
            option.setup_key: _build_initial_position(
                ruleset, fingerprint, option.position
            )
            for option in ruleset.initial_setup_options
        }
    )


def _compile_geometry_carrier(
    rule_definition: RuleSet | Mapping[str, Any],
) -> CompiledGeometryCarrier:
    """Build immutable shape/geometry data without enabling position execution.

    This private boundary intentionally runs structural validation and table
    lowering only. It never calls attack, move-generation, or legal-position
    validation code.
    """
    ruleset = (
        rule_definition
        if isinstance(rule_definition, RuleSet)
        else ruleset_from_dict(rule_definition)
    )
    issues = _basic_validation(ruleset)
    if issues:
        raise RuleValidationError(issues)
    shape = ruleset.board_shape
    fingerprint = compute_fingerprint(ruleset)
    position = Position(
        board=tuple(cell for row in ruleset.initial_position for cell in row),
        ruleset_fingerprint=fingerprint,
        board_width=shape.width,
        board_height=shape.height,
    )
    setup_positions = MappingProxyType(
        {
            option.setup_key: option.position
            for option in ruleset.initial_setup_options
        }
    )
    tables = _build_tables(ruleset)
    return CompiledGeometryCarrier(
        ruleset_fingerprint=fingerprint,
        board_shape=shape,
        types_by_id=MappingProxyType({pt.type_id: pt for pt in ruleset.piece_types}),
        initial_position=position,
        initial_setup_positions=setup_positions,
        leap_targets=MappingProxyType(tables["leap_targets"]),
        ray_paths=MappingProxyType(tables["ray_paths"]),
        empty_mobility=MappingProxyType(tables["empty_mobility"]),
        empty_forward_mobility=MappingProxyType(tables["empty_forward_mobility"]),
    )


def _position_validation(
    compiled: CompiledRuleSet, setup_key: str | None = None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    pos = (
        compiled.initial_position
        if setup_key is None
        else compiled.initial_setup_positions[setup_key]
    )
    path = (
        "initial_position"
        if setup_key is None
        else f"initial_setup_options[{setup_key}]"
    )
    for player in (0, 1):
        if is_in_check(pos, player, compiled):
            issues.append(
                ValidationIssue(
                    "INITIAL_ANCHOR_ATTACKED",
                    path,
                    f"player {player}'s anchor is attacked at the initial position",
                )
            )
    if not legal_actions_from_position(pos, compiled):
        issues.append(
            ValidationIssue(
                "INITIAL_NO_LEGAL_MOVE",
                path,
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
    return _compile_ruleset_baseline(
        rule_definition, allow_semantic_actions=allow_semantic_actions,
        validate_position=True,
    )


def _compile_ruleset_baseline(
    rule_definition: RuleSet | Mapping[str, Any], *,
    allow_semantic_actions: bool, validate_position: bool,
) -> CompiledRuleSet:
    """Build legacy metadata; semantic compilation owns its position checks."""
    ruleset = rule_definition if isinstance(rule_definition, RuleSet) else ruleset_from_dict(rule_definition)
    if (
        ruleset.board_width is not None
        and ruleset.board_height is not None
        and ruleset.board_width != ruleset.board_height
    ):
        raise RuleValidationError(
            [
                ValidationIssue(
                    "RECTANGULAR_EXECUTION_NOT_IN_A_STAGE",
                    "board_width",
                    "this stage supports rectangular schema and geometry only; position execution is not enabled",
                )
            ]
        )
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

    consecutive_action_adjudications = (
        _compile_consecutive_action_adjudications(ruleset)
    )
    repeated_cycle_target_conditions = (
        _compile_repeated_cycle_target_conditions(ruleset)
    )

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
        initial_setup_positions=_build_initial_setup_positions(ruleset, fingerprint),
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
        automatic_adjudications=_compile_automatic_adjudications(ruleset),
        consecutive_action_adjudications=consecutive_action_adjudications,
        declarations=_compile_declarations(ruleset, tuple(sorted(types_by_id))),
        capture_disposition=ruleset.capture_disposition,
        pass_enabled=ruleset.pass_enabled,
        repeated_cycle_target_conditions=repeated_cycle_target_conditions,
        no_progress_draw=_compile_no_progress_draw(
            ruleset, tuple(sorted(types_by_id))
        ),
    )

    if validate_position:
        issues = _position_validation(compiled)
        for setup_key in compiled.initial_setup_positions:
            issues.extend(_position_validation(compiled, setup_key))
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


def _compile_automatic_adjudications(ruleset: RuleSet):
    """Compile the small generic automatic-adjudication vocabulary."""
    definitions = ruleset.automatic_adjudications
    issues: list[ValidationIssue] = []
    ids = [item.adjudication_id for item in definitions]
    if len(definitions) > 1:
        issues.append(
            ValidationIssue(
                "AUTOMATIC_ADJUDICATION_MULTIPLE_UNSUPPORTED",
                "automatic_adjudications",
                "v0 supports at most one automatic adjudication",
            )
        )
    if len(set(ids)) != len(ids):
        issues.append(
            ValidationIssue(
                "AUTOMATIC_ADJUDICATION_ID_DUPLICATE",
                "automatic_adjudications",
                "adjudication IDs must be unique",
            )
        )
    output = []
    for index, item in enumerate(definitions):
        path = f"automatic_adjudications[{index}]"
        if not isinstance(item.adjudication_id, str) or not item.adjudication_id:
            issues.append(
                ValidationIssue(
                    "AUTOMATIC_ADJUDICATION_ID_INVALID",
                    f"{path}.adjudication_id",
                    "must be non-empty",
                )
            )
        if isinstance(item.trigger_ply, bool) or not isinstance(item.trigger_ply, int) or item.trigger_ply < 1:
            issues.append(
                ValidationIssue(
                    "AUTOMATIC_ADJUDICATION_PLY_INVALID",
                    f"{path}.trigger_ply",
                    "must be a positive integer",
                )
            )
        if item.outcome not in AUTOMATIC_ADJUDICATION_OUTCOMES:
            issues.append(
                ValidationIssue(
                    "AUTOMATIC_ADJUDICATION_OUTCOME_INVALID",
                    f"{path}.outcome",
                    repr(item.outcome),
                )
            )
        if item.continuation_policy not in AUTOMATIC_ADJUDICATION_POLICIES:
            issues.append(
                ValidationIssue(
                    "AUTOMATIC_ADJUDICATION_POLICY_INVALID",
                    f"{path}.continuation_policy",
                    repr(item.continuation_policy),
                )
            )
        output.append(
            CompiledAutomaticAdjudication(
                adjudication_id=item.adjudication_id,
                trigger_ply=item.trigger_ply,
                outcome=item.outcome,
                continuation_policy=item.continuation_policy,
            )
        )
    if issues:
        raise RuleValidationError(issues)
    return tuple(output)


def _compile_consecutive_action_adjudications(ruleset: RuleSet):
    definitions = ruleset.consecutive_action_adjudications
    issues: list[ValidationIssue] = []
    if not isinstance(definitions, tuple):
        raise RuleValidationError(
            [
                ValidationIssue(
                    "CONSECUTIVE_ACTION_ADJUDICATIONS_INVALID",
                    "consecutive_action_adjudications",
                    "must be a tuple of policy definitions",
                )
            ]
        )
    if len(definitions) > 1:
        issues.append(
            ValidationIssue(
                "CONSECUTIVE_ACTION_ADJUDICATION_MULTIPLE_UNSUPPORTED",
                "consecutive_action_adjudications",
                "the current executor supports one consecutive action-class policy",
            )
        )
    output = []
    for index, item in enumerate(definitions):
        path = f"consecutive_action_adjudications[{index}]"
        if not isinstance(item, RuleConsecutiveActionAdjudication):
            issues.append(
                ValidationIssue(
                    "CONSECUTIVE_ACTION_ADJUDICATION_INVALID",
                    path,
                    "expected a RuleConsecutiveActionAdjudication",
                )
            )
            continue
        if item.action_class not in CONSECUTIVE_ACTION_CLASSES:
            issues.append(
                ValidationIssue(
                    "CONSECUTIVE_ACTION_CLASS_UNSUPPORTED",
                    f"{path}.action_class",
                    repr(item.action_class),
                )
            )
        elif item.action_class == "pass" and not ruleset.pass_enabled:
            issues.append(
                ValidationIssue(
                    "CONSECUTIVE_ACTION_CLASS_DISABLED",
                    f"{path}.action_class",
                    "pass must be enabled before it can be adjudicated",
                )
            )
        if (
            isinstance(item.threshold, bool)
            or not isinstance(item.threshold, int)
            or item.threshold < 1
        ):
            issues.append(
                ValidationIssue(
                    "CONSECUTIVE_ACTION_THRESHOLD_INVALID",
                    f"{path}.threshold",
                    "threshold must be a positive integer",
                )
            )
        if item.outcome not in CONSECUTIVE_ACTION_OUTCOMES:
            issues.append(
                ValidationIssue(
                    "CONSECUTIVE_ACTION_OUTCOME_INVALID",
                    f"{path}.outcome",
                    repr(item.outcome),
                )
            )
        output.append(
            CompiledConsecutiveActionAdjudication(
                action_class=item.action_class,
                threshold=item.threshold,
                outcome=item.outcome,
            )
        )
    if issues:
        raise RuleValidationError(issues)
    return tuple(output)


def _compile_no_progress_draw(ruleset: RuleSet, type_ids):
    item = ruleset.no_progress_draw
    if item is None:
        return None
    issues = []
    if not isinstance(item, RuleNoProgressDraw):
        raise RuleValidationError([
            ValidationIssue("NO_PROGRESS_RULE_INVALID", "no_progress_draw", "expected RuleNoProgressDraw")
        ])
    if isinstance(item.threshold_plies, bool) or not isinstance(item.threshold_plies, int) or item.threshold_plies < 1:
        issues.append(ValidationIssue("NO_PROGRESS_THRESHOLD_INVALID", "no_progress_draw.threshold_plies", "must be a positive integer"))
    if not isinstance(item.reset_on_capture, bool):
        issues.append(ValidationIssue("NO_PROGRESS_CAPTURE_RESET_INVALID", "no_progress_draw.reset_on_capture", "must be boolean"))
    if not isinstance(item.reset_mover_type_ids, tuple) or any(
        not isinstance(type_id, str) or not type_id
        for type_id in item.reset_mover_type_ids
    ):
        issues.append(ValidationIssue("NO_PROGRESS_RESET_TYPES_INVALID", "no_progress_draw.reset_mover_type_ids", "must be a tuple of unique piece type IDs"))
    else:
        if len(set(item.reset_mover_type_ids)) != len(item.reset_mover_type_ids):
            issues.append(ValidationIssue("NO_PROGRESS_RESET_TYPES_INVALID", "no_progress_draw.reset_mover_type_ids", "must not contain duplicate piece type IDs"))
        for type_id in item.reset_mover_type_ids:
            if type_id not in type_ids:
                issues.append(ValidationIssue("NO_PROGRESS_RESET_TYPE_UNKNOWN", "no_progress_draw.reset_mover_type_ids", repr(type_id)))
    if item.outcome != "DRAW":
        issues.append(ValidationIssue("NO_PROGRESS_OUTCOME_UNSUPPORTED", "no_progress_draw.outcome", repr(item.outcome)))
    if issues:
        raise RuleValidationError(issues)
    return CompiledNoProgressDraw(
        item.threshold_plies,
        item.reset_on_capture,
        tuple(sorted(item.reset_mover_type_ids)),
        item.outcome,
    )


def _compile_repeated_cycle_target_conditions(ruleset: RuleSet):
    definitions = ruleset.repeated_cycle_target_conditions
    if not isinstance(definitions, tuple):
        raise RuleValidationError(
            [
                ValidationIssue(
                    "REPEATED_CYCLE_TARGET_CONDITIONS_INVALID",
                    "repeated_cycle_target_conditions",
                    "must be a tuple of condition definitions",
                )
            ]
        )
    output = []
    seen_actors = set()
    issues = []
    for index, item in enumerate(definitions):
        path = f"repeated_cycle_target_conditions[{index}]"
        if not isinstance(item, RuleRepeatedCycleTargetCondition):
            issues.append(
                ValidationIssue(
                    "REPEATED_CYCLE_TARGET_CONDITION_INVALID",
                    path,
                    "expected a RuleRepeatedCycleTargetCondition",
                )
            )
            continue
        if isinstance(item.actor, bool) or not isinstance(item.actor, int) or item.actor not in (0, 1):
            issues.append(
                ValidationIssue(
                    "REPEATED_CYCLE_TARGET_ACTOR_INVALID",
                    f"{path}.actor",
                    "actor must be 0 or 1",
                )
            )
            continue
        if item.outcome != "actor_loss":
            issues.append(
                ValidationIssue(
                    "REPEATED_CYCLE_TARGET_OUTCOME_INVALID",
                    f"{path}.outcome",
                    "outcome must be 'actor_loss'",
                )
            )
            continue
        if item.actor in seen_actors:
            issues.append(
                ValidationIssue(
                    "REPEATED_CYCLE_TARGET_ACTOR_DUPLICATE",
                    f"{path}.actor",
                    f"actor {item.actor} already has a condition",
                )
            )
            continue
        seen_actors.add(item.actor)
        output.append(
            CompiledRepeatedCycleTargetCondition(
                actor=item.actor, outcome=item.outcome
            )
        )
    if issues:
        raise RuleValidationError(issues)
    return tuple(output)


def compile_ruleset_for_execution(
    rule_definition: RuleSet | Mapping[str, Any],
):
    """Compile either legacy or semantic rules through the product boundary.

    The choice is made from the declarative RuleSet shape.  Semantic rules
    never fall back to the legacy compiler, and a semantic validation error is
    propagated unchanged.
    """
    ruleset = (
        rule_definition
        if isinstance(rule_definition, RuleSet)
        else ruleset_from_dict(rule_definition)
    )
    if ruleset.semantic_actions:
        from .execution import ExecutableSemanticRuleset

        compiled = compile_semantic_ruleset(ruleset)
        return ExecutableSemanticRuleset(
            ir=compiled.ir,
            _legacy_compiled=compiled._legacy_compiled,
            support=compiled.support,
        )
    return compile_ruleset(ruleset)


# ================================================================ semantic IR


def _geometry_board_shape(
    compiled: CompiledRuleSet | CompiledGeometryCarrier,
) -> BoardShape:
    if isinstance(compiled, CompiledGeometryCarrier):
        return compiled.board_shape
    return BoardShape(compiled.board_size, compiled.board_size)


def build_geometry_metadata(
    compiled: CompiledRuleSet | CompiledGeometryCarrier,
) -> dict:
    """Canonical geometry lowering (Design A): per (type, owner, source)
    ordered leap targets and ray path segments, projected from the single
    compiler lowering that also feeds the legacy execution tables."""
    shape = _geometry_board_shape(compiled)
    width = shape.width
    out: dict[str, Any] = {
        "schema": "geometry_v1", "squares": shape.area, "types": {},
    }
    for tid, _pt in compiled.types_by_id.items():
        leaps: dict[str, Any] = {}
        rays: dict[str, Any] = {}
        for owner in (0, 1):
            owner_leaps: dict[int, list[list[int]]] = {}
            owner_rays: dict[int, list[list[int]]] = {}
            for idx in range(shape.area):
                owner_leaps[idx] = [
                    [sq.rank * width + sq.file for sq in atom_targets]
                    for atom_targets in compiled.leap_targets[tid][owner][idx]
                ]
                owner_rays[idx] = [
                    [sq.rank * width + sq.file for sq in path]
                    for path in compiled.ray_paths[tid][owner][idx]
                ]
            leaps[str(owner)] = owner_leaps
            rays[str(owner)] = owner_rays
        out["types"][tid] = {"leap_targets": leaps, "ray_paths": rays}
    return out


def _geometry_paths_from_atom(
    compiled: CompiledRuleSet | CompiledGeometryCarrier, tid: str, atom_index: int
) -> dict[str, dict[int, tuple[int, ...]]]:
    """Canonical per-(owner, source) ordered paths for a legacy atom,
    projected from the single compiler lowering (the same tables the legacy
    Core uses)."""
    shape = _geometry_board_shape(compiled)
    width = shape.width
    out: dict[str, dict[int, tuple[int, ...]]] = {}
    for owner in (0, 1):
        per_source: dict[int, tuple[int, ...]] = {}
        for idx in range(shape.area):
            leap = compiled.leap_targets[tid][owner][idx][atom_index]
            ray = compiled.ray_paths[tid][owner][idx][atom_index]
            if leap:
                per_source[idx] = (leap[0].rank * width + leap[0].file,)
            elif ray:
                per_source[idx] = tuple(s.rank * width + s.file for s in ray)
            else:
                per_source[idx] = ()
        out[str(owner)] = per_source
    return out


def build_legacy_geometry_catalog(
    compiled: CompiledRuleSet | CompiledGeometryCarrier,
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
    board_shape: int | BoardShape, spec, owner: int, source: int
) -> tuple[int, ...]:
    """Ordered path for an explicit leap/ray spec (owner-relative canonical)."""
    from ..core.coordinates import Square, index_to_square, square_to_index

    shape = (
        BoardShape(board_shape, board_shape)
        if isinstance(board_shape, int)
        else board_shape
    )
    src = index_to_square(source, shape)
    if spec.kind == "leap":
        df, dr = spec.offset
        if owner == 1 and spec.owner_relative:
            df, dr = -df, -dr
        target = Square(src.file + df, src.rank + dr)
        if not (0 <= target.file < shape.width and 0 <= target.rank < shape.height):
            return ()
        return (square_to_index(target, shape),)
    # ray
    df, dr = spec.direction
    if owner == 1 and spec.owner_relative:
        df, dr = -df, -dr
    cur = src
    path: list[int] = []
    max_steps = spec.max_steps if spec.max_steps is not None else shape.area
    for step in range(1, max_steps + 1):
        nxt = Square(cur.file + df, cur.rank + dr)
        if not (0 <= nxt.file < shape.width and 0 <= nxt.rank < shape.height):
            break
        path.append(square_to_index(nxt, shape))
        cur = nxt
    return tuple(path)


def _build_explicit_geometry(
    compiled: CompiledRuleSet | CompiledGeometryCarrier, spec, gid: str
):
    from .ir import CompiledGeometry

    if spec.kind == "drop":
        return CompiledGeometry(geometry_id=gid, kind="drop")
    shape = _geometry_board_shape(compiled)
    paths: dict[str, dict[int, tuple[int, ...]]] = {}
    for owner in (0, 1):
        per_source = {
            idx: _explicit_geometry_path(shape, spec, owner, idx)
            for idx in range(shape.area)
        }
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


def lower_legacy_to_ir(
    compiled: CompiledRuleSet | CompiledGeometryCarrier,
    ruleset: RuleSet | None = None,
):
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

    compile_only = isinstance(compiled, CompiledGeometryCarrier)
    if compile_only:
        if ruleset is None:
            raise ValueError("a RuleSet is required with the compile-only geometry carrier")
        if (
            ruleset.board_shape != compiled.board_shape
            or compute_fingerprint(ruleset) != compiled.ruleset_fingerprint
        ):
            raise ValueError("RuleSet does not match the compile-only geometry carrier")
        drop_allowed = ruleset.drop_allowed
        type_ids = tuple(sorted(compiled.types_by_id))
        automatic_adjudications = _compile_automatic_adjudications(ruleset)
        consecutive_action_adjudications = (
            _compile_consecutive_action_adjudications(ruleset)
        )
        repeated_cycle_target_conditions = (
            _compile_repeated_cycle_target_conditions(ruleset)
        )
        declarations = _compile_declarations(ruleset, type_ids)
        capture_disposition = ruleset.capture_disposition
    else:
        if ruleset is not None:
            raise ValueError("RuleSet must not be supplied with an executable compiled ruleset")
        drop_allowed = compiled.drop_allowed
        automatic_adjudications = compiled.automatic_adjudications
        consecutive_action_adjudications = compiled.consecutive_action_adjudications
        repeated_cycle_target_conditions = compiled.repeated_cycle_target_conditions
        declarations = compiled.declarations
        capture_disposition = compiled.capture_disposition

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
                        disposition=capture_disposition,
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
    for tid in sorted(drop_allowed):
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
        automatic_adjudications=automatic_adjudications,
        consecutive_action_adjudications=consecutive_action_adjudications,
        repeated_cycle_target_conditions=repeated_cycle_target_conditions,
        declarations=declarations,
        capabilities=SemanticCapabilities(
            legacy_core_executable=not compile_only,
            new_ir_core_executable=False,
            native_executable=not compile_only,
        ),
    )


def compile_semantic_ir(compiled: CompiledRuleSet):
    """Public alias: lower a legacy compiled ruleset to the v2 production IR."""
    return lower_legacy_to_ir(compiled)


def _build_semantic_support(
    compiled: CompiledRuleSet | CompiledGeometryCarrier,
    ruleset: RuleSet | None = None,
):
    from .ir import CompiledSemanticSupport, SemanticTypeMetadata

    if isinstance(compiled, CompiledGeometryCarrier):
        if ruleset is None:
            raise ValueError("a RuleSet is required with the compile-only geometry carrier")
        shape = compiled.board_shape
        if ruleset.board_shape != shape or compute_fingerprint(ruleset) != compiled.ruleset_fingerprint:
            raise ValueError("RuleSet does not match the compile-only geometry carrier")
        types_by_id = compiled.types_by_id
        drop_allowed = ruleset.drop_allowed
        promotion_allowed = ruleset.promotion_allowed
        promotion_forced = ruleset.promotion_forced
        repetition_limit = ruleset.repetition_limit
        repetition_policy = ruleset.repetition_policy
        pass_enabled = ruleset.pass_enabled
        max_ply = ruleset.max_ply
        stalemate_result = ruleset.stalemate_result
        automatic_adjudications = _compile_automatic_adjudications(ruleset)
        consecutive_action_adjudications = (
            _compile_consecutive_action_adjudications(ruleset)
        )
        no_progress_draw = _compile_no_progress_draw(
            ruleset, tuple(sorted(types_by_id))
        )
        initial_setup_options = compiled.initial_setup_positions
    else:
        if ruleset is not None:
            raise ValueError("RuleSet must not be supplied with an executable compiled ruleset")
        shape = BoardShape(compiled.board_size, compiled.board_size)
        types_by_id = compiled.types_by_id
        drop_allowed = compiled.drop_allowed
        promotion_allowed = compiled.promotion_allowed
        promotion_forced = compiled.promotion_forced
        repetition_limit = compiled.repetition_limit
        repetition_policy = compiled.repetition_policy
        pass_enabled = compiled.pass_enabled
        max_ply = compiled.max_ply
        stalemate_result = compiled.stalemate_result
        automatic_adjudications = compiled.automatic_adjudications
        consecutive_action_adjudications = compiled.consecutive_action_adjudications
        no_progress_draw = compiled.no_progress_draw
        initial_setup_options = {
            key: tuple(
                tuple(position.board[rank * shape.width:(rank + 1) * shape.width])
                for rank in range(shape.height)
            )
            for key, position in compiled.initial_setup_positions.items()
        }

    board = compiled.initial_position.board
    rows = tuple(
        tuple(board[rank * shape.width : (rank + 1) * shape.width])
        for rank in range(shape.height)
    )
    type_metadata = {
        tid: SemanticTypeMetadata(
            type_id=tid,
            is_anchor=pt.is_anchor,
            is_promotable=pt.is_promotable,
            promotion_target_ids=tuple(pt.promotion_target_ids),
        )
        for tid, pt in types_by_id.items()
    }
    return CompiledSemanticSupport(
        board_size=shape.width if shape.width == shape.height else None,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        initial_position=rows,
        initial_setup_options=initial_setup_options,
        type_metadata=type_metadata,
        drop_allowed=drop_allowed,
        promotion_allowed=promotion_allowed,
        promotion_forced=promotion_forced,
        empty_mobility=compiled.empty_mobility,
        repetition_limit=repetition_limit,
        repetition_policy=repetition_policy,
        max_ply=max_ply,
        stalemate_result=stalemate_result,
        automatic_adjudications=automatic_adjudications,
        board_width=None if shape.width == shape.height else shape.width,
        board_height=None if shape.width == shape.height else shape.height,
        pass_enabled=pass_enabled,
        consecutive_action_adjudications=consecutive_action_adjudications,
        no_progress_draw=no_progress_draw,
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


def _compile_declarations(ruleset: RuleSet, type_ids: tuple[str, ...]):
    """Lower action-independent declarations without retaining RuleSet objects."""
    from .ir import (
        CompiledDeclaration,
        CompiledDeclarationOutcomeBand,
        CompiledStatePredicate,
        CompiledWeightedMaterialMetric,
        CompiledZone,
    )
    from .schema import DECLARATION_OUTCOMES

    declarations = ruleset.declarations
    ids = [d.declaration_id for d in declarations]
    issues: list[ValidationIssue] = []
    if len(set(ids)) != len(ids):
        issues.append(ValidationIssue("DECLARATION_ID_DUPLICATE", "declarations", "declaration IDs must be unique"))
    type_set = set(type_ids)
    zone_sets: dict[tuple[tuple[int, int], ...], str] = {}
    shape = ruleset.board_shape

    def register_zone(spatial):
        if spatial is None or spatial.kind != "zone":
            return
        key = tuple(sorted(spatial.zone_squares))
        if key not in zone_sets:
            zone_sets[key] = f"dzone{len(zone_sets)}"
        for file, rank in key:
            if not (0 <= file < shape.width and 0 <= rank < shape.height):
                issues.append(ValidationIssue("DECLARATION_ZONE_BOUNDS", "declarations", str((file, rank))))

    for index, declaration in enumerate(declarations):
        path = f"declarations[{index}]"
        if not isinstance(declaration.declaration_id, str) or not declaration.declaration_id:
            issues.append(ValidationIssue("DECLARATION_ID_INVALID", f"{path}.declaration_id", "must be non-empty"))
        if declaration.owner not in (0, 1):
            issues.append(ValidationIssue("DECLARATION_OWNER_INVALID", f"{path}.owner", "must be 0 or 1"))
        if declaration.ply_limit is not None and declaration.ply_limit < 1:
            issues.append(ValidationIssue("DECLARATION_PLY_LIMIT_INVALID", f"{path}.ply_limit", "must be positive"))
        if declaration.failure_outcome not in DECLARATION_OUTCOMES:
            issues.append(ValidationIssue("DECLARATION_OUTCOME_INVALID", f"{path}.failure_outcome", declaration.failure_outcome))
        previous = None
        if declaration.outcome_bands and declaration.weighted_metric is None:
            issues.append(ValidationIssue("DECLARATION_BANDS_NO_METRIC", f"{path}.outcome_bands", "score thresholds require a weighted metric"))
        for bi, band in enumerate(declaration.outcome_bands):
            if band.outcome not in DECLARATION_OUTCOMES:
                issues.append(ValidationIssue("DECLARATION_OUTCOME_INVALID", f"{path}.outcome_bands[{bi}].outcome", band.outcome))
            if previous is not None and band.threshold >= previous:
                issues.append(ValidationIssue("DECLARATION_BANDS_NOT_DESCENDING", f"{path}.outcome_bands", "thresholds must be strictly descending"))
            previous = band.threshold
        for gi, guard in enumerate(declaration.state_guards):
            gpath = f"{path}.state_guards[{gi}]"
            if guard.location != "board":
                issues.append(ValidationIssue("DECLARATION_GUARD_LOCATION", gpath, "declaration guards support board only"))
            if guard.type_ref.kind not in ("explicit", "any"):
                issues.append(ValidationIssue("DECLARATION_GUARD_TYPE_BINDING", gpath, "action-bound type refs fail closed"))
            if guard.type_ref.kind == "explicit" and guard.type_ref.type_id not in type_set:
                issues.append(ValidationIssue("DECLARATION_TYPE_UNKNOWN", gpath, guard.type_ref.type_id or ""))
            refs = list(guard.spatial.refs)
            if guard.subject_ref is not None:
                refs.append(guard.subject_ref)
            for ref in refs:
                if ref.kind != "fixed":
                    issues.append(ValidationIssue("DECLARATION_SQUARE_REF_UNBOUND", gpath, f"unsupported action-bound ref {ref.kind!r}"))
            register_zone(guard.spatial)
        if declaration.weighted_metric is not None:
            metric = declaration.weighted_metric
            mpath = f"{path}.weighted_metric"
            if metric.compare_field not in ("base", "current"):
                issues.append(ValidationIssue("COMPARE_FIELD_INVALID", mpath, metric.compare_field))
            if metric.owner not in ("self", "opponent", "any"):
                issues.append(ValidationIssue("OWNER_INVALID", mpath, metric.owner))
            for tid, weight in metric.weights.items():
                if not isinstance(tid, str) or not tid:
                    issues.append(ValidationIssue("WEIGHT_TYPE_INVALID", mpath, str(tid)))
                if not isinstance(weight, int) or isinstance(weight, bool):
                    issues.append(ValidationIssue("WEIGHT_INVALID", f"{mpath}.weights", str(tid)))
                if tid not in type_set:
                    issues.append(ValidationIssue("DECLARATION_TYPE_UNKNOWN", f"{mpath}.weights", tid))
            if metric.spatial is not None:
                if metric.spatial.kind != "zone":
                    issues.append(ValidationIssue("DECLARATION_METRIC_SPATIAL", mpath, "only zone spatial filtering is supported"))
                for ref in metric.spatial.refs:
                    if ref.kind != "fixed":
                        issues.append(ValidationIssue("DECLARATION_SQUARE_REF_UNBOUND", mpath, f"unsupported action-bound ref {ref.kind!r}"))
                register_zone(metric.spatial)
    if issues:
        raise RuleValidationError(issues)

    zones = {
        zone_id: CompiledZone(
            zone_id,
            tuple(rank * shape.width + file for file, rank in squares),
        )
        for squares, zone_id in zone_sets.items()
    }
    out = []
    for declaration in declarations:
        guards = tuple(
            CompiledStatePredicate(
                aggregation=g.aggregation,
                owner=g.owner,
                type_ref=_resolve_type_ref(g.type_ref, type_ids),
                compare_field=g.compare_field,
                promoted=g.promoted,
                location=g.location,
                spatial=_resolve_spatial(g.spatial, {}, zone_sets),
                comparison=g.comparison,
                value=g.value,
                subject_ref=(
                    _resolve_square_ref(g.subject_ref, {})
                    if g.subject_ref is not None else None
                ),
            )
            for g in declaration.state_guards
        )
        metric = declaration.weighted_metric
        compiled_metric = None
        if metric is not None:
            compiled_metric = CompiledWeightedMaterialMetric(
                owner=metric.owner,
                compare_field=metric.compare_field,
                weights=tuple(sorted(metric.weights.items())),
                spatial=(
                    _resolve_spatial(metric.spatial, {}, zone_sets)
                    if metric.spatial is not None else None
                ),
                include_hands=metric.include_hands,
            )
        out.append(
            CompiledDeclaration(
                declaration_id=declaration.declaration_id,
                owner=declaration.owner,
                state_guards=guards,
                require_not_in_check=declaration.require_not_in_check,
                ply_limit=declaration.ply_limit,
                weighted_metric=compiled_metric,
                outcome_bands=tuple(
                    CompiledDeclarationOutcomeBand(b.threshold, b.outcome)
                    for b in declaration.outcome_bands
                ),
                failure_outcome=declaration.failure_outcome,
                zones=zones,
            )
        )
    return tuple(out)


def _pattern_components(pattern) -> list[str]:
    components = (
        ["geometry"] * len(pattern.geometry_ids)
        + [pattern.target.kind]
        + [pp.kind for pp in pattern.path]
        + ["state_guard"] * len(pattern.guards)
        + ["slot_guard"] * len(pattern.slot_guards)
        + ["square_zone_guard"] * len(pattern.square_zone_guards)
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


def _semantic_action_geometry_ids(action, action_index, types_by_id, legacy_ids):
    """Select legacy atom geometry for an action through the shared IR seam."""
    if action.geometry.kind != "legacy_atoms":
        raise ValueError("shared legacy geometry selection requires legacy_atoms")
    gids = []
    for tid in action.type_ids:
        if tid not in types_by_id:
            raise RuleValidationError(
                [ValidationIssue("SEMANTIC_TYPE_UNKNOWN", "type_ids", tid)]
            )
        pt = types_by_id[tid]
        for atom_index, atom in enumerate(pt.movement_atoms):
            is_ray = isinstance(atom, RayAtom)
            if action.geometry.atom_kind is None or (
                (action.geometry.atom_kind == "ray") == is_ray
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
    return tuple(sorted(gids))


def _matching_replaced_legacy_patterns(
    action_index, action, geometry, legacy_patterns
):
    """Resolve a replace_legacy selector identically for each IR lowering path."""
    selector = action.replace_selector
    if selector is None:
        raise RuleValidationError(
            [ValidationIssue("REPLACE_NO_SELECTOR", "replace_selector", action.name)]
        )

    def family_ok(gid: str) -> bool:
        kind = geometry[gid].kind
        if selector.action_family == "drop":
            return kind == "drop"
        return kind in ("leap", "ray")

    matched = [
        p.pattern_id
        for p in legacy_patterns
        if set(p.type_ids) & set(selector.type_ids)
        and any(family_ok(g) for g in p.geometry_ids)
        and p.target.kind == f"target_{selector.target_relation}"
        and (
            selector.geometry_kind is None
            or any(geometry[g].kind == selector.geometry_kind for g in p.geometry_ids)
        )
    ]
    matched = tuple(dict.fromkeys(matched))
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
    return matched


def _lower_semantic_effects(action, slot_ids_by_name, type_ids):
    """Lower action effects through the shared semantic-IR constructor."""
    from .ir import CompiledEffect

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
    return tuple(effects)


def _lower_semantic_invariants(action, slot_ids_by_name):
    """Lower action invariants through the shared semantic-IR constructor."""
    from .ir import CompiledInvariant

    return tuple(
        CompiledInvariant(
            invariant.kind,
            tuple(
                _resolve_square_ref(ref, slot_ids_by_name)
                for ref in invariant.square_refs
            ),
        )
        for invariant in action.invariants
    )


def _lower_semantic_path_constraints(action):
    """Lower path predicates from the RuleSet DSL through the shared IR seam."""
    from .ir import CompiledPathPredicate

    return tuple(
        CompiledPathPredicate(
            kind=constraint.kind,
            count=constraint.count,
            lo=constraint.lo,
            hi=constraint.hi,
            owner_filter=constraint.owner_filter,
        )
        for constraint in action.path_constraints
    )


def _lower_compile_only_ray_path_actions(carrier, ruleset):
    """Lower a bounded ray-path diagnostic (capture alone or quiet/capture pair).

    This compile-only seam accepts only the exact quiet and one-screen capture
    shapes used by the diagnostic. It reuses the shared typed-IR lowerers and
    never grants execution capability or opens rectangular execution.
    """
    from .ir import validate_executable_completeness, validate_ir

    if not isinstance(carrier, CompiledGeometryCarrier):
        raise TypeError("compile-only geometry carrier required")
    if (
        ruleset.board_shape != carrier.board_shape
        or compute_fingerprint(ruleset) != carrier.ruleset_fingerprint
    ):
        raise ValueError("RuleSet does not match the compile-only geometry carrier")
    actions = ruleset.semantic_actions
    if len(actions) not in (1, 2):
        raise ValueError("compile-only diagnostic requires one capture or a quiet/capture pair")

    def is_source_to_target_move(effect):
        return (
            effect.kind == "move"
            and effect.from_ref is not None
            and effect.from_ref.kind == "source"
            and effect.to_ref is not None
            and effect.to_ref.kind == "target"
            and effect.square_ref is None
            and effect.piece_owner == "self"
            and effect.piece_type_ref is None
            and effect.disposition is None
            and effect.slot_name is None
            and effect.type_ref is None
            and effect.count == 1
            and effect.value is None
        )

    type_ids = tuple(actions[0].type_ids)
    relations = {action.target_relation for action in actions}
    if len(actions) == 1 and relations != {"enemy"}:
        raise ValueError("single-action diagnostic requires the capture rule")
    if len(actions) == 2 and relations != {"empty", "enemy"}:
        raise ValueError("compile-only pair requires one quiet and one capture action")
    for action_index, action in enumerate(actions):
        selector = action.replace_selector
        path = action.path_constraints
        expected_path = (
            "path_clear" if action.target_relation == "empty" else "path_count_eq"
        )
        expected_count = None if expected_path == "path_clear" else 1
        supported_path = len(path) == 1 and (
            path[0].kind == expected_path and path[0].count == expected_count
            or len(actions) == 1
            and action.target_relation == "enemy"
            and path[0].kind == "path_clear"
            and path[0].count is None
        )
        move_shape = (
            len(action.effects) == 1 and is_source_to_target_move(action.effects[0])
        )
        capture_shape = (
            len(action.effects) == 2
            and action.effects[0].kind == "remove"
            and action.effects[0].square_ref is not None
            and action.effects[0].square_ref.kind == "target"
            and action.effects[0].from_ref is None
            and action.effects[0].to_ref is None
            and action.effects[0].piece_owner == "opponent"
            and action.effects[0].piece_type_ref is None
            and action.effects[0].disposition in DISPOSITIONS
            and action.effects[0].slot_name is None
            and action.effects[0].type_ref is None
            and action.effects[0].count == 1
            and action.effects[0].value is None
            and is_source_to_target_move(action.effects[1])
        )
        expected_effects = (
            move_shape if action.target_relation == "empty" else capture_shape
        )
        if not (
            action.type_ids == type_ids
            and action.geometry.kind == "legacy_atoms"
            and action.geometry.atom_kind == "ray"
            and action.target_relation in ("empty", "enemy")
            and action.composition == "replace_legacy"
            and supported_path
            and path[0].lo is None
            and path[0].hi is None
            and path[0].owner_filter == "any"
            and not action.state_guards
            and not action.slot_guards
            and not action.aux_state
            and not action.triggers
            and not action.postconditions
            and expected_effects
            and len(action.invariants) == 1
            and action.invariants[0].kind == "own_anchor_safe"
            and not action.invariants[0].square_refs
            and selector is not None
            and selector.action_family == "board"
            and selector.target_relation == action.target_relation
            and selector.geometry_kind == "ray"
            and selector.replace_all_matching
            and tuple(selector.type_ids) == type_ids
        ):
            raise ValueError(
                f"semantic action {action_index} is outside the bounded ray-path diagnostic"
            )

    ir = lower_legacy_to_ir(carrier, ruleset=ruleset)
    _, legacy_ids = build_legacy_geometry_catalog(carrier)
    replaced_ids: set[str] = set()
    semantic_patterns = []
    all_type_ids = tuple(sorted(carrier.types_by_id))
    for action_index, action in enumerate(actions):
        gids = _semantic_action_geometry_ids(
            action, action_index, carrier.types_by_id, legacy_ids
        )
        action_replaced_ids = _matching_replaced_legacy_patterns(
            action_index, action, ir.geometry, ir.patterns
        )
        templates = [
            pattern for pattern in ir.patterns
            if pattern.pattern_id in action_replaced_ids
        ]
        if not templates or any(
            pattern.geometry_ids[0] not in gids for pattern in templates
        ):
            raise ValueError("legacy replacement selection does not match action geometry")
        if replaced_ids.intersection(action_replaced_ids):
            raise ValueError("diagnostic actions replace overlapping legacy patterns")
        replaced_ids.update(action_replaced_ids)
        semantic = replace(
            templates[0],
            pattern_id=f"sem_{action_index:02d}_{action.name}",
            name=action.name,
            type_ids=type_ids,
            geometry_ids=gids,
            path=_lower_semantic_path_constraints(action),
            effects=_lower_semantic_effects(action, {}, all_type_ids),
            invariants=_lower_semantic_invariants(action, {}),
            promotion_mode=action.promotion_mode,
            explicit_promotion_type=action.explicit_promotion_type,
            composition="replace_legacy",
            replaced_pattern_ids=action_replaced_ids,
        )
        stratum, cost = _assign_stratum_cost(semantic)
        semantic_patterns.append(replace(semantic, stratum=stratum, cost_class=cost))

    lowered = replace(
        ir,
        patterns=tuple(
            pattern for pattern in ir.patterns
            if pattern.pattern_id not in replaced_ids
        ) + tuple(semantic_patterns),
        capabilities=replace(
            ir.capabilities,
            legacy_core_executable=False,
            new_ir_core_executable=False,
            native_executable=False,
            contains_path_predicate=True,
        ),
    )
    errors = validate_ir(lowered)
    errors.extend(validate_executable_completeness(lowered, all_type_ids))
    if errors:
        raise RuleValidationError(
            [ValidationIssue("SEMANTIC_IR_INVALID", "semantic_actions", "; ".join(errors))]
        )
    support = _build_semantic_support(carrier, ruleset=ruleset)
    return lowered, support


def _lower_compile_only_single_source_offset_guard(carrier, ruleset):
    """Lower one narrow source-offset empty-square guard into static typed IR."""
    from .ir import (
        CompiledStatePredicate,
        validate_executable_completeness,
        validate_ir,
    )

    if not isinstance(carrier, CompiledGeometryCarrier):
        raise TypeError("compile-only geometry carrier required")
    if (
        ruleset.board_shape != carrier.board_shape
        or compute_fingerprint(ruleset) != carrier.ruleset_fingerprint
    ):
        raise ValueError("RuleSet does not match the compile-only geometry carrier")
    if len(ruleset.semantic_actions) != 1:
        raise ValueError("source-offset diagnostic requires exactly one action")
    action = ruleset.semantic_actions[0]
    selector = action.replace_selector
    if len(action.state_guards) != 1:
        raise ValueError("source-offset diagnostic requires exactly one state guard")
    guard = action.state_guards[0]
    refs = guard.spatial.refs
    if not (
        action.geometry.kind == "legacy_atoms"
        and action.geometry.atom_kind == "leap"
        and action.target_relation == "empty"
        and action.composition == "replace_legacy"
        and not action.path_constraints
        and not action.slot_guards
        and not action.aux_state
        and not action.triggers
        and not action.postconditions
        and action.promotion_mode == "none"
        and action.explicit_promotion_type is None
        and len(action.effects) == 1
        and action.effects[0].kind == "move"
        and action.effects[0].from_ref is not None
        and action.effects[0].from_ref.kind == "source"
        and action.effects[0].to_ref is not None
        and action.effects[0].to_ref.kind == "target"
        and action.effects[0].square_ref is None
        and action.effects[0].piece_owner == "self"
        and action.effects[0].piece_type_ref is None
        and action.effects[0].disposition is None
        and action.effects[0].slot_name is None
        and action.effects[0].type_ref is None
        and action.effects[0].count == 1
        and action.effects[0].value is None
        and len(action.invariants) == 1
        and action.invariants[0].kind == "own_anchor_safe"
        and not action.invariants[0].square_refs
        and guard.aggregation == "count"
        and guard.owner == "any"
        and guard.type_ref.kind == "any"
        and guard.type_ref.type_id is None
        and guard.compare_field == "base"
        and guard.promoted == "any"
        and guard.location == "board"
        and guard.spatial.kind == "exact"
        and not guard.spatial.zone_squares
        and len(refs) == 1
        and refs[0].kind == "offset_from_source"
        and refs[0].offset is not None
        and refs[0].owner_relative
        and refs[0].square is None
        and refs[0].step is None
        and refs[0].slot_name is None
        and guard.comparison == "eq"
        and guard.value == 0
        and guard.subject_ref is None
        and selector is not None
        and selector.action_family == "board"
        and selector.target_relation == "empty"
        and selector.geometry_kind == "leap"
        and selector.replace_all_matching
        and tuple(selector.type_ids) == tuple(action.type_ids)
    ):
        raise ValueError("action is outside the bounded source-offset guard diagnostic")

    ir = lower_legacy_to_ir(carrier, ruleset=ruleset)
    _, legacy_ids = build_legacy_geometry_catalog(carrier)
    gids = _semantic_action_geometry_ids(
        action, 0, carrier.types_by_id, legacy_ids
    )
    replaced_ids = _matching_replaced_legacy_patterns(
        0, action, ir.geometry, ir.patterns
    )
    templates = [pattern for pattern in ir.patterns if pattern.pattern_id in replaced_ids]
    if len(gids) != 1 or len(templates) != 1:
        raise ValueError(
            "source-offset diagnostic requires exactly one legacy leap geometry"
        )
    if not templates or any(
        pattern.geometry_ids[0] not in gids for pattern in templates
    ):
        raise ValueError("legacy replacement selection does not match action geometry")

    type_ids = tuple(sorted(carrier.types_by_id))
    compiled_guard = CompiledStatePredicate(
        aggregation=guard.aggregation,
        owner=guard.owner,
        type_ref=_resolve_type_ref(guard.type_ref, type_ids),
        compare_field=guard.compare_field,
        promoted=guard.promoted,
        location=guard.location,
        spatial=_resolve_spatial(guard.spatial, {}, {}),
        comparison=guard.comparison,
        value=guard.value,
    )
    semantic = replace(
        templates[0],
        pattern_id=f"sem_00_{action.name}",
        name=action.name,
        type_ids=tuple(action.type_ids),
        geometry_ids=gids,
        guards=(compiled_guard,),
        effects=_lower_semantic_effects(action, {}, type_ids),
        invariants=_lower_semantic_invariants(action, {}),
        promotion_mode=action.promotion_mode,
        explicit_promotion_type=action.explicit_promotion_type,
        composition="replace_legacy",
        replaced_pattern_ids=replaced_ids,
    )
    stratum, cost = _assign_stratum_cost(semantic)
    semantic = replace(semantic, stratum=stratum, cost_class=cost)
    lowered = replace(
        ir,
        patterns=tuple(
            pattern for pattern in ir.patterns
            if pattern.pattern_id not in set(replaced_ids)
        ) + (semantic,),
        capabilities=replace(
            ir.capabilities,
            legacy_core_executable=False,
            new_ir_core_executable=False,
            native_executable=False,
            contains_state_guard=True,
        ),
    )
    errors = validate_ir(lowered)
    errors.extend(validate_executable_completeness(lowered, type_ids))
    if errors:
        raise RuleValidationError(
            [ValidationIssue("SEMANTIC_IR_INVALID", "semantic_actions[0]", "; ".join(errors))]
        )
    support = _build_semantic_support(carrier, ruleset=ruleset)
    return lowered, support


def compile_semantic_ruleset(ruleset: RuleSet | Mapping[str, Any]):
    """Compile a semantic-DSL RuleSet into the v2 production IR.

    The normalized pattern set is the final action template set
    (legacy - replaced + augment + replacements); an executor consumes only
    this IR and never the high-level RuleSet. Rectangular semantic rules use
    the shape carrier and are executable only by the Python reference engine;
    the legacy compiler remains square-only and native capability stays off.
    """
    if not isinstance(ruleset, RuleSet):
        ruleset = ruleset_from_dict(ruleset)
    _compile_consecutive_action_adjudications(ruleset)
    _compile_repeated_cycle_target_conditions(ruleset)
    if not ruleset.semantic_actions:
        raise RuleValidationError(
            [ValidationIssue("NO_SEMANTIC_ACTIONS", "ruleset.semantic_actions", "empty")]
        )
    shape = ruleset.board_shape
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
        for guard in action.square_zone_guards:
            if guard.spatial.kind != "zone" or not guard.spatial.zone_squares:
                raise RuleValidationError(
                    [
                        ValidationIssue(
                            "SQUARE_ZONE_SELECTOR_INVALID",
                            f"ruleset.semantic_actions {action.name} square_zone_guards",
                            "square zone guard requires a non-empty zone selector",
                        )
                    ]
                )
            if guard.relation not in ("inside", "outside"):
                raise RuleValidationError(
                    [
                        ValidationIssue(
                            "SQUARE_ZONE_RELATION_INVALID",
                            f"ruleset.semantic_actions {action.name} square_zone_guards",
                            "relation must be 'inside' or 'outside'",
                        )
                    ]
                )
            if any(
                not (0 <= file < shape.width and 0 <= rank < shape.height)
                for file, rank in guard.spatial.zone_squares
            ):
                raise RuleValidationError(
                    [
                        ValidationIssue(
                            "SQUARE_ZONE_OUT_OF_BOUNDS",
                            f"ruleset.semantic_actions {action.name} square_zone_guards",
                            "zone square is outside the board",
                        )
                    ]
                )
    if shape.width != shape.height:
        carrier = _compile_geometry_carrier(ruleset)
        compiled = _compile_semantic_ruleset_from_baseline(
            carrier, ruleset, enable_rectangular_reference_executor=True
        )
        if not compiled.ir.capabilities.new_ir_core_executable:
            raise RuleValidationError(
                [
                    ValidationIssue(
                        "RECTANGULAR_SEMANTIC_EXECUTION_UNSUPPORTED",
                        "ruleset.semantic_actions",
                        "the rectangular reference executor does not support this semantic IR combination",
                    )
                ]
            )
        _validate_semantic_initial_position(compiled)
        fingerprint = compute_fingerprint(ruleset)
        if compute_fingerprint(deserialize_ruleset(serialize_ruleset(ruleset))) != fingerprint:
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
    # Legacy attacks may disagree with replaced semantic capture patterns.
    # Keep schema/metadata validation, then validate every start with the
    # final semantic executor below. The public legacy entry stays unchanged.
    baseline = _compile_ruleset_baseline(
        ruleset, allow_semantic_actions=True, validate_position=False)
    compiled = _compile_semantic_ruleset_from_baseline(baseline, ruleset)
    _validate_semantic_initial_position(compiled)
    return compiled


def compile_legacy_ruleset_for_semantic_execution(ruleset: RuleSet | Mapping[str, Any]):
    """Compile a square legacy RuleSet for explicit semantic Core execution.

    This opt-in adapter uses the ordinary legacy schema/position validation,
    then the shared normalized IR/completeness and semantic-start validation.
    It preserves the RuleSet fingerprint and promotion/drop/history rules.
    Semantic actions and identity keys belong to the resulting representation;
    import a played history by replay, rather than copying legacy key strings.
    Overlapping movement atoms retain distinct pattern/geometry actions with
    equal visible coordinates; this is not a one-to-one legacy action adapter.
    Core execution support does not remove separate Native or search path-state
    restrictions (for example no-progress adjudication).
    The default execution selector and semantic-DSL entry remain unchanged.
    """
    if not isinstance(ruleset, RuleSet):
        ruleset = ruleset_from_dict(ruleset)
    baseline = compile_ruleset(ruleset)
    compiled = _compile_semantic_ruleset_from_baseline(baseline, ruleset)
    _validate_semantic_initial_position(compiled)
    from .execution import ExecutableSemanticRuleset

    return ExecutableSemanticRuleset(
        ir=compiled.ir, _legacy_compiled=baseline, support=compiled.support
    )


def _validate_semantic_initial_position(compiled) -> None:
    """Validate a carrier-backed semantic start position with its executor."""
    from ..core.semantic_executor import SemanticEngine

    engine = SemanticEngine(compiled)
    setup_keys = (None, *compiled.support.initial_setup_options.keys())
    for setup_key in setup_keys:
        position = engine._initial_position(setup_key)
        path = (
            "initial_position"
            if setup_key is None
            else f"initial_setup_options[{setup_key}]"
        )
        issues = []
        for player in (0, 1):
            if engine.in_check(position, player):
                issues.append(
                    ValidationIssue(
                        "INITIAL_ANCHOR_ATTACKED",
                        path,
                        f"player {player}'s anchor is attacked at the initial position",
                    )
                )
        if not engine.has_legal_action(position):
            issues.append(
                ValidationIssue(
                    "INITIAL_NO_LEGAL_MOVE",
                    path,
                    "the side to move has no legal action at the initial position",
                )
            )
        if issues:
            raise RuleValidationError(issues)


def _compile_semantic_ruleset_from_baseline(
    baseline: CompiledRuleSet | CompiledGeometryCarrier,
    ruleset: RuleSet,
    *,
    enable_rectangular_reference_executor: bool = False,
):
    """Shared semantic action-to-IR lowering for executable and shape carriers.

    A carrier supplies definition-layer metadata only by default. The public
    rectangular semantic compiler opts into the Python reference executor
    after IR validation; diagnostic carrier callers remain non-executable.
    """
    from . import ir as ir_module
    from .ir import (
        CompiledAuxSlot,
        CompiledGeometry,
        CompiledMovePattern,
        CompiledPostcondition,
        CompiledSemanticIR,
        CompiledSemanticRuleset,
        CompiledSlotGuard,
        CompiledSquareRef,
        CompiledSquareZoneGuard,
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

    compile_only = isinstance(baseline, CompiledGeometryCarrier)
    if enable_rectangular_reference_executor and (
        not compile_only or baseline.board_shape.width == baseline.board_shape.height
    ):
        raise ValueError("rectangular reference execution requires a rectangular shape carrier")
    if compile_only:
        if (
            ruleset.board_shape != baseline.board_shape
            or compute_fingerprint(ruleset) != baseline.ruleset_fingerprint
        ):
            raise ValueError("RuleSet does not match the compile-only geometry carrier")
    elif not isinstance(baseline, CompiledRuleSet):
        raise TypeError("semantic lowering requires a compiled ruleset or geometry carrier")
    elif compute_fingerprint(ruleset) != baseline.ruleset_fingerprint:
        raise ValueError("RuleSet does not match the compiled ruleset")
    type_ids = tuple(sorted(baseline.types_by_id))
    repeated_cycle_target_conditions = (
        _compile_repeated_cycle_target_conditions(ruleset)
    )

    # --- geometry catalog: legacy atoms first, then explicit shapes.
    geometry, legacy_ids = build_legacy_geometry_catalog(baseline)
    drop_gid = f"g{len(geometry)}"
    geometry[drop_gid] = CompiledGeometry(geometry_id=drop_gid, kind="drop")
    next_gid = len(geometry)
    action_geometry_ids: dict[int, tuple[str, ...]] = {}
    for action_index, action in enumerate(ruleset.semantic_actions):
        spec = action.geometry
        if spec.kind == "legacy_atoms":
            action_geometry_ids[action_index] = _semantic_action_geometry_ids(
                action, action_index, baseline.types_by_id, legacy_ids
            )
        else:
            gid = f"g{next_gid}"
            next_gid += 1
            geometry[gid] = _build_explicit_geometry(baseline, spec, gid)
            action_geometry_ids[action_index] = (gid,)

    # --- zones (deterministic: sorted square sets).
    board_shape = _geometry_board_shape(baseline)
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
        for guard in action.square_zone_guards:
            key = tuple(sorted(guard.spatial.zone_squares))
            if key not in zone_ids_by_set:
                zone_ids_by_set[key] = f"z{len(zone_sets)}"
                zone_sets.append(key)
    zones = {
        zid: CompiledZone(
            zid,
            tuple(
                sq[1] * board_shape.width + sq[0]
                for sq in squares
            ),
        )
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
    legacy_ir = lower_legacy_to_ir(
        baseline,
        ruleset=ruleset if compile_only else None,
    )
    legacy_patterns = list(legacy_ir.patterns)
    replaced: set[str] = set()
    semantic_patterns: list[CompiledMovePattern] = []
    contains_path = contains_guard = contains_compound = contains_post = contains_trigger = False

    for action_index, action in enumerate(ruleset.semantic_actions):
        for tid in action.type_ids:
            if tid not in baseline.types_by_id:
                raise RuleValidationError(
                    [ValidationIssue("SEMANTIC_TYPE_UNKNOWN", "type_ids", tid)]
                )
        if action.path_constraints:
            contains_path = True
        if action.state_guards or action.slot_guards or action.square_zone_guards:
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
            replaced_ids = _matching_replaced_legacy_patterns(
                action_index, action, geometry, legacy_patterns
            )
            replaced.update(replaced_ids)

        effects = _lower_semantic_effects(action, slot_ids_by_name, type_ids)

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
        square_zone_guards = tuple(
            CompiledSquareZoneGuard(
                square_ref=_resolve_square_ref(guard.square_ref, slot_ids_by_name),
                spatial=_resolve_spatial(
                    guard.spatial, slot_ids_by_name, zone_ids_by_set
                ),
                relation=guard.relation,
                owner_relative=guard.owner_relative,
            )
            for guard in action.square_zone_guards
        )
        path = _lower_semantic_path_constraints(action)
        invariants = _lower_semantic_invariants(action, slot_ids_by_name)
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
            square_zone_guards=square_zone_guards,
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
            square_zone_guards=pattern.square_zone_guards,
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
        new_ir_core_executable=(not compile_only or enable_rectangular_reference_executor),
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
        ruleset_fingerprint=baseline.ruleset_fingerprint,
        geometry=geometry,
        zones=zones,
        patterns=tuple(normalized),
        aux_slots=compiled_slots,
        triggers=triggers,
        automatic_adjudications=legacy_ir.automatic_adjudications,
        consecutive_action_adjudications=(
            legacy_ir.consecutive_action_adjudications
        ),
        repeated_cycle_target_conditions=repeated_cycle_target_conditions,
        declarations=legacy_ir.declarations,
        capabilities=capabilities,
    )
    errors = validate_ir(ir)
    errors.extend(validate_executable_completeness(ir, type_ids))
    if errors:
        raise RuleValidationError(
            [ValidationIssue("IR_INVALID", "ir", "; ".join(errors))]
        )
    support = _build_semantic_support(
        baseline,
        ruleset=ruleset if compile_only else None,
    )
    # Native execution is a per-ruleset capability, derived from the exact
    # lowered payload rather than a global promise.  Any lowering/shape
    # failure remains fail-closed while Python IR compilation stays usable.
    if not compile_only:
        try:
            from ..native.compiler import build_semantic_compile_payload

            _, native_report = build_semantic_compile_payload(
                CompiledSemanticRuleset(
                    ir=ir, _legacy_compiled=baseline, support=support
                )
            )
            # The current Native semantic payload has neither declaration nor
            # automatic-adjudication sections.  Never advertise a ruleset as
            # fully Native executable while silently dropping either semantic.
            if (
                native_report.native_executable
                and support.stalemate_result == "draw"
                and not ir.declarations
                and not ir.automatic_adjudications
                and not support.consecutive_action_adjudications
                and support.no_progress_draw is None
                and not ir.repeated_cycle_target_conditions
            ):
                ir = replace(
                    ir,
                    capabilities=replace(ir.capabilities, native_executable=True),
                )
        except Exception:
            pass
    return CompiledSemanticRuleset(ir=ir, _legacy_compiled=baseline, support=support)
