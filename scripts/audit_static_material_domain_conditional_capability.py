"""Exact source/domain decomposition of frozen V2D capability; no score change."""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
import hashlib
import json
import math
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
    _effect_key,
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
from scripts.audit_static_semantic_material_prior_v2c import (
    _event_measure_factory,
)

V2C_FREEZE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-freeze.json"
V2C_RAW = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-board.json"
V2D_FREEZE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-freeze.json"
V2D_RAW = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json"
TOPOLOGY_FREEZE = ROOT / ".generic_chess_flow/static-material-domain-fragmentation-freeze.json"
TOPOLOGY_RAW = ROOT / ".generic_chess_flow/static-material-domain-fragmentation-topology.json"
OUTPUT = ROOT / ".generic_chess_flow/static-material-domain-conditional-capability.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fraction(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _parse_fraction(value: str) -> Fraction:
    numerator, denominator = value.split("/", 1)
    return Fraction(int(numerator), int(denominator))


def _read_frozen(path: Path, *, human_free: bool = True) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if human_free and (value.get("human_metrics_computed") is not False
                       or value.get("reference_data_read") not in (None, False)):
        raise RuntimeError(f"Not an eligible pre-reference freeze: {path.name}")
    for relative, expected in value.get("sha256", {}).items():
        source = ROOT / relative
        if not source.is_file() or _sha(source) != expected:
            raise RuntimeError(f"Frozen input hash mismatch in {path.name}: {relative}")
    return value


def _source_u_by_square(compiled: Any, type_id: str, token_ledger: dict[str, Any]) -> dict[str, Any]:
    """Reproduce V2A/V2C successor-option grouping, retaining the source key."""
    area = compiled.support.board_size ** 2
    measure = _event_measure_factory(token_ledger, compiled, type_id)
    groups: dict[tuple, list[tuple]] = defaultdict(list)
    geometries: dict[str, list[int]] = {"0": [0] * area, "1": [0] * area}
    excluded_by_guard: dict[str, list[int]] = {"0": [0] * area, "1": [0] * area}
    history_ledger = []
    drop_ledger = []
    unsupported = []

    for pattern in compiled.ir.patterns:
        if type_id not in pattern.type_ids:
            continue
        if _is_history_conditional(pattern):
            history_ledger.append({"pattern": pattern.name,
                                   "classification": "history_or_auxiliary_state_excluded_from_stationary_source_capability"})
            continue
        for gid in pattern.geometry_ids:
            geometry = compiled.ir.geometry[gid]
            if geometry.kind == "drop":
                drop_ledger.append({"pattern": pattern.name,
                                    "classification": "held_drop_reentry_excluded_from_board_capability"})
                continue
            reasons = _intrinsic_unsupported(pattern, geometry)
            if reasons:
                unsupported.append({"pattern": pattern.name, "geometry": geometry.kind, "reasons": reasons})
                continue
            if {predicate.kind for predicate in pattern.path} - SUPPORTED_PATH_PREDICATES:
                unsupported.append({"pattern": pattern.name, "reason": "unsupported_path_predicate"})
                continue
            for owner in (0, 1):
                for source in range(area):
                    guard = _source_guards_hold(compiled, pattern, type_id, owner, source)
                    if guard is None:
                        unsupported.append({"pattern": pattern.name, "reason": "source_guard_unresolved",
                                            "owner": owner, "source": source})
                        continue
                    for target, path in geometry_candidates(geometry, str(owner), source):
                        geometries[str(owner)][source] += 1
                        if not guard:
                            excluded_by_guard[str(owner)][source] += 1
                            continue
                        path_kinds = {predicate.kind for predicate in pattern.path}
                        clear_path = geometry.kind == "ray" or "path_clear" in path_kinds
                        for state in sorted(SUPPORTED_TARGETS[pattern.target.kind]):
                            relation = {"empty": "target_empty", "enemy": "target_enemy",
                                        "own": "target_friendly"}[state]
                            cube = _with_target(_make_cube(path, relation, clear_path=clear_path), target)
                            promoted = (_promotion_targets(compiled, type_id, owner, source, target)
                                        if pattern.promotion_mode != "none" else ())
                            forced = bool(promoted) and _promotion_forced(compiled, type_id, owner, target)
                            final_types = (() if forced else (type_id,)) + tuple(promoted)
                            for final_type in final_types:
                                key = (owner, source, target, state, _effect_key(pattern), final_type)
                                groups[key].append(cube)

    source_values = {str(owner): [Fraction(0) for _ in range(area)] for owner in (0, 1)}
    for key, cubes in sorted(groups.items()):
        owner, source, _target, _state, _effect, _final_type = key
        probability = measure(owner, type_id, sorted(set(cubes)))
        source_values[str(owner)][source] += probability
    return {"u_by_owner_source": source_values,
            "geometric_candidate_count_by_owner_source": geometries,
            "source_guard_excluded_candidate_count_by_owner_source": excluded_by_guard,
            "excluded_history_ledger": history_ledger,
            "excluded_drop_ledger": drop_ledger,
            "unsupported_semantics": unsupported,
            "coverage_complete": not unsupported,
            "successor_group_count": len(groups)}


