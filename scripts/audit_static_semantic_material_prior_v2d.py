"""Zero-game V2D diagnostic: V2C successor options plus opponent-board removal."""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
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
from scripts.audit_static_semantic_material_prior_v2a import (
    SUPPORTED_PATH_PREDICATES,
    SUPPORTED_TARGETS,
    _is_history_conditional,
    _promotion_forced,
    _promotion_targets,
    _intrinsic_unsupported,
    _make_cube,
    _source_guards_hold,
    _with_target,
    geometry_candidates,
)
from scripts.audit_static_semantic_material_prior_v2c import _event_measure_factory

V2C_FREEZE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-freeze.json"
V2C_CANDIDATE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-board.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _preflight_v2c() -> tuple[dict[str, Any], dict[str, Any]]:
    if not V2C_FREEZE.is_file() or not V2C_CANDIDATE.is_file():
        raise RuntimeError("Corrected frozen V2C baseline is unavailable")
    freeze = json.loads(V2C_FREEZE.read_text(encoding="utf-8"))
    for relative, expected in freeze.get("sha256", {}).items():
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != expected:
            raise RuntimeError(f"Corrected V2C baseline hash mismatch: {relative}")
    candidate = json.loads(V2C_CANDIDATE.read_text(encoding="utf-8"))
    for name, row in candidate["rulesets"].items():
        if not row["coverage_complete"] or row["human_reference_imported"] or row["human_metrics_computed"]:
            raise RuntimeError(f"Corrected V2C raw baseline is not eligible: {name}")
    return freeze, candidate


def resolve_removed_square(ref: Any, *, owner: int, source: int, target: int,
                           path: tuple[int, ...], area_width: int) -> int | None:
    """Resolve compiled, position-independent effect-square references or fail closed."""
    kind = ref.kind
    if kind == "source":
        return source
    if kind == "target":
        return target
    if kind == "path_step":
        return path[ref.step] if ref.step is not None and 0 <= ref.step < len(path) else None
    if kind == "fixed":
        if ref.square is None:
            return None
        file, rank = ref.square
        if ref.owner_relative and owner == 1:
            file, rank = area_width - 1 - file, area_width - 1 - rank
        return rank * area_width + file if 0 <= file < area_width and 0 <= rank < area_width else None
    if kind in ("offset_from_source", "offset_from_target"):
        base = source if kind == "offset_from_source" else target
        if ref.offset is None:
            return None
        df, dr = ref.offset
        if ref.owner_relative and owner == 1:
            df, dr = -df, -dr
        file, rank = base % area_width + df, base // area_width + dr
        return rank * area_width + file if 0 <= file < area_width and 0 <= rank < area_width else None
    # An auxiliary-state square has no stationary state-free prior.
    return None


def _constrain_enemy(cube: tuple, square: int) -> tuple | None:
    constraints = dict(cube)
    enemy = frozenset({"enemy"})
    if square in constraints:
        intersection = frozenset(constraints[square]) & enemy
        if not intersection:
            return None
        constraints[square] = tuple(sorted(intersection))
    else:
        constraints[square] = ("enemy",)
    return tuple(sorted(constraints.items()))


def _add_capture_group(groups: dict, key: tuple[int, int, int], cube: tuple, *,
                       pattern_name: str, disposition: str, promotion_choices: tuple[str, ...]) -> None:
    row = groups.setdefault(key, {"cubes": [], "patterns": set(), "dispositions": set(),
                                  "promotion_choices": set(), "promotion_branch_rows": set()})
    row["cubes"].append(cube)
    row["patterns"].add(pattern_name)
    row["dispositions"].add(disposition)
    row["promotion_choices"].update(promotion_choices)
    row["promotion_branch_rows"].add((pattern_name, promotion_choices))


def capture_group_probabilities(groups: dict, *, type_id: str, event_measure) -> dict[tuple[int, int, int], Fraction]:
    """Evaluate each physical removal identity once after unioning semantic descriptions."""
    return {
        key: event_measure(key[0], type_id, list(sorted(set(row["cubes"]))))
        for key, row in groups.items()
    }


def combine_u_c(u: Fraction, c: Fraction) -> Fraction:
    return u + c


