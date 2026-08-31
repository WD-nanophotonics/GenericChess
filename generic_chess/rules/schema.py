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


SEMANTIC_DSL_VERSION = 2
REPETITION_POLICIES = ("draw", "continuous_check_loss")
AUTOMATIC_ADJUDICATION_OUTCOMES = ("NO_CONTEST",)
AUTOMATIC_ADJUDICATION_POLICIES = ("threshold_actor_continuous_check",)


@dataclass(frozen=True, slots=True)
class RuleAutomaticAdjudication:
    """Optional generic state adjudication triggered by completed plies."""

    adjudication_id: str
    trigger_ply: int
    outcome: str = "NO_CONTEST"
    continuation_policy: str = "threshold_actor_continuous_check"


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
    # Generic policy for a repeated position.  ``draw`` is the historical
    # default; continuous-check adjudication is opt-in per ruleset.
    repetition_policy: str = "draw"
    max_ply: int = 512
    stalemate_result: str = "draw"
    # Additive high-level semantic actions (Phase 1.9B-1).  Omitted/empty
    # keeps legacy semantics; the legacy compiler refuses non-empty values
    # (fail-closed) and ``compile_semantic_ruleset`` is the IR entry point.
    semantic_actions: tuple["RuleSemanticAction", ...] = ()
    semantic_dsl_version: int = SEMANTIC_DSL_VERSION
    # Optional action-independent claims; omitted from legacy JSON when empty.
    declarations: tuple[RuleDeclaration, ...] = ()
    # Optional action-independent automatic adjudication; omitted when empty
    # so historical serialized rulesets and fingerprints remain unchanged.
    automatic_adjudications: tuple[RuleAutomaticAdjudication, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------- semantic DSL

PATH_CONSTRAINT_KINDS = (
    "path_clear",
    "path_count_eq",
    "path_count_range",
    "path_first_blocker_owner",
    "path_last_blocker_owner",
)
GEOMETRY_SPEC_KINDS = ("legacy_atoms", "leap", "ray", "drop")
TARGET_RELATIONS = ("empty", "enemy", "friendly", "any")
SELECTOR_OWNERS = ("self", "opponent", "any")
SELECTOR_PROMOTED = ("yes", "no", "any")
SELECTOR_LOCATIONS = ("board", "hand")
AGGREGATIONS = ("exists", "count")
COMPARISON_OPS = ("eq", "ne", "lt", "le", "gt", "ge")
SEMANTIC_EFFECT_KINDS = (
    "move",
    "remove",
    "remove_from_hand",
    "place",
    "set_current_type",
    "set_bool",
    "clear_right",
    "set_token",
    "clear_token",
    "shift",
)
AUX_VALUE_KINDS = ("bool", "square_or_none")
AUX_SCOPES = ("global", "per_owner")
AUX_LIFETIMES = ("persistent", "expire_next_turn")
INVARIANT_KINDS = ("own_anchor_safe", "squares_not_attacked")
POSTCONDITION_KINDS = (
    "opponent_checked",
    "action_delivers_check",
    "no_legal_reply",
)
SEMANTIC_STRATA = ("S0", "S1", "S2", "S3", "S4", "S5")
TYPE_REF_KINDS = ("action_base", "action_current", "explicit", "any")
SQUARE_REF_KINDS = (
    "source",
    "target",
    "fixed",
    "offset_from_source",
    "offset_from_target",
    "path_step",
    "aux_slot_square",
)
SPATIAL_KINDS = (
    "same_file",
    "same_rank",
    "exact",
    "adjacent",
    "path_between",
    "zone",
)
COMPOSITION_KINDS = ("augment", "replace_legacy")
TRIGGER_EVENTS = ("piece_leaves_square", "piece_removed_from_square")
DISPOSITIONS = ("capture_to_hand", "remove_from_game")
PROMOTION_MODES = ("none", "inherit_compiled_masks", "explicit")
ACTION_FAMILIES = ("board", "drop")

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
class RuleGeometrySpec:
    """Typed exact geometry.  ``legacy_atoms`` selects the piece type's
    existing movement atoms (resolved to explicit atom ids by the compiler);
    ``leap``/``ray`` describe an explicit owner-relative shape; ``drop`` has
    no source."""

    kind: str
    atom_kind: str | None = None       # leap | ray for kind == legacy_atoms
    offset: tuple[int, int] | None = None      # leap
    direction: tuple[int, int] | None = None   # ray
    min_steps: int | None = None               # ray (>= 1)
    max_steps: int | None = None               # ray (>= min_steps or None)
    owner_relative: bool = True


@dataclass(frozen=True, slots=True)
class RuleTypeRef:
    """Explicit type binding for selectors and effect operands."""

    kind: str            # action_base | action_current | explicit | any
    type_id: str | None = None


@dataclass(frozen=True, slots=True)
class RuleSquareRef:
    """Typed, self-resolving square reference (no placeholder strings)."""

    kind: str            # source | target | fixed | offset_from_source |
                         # offset_from_target | path_step | aux_slot_square
    square: tuple[int, int] | None = None
    offset: tuple[int, int] | None = None
    owner_relative: bool = True
    step: int | None = None
    slot_name: str | None = None


@dataclass(frozen=True, slots=True)
class RuleSpatialSelector:
    """Parameterized spatial selector (zone carries an explicit square set)."""

    kind: str
    refs: tuple[RuleSquareRef, ...] = ()
    zone_squares: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True, slots=True)
