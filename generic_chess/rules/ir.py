"""Production Compiled Semantic IR (Phase 1.9B-1).

Typed, frozen, deterministic, serializable compiled representation produced
by ``rules.compiler``.  This is the *compiled* layer: users never construct
these types directly; the compiler lowers high-level ``RuleSet`` definitions
(including the additive ``semantic_actions`` DSL in ``rules.schema``) into
this IR.  No runtime callbacks, no untyped semantic dicts, no game-name
execution tokens.

Core does not execute this IR yet; capability flags (see
:class:`SemanticCapabilities`) are the fail-closed gate until the reference
executor lands in Phase 1.9B-2.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from .schema import (
    AUX_LIFETIMES,
    AUX_STATE_KINDS,
    COMPARISON_OPS,
    EFFECT_SQUARE_REFS,
    INVARIANT_KINDS,
    MAX_SEMANTIC_AUX_SLOTS,
    MAX_SEMANTIC_EFFECTS,
    PATH_CONSTRAINT_KINDS,
    POSTCONDITION_KINDS,
    SEMANTIC_EFFECT_KINDS,
    SEMANTIC_STRATA,
    SELECTOR_LOCATIONS,
    SELECTOR_OWNERS,
    SELECTOR_PROMOTED,
    SELECTOR_SPATIAL,
    SELECTOR_SPATIAL_REFS,
    SELECTOR_TYPE_MODES,
    TARGET_RELATIONS,
)


COMPILED_SEMANTIC_IR_VERSION = 1

COST_CLASSES = ("C0", "C1", "C2", "C3", "C4")
GEOMETRY_KINDS = ("leap", "ray", "drop")

# Stratified probe bound: nested legal-reply probes never re-enter S4.
MAX_PROBE_STRATUM = "S3"


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


# ================================================================ compiled types


@dataclass(frozen=True, slots=True)
class CompiledTargetPredicate:
    kind: str  # target_empty | target_enemy | target_friendly | target_any


@dataclass(frozen=True, slots=True)
class CompiledPathPredicate:
    kind: str
    count: int | None = None
    lo: int | None = None
    hi: int | None = None
    owner_filter: str = "any"


@dataclass(frozen=True, slots=True)
class CompiledPieceSelector:
    owner: str
    type_mode: str
    promoted: str
    location: str
    spatial: str
    spatial_ref: str = "TARGET"


@dataclass(frozen=True, slots=True)
class CompiledStatePredicate:
    aggregation: str
    selector: CompiledPieceSelector
    comparison: str
    value: int = 0


@dataclass(frozen=True, slots=True)
class CompiledSlotGuard:
    slot_id: int
    comparison: str
    value: int = 0


@dataclass(frozen=True, slots=True)
class CompiledEffect:
    kind: str
    square_ref: str = "target"
    slot_id: int | None = None
    type_id: str | None = None


@dataclass(frozen=True, slots=True)
class CompiledAuxSlot:
    slot_id: int
    kind: str
    lifetime: str


@dataclass(frozen=True, slots=True)
class CompiledInvariant:
    kind: str  # own_anchor_safe | squares_not_attacked
    square_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CompiledPostcondition:
    kind: str
    max_stratum: str = "S3"


@dataclass(frozen=True, slots=True)
class CompiledMovePattern:
    """One compiled action template (compiled-layer counterpart of
    ``RuleSemanticAction`` plus legacy lowering)."""

    name: str  # debug label only; never used by an executor
    type_ids: tuple[str, ...]
    geometry: tuple[str, ...]
    target: CompiledTargetPredicate
    path: tuple[CompiledPathPredicate, ...] = ()
    guards: tuple[CompiledStatePredicate, ...] = ()
    slot_guards: tuple[CompiledSlotGuard, ...] = ()
    effects: tuple[CompiledEffect, ...] = ()
    invariants: tuple[CompiledInvariant, ...] = ()
    postconditions: tuple[CompiledPostcondition, ...] = ()
    cost_class: str = "C1"
    stratum: str = "S0"
    promotion_variants: str = "none"  # none | compiled_masks | explicit


@dataclass(frozen=True, slots=True)
class SemanticCapabilities:
    """Fail-closed capability gate for the IR (never silently executed)."""

    legacy_core_executable: bool = False
    new_ir_core_executable: bool = False
    native_executable: bool = False
    contains_path_predicate: bool = False
    contains_state_guard: bool = False
    contains_aux_state: bool = False
    contains_compound_effect: bool = False
    contains_postcondition: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CompiledSemanticIR:
    """The production compiled semantic representation for one ruleset."""

    ir_version: int = COMPILED_SEMANTIC_IR_VERSION
    ruleset_fingerprint: str = ""
    # canonical geometry lowering (Design A single-lowering output)
    geometry_metadata: Mapping[str, Any] = field(default_factory=dict)
    patterns: tuple[CompiledMovePattern, ...] = ()
    aux_slots: tuple[CompiledAuxSlot, ...] = ()
    capabilities: SemanticCapabilities = SemanticCapabilities()

    def serialized(self) -> str:
        return canonical_json(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "ir_version": self.ir_version,
            "ruleset_fingerprint": self.ruleset_fingerprint,
            "geometry_metadata": dict(self.geometry_metadata),
            "patterns": [
                {
                    "name": p.name,
                    "type_ids": list(p.type_ids),
                    "geometry": list(p.geometry),
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
                            "selector": asdict(g.selector),
                            "comparison": g.comparison,
                            "value": g.value,
                        }
                        for g in p.guards
                    ],
                    "slot_guards": [asdict(sg) for sg in p.slot_guards],
                    "effects": [asdict(e) for e in p.effects],
                    "invariants": [
                        {"kind": i.kind, "square_refs": list(i.square_refs)}
                        for i in p.invariants
                    ],
                    "postconditions": [
                        {"kind": pc.kind, "max_stratum": pc.max_stratum}
                        for pc in p.postconditions
                    ],
                    "cost_class": p.cost_class,
                    "stratum": p.stratum,
                    "promotion_variants": p.promotion_variants,
                }
                for p in self.patterns
            ],
            "aux_slots": [asdict(s) for s in self.aux_slots],
            "capabilities": self.capabilities.to_dict(),
        }

    def fingerprint(self) -> str:
        import hashlib

        return hashlib.sha256(self.serialized().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CompiledSemanticRuleset:
    """Compiled product for rulesets that use the semantic DSL.

    ``_legacy_compiled`` is an inspection-only handle (geometry/table
    equivalence audits); it is never a runtime execution path for the new
    semantics — the legacy compiler itself refuses semantic rulesets.
    """

    ir: CompiledSemanticIR
    _legacy_compiled: Any = None


# ================================================================ validation


def _stratum_index(stratum: str) -> int:
    return SEMANTIC_STRATA.index(stratum)


def _component_stratum(component: str) -> str:
    """Static dependency stratum of a compiled component."""
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
    """Compiler-assigned cost class (users never fill this in)."""
    if primitive_kind in GEOMETRY_KINDS:
        return "C1"
    if primitive_kind in TARGET_RELATIONS:
        return "C1"
    if primitive_kind in ("path_clear", "path_first_blocker_owner", "path_last_blocker_owner"):
        return "C1"
    if primitive_kind in ("path_count_eq", "path_count_range"):
        return "C2"
    if primitive_kind == "state_guard" or primitive_kind == "slot_guard":
        return "C2"
    if primitive_kind in ("own_anchor_safe", "squares_not_attacked"):
        return "C3"
    if primitive_kind in ("move", "remove", "remove_from_hand", "place", "set_current_type"):
        return "C3"
    if primitive_kind in ("clear_right", "set_token", "clear_token", "shift"):
        return "C3"
    if primitive_kind in POSTCONDITION_KINDS:
        return "C4"
    return "C1"


def validate_compiled_pattern(pattern: CompiledMovePattern, slot_ids: tuple[int, ...]) -> list[str]:
    """Structural validation of one compiled pattern; returns error list."""
    errors: list[str] = []
    if not pattern.geometry or any(g not in GEOMETRY_KINDS for g in pattern.geometry):
        errors.append("geometry must be a non-empty subset of {GEOMETRY_KINDS}")
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
        sel = guard.selector
        if sel.owner not in SELECTOR_OWNERS or sel.type_mode not in SELECTOR_TYPE_MODES:
            errors.append("invalid selector")
        if sel.promoted not in SELECTOR_PROMOTED or sel.location not in SELECTOR_LOCATIONS:
            errors.append("invalid selector")
        if sel.spatial not in SELECTOR_SPATIAL:
            errors.append(f"unknown spatial selector {sel.spatial}")
        if sel.spatial_ref not in SELECTOR_SPATIAL_REFS:
            errors.append(f"unknown spatial ref {sel.spatial_ref}")
    for sg in pattern.slot_guards:
        if sg.comparison not in COMPARISON_OPS:
            errors.append(f"unknown slot comparison {sg.comparison}")
        if sg.slot_id not in slot_ids:
            errors.append(f"slot guard references undeclared slot {sg.slot_id}")
    if len(pattern.effects) > MAX_SEMANTIC_EFFECTS:
        errors.append(
            f"effect cardinality {len(pattern.effects)} exceeds {MAX_SEMANTIC_EFFECTS}"
        )
    for effect in pattern.effects:
        if effect.kind not in SEMANTIC_EFFECT_KINDS:
            errors.append(f"unknown effect kind {effect.kind}")
        if effect.square_ref not in EFFECT_SQUARE_REFS:
            errors.append(f"unknown effect square ref {effect.square_ref}")
        if effect.kind in ("clear_right", "set_token", "clear_token"):
            if effect.slot_id is None or effect.slot_id not in slot_ids:
                errors.append(f"slot effect references undeclared slot {effect.slot_id}")
    for invariant in pattern.invariants:
        if invariant.kind not in INVARIANT_KINDS:
            errors.append(f"unknown invariant kind {invariant.kind}")
        if invariant.kind == "squares_not_attacked":
            if not invariant.square_refs:
                errors.append("squares_not_attacked requires square_refs")
            if len(invariant.square_refs) > 4:
                errors.append("squares_not_attacked supports at most 4 square refs")
    if len(pattern.postconditions) > 2:
        errors.append("postcondition count exceeds 2")
    for pc in pattern.postconditions:
        if pc.kind not in POSTCONDITION_KINDS:
            errors.append(f"unknown postcondition kind {pc.kind}")
        if pc.kind == "no_legal_reply":
            if pc.max_stratum not in SEMANTIC_STRATA:
                errors.append("invalid probe stratum")
            elif _stratum_index(pc.max_stratum) > _stratum_index(MAX_PROBE_STRATUM):
                errors.append("probe max_stratum must be <= S3 (stratified)")
            elif _stratum_index(pc.max_stratum) >= _stratum_index("S4"):
                errors.append("probe must be strictly below S4")
    if pattern.cost_class not in COST_CLASSES:
        errors.append(f"unknown cost class {pattern.cost_class}")
    if pattern.stratum not in SEMANTIC_STRATA:
        errors.append(f"unknown stratum {pattern.stratum}")

    # Dependency DAG: no component may exceed the pattern stratum.
    components = list(pattern.geometry)
    components.append(pattern.target.kind)
    components.extend(pp.kind for pp in pattern.path)
    components.extend("state_guard" for _ in pattern.guards)
    components.extend("slot_guard" for _ in pattern.slot_guards)
    components.extend(i.kind for i in pattern.invariants)
    components.extend(pc.kind for pc in pattern.postconditions)
    for component in components:
        if _stratum_index(_component_stratum(component)) > _stratum_index(pattern.stratum):
            errors.append(
                f"component {component} exceeds pattern stratum {pattern.stratum}"
            )
    return errors


def validate_ir(ir: CompiledSemanticIR) -> list[str]:
    """Full IR validation: aux slots typed/bounded, patterns valid, DAG ok."""
    errors: list[str] = []
    slot_ids = tuple(slot.slot_id for slot in ir.aux_slots)
    if len(slot_ids) != len(set(slot_ids)):
        errors.append("duplicate aux slot ids")
    if len(ir.aux_slots) > MAX_SEMANTIC_AUX_SLOTS:
        errors.append("aux slot count exceeds 8")
    for slot in ir.aux_slots:
        if slot.kind not in AUX_STATE_KINDS or slot.lifetime not in AUX_LIFETIMES:
            errors.append(f"invalid aux slot {slot}")
    for pattern in ir.patterns:
        errors.extend(validate_compiled_pattern(pattern, slot_ids))
    return errors
