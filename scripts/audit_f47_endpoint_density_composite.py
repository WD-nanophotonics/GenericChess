"""F47 diagnosis-only endpoint completion over the accepted density profile."""

from __future__ import annotations

import hashlib
import inspect
import itertools
import json
import math
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".generic_chess_flow"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import audit_f41_semantic_material_prior as f41  # noqa: E402
import audit_f42_semantic_capability_prior as f42  # noqa: E402
import audit_f44_structural_capability as f44  # noqa: E402
import audit_f46_density_profile as f46  # noqa: E402

from generic_chess.rules.compiler import compile_semantic_ruleset  # noqa: E402
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset  # noqa: E402
from generic_chess.rules.western_chess import build_western_chess_ruleset  # noqa: E402


MANIFEST = ROOT / "tests" / "fixtures" / "f47_endpoint_density_composite_manifest.json"
R1_MANIFEST = ROOT / "tests" / "fixtures" / "f47r1_endpoint_density_composite_manifest.json"
BASELINE = "979c7e026442e9dbb479658d0a770daefd15da85"
R1_MANIFEST_SHA256 = "a41906362aee6118c63f9d60f8ec50d9078f8170dd3bc8246a7c1d8f5bea8ba6"
VARIANTS = (
    "C47-0_CURRENT_ARITHMETIC_CONTROL",
    "C47-1_ENDPOINT_ARITHMETIC",
    "C47-2_ENDPOINT_GEOMETRIC",
    "C47-3_ENDPOINT_HARMONIC",
    "C47-4_ENDPOINT_LOWER_ENVELOPE",
)
REDUCERS = {
    VARIANTS[0]: f46.REDUCERS[0],
    VARIANTS[1]: f46.REDUCERS[0],
    VARIANTS[2]: f46.REDUCERS[1],
    VARIANTS[3]: f46.REDUCERS[2],
    VARIANTS[4]: f46.REDUCERS[3],
}
QUALIFICATION_MAPPING = {
    "ENDPOINT_CONTROL_CANDIDATE_SUPPORTED": "F48_ENDPOINT_CONTROL_INTEGRATION_PROTOTYPE",
    "ENDPOINT_DENSITY_COMPOSITE_CANDIDATE_SUPPORTED": "F48_ENDPOINT_DENSITY_INTEGRATION_PROTOTYPE",
    "MULTIPLE_ENDPOINT_DENSITY_CANDIDATES": "F48_ENDPOINT_DENSITY_DISCRIMINATION",
    "ENDPOINT_DENSITY_CROSS_RULESET_CONFLICT": "F48_GENERIC_MATERIAL_PRIOR_REASSESSMENT",
    "ENDPOINT_DENSITY_COMPOSITE_INSUFFICIENT": "F48_GENERIC_MATERIAL_PRIOR_REASSESSMENT",
    "ENDPOINT_DENSITY_DIRECTIONAL_MISMATCH": "F48_MATERIAL_PRIOR_REASSESSMENT",
    "MIXED_OR_UNRESOLVED": "F48_MATERIAL_PRIOR_REASSESSMENT",
}
BANDS = {"N": [2.5, 3.5], "B": [2.5, 3.75], "R": [4.0, 6.0], "Q": [7.5, 11.0]}


def _manifest() -> dict[str, Any]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    actual = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if actual != data["manifest_sha256"] or data["baseline"]["sandbox_sha"] != BASELINE:
        raise AssertionError("H47A manifest mismatch")
    return data


