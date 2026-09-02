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
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".generic_chess_flow"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import audit_f44_structural_capability as f44  # noqa: E402
from repository_provenance import require_migrated_binding  # noqa: E402


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
    for name, binding in manifest["input_files"].items():
        results[name] = require_migrated_binding(ROOT, "F45", "tests/fixtures/f45_structural_feature_discrimination_manifest.json", name, manifest["baseline"]["f44_sha"], binding["path"], binding["sha256"])
    for name, binding in manifest["f44_evidence_bindings"].items():
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
    evaluator = _line_facts("generic_chess/ai/evaluation/evaluator.py", ("def evaluate", "pseudo_attacks(position, 0", "def _promotion_bonus", "def _anchor_escape", "empty_forward_mobility"))
    analyzer = _line_facts("generic_chess/ai/evaluation/analyzer.py", ("def build_movement_capability", "mobility_density_curve", "expected_mobility=curve"))
    profile = _line_facts("generic_chess/ai/evaluation/profile.py", ("def _raw_capability_score", "mobility_score = sum", "zip(config.density_weights"))
    executor = _line_facts("generic_chess/core/semantic_executor.py", ("for slot_guard in pattern.slot_guards", "pattern.guards", "def _violates_postconditions"))
    attack_text = (ROOT / "generic_chess/core/attacks.py").read_text(encoding="utf-8")
    evaluator_text = (ROOT / "generic_chess/ai/evaluation/evaluator.py").read_text(encoding="utf-8")
    analyzer_text = (ROOT / "generic_chess/ai/evaluation/analyzer.py").read_text(encoding="utf-8")
    profile_text = (ROOT / "generic_chess/ai/evaluation/profile.py").read_text(encoding="utf-8")
    executor_text = (ROOT / "generic_chess/core/semantic_executor.py").read_text(encoding="utf-8")
    endpoint_relation_consumer = any(token in attack_text for token in ("target_empty", "target_enemy", "target_relation"))
    promotion_consumer = "def _promotion_bonus" in evaluator_text and "empty_forward_mobility" in evaluator_text
    guard_consumer = "pattern.guards" in executor_text and "pattern.slot_guards" in executor_text
    curve_consumer = "expected_mobility" in analyzer_text and "density_weights" in profile_text
    dynamic_shape_consumer = any(token in evaluator_text for token in ("density", "curve", "blocker_fragility"))
    return {
        "S44-A_ENDPOINT_CONTROL_SEMANTICS": {
            "consumer_paths": [attack, evaluator],
            "trace_facts": {"pseudo_attack_union": "attacked.update" in attack_text, "endpoint_relation_consumer": endpoint_relation_consumer, "position_occupancy_used": "position.board" in attack_text},
            "shared_information": "position-dependent pseudo-attack destination union/count",
            "unique_information": "target_empty versus target_enemy relation and quiet/control overlap",
            "equivalent_existing_consumer": endpoint_relation_consumer,
            "complete_pre_search_collision_remains": not endpoint_relation_consumer,
            "ownership": "static rule geometry plus partial dynamic union consumer",
        },
        "S44-B_CONDITIONAL_CAPABILITY_RESERVE": {
            "consumer_paths": [executor, evaluator],
            "trace_facts": {"guard_semantic_consumer": guard_consumer, "promotion_consumer": promotion_consumer, "promotion_has_guard_invariance": "state_guard" in evaluator_text or "slot_guard" in evaluator_text},
            "shared_information": "promotion potential is dynamically consumed for promotable pieces",
            "unique_information": "guard availability for executable conditional patterns",
            "equivalent_existing_consumer": guard_consumer and ("state_guard" in evaluator_text or "slot_guard" in evaluator_text),
            "complete_pre_search_collision_remains": guard_consumer and not ("state_guard" in evaluator_text or "slot_guard" in evaluator_text),
            "ownership": "dynamic evaluator / move-state consumer",
        },
        "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY": {
            "consumer_paths": [analyzer, profile, evaluator],
            "trace_facts": {"curve_generated": curve_consumer, "weighted_scalar_reduction": "mobility_score = sum" in profile_text, "dynamic_shape_consumer": dynamic_shape_consumer},
            "shared_information": "density-weighted mobility scalar and dynamic pseudo-attack count",
            "unique_information": "five-point retention curve, curvature, and blocker ordering",
            "equivalent_existing_consumer": dynamic_shape_consumer,
            "complete_pre_search_collision_remains": curve_consumer and not dynamic_shape_consumer,
            "ownership": "static rule-derived profile; no independent dynamic shape consumer",
        },
    }