class RuleStateGuard:
    aggregation: str
    owner: str
    type_ref: RuleTypeRef
    compare_field: str           # base | current
    promoted: str
    location: str
    spatial: RuleSpatialSelector
    comparison: str = "eq"
    value: int = 0
    subject_ref: RuleSquareRef | None = None


DECLARATION_OUTCOMES = ("WIN", "RESTART", "LOSS")


@dataclass(frozen=True, slots=True)
class RuleWeightedMaterialMetric:
    """Generic board/hand integer scoring used by an out-of-band claim."""

    owner: str = "self"
    compare_field: str = "base"
    weights: Mapping[str, int] = field(default_factory=dict)
    spatial: RuleSpatialSelector | None = None
    include_hands: bool = False


@dataclass(frozen=True, slots=True)
class RuleDeclarationOutcomeBand:
    """An ordered inclusive score threshold and its generic outcome."""

    threshold: int
    outcome: str


@dataclass(frozen=True, slots=True)
class RuleDeclaration:
    """An optional, action-independent player declaration/claim."""

    declaration_id: str
    owner: int
    state_guards: tuple[RuleStateGuard, ...] = ()
    require_not_in_check: bool = True
    ply_limit: int | None = None
    weighted_metric: RuleWeightedMaterialMetric | None = None
    outcome_bands: tuple[RuleDeclarationOutcomeBand, ...] = ()
    failure_outcome: str = "LOSS"


@dataclass(frozen=True, slots=True)
class RuleAuxState:
    name: str
    value_kind: str              # bool | square_or_none
    scope: str                   # global | per_owner
    lifetime: str
    initial: int | tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class RuleSlotGuard:
    """Typed pre-action slot guard (bool or square comparison)."""

    slot_name: str
    comparison: str = "eq"
    value: int | None = None             # bool comparison (0/1)
    square_ref: RuleSquareRef | None = None  # square comparison


@dataclass(frozen=True, slots=True)
class RuleActionEffect:
    kind: str
    from_ref: RuleSquareRef | None = None
    to_ref: RuleSquareRef | None = None
    square_ref: RuleSquareRef | None = None
    piece_owner: str = "self"
    piece_type_ref: RuleTypeRef | None = None
    disposition: str | None = None       # capture_to_hand | remove_from_game
    slot_name: str | None = None
    type_ref: RuleTypeRef | None = None
    count: int = 1
    value: int | None = None


@dataclass(frozen=True, slots=True)
class RuleInvariant:
    kind: str
    square_refs: tuple[RuleSquareRef, ...] = ()


@dataclass(frozen=True, slots=True)
class RulePostcondition:
    kind: str
    max_stratum: str = "S3"


@dataclass(frozen=True, slots=True)
class RuleReplaceSelector:
    """Typed selector for REPLACE_LEGACY composition (never name-based)."""

    type_ids: tuple[str, ...]
    action_family: str           # board | drop
    target_relation: str
    geometry_kind: str | None = None
    replace_all_matching: bool = False


@dataclass(frozen=True, slots=True)
class RuleTransitionTrigger:
    """Generic auxiliary invalidation trigger (no game names)."""

    slot_name: str
    event: str                   # piece_leaves_square | piece_removed_from_square
    square_ref: RuleSquareRef
    owner: str = "self"


@dataclass(frozen=True, slots=True)
class RuleSemanticAction:
    """High-level (definition-layer) semantic action template."""

    name: str
    type_ids: tuple[str, ...]
    geometry: RuleGeometrySpec
    target_relation: str
    composition: str = "augment"          # augment | replace_legacy
    replace_selector: RuleReplaceSelector | None = None
    path_constraints: tuple[RulePathConstraint, ...] = ()
    state_guards: tuple[RuleStateGuard, ...] = ()
    slot_guards: tuple[RuleSlotGuard, ...] = ()
    aux_state: tuple[RuleAuxState, ...] = ()
    effects: tuple[RuleActionEffect, ...] = ()
    invariants: tuple[RuleInvariant, ...] = ()
    postconditions: tuple[RulePostcondition, ...] = ()
    promotion_mode: str = "none"          # none | inherit_compiled_masks | explicit
    explicit_promotion_type: str | None = None
    triggers: tuple[RuleTransitionTrigger, ...] = ()


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


def geometry_spec_to_dict(value: RuleGeometrySpec) -> dict:
    return {
        "kind": value.kind,
        "atom_kind": value.atom_kind,
        "offset": list(value.offset) if value.offset else None,
        "direction": list(value.direction) if value.direction else None,
        "min_steps": value.min_steps,
        "max_steps": value.max_steps,
        "owner_relative": value.owner_relative,
    }


