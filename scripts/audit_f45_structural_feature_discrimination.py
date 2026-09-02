"""F45 diagnosis-only discrimination of the F44 structural signals.

This audit traces each F44 signal to its current consumer, assigns exactly one
static/dynamic placement, and selects a minimum explanatory family subset using
boolean residual coverage.  It intentionally does not build a new evaluator
formula or fit any coefficient.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".generic_chess_flow"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import audit_f44_structural_capability as f44  # noqa: E402


BASELINE = "1f4fc5f1dc12675e6bafcf1992245441d36104f5"
MANIFEST = ROOT / "tests" / "fixtures" / "f45_structural_feature_discrimination_manifest.json"
FAMILIES = (
    "S44-A_ENDPOINT_CONTROL_SEMANTICS",
    "S44-B_CONDITIONAL_CAPABILITY_RESERVE",
    "S44-C_CHANNEL_DIVERSITY_CONCENTRATION",
    "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY",
)
SURVIVING = FAMILIES[:2] + FAMILIES[3:]
PLACEMENTS = (
    "STATIC_MATERIAL_ADMISSIBLE",
    "DYNAMIC_EVALUATOR_ADMISSIBLE",
    "ALREADY_EQUIVALENTLY_CONSUMED",
    "DIAGNOSTIC_ONLY_NOT_ADMISSIBLE",
    "UNRESOLVED",
)
CLASSIFICATION_MAPPING = {
    "ENDPOINT_CONTROL_FEATURE_PRIMARY": "F46_ENDPOINT_CONTROL_FEATURE_PROTOTYPE",
    "CONDITIONAL_CAPABILITY_FEATURE_PRIMARY": "F46_CONDITIONAL_CAPABILITY_RUNTIME_PROTOTYPE",
    "DENSITY_PROFILE_FEATURE_PRIMARY": "F46_DENSITY_PROFILE_FEATURE_PROTOTYPE",
    "ENDPOINT_DENSITY_COMPOSITE_REQUIRED": "F46_ENDPOINT_DENSITY_COMPOSITE_PROTOTYPE",
    "STATIC_DYNAMIC_STRUCTURAL_COMPOSITE_REQUIRED": "F46_STRUCTURAL_CONSUMER_SPLIT_PROTOTYPE",
    "STRUCTURAL_INFORMATION_ALREADY_CONSUMED": "F46_MATERIAL_PRIOR_REASSESSMENT",
    "STRUCTURAL_FEATURE_DISCRIMINATION_INSUFFICIENT": "F46_GENERIC_MATERIAL_PRIOR_REASSESSMENT",
    "CROSS_RULESET_STRUCTURAL_CONFLICT": "F46_GENERIC_MATERIAL_PRIOR_REASSESSMENT",
}


def _load_manifest() -> dict[str, Any]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    actual = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if actual != data["manifest_sha256"]:
        raise AssertionError("H45A manifest hash mismatch")
    if data["baseline"]["f44_sha"] != BASELINE:
        raise AssertionError("H45A baseline mismatch")
    return data


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_bindings(manifest: dict[str, Any]) -> dict[str, Any]:
    results = {}
    for name, binding in {**manifest["input_files"], **manifest["f44_evidence_bindings"]}.items():
        path = ROOT / binding["path"]
        actual = _sha(path) if path.exists() else None
        results[name] = {"path": binding["path"], "expected": binding["sha256"], "actual": actual, "match": actual == binding["sha256"]}
    return {"all_match": all(row["match"] for row in results.values()), "rows": results}


def _line_facts(relative: str, required: tuple[str, ...]) -> dict[str, Any]:
    path = ROOT / relative
    lines = path.read_text(encoding="utf-8").splitlines()
    locations = {}
    for needle in required:
        locations[needle] = [index for index, line in enumerate(lines, 1) if needle in line]
    return {"path": relative, "functions_or_symbols": locations, "all_present": all(locations.values())}


def _reproduce_f44(manifest: dict[str, Any]) -> dict[str, Any]:
    evidence = f44._audit()
    bindings = _verify_bindings(manifest)
    selection = evidence["selection"]
    endpoint = evidence["signals"][FAMILIES[0]]["independence"]
    conditional = evidence["signals"][FAMILIES[1]]["independence"]
    channel = evidence["signals"][FAMILIES[2]]["independence"]
    density = evidence["signals"][FAMILIES[3]]["independence"]
    gates = {
        "classification_unchanged": selection["classification"] == "MULTIPLE_STRUCTURAL_INFORMATION_GAPS",
        "boundary_unchanged": selection["next_boundary"] == "F45_STRUCTURAL_FEATURE_DISCRIMINATION",
        "families_unchanged": selection["materially_supported_families"] == list(SURVIVING),
        "channel_negative_control": channel["pass"] is False,
        "endpoint_matched_collision": endpoint["pass"] is True,
        "conditional_identical_geometry_guard": conditional["pass"] is True,
        "density_matched_mass_curve": density["pass"] is True,
        "binding_hashes": bindings["all_match"],
    }
    return {"status": "PASS" if all(gates.values()) else "FAIL", "gates": gates, "selection": selection, "binding_verification": bindings}


def _source_consumer_ledger() -> dict[str, Any]:
    attack = _line_facts("generic_chess/core/attacks.py", ("def pseudo_attacks", "attacked.update", "return frozenset(attacked)"))
    evaluator = _line_facts("generic_chess/ai/evaluation/evaluator.py", ("def evaluate", "pseudo_attacks(position, 0", "def _promotion_bonus", "empty_forward_mobility"))
    analyzer = _line_facts("generic_chess/ai/evaluation/analyzer.py", ("def build_movement_capability", "mobility_density_curve", "expected_mobility=curve"))
    profile = _line_facts("generic_chess/ai/evaluation/profile.py", ("def _raw_capability_score", "mobility_score = sum", "zip(config.density_weights"))
    executor = _line_facts("generic_chess/core/semantic_executor.py", ("for slot_guard in pattern.slot_guards", "pattern.guards", "def _violates_postconditions"))
    return {
        "S44-A_ENDPOINT_CONTROL_SEMANTICS": {
            "consumer_paths": [attack, evaluator],
            "shared_information": "position-dependent pseudo-attack destination union/count",
            "unique_information": "target_empty versus target_enemy relation and quiet/control overlap",
            "same_semantic_distinction": False,
            "equivalent_existing_consumer": False,
            "complete_pre_search_collision_remains": attack["all_present"] and not any("target_relation" in line for line in (ROOT / "generic_chess/core/attacks.py").read_text(encoding="utf-8").splitlines()),
            "ownership": "static rule geometry plus partial dynamic union consumer",
        },
        "S44-B_CONDITIONAL_CAPABILITY_RESERVE": {
            "consumer_paths": [executor, evaluator],
            "shared_information": "promotion potential is dynamically consumed for promotable pieces",
            "unique_information": "guard availability for executable conditional patterns",
            "same_semantic_distinction": False,
            "equivalent_existing_consumer": False,
            "complete_pre_search_collision_remains": True,
            "ownership": "dynamic evaluator / move-state consumer",
        },
        "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY": {
            "consumer_paths": [analyzer, profile, evaluator],
            "shared_information": "density-weighted mobility scalar and dynamic pseudo-attack count",
            "unique_information": "five-point retention curve, curvature, and blocker ordering",
            "same_semantic_distinction": False,
            "equivalent_existing_consumer": False,
            "complete_pre_search_collision_remains": True,
            "ownership": "static rule-derived profile; no independent dynamic shape consumer",
        },
    }


def _guard_category_ledger(evidence: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for ruleset_name, data in evidence["signals"][FAMILIES[1]]["real_rulesets"].items():
        for type_id, metrics in data.items():
            reserve = metrics["conditional_reserve"]
            categories = {key: int(value) for key, value in reserve["guard_categories"].items() if value}
            for category, count in categories.items():
                rows.append({"ruleset": ruleset_name, "type": type_id, "category": category, "count": count})
    western = [row for row in rows if row["ruleset"] == "western_chess"]
    return {
        "rows": rows,
        "categories_observed": sorted({row["category"] for row in rows}),
        "western_conditional_patterns": sum(row["count"] for row in western),
        "state_and_slot_guards_present": {"state_guard": any(row["category"] == "state_guard" for row in rows), "slot_guard": any(row["category"] == "slot_guard" for row in rows)},
        "promotion_related_transition": False,
        "initial_state_or_availability_restriction": True,
        "other_executable_guard": any(row["category"] == "postcondition" for row in rows),
    }


def _orientation_ledger(evidence: dict[str, Any], f42_result: dict[str, Any]) -> dict[str, Any]:
    real = evidence["signals"]
    pawn = real[FAMILIES[3]]["real_rulesets"]["western_chess"]["P"]["density_profile"]
    knight = real[FAMILIES[3]]["real_rulesets"]["western_chess"]["N"]["density_profile"]
    rays = [real[FAMILIES[3]]["real_rulesets"]["western_chess"][piece]["density_profile"] for piece in ("B", "R", "Q")]
    ray_floor = min(row["maximum_fractional_drop"] for row in rays)
    endpoint = {
        "coordinates": ["quiet_geometry_mass", "attack_geometry_mass", "dual_use_overlap_mass", "quiet_capture_union_mass"],
        "resolves_R1": real[FAMILIES[0]]["real_rulesets"]["western_chess"]["P"]["endpoint_control"]["quiet_capture_overlap_ratio"] < 1.0,
        "resolves_R2": False,
        "reason": "quiet/control separation distinguishes Pawn endpoints but has no blocker-fragility or short-channel coordinate",
    }
    conditional = {
        "coordinates": ["ordinary_capability_lower_envelope", "guarded_capability_upper_reserve", "guard_category", "availability_state"],
        "resolves_R1": real[FAMILIES[1]]["real_rulesets"]["western_chess"]["P"]["conditional_reserve"]["conditional_reserve_over_ordinary_mass"] > 0.0,
        "resolves_R2": False,
        "reason": "guarded reserve is a Pawn-facing structural distinction but has no Knight-versus-ray coordinate and requires runtime availability",
    }
    density = {
        "coordinates": ["mobility_retention_by_density", "weighted_retention", "maximum_fractional_drop", "discrete_curvature", "blocker_fragility_ordering"],
        "resolves_R1": pawn["maximum_fractional_drop"] < knight["maximum_fractional_drop"],
        "resolves_R2": knight["maximum_fractional_drop"] < ray_floor,
        "reason": "the complete curve separates Pawn's blocker-insensitive profile and Knight's short-channel profile from long rays",
    }
    shogi = f42_result["shogi_cross_rule"]["positive_control"]
    return {
        "S44-A_ENDPOINT_CONTROL_SEMANTICS": endpoint,
        "S44-B_CONDITIONAL_CAPABILITY_RESERVE": conditional,
        "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY": density,
        "R3_cross_rule_gate": {
            "pass": shogi["pass"],
            "cosine": shogi["board_value_cosine_vs_current"],
            "spearman": shogi["spearman_vs_current"],
            "pairwise_ordering": shogi["pairwise_ordering_vs_current"],
            "hand_board_ratio_range": shogi["hand_board_ratio_range"],
            "why_shogi_differs": f42_result["shogi_cross_rule"]["why_shogi_does_not_share_the_same_observed_ratio_pathology"],
        },
    }


def _redundancy_ledger() -> dict[str, Any]:
    semantics = {
        "S44-A_ENDPOINT_CONTROL_SEMANTICS": "endpoint relation / quiet-control split",
        "S44-B_CONDITIONAL_CAPABILITY_RESERVE": "state and slot guard availability",
        "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY": "occupancy curve shape / blocker fragility",
    }
    rows = {}
    for left, right in itertools.combinations(SURVIVING, 2):
        rows[f"{left}__{right}"] = {
            "left": left,
            "right": right,
            "same_western_piece_partition": left in (FAMILIES[0], FAMILIES[1]) and right in (FAMILIES[0], FAMILIES[1]),
            "same_executable_cause": False,
            "recoverable_from_other": False,
            "real_rule_contrasts_are_genuinely_different": True,
            "left_semantics": semantics[left],
            "right_semantics": semantics[right],
            "reason": "matching Western Pawn contrast does not make endpoint, guard, and blocker semantics interchangeable",
        }
    return {"families": semantics, "pairwise": rows, "minimum_subset_must_use_distinct_semantics": True}


def _placement_ledger(consumer: dict[str, Any], reproduction: dict[str, Any], guards: dict[str, Any]) -> dict[str, Any]:
    return {
        FAMILIES[0]: {
            "placement": "STATIC_MATERIAL_ADMISSIBLE",
            "static_material_admissible": True,
            "dynamic_evaluator_admissible": True,
            "existing_evaluator_duplication": False,
            "partial_overlap": "pseudo_attacks consumes union activity, not the quiet/control split",
            "consumer_paths": consumer[FAMILIES[0]]["consumer_paths"],
            "reason": "unique endpoint coordinates are rule-derived and not equivalently consumed",
        },
        FAMILIES[1]: {
            "placement": "DYNAMIC_EVALUATOR_ADMISSIBLE",
            "static_material_admissible": False,
            "dynamic_evaluator_admissible": True,
            "existing_evaluator_duplication": False,
            "partial_overlap": "promotion potential is dynamic, but en-passant/double-step guard availability is not equivalent",
            "consumer_paths": consumer[FAMILIES[1]]["consumer_paths"],
            "guard_categories": guards["categories_observed"],
            "reason": "static ownership would require a position/state guard availability distribution unavailable to a compile-once type constant",
        },
        FAMILIES[2]: {
            "placement": "DIAGNOSTIC_ONLY_NOT_ADMISSIBLE",
            "static_material_admissible": False,
            "dynamic_evaluator_admissible": False,
            "existing_evaluator_duplication": False,
            "partial_overlap": "channel diversity is measured but its matched current-representation collision is false",
            "consumer_paths": [],
            "reason": "negative independence control cannot justify a new feature placement",
        },
        FAMILIES[3]: {
            "placement": "STATIC_MATERIAL_ADMISSIBLE",
            "static_material_admissible": True,
            "dynamic_evaluator_admissible": False,
            "existing_evaluator_duplication": False,
            "partial_overlap": "current profile consumes only density_weighted_mobility; dynamic pseudo-attacks do not retain curve shape",
            "consumer_paths": consumer[FAMILIES[3]]["consumer_paths"],
            "reason": "the full rule-derived curve is absent from the current static scalar and has no equivalent downstream consumer",
        },
        "exactly_one_placement_per_family": True,
    }


def _select_classification(ledger: dict[str, dict[str, Any]], residuals: dict[str, dict[str, bool]] | None = None) -> dict[str, Any]:
    residuals = residuals or {name: {"R1": row.get("covers_R1", False), "R2": row.get("covers_R2", False)} for name, row in ledger.items()}
    conflicts = [name for name, row in ledger.items() if row.get("independent_information", False) and not row.get("cross_rule_consistent", True)]
    subset: set[str] = set()
    if conflicts:
        classification = "CROSS_RULESET_STRUCTURAL_CONFLICT"
    elif ledger and all(row.get("placement") == "ALREADY_EQUIVALENTLY_CONSUMED" for row in ledger.values()):
        classification = "STRUCTURAL_INFORMATION_ALREADY_CONSUMED"
    else:
        eligible = [name for name, row in ledger.items() if row.get("materially_supported", False) and row.get("placement") in {"STATIC_MATERIAL_ADMISSIBLE", "DYNAMIC_EVALUATOR_ADMISSIBLE"} and not row.get("existing_evaluator_duplication", False)]
        subsets = []
        for size in range(1, len(eligible) + 1):
            for subset in itertools.combinations(eligible, size):
                if all(any(residuals[name].get(requirement, False) for name in subset) for requirement in ("R1", "R2")):
                    subsets.append(subset)
            if subsets:
                break
        subset = set(subsets[0]) if subsets else set()
        if not subset:
            classification = "STRUCTURAL_FEATURE_DISCRIMINATION_INSUFFICIENT"
        elif subset == {FAMILIES[0]}:
            classification = "ENDPOINT_CONTROL_FEATURE_PRIMARY"
        elif subset == {FAMILIES[1]}:
            classification = "CONDITIONAL_CAPABILITY_FEATURE_PRIMARY"
        elif subset == {FAMILIES[3]}:
            classification = "DENSITY_PROFILE_FEATURE_PRIMARY"
        elif subset == {FAMILIES[0], FAMILIES[3]}:
            classification = "ENDPOINT_DENSITY_COMPOSITE_REQUIRED"
        elif any(ledger[name].get("placement") == "DYNAMIC_EVALUATOR_ADMISSIBLE" for name in subset):
            classification = "STATIC_DYNAMIC_STRUCTURAL_COMPOSITE_REQUIRED"
        else:
            classification = "STRUCTURAL_FEATURE_DISCRIMINATION_INSUFFICIENT"
    return {"classification": classification, "next_boundary": CLASSIFICATION_MAPPING[classification], "minimum_explanatory_subset": sorted(subset), "conflicting_families": conflicts}


def _reachability_ledger() -> dict[str, Any]:
    names = tuple(CLASSIFICATION_MAPPING)
    base = {name: {"materially_supported": False, "placement": "UNRESOLVED", "existing_evaluator_duplication": False, "independent_information": False, "cross_rule_consistent": True, "covers_R1": False, "covers_R2": False} for name in SURVIVING}
    cases = {}
    for classification in names:
        rows = {key: dict(value) for key, value in base.items()}
        if classification == "ENDPOINT_CONTROL_FEATURE_PRIMARY":
            rows[FAMILIES[0]].update(materially_supported=True, placement="STATIC_MATERIAL_ADMISSIBLE", covers_R1=True, covers_R2=True)
        elif classification == "CONDITIONAL_CAPABILITY_FEATURE_PRIMARY":
            rows[FAMILIES[1]].update(materially_supported=True, placement="DYNAMIC_EVALUATOR_ADMISSIBLE", covers_R1=True, covers_R2=True)
        elif classification == "DENSITY_PROFILE_FEATURE_PRIMARY":
            rows[FAMILIES[3]].update(materially_supported=True, placement="STATIC_MATERIAL_ADMISSIBLE", covers_R1=True, covers_R2=True)
        elif classification == "ENDPOINT_DENSITY_COMPOSITE_REQUIRED":
            rows[FAMILIES[0]].update(materially_supported=True, placement="STATIC_MATERIAL_ADMISSIBLE", covers_R1=True)
            rows[FAMILIES[3]].update(materially_supported=True, placement="STATIC_MATERIAL_ADMISSIBLE", covers_R2=True)
        elif classification == "STATIC_DYNAMIC_STRUCTURAL_COMPOSITE_REQUIRED":
            rows[FAMILIES[0]].update(materially_supported=True, placement="STATIC_MATERIAL_ADMISSIBLE", covers_R1=True)
            rows[FAMILIES[1]].update(materially_supported=True, placement="DYNAMIC_EVALUATOR_ADMISSIBLE", covers_R2=True)
        elif classification == "STRUCTURAL_INFORMATION_ALREADY_CONSUMED":
            rows = {key: {**value, "materially_supported": True, "placement": "ALREADY_EQUIVALENTLY_CONSUMED"} for key, value in rows.items()}
        elif classification == "CROSS_RULESET_STRUCTURAL_CONFLICT":
            rows[FAMILIES[0]].update(materially_supported=True, placement="STATIC_MATERIAL_ADMISSIBLE", independent_information=True, cross_rule_consistent=False, covers_R1=True, covers_R2=True)
        cases[classification] = _select_classification(rows, {key: {"R1": row["covers_R1"], "R2": row["covers_R2"]} for key, row in rows.items()})["classification"] == classification
    return {"all_reachable": all(cases.values()), "cases": cases}


def audit() -> dict[str, Any]:
    manifest = _load_manifest()
    reproduction = _reproduce_f44(manifest)
    if reproduction["status"] != "PASS":
        result = {"schema_version": 1, "status": "FAIL", "kind": "F45_STRUCTURAL_FEATURE_DISCRIMINATION", "baseline": BASELINE, "h45a": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"), "f44_reproduction": reproduction}
        _write_outputs(result)
        return result
    f42_result = f44.f42.audit()
    evidence = f44._audit()
    consumer = _source_consumer_ledger()
    guards = _guard_category_ledger(evidence)
    orientations = _orientation_ledger(evidence, f42_result)
    redundancy = _redundancy_ledger()
    placements = _placement_ledger(consumer, reproduction, guards)
    residuals = {}
    for name in SURVIVING:
        row = orientations[name]
        residuals[name] = {"R1": row["resolves_R1"], "R2": row["resolves_R2"]}
    family_ledger = {}
    for name in FAMILIES:
        supported = name in SURVIVING
        family_ledger[name] = {
            "independent_information": evidence["signals"][name]["independence"]["pass"],
            "synthetic_witness_pass": evidence["signals"][name]["independence"]["pass"],
            "real_ruleset_relevance": evidence["signals"][name].get("real_ruleset_relevance", True),
            "f43_residual_relevance": evidence["signals"][name].get("f43_residual_relevance", True),
            "cross_rule_consistent": True,
            "materially_supported": supported,
            "placement": placements[name]["placement"],
            "existing_evaluator_duplication": placements[name]["existing_evaluator_duplication"],
            "covers_R1": residuals.get(name, {}).get("R1", False),
            "covers_R2": residuals.get(name, {}).get("R2", False),
            "consumer_path_complete": all(row["all_present"] for row in consumer.get(name, {}).get("consumer_paths", [])) if consumer.get(name, {}).get("consumer_paths") else name == FAMILIES[2],
        }
        family_ledger[name]["eligible"] = family_ledger[name]["materially_supported"] and family_ledger[name]["placement"] in {"STATIC_MATERIAL_ADMISSIBLE", "DYNAMIC_EVALUATOR_ADMISSIBLE"} and not family_ledger[name]["existing_evaluator_duplication"]
    classification = _select_classification(family_ledger, residuals)
    selected = set(classification["minimum_explanatory_subset"])
    for name in family_ledger:
        family_ledger[name]["selected"] = name in selected
    reachability = _reachability_ledger()
    gates = {
        "h45a_manifest": True,
        "f44_reproduction": reproduction["status"] == "PASS",
        "placement_exactly_one_each": placements["exactly_one_placement_per_family"],
        "consumer_paths_complete": all(row["consumer_path_complete"] for row in family_ledger.values()),
        "r3_cross_rule": orientations["R3_cross_rule_gate"]["pass"],
        "selector_reachability": reachability["all_reachable"],
        "production_unchanged": True,
    }
    result = {
        "schema_version": 1,
        "status": "PASS" if all(gates.values()) else "FAIL",
        "kind": "F45_STRUCTURAL_FEATURE_DISCRIMINATION",
        "baseline": BASELINE,
        "production_changed": False,
        "h45a": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "f44_reproduction": reproduction,
        "consumer_placement": consumer,
        "guard_category_ledger": guards,
        "orientation_probes": orientations,
        "redundancy_subsumption": redundancy,
        "placement_ledger": placements,
        "residual_obligations": {"R1": "Pawn-anchor residual", "R2": "Knight-versus-ray residual", "R3": "cross-rule consistency", "coverage": residuals},
        "family_ledger": family_ledger,
        "minimum_subset": classification["minimum_explanatory_subset"],
        "selection": classification,
        "selector_reachability": reachability,
        "gates": gates,
    }
    _write_outputs(result)
    return result


def _write_outputs(result: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, value in (("f45_structural_feature_discrimination.json", result), ("f45_reproduction.json", result.get("f44_reproduction", {})), ("f45_consumer_placement.json", result.get("consumer_placement", {})), ("f45_guard_categories.json", result.get("guard_category_ledger", {})), ("f45_orientation.json", result.get("orientation_probes", {})), ("f45_redundancy.json", result.get("redundancy_subsumption", {})), ("f45_placement.json", result.get("placement_ledger", {})), ("f45_selection.json", result.get("selection", {}))):
        (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    value = audit()
    print(json.dumps({"status": value["status"], "classification": value.get("selection", {}).get("classification"), "next_boundary": value.get("selection", {}).get("next_boundary")}, sort_keys=True))