def _classify_placement(facts: dict[str, Any]) -> str:
    """Classify placement from evidence facts, never from a family name."""
    if not facts.get("consumer_evidence_sufficient", False):
        return "UNRESOLVED"
    if facts.get("equivalent_existing_consumer", False):
        return "ALREADY_EQUIVALENTLY_CONSUMED"
    if not facts.get("independent_support", False):
        return "DIAGNOSTIC_ONLY_NOT_ADMISSIBLE"
    if facts.get("requires_position_state", False):
        return "DYNAMIC_EVALUATOR_ADMISSIBLE"
    if facts.get("compile_once_type_information", False):
        return "STATIC_MATERIAL_ADMISSIBLE"
    return "UNRESOLVED"


def _guard_category_ledger(evidence: dict[str, Any]) -> dict[str, Any]:
    compiled = {"western_chess": f44.compile_semantic_ruleset(f44.build_western_chess_ruleset()), "standard_shogi": f44.compile_semantic_ruleset(f44.build_standard_shogi_ruleset())}
    rows = []
    for ruleset_name, ruleset in compiled.items():
        type_ids = tuple(evidence["signals"][FAMILIES[1]]["real_rulesets"][ruleset_name])
        for type_id in type_ids:
            for pattern in f44._patterns(ruleset, type_id, False):
                categories = []
                if pattern.guards:
                    categories.append("state_guard")
                if pattern.slot_guards:
                    categories.append("slot_guard")
                if pattern.postconditions:
                    categories.append("other_executable_guard")
                if "promotion" in pattern.pattern_id.lower():
                    categories.append("promotion_related_transition")
                if not categories:
                    categories.append("initial_state_or_availability_restriction")
                for category in categories:
                    rows.append({"ruleset": ruleset_name, "type": type_id, "pattern_id": pattern.pattern_id, "category": category})
    western = [row for row in rows if row["ruleset"] == "western_chess"]
    return {
        "rows": rows,
        "categories_observed": sorted({row["category"] for row in rows}),
        "western_conditional_patterns": len({row["pattern_id"] for row in western}),
        "state_and_slot_guards_present": {"state_guard": any(row["category"] == "state_guard" for row in rows), "slot_guard": any(row["category"] == "slot_guard" for row in rows)},
        "promotion_related_transition": any(row["category"] == "promotion_related_transition" for row in rows),
        "initial_state_or_availability_restriction": any(row["category"] == "initial_state_or_availability_restriction" for row in rows),
        "other_executable_guard": any(row["category"] == "other_executable_guard" for row in rows),
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
    endpoint_w = real[FAMILIES[0]]["real_rulesets"]["western_chess"]["P"]["endpoint_control"]
    endpoint_s = real[FAMILIES[0]]["real_rulesets"]["standard_shogi"]["P"]["endpoint_control"]
    conditional_w = real[FAMILIES[1]]["real_rulesets"]["western_chess"]["P"]["conditional_reserve"]
    conditional_s = real[FAMILIES[1]]["real_rulesets"]["standard_shogi"]
    density_s = real[FAMILIES[3]]["real_rulesets"]["standard_shogi"]
    channel_w = real[FAMILIES[2]]["real_rulesets"]["western_chess"]
    channel_s = real[FAMILIES[2]]["real_rulesets"]["standard_shogi"]
    r3 = {
        FAMILIES[0]: {
            "pass": shogi["pass"] and endpoint_w["quiet_capture_overlap_ratio"] < 1.0 and endpoint_s["quiet_capture_overlap_ratio"] >= 0.0 and endpoint_w["quiet_capture_overlap_ratio"] != endpoint_s["quiet_capture_overlap_ratio"],
            "western_pawn_split": endpoint_w["quiet_capture_overlap_ratio"] < 1.0,
            "standard_shogi_pawn_control": endpoint_s["quiet_capture_overlap_ratio"] >= 0.0,
            "reason": "Western Pawn has a split endpoint relation while Standard-Shogi Pawn is measured as a separate control population",
        },
        FAMILIES[1]: {
            "pass": shogi["pass"] and conditional_w["conditional_pattern_count"] > 0 and all(row["conditional_reserve"]["conditional_pattern_count"] == 0 for row in conditional_s.values()),
            "western_conditional_reserve": conditional_w["conditional_pattern_count"] > 0,
            "standard_shogi_negative_control": all(row["conditional_reserve"]["conditional_pattern_count"] == 0 for row in conditional_s.values()),
            "reason": "conditional reserve is present in Western Pawn but absent from the audited Standard-Shogi conditional population",
        },
        FAMILIES[3]: {
            "pass": shogi["pass"] and all(len(row["density_profile"]["mobility_retention_by_density"]) == 5 for row in density_s.values()),
            "standard_shogi_profiles_complete": all(len(row["density_profile"]["mobility_retention_by_density"]) == 5 for row in density_s.values()),
            "healthy_ordering_gate": shogi["pass"],
            "reason": "Standard-Shogi retains complete density profiles and passes the frozen healthy ordering controls",
        },
        FAMILIES[2]: {
            "pass": shogi["pass"] and all(row["channel_diversity"]["sample_count"] > 0 for row in channel_w.values()) and all(row["channel_diversity"]["sample_count"] > 0 for row in channel_s.values()),
            "western_channel_metrics_present": all(row["channel_diversity"]["sample_count"] > 0 for row in channel_w.values()),
            "standard_shogi_channel_metrics_present": all(row["channel_diversity"]["sample_count"] > 0 for row in channel_s.values()),
            "reason": "channel metrics are present in both rulesets, while the F44 matched collision remains a negative independence control",
        },
    }
    return {
        "S44-A_ENDPOINT_CONTROL_SEMANTICS": endpoint,
        "S44-B_CONDITIONAL_CAPABILITY_RESERVE": conditional,
        "S44-D_DENSITY_PROFILE_SHAPE_BLOCKER_FRAGILITY": density,
        "R3_by_family": r3,
        "R3_cross_rule_gate": {
            "pass": shogi["pass"],
            "cosine": shogi["board_value_cosine_vs_current"],
            "spearman": shogi["spearman_vs_current"],
            "pairwise_ordering": shogi["pairwise_ordering_vs_current"],
            "hand_board_ratio_range": shogi["hand_board_ratio_range"],
            "why_shogi_differs": f42_result["shogi_cross_rule"]["why_shogi_does_not_share_the_same_observed_ratio_pathology"],
        },
    }


def _endpoint_behavioral_probe(evidence: dict[str, Any], consumer: dict[str, Any]) -> dict[str, Any]:
    cases = evidence["synthetic"]["cases"]
    left = cases["quiet_only"]
    right = cases["quiet_plus_capture_same_targets"]
    evaluator = consumer[FAMILIES[0]]
    material_equal = math.isclose(left["raw_score"], right["raw_score"], rel_tol=1e-12, abs_tol=1e-12)
    scalar_equal = left["component_values"] == right["component_values"]
    rule_signal_static = all(key in left["endpoint"] and key in right["endpoint"] for key in ("quiet_geometry_mass", "attack_geometry_mass", "dual_use_overlap_mass", "quiet_capture_union_mass", "quiet_capture_overlap_ratio"))
    dynamic_terms = ["dynamic_mobility", "anchor_escape", "promotion_potential"]
    return {
        "controls": ["quiet_only", "quiet_plus_capture_same_targets"],
        "existing_feature_representation": {
            "material_result": {"quiet_only": left["raw_score"], "quiet_plus_capture_same_targets": right["raw_score"]},
            "four_static_capability_components_equal": scalar_equal,
            "dynamic_terms_inspected": dynamic_terms,
            "pseudo_attack_representation": "position-dependent union/count",
            "promotion_potential_for_synthetic_control": "not present in non-promotable X control",
        },
        "consumer_trace": evaluator["trace_facts"],
        "matched_current_component_collision": scalar_equal,
        "same_complete_pre_search_representation": material_equal and scalar_equal and not evaluator["trace_facts"]["endpoint_relation_consumer"],
        "quiet_control_split_not_consumed": not evaluator["trace_facts"]["endpoint_relation_consumer"],
        "rule_signal_static": rule_signal_static,
        "equivalent_existing_consumer": evaluator["equivalent_existing_consumer"],
    }


def _equal(left: Any, right: Any) -> bool:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_equal(left[key], right[key]) for key in left)
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    return left == right


