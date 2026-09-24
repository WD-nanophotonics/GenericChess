"""Build frozen per-owner same-type movement-domain topology features."""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import geometry_candidates
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_static_semantic_material_prior_v2 import (
    _is_history_conditional,
    _promotion_forced,
    _promotion_targets,
)
from scripts.audit_static_semantic_material_prior_v2a import (
    SUPPORTED_PATH_PREDICATES,
    SUPPORTED_TARGETS,
    _intrinsic_unsupported,
    _make_cube,
    _source_guards_hold,
    _with_target,
)
from scripts.audit_static_semantic_material_prior_v2c import _source_joint_counts
from scripts.audit_static_semantic_material_prior_v2d import resolve_removed_square

V2C_FREEZE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-freeze.json"
V2C_RAW = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-board.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fraction(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _load_v2c() -> tuple[dict[str, Any], dict[str, Any]]:
    if not V2C_FREEZE.is_file() or not V2C_RAW.is_file():
        raise RuntimeError("Frozen V2C occupancy baseline is unavailable")
    freeze = json.loads(V2C_FREEZE.read_text(encoding="utf-8"))
    for relative, expected in freeze.get("sha256", {}).items():
        path = ROOT / relative
        if not path.is_file() or _sha(path) != expected:
            raise RuntimeError(f"Frozen V2C hash mismatch: {relative}")
    return freeze, json.loads(V2C_RAW.read_text(encoding="utf-8"))


def _add_label(cube: tuple, square: int, label: str) -> tuple | None:
    restrictions = dict(cube)
    if square in restrictions:
        allowed = set(restrictions[square]) & {label}
        if not allowed:
            return None
        restrictions[square] = tuple(sorted(allowed))
    else:
        restrictions[square] = (label,)
    return tuple(sorted(restrictions.items()))


def _resolve_effects(compiled: Any, pattern: Any, owner: int, source: int, target: int,
                     path: tuple[int, ...]) -> tuple[tuple[int, str], ...] | None:
    constraints = []
    for effect in pattern.effects:
        if effect.kind != "remove":
            continue
        if effect.piece_owner not in ("opponent", "self") or effect.square_ref is None:
            return None
        square = resolve_removed_square(effect.square_ref, owner=owner, source=source,
            target=target, path=path, area_width=compiled.support.board_size)
        if square is None or square == source:
            return None
        label = "enemy" if effect.piece_owner == "opponent" else "own"
        constraints.append((square, label))
    return tuple(sorted(set(constraints)))


def _components(area: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    adjacency = [set() for _ in range(area)]
    for left, right in edges:
        if left == right:
            continue
        adjacency[left].add(right)
        adjacency[right].add(left)
    seen = set()
    components = []
    for start in range(area):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        component = []
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in sorted(adjacency[node], reverse=True):
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=lambda row: (row[0], len(row)))


def component_statistics(area: int, edges: list[tuple[int, int]]) -> dict[str, Any]:
    components = _components(area, edges)
    sizes = [len(component) for component in components]
    d = sum((Fraction(size, area) ** 2 for size in sizes), Fraction(0))
    f = 1 - d
    largest = Fraction(max(sizes, default=0), area)
    return {"component_membership": components, "component_sizes": sizes,
        "component_count": len(components), "largest_component_fraction_exact": _fraction(largest),
        "same_domain_probability_d_exact": _fraction(d), "fragmentation_f_exact": _fraction(f),
        "same_domain_probability_d": float(d), "fragmentation_f": float(f)}


def _cube_feasible(cube: tuple, counts: tuple[int, int, int]) -> bool:
    """Whether finite-population label counts can satisfy one occupancy cube."""
    restrictions = [set(labels) for _square, labels in cube]
    if any(not labels for labels in restrictions):
        return False
    labels = ("empty", "own", "enemy")
    for mask in range(1 << len(labels)):
        subset = {labels[index] for index in range(len(labels)) if mask & (1 << index)}
        allowed_capacity = sum(counts[index] for index in range(len(labels))
                               if labels[index] in subset)
        forced_squares = sum(
            1 for allowed in restrictions
            if allowed <= subset
        )
        if forced_squares > allowed_capacity:
            return False
    return True


def _positive_cube_witness(cube: tuple, source_distribution: dict) -> tuple[int, int, int] | None:
    """Return a supported label-count witness iff this event has positive mass."""
    for counts, mass in sorted(source_distribution.items()):
        if mass > 0 and _cube_feasible(cube, counts):
            return counts
    return None


def _type_topology(compiled: Any, type_id: str, v2c_ledger: dict[str, Any]) -> dict[str, Any]:
    area = compiled.support.board_size ** 2
    source_is_anchor = bool(compiled.support.type_metadata[type_id].is_anchor)
    source_distributions = {
        owner: _source_joint_counts(v2c_ledger, owner, source_is_anchor=source_is_anchor)
        for owner in (0, 1)
    }
    witness_cache: dict[tuple[int, tuple], tuple[int, int, int] | None] = {}

    def witness(owner: int, cube: tuple) -> tuple[int, int, int] | None:
        key = (owner, cube)
        if key not in witness_cache:
            witness_cache[key] = _positive_cube_witness(cube, source_distributions[owner])
        return witness_cache[key]
    edge_groups: dict[tuple[int, int, int], dict[str, Any]] = {}
    transition_groups: dict[tuple, dict[str, Any]] = {}
    drop_ledger = []
    history_ledger = []
    dynamic_ledger = []
    unsupported = []

    for pattern in compiled.ir.patterns:
        if type_id not in pattern.type_ids:
            continue
        dynamic = sorted({invariant.kind for invariant in pattern.invariants
                          if invariant.kind in {"own_anchor_safe", "squares_not_attacked"}})
        for invariant in dynamic:
            dynamic_ledger.append({"pattern": pattern.name, "invariant": invariant,
                "classification": "global_positional_legality_excluded_from_intrinsic_domain_graph"})
        if _is_history_conditional(pattern):
            capture_refs = [repr(effect.square_ref) for effect in pattern.effects if effect.kind == "remove"]
            history_ledger.append({"pattern": pattern.name, "geometry_ids": list(pattern.geometry_ids),
                "effect_square_refs": capture_refs,
                "classification": "history_or_auxiliary_state_excluded_no_stationary_prior"})
            continue
        for gid in pattern.geometry_ids:
            geometry = compiled.ir.geometry[gid]
            if geometry.kind == "drop":
                drop_ledger.append({"pattern": pattern.name, "geometry": geometry.kind,
                    "classification": "held_drop_reentry_excluded_from_same_type_board_graph"})
                continue
            reasons = _intrinsic_unsupported(pattern, geometry)
            if reasons:
                unsupported.append({"pattern": pattern.name, "geometry": geometry.kind, "reasons": reasons})
                continue
            for owner in (0, 1):
                for source in range(area):
                    guard = _source_guards_hold(compiled, pattern, type_id, owner, source)
                    if guard is None:
                        unsupported.append({"pattern": pattern.name, "reason": "source_guard_unresolved",
                                            "owner": owner, "source": source})
                        continue
                    if not guard:
                        continue
                    for target, path in geometry_candidates(geometry, str(owner), source):
                        promoted = ()
                        if pattern.promotion_mode == "inherit_compiled_masks":
                            promoted = _promotion_targets(compiled, type_id, owner, source, target)
                        elif pattern.promotion_mode == "explicit":
                            if pattern.explicit_promotion_type is None:
                                unsupported.append({"pattern": pattern.name,
                                    "reason": "explicit_transition_destination_missing"})
                                continue
                            promoted = (pattern.explicit_promotion_type,)
                        elif pattern.promotion_mode != "none":
                            unsupported.append({"pattern": pattern.name,
                                "reason": "unknown_transition_mode", "mode": pattern.promotion_mode})
                            continue
                        forced = bool(promoted) and (
                            pattern.promotion_mode == "explicit" or _promotion_forced(compiled, type_id, owner, target))
                        path_kinds = {predicate.kind for predicate in pattern.path}
                        if path_kinds - SUPPORTED_PATH_PREDICATES:
                            unsupported.append({"pattern": pattern.name, "reason": "path_predicate_unsupported"})
                            continue
                        effect_constraints = _resolve_effects(compiled, pattern, owner, source, target, path)
                        has_removal = any(effect.kind == "remove" for effect in pattern.effects)
                        if effect_constraints is None and has_removal:
                            unsupported.append({"pattern": pattern.name,
                                "reason": "removed_square_or_owner_unresolved", "owner": owner,
                                "source": source, "target": target})
                            continue
                        for state in sorted(SUPPORTED_TARGETS[pattern.target.kind]):
                            if state == "enemy" and not any(
                                effect.kind == "remove" and effect.piece_owner == "opponent"
                                for effect in pattern.effects
                            ):
                                unsupported.append({"pattern": pattern.name,
                                    "reason": "enemy_target_without_explicit_opponent_removal"})
                                continue
                            relation = {"empty": "target_empty", "enemy": "target_enemy",
                                        "own": "target_friendly"}[state]
                            clear_path = geometry.kind == "ray" or "path_clear" in path_kinds
                            cube = _with_target(_make_cube(path, relation, clear_path=clear_path), target)
                            for square, label in effect_constraints or ():
                                cube = _add_label(cube, square, label)
                                if cube is None:
                                    break
                            if cube is None:
                                continue
                            transition_options = tuple(sorted(set(promoted)))
                            transition_key = (owner, source, target, state, transition_options, forced)
                            if transition_options:
                                row = transition_groups.setdefault(transition_key,
                                    {"cubes": [], "patterns": set(), "removed_effect_constraints": set()})
                                row["cubes"].append(cube)
                                row["patterns"].add(pattern.name)
                                row["removed_effect_constraints"].update(effect_constraints or ())
                            # A forced type change has no same-type successor branch.
                            if not forced:
                                key = (owner, source, target)
                                row = edge_groups.setdefault(key, {"cubes": [], "patterns": set(),
                                                                    "outcomes": set()})
                                row["cubes"].append(cube)
                                row["patterns"].add(pattern.name)
                                row["outcomes"].add(state)

    owner_graphs = {}
    for owner in (0, 1):
        rows = []
        for (edge_owner, source, target), group in sorted(edge_groups.items()):
            if edge_owner != owner:
                continue
            cubes = sorted(set(group["cubes"]))
            witnesses = [witness(owner, cube) for cube in cubes]
            witnesses = [row for row in witnesses if row is not None]
            if witnesses:
                rows.append({"source": source, "target": target,
                    "event_probability_positive": True,
                    "witness_empty_own_enemy_counts": list(witnesses[0]),
                    "semantic_patterns": sorted(group["patterns"]),
                    "target_outcomes": sorted(group["outcomes"]),
                    "occupancy_cube_count_after_union": len(cubes)})
        edges = sorted({(row["source"], row["target"]) for row in rows})
        edge_payload = json.dumps(edges, separators=(",", ":")).encode("utf-8")
        stats = component_statistics(area, edges)
        owner_graphs[str(owner)] = {"directed_edge_rows": rows,
            "directed_edges": [list(edge) for edge in edges],
            "directed_edge_sha256": hashlib.sha256(edge_payload).hexdigest(), **stats}

    transition_rows = []
    outgoing = set()
    for key, group in sorted(transition_groups.items()):
        owner, source, target, state, destinations, forced = key
        cubes = sorted(set(group["cubes"]))
        witnesses = [witness(owner, cube) for cube in cubes]
        witnesses = [row for row in witnesses if row is not None]
        if not witnesses:
            continue
        outgoing.update(destinations)
        transition_rows.append({"owner": owner, "source_square": source, "target_square": target,
            "target_outcome": state, "destination_types": list(destinations),
            "forced": forced, "optional": not forced,
            "event_probability_positive": True,
            "witness_empty_own_enemy_counts": list(witnesses[0]),
            "semantic_patterns": sorted(group["patterns"]),
            "removed_effect_constraints": [list(row) for row in sorted(group["removed_effect_constraints"])]})
    d_mean = sum((Fraction(owner_graphs[str(o)]["same_domain_probability_d_exact"]) for o in (0, 1)), Fraction(0)) / 2
    f_mean = sum((Fraction(owner_graphs[str(o)]["fragmentation_f_exact"]) for o in (0, 1)), Fraction(0)) / 2
    component_count_mean = Fraction(sum(owner_graphs[str(o)]["component_count"] for o in (0, 1)), 2)
    largest_mean = sum((Fraction(owner_graphs[str(o)]["largest_component_fraction_exact"]) for o in (0, 1)), Fraction(0)) / 2
    return {"owner_graphs": owner_graphs,
        "owner_averaged": {"component_count_mean_exact": _fraction(component_count_mean),
            "largest_component_fraction_mean_exact": _fraction(largest_mean),
            "same_domain_probability_d_mean_exact": _fraction(d_mean),
            "fragmentation_f_mean_exact": _fraction(f_mean),
            "same_domain_probability_d_mean": float(d_mean), "fragmentation_f_mean": float(f_mean)},
        "outgoing_type_transition_types": sorted(outgoing),
        "has_outgoing_type_transition": bool(outgoing),
        "type_transition_event_ledger": transition_rows,
        "excluded_drop_ledger": drop_ledger, "excluded_history_ledger": history_ledger,
        "excluded_dynamic_legality_ledger": dynamic_ledger,
        "unsupported_semantics": unsupported, "coverage_complete": not unsupported}


def audit_topology() -> dict[str, Any]:
    v2c_freeze, v2c = _load_v2c()
    compiled_sets = {"western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
        "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset())}
    output = {"schema_version": 1, "kind": "STATIC_MATERIAL_DOMAIN_FRAGMENTATION_PRE_REFERENCE_CANDIDATE",
        "human_reference_imported": False, "v2d_residuals_imported": False,
        "material_formula_modified": False, "v2e_transition_value_used": False,
        "transport_efficiency_used": False, "piece_specific_logic": False, "game_specific_logic": False,
        "v2c_freeze_sha256": _sha(V2C_FREEZE),
        "v2c_candidate_sha256": v2c_freeze["sha256"][".generic_chess_flow/static-semantic-material-prior-v2c-board.json"],
        "rulesets": {}}
    for name, compiled in compiled_sets.items():
        result = {"board_area": compiled.support.board_size ** 2,
            "board_size": compiled.support.board_size, "coverage_complete": True, "pieces": {}}
        for type_id in sorted(v2c["rulesets"][name]["ledger"]):
            topology = _type_topology(compiled, type_id, v2c["rulesets"][name]["token_state_ledger"])
            result["coverage_complete"] &= topology["coverage_complete"]
            result["pieces"][type_id] = topology
        output["rulesets"][name] = result
    output["coverage_complete"] = all(row["coverage_complete"] for row in output["rulesets"].values())
    output["classification"] = ("STATIC_MATERIAL_DOMAIN_FRAGMENTATION_READY_FOR_V2D_DEVELOPMENT_COMPARISON"
        if output["coverage_complete"] else "STATIC_MATERIAL_DOMAIN_FRAGMENTATION_HYPOTHESIS_INCONCLUSIVE")
    return output


def main() -> int:
    output = audit_topology()
    path = ROOT / ".generic_chess_flow/static-material-domain-fragmentation-topology.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(path), "classification": output["classification"],
        "coverage_complete": output["coverage_complete"],
        "types": {name: len(row["pieces"]) for name, row in output["rulesets"].items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