def _source_c_by_square(v2d_type: dict[str, Any], area: int) -> dict[str, Any]:
    source_values = {str(owner): [Fraction(0) for _ in range(area)] for owner in (0, 1)}
    identities: set[tuple[int, int, int]] = set()
    unsupported = []
    for row in v2d_type["capture_affordance_event_ledger"]:
        owner, source, removed = row["owner"], row["source_square"], row["removed_square"]
        identity = (owner, source, removed)
        if row.get("unique_affordance_key") != list(identity) or identity in identities:
            unsupported.append({"reason": "V2D physical capture identity missing_or_duplicated", "key": list(identity)})
            continue
        identities.add(identity)
        probability = _parse_fraction(row["event_probability_exact"])
        if probability <= 0:
            unsupported.append({"reason": "nonpositive_event_in_frozen_V2D_capture_ledger", "key": list(identity)})
            continue
        source_values[str(owner)][source] += probability
    exact_total = sum((sum(values, Fraction(0)) for values in source_values.values()), Fraction(0))
    return {"c_by_owner_source": source_values,
            "capture_identity_count": len(identities),
            "unsupported_capture_ledger": unsupported,
            "capture_affordance_reconstructed_exact": _fraction(exact_total / (2 * area)),
            "coverage_complete": not unsupported}


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2
        for offset in range(i, j):
            ranks[order[offset]] = rank
        i = j
    return ranks


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3 or len(left) != len(right):
        return None
    lm, rm = sum(left) / len(left), sum(right) / len(right)
    cov = sum((a - lm) * (b - rm) for a, b in zip(left, right))
    lv = sum((a - lm) ** 2 for a in left)
    rv = sum((b - rm) ** 2 for b in right)
    if not lv or not rv:
        return None
    return cov / math.sqrt(lv * rv)