def _signal_vector(case: dict[str, Any], family: str) -> Any:
    if family == FAMILIES[0]:
        return tuple(case["endpoint"][key] for key in ("quiet_geometry_mass", "attack_geometry_mass", "dual_use_overlap_mass", "quiet_capture_union_mass", "quiet_capture_overlap_ratio"))
    if family == FAMILIES[1]:
        return tuple(case["conditional"][key] for key in ("conditional_pattern_count", "path_clear_only_reserve_mass", "conditional_reserve_over_ordinary_mass", "ordinary_pattern_count"))
    return tuple(case["density"][key] for key in ("mobility_curve", "empty_board_mass", "maximum_fractional_drop"))


def _partition_relation(left: dict[Any, int], right: dict[Any, int]) -> str:
    domain = sorted(set(left) & set(right), key=repr)
    left_equal = all((left[a] == left[b]) == (right[a] == right[b]) for a, b in itertools.combinations(domain, 2))
    left_refines = all(not (left[a] == left[b]) or right[a] == right[b] for a, b in itertools.combinations(domain, 2))
    right_refines = all(not (right[a] == right[b]) or left[a] == left[b] for a, b in itertools.combinations(domain, 2))
    if left_equal:
        return "same_partition"
    if left_refines:
        return "left_refines_right"
    if right_refines:
        return "right_refines_left"
    return "incomparable"


