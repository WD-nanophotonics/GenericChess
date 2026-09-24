"""V2E static option premium for compiled, executable piece-type transitions."""

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
from scripts.audit_static_semantic_material_prior_v2 import _is_history_conditional, _promotion_forced, _promotion_targets
from scripts.audit_static_semantic_material_prior_v2a import (
    SUPPORTED_PATH_PREDICATES,
    SUPPORTED_TARGETS,
    _intrinsic_unsupported,
    _make_cube,
    _source_guards_hold,
    _with_target,
    geometry_candidates,
)
from scripts.audit_static_semantic_material_prior_v2c import _event_measure_factory
from scripts.audit_static_semantic_material_prior_v2d import resolve_removed_square

V2D_FREEZE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-freeze.json"
V2D_CANDIDATE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fstr(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _public_event(event: dict[str, Any]) -> dict[str, Any]:
    public = {key: value for key, value in event.items()
              if key not in {"probability", "destination_capabilities_b0_or_b1", "selected_v_after",
                             "signed_delta", "probability_times_delta"}}
    if "probability" in event:
        public["probability_exact"] = _fstr(event["probability"])
    if "destination_capabilities_b0_or_b1" in event:
        caps = event["destination_capabilities_b0_or_b1"]
        public["destination_capabilities_exact"] = {type_id: _fstr(value) for type_id, value in caps.items()}
        public["destination_capabilities"] = {type_id: float(value) for type_id, value in caps.items()}
        public["selected_v_after_exact"] = _fstr(event["selected_v_after"])
        public["selected_v_after"] = float(event["selected_v_after"])
        public["signed_delta_exact"] = _fstr(event["signed_delta"])
        public["signed_delta"] = float(event["signed_delta"])
        public["probability_times_delta_exact"] = _fstr(event["probability_times_delta"])
        public["probability_times_delta"] = float(event["probability_times_delta"])
    return public


def _load_frozen_v2d() -> tuple[dict[str, Any], dict[str, Any]]:
    if not V2D_FREEZE.is_file() or not V2D_CANDIDATE.is_file():
        raise RuntimeError("Frozen V2D baseline is unavailable")
    freeze = json.loads(V2D_FREEZE.read_text(encoding="utf-8"))
    for relative, expected in freeze.get("sha256", {}).items():
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != expected:
            raise RuntimeError(f"Frozen V2D baseline hash mismatch: {relative}")
    candidate = json.loads(V2D_CANDIDATE.read_text(encoding="utf-8"))
    if candidate.get("human_reference_imported") or candidate.get("human_metrics_computed"):
        raise RuntimeError("Frozen V2D raw baseline must not contain human validation")
    return freeze, candidate


def _add_constraint(cube: tuple, square: int, labels: set[str]) -> tuple | None:
    constraints = dict(cube)
    if square in constraints:
        common = set(constraints[square]) & labels
        if not common:
            return None
        constraints[square] = tuple(sorted(common))
    else:
        constraints[square] = tuple(sorted(labels))
    return tuple(sorted(constraints.items()))


def _effect_rows(compiled: Any, pattern: Any, owner: int, source: int, target: int,
                 path: tuple[int, ...]) -> tuple[tuple[int, str, str], ...] | None:
    rows = []
    for effect in pattern.effects:
        if effect.kind != "remove" or effect.piece_owner != "opponent":
            continue
        if effect.disposition not in ("remove_from_game", "capture_to_hand") or effect.square_ref is None:
            return None
        square = resolve_removed_square(effect.square_ref, owner=owner, source=source,
            target=target, path=path, area_width=compiled.support.board_size)
        if square is None or square == source:
            return None
        rows.append((square, effect.disposition, repr(effect.square_ref)))
    return tuple(sorted(rows))


def canonical_removed_effect_identity(effect_rows: tuple[tuple[int, str, str], ...]) -> tuple[tuple[int, str], ...]:
    """Canonical physical identity: resolved square and disposition, never ref syntax."""
    return tuple(sorted({(square, disposition) for square, disposition, _ref in effect_rows}))


def _add_transition_event(groups: dict, physical_key: tuple, cube: tuple, *,
                         allowed_types: tuple[str, ...], pattern_name: str,
                         forced: bool, promotion_mode: str,
                         effect_square_refs: tuple[str, ...] = ()) -> None:
    row = groups.setdefault(physical_key, {"cubes": [], "option_sets": set(),
        "patterns": set(), "forced_flags": set(), "promotion_modes": set(), "effect_square_refs": set()})
    row["cubes"].append(cube)
    row["option_sets"].add(tuple(sorted(set(allowed_types))))
    row["patterns"].add(pattern_name)
    row["forced_flags"].add(forced)
    row["promotion_modes"].add(promotion_mode)
    row["effect_square_refs"].update(effect_square_refs)


def _transition_events(compiled: Any, type_id: str, event_measure) -> dict[str, Any]:
    area = compiled.support.board_size ** 2
    width = compiled.support.board_size
    groups: dict[tuple, dict[str, Any]] = {}
    history_rows: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    graph_edges: set[tuple[str, str]] = set()
    for pattern in compiled.ir.patterns:
        if type_id not in pattern.type_ids or pattern.promotion_mode == "none":
            continue
        if pattern.promotion_mode not in ("inherit_compiled_masks", "explicit"):
            unsupported.append({"pattern": pattern.name, "reason": "unknown_type_transition_mode"})
            continue
        effects = [effect for effect in pattern.effects if effect.kind == "remove"]
        ambiguous_owner = [effect for effect in effects if effect.piece_owner not in ("opponent", "self")]
        if ambiguous_owner:
            unsupported.append({"pattern": pattern.name, "reason": "transition_capture_owner_ambiguous"})
            continue
        if _is_history_conditional(pattern):
            capture_refs = [repr(effect.square_ref) for effect in effects if effect.piece_owner == "opponent"]
            resolved = set()
            for gid in pattern.geometry_ids:
                geometry = compiled.ir.geometry[gid]
                for owner in (0, 1):
                    for source in range(area):
                        for target, path in geometry_candidates(geometry, str(owner), source):
                            refs = _effect_rows(compiled, pattern, owner, source, target, path)
                            if refs:
                                resolved.update(square for square, _disposition, _ref in refs)
            history_rows.append({"pattern": pattern.name, "type_id": type_id,
                "effect_square_refs": capture_refs, "resolved_removed_square_indices": sorted(resolved),
                "classification": "history_or_auxiliary_state_excluded_no_stationary_prior"})
            if capture_refs and not resolved:
                unsupported.append({"pattern": pattern.name, "reason": "history_transition_removed_square_unresolvable"})
            continue
        for gid in pattern.geometry_ids:
            geometry = compiled.ir.geometry[gid]
            reasons = _intrinsic_unsupported(pattern, geometry)
            if reasons:
                unsupported.append({"pattern": pattern.name, "geometry": geometry.kind,
                                    "reason": "transition_pattern_outside_v2d_semantic_coverage", "details": reasons})
                continue
            for owner in (0, 1):
                for source in range(area):
                    guard = _source_guards_hold(compiled, pattern, type_id, owner, source)
                    if guard is None:
                        unsupported.append({"pattern": pattern.name, "reason": "transition_source_guard_unresolved"})
                        continue
                    if not guard:
                        continue
                    for target, path in geometry_candidates(geometry, str(owner), source):
                        targets = ((pattern.explicit_promotion_type,) if pattern.promotion_mode == "explicit"
                                   and pattern.explicit_promotion_type else
                                   _promotion_targets(compiled, type_id, owner, source, target))
                        if not targets:
                            if pattern.promotion_mode == "explicit":
                                unsupported.append({"pattern": pattern.name, "reason": "explicit_transition_destination_missing"})
                            continue
                        forced = pattern.promotion_mode == "explicit" or _promotion_forced(compiled, type_id, owner, target)
                        options = tuple(sorted(set(targets if forced else (type_id, *targets))))
                        path_kinds = {predicate.kind for predicate in pattern.path}
                        if path_kinds - SUPPORTED_PATH_PREDICATES:
                            unsupported.append({"pattern": pattern.name, "reason": "transition_path_predicate_unsupported"})
                            continue
                        opponent_removal_present = any(effect.piece_owner == "opponent" for effect in effects)
                        for state in sorted(SUPPORTED_TARGETS[pattern.target.kind]):
                            outcome = "capture" if state == "enemy" or opponent_removal_present else "quiet"
                            removed_effects = _effect_rows(compiled, pattern, owner, source, target, path)
                            if opponent_removal_present and removed_effects is None:
                                unsupported.append({"pattern": pattern.name,
                                    "reason": "transition_capture_removed_square_unresolvable"})
                                continue
                            if state == "enemy" and not opponent_removal_present:
                                unsupported.append({"pattern": pattern.name,
                                    "reason": "enemy_transition_without_explicit_opponent_removal"})
                                continue
                            relation = {"empty": "target_empty", "enemy": "target_enemy",
                                        "own": "target_friendly"}[state]
                            clear_path = geometry.kind == "ray" or "path_clear" in path_kinds
                            cube = _with_target(_make_cube(path, relation, clear_path=clear_path), target)
                            if outcome == "capture":
                                for square, _disposition, _ref in removed_effects:
                                    cube = _add_constraint(cube, square, {"enemy"})
                                    if cube is None:
                                        break
                            if cube is None:
                                continue
                            physical_effect_identity = canonical_removed_effect_identity(removed_effects or ())
                            physical_key = (owner, source, target, state, outcome, physical_effect_identity)
                            raw_refs = tuple(sorted(repr(effect.square_ref) for effect in effects
                                                     if effect.piece_owner == "opponent"))
                            _add_transition_event(groups, physical_key, cube, allowed_types=options,
                                pattern_name=pattern.name, forced=forced, promotion_mode=pattern.promotion_mode,
                                effect_square_refs=raw_refs)

    events = []
    for key, row in sorted(groups.items()):
        if len(row["option_sets"]) != 1 or len(row["forced_flags"]) != 1:
            unsupported.append({"physical_event_key": repr(key),
                "reason": "same_physical_event_has_incompatible_type_transition_choices"})
            continue
        options = next(iter(row["option_sets"]))
        probability = event_measure(key[0], type_id, list(sorted(set(row["cubes"]))))
        if probability <= 0:
            continue
        if not any(destination != type_id for destination in options):
            continue
        events.append({"event_key": key, "source_type": type_id, "owner": key[0], "source_square": key[1],
            "target_square": key[2], "target_relation": key[3], "outcome": key[4],
            "removed_effect_identity": key[5], "allowed_resulting_types": options,
            "optional_stay": type_id in options, "forced": type_id not in options,
            "probability": probability, "semantic_patterns": tuple(sorted(row["patterns"])),
            "raw_effect_square_refs_in_ledger": tuple(sorted(row["effect_square_refs"])),
            "occupancy_cube_count_after_union": len(set(row["cubes"]))})
    graph_edges = {(type_id, destination) for event in events
                   for destination in event["allowed_resulting_types"] if destination != type_id}
    return {"events": events, "history_exclusions": history_rows, "unsupported": unsupported,
            "graph_edges": graph_edges, "coverage_complete": not unsupported}


def solve_transition_values(base_values: dict[str, Fraction], events_by_type: dict[str, list[dict]], area: int) -> dict[str, Any]:
    graph = {type_id: set() for type_id in base_values}
    for source, events in events_by_type.items():
        for event in events:
            for destination in event["allowed_resulting_types"]:
                if destination != source:
                    graph.setdefault(source, set()).add(destination)
                    graph.setdefault(destination, set())
    unresolved = sorted(set(graph) - set(base_values))
    if unresolved:
        return {"acyclic": False, "cycle": [], "unresolved_destination_types": unresolved,
                "graph": graph, "reverse_topological_order": []}
    visiting: set[str] = set()
    visited: set[str] = set()
    reverse_topological: list[str] = []
    cycle: list[str] = []

    def visit(node: str, stack: tuple[str, ...]) -> None:
        nonlocal cycle
        if node in visited or cycle:
            return
        if node in visiting:
            cycle = list(stack[stack.index(node):] + (node,))
            return
        visiting.add(node)
        for child in sorted(graph.get(node, ())):
            visit(child, stack + (node,))
        visiting.remove(node)
        visited.add(node)
        reverse_topological.append(node)

    for node in sorted(graph):
        visit(node, ())
    if cycle:
        return {"acyclic": False, "cycle": cycle, "graph": graph, "reverse_topological_order": []}

    premiums = {type_id: Fraction(0) for type_id in graph}
    values = dict(base_values)
    evaluated_events: dict[str, list[dict[str, Any]]] = {}
    for source in reverse_topological:
        total = Fraction(0)
        rows = []
        for event in events_by_type.get(source, ()):
            available_values = {
                destination: (base_values[source] if destination == source else values[destination])
                for destination in event["allowed_resulting_types"]
            }
            after = max(available_values.values())
            delta = after - base_values[source]
            weighted = event["probability"] * delta
            total += weighted
            rows.append({**event, "destination_capabilities_b0_or_b1": available_values,
                         "selected_v_after": after, "signed_delta": delta,
                         "probability_times_delta": weighted})
        premiums[source] = total / (2 * area)
        values[source] = base_values[source] + premiums[source]
        evaluated_events[source] = rows
    return {"acyclic": True, "cycle": [], "graph": graph,
            "reverse_topological_order": reverse_topological,
            "transition_premiums": premiums, "transition_values_b1": values,
            "evaluated_events": evaluated_events}


def audit_benchmarks_v2e() -> dict[str, Any]:
    v2d_freeze, v2d = _load_frozen_v2d()
    compiled_sets = {"western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
                     "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset())}
    result: dict[str, Any] = {"schema_version": 1, "kind": "STATIC_MATERIAL_PRIOR_V2E_TYPE_TRANSITION_PRE_REFERENCE_CANDIDATE",
        "human_reference_imported": False, "human_metrics_computed": False,
        "base_v2d_reproduced": True, "transition_coefficient": 1,
        "transition_coefficient_reason": "T is already measured in frozen B0 capability units; add one unit of that same scale",
        "temporal_discount_used": False, "transport_term_used": False, "density_scan_used": False,
        "piece_specific_adjustment": False, "game_specific_adjustment": False,
        "v2d_baseline_freeze_sha256": _sha256(V2D_FREEZE),
        "v2d_baseline_candidate_sha256": v2d_freeze["sha256"][".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json"],
        "recurrence": "Reverse topological: B1(dest)=B0(dest)+T(dest); optional stay uses B0(source) stopping value; delta=max available continuation minus B0(source); forced lower transitions retain negative delta.",
        "rulesets": {}}
    for name, compiled in compiled_sets.items():
        baseline = v2d["rulesets"][name]
        type_rows = {}
        event_map = {}
        graph_edges = set()
        history = {}
        unsupported = {}
        for type_id, base_row in baseline["ledger"].items():
            b0 = Fraction(base_row["v2d_m_exact"])
            if b0 != Fraction(base_row["v2c_u_exact"]) + Fraction(base_row["capture_affordance_exact"]):
                raise RuntimeError(f"Frozen V2D B0 != U+C for {name}:{type_id}")
            measure = _event_measure_factory(baseline["token_state_ledger"], compiled, type_id)
            transitions = _transition_events(compiled, type_id, measure)
            event_map[type_id] = transitions["events"]
            graph_edges.update(transitions["graph_edges"])
            if transitions["history_exclusions"]:
                history[type_id] = transitions["history_exclusions"]
            if transitions["unsupported"]:
                unsupported[type_id] = transitions["unsupported"]
            type_rows[type_id] = {"v2c_u_exact": base_row["v2c_u_exact"], "v2c_u": base_row["v2c_u"],
                "v2d_c_exact": base_row["capture_affordance_exact"], "v2d_c": base_row["capture_affordance"],
                "b0_v2d_exact": f"{b0.numerator}/{b0.denominator}", "b0_v2d": float(b0),
                "type_transition_exists": bool(transitions["events"]),
                "transition_event_candidates": [_public_event(event) for event in transitions["events"]],
                "excluded_history_transition_rows": transitions["history_exclusions"],
                "unsupported_transition_semantics": transitions["unsupported"]}
        base_values = {type_id: Fraction(row["b0_v2d_exact"]) for type_id, row in type_rows.items()}
        solved = solve_transition_values(base_values, event_map, baseline["ruleset"]["board_square_count"])
        graph_complete = all(not rows for rows in unsupported.values())
        complete = baseline["coverage_complete"] and graph_complete and solved["acyclic"]
        for type_id, row in type_rows.items():
            if solved["acyclic"]:
                t = solved["transition_premiums"].get(type_id, Fraction(0))
                b1 = solved["transition_values_b1"].get(type_id, base_values[type_id])
                row.update({"transition_premium_t_exact": f"{t.numerator}/{t.denominator}", "transition_premium_t": float(t),
                    "b1_exact": f"{b1.numerator}/{b1.denominator}", "b1": float(b1),
                    "evaluated_transition_events": [_public_event(event)
                        for event in solved["evaluated_events"].get(type_id, [])]})
            else:
                row["transition_premium_t_exact"] = None
                row["b1_exact"] = None
        result["rulesets"][name] = {"coverage_complete": complete,
            "classification": "STATIC_MATERIAL_PRIOR_V2E_TYPE_TRANSITION_READY_FOR_HUMAN_VALIDATION" if complete else "STATIC_MATERIAL_PRIOR_V2E_TYPE_TRANSITION_INCONCLUSIVE",
            "transition_graph_edges": [list(edge) for edge in sorted(graph_edges)],
            "transition_graph_acyclic": solved["acyclic"],
            "cycle_evidence": solved["cycle"],
            "unresolved_destination_types": solved.get("unresolved_destination_types", []),
            "reverse_topological_order": solved["reverse_topological_order"],
            "history_excluded_transition_rows": history,
            "unsupported_transition_semantics": unsupported,
            "token_state_ledger": baseline["token_state_ledger"], "ledger": type_rows}
    result["coverage_complete"] = all(row["coverage_complete"] for row in result["rulesets"].values())
    result["classification"] = ("STATIC_MATERIAL_PRIOR_V2E_TYPE_TRANSITION_READY_FOR_HUMAN_VALIDATION"
        if result["coverage_complete"] else "STATIC_MATERIAL_PRIOR_V2E_TYPE_TRANSITION_INCONCLUSIVE")
    return result


def main() -> int:
    result = audit_benchmarks_v2e()
    output = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2e-type-transition.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "classification": result["classification"],
        "coverage_complete": result["coverage_complete"],
        "graph": {name: {"acyclic": row["transition_graph_acyclic"], "edges": row["transition_graph_edges"],
                         "order": row["reverse_topological_order"]} for name, row in result["rulesets"].items()}},
        indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