def geometry_spec_from_dict(data: Mapping[str, Any], path: str) -> RuleGeometrySpec:
    data = _require_mapping(data, path)
    kind = _require_member(
        _require_str(_require_field(data, "kind", path), f"{path}.kind"),
        GEOMETRY_SPEC_KINDS,
        f"{path}.kind",
        "GEOMETRY_SPEC_KIND_INVALID",
    )
    atom_kind = data.get("atom_kind")
    if atom_kind is not None:
        atom_kind = _require_member(
            _require_str(atom_kind, f"{path}.atom_kind"),
            ("leap", "ray"),
            f"{path}.atom_kind",
            "ATOM_KIND_INVALID",
        )
    offset = data.get("offset")
    if offset is not None:
        offset = tuple(_require_int_pair(offset, f"{path}.offset"))
    direction = data.get("direction")
    if direction is not None:
        direction = tuple(_require_int_pair(direction, f"{path}.direction"))
    min_steps = data.get("min_steps")
    if min_steps is not None:
        min_steps = _require_int(min_steps, f"{path}.min_steps")
        if min_steps < 1:
            raise _err("GEOMETRY_MIN_STEPS_INVALID", f"{path}.min_steps", "min_steps >= 1")
    max_steps = data.get("max_steps")
    if max_steps is not None:
        max_steps = _require_int(max_steps, f"{path}.max_steps")
    if min_steps is not None and max_steps is not None and max_steps < min_steps:
        raise _err("GEOMETRY_MAX_STEPS_INVALID", f"{path}.max_steps", "max_steps >= min_steps")
    owner_relative = _require_bool(data.get("owner_relative", True), f"{path}.owner_relative")
    if kind == "drop":
        if offset or direction or min_steps or max_steps:
            raise _err("GEOMETRY_DROP_HAS_SHAPE", f"{path}", "drop geometry takes no shape")
    if kind == "leap" and offset is None:
        raise _err("GEOMETRY_LEAP_NO_OFFSET", f"{path}", "leap requires an offset")
    if kind == "ray" and direction is None:
        raise _err("GEOMETRY_RAY_NO_DIRECTION", f"{path}", "ray requires a direction")
    return RuleGeometrySpec(
        kind=kind,
        atom_kind=atom_kind,
        offset=offset,
        direction=direction,
        min_steps=min_steps,
        max_steps=max_steps,
        owner_relative=owner_relative,
    )


def type_ref_to_dict(value: RuleTypeRef) -> dict:
    return {"kind": value.kind, "type_id": value.type_id}


def type_ref_from_dict(data: Mapping[str, Any], path: str) -> RuleTypeRef:
    data = _require_mapping(data, path)
    kind = _require_member(
        _require_str(_require_field(data, "kind", path), f"{path}.kind"),
        TYPE_REF_KINDS,
        f"{path}.kind",
        "TYPE_REF_KIND_INVALID",
    )
    type_id = data.get("type_id")
    if type_id is not None:
        type_id = _require_str(type_id, f"{path}.type_id")
    if kind == "explicit" and not type_id:
        raise _err("TYPE_REF_EXPLICIT_NO_ID", f"{path}", "explicit type ref requires type_id")
    if kind != "explicit" and type_id is not None:
        raise _err("TYPE_REF_ID_ONLY_EXPLICIT", f"{path}", "type_id only for explicit")
    return RuleTypeRef(kind=kind, type_id=type_id)


def square_ref_to_dict(value: RuleSquareRef) -> dict:
    return {
        "kind": value.kind,
        "square": list(value.square) if value.square else None,
        "offset": list(value.offset) if value.offset else None,
        "owner_relative": value.owner_relative,
        "step": value.step,
        "slot_name": value.slot_name,
    }


def square_ref_from_dict(data: Mapping[str, Any], path: str) -> RuleSquareRef:
    data = _require_mapping(data, path)
    kind = _require_member(
        _require_str(_require_field(data, "kind", path), f"{path}.kind"),
        SQUARE_REF_KINDS,
        f"{path}.kind",
        "SQUARE_REF_KIND_INVALID",
    )
    square = data.get("square")
    if square is not None:
        square = tuple(_require_int_pair(square, f"{path}.square"))
    offset = data.get("offset")
    if offset is not None:
        offset = tuple(_require_int_pair(offset, f"{path}.offset"))
    owner_relative = _require_bool(data.get("owner_relative", True), f"{path}.owner_relative")
    step = data.get("step")
    if step is not None:
        step = _require_int(step, f"{path}.step")
        if step < 0:
            raise _err("PATH_STEP_NEGATIVE", f"{path}.step", "step must be >= 0")
    slot_name = data.get("slot_name")
    if slot_name is not None:
        slot_name = _require_str(slot_name, f"{path}.slot_name")
    if kind == "fixed" and square is None:
        raise _err("SQUARE_REF_FIXED_NO_SQUARE", f"{path}", "fixed ref requires square")
    if kind in ("offset_from_source", "offset_from_target") and offset is None:
        raise _err("SQUARE_REF_OFFSET_MISSING", f"{path}", "offset ref requires offset")
    if kind == "path_step" and step is None:
        raise _err("SQUARE_REF_STEP_MISSING", f"{path}", "path_step requires step")
    if kind == "aux_slot_square" and not slot_name:
        raise _err("SQUARE_REF_SLOT_MISSING", f"{path}", "aux_slot_square requires slot_name")
    return RuleSquareRef(
        kind=kind,
        square=square,
        offset=offset,
        owner_relative=owner_relative,
        step=step,
        slot_name=slot_name,
    )


def spatial_selector_to_dict(value: RuleSpatialSelector) -> dict:
    return {
        "kind": value.kind,
        "refs": [square_ref_to_dict(r) for r in value.refs],
        "zone_squares": [list(s) for s in value.zone_squares],
    }


