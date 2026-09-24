"""Frozen V2A phase-averaged, rule-only board material prior.

No human reference data is imported here.  All occupancy calculations use
exact rational polynomial arithmetic and compiled executable rule semantics.
"""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from fractions import Fraction
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
from scripts.audit_static_semantic_material_prior_v2 import (
    OCCUPANCY_STATES,
    SEPARATE_STATE_EFFECTS,
    SUPPORTED_EFFECTS,
    SUPPORTED_PATH_PREDICATES,
    SUPPORTED_TARGETS,
    _effect_key,
    _is_history_conditional,
    _promotion_forced,
    _promotion_targets,
    _simple_source_guard_supported,
    _source_guards_hold,
    audit_ruleset as audit_v2_ruleset,
)

Poly = tuple[Fraction, ...]  # ascending powers of rho
Cube = tuple[tuple[int, tuple[str, ...]], ...]
EventSet = tuple[Cube, ...]
EMPTY: Poly = (Fraction(1),)
ZERO: Poly = (Fraction(0),)
LABEL_WEIGHT: dict[str, Poly] = {
    "empty": (Fraction(1), Fraction(-1)),
    "own": (Fraction(0), Fraction(1, 2)),
    "enemy": (Fraction(0), Fraction(1, 2)),
}
ALL_LABELS = frozenset(OCCUPANCY_STATES)
ALLOWED_EFFECTS = SUPPORTED_EFFECTS | SEPARATE_STATE_EFFECTS | {"clear_right"}


def _trim(poly: tuple[Fraction, ...]) -> Poly:
    out = list(poly)
    while len(out) > 1 and out[-1] == 0:
        out.pop()
    return tuple(out)


def _poly_add(left: Poly, right: Poly) -> Poly:
    size = max(len(left), len(right))
    return _trim(tuple(
        (left[i] if i < len(left) else Fraction(0))
        + (right[i] if i < len(right) else Fraction(0))
        for i in range(size)
    ))


def _poly_mul(left: Poly, right: Poly) -> Poly:
    out = [Fraction(0)] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            out[i + j] += a * b
    return _trim(tuple(out))


def _cube(items: dict[int, frozenset[str]]) -> Cube:
    return tuple(sorted(
        (square, tuple(sorted(labels)))
        for square, labels in items.items()
        if labels != ALL_LABELS
    ))


def _event_set(cubes: list[Cube] | tuple[Cube, ...]) -> EventSet:
    return tuple(sorted(set(cubes)))


def union_probability_polynomial(cubes: list[Cube] | tuple[Cube, ...]) -> Poly:
    """Return exact conditional P(union of occupancy cubes | rho)."""
    initial = _event_set(cubes)

    @lru_cache(maxsize=None)
    def visit(events: EventSet) -> Poly:
        if not events:
            return ZERO
        if () in events:
            return EMPTY
        square = min(sq for cube in events for sq, _labels in cube)
        result = ZERO
        for label in OCCUPANCY_STATES:
            branches: list[Cube] = []
            for cube in events:
                constraints = dict(cube)
                allowed = constraints.get(square)
                if allowed is not None and label not in allowed:
                    continue
                constraints.pop(square, None)
                branches.append(_cube({sq: frozenset(vals) for sq, vals in constraints.items()}))
            result = _poly_add(result, _poly_mul(LABEL_WEIGHT[label], visit(_event_set(branches))))
        return result

    return visit(initial)


def integrate_density_polynomial(poly: Poly, rho_max: Fraction) -> Fraction:
    """Mean of a polynomial over Uniform[0,rho_max], exact over rationals."""
    if rho_max <= 0:
        return poly[0]
    return sum(
        coefficient * rho_max ** (power + 1) / (power + 1)
        for power, coefficient in enumerate(poly)
    ) / rho_max


def evaluate_density_polynomial(poly: Poly, rho: Fraction) -> Fraction:
    return sum(coefficient * rho ** power for power, coefficient in enumerate(poly))


def event_probability(cube: Cube, rho_max: Fraction) -> Fraction:
    return integrate_density_polynomial(union_probability_polynomial([cube]), rho_max)


def _inventory_bound(compiled: Any) -> dict[str, Any]:
    """Fail closed unless compiled actions cannot increase physical token count."""
    reasons: list[str] = []
    pattern_rows: list[dict[str, Any]] = []
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
        pattern_rows.append({
            "pattern": pattern.name,
            "geometry": sorted(geometry_kinds),
            "effects": counts,
            "token_effect": "drop transfers hand to board" if is_drop else "move/promote preserve; capture transfers or removes",
        })

    initial = compiled.support.initial_position
    initial_tokens = sum(cell is not None for row in initial for cell in row)
    area = sum(len(row) for row in initial)
    if area <= 0:
        reasons.append("empty_initial_board")
    rho_max = min(Fraction(1), Fraction(initial_tokens, area)) if area else Fraction(0)
    return {
        "complete": not reasons,
        "initial_token_count": initial_tokens,
        "board_square_count": area,
        "rho_max": f"{rho_max.numerator}/{rho_max.denominator}",
        "rho_max_decimal": float(rho_max),
        "evidence": "compiled initial board plus exhaustive compiled action/effect inventory audit",
        "pattern_effects": pattern_rows,
        "failure_reasons": sorted(set(reasons)),
    }


