"""The JSON-serializable RuleSet schema and fingerprint computation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..core.coordinates import Square
from ..core.movement import LeapAtom, RayAtom, MovementAtom
from ..core.pieces import Piece, PieceType
from .validation import RuleValidationError, ValidationIssue


def atom_to_dict(atom: MovementAtom) -> dict[str, Any]:
    if isinstance(atom, LeapAtom):
        return {"kind": "leap", "offset": list(atom.offset)}
    return {"kind": "ray", "direction": list(atom.direction), "max_steps": atom.max_steps}


def _err(code: str, path: str, message: str) -> RuleValidationError:
    return RuleValidationError([ValidationIssue(code, path, message)])


def _require_mapping(data: Any, path: str) -> dict:
    if not isinstance(data, dict):
        raise _err("FIELD_NOT_OBJECT", path, f"expected a JSON object, got {data!r}")
    return data


def _require_field(data: dict, key: str, path: str) -> Any:
    if key not in data:
        raise _err("MISSING_FIELD", f"{path}.{key}", f"required field {key!r} is missing")
    return data[key]


def _require_int(value: Any, path: str, code: str = "FIELD_NOT_INT") -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _err(code, path, f"expected an integer, got {value!r}")
    return value


def _require_bool(value: Any, path: str, code: str = "FIELD_NOT_BOOL") -> bool:
    if not isinstance(value, bool):
        raise _err(code, path, f"expected a boolean, got {value!r}")
    return value


def _require_str(value: Any, path: str, code: str = "FIELD_NOT_STRING") -> str:
    if not isinstance(value, str):
        raise _err(code, path, f"expected a string, got {value!r}")
    return value


def _require_int_pair(value: Any, path: str) -> tuple[int, int]:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or any(isinstance(x, bool) or not isinstance(x, int) for x in value)
    ):
        raise _err("FIELD_NOT_INT_PAIR", path, f"expected a pair of integers, got {value!r}")
    return (value[0], value[1])


def _require_int_quad(value: Any, path: str) -> tuple[int, int, int, int]:
    """A 4-int list: ``[from_file, from_rank, to_file, to_rank]``."""
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 4
        or any(isinstance(x, bool) or not isinstance(x, int) for x in value)
    ):
        raise _err("FIELD_NOT_INT_QUAD", path, f"expected a 4-int list, got {value!r}")
    return (value[0], value[1], value[2], value[3])


def _require_str_list(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise _err("FIELD_NOT_LIST", path, f"expected a list, got {value!r}")
    return tuple(_require_str(v, f"{path}[{i}]") for i, v in enumerate(value))


def atom_from_dict(data: Mapping[str, Any], path: str = "movement_atoms[]") -> MovementAtom:
    data = _require_mapping(data, path)
    kind = _require_str(_require_field(data, "kind", path), f"{path}.kind")
    if kind == "leap":
        offset = _require_int_pair(_require_field(data, "offset", path), f"{path}.offset")
        return LeapAtom(offset)
    if kind == "ray":
        direction = _require_int_pair(
            _require_field(data, "direction", path), f"{path}.direction"
        )
        max_steps = data.get("max_steps")
        if max_steps is not None:
            max_steps = _require_int(max_steps, f"{path}.max_steps", "RAY_MAX_STEPS_INVALID")
            if max_steps < 1:
                raise _err(
                    "RAY_MAX_STEPS_INVALID",
                    f"{path}.max_steps",
                    f"max_steps must be a positive integer, got {max_steps}",
                )
        return RayAtom(direction, max_steps)
    raise _err("ATOM_KIND_INVALID", f"{path}.kind", f"unknown atom kind {kind!r}")


def piece_to_dict(piece: Piece) -> dict[str, Any]:
    return {
        "owner": piece.owner,
        "base_type_id": piece.base_type_id,
        "current_type_id": piece.current_type_id,
        "promoted": piece.promoted,
    }


def piece_from_dict(data: Mapping[str, Any], path: str = "initial_position[]") -> Piece:
    data = _require_mapping(data, path)
    owner = _require_int(_require_field(data, "owner", path), f"{path}.owner")
    if owner not in (0, 1):
        raise _err("ILLEGAL_OWNER", f"{path}.owner", f"owner must be 0 or 1, got {owner!r}")
    base = _require_str(_require_field(data, "base_type_id", path), f"{path}.base_type_id")
    current = data.get("current_type_id", base)
    current = _require_str(current, f"{path}.current_type_id")
    promoted = _require_bool(data.get("promoted", False), f"{path}.promoted")
    return Piece(
        owner=owner,
        base_type_id=base,
        current_type_id=current,
        promoted=promoted,
    )


@dataclass(frozen=True, slots=True)
class RuleSet:
    """A declarative, JSON-serializable game definition.

    ``initial_position`` is stored as rows of ``Piece | None`` ordered from
    rank 0 (bottom) to rank n-1 (top).  Drop and promotion policies are
    stored as explicit per-square masks so the compiler never has to guess
    them.  ``metadata`` must never influence game results; it is excluded
    from the fingerprint.
    """

    schema_version: int = 1
    board_size: int = 8
    piece_types: tuple[PieceType, ...] = ()
    initial_position: tuple[tuple[Piece | None, ...], ...] = ()
    drop_allowed: Mapping[str, tuple[tuple[bool, ...], ...]] = field(default_factory=dict)
    promotion_allowed: Mapping[str, tuple[frozenset[tuple[Square, Square]], ...]] = field(
        default_factory=dict
    )
    promotion_forced: Mapping[str, tuple[frozenset[Square], ...]] = field(default_factory=dict)
    repetition_limit: int = 4
    max_ply: int = 512
    stalemate_result: str = "draw"
    # Additive high-level semantic actions (Phase 1.9B-1).  Omitted/empty
    # keeps legacy semantics; the legacy compiler refuses non-empty values
    # (fail-closed) and ``compile_semantic_ruleset`` is the IR entry point.
    semantic_actions: tuple["RuleSemanticAction", ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------- semantic DSL

PATH_CONSTRAINT_KINDS = (
    "path_clear",
    "path_count_eq",
    "path_count_range",
    "path_first_blocker_owner",
    "path_last_blocker_owner",
)
SEMANTIC_GEOMETRY_KINDS = ("leap", "ray", "drop")
TARGET_RELATIONS = ("empty", "enemy", "friendly", "any")
SELECTOR_OWNERS = ("self", "opponent", "any")
SELECTOR_TYPE_MODES = ("base", "current", "any")
SELECTOR_PROMOTED = ("yes", "no", "any")
SELECTOR_LOCATIONS = ("board", "hand")
SELECTOR_SPATIAL = (
    "same_file",
    "same_rank",
    "zone",
    "exact",
    "adjacent",
    "path_between",
)
SELECTOR_SPATIAL_REFS = ("SOURCE", "TARGET", "FIXED_SQUARE", "AUX_SLOT")
AGGREGATIONS = ("exists", "count")
COMPARISON_OPS = ("eq", "ne", "lt", "le", "gt", "ge")
SEMANTIC_EFFECT_KINDS = (
    "move",
    "remove",
    "remove_from_hand",
    "place",
    "set_current_type",
    "clear_right",
    "set_token",
    "clear_token",
    "shift",
)
EFFECT_SQUARE_REFS = ("target", "source", "token", "partner_square")
AUX_STATE_KINDS = ("right", "token_square")
AUX_LIFETIMES = ("persistent", "expire_next_turn")
INVARIANT_KINDS = ("own_anchor_safe", "squares_not_attacked")
POSTCONDITION_KINDS = ("opponent_checked", "no_legal_reply")
SEMANTIC_STRATA = ("S0", "S1", "S2", "S3", "S4", "S5")

MAX_SEMANTIC_EFFECTS = 4
MAX_SEMANTIC_AUX_SLOTS = 8
MAX_SQUARES_NOT_ATTACKED = 4


@dataclass(frozen=True, slots=True)
class RulePathConstraint:
    kind: str
    count: int | None = None
    lo: int | None = None
    hi: int | None = None
    owner_filter: str = "any"


@dataclass(frozen=True, slots=True)
class RuleSlotGuard:
    """Pre-action guard reading a named auxiliary slot."""

    slot_name: str
    comparison: str = "eq"
    value: int = 0


@dataclass(frozen=True, slots=True)
class RuleStateGuard:
    aggregation: str
    owner: str
    type_mode: str
    promoted: str
    location: str
    spatial: str
    spatial_ref: str = "TARGET"
    comparison: str = "eq"
    value: int = 0


@dataclass(frozen=True, slots=True)
class RuleAuxState:
    name: str
    kind: str
    lifetime: str


@dataclass(frozen=True, slots=True)
class RuleActionEffect:
    kind: str
    square_ref: str = "target"
    slot_name: str | None = None
    type_id: str | None = None


@dataclass(frozen=True, slots=True)
class RuleInvariant:
    kind: str
    square_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RulePostcondition:
    kind: str
    max_stratum: str = "S3"


@dataclass(frozen=True, slots=True)
class RuleSemanticAction:
    """High-level (definition-layer) semantic action template."""

    name: str
    type_ids: tuple[str, ...]
    geometry: tuple[str, ...]
    target_relation: str
    path_constraints: tuple[RulePathConstraint, ...] = ()
    state_guards: tuple[RuleStateGuard, ...] = ()
    slot_guards: tuple[RuleSlotGuard, ...] = ()
    aux_state: tuple[RuleAuxState, ...] = ()
    effects: tuple[RuleActionEffect, ...] = ()
    invariants: tuple[RuleInvariant, ...] = ()
    postconditions: tuple[RulePostcondition, ...] = ()


def _require_member(value: str, allowed: tuple[str, ...], path: str, code: str) -> str:
    if value not in allowed:
        raise _err(code, path, f"expected one of {allowed}, got {value!r}")
    return value


def path_constraint_to_dict(value: RulePathConstraint) -> dict:
    return {
        "kind": value.kind,
        "count": value.count,
        "lo": value.lo,
        "hi": value.hi,
        "owner_filter": value.owner_filter,
    }


def path_constraint_from_dict(data: Mapping[str, Any], path: str) -> RulePathConstraint:
    data = _require_mapping(data, path)
    kind = _require_member(
        _require_str(_require_field(data, "kind", path), f"{path}.kind"),
        PATH_CONSTRAINT_KINDS,
        f"{path}.kind",
        "PATH_CONSTRAINT_KIND_INVALID",
    )
    count = data.get("count")
    if count is not None:
        count = _require_int(count, f"{path}.count")
        if count < 0:
            raise _err("PATH_COUNT_NEGATIVE", f"{path}.count", "count must be >= 0")
    lo = data.get("lo")
    if lo is not None:
        lo = _require_int(lo, f"{path}.lo")
    hi = data.get("hi")
    if hi is not None:
        hi = _require_int(hi, f"{path}.hi")
    if lo is not None and hi is not None and lo > hi:
        raise _err("PATH_RANGE_INVALID", f"{path}", "lo must be <= hi")
    owner_filter = _require_member(
        _require_str(data.get("owner_filter", "any"), f"{path}.owner_filter"),
        SELECTOR_OWNERS,
        f"{path}.owner_filter",
        "OWNER_FILTER_INVALID",
    )
    return RulePathConstraint(kind=kind, count=count, lo=lo, hi=hi, owner_filter=owner_filter)


def slot_guard_to_dict(value: RuleSlotGuard) -> dict:
    return {"slot_name": value.slot_name, "comparison": value.comparison, "value": value.value}


def slot_guard_from_dict(data: Mapping[str, Any], path: str) -> RuleSlotGuard:
    data = _require_mapping(data, path)
    slot_name = _require_str(_require_field(data, "slot_name", path), f"{path}.slot_name")
    comparison = _require_member(
        _require_str(data.get("comparison", "eq"), f"{path}.comparison"),
        COMPARISON_OPS,
        f"{path}.comparison",
        "COMPARISON_INVALID",
    )
    value = _require_int(data.get("value", 0), f"{path}.value")
    return RuleSlotGuard(slot_name=slot_name, comparison=comparison, value=value)


def state_guard_to_dict(value: RuleStateGuard) -> dict:
    return {
        "aggregation": value.aggregation,
        "owner": value.owner,
        "type_mode": value.type_mode,
        "promoted": value.promoted,
        "location": value.location,
        "spatial": value.spatial,
        "spatial_ref": value.spatial_ref,
        "comparison": value.comparison,
        "value": value.value,
    }


def state_guard_from_dict(data: Mapping[str, Any], path: str) -> RuleStateGuard:
    data = _require_mapping(data, path)
    aggregation = _require_member(
        _require_str(_require_field(data, "aggregation", path), f"{path}.aggregation"),
        AGGREGATIONS,
        f"{path}.aggregation",
        "AGGREGATION_INVALID",
    )
    owner = _require_member(
        _require_str(_require_field(data, "owner", path), f"{path}.owner"),
        SELECTOR_OWNERS,
        f"{path}.owner",
        "OWNER_INVALID",
    )
    type_mode = _require_member(
        _require_str(_require_field(data, "type_mode", path), f"{path}.type_mode"),
        SELECTOR_TYPE_MODES,
        f"{path}.type_mode",
        "TYPE_MODE_INVALID",
    )
    promoted = _require_member(
        _require_str(_require_field(data, "promoted", path), f"{path}.promoted"),
        SELECTOR_PROMOTED,
        f"{path}.promoted",
        "PROMOTED_INVALID",
    )
    location = _require_member(
        _require_str(_require_field(data, "location", path), f"{path}.location"),
        SELECTOR_LOCATIONS,
        f"{path}.location",
        "LOCATION_INVALID",
    )
    spatial = _require_member(
        _require_str(_require_field(data, "spatial", path), f"{path}.spatial"),
        SELECTOR_SPATIAL,
        f"{path}.spatial",
        "SPATIAL_INVALID",
    )
    spatial_ref = _require_member(
        _require_str(data.get("spatial_ref", "TARGET"), f"{path}.spatial_ref"),
        SELECTOR_SPATIAL_REFS,
        f"{path}.spatial_ref",
        "SPATIAL_REF_INVALID",
    )
    comparison = _require_member(
        _require_str(data.get("comparison", "eq"), f"{path}.comparison"),
        COMPARISON_OPS,
        f"{path}.comparison",
        "COMPARISON_INVALID",
    )
    value = _require_int(data.get("value", 0), f"{path}.value")
    return RuleStateGuard(
        aggregation=aggregation,
        owner=owner,
        type_mode=type_mode,
        promoted=promoted,
        location=location,
        spatial=spatial,
        spatial_ref=spatial_ref,
        comparison=comparison,
        value=value,
    )


def aux_state_to_dict(value: RuleAuxState) -> dict:
    return {"name": value.name, "kind": value.kind, "lifetime": value.lifetime}


def aux_state_from_dict(data: Mapping[str, Any], path: str) -> RuleAuxState:
    data = _require_mapping(data, path)
    name = _require_str(_require_field(data, "name", path), f"{path}.name")
    kind = _require_member(
        _require_str(_require_field(data, "kind", path), f"{path}.kind"),
        AUX_STATE_KINDS,
        f"{path}.kind",
        "AUX_KIND_INVALID",
    )
    lifetime = _require_member(
        _require_str(_require_field(data, "lifetime", path), f"{path}.lifetime"),
        AUX_LIFETIMES,
        f"{path}.lifetime",
        "AUX_LIFETIME_INVALID",
    )
    return RuleAuxState(name=name, kind=kind, lifetime=lifetime)


def effect_to_dict(value: RuleActionEffect) -> dict:
    return {
        "kind": value.kind,
        "square_ref": value.square_ref,
        "slot_name": value.slot_name,
        "type_id": value.type_id,
    }


def effect_from_dict(data: Mapping[str, Any], path: str) -> RuleActionEffect:
    data = _require_mapping(data, path)
    kind = _require_member(
        _require_str(_require_field(data, "kind", path), f"{path}.kind"),
        SEMANTIC_EFFECT_KINDS,
        f"{path}.kind",
        "EFFECT_KIND_INVALID",
    )
    square_ref = _require_member(
        _require_str(data.get("square_ref", "target"), f"{path}.square_ref"),
        EFFECT_SQUARE_REFS,
        f"{path}.square_ref",
        "EFFECT_SQUARE_REF_INVALID",
    )
    slot_name = data.get("slot_name")
    if slot_name is not None:
        slot_name = _require_str(slot_name, f"{path}.slot_name")
    type_id = data.get("type_id")
    if type_id is not None:
        type_id = _require_str(type_id, f"{path}.type_id")
    return RuleActionEffect(
        kind=kind, square_ref=square_ref, slot_name=slot_name, type_id=type_id
    )


def invariant_to_dict(value: RuleInvariant) -> dict:
    return {"kind": value.kind, "square_refs": list(value.square_refs)}


def invariant_from_dict(data: Mapping[str, Any], path: str) -> RuleInvariant:
    data = _require_mapping(data, path)
    kind = _require_member(
        _require_str(_require_field(data, "kind", path), f"{path}.kind"),
        INVARIANT_KINDS,
        f"{path}.kind",
        "INVARIANT_KIND_INVALID",
    )
    square_refs_raw = data.get("square_refs", [])
    if not isinstance(square_refs_raw, list):
        raise _err("FIELD_NOT_LIST", f"{path}.square_refs", "square_refs must be a list")
    square_refs = tuple(
        _require_member(
            _require_str(ref, f"{path}.square_refs[{i}]"),
            ("SOURCE", "TARGET", "FIXED_SQUARE", "AUX_SLOT"),
            f"{path}.square_refs[{i}]",
            "SQUARE_REF_INVALID",
        )
        for i, ref in enumerate(square_refs_raw)
    )
    if len(square_refs) > MAX_SQUARES_NOT_ATTACKED:
        raise _err(
            "INVARIANT_SQUARES_TOO_MANY",
            f"{path}.square_refs",
            f"squares_not_attacked supports at most {MAX_SQUARES_NOT_ATTACKED} refs",
        )
    return RuleInvariant(kind=kind, square_refs=square_refs)


def postcondition_to_dict(value: RulePostcondition) -> dict:
    return {"kind": value.kind, "max_stratum": value.max_stratum}


def postcondition_from_dict(data: Mapping[str, Any], path: str) -> RulePostcondition:
    data = _require_mapping(data, path)
    kind = _require_member(
        _require_str(_require_field(data, "kind", path), f"{path}.kind"),
        POSTCONDITION_KINDS,
        f"{path}.kind",
        "POSTCONDITION_KIND_INVALID",
    )
    max_stratum = _require_member(
        _require_str(data.get("max_stratum", "S3"), f"{path}.max_stratum"),
        SEMANTIC_STRATA,
        f"{path}.max_stratum",
        "MAX_STRATUM_INVALID",
    )
    return RulePostcondition(kind=kind, max_stratum=max_stratum)


def semantic_action_to_dict(value: RuleSemanticAction) -> dict:
    return {
        "name": value.name,
        "type_ids": list(value.type_ids),
        "geometry": list(value.geometry),
        "target_relation": value.target_relation,
        "path_constraints": [path_constraint_to_dict(c) for c in value.path_constraints],
        "state_guards": [state_guard_to_dict(g) for g in value.state_guards],
        "slot_guards": [slot_guard_to_dict(g) for g in value.slot_guards],
        "aux_state": [aux_state_to_dict(a) for a in value.aux_state],
        "effects": [effect_to_dict(e) for e in value.effects],
        "invariants": [invariant_to_dict(i) for i in value.invariants],
        "postconditions": [postcondition_to_dict(p) for p in value.postconditions],
    }


def semantic_action_from_dict(data: Mapping[str, Any], path: str) -> RuleSemanticAction:
    data = _require_mapping(data, path)
    name = _require_str(_require_field(data, "name", path), f"{path}.name")
    type_ids = _require_str_list(
        _require_field(data, "type_ids", path), f"{path}.type_ids"
    )
    geometry_raw = _require_str_list(_require_field(data, "geometry", path), f"{path}.geometry")
    geometry = tuple(
        _require_member(g, SEMANTIC_GEOMETRY_KINDS, f"{path}.geometry", "GEOMETRY_KIND_INVALID")
        for g in geometry_raw
    )
    if not geometry:
        raise _err("GEOMETRY_EMPTY", f"{path}.geometry", "geometry must be non-empty")
    target_relation = _require_member(
        _require_str(
            _require_field(data, "target_relation", path), f"{path}.target_relation"
        ),
        TARGET_RELATIONS,
        f"{path}.target_relation",
        "TARGET_RELATION_INVALID",
    )
    return RuleSemanticAction(
        name=name,
        type_ids=type_ids,
        geometry=geometry,
        target_relation=target_relation,
        path_constraints=tuple(
            path_constraint_from_dict(item, f"{path}.path_constraints[{i}]")
            for i, item in enumerate(data.get("path_constraints", ()))
        ),
        state_guards=tuple(
            state_guard_from_dict(item, f"{path}.state_guards[{i}]")
            for i, item in enumerate(data.get("state_guards", ()))
        ),
        slot_guards=tuple(
            slot_guard_from_dict(item, f"{path}.slot_guards[{i}]")
            for i, item in enumerate(data.get("slot_guards", ()))
        ),
        aux_state=tuple(
            aux_state_from_dict(item, f"{path}.aux_state[{i}]")
            for i, item in enumerate(data.get("aux_state", ()))
        ),
        effects=tuple(
            effect_from_dict(item, f"{path}.effects[{i}]")
            for i, item in enumerate(data.get("effects", ()))
        ),
        invariants=tuple(
            invariant_from_dict(item, f"{path}.invariants[{i}]")
            for i, item in enumerate(data.get("invariants", ()))
        ),
        postconditions=tuple(
            postcondition_from_dict(item, f"{path}.postconditions[{i}]")
            for i, item in enumerate(data.get("postconditions", ()))
        ),
    )


def ruleset_to_dict(ruleset: RuleSet, include_metadata: bool = True) -> dict[str, Any]:
    """Convert a RuleSet to a JSON-friendly dict with canonical ordering."""
    piece_types = []
    for pt in ruleset.piece_types:
        piece_types.append(
            {
                "type_id": pt.type_id,
                "name": pt.name,
                "movement_atoms": [atom_to_dict(a) for a in pt.movement_atoms],
                "is_anchor": pt.is_anchor,
                "is_promotable": pt.is_promotable,
                "promotion_target_ids": list(pt.promotion_target_ids),
            }
        )
    initial_position = [
        [None if cell is None else piece_to_dict(cell) for cell in row]
        for row in ruleset.initial_position
    ]
    drop_allowed = {
        tid: [[bool(b) for b in mask] for mask in masks] for tid, masks in ruleset.drop_allowed.items()
    }
    promotion_allowed = {
        tid: [
            sorted(([a.file, a.rank, b.file, b.rank] for a, b in pairs))
            for pairs in masks
        ]
        for tid, masks in ruleset.promotion_allowed.items()
    }
    promotion_forced = {
        tid: [sorted([s.file, s.rank] for s in squares) for squares in masks]
        for tid, masks in ruleset.promotion_forced.items()
    }
    data: dict[str, Any] = {
        "schema_version": ruleset.schema_version,
        "board_size": ruleset.board_size,
        "piece_types": piece_types,
        "initial_position": initial_position,
        "drop_allowed": drop_allowed,
        "promotion_allowed": promotion_allowed,
        "promotion_forced": promotion_forced,
        "repetition_limit": ruleset.repetition_limit,
        "max_ply": ruleset.max_ply,
        "stalemate_result": ruleset.stalemate_result,
    }
    # Additive semantic actions: emitted only when non-empty so legacy
    # serialization (and therefore fingerprints) stays byte-identical.
    if ruleset.semantic_actions:
        data["semantic_actions"] = [
            semantic_action_to_dict(a) for a in ruleset.semantic_actions
        ]
    if include_metadata:
        data["metadata"] = dict(ruleset.metadata)
    return data


def ruleset_from_dict(data: Mapping[str, Any]) -> RuleSet:
    """Strictly parse a RuleSet dict; malformed input raises RuleValidationError."""
    path = "ruleset"
    data = _require_mapping(data, path)
    schema_version = _require_int(data.get("schema_version", 1), f"{path}.schema_version")
    board_size = _require_int(_require_field(data, "board_size", path), f"{path}.board_size")
    if board_size < 3:
        raise _err(
            "BOARD_SIZE_TOO_SMALL", f"{path}.board_size", "board_size must be an integer >= 3"
        )

    piece_types_raw = _require_field(data, "piece_types", path)
    if not isinstance(piece_types_raw, list):
        raise _err("FIELD_NOT_LIST", f"{path}.piece_types", "piece_types must be a list")
    piece_types_list: list[PieceType] = []
    for i, raw in enumerate(piece_types_raw):
        p_path = f"{path}.piece_types[{i}]"
        raw = _require_mapping(raw, p_path)
        type_id = _require_str(_require_field(raw, "type_id", p_path), f"{p_path}.type_id")
        name = _require_str(raw.get("name", type_id), f"{p_path}.name")
        atoms_raw = _require_field(raw, "movement_atoms", p_path)
        if not isinstance(atoms_raw, list):
            raise _err("FIELD_NOT_LIST", f"{p_path}.movement_atoms", "movement_atoms must be a list")
        is_anchor = _require_bool(raw.get("is_anchor", False), f"{p_path}.is_anchor")
        is_promotable = _require_bool(
            raw.get("is_promotable", False), f"{p_path}.is_promotable"
        )
        targets = _require_str_list(
            raw.get("promotion_target_ids", ()), f"{p_path}.promotion_target_ids"
        )
        piece_types_list.append(
            PieceType(
                type_id=type_id,
                name=name,
                movement_atoms=tuple(atom_from_dict(a, f"{p_path}.movement_atoms[{j}]") for j, a in enumerate(atoms_raw)),
                is_anchor=is_anchor,
                is_promotable=is_promotable,
                promotion_target_ids=targets,
            )
        )
    piece_types = tuple(piece_types_list)

    initial_raw = _require_field(data, "initial_position", path)
    if not isinstance(initial_raw, list) or any(not isinstance(row, list) for row in initial_raw):
        raise _err(
            "FIELD_NOT_LIST",
            f"{path}.initial_position",
            "initial_position must be a list of rows",
        )
    initial_position = tuple(
        tuple(
            None
            if cell is None
            else piece_from_dict(cell, f"{path}.initial_position[{r}][{f}]")
            for f, cell in enumerate(row)
        )
        for r, row in enumerate(initial_raw)
    )

    drop_raw = _require_mapping(data.get("drop_allowed", {}), f"{path}.drop_allowed")
    drop_allowed: dict[str, tuple[tuple[bool, ...], ...]] = {}
    for tid, masks in drop_raw.items():
        d_path = f"{path}.drop_allowed[{tid}]"
        if not isinstance(masks, list) or len(masks) != 2:
            raise _err("DROP_MASK_BAD_SHAPE", d_path, "expected two player masks")
        players: list[tuple[bool, ...]] = []
        for player, mask in enumerate(masks):
            m_path = f"{d_path}[{player}]"
            if not isinstance(mask, list):
                raise _err("DROP_MASK_BAD_SHAPE", m_path, "mask must be a list of booleans")
            players.append(
                tuple(
                    _require_bool(b, f"{m_path}[{i}]", "DROP_MASK_BAD_TYPE")
                    for i, b in enumerate(mask)
                )
            )
        drop_allowed[tid] = tuple(players)

    promo_raw = _require_mapping(data.get("promotion_allowed", {}), f"{path}.promotion_allowed")
    promotion_allowed: dict[str, tuple[frozenset[tuple[Square, Square]], ...]] = {}
    for tid, masks in promo_raw.items():
        p_path = f"{path}.promotion_allowed[{tid}]"
        if not isinstance(masks, list) or len(masks) != 2:
            raise _err("PROMOTION_MASK_BAD_SHAPE", p_path, "expected two player masks")
        players: list[frozenset[tuple[Square, Square]]] = []
        for player, pairs in enumerate(masks):
            q_path = f"{p_path}[{player}]"
            if not isinstance(pairs, list):
                raise _err("PROMOTION_MASK_BAD_SHAPE", q_path, "pairs must be a list")
            squares: set[tuple[Square, Square]] = set()
            for i, a in enumerate(pairs):
                q = _require_int_quad(a, f"{q_path}[{i}]")
                squares.add((Square(q[0], q[1]), Square(q[2], q[3])))
            players.append(frozenset(squares))
        promotion_allowed[tid] = tuple(players)

    forced_raw = _require_mapping(data.get("promotion_forced", {}), f"{path}.promotion_forced")
    promotion_forced: dict[str, tuple[frozenset[Square], ...]] = {}
    for tid, masks in forced_raw.items():
        p_path = f"{path}.promotion_forced[{tid}]"
        if not isinstance(masks, list) or len(masks) != 2:
            raise _err("PROMOTION_MASK_BAD_SHAPE", p_path, "expected two player masks")
        players: list[frozenset[Square]] = []
        for player, squares in enumerate(masks):
            q_path = f"{p_path}[{player}]"
            if not isinstance(squares, list):
                raise _err("PROMOTION_MASK_BAD_SHAPE", q_path, "squares must be a list")
            fs: set[Square] = set()
            for i, s in enumerate(squares):
                q = _require_int_pair(s, f"{q_path}[{i}]")
                fs.add(Square(q[0], q[1]))
            players.append(frozenset(fs))
        promotion_forced[tid] = tuple(players)

    repetition_limit = _require_int(
        data.get("repetition_limit", 4), f"{path}.repetition_limit", "REPETITION_LIMIT_INVALID"
    )
    max_ply = _require_int(data.get("max_ply", 512), f"{path}.max_ply", "MAX_PLY_INVALID")
    stalemate_result = _require_str(
        data.get("stalemate_result", "draw"), f"{path}.stalemate_result"
    )
    semantic_actions_raw = data.get("semantic_actions", ())
    if not isinstance(semantic_actions_raw, (list, tuple)):
        raise _err(
            "FIELD_NOT_LIST", f"{path}.semantic_actions", "semantic_actions must be a list"
        )
    semantic_actions = tuple(
        semantic_action_from_dict(item, f"{path}.semantic_actions[{i}]")
        for i, item in enumerate(semantic_actions_raw)
    )
    metadata = _require_mapping(data.get("metadata", {}), f"{path}.metadata")

    return RuleSet(
        schema_version=schema_version,
        board_size=board_size,
        piece_types=piece_types,
        initial_position=initial_position,
        drop_allowed=drop_allowed,
        promotion_allowed=promotion_allowed,
        promotion_forced=promotion_forced,
        repetition_limit=repetition_limit,
        max_ply=max_ply,
        stalemate_result=stalemate_result,
        semantic_actions=semantic_actions,
        metadata=dict(metadata),
    )


def canonical_json(data: Any) -> str:
    """Deterministic JSON: sorted keys, compact separators, ASCII-safe."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_fingerprint(ruleset: RuleSet) -> str:
    """SHA-256 of the canonical JSON of all semantic fields (no metadata)."""
    payload = canonical_json(ruleset_to_dict(ruleset, include_metadata=False))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