def spatial_selector_from_dict(data: Mapping[str, Any], path: str) -> RuleSpatialSelector:
    data = _require_mapping(data, path)
    kind = _require_member(
        _require_str(_require_field(data, "kind", path), f"{path}.kind"),
        SPATIAL_KINDS,
        f"{path}.kind",
        "SPATIAL_KIND_INVALID",
    )
    refs_raw = data.get("refs", ())
    refs = tuple(
        square_ref_from_dict(item, f"{path}.refs[{i}]") for i, item in enumerate(refs_raw)
    )
    zone_raw = data.get("zone_squares", ())
    zone = tuple(tuple(_require_int_pair(s, f"{path}.zone_squares[{i}]")) for i, s in enumerate(zone_raw))
    if kind in ("same_file", "same_rank", "exact", "adjacent") and len(refs) != 1:
        raise _err("SPATIAL_REF_COUNT", f"{path}.refs", f"{kind} requires exactly 1 ref")
    if kind == "path_between" and len(refs) != 2:
        raise _err("SPATIAL_REF_COUNT", f"{path}.refs", "path_between requires 2 refs")
    if kind == "zone" and not zone:
        raise _err("SPATIAL_ZONE_EMPTY", f"{path}.zone_squares", "zone requires squares")
    return RuleSpatialSelector(kind=kind, refs=refs, zone_squares=zone)