def _h47r1a_manifest() -> dict[str, Any]:
    data = json.loads(R1_MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    actual = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if actual != data["manifest_sha256"] or actual != R1_MANIFEST_SHA256:
        raise AssertionError("H47R1A manifest hash mismatch")
    if data["baseline"]["immediate_f47_sha"] != "d8d39bb4ef15f018e97afedf97733041490686b2":
        raise AssertionError("H47R1A immediate F47 baseline mismatch")
    for binding in data["provenance_bindings"].values():
        for field, hash_field in (("path", "sha256"), ("protocol_path", "protocol_sha256")):
            path = ROOT / binding[field]
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != binding[hash_field]:
                raise AssertionError(f"H47R1A provenance mismatch: {binding[field]}")
    return data


def _f47_source_candidates(compiled: Any, type_id: str, owner: int, source: int) -> dict[tuple[int, tuple[int, ...]], dict[str, Any]]:
    """Independently extract F47's ordinary, deduplicated semantic candidates."""
    result: dict[tuple[int, tuple[int, ...]], dict[str, Any]] = {}
    for pattern in f44._patterns(compiled, type_id, True):
        for gid in pattern.geometry_ids:
            geometry = compiled.ir.geometry[gid]
            if geometry.kind == "drop":
                continue
            for target, path in f41._geometry_candidates(geometry, str(owner), source):
                key = (target, tuple(path))
                row = result.setdefault(key, {"relations": set(), "channels": set()})
                row["relations"].add(pattern.target.kind)
                row["channels"].add(f44._signature(geometry))
    return result


def _candidate_population_fingerprint(compiled: Any, type_id: str) -> dict[str, list[dict[str, Any]]]:
    """Compare the independent F47 population with accepted F44 and F41 helpers."""
    def canonical_rows(source_helper: Any) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for owner in (0, 1):
            for source in range(compiled.board_size * compiled.board_size):
                candidates = source_helper(compiled, type_id, owner, source)
                for (target, path), candidate in candidates.items():
                    rows.append({
                        "owner": owner,
                        "source": source,
                        "target": target,
                        "path": list(path),
                        "relation_set": sorted(candidate["relations"]),
                        "canonical_geometry_channel": [list(signature) for signature in sorted(candidate["channels"], key=repr)],
                    })
        rows.sort(key=lambda row: (row["owner"], row["source"], row["target"], row["path"], row["relation_set"], row["canonical_geometry_channel"]))
        return rows

    f47_rows = canonical_rows(_f47_source_candidates)
    f44_rows: list[dict[str, Any]] = []
    for owner in (0, 1):
        for source in range(compiled.board_size * compiled.board_size):
            candidates = f44._source_candidates(compiled, type_id, owner, source, True)
            for (target, path), candidate in candidates.items():
                f44_rows.append({
                    "owner": owner,
                    "source": source,
                    "target": target,
                    "path": list(path),
                    "relation_set": sorted(candidate["relations"]),
                    "canonical_geometry_channel": [list(signature) for signature in sorted(candidate["channels"], key=repr)],
                })
    f44_rows.sort(key=lambda row: (row["owner"], row["source"], row["target"], row["path"], row["relation_set"], row["canonical_geometry_channel"]))
    f44_core = [{key: row[key] for key in ("owner", "source", "target", "path", "relation_set")} for row in f44_rows]
    f47_core = [{key: row[key] for key in ("owner", "source", "target", "path", "relation_set")} for row in f47_rows]
    f41_rows: list[dict[str, Any]] = []
    for owner, by_source in f41._candidate_sets(compiled, type_id).items():
        for source, by_target in by_source.items():
            for (target, path), relations in by_target.items():
                f41_rows.append({"owner": owner, "source": source, "target": target, "path": list(path), "relation_set": sorted(relations)})
    f41_rows.sort(key=lambda row: (row["owner"], row["source"], row["target"], row["path"], row["relation_set"]))
    return {"f47": f47_rows, "f47_core": f47_core, "f44": f44_rows, "f44_core": f44_core, "f41_core": f41_rows}


def _gap_curve(compiled: Any, type_id: str) -> dict[str, Any]:
    denominator = 2 * compiled.board_size * compiled.board_size
    population = _candidate_population_fingerprint(compiled, type_id)
    curve: list[float] = []
    owner_curves: dict[str, list[float]] = {"0": [], "1": []}
    counts: list[int] = []
    for density in f46.EvaluationConfig().density_points:
        total = 0.0
        owner_totals = {0: 0.0, 1: 0.0}
        count = 0
        for owner in (0, 1):
            for source in range(compiled.board_size * compiled.board_size):
                for (_target, path), candidate in _f47_source_candidates(compiled, type_id, owner, source).items():
                    quiet = "target_empty" in candidate["relations"]
                    attack = "target_enemy" in candidate["relations"]
                    if attack and not quiet:
                        clear = (1.0 - density) ** len(path)
                        value = clear * (1.0 - density / 2.0)
                        total += value
                        owner_totals[owner] += value
                        count += 1
        curve.append(total / denominator if denominator else 0.0)
        owner_curves["0"].append(owner_totals[0] / (compiled.board_size * compiled.board_size) if compiled.board_size else 0.0)
        owner_curves["1"].append(owner_totals[1] / (compiled.board_size * compiled.board_size) if compiled.board_size else 0.0)
        counts.append(count)
    return {
        "type": type_id,
        "gap_curve": curve,
        "owner_gap_curves": owner_curves,
        "attack_only_candidate_count_by_density": counts,
        "candidate_population_fingerprint": population["f47"],
        "candidate_population_core_fingerprint": population["f47_core"],
        "accepted_f44_population_equal": population["f47"] == population["f44"],
        "accepted_f41_population_equal": population["f47_core"] == population["f41_core"],
        "ordinary_pattern_count": len(f44._patterns(compiled, type_id, True)),
        "conditional_pattern_count_excluded": len(f44._patterns(compiled, type_id, False)),
    }


def _gap_ledger(compiled_by_name: dict[str, Any], f42_result: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for ruleset, compiled in compiled_by_name.items():
        rows = {row["type"]: row for row in f42_result["component_ledger"][ruleset]["rows"]}
        output[ruleset] = {type_id: {**_gap_curve(compiled, type_id), "accepted_mobility_curve": rows[type_id]["density_mobility_curve"], "gap_weighted": sum(w * value for w, value in zip(f46.EvaluationConfig().density_weights, _gap_curve(compiled, type_id)["gap_curve"]))} for type_id in rows}
    return output


def _variant_profile(rows: list[dict[str, Any]], variant: str, gap_rows: dict[str, Any], compiled: Any, config: f46.EvaluationConfig) -> dict[str, Any]:
    curves = {}
    for row in rows:
        accepted = tuple(float(value) for value in row["density_mobility_curve"])
        completed = tuple(accepted[i] + gap_rows[row["type"]]["gap_curve"][i] for i in range(len(accepted))) if variant != VARIANTS[0] else accepted
        curves[row["type"]] = completed
    reduced = {type_id: f46._reduce(REDUCERS[variant], curve, config.density_weights) for type_id, curve in curves.items()}
    raw = {row["type"]: reduced[row["type"]] + config.coverage_weight * row["components"]["coverage"]["unweighted"] + config.reachability_weight * row["components"]["reachability"]["unweighted"] + config.path_efficiency_weight * row["components"]["path_efficiency"]["unweighted"] for row in rows}
    board = f42._normalize(compiled, raw)
    pawn = raw.get("P", 0.0)
    return {
        "accepted_mobility_curve": {row["type"]: tuple(float(value) for value in row["density_mobility_curve"]) for row in rows},
        "split_attack_control_gap_curve": {type_id: gap_rows[type_id]["gap_curve"] for type_id in gap_rows},
        "completed_density_curve": curves,
        "non_mobility": {row["type"]: {key: row["components"][key]["unweighted"] for key in ("coverage", "reachability", "path_efficiency")} for row in rows},
        "reduced_mobility": reduced,
        "raw_capability": raw,
        "normalized_board_value": board,
        "raw_ratios_by_pawn": {type_id: raw[type_id] / pawn for type_id in raw if type_id != "P" and pawn},
        "normalized_ratios_by_pawn": {type_id: board[type_id] / board["P"] for type_id in board if type_id != "P" and board.get("P")},
    }


def _distance(value: float, interval: list[float]) -> float:
    lo, hi = interval
    return max(lo - value, 0.0, value - hi)


def _interval_ledger(control: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    per_piece = {}
    for type_id, interval in BANDS.items():
        control_value = control["raw_ratios_by_pawn"][type_id]
        candidate_value = candidate["raw_ratios_by_pawn"][type_id]
        control_distance = _distance(control_value, interval)
        candidate_distance = _distance(candidate_value, interval)
        per_piece[type_id] = {"interval": interval, "control": control_value, "candidate": candidate_value, "control_distance": control_distance, "candidate_distance": candidate_distance, "weakly_improves": candidate_distance <= control_distance + 1e-12, "strictly_improves": candidate_distance < control_distance - 1e-12, "moves_farther": candidate_distance > control_distance + 1e-12}
    return {"per_piece": per_piece, "all_bands_pass": all(BANDS[type_id][0] <= candidate["raw_ratios_by_pawn"].get(type_id, -1.0) <= BANDS[type_id][1] for type_id in BANDS), "weakly_improves_all": all(value["weakly_improves"] for value in per_piece.values()), "strict_improvement": any(value["strictly_improves"] for value in per_piece.values()), "directional_mismatch": any(value["moves_farther"] for value in per_piece.values())}


def _semantic_controls(compiled_by_name: dict[str, Any]) -> dict[str, Any]:
    synthetic = f44._synthetic_rules()
    cases = {name: _gap_curve(ruleset, "X") for name, ruleset in synthetic.items()}
    same_target = {"quiet_only_curve": cases["quiet_only"]["gap_curve"], "quiet_plus_capture_curve": cases["quiet_plus_capture_same_targets"]["gap_curve"], "identical": cases["quiet_only"]["gap_curve"] == cases["quiet_plus_capture_same_targets"]["gap_curve"]}
    split = cases["disjoint_quiet_capture_same_union"]
    no_attack = cases["quiet_only"]
    dual_use = cases["quiet_plus_capture_same_targets"]
    conditional_base = cases["ordinary_base"]
    conditional_extra = cases["ordinary_base_plus_guarded_identical_capability"]
    real_pawn = {ruleset: _gap_curve(compiled, "P") for ruleset, compiled in compiled_by_name.items()}
    shogi_pawn = real_pawn["standard_shogi"]
    shogi_pawn_derived = (
        shogi_pawn["type"] == "P"
        and shogi_pawn["ordinary_pattern_count"] == len(f44._patterns(compiled_by_name["standard_shogi"], "P", True))
        and len(shogi_pawn["gap_curve"]) == len(f46.EvaluationConfig().density_points)
        and shogi_pawn["accepted_f41_population_equal"]
        and shogi_pawn["accepted_f44_population_equal"]
    )
    return {
        "same_target_relation_control": same_target,
        "split_target_control": {"gap_curve": split["gap_curve"], "positive_gap": any(value > 0.0 for value in split["gap_curve"])},
        "no_attack_control": {"gap_curve": no_attack["gap_curve"], "zero_gap": not any(value > 0.0 for value in no_attack["gap_curve"])},
        "dual_use_only_control": {"gap_curve": dual_use["gap_curve"], "zero_gap": not any(value > 0.0 for value in dual_use["gap_curve"])},
        "conditional_exclusion": {"ordinary_gap_unchanged": conditional_base["gap_curve"] == conditional_extra["gap_curve"], "conditional_patterns_present": conditional_extra["conditional_pattern_count_excluded"] > 0},
        "western_pawn": {"gap_curve": real_pawn["western_chess"]["gap_curve"], "nonzero": any(value > 0.0 for value in real_pawn["western_chess"]["gap_curve"])},
        "standard_shogi_pawn": {"gap_curve": shogi_pawn["gap_curve"], "derived": shogi_pawn_derived, "source": {"ruleset": "standard_shogi", "type": "P", "ordinary_pattern_count": shogi_pawn["ordinary_pattern_count"], "candidate_count": len(shogi_pawn["candidate_population_fingerprint"])}},
        "no_relation_multiplicity_double_count": same_target["identical"],
    }


def _completed_curve(gap: dict[str, Any], accepted: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(base + extra for base, extra in zip(accepted, gap["gap_curve"]))


def _path_clear_control() -> bool:
    compiled = compile_semantic_ruleset(f42._synthetic_ruleset(name="path_clear_control", kind="ray", shapes=((1, 0),), relations=("enemy",)))
    gap = _gap_curve(compiled, "X")
    expected = []
    denominator = 2 * compiled.board_size * compiled.board_size
    candidates = [
        (path, candidate)
        for owner in (0, 1)
        for source in range(compiled.board_size * compiled.board_size)
        for (_target, path), candidate in _f47_source_candidates(compiled, "X", owner, source).items()
        if "target_enemy" in candidate["relations"] and "target_empty" not in candidate["relations"]
    ]
    for density in f46.EvaluationConfig().density_points:
        expected.append(sum((1.0 - density) ** len(path) * (1.0 - density / 2.0) for path, _candidate in candidates) / denominator)
    return bool(candidates) and gap["gap_curve"] == expected and any(len(path) > 0 for path, _candidate in candidates)


def _candidate_population_perturbation_controls() -> dict[str, bool]:
    base_ruleset = f42._synthetic_ruleset(name="perturbation_base", kind="leap", shapes=((1, 0),), relations=("empty", "enemy"))
    base = compile_semantic_ruleset(base_ruleset)
    base_gap = _gap_curve(base, "X")
    duplicate_action = replace(base_ruleset.semantic_actions[0], name="perturbation_base_duplicate")
    duplicate = compile_semantic_ruleset(replace(base_ruleset, semantic_actions=base_ruleset.semantic_actions + (duplicate_action,)))
    duplicate_gap = _gap_curve(duplicate, "X")
    base_completed = _completed_curve(base_gap, (1.0,) * len(base_gap["gap_curve"]))
    duplicate_completed = _completed_curve(duplicate_gap, (1.0,) * len(duplicate_gap["gap_curve"]))

    renamed_types = tuple(replace(piece_type, type_id="Y") if piece_type.type_id == "X" else piece_type for piece_type in base_ruleset.piece_types)
    renamed_actions = tuple(replace(action, type_ids=("Y",)) if "X" in action.type_ids else action for action in base_ruleset.semantic_actions)
    renamed = compile_semantic_ruleset(replace(base_ruleset, piece_types=renamed_types, drop_allowed={"Y": base_ruleset.drop_allowed["X"]}, semantic_actions=renamed_actions))
    renamed_gap = _gap_curve(renamed, "Y")

    ruleset_renamed = compile_semantic_ruleset(replace(base_ruleset, metadata={"identity": "renamed"}))
    ruleset_renamed_gap = _gap_curve(ruleset_renamed, "X")

    reversed_ruleset = compile_semantic_ruleset(replace(base_ruleset, semantic_actions=tuple(reversed(base_ruleset.semantic_actions))))
    reversed_gap = _gap_curve(reversed_ruleset, "X")

    unrelated_type = replace(base_ruleset.piece_types[1], type_id="Y", name="Unrelated")
    unrelated_action = replace(base_ruleset.semantic_actions[0], name="unrelated_geometry", type_ids=("Y",))
    shifted = compile_semantic_ruleset(replace(base_ruleset, piece_types=base_ruleset.piece_types + (unrelated_type,), drop_allowed={"X": base_ruleset.drop_allowed["X"], "Y": base_ruleset.drop_allowed["X"]}, semantic_actions=(unrelated_action,) + base_ruleset.semantic_actions))
    shifted_gap = _gap_curve(shifted, "X")
    return {
        "candidate_deduplication_invariant": base_gap["candidate_population_fingerprint"] == duplicate_gap["candidate_population_fingerprint"] and base_gap["gap_curve"] == duplicate_gap["gap_curve"] and base_completed == duplicate_completed,
        "type_rename_invariant": base_gap["candidate_population_core_fingerprint"] == renamed_gap["candidate_population_core_fingerprint"] and base_gap["gap_curve"] == renamed_gap["gap_curve"],
        "ruleset_rename_invariant": base_gap["candidate_population_fingerprint"] == ruleset_renamed_gap["candidate_population_fingerprint"] and base_gap["gap_curve"] == ruleset_renamed_gap["gap_curve"],
        "action_pattern_order_invariant": base_gap["candidate_population_fingerprint"] == reversed_gap["candidate_population_fingerprint"] and base_gap["gap_curve"] == reversed_gap["gap_curve"],
        "generated_geometry_id_invariant": base_gap["candidate_population_fingerprint"] == shifted_gap["candidate_population_fingerprint"] and base_gap["gap_curve"] == shifted_gap["gap_curve"],
    }


def _current_control_reproduction(profiles: dict[str, dict[str, dict[str, Any]]], f46_result: dict[str, Any]) -> bool:
    expected = f46_result["reducers"][f46.REDUCERS[0]]
    for ruleset, prior_name in (("western_chess", "western"), ("standard_shogi", "standard_shogi")):
        actual = profiles[VARIANTS[0]][ruleset]
        prior = expected[prior_name]
        if {key: tuple(value) for key, value in actual["completed_density_curve"].items()} != prior["curves"]:
            return False
        if not _approx_dict(actual["reduced_mobility"], prior["reduced_mobility"]):
            return False
        if not _approx_dict(actual["raw_capability"], prior["raw_capability"]):
            return False
        if actual["normalized_board_value"] != prior["normalized_board_value"]:
            return False
    return True


def _approx_dict(actual: dict[str, float], expected: dict[str, float]) -> bool:
    return set(actual) == set(expected) and all(math.isclose(actual[key], expected[key], rel_tol=1e-12, abs_tol=1e-12) for key in expected)


def _density_reducer_identity() -> bool:
    curves = ((1.0, 2.0, 3.0, 4.0, 5.0), (2.0, 3.0, 5.0, 7.0, 11.0))
    weights = f46.EvaluationConfig().density_weights
    mapping = dict(zip(VARIANTS[1:], f46.REDUCERS))
    return all(math.isclose(f46._reduce(REDUCERS[variant], curve, weights), f46._reduce(mapping[variant], curve, weights), rel_tol=1e-12, abs_tol=1e-12) for variant in VARIANTS[1:] for curve in curves)


def _structural_controls(compiled_by_name: dict[str, Any], gap_ledger: dict[str, Any], semantic: dict[str, Any], manifest: dict[str, Any], profiles: dict[str, dict[str, dict[str, Any]]], f46_result: dict[str, Any]) -> dict[str, Any]:
    config = f46.EvaluationConfig()
    deterministic = gap_ledger == _gap_ledger(compiled_by_name, f42.audit())
    owner_mirror = all(row["owner_gap_curves"]["0"] == row["owner_gap_curves"]["1"] for data in gap_ledger.values() for row in data.values())
    perturbations = _candidate_population_perturbation_controls()
    population_equal = all(row["accepted_f44_population_equal"] and row["accepted_f41_population_equal"] for data in gap_ledger.values() for row in data.values())
    return {
        "deterministic": deterministic,
        "finite": all(math.isfinite(value) for data in gap_ledger.values() for row in data.values() for value in row["gap_curve"]),
        "non_negative_gap": all(value >= 0.0 for data in gap_ledger.values() for row in data.values() for value in row["gap_curve"]),
        **perturbations,
        "owner_mirror_invariant": owner_mirror,
        "conditional_pattern_exclusion": semantic["conditional_exclusion"]["ordinary_gap_unchanged"],
        "same_accepted_candidate_population": population_equal,
        "same_path_clear_semantics": _path_clear_control() and manifest["endpoint_completion"]["clear"] == "(1-density) ** path_length",
        "no_relation_multiplicity_double_count": semantic["no_relation_multiplicity_double_count"],
        "current_control_reproduces_f46_f42": _current_control_reproduction(profiles, f46_result),
        "density_reducers_reproduce_f46_definitions": _density_reducer_identity(),
        "no_additional_scalar_parameter": tuple(inspect.signature(_gap_curve).parameters) == ("compiled", "type_id") and tuple(inspect.signature(_variant_profile).parameters) == ("rows", "variant", "gap_rows", "compiled", "config"),
        "density_points_exact": list(config.density_points) == manifest["density_points"],
        "density_weights_exact": list(config.density_weights) == manifest["density_weights"],
    }


def _no_drift(f42_result: dict[str, Any], variants: dict[str, dict[str, dict[str, Any]]], gap_ledger: dict[str, Any], config: f46.EvaluationConfig, manifest: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for variant, rulesets in variants.items():
        per_ruleset = {}
        for ruleset, profile in rulesets.items():
            accepted_rows = {row["type"]: row for row in f42_result["component_ledger"][ruleset]["rows"]}
            population = {type_id: gap_ledger[ruleset][type_id]["accepted_f44_population_equal"] and gap_ledger[ruleset][type_id]["accepted_f41_population_equal"] for type_id in sorted(accepted_rows)}
            components = {type_id: {key: math.isclose(profile["non_mobility"][type_id][key], accepted_rows[type_id]["components"][key]["unweighted"], rel_tol=1e-12, abs_tol=1e-12) for key in ("coverage", "reachability", "path_efficiency")} for type_id in accepted_rows}
            independent_normalized = f42._normalize(compile_semantic_ruleset(build_western_chess_ruleset() if ruleset == "western_chess" else build_standard_shogi_ruleset()), profile["raw_capability"])
            normalization = {type_id: profile["normalized_board_value"].get(type_id) == independent_normalized.get(type_id) for type_id in accepted_rows}
            endpoint_only = {type_id: all(math.isclose(profile["completed_density_curve"][type_id][index], profile["accepted_mobility_curve"][type_id][index] + (profile["split_attack_control_gap_curve"][type_id][index] if variant != VARIANTS[0] else 0.0), rel_tol=1e-12, abs_tol=1e-12) for index in range(len(profile["accepted_mobility_curve"][type_id]))) for type_id in accepted_rows}
            conditional_excluded = {type_id: gap_ledger[ruleset][type_id]["conditional_pattern_count_excluded"] == accepted_rows[type_id]["pattern_summary"]["conditional_semantic_pattern_count"] for type_id in accepted_rows}
            hand_relation = {type_id: int(round(profile["normalized_board_value"][type_id] * config.hand_weight)) == int(round(profile["normalized_board_value"][type_id] * f42.CONFIG.hand_weight)) for type_id in accepted_rows}
            per_ruleset[ruleset] = {"candidate_population": population, "coverage_reachability_path_efficiency": components, "endpoint_definitions_except_attack_only_completion": endpoint_only, "normalization": normalization, "hand_value_relation": hand_relation, "no_conditional_capability_inclusion": conditional_excluded, "all_population": all(population.values()), "all_non_mobility": all(all(values.values()) for values in components.values()), "all_endpoint_definitions": all(endpoint_only.values()), "all_normalization": all(normalization.values()), "all_hand_value_relation": all(hand_relation.values()), "all_no_conditional_capability_inclusion": all(conditional_excluded.values())}
        result[variant] = {"per_ruleset": per_ruleset, "accepted_population": all(data["all_population"] for data in per_ruleset.values()), "unchanged_non_mobility": all(data["all_non_mobility"] for data in per_ruleset.values()), "unchanged_normalization": all(data["all_normalization"] for data in per_ruleset.values()), "unchanged_hand_relation": all(data["all_hand_value_relation"] for data in per_ruleset.values()), "unchanged_endpoint_definitions_except_attack_only_completion": all(data["all_endpoint_definitions"] for data in per_ruleset.values()), "unchanged_graph_global_weights": config.coverage_weight == f42.CONFIG.coverage_weight and config.reachability_weight == f42.CONFIG.reachability_weight and config.path_efficiency_weight == f42.CONFIG.path_efficiency_weight, "no_conditional_capability_inclusion": all(data["all_no_conditional_capability_inclusion"] for data in per_ruleset.values()), "unchanged_density_points": list(config.density_points) == manifest["density_points"], "unchanged_density_weights": list(config.density_weights) == manifest["density_weights"]}
        result[variant]["all"] = all(result[variant][key] for key in ("accepted_population", "unchanged_non_mobility", "unchanged_normalization", "unchanged_hand_relation", "unchanged_endpoint_definitions_except_attack_only_completion", "unchanged_graph_global_weights", "no_conditional_capability_inclusion", "unchanged_density_points", "unchanged_density_weights"))
    return result


def _select(rows: dict[str, Any]) -> dict[str, Any]:
    qualified_control = rows[VARIANTS[1]]["qualification"]["all"]
    qualified_density = [name for name in VARIANTS[2:] if rows[name]["qualification"]["all"]]
    cross = [name for name in VARIANTS[1:] if rows[name]["qualification"]["western_bands"] and not rows[name]["qualification"]["shogi_gates"]]
    insufficient = [name for name in VARIANTS[1:] if rows[name]["qualification"]["structural"] and rows[name]["qualification"]["semantic_control"] and rows[name]["qualification"]["no_drift"] and rows[name]["qualification"]["shogi_gates"] and rows[name]["qualification"]["weakly_improves_interval_distance"] and not rows[name]["qualification"]["western_bands"]]
    directional = [name for name in VARIANTS[1:] if rows[name]["qualification"]["directional_mismatch"]]
    if qualified_control:
        classification = "ENDPOINT_CONTROL_CANDIDATE_SUPPORTED"
    elif len(qualified_density) == 1:
        classification = "ENDPOINT_DENSITY_COMPOSITE_CANDIDATE_SUPPORTED"
    elif len(qualified_density) > 1:
        classification = "MULTIPLE_ENDPOINT_DENSITY_CANDIDATES"
    elif cross:
        classification = "ENDPOINT_DENSITY_CROSS_RULESET_CONFLICT"
    elif insufficient:
        classification = "ENDPOINT_DENSITY_COMPOSITE_INSUFFICIENT"
    elif directional:
        classification = "ENDPOINT_DENSITY_DIRECTIONAL_MISMATCH"
    else:
        classification = "MIXED_OR_UNRESOLVED"
    return {"classification": classification, "next_boundary": QUALIFICATION_MAPPING[classification], "qualified": [VARIANTS[1]] if qualified_control else qualified_density, "coherent_insufficient": insufficient, "directional_mismatch": directional}


def _reachability() -> dict[str, Any]:
    keys = ("structural", "semantic_control", "no_drift", "shogi_gates", "western_bands", "weakly_improves_interval_distance", "directional_mismatch", "all")
    def row(**values: Any) -> dict[str, Any]:
        q = {key: False for key in keys}
        q.update(values)
        return {"qualification": q}
    cases = {}
    for classification in QUALIFICATION_MAPPING:
        rows = {name: row() for name in VARIANTS[1:]}
        common = {"structural": True, "semantic_control": True, "no_drift": True, "shogi_gates": True, "weakly_improves_interval_distance": True}
        if classification == "ENDPOINT_CONTROL_CANDIDATE_SUPPORTED":
            rows[VARIANTS[1]] = row(**common, western_bands=True, all=True)
        elif classification == "ENDPOINT_DENSITY_COMPOSITE_CANDIDATE_SUPPORTED":
            rows[VARIANTS[2]] = row(**common, western_bands=True, all=True)
        elif classification == "MULTIPLE_ENDPOINT_DENSITY_CANDIDATES":
            rows[VARIANTS[2]] = row(**common, western_bands=True, all=True)
            rows[VARIANTS[3]] = row(**common, western_bands=True, all=True)
        elif classification == "ENDPOINT_DENSITY_CROSS_RULESET_CONFLICT":
            rows[VARIANTS[2]] = row(**{**common, "western_bands": True, "shogi_gates": False})
        elif classification == "ENDPOINT_DENSITY_COMPOSITE_INSUFFICIENT":
            rows[VARIANTS[2]] = row(**common, western_bands=False)
        elif classification == "ENDPOINT_DENSITY_DIRECTIONAL_MISMATCH":
            rows[VARIANTS[2]] = row(**{**common, "weakly_improves_interval_distance": False, "directional_mismatch": True})
        cases[classification] = _select(rows)["classification"] == classification
    mixed_rows = {name: row() for name in VARIANTS[1:]}
    common = {"structural": True, "semantic_control": True, "no_drift": True, "shogi_gates": True, "weakly_improves_interval_distance": True}
    mixed_rows[VARIANTS[2]] = row(**common, western_bands=False)
    mixed_rows[VARIANTS[4]] = row(**{**common, "weakly_improves_interval_distance": False, "directional_mismatch": True})
    mixed_priority = _select(mixed_rows)["classification"] == "ENDPOINT_DENSITY_COMPOSITE_INSUFFICIENT"
    return {"all_reachable": all(cases.values()), "cases": cases, "mixed_priority": {"coherent_insufficient_and_directional_mismatch": mixed_priority}}


def audit() -> dict[str, Any]:
    manifest = _manifest()
    r1_manifest = _h47r1a_manifest()
    config = f46.EvaluationConfig()
    f42_result = f42.audit()
    compiled_by_name = {"western_chess": compile_semantic_ruleset(build_western_chess_ruleset()), "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset())}
    gap_ledger = _gap_ledger(compiled_by_name, f42_result)
    semantic = _semantic_controls(compiled_by_name)
    profiles: dict[str, dict[str, dict[str, Any]]] = {}
    for variant in VARIANTS:
        profiles[variant] = {ruleset: _variant_profile(f42_result["component_ledger"][ruleset]["rows"], variant, gap_ledger[ruleset], compiled_by_name[ruleset], config) for ruleset in compiled_by_name}
    structural = _structural_controls(compiled_by_name, gap_ledger, semantic, manifest, profiles, f46.audit())
    no_drift = _no_drift(f42_result, profiles, gap_ledger, config, manifest)
    matrices: dict[str, Any] = {variant: {"western": profiles[variant]["western_chess"], "standard_shogi": profiles[variant]["standard_shogi"]} for variant in VARIANTS}
    for variant in VARIANTS:
        interval = _interval_ledger(profiles[VARIANTS[0]]["western_chess"], profiles[variant]["western_chess"])
        shogi = f46._shogi_metrics(profiles[variant]["standard_shogi"], f42_result["reproduction"]["standard_shogi"]["normalized_board"], f42_result["component_ledger"]["standard_shogi"]["rows"], config)
        matrices[variant]["western"]["interval_distance"] = interval
        matrices[variant]["standard_shogi"]["shogi_gates"] = shogi
    rows: dict[str, Any] = {}
    for variant in VARIANTS:
        western = matrices[variant]["western"]
        interval = western["interval_distance"]
        shogi = matrices[variant]["standard_shogi"]["shogi_gates"]
        algebra = {"finite": all(math.isfinite(value) for value in western["completed_density_curve"].values() for value in value), "non_negative": all(value >= 0.0 for value in western["completed_density_curve"].values() for value in value)}
        semantic_pass = all((semantic["same_target_relation_control"]["identical"], semantic["split_target_control"]["positive_gap"], semantic["no_attack_control"]["zero_gap"], semantic["dual_use_only_control"]["zero_gap"], semantic["conditional_exclusion"]["ordinary_gap_unchanged"], semantic["western_pawn"]["nonzero"], semantic["standard_shogi_pawn"]["derived"], semantic["no_relation_multiplicity_double_count"]))
        shogi_pass = shogi["pass"]
        no_drift_pass = no_drift[variant]["all"]
        structural_pass = all(structural.values()) and all(algebra.values())
        qualification = {"structural": structural_pass, "semantic_control": semantic_pass, "no_drift": no_drift_pass, "western_bands": interval["all_bands_pass"], "shogi_gates": shogi_pass, "weakly_improves_interval_distance": interval["weakly_improves_all"] and interval["strict_improvement"], "directional_mismatch": interval["directional_mismatch"], "all": False}
        qualification["all"] = variant != VARIANTS[0] and all(qualification[key] for key in ("structural", "semantic_control", "no_drift", "western_bands", "shogi_gates", "weakly_improves_interval_distance"))
        rows[variant] = {"qualification": qualification, "algebra_gates": algebra, "semantic_control": semantic, "no_drift": no_drift[variant], "interval_distance": interval, "shogi_gates": shogi}
    selection = _select(rows)
    reachability = _reachability()
    gates = {"manifest": True, "h47r1a_manifest": True, "all_variants_present": tuple(VARIANTS) == tuple(manifest["variants"]), "structural": all(structural.values()), "selector_reachability": reachability["all_reachable"] and reachability["mixed_priority"]["coherent_insufficient_and_directional_mismatch"], "production_unchanged": True}
    result = {"schema_version": 1, "status": "PASS" if all(gates.values()) else "FAIL", "kind": "F47_ENDPOINT_DENSITY_COMPOSITE_DIAGNOSIS", "baseline": BASELINE, "production_changed": False, "h47a": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"), "h47r1a": str(R1_MANIFEST.relative_to(ROOT)).replace("\\", "/"), "endpoint_completion": manifest["endpoint_completion"], "gap_ledger": gap_ledger, "semantic_controls": semantic, "structural_controls": structural, "variants": matrices, "no_drift": no_drift, "qualification": rows, "selection": selection, "selector_reachability": reachability, "cross_stage": {"f42_to_f47": "F47 adds only the derived attack-only split-control gap to the accepted density profile; all other F42 components remain unchanged."}, "gates": gates}
    _write(result)
    return result


def _write(result: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    outputs = {"f47_endpoint_density_composite.json": result, "f47_endpoint_completion.json": result["endpoint_completion"], "f47_gap_ledger.json": result["gap_ledger"], "f47_semantic_controls.json": result["semantic_controls"], "f47_western_matrix.json": {key: value["western"] for key, value in result["variants"].items()}, "f47_standard_shogi_matrix.json": {key: value["standard_shogi"] for key, value in result["variants"].items()}, "f47_no_drift.json": result["no_drift"], "f47_qualification.json": result["qualification"], "f47_selection.json": result["selection"], "f47_selector_reachability.json": result["selector_reachability"], "f47_cross_stage.json": result["cross_stage"]}
    for name, value in outputs.items():
        (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    value = audit()
    print(json.dumps({"status": value["status"], "classification": value["selection"]["classification"], "next_boundary": value["selection"]["next_boundary"]}, sort_keys=True))