def _intrinsic_unsupported(pattern: Any, geometry: Any) -> list[str]:
    reasons: list[str] = []
    if geometry.kind not in ("leap", "ray"):
        reasons.append(f"geometry:{geometry.kind}")
    if pattern.target.kind not in SUPPORTED_TARGETS:
        reasons.append(f"target:{pattern.target.kind}")
    if any(pred.kind not in SUPPORTED_PATH_PREDICATES for pred in pattern.path):
        reasons.append("path_predicate_not_exactly_modeled")
    if pattern.guards and any(not _simple_source_guard_supported(guard) for guard in pattern.guards):
        reasons.append("intrinsic_source_or_state_guard_not_exactly_modeled")
    dynamic_kinds = {"own_anchor_safe", "squares_not_attacked"}
    unknown_invariants = {inv.kind for inv in pattern.invariants} - dynamic_kinds
    if unknown_invariants:
        reasons.append(f"unknown_invariant:{sorted(unknown_invariants)}")
    if pattern.postconditions:
        reasons.append("intrinsic_postcondition_not_exactly_modeled")
    if any(effect.kind not in ALLOWED_EFFECTS for effect in pattern.effects):
        reasons.append("effect_not_exactly_modeled")
    moves = [effect for effect in pattern.effects if effect.kind == "move"]
    if len(moves) != 1 or moves[0].from_ref is None or moves[0].from_ref.kind != "source" or moves[0].to_ref is None or moves[0].to_ref.kind != "target":
        reasons.append("not_one_source_to_target_move")
    return sorted(set(reasons))


def _make_cube(path: tuple[int, ...], relation: str, *, clear_path: bool) -> Cube:
    constraints: dict[int, frozenset[str]] = {}
    if clear_path:
        for square in set(path):
            constraints[square] = frozenset({"empty"})
    targets = SUPPORTED_TARGETS[relation]
    if targets != ALL_LABELS:
        # geometry_candidates never returns the source as its target.
        constraints[-1] = frozenset(targets)  # replaced by caller with real target index
    return _cube(constraints)


def _with_target(cube: Cube, target: int) -> Cube:
    return tuple(sorted((target if square == -1 else square, labels) for square, labels in cube))


def _group_probability(groups: dict[tuple[Any, ...], dict[str, Any]], rho_max: Fraction) -> tuple[dict[tuple[Any, ...], Fraction], Fraction]:
    values: dict[tuple[Any, ...], Fraction] = {}
    for key, row in groups.items():
        values[key] = integrate_density_polynomial(union_probability_polynomial(row["cubes"]), rho_max)
    return values, sum(values.values(), Fraction(0))


def _push(groups: dict[tuple[Any, ...], dict[str, Any]], key: tuple[Any, ...], cube: Cube, **metadata: Any) -> None:
    row = groups.setdefault(key, {"cubes": [], **metadata})
    row["cubes"].append(cube)