def _domain_table(area: int, u: list[Fraction], c: list[Fraction], components: list[list[int]],
                  *, joint_applicable: bool = True) -> dict[str, Any]:
    if sorted(square for component in components for square in component) != list(range(area)):
        raise ValueError("domain components do not partition board squares")
    domains = []
    weights: list[Fraction] = []
    capabilities: list[Fraction] = []
    for index, squares in enumerate(components):
        size = len(squares)
        if not size:
            raise ValueError("empty movement domain")
        us = sum((u[square] for square in squares), Fraction(0)) / size
        cs = sum((c[square] for square in squares), Fraction(0)) / size
        bs = us + cs
        weight = Fraction(size, area)
        domains.append({"domain_index": index, "squares": squares, "size": size,
                        "w_exact": _fraction(weight), "u_bar_exact": _fraction(us),
                        "c_bar_exact": _fraction(cs), "b_bar_exact": _fraction(bs)})
        weights.append(weight)
        capabilities.append(bs)
    owner_u = sum((weight * _parse_fraction(row["u_bar_exact"])
                   for weight, row in zip(weights, domains)), Fraction(0))
    owner_c = sum((weight * _parse_fraction(row["c_bar_exact"])
                   for weight, row in zip(weights, domains)), Fraction(0))
    owner_b = owner_u + owner_c
    d = sum((weight ** 2 for weight in weights), Fraction(0))
    if joint_applicable:
        j = sum((weight ** 2 * capability for weight, capability in zip(weights, capabilities)), Fraction(0))
        fct = owner_b * d
    mean = sum(capabilities, Fraction(0)) / len(capabilities)
    variance = sum(((value - mean) ** 2 for value in capabilities), Fraction(0)) / len(capabilities)
    nonzero_capabilities = [value for value in capabilities if value]
    cv = math.sqrt(float(variance)) / float(mean) if mean else None
    equality_groups: dict[str, list[int]] = defaultdict(list)
    for row in domains:
        equality_groups[row["b_bar_exact"]].append(row["domain_index"])
    corr_defined = len(domains) >= 3 and len(set(weights)) > 1 and len(set(capabilities)) > 1
    result = {"domains": domains,
            "domain_size_weighted_u_bar_exact": _fraction(owner_u),
            "domain_size_weighted_c_bar_exact": _fraction(owner_c),
            "domain_size_weighted_b_bar_exact": _fraction(owner_b),
            "d_exact": _fraction(d),
            "b_bar_min_exact": _fraction(min(capabilities)),
            "b_bar_max_exact": _fraction(max(capabilities)),
            "b_bar_unweighted_domain_mean_exact": _fraction(mean),
            "b_bar_population_variance_exact": _fraction(variance),
            "b_bar_coefficient_of_variation": cv,
            "pearson_w_vs_b_bar": _correlation([float(x) for x in weights], [float(x) for x in capabilities]) if corr_defined else None,
            "spearman_w_vs_b_bar": _correlation(_ranks([float(x) for x in weights]), _ranks([float(x) for x in capabilities])) if corr_defined else None,
            "correlation_undefined_reason": None if corr_defined else "fewer_than_three_domains_or_constant_domain_size_or_capability",
            "exact_b_bar_equality_groups": dict(sorted(equality_groups.items())),
            "nonzero_domain_count": len(nonzero_capabilities)}
    if joint_applicable:
        result.update({"j_exact": _fraction(j), "fct_exact": _fraction(fct),
                      "factorization_error_exact": _fraction(fct - j),
                      "relative_factorization_error_exact": _fraction((fct - j) / j) if j else None,
                      "r_joint_exact": _fraction(j / owner_b) if owner_b else None})
    return result