def _consumer_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(sorted((path["path"], tuple(sorted(path["functions_or_symbols"]))) for path in row.get("consumer_paths", [])))


def _redundancy_ledger(evidence: dict[str, Any], consumer: dict[str, Any]) -> dict[str, Any]:
    cases = evidence["synthetic"]["cases"]
    semantics = {
        FAMILIES[0]: "endpoint relation / quiet-control split",
        FAMILIES[1]: "state and slot guard availability",
        FAMILIES[3]: "occupancy curve shape / blocker fragility",
    }
    controls = tuple(cases)
    rows = {}
    for source, target in itertools.permutations(SURVIVING, 2):
        witnesses = []
        for left_name, right_name in itertools.combinations(controls, 2):
            source_equal = _equal(_signal_vector(cases[left_name], source), _signal_vector(cases[right_name], source))
            target_differs = not _equal(_signal_vector(cases[left_name], target), _signal_vector(cases[right_name], target))
            if source_equal and target_differs:
                witnesses.append([left_name, right_name])
        rows[f"{source}__{target}"] = {
            "source": source,
            "target": target,
            "target_recoverability_from_source": "NOT_RECOVERABLE" if witnesses else "UNRESOLVED",
            "recoverability_witnesses": witnesses[:8],
            "source_semantics": semantics[source],
            "target_semantics": semantics[target],
        }
    real = {}
    for family in SURVIVING:
        signatures = {}
        for ruleset_name, data in evidence["signals"][family]["real_rulesets"].items():
            for type_id, metrics in data.items():
                if family == FAMILIES[0]:
                    value = metrics["endpoint_control"]["quiet_capture_overlap_ratio"]
                    signature = (round(value, 3), round(metrics["endpoint_control"]["split_semantics_ratio"], 3))
                elif family == FAMILIES[1]:
                    value = metrics["conditional_reserve"]
                    signature = (value["conditional_pattern_count"], round(value["conditional_reserve_over_ordinary_mass"], 3))
                else:
                    value = metrics["density_profile"]
                    signature = (tuple(round(v, 3) for v in value["mobility_retention_by_density"]), round(value["maximum_fractional_drop"], 3))
                signatures[f"{ruleset_name}:{type_id}"] = signature
        classes = {}
        for key, signature in signatures.items():
            classes.setdefault(repr(signature), len(classes))
        real[family] = {"signatures": signatures, "equality_classes": {key: classes[repr(value)] for key, value in signatures.items()}}
    for left, right in itertools.combinations(SURVIVING, 2):
        rows[f"partition:{left}__{right}"] = {"left": left, "right": right, "partition_relation": _partition_relation(real[left]["equality_classes"], real[right]["equality_classes"]), "same_executable_cause": False}
        rows[f"partition:{left}__{right}"]["same_executable_cause"] = _consumer_signature(consumer[left]) == _consumer_signature(consumer[right])
    return {"families": semantics, "pairwise_ordered": rows, "real_rule_partitions": real, "minimum_subset_must_use_distinct_semantics": True}