def audit_ruleset_v2a(compiled: Any) -> dict[str, Any]:
    inventory = _inventory_bound(compiled)
    if not inventory["complete"]:
        return {
            "classification": "STATIC_MATERIAL_PRIOR_V2A_BOARD_INCONCLUSIVE",
            "coverage_complete": False,
            "inventory_bound": inventory,
            "ledger": {},
            "unsupported_intrinsic_semantics": [],
            "human_metrics_computed": False,
        }
    rho_max = Fraction(*map(int, inventory["rho_max"].split("/")))
    area = inventory["board_square_count"]
    denominator = 2 * area
    v2 = audit_v2_ruleset(compiled)  # calculation-only baseline; no human tables imported
    unsupported_all: list[dict[str, Any]] = []
    state_freeze_ledger: list[dict[str, Any]] = []
    by_type: dict[str, dict[str, Any]] = {}

    for type_id in sorted(compiled.support.type_metadata):
        groups: dict[tuple[Any, ...], dict[str, Any]] = {}
        unrestricted_groups: dict[tuple[Any, ...], dict[str, Any]] = {}
        ray_actual: dict[tuple[Any, ...], dict[str, Any]] = {}
        ray_clear: dict[tuple[Any, ...], dict[str, Any]] = {}
        held_rows: list[dict[str, Any]] = []
        dynamic_rows: set[tuple[str, str]] = set()
        history_rows: list[dict[str, Any]] = []
        unsupported: list[dict[str, Any]] = []
        source_candidates = 0
        source_excluded_candidates = 0
        destination_squares: set[tuple[int, int]] = set()
        promotion_mass_groups: dict[tuple[Any, ...], dict[str, Any]] = {}
        promotion_details: set[tuple[str, str, bool]] = set()

        for pattern in compiled.ir.patterns:
            if type_id not in pattern.type_ids:
                continue
            for gid in pattern.geometry_ids:
                geometry = compiled.ir.geometry[gid]
                if _is_history_conditional(pattern):
                    history_rows.append({
                        "pattern": pattern.name,
                        "geometry": geometry.kind,
                        "classification": "history_or_auxiliary_state; no stationary prior",
                    })
                    continue
                if geometry.kind == "drop":
                    held_rows.append({
                        "pattern": pattern.name,
                        "geometry": geometry.kind,
                        "guards": [guard.spatial.kind for guard in pattern.guards],
                        "invariants": [inv.kind for inv in pattern.invariants],
                        "postconditions": [post.kind for post in pattern.postconditions],
                        "classification": "HELD_OR_REENTRY_SEMANTICS; excluded from board score",
                    })
                    continue

                reasons = _intrinsic_unsupported(pattern, geometry)
                dynamic = {inv.kind for inv in pattern.invariants} & {"own_anchor_safe", "squares_not_attacked"}
                dynamic_rows.update((pattern.name, kind) for kind in dynamic)
                if reasons:
                    entry = {"pattern": pattern.name, "geometry": geometry.kind, "reasons": reasons}
                    unsupported.append(entry)
                    unsupported_all.append({"type": type_id, **entry})
                    continue

                for owner in (0, 1):
                    for source in range(area):
                        guard_holds = _source_guards_hold(compiled, pattern, type_id, owner, source)
                        if guard_holds is None:
                            entry = {"pattern": pattern.name, "geometry": geometry.kind,
                                     "reasons": ["source_guard_evaluation_incomplete"]}
                            unsupported.append(entry)
                            unsupported_all.append({"type": type_id, **entry})
                            continue
                        for target, path in geometry_candidates(geometry, str(owner), source):
                            source_candidates += 1
                            destination_squares.add((source, target))
                            if not guard_holds:
                                source_excluded_candidates += 1
                            path_kinds = {pred.kind for pred in pattern.path}
                            clear_path = geometry.kind == "ray" or "path_clear" in path_kinds
                            if path_kinds - SUPPORTED_PATH_PREDICATES:
                                continue
                            for state in sorted(SUPPORTED_TARGETS[pattern.target.kind]):
                                target_relation = {"empty": "target_empty", "enemy": "target_enemy",
                                                   "own": "target_friendly"}[state]
                                cube = _with_target(_make_cube(path, target_relation, clear_path=clear_path), target)
                                promoted_targets = (
                                    _promotion_targets(compiled, type_id, owner, source, target)
                                    if pattern.promotion_mode != "none" else ()
                                )
                                forced = bool(promoted_targets) and _promotion_forced(compiled, type_id, owner, target)
                                effect_key = _effect_key(pattern)
                                final_types = (() if forced else (type_id,)) + tuple(promoted_targets)
                                for final_type in final_types:
                                    key = (owner, source, target, state, effect_key, final_type)
                                    metadata = {
                                        "state": state,
                                        "promoted": final_type != type_id,
                                        "capture": state == "enemy",
                                        "geometry": geometry.kind,
                                    }
                                    _push(unrestricted_groups, key, cube, **metadata)
                                    if guard_holds:
                                        _push(groups, key, cube, **metadata)
                                    if geometry.kind == "ray":
                                        if guard_holds:
                                            _push(ray_clear, key, _with_target(_make_cube((), target_relation, clear_path=False), target), **metadata)
                                            _push(ray_actual, key, cube, **metadata)
                                    if final_type != type_id:
                                        promotion_details.add((type_id, final_type, forced))
                                        _push(promotion_mass_groups, key, cube, **metadata)

        outcome_values, total = _group_probability(groups, rho_max)
        fixed_label_total = sum(
            (evaluate_density_polynomial(union_probability_polynomial(row["cubes"]), Fraction(2, 3))
             for row in groups.values()),
            Fraction(0),
        )
        unrestricted_values, unrestricted_total = _group_probability(unrestricted_groups, rho_max)
        ray_values, ray_total = _group_probability(ray_actual, rho_max)
        ray_clear_values, ray_clear_total = _group_probability(ray_clear, rho_max)
        promotion_values, promotion_total = _group_probability(promotion_mass_groups, rho_max)
        quiet = capture = Fraction(0)
        for key, value in outcome_values.items():
            if key[3] == "enemy":
                capture += value
            else:
                quiet += value
        raw = total / denominator
        v2_row = v2["ledger"].get(type_id, {})
        masks = compiled.support.drop_allowed.get(type_id, ())
        allowed_drops = sum(sum(bool(x) for x in mask) for mask in masks[:2])
        held_count = len(held_rows) + (1 if allowed_drops else 0)
        dynamic_count = sum(1 for _ in dynamic_rows)
        pawn_special = [row for row in held_rows if row["postconditions"] or row["guards"]]
        by_type[type_id] = {
            "v2_fixed_occupancy_board_intrinsic": v2_row.get("board_intrinsic"),
            "v2a_phase_averaged_board_intrinsic": float(raw),
            "v2a_raw_exact": f"{raw.numerator}/{raw.denominator}",
            "fixed_three_label_reproduction": {
                "v2a_semantics_at_rho_2_3": float(fixed_label_total / denominator),
                "v2_original_board_intrinsic": v2_row.get("board_intrinsic"),
                "absolute_difference": abs(float(fixed_label_total / denominator) - float(v2_row.get("board_intrinsic", 0.0))),
            },
            "components": {
                "quiet": float(quiet / denominator),
                "capture": float(capture / denominator),
                "ray_path_attenuation": float(max(Fraction(0), (ray_clear_total - ray_total) / denominator)),
                "source_restriction_excluded_raw": float(max(Fraction(0), (unrestricted_total - total) / denominator)),
                "immediate_promotion_branch_mass": float(promotion_total / denominator),
                "held_drop": 0.0,
            },
            "dynamic_positional_legality_ledger_count": dynamic_count,
            "dynamic_positional_legality_reason": "global positional legality; excluded from intrinsic piece-type material prior",
            "held_drop_semantics_ledger_count": held_count,
            "held_drop_special_rows": pawn_special,
            "drop_mask_allowed_outcomes_ledgered_not_scored": allowed_drops,
            "history_auxiliary_rules": history_rows,
            "intrinsic_unsupported_semantics": unsupported,
            "source_destination_candidates": source_candidates,
            "source_restricted_candidate_count": source_excluded_candidates,
            "distinct_geometric_source_destination_pairs": len(destination_squares),
            "promotion_transitions": [
                {"source_type": a, "destination_type": b, "forced": c}
                for a, b, c in sorted(promotion_details)
            ],
            "v2a_coverage": "COMPLETE" if not unsupported else "INCOMPLETE",
        }

    coverage_complete = inventory["complete"] and not unsupported_all
    return {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_PRIOR_V2A_PHASE_AVERAGED_BOARD_AUDIT",
        "density_model": {
            "rho_distribution": "Uniform[0,rho_max]",
            "conditional_square_labels": {"empty": "1-rho", "own": "rho/2", "enemy": "rho/2"},
            "rho_max_includes_zero_density_reference_endpoint": True,
            "is_empirical_game_phase_distribution": False,
            "integration": "exact rational polynomial; union events conditionally before shared-rho integration",
        },
        "inventory_bound": inventory,
        "coverage_complete": coverage_complete,
        "classification": "STATIC_MATERIAL_PRIOR_V2A_BOARD_READY_FOR_HUMAN_VALIDATION" if coverage_complete else "STATIC_MATERIAL_PRIOR_V2A_BOARD_INCONCLUSIVE",
        "human_metrics_computed": False,
        "unsupported_intrinsic_semantics": unsupported_all,
        "state_freeze_ledger": state_freeze_ledger,
        "ledger": by_type,
    }


def audit_benchmarks_v2a() -> dict[str, Any]:
    rulesets = {
        "western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
        "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset()),
    }
    return {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_PRIOR_V2A_BOARD_COVERAGE_GATE",
        "human_metrics_computed": False,
        "rulesets": {name: audit_ruleset_v2a(compiled) for name, compiled in rulesets.items()},
    }


def main() -> int:
    result = audit_benchmarks_v2a()
    output = ROOT / ".generic_chess_flow" / "static-semantic-material-prior-v2a-board.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        name: {
            "classification": row["classification"],
            "coverage_complete": row["coverage_complete"],
            "inventory_bound_complete": row["inventory_bound"]["complete"],
            "rho_max": row["inventory_bound"]["rho_max"],
            "unsupported_intrinsic_count": len(row["unsupported_intrinsic_semantics"]),
            "human_metrics_computed": row["human_metrics_computed"],
        }
        for name, row in result["rulesets"].items()
    }
    print(json.dumps({"output": str(output), "rulesets": summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