def _capture_rows(compiled: Any, type_id: str, event_measure) -> dict[str, Any]:
    area = compiled.support.board_size ** 2
    width = compiled.support.board_size
    groups: dict[tuple[int, int, int], dict[str, Any]] = {}
    history_ledger: list[dict[str, Any]] = []
    excluded_nonopponent_removals: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    observed_dispositions: set[str] = set()

    for pattern in compiled.ir.patterns:
        if type_id not in pattern.type_ids:
            continue
        remove_effects = [e for e in pattern.effects if e.kind == "remove"]
        opponent_effects = [e for e in remove_effects if e.piece_owner == "opponent"]
        ambiguous_effects = [e for e in remove_effects if e.piece_owner not in ("opponent", "self")]
        excluded_nonopponent_removals.extend({"pattern": pattern.name, "piece_owner": effect.piece_owner,
            "effect_square_ref": repr(effect.square_ref), "classification": "not_an_explicit_opponent_board_removal; excluded_from_C"}
            for effect in remove_effects if effect.piece_owner == "self")
        if ambiguous_effects:
            unsupported.append({"pattern": pattern.name, "reason": "remove_effect_owner_not_explicit_opponent"})
        for gid in pattern.geometry_ids:
            geometry = compiled.ir.geometry[gid]
            if geometry.kind not in ("leap", "ray"):
                if opponent_effects:
                    unsupported.append({"pattern": pattern.name, "geometry": geometry.kind,
                                        "reason": "capture_geometry_not_covered_by_v2c_board_model"})
                continue
            if not opponent_effects:
                continue
            for effect in opponent_effects:
                disposition = effect.disposition
                if disposition not in ("remove_from_game", "capture_to_hand"):
                    unsupported.append({"pattern": pattern.name, "reason": "unknown_capture_disposition",
                                        "disposition": disposition})
                    continue
                observed_dispositions.add(disposition)
                if effect.square_ref is None:
                    unsupported.append({"pattern": pattern.name, "reason": "capture_effect_missing_square_ref"})
                    continue
                is_history = _is_history_conditional(pattern)
                if is_history:
                    resolved = set()
                    for owner in (0, 1):
                        for source in range(area):
                            for target, path in geometry_candidates(geometry, str(owner), source):
                                square = resolve_removed_square(effect.square_ref, owner=owner, source=source,
                                                               target=target, path=path, area_width=width)
                                if square is not None:
                                    resolved.add(square)
                    history_ledger.append({"pattern": pattern.name, "geometry": geometry.kind,
                        "effect_square_ref": repr(effect.square_ref), "resolved_removed_square_indices": sorted(resolved),
                        "disposition": disposition, "classification": "history_or_auxiliary_state_excluded_no_stationary_prior"})
                    if not resolved:
                        unsupported.append({"pattern": pattern.name, "reason": "history_capture_removed_square_unresolvable"})
                    continue

                reasons = _intrinsic_unsupported(pattern, geometry)
                if reasons:
                    unsupported.append({"pattern": pattern.name, "geometry": geometry.kind,
                                        "reason": "capture_pattern_outside_v2c_intrinsic_coverage", "details": reasons})
                    continue
                for owner in (0, 1):
                    for source in range(area):
                        guard_holds = _source_guards_hold(compiled, pattern, type_id, owner, source)
                        if guard_holds is None:
                            unsupported.append({"pattern": pattern.name,
                                                "reason": "capture_source_guard_evaluation_incomplete"})
                            continue
                        if not guard_holds:
                            continue
                        for target, path in geometry_candidates(geometry, str(owner), source):
                            removed_square = resolve_removed_square(effect.square_ref, owner=owner, source=source,
                                                                    target=target, path=path, area_width=width)
                            if removed_square is None:
                                unsupported.append({"pattern": pattern.name, "geometry": geometry.kind,
                                    "reason": "capture_effect_square_ref_unresolvable", "effect_square_ref": repr(effect.square_ref)})
                                continue
                            if removed_square == source:
                                unsupported.append({"pattern": pattern.name, "reason": "capture_removes_own_source_square"})
                                continue
                            path_kinds = {predicate.kind for predicate in pattern.path}
                            clear_path = geometry.kind == "ray" or "path_clear" in path_kinds
                            if path_kinds - SUPPORTED_PATH_PREDICATES:
                                unsupported.append({"pattern": pattern.name, "reason": "capture_path_predicate_unsupported"})
                                continue
                            for state in sorted(SUPPORTED_TARGETS[pattern.target.kind]):
                                relation = {"empty": "target_empty", "enemy": "target_enemy",
                                            "own": "target_friendly"}[state]
                                cube = _with_target(_make_cube(path, relation, clear_path=clear_path), target)
                                capture_cube = _constrain_enemy(cube, removed_square)
                                if capture_cube is None:
                                    continue
                                promoted = ()
                                if pattern.promotion_mode != "none":
                                    promoted = _promotion_targets(compiled, type_id, owner, source, target)
                                    choices = promoted if promoted and _promotion_forced(compiled, type_id, owner, target) else (type_id, *promoted)
                                else:
                                    choices = (type_id,)
                                key = (owner, source, removed_square)
                                _add_capture_group(groups, key, capture_cube, pattern_name=pattern.name,
                                                   disposition=disposition, promotion_choices=tuple(choices))

    value_by_key = capture_group_probabilities(groups, type_id=type_id, event_measure=event_measure)
    public_rows = []
    for (owner, source, removed_square), row in sorted(groups.items()):
        cubes = tuple(sorted(set(row["cubes"])))
        probability = value_by_key[(owner, source, removed_square)]
        if probability == 0:
            continue
        public_rows.append({"owner": owner, "source_square": source, "removed_square": removed_square,
            "unique_affordance_key": [owner, source, removed_square], "event_probability_exact": f"{probability.numerator}/{probability.denominator}",
            "semantic_patterns": sorted(row["patterns"]), "capture_dispositions": sorted(row["dispositions"]),
            "promotion_branches_collapsed": len(row["promotion_choices"]),
            "promotion_branch_type_ids": sorted(row["promotion_choices"]), "occupancy_cube_count_after_union": len(cubes)})
    value = sum(value_by_key.values(), Fraction(0)) / (2 * area)
    return {"capture_affordance_exact": f"{value.numerator}/{value.denominator}",
        "capture_affordance": float(value), "unique_capture_affordance_key_count": len(value_by_key),
        "capture_affordance_event_ledger": public_rows, "capture_dispositions_observed": sorted(observed_dispositions),
        "excluded_history_conditioned_capture_rows": history_ledger,
        "excluded_nonopponent_removals": excluded_nonopponent_removals,
        "unsupported_capture_semantics": unsupported,
        "capture_coverage_complete": not unsupported}