def audit_conditional_capability() -> dict[str, Any]:
    v2c_freeze = _read_frozen(V2C_FREEZE)
    v2d_freeze = _read_frozen(V2D_FREEZE)
    topology_freeze = json.loads(TOPOLOGY_FREEZE.read_text(encoding="utf-8"))
    if topology_freeze.get("human_reference_read") is not False or topology_freeze.get("v2d_validation_residuals_read") is not False:
        raise RuntimeError("ADR-128 topology was not frozen before reference access")
    for relative, expected in topology_freeze["sha256"].items():
        source = ROOT / relative
        if not source.is_file() or _sha(source) != expected:
            raise RuntimeError(f"Frozen topology input hash mismatch: {relative}")
    if _sha(TOPOLOGY_RAW) != topology_freeze["topology_candidate_sha256"]:
        raise RuntimeError("ADR-128 topology raw candidate hash mismatch")
    v2c = json.loads(V2C_RAW.read_text(encoding="utf-8"))
    v2d = json.loads(V2D_RAW.read_text(encoding="utf-8"))
    topology = json.loads(TOPOLOGY_RAW.read_text(encoding="utf-8"))
    if (v2c.get("human_reference_imported") is not False
            or v2c.get("human_metrics_computed") is not False
            or v2d.get("human_reference_imported") is not False
            or v2d.get("human_metrics_computed") is not False
            or not topology.get("coverage_complete")):
        raise RuntimeError("One or more frozen rule-only baselines are ineligible")

    compiled_sets = {"western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
                     "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset())}
    output = {"schema_version": 1,
              "kind": "STATIC_MATERIAL_DOMAIN_CONDITIONAL_CAPABILITY_PRE_REFERENCE_CANDIDATE",
              "human_reference_imported": False,
              "v2d_residuals_imported": False,
              "material_formula_modified": False,
              "score_validation_performed": False,
              "v2e_transition_value_used": False,
              "transport_efficiency_used": False,
              "transition_bearing_domain_payoff_assigned": False,
              "piece_specific_logic": False,
              "game_specific_logic": False,
              "v2c_freeze_sha256": _sha(V2C_FREEZE),
              "v2c_candidate_sha256": _sha(V2C_RAW),
              "v2d_freeze_sha256": _sha(V2D_FREEZE),
              "v2d_candidate_sha256": _sha(V2D_RAW),
              "topology_freeze_sha256": _sha(TOPOLOGY_FREEZE),
              "topology_candidate_sha256": _sha(TOPOLOGY_RAW),
              "coverage_complete": True,
              "reconstruction_complete": True,
              "rulesets": {}}

    for name, compiled in compiled_sets.items():
        area = compiled.support.board_size ** 2
        c_types = v2c["rulesets"][name]["ledger"]
        d_types = v2d["rulesets"][name]["ledger"]
        topo_types = topology["rulesets"][name]["pieces"]
        if set(c_types) != set(d_types) or set(d_types) != set(topo_types):
            output["coverage_complete"] = False
            output["reconstruction_complete"] = False
            output.setdefault("failures", []).append({"ruleset": name, "reason": "type_ledger_set_mismatch"})
            continue
        ledger = v2c["rulesets"][name]["token_state_ledger"]
        if not ledger.get("complete"):
            output["coverage_complete"] = False
            output["reconstruction_complete"] = False
            output.setdefault("failures", []).append({"ruleset": name, "reason": "frozen_v2c_token_ledger_incomplete"})
        type_rows = {}
        for type_id in sorted(d_types):
            v2c_row = c_types[type_id]
            v2d_row = d_types[type_id]
            topo_row = topo_types[type_id]
            u_result = _source_u_by_square(compiled, type_id, ledger)
            c_result = _source_c_by_square(v2d_row, area)
            source_u = u_result["u_by_owner_source"]
            source_c = c_result["c_by_owner_source"]
            source_b = {owner: [source_u[owner][square] + source_c[owner][square]
                                for square in range(area)] for owner in ("0", "1")}
            terminal = not topo_row["has_outgoing_type_transition"]
            u_global = sum((sum(values, Fraction(0)) for values in source_u.values()), Fraction(0)) / (2 * area)
            c_global = sum((sum(values, Fraction(0)) for values in source_c.values()), Fraction(0)) / (2 * area)
            b_global = u_global + c_global
            expected_u = _parse_fraction(v2d_row["v2c_u_exact"])
            expected_c = _parse_fraction(v2d_row["capture_affordance_exact"])
            expected_b = _parse_fraction(v2d_row["v2d_m_exact"])
            v2c_u = _parse_fraction(v2c_row["v2c_exact"])
            u_ok = u_global == expected_u == v2c_u
            c_ok = c_global == expected_c
            b_ok = b_global == expected_b == expected_u + expected_c
            if not (u_ok and c_ok and b_ok and u_result["coverage_complete"]
                    and c_result["coverage_complete"] and topo_row["coverage_complete"]):
                output["reconstruction_complete"] = False
                output["coverage_complete"] = False
                output.setdefault("failures", []).append({"ruleset": name, "type": type_id,
                    "u_reconstructed": _fraction(u_global), "u_frozen_v2d": _fraction(expected_u),
                    "c_reconstructed": _fraction(c_global), "c_frozen_v2d": _fraction(expected_c),
                    "b_reconstructed": _fraction(b_global), "b_frozen_v2d": _fraction(expected_b),
                    "u_semantic_coverage": u_result["coverage_complete"],
                    "c_semantic_coverage": c_result["coverage_complete"],
                    "topology_coverage": topo_row["coverage_complete"],
                    "u_unsupported": u_result["unsupported_semantics"],
                    "c_unsupported": c_result["unsupported_capture_ledger"]})

            owner_rows = {}
            for owner in ("0", "1"):
                graph = topo_row["owner_graphs"][owner]
                components = graph["component_membership"]
                component_for_square = {}
                for index, squares in enumerate(components):
                    for square in squares:
                        if square in component_for_square:
                            output["coverage_complete"] = False
                        component_for_square[square] = index
                if set(component_for_square) != set(range(area)):
                    output["coverage_complete"] = False
                    output["reconstruction_complete"] = False
                local_u = source_u[owner]
                local_c = source_c[owner]
                local_b = source_b[owner]
                owner_u = sum(local_u, Fraction(0)) / area
                owner_c = sum(local_c, Fraction(0)) / area
                owner_b = owner_u + owner_c
                if terminal:
                    owner_domains = _domain_table(area, local_u, local_c, components)
                    domain_reconstruction_ok = (
                        _parse_fraction(owner_domains["domain_size_weighted_u_bar_exact"]) == owner_u
                        and _parse_fraction(owner_domains["domain_size_weighted_c_bar_exact"]) == owner_c
                        and _parse_fraction(owner_domains["domain_size_weighted_b_bar_exact"]) == owner_b
                    )
                else:
                    owner_domains = {"domains": [{"domain_index": index, "squares": squares,
                        "size": len(squares), "w_exact": _fraction(Fraction(len(squares), area))}
                        for index, squares in enumerate(components)],
                        "same_type_d_exact": graph["same_domain_probability_d_exact"],
                        "joint_measure_status": "NOT_APPLICABLE_TRANSITION_BEARING_TYPE"}
                    domain_reconstruction_ok = True
                if not domain_reconstruction_ok:
                    output["reconstruction_complete"] = False
                    output.setdefault("failures", []).append({"ruleset": name, "type": type_id,
                        "owner": int(owner), "reason": "domain_weighted_source_mean_mismatch"})
                owner_rows[owner] = {
                    "u_owner_average_exact": _fraction(owner_u),
                    "c_owner_average_exact": _fraction(owner_c),
                    "b0_owner_average_exact": _fraction(owner_b),
                    "source_rows": [{
                        "source_square": square,
                        "u_exact": _fraction(local_u[square]),
                        "c_exact": _fraction(local_c[square]),
                        "b_exact": _fraction(local_b[square]),
                        "domain_index": component_for_square.get(square),
                        "geometric_candidate_count": u_result["geometric_candidate_count_by_owner_source"][owner][square],
                        "source_guard_excluded_candidate_count": u_result["source_guard_excluded_candidate_count_by_owner_source"][owner][square],
                    } for square in range(area)],
                    "source_guard_excluded_square_count": sum(
                        1 for count in u_result["source_guard_excluded_candidate_count_by_owner_source"][owner]
                        if count > 0),
                    "component_sizes": [len(row) for row in components],
                    "component_count": len(components),
                    "d_exact": graph["same_domain_probability_d_exact"],
                    "domain_conditioned": owner_domains,
                }

            owner_b0 = [_parse_fraction(owner_rows[o]["b0_owner_average_exact"]) for o in ("0", "1")]
            owner_u_avg = [_parse_fraction(owner_rows[o]["u_owner_average_exact"]) for o in ("0", "1")]
            owner_c_avg = [_parse_fraction(owner_rows[o]["c_owner_average_exact"]) for o in ("0", "1")]
            row = {
                "terminal_current_type": terminal,
                "outgoing_type_transition_types": topo_row["outgoing_type_transition_types"],
                "type_transition_event_ledger": topo_row["type_transition_event_ledger"],
                "u_exact": _fraction(u_global), "u_frozen_v2d_exact": _fraction(expected_u),
                "c_exact": _fraction(c_global), "c_frozen_v2d_exact": _fraction(expected_c),
                "b0_exact": _fraction(b_global), "b0_frozen_v2d_exact": _fraction(expected_b),
                "u_reconstruction_exact": u_ok, "c_reconstruction_exact": c_ok,
                "b0_reconstruction_exact": b_ok,
                "owner_averaged_u_exact": _fraction(sum(owner_u_avg, Fraction(0)) / 2),
                "owner_averaged_c_exact": _fraction(sum(owner_c_avg, Fraction(0)) / 2),
                "owner_averaged_b0_exact": _fraction(sum(owner_b0, Fraction(0)) / 2),
                "owner_graphs": owner_rows,
                "excluded_semantics": {
                    "history_auxiliary": u_result["excluded_history_ledger"],
                    "held_drop_reentry": u_result["excluded_drop_ledger"],
                    "dynamic_positional_legality": topo_row["excluded_dynamic_legality_ledger"],
                    "history_capture": v2d_row["excluded_history_conditioned_capture_rows"],
                    "nonopponent_removals": v2d_row["excluded_nonopponent_removals"],
                },
                "semantic_coverage": {"u": u_result["coverage_complete"],
                                      "c": c_result["coverage_complete"],
                                      "topology": topo_row["coverage_complete"]},
                "unsupported_semantics": u_result["unsupported_semantics"],
                "unsupported_capture_ledger": c_result["unsupported_capture_ledger"],
                "u_successor_group_count": u_result["successor_group_count"],
                "c_physical_capture_identity_count": c_result["capture_identity_count"],
            }
            if terminal:
                j = sum((_parse_fraction(owner_rows[o]["domain_conditioned"]["j_exact"])
                         for o in ("0", "1")), Fraction(0)) / 2
                fct = sum((_parse_fraction(owner_rows[o]["domain_conditioned"]["fct_exact"])
                           for o in ("0", "1")), Fraction(0)) / 2
                d_owner = [_parse_fraction(owner_rows[o]["d_exact"]) for o in ("0", "1")]
                d_mean = sum(d_owner, Fraction(0)) / 2
                row.update({"joint_measure_status": "APPLICABLE_TERMINAL_TYPE_SAME_WEAK_DOMAIN_RANDOM_TARGET_DIAGNOSTIC_ONLY",
                    "j_exact": _fraction(j), "fct_owner_consistent_exact": _fraction(fct),
                    "factorization_error_exact": _fraction(fct - j),
                    "relative_factorization_error_exact": _fraction((fct - j) / j) if j else None,
                    "r_joint_exact": _fraction(j / b_global) if b_global else None,
                    "owner_averaged_d_exact": _fraction(d_mean),
                    "owner_averaged_b0_times_d_separately_exact": _fraction(b_global * d_mean),
                    "owner_consistent_fct_minus_owner_average_b0_times_d_exact": _fraction(fct - b_global * d_mean)})
            else:
                row.update({"joint_measure_status": "NOT_APPLICABLE_TRANSITION_BEARING_TYPE",
                            "j_exact": None, "fct_owner_consistent_exact": None,
                            "factorization_error_exact": None,
                            "relative_factorization_error_exact": None,
                            "r_joint_exact": None})
            type_rows[type_id] = row

        terminal_rows = [row for row in type_rows.values() if row["terminal_current_type"]]
        terminal_errors = [_parse_fraction(row["factorization_error_exact"]) for row in terminal_rows]
        ruleset_reconstruction = all(row["u_reconstruction_exact"] and row["c_reconstruction_exact"]
                                     and row["b0_reconstruction_exact"] for row in type_rows.values())
        output["reconstruction_complete"] &= ruleset_reconstruction
        output["coverage_complete"] &= all(
            all(value is True for value in row["semantic_coverage"].values())
            for row in type_rows.values())
        output["rulesets"][name] = {
            "board_area": area,
            "coverage_complete": all(all(value is True for value in row["semantic_coverage"].values())
                                      for row in type_rows.values()),
            "reconstruction_complete": ruleset_reconstruction,
            "terminal_type_count": len(terminal_rows),
            "factorability_exact": all(error == 0 for error in terminal_errors),
            "types": type_rows,
        }

    if not output["coverage_complete"] or not output["reconstruction_complete"]:
        output["classification"] = "STATIC_MATERIAL_DOMAIN_CONDITIONAL_CAPABILITY_INCONCLUSIVE"
    elif any(not row["factorability_exact"] for row in output["rulesets"].values()):
        output["classification"] = "STATIC_MATERIAL_DOMAIN_CONDITIONAL_CAPABILITY_NONFACTORABLE"
    else:
        output["classification"] = "STATIC_MATERIAL_DOMAIN_CONDITIONAL_CAPABILITY_FACTORABLE"
    output["factorization_scope"] = (
        "same_weak_domain_random_target_diagnostic_only_not_directed_reachability_or_game_deployment"
    )
    output["input_sha256"] = {
        "v2c_freeze": _sha(V2C_FREEZE), "v2c_candidate": _sha(V2C_RAW),
        "v2d_freeze": _sha(V2D_FREEZE), "v2d_candidate": _sha(V2D_RAW),
        "topology_freeze": _sha(TOPOLOGY_FREEZE), "topology_candidate": _sha(TOPOLOGY_RAW),
    }
    return output


def main() -> int:
    result = audit_conditional_capability()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "classification": result["classification"],
        "coverage_complete": result["coverage_complete"],
        "reconstruction_complete": result["reconstruction_complete"],
        "terminal_types": {name: row["terminal_type_count"] for name, row in result["rulesets"].items()},
        "nonzero_factorization_errors": {name: sum(
            1 for item in row["types"].values() if item["terminal_current_type"]
            and item["factorization_error_exact"] != "0/1") for name, row in result["rulesets"].items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