def state_guard_to_dict(
    value: RuleStateGuard, *, include_none_subject_ref: bool = True
) -> dict:
    data = {
        "aggregation": value.aggregation,
        "owner": value.owner,
        "type_ref": type_ref_to_dict(value.type_ref),
        "compare_field": value.compare_field,
        "promoted": value.promoted,
        "location": value.location,
        "spatial": spatial_selector_to_dict(value.spatial),
        "comparison": value.comparison,
        "value": value.value,
    }
    if value.subject_ref is not None or include_none_subject_ref:
        data["subject_ref"] = (
            square_ref_to_dict(value.subject_ref) if value.subject_ref is not None else None
        )
    return data


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
    type_ref = type_ref_from_dict(
        _require_mapping(_require_field(data, "type_ref", path), f"{path}.type_ref"),
        f"{path}.type_ref",
    )
    compare_field = _require_member(
        _require_str(_require_field(data, "compare_field", path), f"{path}.compare_field"),
        ("base", "current"),
        f"{path}.compare_field",
        "COMPARE_FIELD_INVALID",
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
    spatial = spatial_selector_from_dict(
        _require_mapping(_require_field(data, "spatial", path), f"{path}.spatial"),
        f"{path}.spatial",
    )
    comparison = _require_member(
        _require_str(data.get("comparison", "eq"), f"{path}.comparison"),
        COMPARISON_OPS,
        f"{path}.comparison",
        "COMPARISON_INVALID",
    )
    value = _require_int(data.get("value", 0), f"{path}.value")
    subject_raw = data.get("subject_ref")
    subject_ref = (
        None
        if subject_raw is None
        else square_ref_from_dict(
            _require_mapping(subject_raw, f"{path}.subject_ref"),
            f"{path}.subject_ref",
        )
    )
    return RuleStateGuard(
        aggregation=aggregation,
        owner=owner,
        type_ref=type_ref,
        compare_field=compare_field,
        promoted=promoted,
        location=location,
        spatial=spatial,
        comparison=comparison,
        value=value,
        subject_ref=subject_ref,
    )


def weighted_material_metric_to_dict(value: RuleWeightedMaterialMetric) -> dict:
    return {
        "owner": value.owner,
        "compare_field": value.compare_field,
        "weights": dict(sorted(value.weights.items())),
        "spatial": spatial_selector_to_dict(value.spatial) if value.spatial else None,
        "include_hands": value.include_hands,
    }


def weighted_material_metric_from_dict(
    data: Mapping[str, Any], path: str
) -> RuleWeightedMaterialMetric:
    data = _require_mapping(data, path)
    owner = _require_member(
        _require_str(data.get("owner", "self"), f"{path}.owner"),
        SELECTOR_OWNERS,
        f"{path}.owner",
        "OWNER_INVALID",
    )
    compare_field = _require_member(
        _require_str(data.get("compare_field", "base"), f"{path}.compare_field"),
        ("base", "current"),
        f"{path}.compare_field",
        "COMPARE_FIELD_INVALID",
    )
    weights_raw = _require_mapping(data.get("weights", {}), f"{path}.weights")
    weights: dict[str, int] = {}
    for type_id, weight in weights_raw.items():
        if not isinstance(type_id, str) or not type_id:
            raise _err("WEIGHT_TYPE_INVALID", f"{path}.weights", "type IDs must be strings")
        weights[type_id] = _require_int(weight, f"{path}.weights[{type_id!r}]")
    spatial_raw = data.get("spatial")
    spatial = (
        None
        if spatial_raw is None
        else spatial_selector_from_dict(
            _require_mapping(spatial_raw, f"{path}.spatial"), f"{path}.spatial"
        )
    )
    include_hands = _require_bool(data.get("include_hands", False), f"{path}.include_hands")
    return RuleWeightedMaterialMetric(
        owner=owner,
        compare_field=compare_field,
        weights=weights,
        spatial=spatial,
        include_hands=include_hands,
    )


def declaration_outcome_band_to_dict(value: RuleDeclarationOutcomeBand) -> dict:
    return {"threshold": value.threshold, "outcome": value.outcome}


def declaration_outcome_band_from_dict(
    data: Mapping[str, Any], path: str
) -> RuleDeclarationOutcomeBand:
    data = _require_mapping(data, path)
    threshold = _require_int(_require_field(data, "threshold", path), f"{path}.threshold")
    outcome = _require_member(
        _require_str(_require_field(data, "outcome", path), f"{path}.outcome"),
        DECLARATION_OUTCOMES,
        f"{path}.outcome",
        "DECLARATION_OUTCOME_INVALID",
    )
    return RuleDeclarationOutcomeBand(threshold=threshold, outcome=outcome)


def declaration_to_dict(value: RuleDeclaration) -> dict:
    return {
        "declaration_id": value.declaration_id,
        "owner": value.owner,
        "state_guards": [state_guard_to_dict(g) for g in value.state_guards],
        "require_not_in_check": value.require_not_in_check,
        "ply_limit": value.ply_limit,
        "weighted_metric": (
            weighted_material_metric_to_dict(value.weighted_metric)
            if value.weighted_metric
            else None
        ),
        "outcome_bands": [declaration_outcome_band_to_dict(b) for b in value.outcome_bands],
        "failure_outcome": value.failure_outcome,
    }


def declaration_from_dict(data: Mapping[str, Any], path: str) -> RuleDeclaration:
    data = _require_mapping(data, path)
    declaration_id = _require_str(
        _require_field(data, "declaration_id", path), f"{path}.declaration_id"
    )
    owner = _require_int(_require_field(data, "owner", path), f"{path}.owner")
    guards_raw = data.get("state_guards", ())
    if not isinstance(guards_raw, (list, tuple)):
        raise _err("FIELD_NOT_LIST", f"{path}.state_guards", "state_guards must be a list")
    guards = tuple(
        state_guard_from_dict(item, f"{path}.state_guards[{i}]")
        for i, item in enumerate(guards_raw)
    )
    require_not_in_check = _require_bool(
        data.get("require_not_in_check", True), f"{path}.require_not_in_check"
    )
    ply_limit = data.get("ply_limit")
    if ply_limit is not None:
        ply_limit = _require_int(ply_limit, f"{path}.ply_limit")
    metric_raw = data.get("weighted_metric")
    metric = (
        None
        if metric_raw is None
        else weighted_material_metric_from_dict(
            _require_mapping(metric_raw, f"{path}.weighted_metric"),
            f"{path}.weighted_metric",
        )
    )
    bands_raw = data.get("outcome_bands", ())
    if not isinstance(bands_raw, (list, tuple)):
        raise _err("FIELD_NOT_LIST", f"{path}.outcome_bands", "outcome_bands must be a list")
    bands = tuple(
        declaration_outcome_band_from_dict(item, f"{path}.outcome_bands[{i}]")
        for i, item in enumerate(bands_raw)
    )
    failure_outcome = _require_member(
        _require_str(data.get("failure_outcome", "LOSS"), f"{path}.failure_outcome"),
        DECLARATION_OUTCOMES,
        f"{path}.failure_outcome",
        "DECLARATION_OUTCOME_INVALID",
    )
    return RuleDeclaration(
        declaration_id=declaration_id,
        owner=owner,
        state_guards=guards,
        require_not_in_check=require_not_in_check,
        ply_limit=ply_limit,
        weighted_metric=metric,
        outcome_bands=bands,
        failure_outcome=failure_outcome,
    )


def automatic_adjudication_to_dict(value: RuleAutomaticAdjudication) -> dict:
    return {
        "adjudication_id": value.adjudication_id,
        "trigger_ply": value.trigger_ply,
        "outcome": value.outcome,
        "continuation_policy": value.continuation_policy,
    }


def automatic_adjudication_from_dict(
    data: Mapping[str, Any], path: str
) -> RuleAutomaticAdjudication:
    data = _require_mapping(data, path)
    adjudication_id = _require_str(
        _require_field(data, "adjudication_id", path), f"{path}.adjudication_id"
    )
    if not adjudication_id:
        raise _err(
            "AUTOMATIC_ADJUDICATION_ID_INVALID",
            f"{path}.adjudication_id",
            "must be non-empty",
        )
    trigger_ply = _require_int(
        _require_field(data, "trigger_ply", path), f"{path}.trigger_ply"
    )
    if trigger_ply < 1:
        raise _err(
            "AUTOMATIC_ADJUDICATION_PLY_INVALID",
            f"{path}.trigger_ply",
            "must be positive",
        )
    outcome = _require_member(
        _require_str(data.get("outcome", "NO_CONTEST"), f"{path}.outcome"),
        AUTOMATIC_ADJUDICATION_OUTCOMES,
        f"{path}.outcome",
        "AUTOMATIC_ADJUDICATION_OUTCOME_INVALID",
    )
    continuation_policy = _require_member(
        _require_str(
            data.get("continuation_policy", "threshold_actor_continuous_check"),
            f"{path}.continuation_policy",
        ),
        AUTOMATIC_ADJUDICATION_POLICIES,
        f"{path}.continuation_policy",
        "AUTOMATIC_ADJUDICATION_POLICY_INVALID",
    )
    return RuleAutomaticAdjudication(
        adjudication_id=adjudication_id,
        trigger_ply=trigger_ply,
        outcome=outcome,
        continuation_policy=continuation_policy,
    )


def aux_state_to_dict(value: RuleAuxState) -> dict:
    initial = value.initial
    if isinstance(initial, tuple):
        initial = list(initial)
    return {
        "name": value.name,
        "value_kind": value.value_kind,
        "scope": value.scope,
        "lifetime": value.lifetime,
        "initial": initial,
    }


def aux_state_from_dict(data: Mapping[str, Any], path: str) -> RuleAuxState:
    data = _require_mapping(data, path)
    name = _require_str(_require_field(data, "name", path), f"{path}.name")
    value_kind = _require_member(
        _require_str(_require_field(data, "value_kind", path), f"{path}.value_kind"),
        AUX_VALUE_KINDS,
        f"{path}.value_kind",
        "AUX_VALUE_KIND_INVALID",
    )
    scope = _require_member(
        _require_str(_require_field(data, "scope", path), f"{path}.scope"),
        AUX_SCOPES,
        f"{path}.scope",
        "AUX_SCOPE_INVALID",
    )
    lifetime = _require_member(
        _require_str(_require_field(data, "lifetime", path), f"{path}.lifetime"),
        AUX_LIFETIMES,
        f"{path}.lifetime",
        "AUX_LIFETIME_INVALID",
    )
    initial = data.get("initial")
    if value_kind == "bool":
        if initial is None:
            initial = 0
        initial = _require_int(initial, f"{path}.initial")
        if initial not in (0, 1):
            raise _err("AUX_BOOL_INITIAL", f"{path}.initial", "bool initial must be 0 or 1")
    else:
        if initial is None:
            initial = None
        else:
            initial = tuple(_require_int_pair(initial, f"{path}.initial"))
    return RuleAuxState(name=name, value_kind=value_kind, scope=scope, lifetime=lifetime, initial=initial)


def slot_guard_to_dict(value: RuleSlotGuard) -> dict:
    return {
        "slot_name": value.slot_name,
        "comparison": value.comparison,
        "value": value.value,
        "square_ref": square_ref_to_dict(value.square_ref) if value.square_ref else None,
    }


def slot_guard_from_dict(data: Mapping[str, Any], path: str) -> RuleSlotGuard:
    data = _require_mapping(data, path)
    slot_name = _require_str(_require_field(data, "slot_name", path), f"{path}.slot_name")
    comparison = _require_member(
        _require_str(data.get("comparison", "eq"), f"{path}.comparison"),
        COMPARISON_OPS,
        f"{path}.comparison",
        "COMPARISON_INVALID",
    )
    value = data.get("value")
    if value is not None:
        value = _require_int(value, f"{path}.value")
    square_ref_raw = data.get("square_ref")
    square_ref = (
        square_ref_from_dict(_require_mapping(square_ref_raw, f"{path}.square_ref"), f"{path}.square_ref")
        if square_ref_raw is not None
        else None
    )
    return RuleSlotGuard(slot_name=slot_name, comparison=comparison, value=value, square_ref=square_ref)


def effect_to_dict(value: RuleActionEffect) -> dict:
    return {
        "kind": value.kind,
        "from_ref": square_ref_to_dict(value.from_ref) if value.from_ref else None,
        "to_ref": square_ref_to_dict(value.to_ref) if value.to_ref else None,
        "square_ref": square_ref_to_dict(value.square_ref) if value.square_ref else None,
        "piece_owner": value.piece_owner,
        "piece_type_ref": type_ref_to_dict(value.piece_type_ref) if value.piece_type_ref else None,
        "disposition": value.disposition,
        "slot_name": value.slot_name,
        "type_ref": type_ref_to_dict(value.type_ref) if value.type_ref else None,
        "count": value.count,
        "value": value.value,
    }


def effect_from_dict(data: Mapping[str, Any], path: str) -> RuleActionEffect:
    data = _require_mapping(data, path)
    kind = _require_member(
        _require_str(_require_field(data, "kind", path), f"{path}.kind"),
        SEMANTIC_EFFECT_KINDS,
        f"{path}.kind",
        "EFFECT_KIND_INVALID",
    )
    from_ref_raw = data.get("from_ref")
    to_ref_raw = data.get("to_ref")
    square_ref_raw = data.get("square_ref")
    from_ref = (
        square_ref_from_dict(_require_mapping(from_ref_raw, f"{path}.from_ref"), f"{path}.from_ref")
        if from_ref_raw is not None
        else None
    )
    to_ref = (
        square_ref_from_dict(_require_mapping(to_ref_raw, f"{path}.to_ref"), f"{path}.to_ref")
        if to_ref_raw is not None
        else None
    )
    square_ref = (
        square_ref_from_dict(_require_mapping(square_ref_raw, f"{path}.square_ref"), f"{path}.square_ref")
        if square_ref_raw is not None
        else None
    )
    piece_owner = _require_member(
        _require_str(data.get("piece_owner", "self"), f"{path}.piece_owner"),
        SELECTOR_OWNERS,
        f"{path}.piece_owner",
        "PIECE_OWNER_INVALID",
    )
    piece_type_ref_raw = data.get("piece_type_ref")
    piece_type_ref = (
        type_ref_from_dict(_require_mapping(piece_type_ref_raw, f"{path}.piece_type_ref"), f"{path}.piece_type_ref")
        if piece_type_ref_raw is not None
        else None
    )
    disposition = data.get("disposition")
    if disposition is not None:
        disposition = _require_member(
            _require_str(disposition, f"{path}.disposition"),
            DISPOSITIONS,
            f"{path}.disposition",
            "DISPOSITION_INVALID",
        )
    slot_name = data.get("slot_name")
    if slot_name is not None:
        slot_name = _require_str(slot_name, f"{path}.slot_name")
    type_ref_raw = data.get("type_ref")
    type_ref = (
        type_ref_from_dict(_require_mapping(type_ref_raw, f"{path}.type_ref"), f"{path}.type_ref")
        if type_ref_raw is not None
        else None
    )
    count = _require_int(data.get("count", 1), f"{path}.count")
    value = data.get("value")
    if value is not None:
        value = _require_int(value, f"{path}.value")
    return RuleActionEffect(
        kind=kind,
        from_ref=from_ref,
        to_ref=to_ref,
        square_ref=square_ref,
        piece_owner=piece_owner,
        piece_type_ref=piece_type_ref,
        disposition=disposition,
        slot_name=slot_name,
        type_ref=type_ref,
        count=count,
        value=value,
    )


def invariant_to_dict(value: RuleInvariant) -> dict:
    return {"kind": value.kind, "square_refs": [square_ref_to_dict(r) for r in value.square_refs]}


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
        square_ref_from_dict(_require_mapping(ref, f"{path}.square_refs[{i}]"), f"{path}.square_refs[{i}]")
        for i, ref in enumerate(square_refs_raw)
    )
    if len(square_refs) > MAX_SQUARES_NOT_ATTACKED:
        raise _err(
            "INVARIANT_SQUARES_TOO_MANY",
            f"{path}.square_refs",
            f"squares_not_attacked supports at most {MAX_SQUARES_NOT_ATTACKED} refs",
        )
    return RuleInvariant(kind=kind, square_refs=square_refs)