def audit_benchmarks_v2d() -> dict[str, Any]:
    freeze, baseline = _preflight_v2c()
    rulesets = {"western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
                "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset())}
    output = {"schema_version": 1, "kind": "STATIC_MATERIAL_PRIOR_V2D_CAPTURE_AFFORDANCE_PRE_REFERENCE_CANDIDATE",
        "human_reference_imported": False, "human_metrics_computed": False, "transport_term_used": False,
        "density_scan_used": False, "floor_fallback_used": False,
        "piece_specific_adjustment": False, "game_specific_adjustment": False,
        "capture_affordance_coefficient": 1,
        "coefficient_reason": "one unit per distinct executable opponent-board-resource removal affordance",
        "scientific_interpretation": "U and C are separately counted executable rule-consequence classes; equal unit weight is a declared falsifiable hypothesis, not an empirically fitted law.",
        "v2c_baseline_freeze_sha256": _sha256(V2C_FREEZE),
        "v2c_baseline_candidate_sha256": freeze["sha256"][".generic_chess_flow/static-semantic-material-prior-v2c-board.json"],
        "rulesets": {}}
    for name, compiled in rulesets.items():
        base = baseline["rulesets"][name]
        type_rows = {}
        capture_coverage = True
        for type_id, urow in base["ledger"].items():
            measure = _event_measure_factory(base["token_state_ledger"], compiled, type_id)
            captures = _capture_rows(compiled, type_id, measure)
            capture_coverage &= captures["capture_coverage_complete"]
            u = Fraction(urow["v2c_exact"])
            c = Fraction(captures["capture_affordance_exact"])
            quiet = Fraction(urow["components_v2c_exact"]["quiet"])
            capture_successor = Fraction(urow["components_v2c_exact"]["capture"])
            m = combine_u_c(u, c)
            type_rows[type_id] = {"v2a": urow["v2a_uniform_0_rho_max"], "v2b": urow["v2b_fixed_rho_max"],
                "v2c_u_exact": f"{u.numerator}/{u.denominator}", "v2c_u": float(u),
                "quiet_successor_contribution_exact": f"{quiet.numerator}/{quiet.denominator}",
                "capture_successor_contribution_inside_u_exact": f"{capture_successor.numerator}/{capture_successor.denominator}",
                "capture_affordance_exact": f"{c.numerator}/{c.denominator}", "capture_affordance": float(c),
                "v2d_m_exact": f"{m.numerator}/{m.denominator}", "v2d_m": float(m),
                "quiet_capture_additive_identity_checked": m == u + c, **captures,
                "held_drop_semantics_ledger_count": urow["held_drop_semantics_ledger_count"],
                "dynamic_positional_legality_ledger_count": urow["dynamic_positional_legality_ledger_count"]}
        coverage = base["coverage_complete"] and capture_coverage
        output["rulesets"][name] = {"coverage_complete": coverage,
            "classification": "STATIC_MATERIAL_PRIOR_V2D_CAPTURE_AFFORDANCE_READY_FOR_HUMAN_VALIDATION" if coverage else "STATIC_MATERIAL_PRIOR_V2D_CAPTURE_AFFORDANCE_INCONCLUSIVE",
            "board_capture_affordance_only": name == "standard_shogi",
            "capture_to_hand_future_hand_value_included": False,
            "ruleset": base["ruleset"], "token_state_ledger": base["token_state_ledger"], "ledger": type_rows}
    output["coverage_complete"] = all(row["coverage_complete"] for row in output["rulesets"].values())
    output["classification"] = ("STATIC_MATERIAL_PRIOR_V2D_CAPTURE_AFFORDANCE_READY_FOR_HUMAN_VALIDATION"
                                 if output["coverage_complete"] else "STATIC_MATERIAL_PRIOR_V2D_CAPTURE_AFFORDANCE_INCONCLUSIVE")
    return output


def main() -> int:
    result = audit_benchmarks_v2d()
    path = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(path), "classification": result["classification"],
                      "coverage_complete": result["coverage_complete"],
                      "capture_key_counts": {name: {tid: row["unique_capture_affordance_key_count"]
                          for tid, row in data["ledger"].items()} for name, data in result["rulesets"].items()}},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
