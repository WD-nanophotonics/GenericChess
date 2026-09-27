"""Coverage-only V2A audit bound to the currently compiled rulesets.

This module intentionally does not call the V2A option-value calculation. It
emits semantic inventory, exclusions, unsupported reasons, and RuleSet
fingerprints only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from scripts.audit_static_semantic_material_prior_v2a import (
    ALLOWED_EFFECTS,
    _intrinsic_unsupported,
    _is_history_conditional,
    _source_guards_hold,
)


GENERATOR_VERSION = "v2a-coverage-only-3"
SCOPE_CONTRACT = "INTRINSIC_BOARD_SEMANTICS"
_DYNAMIC_INVARIANTS = {"own_anchor_safe", "squares_not_attacked"}


def _semantic_inputs(pattern: Any) -> dict[str, Any]:
    """Preserve the executable conditions behind every coverage classification."""
    return {
        "target": repr(pattern.target),
        "path_predicates": [repr(predicate) for predicate in pattern.path],
        "guards": [repr(guard) for guard in pattern.guards],
        "square_zone_guards": [repr(guard) for guard in pattern.square_zone_guards],
        "slot_guards": [repr(guard) for guard in pattern.slot_guards],
        "effects": [{
            "kind": effect.kind,
            "piece_owner": getattr(effect, "piece_owner", None),
            "disposition": getattr(effect, "disposition", None),
            "slot_id": getattr(effect, "slot_id", None),
            "from_ref": repr(getattr(effect, "from_ref", None)),
            "to_ref": repr(getattr(effect, "to_ref", None)),
            "square_ref": repr(getattr(effect, "square_ref", None)),
        } for effect in pattern.effects],
        "invariants": [repr(invariant) for invariant in pattern.invariants],
        "postconditions": [repr(postcondition) for postcondition in pattern.postconditions],
        "promotion_mode": pattern.promotion_mode,
    }


def _inventory_coverage(compiled: Any) -> dict[str, Any]:
    """Check token-conservation semantics without deriving a density bound."""
    reasons: list[str] = []
    for pattern in compiled.ir.patterns:
        effects = tuple(effect.kind for effect in pattern.effects)
        counts = {kind: effects.count(kind) for kind in set(effects)}
        geometry_kinds = {compiled.ir.geometry[gid].kind for gid in pattern.geometry_ids}
        is_drop = geometry_kinds == {"drop"}
        if not geometry_kinds or not geometry_kinds <= {"leap", "ray", "drop"}:
            reasons.append(f"{pattern.name}:unrecognized_geometry_inventory_effect")
        if any(kind not in ALLOWED_EFFECTS for kind in effects):
            reasons.append(f"{pattern.name}:unrecognized_effect:{sorted(set(effects)-ALLOWED_EFFECTS)}")
        if is_drop:
            if counts.get("place", 0) != 1 or counts.get("remove_from_hand", 0) != 1:
                reasons.append(f"{pattern.name}:drop_not_one_for_one_hand_to_board")
        elif counts.get("place", 0) or counts.get("remove_from_hand", 0):
            reasons.append(f"{pattern.name}:unpaired_board_creation_or_hand_removal")
        for effect in pattern.effects:
            if effect.kind == "remove" and effect.disposition not in ("capture_to_hand", "remove_from_game"):
                reasons.append(f"{pattern.name}:unrecognized_capture_disposition:{effect.disposition}")

    initial = compiled.support.initial_position
    board_area = sum(len(row) for row in initial)
    if board_area <= 0:
        reasons.append("empty_initial_board")
    return {
        "complete": not reasons,
        "board_area": board_area,
        "failure_reasons": sorted(set(reasons)),
    }


def _finite_local_path_supported(pattern: Any) -> bool:
    """Recognize only already-verified finite path occupancy predicates."""
    for predicate in pattern.path:
        if predicate.owner_filter != "any":
            return False
        if predicate.kind == "path_clear":
            if any(value is not None for value in (predicate.count, predicate.lo, predicate.hi)):
                return False
        elif predicate.kind == "path_count_eq":
            if predicate.count != 1 or predicate.lo is not None or predicate.hi is not None:
                return False
        else:
            return False
    return True


def _single_square_empty_guard(guard: Any) -> bool:
    """Exact one-cell occupancy-zero guard over the local three-label space."""
    refs = guard.spatial.refs
    return bool(
        guard.aggregation == "count"
        and guard.owner == "any"
        and guard.type_ref.kind == "any"
        and guard.compare_field == "base"
        and guard.promoted == "any"
        and guard.location == "board"
        and guard.spatial.kind == "exact"
        and len(refs) == 1
        and refs[0].kind == "offset_from_source"
        and refs[0].offset is not None
        and refs[0].owner_relative
        and guard.comparison == "eq"
        and guard.value == 0
        and guard.subject_ref == refs[0]
    )


def _typed_target_guard(guard: Any) -> bool:
    refs = guard.spatial.refs
    return bool(
        guard.aggregation == "count"
        and guard.owner in ("own", "opponent")
        and guard.compare_field == "current"
        and guard.promoted == "any"
        and guard.location == "board"
        and guard.spatial.kind == "exact"
        and len(refs) == 1
        and refs[0].kind == "target"
        and guard.type_ref.kind == "explicit"
        and guard.comparison == "eq"
        and guard.value == 1
        and guard.subject_ref == refs[0]
    )


def _deterministic_domain_guard_supported(compiled: Any, guard: Any) -> bool:
    return bool(
        guard.square_ref.kind in ("source", "target")
        and guard.spatial.kind == "zone"
        and guard.spatial.zone_id in compiled.ir.zones
        and guard.relation in ("inside", "outside")
        and isinstance(guard.owner_relative, bool)
    )


def _domain_guard_holds(
    compiled: Any, guard: Any, owner: int, source: int, target: int
) -> bool | None:
    """Evaluate a compiled source/target zone mask without occupancy weights."""
    if not _deterministic_domain_guard_supported(compiled, guard):
        return None
    width = compiled.board_shape.width
    height = compiled.board_shape.height
    zone = set(compiled.ir.zones[guard.spatial.zone_id].squares)
    if guard.owner_relative and owner == 1:
        zone = {
            (height - 1 - square // width) * width
            + (width - 1 - square % width)
            for square in zone
        }
    selected = source if guard.square_ref.kind == "source" else target
    inside = selected in zone
    return inside if guard.relation == "inside" else not inside


def _coverage_intrinsic_reasons(pattern: Any, geometry: Any, compiled: Any) -> list[str]:
    reasons = _intrinsic_unsupported(pattern, geometry)
    if _finite_local_path_supported(pattern):
        reasons = [reason for reason in reasons if reason != "path_predicate_not_exactly_modeled"]
    if pattern.guards and all(_single_square_empty_guard(g) for g in pattern.guards):
        reasons = [
            reason for reason in reasons
            if reason != "intrinsic_source_or_state_guard_not_exactly_modeled"
        ]
    elif pattern.guards and all(_typed_target_guard(g) for g in pattern.guards):
        reasons = [
            reason for reason in reasons
            if reason != "intrinsic_source_or_state_guard_not_exactly_modeled"
        ]
        reasons.append("typed_target_occupancy_not_in_frozen_alphabet")
    for guard in pattern.square_zone_guards:
        if not _deterministic_domain_guard_supported(compiled, guard):
            ref_kind = guard.square_ref.kind
            position = ref_kind if ref_kind in ("source", "target") else "other"
            reasons.append(f"square_zone_{position}_guard_not_exactly_modeled")
    return sorted(set(reasons))


def audit_coverage_ruleset(compiled: Any, ruleset_name: str) -> dict[str, Any]:
    """Classify current compiled semantics without calculating prior scores."""
    inventory = _inventory_coverage(compiled)
    board_area = inventory["board_area"]
    modeled: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []

    for pattern in compiled.ir.patterns:
        for geometry_id in pattern.geometry_ids:
            geometry = compiled.ir.geometry[geometry_id]
            for invariant in pattern.invariants:
                if invariant.kind in _DYNAMIC_INVARIANTS:
                    excluded.append({
                        "types": sorted(pattern.type_ids),
                    "pattern": pattern.name,
                    "geometry": geometry.kind,
                    "family": "dynamic_positional_legality",
                    "invariant": invariant.kind,
                    "reason": "Global legality depends on joint board state and is explicitly excluded from the intrinsic piece-type prior.",
                    "semantic_inputs": _semantic_inputs(pattern),
                })
            if _is_history_conditional(pattern):
                excluded.append({
                    "types": sorted(pattern.type_ids),
                    "pattern": pattern.name,
                    "geometry": geometry.kind,
                    "family": "history_or_auxiliary_state",
                    "reason": "No stationary auxiliary-state distribution is declared by the V2A contract.",
                    "semantic_inputs": _semantic_inputs(pattern),
                })
                continue
            if geometry.kind == "drop":
                excluded.append({
                    "types": sorted(pattern.type_ids),
                    "pattern": pattern.name,
                    "geometry": geometry.kind,
                    "family": "held_or_reentry_semantics",
                    "reason": "Drop, held-token, inventory, and drop-restriction semantics are explicitly outside the board-only prior.",
                    "semantic_inputs": _semantic_inputs(pattern),
                })
                continue

            reasons = _coverage_intrinsic_reasons(pattern, geometry, compiled)
            if reasons:
                unsupported.append({
                    "types": sorted(pattern.type_ids),
                    "pattern": pattern.name,
                    "geometry": geometry.kind,
                    "reasons": reasons,
                    "semantic_inputs": _semantic_inputs(pattern),
                })
                continue

            guard_complete = not pattern.guards or all(
                _single_square_empty_guard(g) for g in pattern.guards
            )
            if not guard_complete:
                guard_complete = True
                for type_id in sorted(pattern.type_ids):
                    for owner in (0, 1):
                        for source in range(board_area):
                            if _source_guards_hold(compiled, pattern, type_id, owner, source) is None:
                                guard_complete = False
                                break
                        if not guard_complete:
                            break
                    if not guard_complete:
                        break
            if not guard_complete:
                unsupported.append({
                    "types": sorted(pattern.type_ids),
                    "pattern": pattern.name,
                    "geometry": geometry.kind,
                    "reasons": ["source_guard_evaluation_incomplete"],
                    "semantic_inputs": _semantic_inputs(pattern),
                })
                continue

            families = [
                "movement_geometry",
                "quiet_capture_endpoint_relations",
                "path_and_screen_occupancy",
            ]
            if (any(predicate.kind == "path_count_eq" for predicate in pattern.path)
                    or pattern.guards):
                families.append("finite_local_occupancy_predicates")
            if pattern.square_zone_guards:
                families.append("deterministic_geometry_domain_masks")
            modeled.append({
                "types": sorted(pattern.type_ids),
                "pattern": pattern.name,
                "geometry": geometry.kind,
                "semantic_inputs": _semantic_inputs(pattern),
                "families": families + (["immediate_type_transition_outcomes"]
                                         if pattern.promotion_mode != "none" else []),
                "source_guards": "exactly_supported_and_evaluable",
            })

    inventory_complete = inventory["complete"]
    scoped_complete = inventory_complete and not unsupported
    return {
        "ruleset_name": ruleset_name,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "scope_contract": SCOPE_CONTRACT,
        "inventory_complete": inventory_complete,
        "inventory_failure_reasons": inventory["failure_reasons"],
        "IN_SCOPE_MODELED": modeled,
        "OUT_OF_SCOPE_EXPLICIT": excluded,
        "IN_SCOPE_UNSUPPORTED": unsupported,
        "scoped_coverage_complete": scoped_complete,
        "classification": (
            "CURRENT_BUILDERS_SCOPED_COVERAGE_VERIFIED"
            if scoped_complete else "CURRENT_BUILDERS_SCOPED_COVERAGE_NOT_READY"
        ),
    }


def audit_current_builders() -> dict[str, Any]:
    """Compile the current Chess, Shogi, and Xiangqi diagnostic builders."""
    rulesets = (
        ("western_chess", build_western_chess_ruleset()),
        ("standard_shogi", build_standard_shogi_ruleset()),
        ("xiangqi_diagnostic", build_xiangqi_diagnostic_ruleset()),
    )
    return {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_PRIOR_V2A_SCOPED_COVERAGE_ONLY",
        "scope_contract": SCOPE_CONTRACT,
        "generator": {
            "identity": "scripts/audit_static_semantic_material_prior_v2a_coverage.py",
            "version": GENERATOR_VERSION,
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "rulesets": {
            name: audit_coverage_ruleset(compile_semantic_ruleset(rules), name)
            for name, rules in rulesets
        },
    }


def main() -> int:
    result = audit_current_builders()
    output = ROOT / ".generic_chess_flow" / "static-semantic-material-prior-v2a-current-coverage.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        name: {
            "ruleset_fingerprint": row["ruleset_fingerprint"],
            "scope_contract": row["scope_contract"],
            "inventory_complete": row["inventory_complete"],
            "modeled_family_count": len(row["IN_SCOPE_MODELED"]),
            "explicit_exclusion_count": len(row["OUT_OF_SCOPE_EXPLICIT"]),
            "unsupported_count": len(row["IN_SCOPE_UNSUPPORTED"]),
            "scoped_coverage_complete": row["scoped_coverage_complete"],
            "classification": row["classification"],
        }
        for name, row in result["rulesets"].items()
    }
    print(json.dumps({"output": str(output), "rulesets": summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
