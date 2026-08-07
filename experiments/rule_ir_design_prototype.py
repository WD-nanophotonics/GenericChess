"""Structural prototype for the proposed Generic Rule Semantic IR.

Phase 1.9A-2 design artifact ONLY.  Production code must never import this
module: it defines a *proposed* compiled-semantic schema and runs structural
validation (stratum ordering, effect cardinality, typed aux slots, cost
classes, absence of game-name tokens, dependency-cycle rejection).  It does
not implement any move generation or rule execution.

The five stress tests (screen-ray capture, king-side shift, double-step
token capture, file-occupancy drop guard, drop-with-no-reply) and five
counterexample "weird" rules are expressed with the same small closed
primitive set; no game name appears in any execution primitive kind.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


# ================================================================ primitives

# Execution primitive kinds (closed sets; all lower-case, no game names).
GEOMETRY_KINDS = ("leap", "ray", "drop")
PATH_KINDS = (
    "path_clear",                       # zero occupied intermediate squares
    "path_count_eq",                    # exactly n occupied intermediate squares
    "path_count_range",                 # lo..hi occupied intermediate squares
    "path_first_blocker_owner",         # owner filter on the first blocker
    "path_last_blocker_owner",          # owner filter on the last blocker
)
TARGET_KINDS = (
    "target_empty",
    "target_enemy",
    "target_friendly",
    "target_any",
)
SELECTOR_OWNER = ("self", "opponent", "any")
SELECTOR_TYPE_MODE = ("base", "current", "any")
SELECTOR_PROMOTED = ("yes", "no", "any")
SELECTOR_LOCATION = ("board", "hand")
SELECTOR_SPATIAL = (
    "same_file",
    "same_rank",
    "zone",
    "exact",
    "adjacent",
    "path_between",
)
STATE_AGGREGATION = ("exists", "count")
COMPARISON_OPS = ("eq", "ne", "lt", "le", "gt", "ge")
EFFECT_KINDS = (
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
AUX_KINDS = ("right", "token_square")
AUX_LIFETIMES = ("persistent", "expire_next_turn")
INVARIANT_KINDS = ("own_anchor_safe", "squares_not_attacked")
POSTCONDITION_KINDS = ("opponent_checked", "no_legal_reply")
PROBE_KINDS = ("exists_legal_reply",)
COST_CLASSES = ("C0", "C1", "C2", "C3", "C4")
STRATA = ("S0", "S1", "S2", "S3", "S4", "S5")

# Design envelope (compile-time fixed bounds for the first IR).
MAX_EFFECTS_PER_ACTION = 4
MAX_PREDICATES_PER_TEMPLATE = 8
MAX_AUX_SLOTS_PER_RULESET = 8
MAX_POSTCONDITIONS_PER_TEMPLATE = 2
MAX_PROBE_STRATUM = "S3"  # stratified probe: nested replies never re-enter S4

# Tokens that must never appear as execution primitive kinds (or their
# parameters).  Human-readable debug labels are allowed elsewhere.
FORBIDDEN_EXECUTION_TOKENS = (
    "pawn",
    "king",
    "rook",
    "bishop",
    "knight",
    "cannon",
    "castle",
    "castl",
    "shogi",
    "chess",
    "xiangqi",
    "nifu",
    "uchifuzume",
    "en_passant",
)


# ================================================================ model


@dataclass(frozen=True, slots=True)
class AuxSlot:
    """Typed auxiliary semantic state slot (right or ephemeral token)."""

    slot_id: int
    kind: str
    lifetime: str


@dataclass(frozen=True, slots=True)
class StateQuery:
    """Pre-action state predicate: aggregation over a piece selector."""

    aggregation: str                 # exists | count
    owner: str                       # self | opponent | any
    type_mode: str                   # base | current | any
    promoted: str                    # yes | no | any
    location: str                    # board | hand
    spatial: str                     # same_file | same_rank | zone | ...
    comparison: str                  # eq | ne | lt | le | gt | ge
    value: int = 0


@dataclass(frozen=True, slots=True)
class SlotQuery:
    """Pre-action guard reading a typed auxiliary slot."""

    slot_id: int
    comparison: str                  # eq | ne | ...
    value: int = 0                   # bool 1/0 for rights; square ref for tokens


@dataclass(frozen=True, slots=True)
class PathPredicate:
    """Occupancy condition along the candidate path (source..target)."""

    kind: str
    count: int | None = None
    lo: int | None = None
    hi: int | None = None
    owner_filter: str = "any"


@dataclass(frozen=True, slots=True)
class TargetPredicate:
    kind: str


@dataclass(frozen=True, slots=True)
class Effect:
    kind: str
    square_ref: str = "target"       # target | source | token | partner_square
    slot_id: int | None = None
    type_id: str | None = None


@dataclass(frozen=True, slots=True)
class Postcondition:
    kind: str
    probe_stratum: str = "S3"        # used only by no_legal_reply


@dataclass(frozen=True, slots=True)
class IRTemplate:
    """One compiled action template (proposed schema)."""

    name: str
    geometry: tuple[str, ...]
    target: TargetPredicate | None = None
    path: tuple[PathPredicate, ...] = ()
    guards: tuple[StateQuery, ...] = ()
    slot_guards: tuple[SlotQuery, ...] = ()
    effects: tuple[Effect, ...] = ()
    aux_slots: tuple[AuxSlot, ...] = ()
    invariants: tuple[str, ...] = ()
    postconditions: tuple[Postcondition, ...] = ()
    cost_class: str = "C1"
    stratum: str = "S0"

    def to_dict(self) -> dict:
        return json.loads(json.dumps(asdict(self), sort_keys=True))


# ================================================================ validation


def _stratum_index(stratum: str) -> int:
    return STRATA.index(stratum)


def _stratum_of(component: str) -> str:
    """Static stratum of each template component (dependency source)."""
    if component in GEOMETRY_KINDS or component in TARGET_KINDS:
        return "S0"
    if component in PATH_KINDS:
        return "S0"  # path *structure* is S0; occupancy evaluation is S0/S1
    if component == "state_query":
        return "S1"
    if component in INVARIANT_KINDS:
        return "S2"
    if component == "own_anchor_safe":
        return "S3"
    if component in POSTCONDITION_KINDS:
        return "S4"
    if component in PROBE_KINDS:
        return "S4"
    if component in EFFECT_KINDS or component in AUX_KINDS:
        return "S3"  # effects execute after legality (trial-transition layer)
    raise ValueError(f"unknown component {component!r}")


def _has_forbidden_token(value: Any) -> bool:
    if isinstance(value, str):
        lower = value.lower()
        return any(token in lower for token in FORBIDDEN_EXECUTION_TOKENS)
    if isinstance(value, (list, tuple)):
        return any(_has_forbidden_token(v) for v in value)
    if isinstance(value, dict):
        return any(_has_forbidden_token(k) or _has_forbidden_token(v) for k, v in value.items())
    return False


def validate_template(template: IRTemplate) -> dict:
    """Structural validation; returns a report dict, raises on violation."""
    errors: list[str] = []
    if not template.name:
        errors.append("template name is empty")
    if not template.geometry or any(g not in GEOMETRY_KINDS for g in template.geometry):
        errors.append("geometry must be a non-empty subset of {GEOMETRY_KINDS}")
    if template.target and template.target.kind not in TARGET_KINDS:
        errors.append(f"unknown target kind {template.target.kind}")
    for predicate in template.path:
        if predicate.kind not in PATH_KINDS:
            errors.append(f"unknown path kind {predicate.kind}")
    for query in template.guards:
        if query.aggregation not in STATE_AGGREGATION:
            errors.append(f"unknown aggregation {query.aggregation}")
        if query.comparison not in COMPARISON_OPS:
            errors.append(f"unknown comparison {query.comparison}")
        if query.owner not in SELECTOR_OWNER or query.type_mode not in SELECTOR_TYPE_MODE:
            errors.append("invalid selector")
        if query.promoted not in SELECTOR_PROMOTED or query.location not in SELECTOR_LOCATION:
            errors.append("invalid selector")
        if query.spatial not in SELECTOR_SPATIAL:
            errors.append(f"unknown spatial selector {query.spatial}")
    slot_ids = [slot.slot_id for slot in template.aux_slots]
    for slot_query in template.slot_guards:
        if slot_query.comparison not in COMPARISON_OPS:
            errors.append(f"unknown slot comparison {slot_query.comparison}")
        if slot_query.slot_id not in slot_ids:
            errors.append(
                f"slot guard references undeclared slot {slot_query.slot_id}"
            )
    if len(template.effects) > MAX_EFFECTS_PER_ACTION:
        errors.append(
            f"effect cardinality {len(template.effects)} exceeds "
            f"{MAX_EFFECTS_PER_ACTION}"
        )
    if len(template.guards) + len(template.path) + (
        1 if template.target else 0
    ) > MAX_PREDICATES_PER_TEMPLATE:
        errors.append("predicate count exceeds MAX_PREDICATES_PER_TEMPLATE")
    if len(slot_ids) != len(set(slot_ids)):
        errors.append("duplicate aux slot ids")
    if len(template.aux_slots) > MAX_AUX_SLOTS_PER_RULESET:
        errors.append("aux slot count exceeds MAX_AUX_SLOTS_PER_RULESET")
    for slot in template.aux_slots:
        if slot.kind not in AUX_KINDS or slot.lifetime not in AUX_LIFETIMES:
            errors.append(f"invalid aux slot {slot}")
    for effect in template.effects:
        if effect.kind not in EFFECT_KINDS:
            errors.append(f"unknown effect kind {effect.kind}")
    for invariant in template.invariants:
        if invariant not in INVARIANT_KINDS:
            errors.append(f"unknown invariant kind {invariant}")
    if len(template.postconditions) > MAX_POSTCONDITIONS_PER_TEMPLATE:
        errors.append("postcondition count exceeds maximum")
    for post in template.postconditions:
        if post.kind not in POSTCONDITION_KINDS:
            errors.append(f"unknown postcondition kind {post.kind}")
        if post.kind == "no_legal_reply":
            if post.probe_stratum not in STRATA:
                errors.append("invalid probe stratum")
            elif _stratum_index(post.probe_stratum) > _stratum_index(MAX_PROBE_STRATUM):
                errors.append(
                    "probe stratum must be <= MAX_PROBE_STRATUM (stratified "
                    "probe: nested replies never re-enter S4)"
                )
    if template.cost_class not in COST_CLASSES:
        errors.append(f"unknown cost class {template.cost_class}")
    if template.stratum not in STRATA:
        errors.append(f"unknown stratum {template.stratum}")

    # Dependency acyclicity: every component's static stratum must be at or
    # below the template stratum, and the probe stratum must be strictly
    # below the postcondition stratum (no recursion into S4).
    component_strata = [
        _stratum_of(g) for g in template.geometry
    ] + [_stratum_of(template.target.kind) if template.target else "S0"] + [
        _stratum_of(p.kind) for p in template.path
    ] + [_stratum_of("state_query") for _ in template.guards] + [
        "S1" for _ in template.slot_guards
    ] + [
        _stratum_of(i) for i in template.invariants
    ] + [_stratum_of(p.kind) for p in template.postconditions]
    for stratum in component_strata:
        if _stratum_index(stratum) > _stratum_index(template.stratum):
            errors.append(
                f"component at {stratum} exceeds template stratum {template.stratum}"
            )
    for post in template.postconditions:
        if post.kind == "no_legal_reply":
            probe_idx = _stratum_index(post.probe_stratum)
            post_idx = _stratum_index(_stratum_of(post.kind))
            if probe_idx >= post_idx:
                errors.append("probe stratum must be strictly below S4")

    execution_payload = template.to_dict()
    execution_payload.pop("name", None)  # debug label, never executed
    if _has_forbidden_token(execution_payload):
        errors.append("forbidden game token found in execution template")
    return {
        "name": template.name,
        "valid": not errors,
        "errors": errors,
        "stratum": template.stratum,
        "cost_class": template.cost_class,
        "effect_count": len(template.effects),
        "aux_slots": [s.slot_id for s in template.aux_slots],
    }


def dependency_cycle_rejected() -> dict:
    """Demonstrate the compiler must reject a guard/probe cycle."""
    cycle_template = IRTemplate(
        name="illegal_cycle_probe",
        geometry=("drop",),
        guards=(
            StateQuery(
                aggregation="exists",
                owner="any",
                type_mode="any",
                promoted="any",
                location="board",
                spatial="exact",
                comparison="eq",
                value=1,
            ),
        ),
        effects=(Effect("place"),),
        postconditions=(Postcondition("no_legal_reply", probe_stratum="S4"),),
        cost_class="C4",
        stratum="S4",
    )
    report = validate_template(cycle_template)
    return {
        "description": (
            "a guard that reads a full-legal-reply result while the reply "
            "probe re-enters S4 is rejected (probe stratum must be <= S3)"
        ),
        "rejected": not report["valid"],
        "errors": report["errors"],
    }


# ================================================================ stress tests


def _screen_ray_templates() -> tuple[IRTemplate, IRTemplate]:
    """Xiangqi-cannon-like screen ray: quiet (0 screens) + capture (1 screen)."""
    quiet = IRTemplate(
        name="ray_quiet_screen_free",
        geometry=("ray",),
        target=TargetPredicate("target_empty"),
        path=(PathPredicate("path_clear"),),
        effects=(Effect("move"),),
        cost_class="C1",
        stratum="S3",
    )
    capture = IRTemplate(
        name="ray_capture_one_screen",
        geometry=("ray",),
        target=TargetPredicate("target_enemy"),
        path=(PathPredicate("path_count_eq", count=1, owner_filter="any"),),
        effects=(Effect("remove", square_ref="target"), Effect("move")),
        cost_class="C2",
        stratum="S3",
    )
    return quiet, capture


def _castle_templates() -> tuple[IRTemplate, IRTemplate, IRTemplate]:
    """King-side shift with persistent right + transit guards + rook move."""
    right = AuxSlot(slot_id=0, kind="right", lifetime="persistent")
    castle = IRTemplate(
        name="king_side_shift",
        geometry=("leap",),
        target=TargetPredicate("target_empty"),
        path=(PathPredicate("path_clear"),),
        slot_guards=(SlotQuery(slot_id=0, comparison="eq", value=1),),
        effects=(
            Effect("move"),
            Effect("move", square_ref="partner_square"),
            Effect("clear_right", slot_id=0),
        ),
        aux_slots=(right,),
        invariants=("squares_not_attacked",),
        cost_class="C3",
        stratum="S3",
    )
    # Normal king/rook movement clears the right (compiler emits the same
    # generic effect; the right check itself is a pre-action guard).
    king_move = IRTemplate(
        name="king_shift_clears_right",
        geometry=("leap",),
        target=TargetPredicate("target_any"),
        effects=(Effect("move"), Effect("clear_right", slot_id=0)),
        aux_slots=(right,),
        cost_class="C1",
        stratum="S3",
    )
    rook_clears = IRTemplate(
        name="rook_shift_clears_right",
        geometry=("ray",),
        target=TargetPredicate("target_any"),
        effects=(Effect("move"), Effect("clear_right", slot_id=0)),
        aux_slots=(right,),
        cost_class="C1",
        stratum="S3",
    )
    return castle, king_move, rook_clears


def _en_passant_templates() -> tuple[IRTemplate, IRTemplate]:
    """Double-step token creation + off-target-capture reply template."""
    token = AuxSlot(slot_id=1, kind="token_square", lifetime="expire_next_turn")
    creation = IRTemplate(
        name="double_step_creates_token",
        geometry=("ray",),
        target=TargetPredicate("target_empty"),
        path=(PathPredicate("path_clear"),),
        effects=(Effect("move"), Effect("set_token", slot_id=1)),
        aux_slots=(token,),
        cost_class="C2",
        stratum="S3",
    )
    capture = IRTemplate(
        name="token_adjacent_capture_removes_off_target",
        geometry=("leap",),
        target=TargetPredicate("target_enemy"),
        slot_guards=(SlotQuery(slot_id=1, comparison="eq", value=0),),
        effects=(
            Effect("move"),
            Effect("remove", square_ref="token"),
            Effect("clear_token", slot_id=1),
        ),
        aux_slots=(token,),
        cost_class="C2",
        stratum="S3",
    )
    return creation, capture


def _nifu_template() -> IRTemplate:
    """File-occupancy drop guard (same file, self, unpromoted, matching base)."""
    return IRTemplate(
        name="drop_file_occupancy_guard",
        geometry=("drop",),
        target=TargetPredicate("target_empty"),
        guards=(
            StateQuery(
                aggregation="count",
                owner="self",
                type_mode="base",
                promoted="no",
                location="board",
                spatial="same_file",
                comparison="eq",
                value=0,
            ),
        ),
        effects=(Effect("remove_from_hand"), Effect("place")),
        cost_class="C1",
        stratum="S1",
    )


def _uchifuzume_template() -> IRTemplate:
    """Drop-with-no-legal-reply postcondition (stratified bounded probe)."""
    return IRTemplate(
        name="drop_no_legal_reply_forbidden",
        geometry=("drop",),
        target=TargetPredicate("target_empty"),
        effects=(Effect("remove_from_hand"), Effect("place")),
        invariants=("own_anchor_safe",),
        postconditions=(
            Postcondition("opponent_checked"),
            Postcondition("no_legal_reply", probe_stratum="S3"),
        ),
        cost_class="C4",
        stratum="S4",
    )


def _weird_templates() -> tuple[IRTemplate, ...]:
    """Counterexample rules: the IR must be generic, not five special cases."""
    weird_ray = IRTemplate(
        name="ray_quiet_zero_capture_two_screens",
        geometry=("ray",),
        target=TargetPredicate("target_enemy"),
        path=(PathPredicate("path_count_eq", count=2, owner_filter="any"),),
        effects=(Effect("remove", square_ref="target"), Effect("move")),
        cost_class="C2",
        stratum="S3",
    )
    zone_drop = IRTemplate(
        name="drop_zone_capacity_guard",
        geometry=("drop",),
        target=TargetPredicate("target_empty"),
        guards=(
            StateQuery(
                aggregation="count",
                owner="self",
                type_mode="current",
                promoted="any",
                location="board",
                spatial="zone",
                comparison="lt",
                value=3,
            ),
        ),
        effects=(Effect("remove_from_hand"), Effect("place")),
        cost_class="C1",
        stratum="S1",
    )
    temp_right = IRTemplate(
        name="promotion_grants_one_turn_right",
        geometry=("leap",),
        target=TargetPredicate("target_any"),
        effects=(
            Effect("set_current_type"),
            Effect("set_token", slot_id=2),
            Effect("move"),
        ),
        aux_slots=(AuxSlot(2, "right", "expire_next_turn"),),
        cost_class="C1",
        stratum="S3",
    )
    compound = IRTemplate(
        name="move_and_shift_adjacent_friendly",
        geometry=("leap",),
        target=TargetPredicate("target_empty"),
        effects=(
            Effect("move"),
            Effect("shift", square_ref="partner_square"),
        ),
        cost_class="C1",
        stratum="S3",
    )
    restricted = IRTemplate(
        name="action_class_no_immediate_mate",
        geometry=("ray",),
        target=TargetPredicate("target_enemy"),
        effects=(Effect("remove", square_ref="target"), Effect("move")),
        postconditions=(
            Postcondition("opponent_checked"),
            Postcondition("no_legal_reply", probe_stratum="S3"),
        ),
        cost_class="C4",
        stratum="S4",
    )
    return weird_ray, zone_drop, temp_right, compound, restricted


def build_all_templates() -> dict[str, tuple[IRTemplate, ...]]:
    quiet, capture = _screen_ray_templates()
    castle, king_move, rook_clears = _castle_templates()
    ep_creation, ep_capture = _en_passant_templates()
    return {
        "screen_ray": (quiet, capture),
        "king_side_shift": (castle, king_move, rook_clears),
        "double_step_token": (ep_creation, ep_capture),
        "file_occupancy_drop_guard": (_nifu_template(),),
        "drop_no_legal_reply": (_uchifuzume_template(),),
        "weird_rules": _weird_templates(),
    }


def validate_all() -> dict:
    """Validate every stress/counterexample template; report by group."""
    report: dict[str, Any] = {}
    for group, templates in build_all_templates().items():
        entries = []
        for template in templates:
            entries.append(validate_template(template))
        report[group] = {
            "valid": all(entry["valid"] for entry in entries),
            "templates": entries,
        }
    report["dependency_cycle_rejected"] = dependency_cycle_rejected()
    return report


def serialize_all() -> dict:
    return {
        group: [t.to_dict() for t in templates]
        for group, templates in build_all_templates().items()
    }


if __name__ == "__main__":
    print(json.dumps(validate_all(), indent=2, sort_keys=True))
