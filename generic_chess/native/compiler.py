"""Python RuleSet -> native compiled rules (payload build + validation)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any

from ..core.movement import LeapAtom, RayAtom
from ..ai.evaluation.config import (
    MATE_SCORE,
    MATE_THRESHOLD,
    MAX_STATIC_EVAL,
    config_hash,
)
from ..rules.compiled import CompiledRuleSet
from . import _module, native_available

NATIVE_SCHEMA_VERSION = "native-0.4.0"

GC_MAX_PLY = 512
GC_MAX_HAND = 256

SEMANTIC_PAYLOAD_VERSION = 2
GC_SEM_MAX_TYPES = 64
GC_SEM_MAX_PATTERNS = 256
GC_SEM_MAX_GEOMETRIES = 4096
GC_SEM_MAX_AUX_SLOTS = 8
GC_SEM_MAX_EFFECTS = 4
GC_SEM_MAX_INVARIANT_REFS = 4

# Frozen numeric enum codes (ADR-017 section 9).  Unknown values fail closed.
_SEM_GEOMETRY_CODES = {"leap": 0, "ray": 1, "drop": 2}
_SEM_TARGET_CODES = {
    "target_empty": 0,
    "target_enemy": 1,
    "target_friendly": 2,
    "target_any": 3,
}
_SEM_PATH_CODES = {
    "path_clear": 0,
    "path_count_eq": 1,
    "path_count_range": 2,
    "path_first_blocker_owner": 3,
    "path_last_blocker_owner": 4,
}
_SEM_OWNER_CODES = {"self": 0, "opponent": 1, "any": 2}
_SEM_AGGREGATION_CODES = {"exists": 0, "count": 1}
_SEM_COMPARISON_CODES = {"eq": 0, "ne": 1, "lt": 2, "le": 3, "gt": 4, "ge": 5}
_SEM_FIELD_CODES = {"base": 0, "current": 1}
_SEM_PROMOTED_CODES = {"yes": 0, "no": 1, "any": 2}
_SEM_TYPE_REF_CODES = {
    "action_base": 0,
    "action_current": 1,
    "explicit": 2,
    "any": 3,
}
_SEM_SQUARE_REF_CODES = {
    "source": 0,
    "target": 1,
    "fixed": 2,
    "offset_from_source": 3,
    "offset_from_target": 4,
    "path_step": 5,
    "aux_slot_square": 6,
}
_SEM_SPATIAL_CODES = {
    "same_file": 0,
    "same_rank": 1,
    "exact": 2,
    "adjacent": 3,
    "path_between": 4,
    "zone": 5,
}
_SEM_AUX_VALUE_CODES = {"bool": 0, "square_or_none": 1}
_SEM_AUX_SCOPE_CODES = {"global": 0, "per_owner": 1}
_SEM_AUX_LIFETIME_CODES = {"persistent": 0, "expire_next_turn": 1}
_SEM_TRIGGER_EVENT_CODES = {
    "piece_leaves_square": 0,
    "piece_removed_from_square": 1,
}
_SEM_EFFECT_CODES = {
    "move": 0,
    "remove": 1,
    "remove_from_hand": 2,
    "place": 3,
    "set_current_type": 4,
    "set_bool": 5,
    "clear_right": 6,
    "set_token": 7,
    "clear_token": 8,
    "shift": 9,
}
_SEM_DISPOSITION_CODES = {"capture_to_hand": 0, "remove_from_game": 1}
_SEM_INVARIANT_CODES = {"own_anchor_safe": 0, "squares_not_attacked": 1}
_SEM_POSTCONDITION_CODES = {"opponent_checked": 0, "no_legal_reply": 1}
_SEM_PROMOTION_MODE_CODES = {
    "none": 0,
    "inherit_compiled_masks": 1,
    "explicit": 2,
}
_SEM_COST_CODES = {"C0": 0, "C1": 1, "C2": 2, "C3": 3, "C4": 4}
_SEM_STRATUM_CODES = {"S0": 0, "S1": 1, "S2": 2, "S3": 3, "S4": 4, "S5": 5}
# `location` is not enumerated in ADR-017 because hand predicates are
# fail-closed at compile time; board=0 is the only reachable value.
_SEM_LOCATION_CODES = {"board": 0, "hand": 1}


def _sem_enum(table, value, what, fingerprint):
    code = table.get(value)
    if code is None:
        raise NativeUnsupportedRuleError(
            f"unsupported semantic {what} {value!r} "
            f"(ruleset fingerprint {fingerprint}, "
            f"native schema {NATIVE_SCHEMA_VERSION})"
        )
    return code


def _sem_square_ref(ref, n, fingerprint):
    out = {
        "kind": _sem_enum(_SEM_SQUARE_REF_CODES, ref.kind, "square_ref kind", fingerprint),
        "square": None,
        "offset": None,
        "owner_relative": 1 if ref.owner_relative else 0,
        "step": None,
        "slot_id": None,
    }
    if ref.kind == "fixed":
        f, r = ref.square
        out["square"] = r * n + f
    elif ref.kind in ("offset_from_source", "offset_from_target"):
        out["offset"] = [ref.offset[0], ref.offset[1]]
    elif ref.kind == "path_step":
        out["step"] = ref.step
    elif ref.kind == "aux_slot_square":
        out["slot_id"] = ref.slot_id
    return out


def _sem_type_ref(ref, type_map, fingerprint):
    out = {
        "kind": _sem_enum(_SEM_TYPE_REF_CODES, ref.kind, "type_ref kind", fingerprint),
        "type_index": None,
    }
    if ref.kind == "explicit":
        out["type_index"] = type_map[ref.type_id]
    return out


def _sem_spatial(sel, n, type_map, zone_map, fingerprint):
    return {
        "kind": _sem_enum(_SEM_SPATIAL_CODES, sel.kind, "spatial kind", fingerprint),
        "refs": [_sem_square_ref(r, n, fingerprint) for r in sel.refs],
        "zone_index": (
            zone_map[sel.zone_id]
            if sel.kind == "zone" and sel.zone_id is not None
            else None
        ),
    }


def _sem_state_guard(g, n, type_map, zone_map, fingerprint):
    return {
        "aggregation": _sem_enum(_SEM_AGGREGATION_CODES, g.aggregation, "aggregation", fingerprint),
        "owner": _sem_enum(_SEM_OWNER_CODES, g.owner, "owner", fingerprint),
        "type_ref": _sem_type_ref(g.type_ref, type_map, fingerprint),
        "compare_field": _sem_enum(_SEM_FIELD_CODES, g.compare_field, "compare_field", fingerprint),
        "promoted": _sem_enum(_SEM_PROMOTED_CODES, g.promoted, "promoted selector", fingerprint),
        "location": _sem_enum(_SEM_LOCATION_CODES, g.location, "location", fingerprint),
        "spatial": _sem_spatial(g.spatial, n, type_map, zone_map, fingerprint),
        "comparison": _sem_enum(_SEM_COMPARISON_CODES, g.comparison, "comparison", fingerprint),
        "value": g.value,
    }


def _sem_slot_guard(sg, n, fingerprint):
    return {
        "slot_id": sg.slot_id,
        "comparison": _sem_enum(_SEM_COMPARISON_CODES, sg.comparison, "comparison", fingerprint),
        "value": sg.value,
        "square_ref": (
            _sem_square_ref(sg.square_ref, n, fingerprint)
            if sg.square_ref is not None
            else None
        ),
    }


def _sem_effect(e, n, type_map, fingerprint):
    return {
        "kind": _sem_enum(_SEM_EFFECT_CODES, e.kind, "effect kind", fingerprint),
        "from_ref": (
            _sem_square_ref(e.from_ref, n, fingerprint)
            if e.from_ref is not None
            else None
        ),
        "to_ref": (
            _sem_square_ref(e.to_ref, n, fingerprint)
            if e.to_ref is not None
            else None
        ),
        "square_ref": (
            _sem_square_ref(e.square_ref, n, fingerprint)
            if e.square_ref is not None
            else None
        ),
        "piece_owner": _sem_enum(_SEM_OWNER_CODES, e.piece_owner, "piece_owner", fingerprint),
        "piece_type_ref": (
            _sem_type_ref(e.piece_type_ref, type_map, fingerprint)
            if e.piece_type_ref is not None
            else None
        ),
        "disposition": (
            _sem_enum(_SEM_DISPOSITION_CODES, e.disposition, "disposition", fingerprint)
            if e.disposition is not None
            else None
        ),
        "slot_id": e.slot_id,
        "type_ref": (
            _sem_type_ref(e.type_ref, type_map, fingerprint)
            if e.type_ref is not None
            else None
        ),
        "count": e.count,
        "value": e.value,
    }


def _sem_invariant(inv, n, fingerprint):
    return {
        "kind": _sem_enum(_SEM_INVARIANT_CODES, inv.kind, "invariant kind", fingerprint),
        "square_refs": [_sem_square_ref(r, n, fingerprint) for r in inv.square_refs],
    }


def _sem_postcondition(pc, fingerprint):
    return {
        "kind": _sem_enum(_SEM_POSTCONDITION_CODES, pc.kind, "postcondition kind", fingerprint),
        "max_stratum": _sem_enum(_SEM_STRATUM_CODES, pc.max_stratum, "max_stratum", fingerprint),
    }


def _sem_path_predicate(pp, fingerprint):
    return {
        "kind": _sem_enum(_SEM_PATH_CODES, pp.kind, "path kind", fingerprint),
        "count": pp.count,
        "lo": pp.lo,
        "hi": pp.hi,
        "owner_filter": _sem_enum(_SEM_OWNER_CODES, pp.owner_filter, "owner_filter", fingerprint),
    }


class NativeUnsupportedRuleError(ValueError):
    """Raised when a RuleSet cannot be expressed by the native kernel."""


class NativeActionError(ValueError):
    """Raised by the public checked action API.

    ``fields`` carries the structured failure context: ``status`` (int code),
    ``reason`` (stable name), ``packed`` (hex), ``kind/from/to/base/promo``,
    ``fingerprint`` and ``ply``.
    """

    def __init__(self, message: str, fields: dict[str, Any]) -> None:
        super().__init__(message)
        self.fields = dict(fields)

    @property
    def status(self) -> int:
        return int(self.fields.get("status", -1))

    @property
    def reason(self) -> str:
        return str(self.fields.get("reason", "unknown"))


@dataclass(frozen=True)
class NativeEvaluationTables:
    """Owns the native evaluation capsule plus identity metadata."""

    capsule: object
    fingerprint: str
    config_hash: str
    evaluator_version: str
    type_count: int

    @property
    def native_schema_version(self) -> str:
        return NATIVE_SCHEMA_VERSION


@dataclass(frozen=True)
class NativeCompilationReport:
    ruleset_fingerprint: str
    type_count: int
    board_squares: int
    leap_atom_entries: int
    ray_atom_entries: int
    estimated_bytes: int
    native_schema_version: str


class NativeCompiledRules:
    """Owns the native rules capsule plus the type index mapping."""

    def __init__(
        self,
        capsule,
        report: NativeCompilationReport,
        type_map: dict[str, int],
        type_ids: list[str],
    ) -> None:
        self._capsule = capsule
        self._report = report
        self._type_map = MappingProxyType(dict(type_map))
        self._type_ids = tuple(type_ids)

    @property
    def capsule(self):
        return self._capsule

    @property
    def fingerprint(self) -> str:
        return self._report.ruleset_fingerprint

    @property
    def type_count(self) -> int:
        return self._report.type_count

    @property
    def type_map(self) -> dict[str, int]:
        return self._type_map

    @property
    def type_ids(self) -> list[str]:
        return self._type_ids

    @property
    def report(self) -> NativeCompilationReport:
        return self._report


def _validate(condition: bool, message: str, fingerprint: str) -> None:
    if not condition:
        raise NativeUnsupportedRuleError(
            f"{message} (ruleset fingerprint {fingerprint}, "
            f"native schema {NATIVE_SCHEMA_VERSION})"
        )


def build_compile_payload(compiled: CompiledRuleSet) -> dict[str, Any]:
    """Convert a CompiledRuleSet into the plain native payload dict."""
    n = compiled.board_size
    fingerprint = compiled.ruleset_fingerprint
    _validate(1 <= n <= 16 and n * n <= 256, "board size out of native range", fingerprint)
    _validate(
        compiled.max_ply <= GC_MAX_PLY,
        f"max_ply {compiled.max_ply} exceeds native limit {GC_MAX_PLY}",
        fingerprint,
    )
    types = tuple(compiled.piece_types)
    _validate(len(types) <= 64, "too many piece types for native kernel", fingerprint)
    type_ids = sorted(t.type_id for t in types)
    type_map = {tid: i for i, tid in enumerate(type_ids)}
    by_id = {t.type_id: t for t in types}

    payload_types = []
    leap_entries = ray_entries = 0
    for tid in type_ids:
        pt = by_id[tid]
        atoms = []
        for atom in pt.movement_atoms:
            if isinstance(atom, LeapAtom):
                atoms.append(
                    {
                        "kind": 0,
                        "df": atom.offset[0],
                        "dr": atom.offset[1],
                        "max_steps": 0,
                    }
                )
                leap_entries += 1
            elif isinstance(atom, RayAtom):
                atoms.append(
                    {
                        "kind": 1,
                        "df": atom.direction[0],
                        "dr": atom.direction[1],
                        "max_steps": atom.max_steps or 0,
                    }
                )
                ray_entries += 1
            else:  # pragma: no cover - MovementAtom is the closed union
                raise NativeUnsupportedRuleError(
                    f"unknown movement atom {atom!r} for type {pt.type_id!r} "
                    f"(ruleset {fingerprint}, native schema {NATIVE_SCHEMA_VERSION})"
                )
        _validate(len(atoms) <= 16, f"type {pt.type_id!r}: too many atoms", fingerprint)
        targets = []
        for tid in pt.promotion_target_ids:
            _validate(
                tid in type_map,
                f"type {pt.type_id!r}: promotion target {tid!r} missing",
                fingerprint,
            )
            targets.append(type_map[tid])
        _validate(len(targets) <= 8, f"type {pt.type_id!r}: too many promotion targets", fingerprint)

        promo_allowed = []
        promo_forced = []
        alive_promo = []
        drop_mask = []
        for owner in (0, 1):
            pairs = [
                (f.rank * n + f.file) << 16 | (t.rank * n + t.file)
                for f, t in compiled.promotion_allowed.get(pt.type_id, ((), ()))[owner]
            ]
            promo_allowed.append(sorted(pairs))
            forced = sorted(
                (s.rank * n + s.file)
                for s in compiled.promotion_forced.get(pt.type_id, (frozenset(), frozenset()))[owner]
            )
            promo_forced.append(forced)
            alive = []
            for idx in range(n * n):
                mask = 0
                for tid in pt.promotion_target_ids:
                    if compiled.empty_mobility[tid][owner][idx]:
                        mask |= 1 << type_map[tid]
                alive.append(mask)
            alive_promo.append(alive)
            allowed_squares = []
            if pt.type_id in compiled.drop_allowed:
                mask = compiled.drop_allowed[pt.type_id][owner]
                allowed_squares = [i for i, ok in enumerate(mask) if ok]
            drop_mask.append(allowed_squares)
        payload_types.append(
            {
                "is_anchor": pt.is_anchor,
                "is_promotable": pt.is_promotable,
                "atoms": atoms,
                "promo_targets": targets,
                "promo_allowed": promo_allowed,
                "promo_forced": promo_forced,
                "alive_promo": alive_promo,
                "drop_mask": drop_mask,
            }
        )

    payload = {
        "fingerprint": fingerprint,
        "width": n,
        "height": n,
        "repetition_limit": compiled.repetition_limit,
        "max_ply": compiled.max_ply,
        "types": payload_types,
    }
    estimated = (
        2 * 2 * 256 * 8  # owner+square hash
        + 2 * 256 * 64 * 8 * 2  # base + current hash
        + 2 * 256 * 8  # promoted hash
        + 2 * 2 * 64 * 64 * 8  # hand hash
        + 2 * 2 * 8  # side hash
        + 64 * 2 * 256 * 8  # alive promo
        + 64 * 2 * 4 * 8 * 2  # forced + drop bitsets
        + sum(len(p["promo_allowed"][0]) + len(p["promo_allowed"][1]) for p in payload_types) * 4
    )
    return payload, NativeCompilationReport(
        ruleset_fingerprint=fingerprint,
        type_count=len(types),
        board_squares=n * n,
        leap_atom_entries=leap_entries,
        ray_atom_entries=ray_entries,
        estimated_bytes=estimated,
        native_schema_version=NATIVE_SCHEMA_VERSION,
    )


def compile_native_rules(compiled: CompiledRuleSet) -> NativeCompiledRules:
    """Compile a CompiledRuleSet into the native kernel (one-time cost)."""
    if not native_available():
        raise NativeUnsupportedRuleError(
            "native extension is not built; run scripts/build_native_zig.py"
        )
    payload, report = build_compile_payload(compiled)
    capsule = _module().compile_rules(payload)
    type_ids = sorted(t.type_id for t in compiled.piece_types)
    type_map = {tid: i for i, tid in enumerate(type_ids)}
    return NativeCompiledRules(capsule, report, type_map, type_ids)


def compile_native_evaluation(
    native_rules: NativeCompiledRules,
    evaluation_profile,
    evaluation_config,
    *,
    material_override=None,
) -> NativeEvaluationTables:
    """Compile the rule-derived evaluation profile into native tables.

    The same RuleSet may be paired with different ``EvaluationConfig`` objects,
    so the tables are a separate object keyed by ``config_hash``; they are
    never folded into :class:`NativeCompiledRules`.

    ``material_override`` (optional) supplies per-type board/hand material
    weights (e.g. a learnable checkpoint).  It must expose:
    ``quantized_board(type_ids) -> list[int]``,
    ``quantized_hand(type_ids) -> list[int]`` and ``config_hash``.  Anchor
    entries are forced to 0 and are never overridden.  The resulting
    ``config_hash`` differs per checkpoint, so TT entries are never shared
    across evaluators (and callers should create a fresh engine per
    checkpoint).
    """
    if not native_available():
        raise NativeUnsupportedRuleError(
            "native extension is not built; run scripts/build_native_zig.py"
        )
    if evaluation_profile.ruleset_fingerprint != native_rules.fingerprint:
        raise ValueError(
            "evaluation profile fingerprint does not match native rules "
            f"({evaluation_profile.ruleset_fingerprint} vs "
            f"{native_rules.fingerprint})"
        )
    type_ids = native_rules.type_ids
    if material_override is not None:
        board_values = list(material_override.quantized_board(type_ids))
        hand_values = list(material_override.quantized_hand(type_ids))
        if len(board_values) != len(type_ids) or len(hand_values) != len(type_ids):
            raise ValueError(
                "material override quantized tables must cover all native types"
            )
        config_hash_used = str(material_override.config_hash)
        version_used = str(
            getattr(material_override, "evaluator_version", "learnable-material-v1")
        )
    else:
        if evaluation_profile.config_hash != config_hash(evaluation_config):
            raise ValueError(
                "evaluation profile config_hash does not match the evaluation config"
            )
        missing = (
            set(type_ids)
            - set(evaluation_profile.board_value_by_type)
            - set(evaluation_profile.hand_value_by_base_type)
            - set(evaluation_profile.promotion_gain_by_type)
        )
        if missing:
            raise ValueError(
                f"evaluation profile missing native types: {sorted(missing)}"
            )
        for pt in native_rules.type_ids:
            _validate(
                evaluation_profile.board_value_by_type[pt] <= MAX_STATIC_EVAL,
                f"board value for {pt!r} exceeds MAX_STATIC_EVAL",
                native_rules.fingerprint,
            )
        board_values = [
            evaluation_profile.board_value_by_type[tid] for tid in type_ids
        ]
        hand_values = [
            evaluation_profile.hand_value_by_base_type[tid] for tid in type_ids
        ]
        config_hash_used = evaluation_profile.config_hash
        version_used = evaluation_profile.evaluator_version
    payload = {
        "type_count": native_rules.type_count,
        "mate_score": MATE_SCORE,
        "mate_threshold": MATE_THRESHOLD,
        "max_static_eval": MAX_STATIC_EVAL,
        "config_hash": config_hash_used,
        "evaluator_version": version_used,
        "board_value": board_values,
        "hand_value": hand_values,
        "promotion_gain": [
            evaluation_profile.promotion_gain_by_type[tid] for tid in type_ids
        ],
    }
    capsule = _module().compile_evaluation(native_rules.capsule, payload)
    return NativeEvaluationTables(
        capsule=capsule,
        fingerprint=native_rules.fingerprint,
        config_hash=config_hash_used,
        evaluator_version=version_used,
        type_count=native_rules.type_count,
    )


# ---------------------------------------------------------------- C-1 semantic


@dataclass(frozen=True)
class NativeSemanticCompilationReport:
    """Compile-time report for the native semantic payload (Phase 1.9C-1)."""

    ruleset_fingerprint: str
    ir_version: int
    semantic_payload_version: int
    native_schema_version: str
    board_squares: int
    type_count: int
    pattern_count: int
    geometry_count: int
    zone_count: int
    aux_slot_count: int
    trigger_count: int
    estimated_bytes: int
    native_executable: bool = False


class NativeSemanticCompiledRules:
    """Owns the C-owned semantic rules capsule plus reversible ID tuples."""

    def __init__(
        self,
        capsule,
        report: NativeSemanticCompilationReport,
        type_ids,
        pattern_ids,
        geometry_ids,
        zone_ids,
    ) -> None:
        self._capsule = capsule
        self._report = report
        self._type_ids = tuple(type_ids)
        self._pattern_ids = tuple(pattern_ids)
        self._geometry_ids = tuple(geometry_ids)
        self._zone_ids = tuple(zone_ids)

    @property
    def capsule(self):
        return self._capsule

    @property
    def fingerprint(self) -> str:
        return self._report.ruleset_fingerprint

    @property
    def report(self) -> NativeSemanticCompilationReport:
        return self._report

    @property
    def native_executable(self) -> bool:
        """Fail-closed per-ruleset Native payload support result."""
        return bool(self._report.native_executable)

    @property
    def type_ids(self):
        return self._type_ids

    @property
    def pattern_ids(self):
        return self._pattern_ids

    @property
    def geometry_ids(self):
        return self._geometry_ids

    @property
    def zone_ids(self):
        return self._zone_ids


def _native_payload_is_executable(payload, report: NativeSemanticCompilationReport) -> bool:
    """Validate the complete lowered payload shape for the runtime gate.

    The lowering function has already rejected unknown enums and unsupported
    operands.  This second, structural check keeps the per-ruleset capability
    fail-closed if the payload/report contract changes independently.
    """
    required = {
        "semantic_payload_version", "fingerprint", "board_size",
        "repetition_limit", "max_ply", "type_ids", "types",
        "promo_allowed", "promo_forced", "alive_promo", "drop_mask",
        "geometries", "zones", "aux_slots", "triggers", "patterns",
    }
    if not isinstance(payload, dict) or not required.issubset(payload):
        return False
    patterns = payload["patterns"]
    if not isinstance(patterns, list) or len(patterns) != report.pattern_count:
        return False
    pattern_required = {
        "type_indices", "geometry_indices", "target", "path", "guards",
        "slot_guards", "effects", "invariants", "postconditions",
        "promotion_mode", "explicit_promotion_type", "cost", "stratum",
    }
    if any(
        not isinstance(pattern, dict)
        or not pattern_required.issubset(pattern)
        or len(pattern.get("effects", ())) > GC_SEM_MAX_EFFECTS
        or any(
            not isinstance(inv, dict)
            or len(inv.get("square_refs", ())) > GC_SEM_MAX_INVARIANT_REFS
            for inv in pattern.get("invariants", ())
        )
        or any(
            not isinstance(post, dict)
            or post.get("max_stratum", 99) > _SEM_STRATUM_CODES["S3"]
            for post in pattern.get("postconditions", ())
        )
        for pattern in patterns
    ):
        return False
    return (
        payload["semantic_payload_version"] == SEMANTIC_PAYLOAD_VERSION
        and report.ir_version == 2
        and report.native_schema_version == NATIVE_SCHEMA_VERSION
        and report.type_count <= GC_SEM_MAX_TYPES
        and report.pattern_count <= GC_SEM_MAX_PATTERNS
        and report.geometry_count <= GC_SEM_MAX_GEOMETRIES
        and len(payload["types"]) == report.type_count
        and len(payload["geometries"]) == report.geometry_count
        and len(payload["zones"]) == report.zone_count
        and report.aux_slot_count <= GC_SEM_MAX_AUX_SLOTS
        and len(payload["aux_slots"]) == report.aux_slot_count
        and len(payload["triggers"]) == report.trigger_count
        and report.board_squares <= 256
    )


def build_semantic_compile_payload(semantic):
    """Lower ``CompiledSemanticRuleset.ir + .support`` into a deterministic
    numeric native payload (ADR-017).

    Authorities are exactly ``semantic.ir`` and ``semantic.support``;
    ``_legacy_compiled``, high-level RuleSet and movement atoms are never
    consulted.  The payload is the static closure of the frozen semantic IR
    v2 and must be exactly reconstructable from the C-owned capsule.
    """
    ir = semantic.ir
    support = semantic.support
    fingerprint = support.ruleset_fingerprint
    n = support.board_size

    _validate(
        1 <= n <= 16 and n * n <= 256,
        "semantic board size out of native range",
        fingerprint,
    )
    _validate(ir.ir_version == 2, "unsupported semantic IR version", fingerprint)
    _validate(
        support.max_ply <= GC_MAX_PLY,
        f"max_ply {support.max_ply} exceeds native limit {GC_MAX_PLY}",
        fingerprint,
    )
    _validate(
        1 <= support.repetition_limit <= 0xFFFF,
        f"repetition_limit {support.repetition_limit} outside native u16 range",
        fingerprint,
    )

    type_ids = tuple(sorted(support.type_metadata))
    pattern_ids = tuple(p.pattern_id for p in ir.patterns)
    geometry_ids = tuple(sorted(ir.geometry))
    zone_ids = tuple(sorted(ir.zones))
    _validate(len(type_ids) <= GC_SEM_MAX_TYPES, "too many semantic types", fingerprint)
    _validate(
        len(pattern_ids) <= GC_SEM_MAX_PATTERNS,
        "too many semantic patterns",
        fingerprint,
    )
    _validate(
        len(geometry_ids) <= GC_SEM_MAX_GEOMETRIES,
        f"too many semantic geometries (limit {GC_SEM_MAX_GEOMETRIES})",
        fingerprint,
    )
    _validate(
        len(ir.aux_slots) <= GC_SEM_MAX_AUX_SLOTS,
        "too many semantic aux slots",
        fingerprint,
    )
    type_map = {tid: i for i, tid in enumerate(type_ids)}
    geometry_map = {gid: i for i, gid in enumerate(geometry_ids)}
    zone_map = {zid: i for i, zid in enumerate(zone_ids)}

    # ---- support section
    types = []
    for tid in type_ids:
        meta = support.type_metadata[tid]
        types.append(
            {
                "is_anchor": 1 if meta.is_anchor else 0,
                "is_promotable": 1 if meta.is_promotable else 0,
                "promo_targets": [type_map[t] for t in meta.promotion_target_ids],
            }
        )

    promo_allowed = []
    for tid in type_ids:
        pairs = []
        for owner in (0, 1):
            pairs.append(
                sorted(
                    (f.rank * n + f.file) << 16 | (t.rank * n + t.file)
                    for f, t in support.promotion_allowed.get(tid, ((), ()))[owner]
                )
            )
        promo_allowed.append(pairs)

    promo_forced = []
    for tid in type_ids:
        forced = []
        for owner in (0, 1):
            forced.append(
                sorted(
                    s.rank * n + s.file
                    for s in support.promotion_forced.get(tid, (frozenset(), frozenset()))[owner]
                )
            )
        promo_forced.append(forced)

    alive_promo = []
    for tid in type_ids:
        meta = support.type_metadata[tid]
        per_type = []
        for owner in (0, 1):
            masks = []
            for sq in range(n * n):
                mask = 0
                for j, ptid in enumerate(meta.promotion_target_ids):
                    if support.empty_mobility.get(ptid, ((), ()))[owner][sq]:
                        mask |= 1 << j
                masks.append(mask)
            per_type.append(masks)
        alive_promo.append(per_type)

    drop_mask = []
    for tid in type_ids:
        per_type = []
        for owner in (0, 1):
            mask = support.drop_allowed.get(tid, ((), ()))[owner]
            per_type.append([i for i, ok in enumerate(mask) if ok])
        drop_mask.append(per_type)

    # ---- IR section
    geometries = []
    for gid in geometry_ids:
        geo = ir.geometry[gid]
        atom_source = None
        if geo.atom_source is not None:
            atom_source = [type_map[geo.atom_source[0]], geo.atom_source[1]]
        paths = []
        for owner in ("0", "1"):
            per_source = []
            for source in sorted(geo.paths.get(owner, {})):
                path = geo.paths[owner][source]
                if path:
                    per_source.append([source, list(path)])
            paths.append(per_source)
        geometries.append(
            {
                "kind": _sem_enum(_SEM_GEOMETRY_CODES, geo.kind, "geometry kind", fingerprint),
                "min_steps": geo.min_steps,
                "atom_source": atom_source,
                "paths": paths,
            }
        )

    zones = [{"squares": list(ir.zones[zid].squares)} for zid in zone_ids]

    aux_slots = []
    for slot in ir.aux_slots:
        initial = slot.initial
        if slot.value_kind == "square_or_none" and initial is not None:
            initial = [initial[0], initial[1]]
        aux_slots.append(
            {
                "slot_id": slot.slot_id,
                "value_kind": _sem_enum(_SEM_AUX_VALUE_CODES, slot.value_kind, "aux value kind", fingerprint),
                "scope": _sem_enum(_SEM_AUX_SCOPE_CODES, slot.scope, "aux scope", fingerprint),
                "lifetime": _sem_enum(_SEM_AUX_LIFETIME_CODES, slot.lifetime, "aux lifetime", fingerprint),
                "initial": initial,
            }
        )

    triggers = []
    for t in ir.triggers:
        triggers.append(
            {
                "slot_id": t.slot_id,
                "event": _sem_enum(_SEM_TRIGGER_EVENT_CODES, t.event, "trigger event", fingerprint),
                "square_ref": _sem_square_ref(t.square_ref, n, fingerprint),
                "owner": _sem_enum(_SEM_OWNER_CODES, t.owner, "trigger owner", fingerprint),
            }
        )

    patterns = []
    for p in ir.patterns:
        _validate(
            len(p.effects) <= GC_SEM_MAX_EFFECTS,
            f"pattern {p.pattern_id}: too many effects",
            fingerprint,
        )
        for inv in p.invariants:
            if inv.kind == "squares_not_attacked":
                _validate(
                    len(inv.square_refs) <= GC_SEM_MAX_INVARIANT_REFS,
                    f"pattern {p.pattern_id}: too many invariant refs",
                    fingerprint,
                )
        for pc in p.postconditions:
            if pc.max_stratum not in ("S0", "S1", "S2", "S3"):
                raise NativeUnsupportedRuleError(
                    f"postcondition probe stratum {pc.max_stratum} exceeds S3 "
                    f"(ruleset fingerprint {fingerprint}, "
                    f"native schema {NATIVE_SCHEMA_VERSION})"
                )
        patterns.append(
            {
                "type_indices": [type_map[t] for t in p.type_ids],
                "geometry_indices": [geometry_map[g] for g in p.geometry_ids],
                "target": _sem_enum(_SEM_TARGET_CODES, p.target.kind, "target kind", fingerprint),
                "path": [_sem_path_predicate(pp, fingerprint) for pp in p.path],
                "guards": [
                    _sem_state_guard(g, n, type_map, zone_map, fingerprint)
                    for g in p.guards
                ],
                "slot_guards": [
                    _sem_slot_guard(sg, n, fingerprint) for sg in p.slot_guards
                ],
                "effects": [_sem_effect(e, n, type_map, fingerprint) for e in p.effects],
                "invariants": [_sem_invariant(inv, n, fingerprint) for inv in p.invariants],
                "postconditions": [
                    _sem_postcondition(pc, fingerprint) for pc in p.postconditions
                ],
                "promotion_mode": _sem_enum(
                    _SEM_PROMOTION_MODE_CODES, p.promotion_mode, "promotion mode", fingerprint
                ),
                "explicit_promotion_type": (
                    type_map[p.explicit_promotion_type]
                    if p.explicit_promotion_type is not None
                    else None
                ),
                "cost": _sem_enum(_SEM_COST_CODES, p.cost_class, "cost class", fingerprint),
                "stratum": _sem_enum(_SEM_STRATUM_CODES, p.stratum, "stratum", fingerprint),
            }
        )

    payload = {
        "semantic_payload_version": SEMANTIC_PAYLOAD_VERSION,
        "fingerprint": fingerprint,
        "board_size": n,
        "repetition_limit": support.repetition_limit,
        "max_ply": support.max_ply,
        # Runtime identity is the Python semantic_position_key JSON.  It
        # contains public type IDs, so the Native executor must own this
        # stable mapping instead of relying on a Python wrapper at runtime.
        "type_ids": list(type_ids),
        "types": types,
        "promo_allowed": promo_allowed,
        "promo_forced": promo_forced,
        "alive_promo": alive_promo,
        "drop_mask": drop_mask,
        "geometries": geometries,
        "zones": zones,
        "aux_slots": aux_slots,
        "triggers": triggers,
        "patterns": patterns,
    }

    estimated = (
        65
        + len(types) * 16
        + sum(
            (len(pairs[0]) + len(pairs[1])) * 4
            + (len(forced[0]) + len(forced[1])) * 2
            + (len(drop[0]) + len(drop[1])) * 2
            for pairs, forced, drop in zip(promo_allowed, promo_forced, drop_mask)
        )
        + len(type_ids) * 2 * n * n * 8
        + sum(
            (len(o0) + len(o1)) * (4 + 2 * sum(len(e) for e in o0 + o1))
            for g in geometries
            for o0, o1 in [tuple(g["paths"])]
        )
        + sum(len(z["squares"]) * 2 for z in zones)
        + len(aux_slots) * 24
        + len(triggers) * 40
        + len(patterns) * 96
    )

    report = NativeSemanticCompilationReport(
        ruleset_fingerprint=fingerprint,
        ir_version=ir.ir_version,
        semantic_payload_version=SEMANTIC_PAYLOAD_VERSION,
        native_schema_version=NATIVE_SCHEMA_VERSION,
        board_squares=n * n,
        type_count=len(type_ids),
        pattern_count=len(pattern_ids),
        geometry_count=len(geometry_ids),
        zone_count=len(zone_ids),
        aux_slot_count=len(aux_slots),
        trigger_count=len(triggers),
        estimated_bytes=estimated,
        native_executable=False,
    )
    report = replace(report, native_executable=_native_payload_is_executable(payload, report))
    return payload, report


def compile_native_semantic_rules(semantic) -> NativeSemanticCompiledRules:
    """Compile a CompiledSemanticRuleset into the C-owned semantic rules
    capsule (compile-only contract; no semantic execution)."""
    if not native_available():
        raise NativeUnsupportedRuleError(
            "native extension is not built; run scripts/build_native_zig.py"
        )
    payload, report = build_semantic_compile_payload(semantic)
    capsule = _module().compile_semantic_rules(payload)
    type_ids = tuple(sorted(semantic.support.type_metadata))
    pattern_ids = tuple(p.pattern_id for p in semantic.ir.patterns)
    geometry_ids = tuple(sorted(semantic.ir.geometry))
    zone_ids = tuple(sorted(semantic.ir.zones))
    return NativeSemanticCompiledRules(
        capsule=capsule,
        report=report,
        type_ids=type_ids,
        pattern_ids=pattern_ids,
        geometry_ids=geometry_ids,
        zone_ids=zone_ids,
    )
