"""Production Compiled Semantic IR v2 (Phase 1.9B-1.5).

Executable-completeness hardening of the B-1 IR: every runtime operand
(exact geometry, pattern id, type binding, spatial parameter, square
reference, effect operand, capture disposition, promotion mode, auxiliary
slot, transition trigger, composition) is fixed at compile time.  A future
executor receives only this IR + a Position + a candidate binding and never
guesses, re-reads the high-level RuleSet, or uses game names.

IR v1 (Phase 1.9B-1) was a design/foundation artifact and is rejected by
this module (``COMPILED_SEMANTIC_IR_VERSION == 2``).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from .schema import (
    AUX_LIFETIMES,
    AUX_SCOPES,
    AUX_VALUE_KINDS,
    COMPARISON_OPS,
    COMPOSITION_KINDS,
    DISPOSITIONS,
    INVARIANT_KINDS,
    MAX_SEMANTIC_AUX_SLOTS,
    MAX_SEMANTIC_EFFECTS,
    PATH_CONSTRAINT_KINDS,
    POSTCONDITION_KINDS,
    PROMOTION_MODES,
    SEMANTIC_EFFECT_KINDS,
    SEMANTIC_STRATA,
    SELECTOR_LOCATIONS,
    SELECTOR_OWNERS,
    SELECTOR_PROMOTED,
    SPATIAL_KINDS,
    SQUARE_REF_KINDS,
    TARGET_RELATIONS,
    TRIGGER_EVENTS,
    TYPE_REF_KINDS,
)


COMPILED_SEMANTIC_IR_VERSION = 2
COST_CLASSES = ("C0", "C1", "C2", "C3", "C4")
GEOMETRY_KINDS = ("leap", "ray", "drop")
MAX_PROBE_STRATUM = "S3"
MAX_PATTERNS_PER_RULESET = 256


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


# ================================================================ compiled types


@dataclass(frozen=True, slots=True)
class CompiledGeometry:
    """One exact geometry with canonical per-(owner, source) ordered paths.

    Design A single lowering: the compiler emits the ordered path structure;
    the executor derives candidates mechanically (target = path[i],
    intermediate = path[:i]) without reinterpreting direction or
    ``max_steps``.  For a leap the path is the single target (or empty).
    """

    geometry_id: str
    kind: str  # leap | ray | drop
    owner_relative: bool = True
    offset: tuple[int, int] | None = None
    direction: tuple[int, int] | None = None
    min_steps: int | None = None
    max_steps: int | None = None
    atom_source: tuple[str, int] | None = None  # (type_id, atom_index) for legacy
    paths: Mapping[str, Mapping[int, tuple[int, ...]]] = (
        field(default_factory=dict)
    )


def geometry_candidates(
    geometry: "CompiledGeometry", owner: str, source: int
) -> tuple[tuple[int, tuple[int, ...]], ...]:
    """Mechanical candidate derivation from the compiled ordered path."""
    path = geometry.paths.get(owner, {}).get(source, ())
    if geometry.kind == "leap":
        return ((path[0], ()),) if path else ()
    start = max(0, (geometry.min_steps or 1) - 1)
    return tuple(
        (path[index], tuple(path[:index]))
        for index in range(start, len(path))
    )


@dataclass(frozen=True, slots=True)
class CompiledTypeRef:
    kind: str  # action_base | action_current | explicit | any
    type_id: str | None = None


@dataclass(frozen=True, slots=True)
class CompiledSquareRef:
    kind: str  # source | target | fixed | offset_from_source |
               # offset_from_target | path_step | aux_slot_square
    square: tuple[int, int] | None = None
    offset: tuple[int, int] | None = None
    owner_relative: bool = True
    step: int | None = None
    slot_id: int | None = None


@dataclass(frozen=True, slots=True)
class CompiledZone:
    zone_id: str
    squares: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class CompiledSpatialSelector:
    kind: str
    refs: tuple[CompiledSquareRef, ...] = ()
    zone_id: str | None = None


@dataclass(frozen=True, slots=True)
class CompiledStatePredicate:
    aggregation: str
    owner: str
    type_ref: CompiledTypeRef
    compare_field: str
    promoted: str
    location: str
    spatial: CompiledSpatialSelector
    comparison: str
    value: int = 0


@dataclass(frozen=True, slots=True)
class CompiledSlotGuard:
    slot_id: int
    comparison: str
    value: int | None = None
    square_ref: CompiledSquareRef | None = None


@dataclass(frozen=True, slots=True)
class CompiledAuxSlot:
    slot_id: int
    value_kind: str  # bool | square_or_none
    scope: str  # global | per_owner
    lifetime: str  # persistent | expire_next_turn
    initial: int | tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class CompiledTransitionTrigger:
    slot_id: int
    event: str  # piece_leaves_square | piece_removed_from_square
    square_ref: CompiledSquareRef
    owner: str = "self"


@dataclass(frozen=True, slots=True)
class CompiledEffect:
    kind: str
    from_ref: CompiledSquareRef | None = None
    to_ref: CompiledSquareRef | None = None
    square_ref: CompiledSquareRef | None = None
    piece_owner: str = "self"
    piece_type_ref: CompiledTypeRef | None = None
    disposition: str | None = None
    slot_id: int | None = None
    type_ref: CompiledTypeRef | None = None
    count: int = 1
    value: int | None = None


@dataclass(frozen=True, slots=True)
class CompiledInvariant:
    kind: str
    square_refs: tuple[CompiledSquareRef, ...] = ()


@dataclass(frozen=True, slots=True)
class CompiledPostcondition:
    kind: str
    max_stratum: str = "S3"


@dataclass(frozen=True, slots=True)
class CompiledPathPredicate:
    kind: str
    count: int | None = None
    lo: int | None = None
    hi: int | None = None
    owner_filter: str = "any"


@dataclass(frozen=True, slots=True)
class CompiledTargetPredicate:
    kind: str  # target_empty | target_enemy | target_friendly | target_any


@dataclass(frozen=True, slots=True)
class CompiledMovePattern:
    pattern_id: str
    name: str  # debug label only; never executed
    type_ids: tuple[str, ...]
    geometry_ids: tuple[str, ...]
    target: CompiledTargetPredicate
    path: tuple[CompiledPathPredicate, ...] = ()
    guards: tuple[CompiledStatePredicate, ...] = ()
    slot_guards: tuple[CompiledSlotGuard, ...] = ()
    effects: tuple[CompiledEffect, ...] = ()
    invariants: tuple[CompiledInvariant, ...] = ()
    postconditions: tuple[CompiledPostcondition, ...] = ()
    promotion_mode: str = "none"  # none | inherit_compiled_masks | explicit
    explicit_promotion_type: str | None = None
    composition: str = "augment"
    replaced_pattern_ids: tuple[str, ...] = ()
    cost_class: str = "C1"
    stratum: str = "S0"


@dataclass(frozen=True, slots=True)
class SemanticCapabilities:
    legacy_core_executable: bool = False
    new_ir_core_executable: bool = False
    native_executable: bool = False
    contains_path_predicate: bool = False
    contains_state_guard: bool = False
    contains_aux_state: bool = False
    contains_compound_effect: bool = False
    contains_postcondition: bool = False
    contains_transition_trigger: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CompiledSemanticIR:
    ir_version: int = COMPILED_SEMANTIC_IR_VERSION
    ruleset_fingerprint: str = ""
    geometry: Mapping[str, CompiledGeometry] = field(default_factory=dict)
    zones: Mapping[str, CompiledZone] = field(default_factory=dict)
    patterns: tuple[CompiledMovePattern, ...] = ()
    aux_slots: tuple[CompiledAuxSlot, ...] = ()
    triggers: tuple[CompiledTransitionTrigger, ...] = ()
    capabilities: SemanticCapabilities = SemanticCapabilities()

    def serialized(self) -> str:
        return canonical_json(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "ir_version": self.ir_version,
            "ruleset_fingerprint": self.ruleset_fingerprint,
            "geometry": {
                gid: {
                    "geometry_id": geo.geometry_id,
                    "kind": geo.kind,
                    "owner_relative": geo.owner_relative,
                    "offset": list(geo.offset) if geo.offset else None,
                    "direction": list(geo.direction) if geo.direction else None,
                    "min_steps": geo.min_steps,
                    "max_steps": geo.max_steps,
                    "atom_source": (
                        list(geo.atom_source) if geo.atom_source else None
                    ),
                    "paths": [
                        [owner, source, list(path)]
                        for owner in ("0", "1")
                        for source, candidates in sorted(
                            geo.paths.get(owner, {}).items()
                        )
                        for path in (candidates,)
                    ],
                }
                for gid, geo in sorted(self.geometry.items())
            },
            "zones": {
                zid: {"zone_id": z.zone_id, "squares": list(z.squares)}
                for zid, z in sorted(self.zones.items())
            },
            "patterns": [self._pattern_dict(p) for p in self.patterns],
            "aux_slots": [asdict(s) for s in self.aux_slots],
            "triggers": [
                {
                    "slot_id": t.slot_id,
                    "event": t.event,
                    "square_ref": _square_ref_dict(t.square_ref),
                    "owner": t.owner,
                }
                for t in self.triggers
            ],
            "capabilities": self.capabilities.to_dict(),
        }

    @staticmethod
    def _pattern_dict(p: CompiledMovePattern) -> dict:
        return {
            "pattern_id": p.pattern_id,
            "name": p.name,
            "type_ids": list(p.type_ids),
            "geometry_ids": list(p.geometry_ids),
            "target": {"kind": p.target.kind},
            "path": [
                {
                    "kind": pp.kind,
                    "count": pp.count,
                    "lo": pp.lo,
                    "hi": pp.hi,
                    "owner_filter": pp.owner_filter,
                }
                for pp in p.path
            ],
            "guards": [
                {
                    "aggregation": g.aggregation,
                    "owner": g.owner,
                    "type_ref": _type_ref_dict(g.type_ref),
                    "compare_field": g.compare_field,
                    "promoted": g.promoted,
                    "location": g.location,
                    "spatial": _spatial_dict(g.spatial),
                    "comparison": g.comparison,
                    "value": g.value,
                }
                for g in p.guards
            ],
            "slot_guards": [
                {
                    "slot_id": sg.slot_id,
                    "comparison": sg.comparison,
                    "value": sg.value,
                    "square_ref": _square_ref_dict(sg.square_ref) if sg.square_ref else None,
                }
                for sg in p.slot_guards
            ],
            "effects": [_effect_dict(e) for e in p.effects],
            "invariants": [
                {
                    "kind": i.kind,
                    "square_refs": [_square_ref_dict(r) for r in i.square_refs],
                }
                for i in p.invariants
            ],
            "postconditions": [
                {"kind": pc.kind, "max_stratum": pc.max_stratum}
                for pc in p.postconditions
            ],
            "promotion_mode": p.promotion_mode,
            "explicit_promotion_type": p.explicit_promotion_type,
            "composition": p.composition,
            "replaced_pattern_ids": list(p.replaced_pattern_ids),
            "cost_class": p.cost_class,
            "stratum": p.stratum,
        }

    def fingerprint(self) -> str:
        return hashlib.sha256(self.serialized().encode("utf-8")).hexdigest()


def _type_ref_dict(value: CompiledTypeRef) -> dict:
    return {"kind": value.kind, "type_id": value.type_id}


def _square_ref_dict(value: CompiledSquareRef) -> dict:
    return {
        "kind": value.kind,
        "square": list(value.square) if value.square else None,
        "offset": list(value.offset) if value.offset else None,
        "owner_relative": value.owner_relative,
        "step": value.step,
        "slot_id": value.slot_id,
    }


def _spatial_dict(value: CompiledSpatialSelector) -> dict:
    return {
        "kind": value.kind,
        "refs": [_square_ref_dict(r) for r in value.refs],
        "zone_id": value.zone_id,
    }


def _effect_dict(value: CompiledEffect) -> dict:
    return {
        "kind": value.kind,
        "from_ref": _square_ref_dict(value.from_ref) if value.from_ref else None,
        "to_ref": _square_ref_dict(value.to_ref) if value.to_ref else None,
        "square_ref": _square_ref_dict(value.square_ref) if value.square_ref else None,
        "piece_owner": value.piece_owner,
        "piece_type_ref": (
            _type_ref_dict(value.piece_type_ref) if value.piece_type_ref else None
        ),
        "disposition": value.disposition,
        "slot_id": value.slot_id,
        "type_ref": _type_ref_dict(value.type_ref) if value.type_ref else None,
        "count": value.count,
        "value": value.value,
    }


@dataclass(frozen=True, slots=True)
class CompiledSemanticRuleset:
    """Compiled product for semantic-DSL rulesets.

    ``_legacy_compiled`` is an inspection-only handle; executable
    completeness never depends on it.  ``support`` is the explicit typed
    generic Core support payload (ADR-013).
    """

    ir: CompiledSemanticIR
    _legacy_compiled: Any = None
    support: "CompiledSemanticSupport | None" = None


@dataclass(frozen=True, slots=True)
class SemanticTypeMetadata:
    """Stripped type metadata for execution (no movement atoms)."""

    type_id: str
    is_anchor: bool
    is_promotable: bool
    promotion_target_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CompiledSemanticSupport:
    """Typed generic Core support payload owned by the semantic ruleset
    (ADR-013).  Compiler-produced and immutable; never reinterprets
    movement atoms; ``_legacy_compiled`` is not part of execution."""

    board_size: int
    ruleset_fingerprint: str = ""
    initial_position: tuple[tuple[Any, ...], ...] = ()
    type_metadata: Mapping[str, SemanticTypeMetadata] = field(default_factory=dict)
    drop_allowed: Mapping[str, tuple[tuple[bool, ...], ...]] = field(default_factory=dict)
    promotion_allowed: Mapping[str, tuple[frozenset[tuple[Any, Any]], ...]] = field(
        default_factory=dict
    )
    promotion_forced: Mapping[str, tuple[frozenset[Any], ...]] = field(
        default_factory=dict
    )
    empty_mobility: Mapping[str, tuple[tuple[tuple[Any, ...], ...], ...]] = field(
        default_factory=dict
    )
    repetition_limit: int = 4
    max_ply: int = 512
    stalemate_result: str = "draw"


# ================================================================ validation


def _stratum_index(stratum: str) -> int:
    return SEMANTIC_STRATA.index(stratum)


def _component_stratum(component: str) -> str:
    if component == "geometry":
        return "S0"
    if component in GEOMETRY_KINDS:
        return "S0"
    if component.startswith("target_") and component[7:] in TARGET_RELATIONS:
        return "S0"
    if component in TARGET_RELATIONS or component in PATH_CONSTRAINT_KINDS:
        return "S0"
    if component == "state_guard" or component == "slot_guard":
        return "S1"
    if component in INVARIANT_KINDS:
        return "S2"
    if component in POSTCONDITION_KINDS:
        return "S4"
    if component in SEMANTIC_EFFECT_KINDS:
        return "S3"
    raise ValueError(f"unknown compiled component {component!r}")


def cost_class_of(primitive_kind: str) -> str:
    if primitive_kind == "geometry":
        return "C1"
    if primitive_kind in GEOMETRY_KINDS or primitive_kind in TARGET_RELATIONS:
        return "C1"
    if primitive_kind in ("path_clear", "path_first_blocker_owner", "path_last_blocker_owner"):
        return "C1"
    if primitive_kind in ("path_count_eq", "path_count_range"):
        return "C2"
    if primitive_kind in ("state_guard", "slot_guard"):
        return "C2"
    if primitive_kind in INVARIANT_KINDS:
        return "C3"
    if primitive_kind in SEMANTIC_EFFECT_KINDS:
        return "C3"
    if primitive_kind in POSTCONDITION_KINDS:
        return "C4"
    return "C1"


_EFFECT_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "move": {
        "requires": ("from_ref", "to_ref"),
        "forbids": ("disposition", "type_ref"),
    },
    "remove": {
        "requires": ("square_ref", "disposition"),
        "forbids": ("from_ref", "to_ref"),
    },
    "remove_from_hand": {
        "requires": ("piece_type_ref",),
        "forbids": ("from_ref", "to_ref", "square_ref", "disposition"),
    },
    "place": {
        "requires": ("to_ref", "piece_type_ref"),
        "forbids": ("from_ref", "square_ref", "disposition"),
    },
    "set_current_type": {
        "requires": ("square_ref", "type_ref"),
        "forbids": ("from_ref", "to_ref", "disposition"),
    },
    "set_bool": {
        "requires": ("slot_id", "value"),
        "forbids": ("square_ref", "type_ref", "disposition", "from_ref", "to_ref"),
    },
    "clear_right": {
        "requires": ("slot_id",),
        "forbids": ("square_ref", "type_ref", "disposition"),
    },
    "set_token": {
        "requires": ("slot_id", "square_ref"),
        "forbids": ("type_ref", "disposition"),
    },
    "clear_token": {
        "requires": ("slot_id",),
        "forbids": ("square_ref", "type_ref", "disposition"),
    },
    "shift": {
        "requires": ("from_ref", "to_ref"),
        "forbids": ("disposition", "type_ref"),
    },
}


def _validate_effect_wellformed(
    effect: CompiledEffect, slot_kinds: dict[int, str], errors: list[str]
) -> None:
    spec = _EFFECT_REQUIREMENTS.get(effect.kind)
    if spec is None:
        errors.append(f"unknown effect kind {effect.kind}")
        return
    for required in spec["requires"]:
        if getattr(effect, required) is None:
            errors.append(f"effect {effect.kind} requires {required}")
    for forbidden in spec["forbids"]:
        if getattr(effect, forbidden) is not None:
            errors.append(f"effect {effect.kind} must not carry {forbidden}")
    if effect.kind in ("clear_right", "set_token", "clear_token"):
        if effect.slot_id is None or effect.slot_id not in slot_kinds:
            errors.append(f"slot effect references undeclared slot {effect.slot_id}")
        else:
            kind = slot_kinds[effect.slot_id]
            if effect.kind in ("set_token", "clear_token") and kind != "square_or_none":
                errors.append("set_token/clear_token require a square_or_none slot")
            if effect.kind == "clear_right" and kind != "bool":
                errors.append("clear_right requires a bool slot")
    if effect.kind == "remove" and effect.disposition not in DISPOSITIONS:
        errors.append(f"remove requires an explicit disposition, got {effect.disposition!r}")
    if effect.count != 1:
        errors.append("effect count must be 1 in IR v2")
    if effect.kind == "set_bool":
        if effect.slot_id is None or effect.slot_id not in slot_kinds:
            errors.append(f"set_bool references undeclared slot {effect.slot_id}")
        elif slot_kinds[effect.slot_id] != "bool":
            errors.append("set_bool requires a bool slot")
        if effect.value not in (0, 1):
            errors.append("set_bool requires value 0/1")


def validate_ir(ir: CompiledSemanticIR) -> list[str]:
    errors: list[str] = []
    if ir.ir_version != COMPILED_SEMANTIC_IR_VERSION:
        errors.append(
            f"unsupported IR version {ir.ir_version}; expected "
            f"{COMPILED_SEMANTIC_IR_VERSION}"
        )
    slot_ids = tuple(slot.slot_id for slot in ir.aux_slots)
    if len(slot_ids) != len(set(slot_ids)):
        errors.append("duplicate aux slot ids")
    if len(ir.aux_slots) > MAX_SEMANTIC_AUX_SLOTS:
        errors.append("aux slot count exceeds 8")
    slot_kinds = {slot.slot_id: slot.value_kind for slot in ir.aux_slots}
    for slot in ir.aux_slots:
        if slot.value_kind not in AUX_VALUE_KINDS:
            errors.append(f"invalid aux value kind {slot.value_kind}")
        if slot.scope not in AUX_SCOPES or slot.lifetime not in AUX_LIFETIMES:
            errors.append(f"invalid aux slot {slot}")
        if slot.value_kind == "bool" and slot.initial not in (0, 1):
            errors.append(f"bool slot {slot.slot_id} needs initial 0/1")
    for trigger in ir.triggers:
        if trigger.event not in TRIGGER_EVENTS:
            errors.append(f"unknown trigger event {trigger.event}")
        if trigger.slot_id not in slot_ids:
            errors.append(f"trigger references undeclared slot {trigger.slot_id}")
        if trigger.square_ref.kind not in SQUARE_REF_KINDS:
            errors.append(f"trigger has invalid square ref {trigger.square_ref.kind}")
    for pattern in ir.patterns:
        errors.extend(validate_compiled_pattern(pattern, slot_ids, slot_kinds))
    return errors


def validate_compiled_pattern(
    pattern: CompiledMovePattern,
    slot_ids: tuple[int, ...],
    slot_kinds: dict[int, str],
) -> list[str]:
    errors: list[str] = []
    if not pattern.pattern_id or not pattern.name:
        errors.append("pattern requires pattern_id and name")
    if not pattern.geometry_ids:
        errors.append("pattern requires at least one geometry id")
    compiled_targets = {f"target_{r}" for r in TARGET_RELATIONS}
    if pattern.target.kind not in compiled_targets:
        errors.append(f"unknown target kind {pattern.target.kind}")
    for pp in pattern.path:
        if pp.kind not in PATH_CONSTRAINT_KINDS:
            errors.append(f"unknown path kind {pp.kind}")
    for guard in pattern.guards:
        if guard.aggregation not in ("exists", "count"):
            errors.append(f"unknown aggregation {guard.aggregation}")
        if guard.comparison not in COMPARISON_OPS:
            errors.append(f"unknown comparison {guard.comparison}")
        if guard.type_ref.kind not in TYPE_REF_KINDS:
            errors.append(f"unknown type ref kind {guard.type_ref.kind}")
        if guard.compare_field not in ("base", "current"):
            errors.append(f"unknown compare field {guard.compare_field}")
        if guard.promoted not in SELECTOR_PROMOTED or guard.location not in SELECTOR_LOCATIONS:
            errors.append("invalid selector")
        if guard.spatial.kind not in SPATIAL_KINDS:
            errors.append(f"unknown spatial kind {guard.spatial.kind}")
        if guard.spatial.kind in ("same_file", "same_rank", "exact", "adjacent") and len(
            guard.spatial.refs
        ) != 1:
            errors.append(f"spatial {guard.spatial.kind} requires exactly 1 ref")
        if guard.spatial.kind == "path_between" and len(guard.spatial.refs) != 2:
            errors.append("path_between requires 2 refs")
        if guard.spatial.kind == "zone" and not guard.spatial.zone_id:
            errors.append("zone spatial selector requires zone_id")
    for sg in pattern.slot_guards:
        if sg.comparison not in COMPARISON_OPS:
            errors.append(f"unknown slot comparison {sg.comparison}")
        if sg.slot_id not in slot_ids:
            errors.append(f"slot guard references undeclared slot {sg.slot_id}")
        else:
            kind = slot_kinds[sg.slot_id]
            if kind == "bool":
                if sg.value not in (0, 1):
                    errors.append("bool slot guard requires value 0/1")
                if sg.square_ref is not None:
                    errors.append("bool slot guard must not use square_ref")
            else:
                if sg.square_ref is None and sg.comparison not in ("eq", "ne"):
                    errors.append("square slot guard with None needs eq/ne")
    if len(pattern.effects) > MAX_SEMANTIC_EFFECTS:
        errors.append(f"effect cardinality exceeds {MAX_SEMANTIC_EFFECTS}")
    for effect in pattern.effects:
        if effect.kind not in SEMANTIC_EFFECT_KINDS:
            errors.append(f"unknown effect kind {effect.kind}")
        _validate_effect_wellformed(effect, slot_kinds, errors)
    for invariant in pattern.invariants:
        if invariant.kind not in INVARIANT_KINDS:
            errors.append(f"unknown invariant kind {invariant.kind}")
        if invariant.kind == "squares_not_attacked":
            if not invariant.square_refs:
                errors.append("squares_not_attacked requires square_refs")
            if len(invariant.square_refs) > 4:
                errors.append("squares_not_attacked supports at most 4 refs")
    if len(pattern.postconditions) > 2:
        errors.append("postcondition count exceeds 2")
    for pc in pattern.postconditions:
        if pc.kind not in POSTCONDITION_KINDS:
            errors.append(f"unknown postcondition kind {pc.kind}")
        if pc.kind == "no_legal_reply":
            if pc.max_stratum not in SEMANTIC_STRATA:
                errors.append("invalid probe stratum")
            elif _stratum_index(pc.max_stratum) > _stratum_index(MAX_PROBE_STRATUM):
                errors.append("probe max_stratum must be <= S3")
            elif _stratum_index(pc.max_stratum) >= _stratum_index("S4"):
                errors.append("probe must be strictly below S4")
    if pattern.promotion_mode not in PROMOTION_MODES:
        errors.append(f"unknown promotion mode {pattern.promotion_mode}")
    if pattern.promotion_mode == "explicit" and not pattern.explicit_promotion_type:
        errors.append("explicit promotion requires explicit_promotion_type")
    if pattern.composition not in COMPOSITION_KINDS:
        errors.append(f"unknown composition {pattern.composition}")
    if pattern.composition == "replace_legacy" and not pattern.replaced_pattern_ids:
        errors.append("replace_legacy pattern must record replaced_pattern_ids")
    if pattern.cost_class not in COST_CLASSES or pattern.stratum not in SEMANTIC_STRATA:
        errors.append("invalid cost_class/stratum")
    components = (
        ["geometry"] * len(pattern.geometry_ids)
        + [pattern.target.kind]
        + [pp.kind for pp in pattern.path]
        + ["state_guard"] * len(pattern.guards)
        + ["slot_guard"] * len(pattern.slot_guards)
        + [i.kind for i in pattern.invariants]
        + [pc.kind for pc in pattern.postconditions]
    )
    for component in components:
        if _stratum_index(_component_stratum(component)) > _stratum_index(pattern.stratum):
            errors.append(
                f"component {component} exceeds pattern stratum {pattern.stratum}"
            )
    return errors


def validate_executable_completeness(
    ir: CompiledSemanticIR, type_ids: tuple[str, ...]
) -> list[str]:
    """Static executable-completeness: every runtime operand must have a
    typed, self-resolving source.  A future executor must never guess."""
    errors: list[str] = []
    geometry_ids = set(ir.geometry)
    zone_ids = set(ir.zones)
    slot_ids = tuple(slot.slot_id for slot in ir.aux_slots)
    slot_kinds = {slot.slot_id: slot.value_kind for slot in ir.aux_slots}
    pattern_ids = {p.pattern_id for p in ir.patterns}
    if len(pattern_ids) != len(ir.patterns):
        errors.append("duplicate pattern ids")

    for gid, geometry in ir.geometry.items():
        if geometry.geometry_id != gid:
            errors.append(f"geometry id key mismatch {gid}")
        if geometry.kind not in GEOMETRY_KINDS:
            errors.append(f"unknown geometry kind {geometry.kind}")
        if geometry.kind == "drop":
            if geometry.paths:
                errors.append(f"drop geometry {gid} must not carry paths")
        else:
            for owner, per_source in geometry.paths.items():
                for source, path in per_source.items():
                    if source in path:
                        errors.append(f"geometry {gid} path must exclude source")
                    if len(set(path)) != len(path):
                        errors.append(f"geometry {gid} path contains repeats")

    for pattern in ir.patterns:
        for gid in pattern.geometry_ids:
            if gid not in geometry_ids:
                errors.append(f"pattern {pattern.pattern_id} refs unknown geometry {gid}")
        exact_ray_steps: set[int] | None = None
        for gid in pattern.geometry_ids:
            geo = ir.geometry[gid]
            if geo.kind == "ray" and geo.min_steps is not None and geo.max_steps == geo.min_steps:
                if exact_ray_steps is None:
                    exact_ray_steps = set()
                exact_ray_steps.add(geo.max_steps)
            elif geo.kind != "ray":
                continue
            else:
                exact_ray_steps = None
                break
        for guard in pattern.guards:
            _complete_type_ref(guard.type_ref, type_ids, pattern.pattern_id, errors)
            if guard.spatial.kind == "zone" and guard.spatial.zone_id not in zone_ids:
                errors.append(
                    f"pattern {pattern.pattern_id} refs unknown zone {guard.spatial.zone_id}"
                )
            for ref in guard.spatial.refs:
                _complete_square_ref(
                    ref, slot_ids, slot_kinds, pattern.pattern_id, errors,
                    exact_ray_steps=exact_ray_steps,
                )
        for sg in pattern.slot_guards:
            if sg.square_ref is not None:
                _complete_square_ref(
                    sg.square_ref, slot_ids, slot_kinds, pattern.pattern_id, errors,
                    exact_ray_steps=exact_ray_steps,
                )
        for effect in pattern.effects:
            for ref in (effect.from_ref, effect.to_ref, effect.square_ref):
                if ref is not None:
                    _complete_square_ref(
                        ref, slot_ids, slot_kinds, pattern.pattern_id, errors,
                        exact_ray_steps=exact_ray_steps,
                    )
            for tref in (effect.piece_type_ref, effect.type_ref):
                if tref is not None:
                    _complete_type_ref(tref, type_ids, pattern.pattern_id, errors)
        for invariant in pattern.invariants:
            for ref in invariant.square_refs:
                _complete_square_ref(
                    ref, slot_ids, slot_kinds, pattern.pattern_id, errors,
                    exact_ray_steps=exact_ray_steps,
                )
    for trigger in ir.triggers:
        _complete_square_ref(trigger.square_ref, slot_ids, slot_kinds, "trigger", errors)
    return errors


def _complete_type_ref(
    ref: CompiledTypeRef, type_ids: tuple[str, ...], context: str, errors: list[str]
) -> None:
    if ref.kind not in TYPE_REF_KINDS:
        errors.append(f"{context}: invalid type ref kind {ref.kind}")
    if ref.kind == "explicit" and ref.type_id not in type_ids:
        errors.append(f"{context}: explicit type ref {ref.type_id!r} not in ruleset")


def _complete_square_ref(
    ref: CompiledSquareRef,
    slot_ids: tuple[int, ...],
    slot_kinds: dict[int, str],
    context: str,
    errors: list[str],
    exact_ray_steps: set[int] | None = None,
) -> None:
    if ref.kind not in SQUARE_REF_KINDS:
        errors.append(f"{context}: invalid square ref kind {ref.kind}")
    if ref.kind == "fixed" and ref.square is None:
        errors.append(f"{context}: fixed square ref missing square")
    if ref.kind in ("offset_from_source", "offset_from_target") and ref.offset is None:
        errors.append(f"{context}: offset square ref missing offset")
    if ref.kind == "path_step" and ref.step is None:
        errors.append(f"{context}: path_step square ref missing step")
    if ref.kind == "path_step" and exact_ray_steps:
        max_intermediate = max(steps - 1 for steps in exact_ray_steps)
        if ref.step >= max_intermediate:
            errors.append(
                f"{context}: path_step {ref.step} outside static range of "
                f"exact rays (max intermediate index {max_intermediate - 1})"
            )
    if ref.kind == "aux_slot_square":
        if ref.slot_id not in slot_ids:
            errors.append(f"{context}: aux_slot_square refs undeclared slot {ref.slot_id}")
        elif slot_kinds.get(ref.slot_id) != "square_or_none":
            errors.append(
                f"{context}: aux_slot_square ref points to non-square slot {ref.slot_id}"
            )