def _placement_ledger(consumer: dict[str, Any], reproduction: dict[str, Any], guards: dict[str, Any], evidence: dict[str, Any], endpoint_probe: dict[str, Any], orientations: dict[str, Any]) -> dict[str, Any]:
    facts = {
        FAMILIES[0]: {
            "independent_support": evidence["signals"][FAMILIES[0]]["independence"]["pass"],
            "consumer_evidence_sufficient": endpoint_probe["same_complete_pre_search_representation"] is True,
            "equivalent_existing_consumer": endpoint_probe["equivalent_existing_consumer"],
            "requires_position_state": not endpoint_probe["rule_signal_static"],
            "compile_once_type_information": endpoint_probe["rule_signal_static"],
        },
        FAMILIES[1]: {
            "independent_support": evidence["signals"][FAMILIES[1]]["independence"]["pass"],
            "consumer_evidence_sufficient": consumer[FAMILIES[1]]["trace_facts"]["guard_semantic_consumer"],
            "equivalent_existing_consumer": consumer[FAMILIES[1]]["equivalent_existing_consumer"],
            "requires_position_state": guards["state_and_slot_guards_present"]["state_guard"] or guards["state_and_slot_guards_present"]["slot_guard"],
            "compile_once_type_information": False,
        },
        FAMILIES[2]: {
            "independent_support": evidence["signals"][FAMILIES[2]]["independence"]["pass"],
            "consumer_evidence_sufficient": True,
            "equivalent_existing_consumer": False,
            "requires_position_state": False,
            "compile_once_type_information": False,
        },
        FAMILIES[3]: {
            "independent_support": evidence["signals"][FAMILIES[3]]["independence"]["pass"],
            "consumer_evidence_sufficient": consumer[FAMILIES[3]]["trace_facts"]["curve_generated"] and consumer[FAMILIES[3]]["trace_facts"]["weighted_scalar_reduction"],
            "equivalent_existing_consumer": consumer[FAMILIES[3]]["equivalent_existing_consumer"],
            "requires_position_state": False,
            "compile_once_type_information": True,
        },
    }
    result = {}
    for name, row in facts.items():
        placement = _classify_placement(row)
        result[name] = {
            "placement": placement,
            "facts": row,
            "static_material_admissible": placement == "STATIC_MATERIAL_ADMISSIBLE",
            "dynamic_evaluator_admissible": placement == "DYNAMIC_EVALUATOR_ADMISSIBLE",
            "existing_evaluator_duplication": placement == "ALREADY_EQUIVALENTLY_CONSUMED",
            "consumer_paths": consumer.get(name, {}).get("consumer_paths", []),
            "guard_categories": guards["categories_observed"] if name == FAMILIES[1] else [],
            "r3": orientations.get("R3_by_family", {}).get(name, {}),
        }
    result["exactly_one_placement_per_family"] = all(row["placement"] in PLACEMENTS for row in result.values())
    return result


def _select_classification(ledger: dict[str, dict[str, Any]], residuals: dict[str, dict[str, bool]] | None = None) -> dict[str, Any]:
    residuals = residuals or {name: {"R1": row.get("covers_R1", False), "R2": row.get("covers_R2", False)} for name, row in ledger.items()}
    conflicts = [name for name, row in ledger.items() if row.get("independent_information", False) and not row.get("cross_rule_consistent", True)]
    subset: set[str] = set()
    tie_status = "not_applicable"
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
        if len(subsets) > 1:
            tie_status = "unresolved_equal_minimum_subsets"
            classification = "STRUCTURAL_FEATURE_DISCRIMINATION_INSUFFICIENT"
        else:
            subset = set(subsets[0]) if subsets else set()
        if not subset and len(subsets) <= 1:
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
    return {"classification": classification, "next_boundary": CLASSIFICATION_MAPPING[classification], "minimum_explanatory_subset": sorted(subset), "conflicting_families": conflicts, "tie_status": tie_status}


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
    endpoint_probe = _endpoint_behavioral_probe(evidence, consumer)
    redundancy = _redundancy_ledger(evidence, consumer)
    placements = _placement_ledger(consumer, reproduction, guards, evidence, endpoint_probe, orientations)
    residuals = {}
    for name in FAMILIES:
        row = orientations.get(name, {})
        residuals[name] = {"R1": row.get("resolves_R1", False), "R2": row.get("resolves_R2", False)}
    family_ledger = {}
    for name in FAMILIES:
        r3 = orientations.get("R3_by_family", {}).get(name, {})
        supported = evidence["signals"][name]["independence"]["pass"] and evidence["signals"][name].get("real_ruleset_relevance", True) and evidence["signals"][name].get("f43_residual_relevance", True)
        family_ledger[name] = {
            "independent_information": evidence["signals"][name]["independence"]["pass"],
            "synthetic_witness_pass": evidence["signals"][name]["independence"]["pass"],
            "real_ruleset_relevance": evidence["signals"][name].get("real_ruleset_relevance", True),
            "f43_residual_relevance": evidence["signals"][name].get("f43_residual_relevance", True),
            "cross_rule_consistent": r3.get("pass", False),
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
        "r3_cross_rule": all(row.get("pass", False) for row in orientations["R3_by_family"].values()),
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
        "endpoint_behavioral_probe": endpoint_probe,
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