def replace_selector_to_dict(value: RuleReplaceSelector) -> dict:
    return {
        "type_ids": list(value.type_ids),
        "action_family": value.action_family,
        "target_relation": value.target_relation,
        "geometry_kind": value.geometry_kind,
        "replace_all_matching": value.replace_all_matching,
    }


def replace_selector_from_dict(data: Mapping[str, Any], path: str) -> RuleReplaceSelector:
    data = _require_mapping(data, path)
    type_ids = _require_str_list(_require_field(data, "type_ids", path), f"{path}.type_ids")
    action_family = _require_member(
        _require_str(_require_field(data, "action_family", path), f"{path}.action_family"),
        ACTION_FAMILIES,
        f"{path}.action_family",
        "ACTION_FAMILY_INVALID",
    )
    target_relation = _require_member(
        _require_str(_require_field(data, "target_relation", path), f"{path}.target_relation"),
        TARGET_RELATIONS,
        f"{path}.target_relation",
        "TARGET_RELATION_INVALID",
    )
    geometry_kind = data.get("geometry_kind")
    if geometry_kind is not None:
        geometry_kind = _require_member(
            _require_str(geometry_kind, f"{path}.geometry_kind"),
            ("leap", "ray"),
            f"{path}.geometry_kind",
            "GEOMETRY_KIND_INVALID",
        )
    replace_all = _require_bool(data.get("replace_all_matching", False), f"{path}.replace_all_matching")
    return RuleReplaceSelector(
        type_ids=type_ids,
        action_family=action_family,
        target_relation=target_relation,
        geometry_kind=geometry_kind,
        replace_all_matching=replace_all,
    )


