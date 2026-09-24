"""Isolated V2 local semantic-option prior and coverage audit.

This module deliberately does not import human material tables.  It either
returns local rule-derived board/hand option measures plus an explicit
semantic coverage ledger, or marks the audit inconclusive before validation.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.core.coordinates import index_to_square
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import geometry_candidates
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


OCCUPANCY_STATES = ("empty", "own", "enemy")
STATE_PROBABILITY = 1.0 / len(OCCUPANCY_STATES)
SUPPORTED_TARGETS = {
    "target_empty": {"empty"},
    "target_enemy": {"enemy"},
    "target_friendly": {"own"},
    "target_any": set(OCCUPANCY_STATES),
}
SUPPORTED_EFFECTS = {"move", "remove", "place", "remove_from_hand"}
SEPARATE_STATE_EFFECTS = {"set_token", "clear_token"}
SUPPORTED_PATH_PREDICATES = {"path_clear"}


def _area(compiled: Any) -> int:
    rows = compiled.support.initial_position
    return sum(len(row) for row in rows)


def _effect_key(pattern: Any) -> tuple[Any, ...]:
    return tuple(
        (
            effect.kind,
            effect.from_ref,
            effect.to_ref,
            effect.square_ref,
            effect.piece_owner,
            effect.disposition,
            effect.piece_type_ref,
            effect.type_ref,
        )
        for effect in pattern.effects
        if effect.kind not in SEPARATE_STATE_EFFECTS
    )


def _simple_source_guard_supported(guard: Any) -> bool:
    subject = guard.subject_ref
    spatial = guard.spatial
    return bool(
        guard.aggregation == "count"
        and guard.owner == "self"
        and guard.type_ref.kind in ("action_base", "action_current")
        and guard.compare_field in ("base", "current")
        and guard.promoted in ("no", "any")
        and guard.location == "board"
        and guard.comparison == "eq"
        and guard.value == 1
        and subject is not None
        and subject.kind == "source"
        and spatial.kind == "same_rank"
        and len(spatial.refs) == 1
        and spatial.refs[0].kind == "fixed"
    )


def _source_guards_hold(compiled: Any, pattern: Any, type_id: str, owner: int, source: int) -> bool | None:
    if not pattern.guards:
        return True
    if any(not _simple_source_guard_supported(guard) for guard in pattern.guards):
        return None
    n = compiled.board_size
    source_square = index_to_square(source, n)
    promoted_types = {
        destination
        for metadata in compiled.support.type_metadata.values()
        for destination in metadata.promotion_target_ids
    }
    actor_is_base = type_id not in promoted_types
    for guard in pattern.guards:
        if guard.promoted == "no" and not actor_is_base:
            return False
        ref = guard.spatial.refs[0]
        file, rank = ref.square
        if ref.owner_relative and owner == 1:
            file, rank = n - 1 - file, n - 1 - rank
        if source_square.rank != rank:
            return False
    return True


def _path_probability(pattern: Any, path: tuple[int, ...]) -> float | None:
    if any(predicate.kind not in SUPPORTED_PATH_PREDICATES for predicate in pattern.path):
        return None
    # In the frozen local measure each distinct path square is independently
    # empty with probability 1/3.  The exact finite joint probability is thus
    # the product; duplicate path squares are removed defensively.
    return STATE_PROBABILITY ** len(set(path))


def expected_action_probability(
    path: tuple[int, ...], target_relation: str, path_predicates: tuple[Any, ...] = (),
) -> float | None:
    """Exact local-measure probability for a supported path/endpoint event."""
    if target_relation not in SUPPORTED_TARGETS:
        return None
    if any(predicate.kind not in SUPPORTED_PATH_PREDICATES for predicate in path_predicates):
        return None
    clear_probability = STATE_PROBABILITY ** len(set(path))
    endpoint_probability = len(SUPPORTED_TARGETS[target_relation]) * STATE_PROBABILITY
    return clear_probability * endpoint_probability


def expected_drop_option_count(masks: tuple[tuple[bool, ...], ...]) -> float:
    """Expected held-token drop outcomes, averaged over owners and squares."""
    area = sum(len(mask) for mask in masks[:2])
    if area == 0:
        return 0.0
    return sum(STATE_PROBABILITY for mask in masks[:2] for allowed in mask if allowed) / area


def _is_history_conditional(pattern: Any) -> bool:
    if pattern.slot_guards:
        return True
    return any(
        ref is not None and ref.kind == "aux_slot_square"
        for guard in pattern.guards
        for ref in (*guard.spatial.refs, guard.subject_ref)
    )


def _unsupported_reasons(pattern: Any, geometry: Any) -> list[str]:
    reasons: list[str] = []
    if geometry.kind not in ("leap", "ray", "drop"):
        reasons.append(f"geometry:{geometry.kind}")
    if pattern.target.kind not in SUPPORTED_TARGETS:
        reasons.append(f"target:{pattern.target.kind}")
    if any(predicate.kind not in SUPPORTED_PATH_PREDICATES for predicate in pattern.path):
        reasons.append("path_predicate_not_exactly_modeled")
    if pattern.guards and not _is_history_conditional(pattern) and any(
        not _simple_source_guard_supported(guard) for guard in pattern.guards
    ):
        reasons.append("board_state_guard_not_exactly_modeled")
    if pattern.invariants:
        reasons.append("action_invariant_not_exactly_modeled")
    if pattern.postconditions:
        reasons.append("postcondition_not_intrinsic_movement")
    if any(effect.kind not in SUPPORTED_EFFECTS and effect.kind not in SEPARATE_STATE_EFFECTS for effect in pattern.effects):
        reasons.append("effect_not_exactly_modeled")
    if geometry.kind != "drop":
        moves = [effect for effect in pattern.effects if effect.kind == "move"]
        if len(moves) != 1:
            reasons.append("not_one_source_to_target_move")
        elif (moves[0].from_ref is None or moves[0].from_ref.kind != "source"
              or moves[0].to_ref is None or moves[0].to_ref.kind != "target"):
            reasons.append("move_refs_not_source_to_target")
    return sorted(set(reasons))


def _promotion_targets(compiled: Any, type_id: str, owner: int, source: int, target: int) -> tuple[str, ...]:
    metadata = compiled.support.type_metadata[type_id]
    if not metadata.is_promotable:
        return ()
    pair = (
        index_to_square(source, compiled.board_size),
        index_to_square(target, compiled.board_size),
    )
    allowed_by_owner = compiled.support.promotion_allowed.get(type_id, ())
    if owner < 0 or owner >= len(allowed_by_owner):
        return ()
    return metadata.promotion_target_ids if pair in allowed_by_owner[owner] else ()


def _promotion_forced(compiled: Any, type_id: str, owner: int, target: int) -> bool:
    forced_by_owner = compiled.support.promotion_forced.get(type_id, ())
    if owner < 0 or owner >= len(forced_by_owner):
        return False
    return index_to_square(target, compiled.board_size) in forced_by_owner[owner]


def audit_ruleset(compiled: Any) -> dict[str, Any]:
    """Return candidate option values and explicit semantic coverage.

    History/auxiliary-state guarded patterns are listed separately because
    the frozen score is state-free. Unsupported board predicates, invariants,
    effects, or geometry prevent validation; they are never assigned zero.
    """
    area = _area(compiled)
    if area <= 0:
        raise ValueError("compiled ruleset has no board squares")
    denominator = 2 * area
    by_type: dict[str, dict[str, Any]] = {}
    all_unsupported: list[dict[str, str]] = []
    all_state_dependent: list[dict[str, str]] = []

    for type_id in sorted(compiled.support.type_metadata):
        outcomes: dict[tuple[Any, ...], float] = {}
        unblocked_outcomes: dict[tuple[Any, ...], float] = {}
        drop_outcomes: dict[tuple[Any, ...], float] = {}
        conditional: list[dict[str, Any]] = []
        unsupported: list[dict[str, Any]] = []
        state_dependent: list[dict[str, Any]] = []
        state_transition_effects: list[dict[str, Any]] = []
        source_count = 0
        destination_count = 0
        promotion_rows: dict[tuple[str, str, bool], float] = defaultdict(float)
        components = {"quiet": 0.0, "capture": 0.0, "blocked_path": 0.0, "drop": 0.0}

        for pattern in compiled.ir.patterns:
            if type_id not in pattern.type_ids:
                continue
            stateful_effects = [effect for effect in pattern.effects if effect.kind in SEPARATE_STATE_EFFECTS]
            if stateful_effects:
                state_transition_effects.extend({
                    "pattern": pattern.name,
                    "effect": effect.kind,
                    "slot_id": effect.slot_id,
                    "square_ref": repr(effect.square_ref),
                    "classification": "history_or_auxiliary_transition_effect_not_an_extra_material_option",
                } for effect in stateful_effects)
            for geometry_id in pattern.geometry_ids:
                geometry = compiled.ir.geometry[geometry_id]
                if _is_history_conditional(pattern):
                    conditional.append({
                        "pattern": pattern.name,
                        "geometry": geometry.kind,
                        "guards": [guard.aggregation for guard in pattern.guards],
                        "slot_guards": len(pattern.slot_guards),
                        "effects": [effect.kind for effect in pattern.effects],
                        "classification": "excluded_state_free_history_or_auxiliary_state",
                    })
                    continue
                reasons = _unsupported_reasons(pattern, geometry)
                if reasons:
                    if set(reasons) == {"action_invariant_not_exactly_modeled"}:
                        state_dependent.append({
                            "pattern": pattern.name,
                            "geometry": geometry.kind,
                            "invariants": [invariant.kind for invariant in pattern.invariants],
                            "classification": "global_legality_invariant_requires_joint_board_state",
                        })
                        all_state_dependent.extend({
                            "type": type_id,
                            "pattern": pattern.name,
                            "reason": "global_legality_invariant_requires_joint_board_state",
                        } for _ in (0,))
                    else:
                        unsupported.append({"pattern": pattern.name, "geometry": geometry.kind, "reasons": reasons})
                        all_unsupported.extend({"type": type_id, "pattern": pattern.name, "reason": reason} for reason in reasons)
                    # Retain a clearly partial geometry-only diagnostic when
                    # the sole omitted condition is a global action invariant.
                    # The enclosing audit remains INCONCLUSIVE and may not be
                    # compared with human values.
                    if set(reasons) != {"action_invariant_not_exactly_modeled"}:
                        continue

                if geometry.kind == "drop":
                    masks = compiled.support.drop_allowed.get(type_id, ())
                    if not masks:
                        continue
                    for owner, mask in enumerate(masks[:2]):
                        for target, allowed in enumerate(mask):
                            if not allowed:
                                continue
                            # Drop target must be empty.  The effect key keeps
                            # semantically distinct drop transitions distinct.
                            key = (owner, target, "empty", "drop", _effect_key(pattern))
                            drop_outcomes[key] = STATE_PROBABILITY
                    continue

                for owner in (0, 1):
                    for source in range(area):
                        guard_holds = _source_guards_hold(compiled, pattern, type_id, owner, source)
                        if guard_holds is None:
                            continue
                        if not guard_holds:
                            continue
                        for target, path in geometry_candidates(geometry, str(owner), source):
                            p_path = _path_probability(pattern, path)
                            if p_path is None:
                                continue
                            source_count += 1
                            destination_count += 1
                            for state in sorted(SUPPORTED_TARGETS[pattern.target.kind]):
                                p = p_path * STATE_PROBABILITY
                                p_unblocked = STATE_PROBABILITY
                                promoted_targets = _promotion_targets(compiled, type_id, owner, source, target) if pattern.promotion_mode != "none" else ()
                                forced = bool(promoted_targets) and _promotion_forced(compiled, type_id, owner, target)
                                effect_key = _effect_key(pattern)
                                if not forced:
                                    key = (owner, source, target, path, state, effect_key, type_id)
                                    outcomes[key] = max(outcomes.get(key, 0.0), p)
                                    unblocked_outcomes[key] = max(unblocked_outcomes.get(key, 0.0), p_unblocked)
                                for promoted_type in promoted_targets:
                                    key = (owner, source, target, path, state, effect_key, promoted_type)
                                    outcomes[key] = max(outcomes.get(key, 0.0), p)
                                    unblocked_outcomes[key] = max(unblocked_outcomes.get(key, 0.0), p_unblocked)
                                    transition_key = (type_id, promoted_type, forced, owner, source, target, path, state)
                                    promotion_rows[transition_key] = p / denominator

        board_value = sum(outcomes.values()) / denominator
        hand_value = sum(drop_outcomes.values()) / denominator
        for key, probability in outcomes.items():
            component = "capture" if key[4] == "enemy" else "quiet"
            components[component] += probability / denominator
        components["blocked_path"] = sum(
            max(0.0, probability - outcomes.get(key, 0.0))
            for key, probability in unblocked_outcomes.items()
        ) / denominator
        components["drop"] = hand_value
        by_type[type_id] = {
            "board_intrinsic": board_value,
            "hand_drop": hand_value,
            "score_coverage": "PARTIAL_UNVALIDATED" if unsupported or state_dependent else "COMPLETE",
            "components": components,
            "movement_source_candidates": source_count,
            "movement_destination_candidates": destination_count,
            "promotion_transitions": [
                {"source_type": source_type, "destination_type": destination_type,
                 "forced": forced, "expected_transition_mass": mass}
                for (source_type, destination_type, forced, _owner, _source, _target, _path, _state), mass
                in sorted(promotion_rows.items())
            ],
            "conditional_rules": conditional,
            "state_dependent_rules": state_dependent,
            "state_transition_effects": state_transition_effects,
            "unsupported_semantics": unsupported,
        }

    coverage_complete = not all_unsupported and not all_state_dependent
    return {
        "schema_version": 1,
        "kind": "STATIC_SEMANTIC_MATERIAL_PRIOR_V2_LOCAL_OPTION_AUDIT",
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "board_square_count": area,
        "local_state_measure": {state: STATE_PROBABILITY for state in OCCUPANCY_STATES},
        "source_weighting": "uniform_over_both_owners_and_all_board_squares",
        "coverage_complete": coverage_complete,
        "classification": "COVERAGE_READY_FOR_STATIC_VALIDATION" if coverage_complete else "STATIC_SEMANTIC_MATERIAL_PRIOR_V2_INCONCLUSIVE",
        "unsupported_semantics": all_unsupported,
        "state_dependent_semantics": all_state_dependent,
        "ledger": by_type,
        "human_metrics_computed": False,
    }


def audit_benchmarks() -> dict[str, Any]:
    """Run only the pre-validation semantic coverage and option audit."""
    return {
        "schema_version": 1,
        "kind": "STATIC_SEMANTIC_MATERIAL_PRIOR_V2_COVERAGE_GATE",
        "human_metrics_computed": False,
        "rulesets": {
            "western_chess": audit_ruleset(
                compile_semantic_ruleset(build_western_chess_ruleset())
            ),
            "standard_shogi": audit_ruleset(
                compile_semantic_ruleset(build_standard_shogi_ruleset())
            ),
        },
    }


def main() -> int:
    result = audit_benchmarks()
    output = ROOT / ".generic_chess_flow" / "static-semantic-material-prior-v2-coverage.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        name: {
            "classification": row["classification"],
            "coverage_complete": row["coverage_complete"],
            "unsupported_count": len(row["unsupported_semantics"]),
            "state_dependent_count": len(row["state_dependent_semantics"]),
            "human_metrics_computed": row["human_metrics_computed"],
        }
        for name, row in result["rulesets"].items()
    }
    print(json.dumps({"output": str(output), "rulesets": summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