def transition_trigger_to_dict(value: RuleTransitionTrigger) -> dict:
    return {
        "slot_name": value.slot_name,
        "event": value.event,
        "square_ref": square_ref_to_dict(value.square_ref),
        "owner": value.owner,
    }


def transition_trigger_from_dict(data: Mapping[str, Any], path: str) -> RuleTransitionTrigger:
    data = _require_mapping(data, path)
    slot_name = _require_str(_require_field(data, "slot_name", path), f"{path}.slot_name")
    event = _require_member(
        _require_str(_require_field(data, "event", path), f"{path}.event"),
        TRIGGER_EVENTS,
        f"{path}.event",
        "TRIGGER_EVENT_INVALID",
    )
    square_ref = square_ref_from_dict(
        _require_mapping(_require_field(data, "square_ref", path), f"{path}.square_ref"),
        f"{path}.square_ref",
    )
    owner = _require_member(
        _require_str(data.get("owner", "self"), f"{path}.owner"),
        SELECTOR_OWNERS,
        f"{path}.owner",
        "OWNER_INVALID",
    )
    return RuleTransitionTrigger(slot_name=slot_name, event=event, square_ref=square_ref, owner=owner)


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


def semantic_action_to_dict(
    value: RuleSemanticAction, *, include_none_subject_ref: bool = True
) -> dict:
    return {
        "name": value.name,
        "type_ids": list(value.type_ids),
        "geometry": geometry_spec_to_dict(value.geometry),
        "target_relation": value.target_relation,
        "composition": value.composition,
        "replace_selector": (
            replace_selector_to_dict(value.replace_selector)
            if value.replace_selector
            else None
        ),
        "path_constraints": [path_constraint_to_dict(c) for c in value.path_constraints],
        "state_guards": [
            state_guard_to_dict(g, include_none_subject_ref=include_none_subject_ref)
            for g in value.state_guards
        ],
        "slot_guards": [slot_guard_to_dict(g) for g in value.slot_guards],
        "aux_state": [aux_state_to_dict(a) for a in value.aux_state],
        "effects": [effect_to_dict(e) for e in value.effects],
        "invariants": [invariant_to_dict(i) for i in value.invariants],
        "postconditions": [postcondition_to_dict(p) for p in value.postconditions],
        "promotion_mode": value.promotion_mode,
        "explicit_promotion_type": value.explicit_promotion_type,
        "triggers": [transition_trigger_to_dict(t) for t in value.triggers],
    }


def semantic_action_from_dict(data: Mapping[str, Any], path: str) -> RuleSemanticAction:
    data = _require_mapping(data, path)
    name = _require_str(_require_field(data, "name", path), f"{path}.name")
    type_ids = _require_str_list(
        _require_field(data, "type_ids", path), f"{path}.type_ids"
    )
    geometry = geometry_spec_from_dict(
        _require_mapping(_require_field(data, "geometry", path), f"{path}.geometry"),
        f"{path}.geometry",
    )
    target_relation = _require_member(
        _require_str(
            _require_field(data, "target_relation", path), f"{path}.target_relation"
        ),
        TARGET_RELATIONS,
        f"{path}.target_relation",
        "TARGET_RELATION_INVALID",
    )
    composition = _require_member(
        _require_str(data.get("composition", "augment"), f"{path}.composition"),
        COMPOSITION_KINDS,
        f"{path}.composition",
        "COMPOSITION_INVALID",
    )
    replace_selector_raw = data.get("replace_selector")
    replace_selector = (
        replace_selector_from_dict(
            _require_mapping(replace_selector_raw, f"{path}.replace_selector"),
            f"{path}.replace_selector",
        )
        if replace_selector_raw is not None
        else None
    )
    promotion_mode = _require_member(
        _require_str(data.get("promotion_mode", "none"), f"{path}.promotion_mode"),
        PROMOTION_MODES,
        f"{path}.promotion_mode",
        "PROMOTION_MODE_INVALID",
    )
    explicit_promotion_type = data.get("explicit_promotion_type")
    if explicit_promotion_type is not None:
        explicit_promotion_type = _require_str(
            explicit_promotion_type, f"{path}.explicit_promotion_type"
        )
    return RuleSemanticAction(
        name=name,
        type_ids=type_ids,
        geometry=geometry,
        target_relation=target_relation,
        composition=composition,
        replace_selector=replace_selector,
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
        promotion_mode=promotion_mode,
        explicit_promotion_type=explicit_promotion_type,
        triggers=tuple(
            transition_trigger_from_dict(item, f"{path}.triggers[{i}]")
            for i, item in enumerate(data.get("triggers", ()))
        ),
    )


def ruleset_to_dict(
    ruleset: RuleSet,
    include_metadata: bool = True,
    *,
    include_none_subject_ref: bool = True,
) -> dict[str, Any]:
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
    if ruleset.repetition_policy != "draw":
        data["repetition_policy"] = ruleset.repetition_policy
    # Additive semantic actions: emitted only when non-empty so legacy
    # serialization (and therefore fingerprints) stays byte-identical.
    if ruleset.semantic_actions:
        data["semantic_dsl_version"] = ruleset.semantic_dsl_version
        data["semantic_actions"] = [
            semantic_action_to_dict(
                a, include_none_subject_ref=include_none_subject_ref
            )
            for a in ruleset.semantic_actions
        ]
    if ruleset.declarations:
        data["declarations"] = [declaration_to_dict(d) for d in ruleset.declarations]
    if ruleset.automatic_adjudications:
        data["automatic_adjudications"] = [
            automatic_adjudication_to_dict(a)
            for a in ruleset.automatic_adjudications
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
    repetition_policy = _require_str(
        data.get("repetition_policy", "draw"), f"{path}.repetition_policy"
    )
    if repetition_policy not in REPETITION_POLICIES:
        raise _err(
            "REPETITION_POLICY_UNSUPPORTED",
            f"{path}.repetition_policy",
            f"unsupported repetition policy {repetition_policy!r}",
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
    semantic_dsl_version = SEMANTIC_DSL_VERSION
    if semantic_actions:
        semantic_dsl_version = _require_int(
            data.get("semantic_dsl_version", 1), f"{path}.semantic_dsl_version"
        )
        if semantic_dsl_version != SEMANTIC_DSL_VERSION:
            raise _err(
                "SEMANTIC_DSL_VERSION_UNSUPPORTED",
                f"{path}.semantic_dsl_version",
                f"unsupported semantic DSL version {semantic_dsl_version}; "
                f"current is {SEMANTIC_DSL_VERSION}",
            )
    declarations_raw = data.get("declarations", ())
    if not isinstance(declarations_raw, (list, tuple)):
        raise _err("FIELD_NOT_LIST", f"{path}.declarations", "declarations must be a list")
    declarations = tuple(
        declaration_from_dict(item, f"{path}.declarations[{i}]")
        for i, item in enumerate(declarations_raw)
    )
    automatic_raw = data.get("automatic_adjudications", ())
    if not isinstance(automatic_raw, (list, tuple)):
        raise _err(
            "FIELD_NOT_LIST",
            f"{path}.automatic_adjudications",
            "automatic_adjudications must be a list",
        )
    automatic_adjudications = tuple(
        automatic_adjudication_from_dict(
            item, f"{path}.automatic_adjudications[{i}]"
        )
        for i, item in enumerate(automatic_raw)
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
        repetition_policy=repetition_policy,
        max_ply=max_ply,
        stalemate_result=stalemate_result,
        semantic_actions=semantic_actions,
        semantic_dsl_version=semantic_dsl_version,
        declarations=declarations,
        automatic_adjudications=automatic_adjudications,
        metadata=dict(metadata),
    )


def canonical_json(data: Any) -> str:
    """Deterministic JSON: sorted keys, compact separators, ASCII-safe."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_fingerprint(ruleset: RuleSet) -> str:
    """SHA-256 of the canonical JSON of all semantic fields (no metadata)."""
    payload = canonical_json(
        ruleset_to_dict(
            ruleset, include_metadata=False, include_none_subject_ref=False
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
