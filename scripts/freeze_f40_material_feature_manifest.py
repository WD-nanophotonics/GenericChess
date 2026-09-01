"""Freeze the F40 material and feature-utilization audit before analysis."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "f40_material_feature_manifest.json"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def bind(path: str) -> dict[str, str]:
    return {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


def manifest() -> dict[str, Any]:
    source_paths = [
        "generic_chess/ai/evaluation/profile.py",
        "generic_chess/ai/evaluation/config.py",
        "generic_chess/ai/evaluation/evaluator.py",
        "generic_chess/ai/evaluation/analyzer.py",
        "generic_chess/rules/compiler.py",
        "generic_chess/rules/western_chess.py",
        "generic_chess/rules/standard_shogi.py",
        "generic_chess/learning/material.py",
        "generic_chess/learning/features.py",
        "generic_chess/learning/tdleaf.py",
        "generic_chess/learning/arena.py",
        "generic_chess/learning/experiment.py",
        "generic_chess/learning/selfplay.py",
        "generic_chess/native/compiler.py",
        "generic_chess/native/engine.py",
        "generic_chess/ai/alphabeta/player.py",
        "tests/fixtures/f39_generalization_selection.json",
        "tests/fixtures/f39_component_ablation.json",
        "tests/fixtures/f39_distribution_shift.json",
        "tests/fixtures/f24a_minimal_cheap_evaluator.json",
        "docs/learning_phase1_5_arena_audit.md",
        "docs/learning_phase1_6_signal_diagnostics.md",
        "docs/learning_phase1_7_evaluation_leverage.md",
        "docs/learning_phase1_8_alphasho_positive_control.md",
    ]
    value = {
        "schema_version": 1,
        "kind": "F40_RULE_DERIVED_MATERIAL_AND_FEATURE_UTILIZATION_AUDIT",
        "work_order": "GENERICCHESS-F40-RULE-DERIVED-MATERIAL-AND-FEATURE-UTILIZATION-AUDIT",
        "baseline": {
            "master": "44fce4f9dfeee0ef9480597c7ab34195db984100",
            "sandbox_before_f40": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
            "product_authority": "a389adc50ed42096874ee38f818584978468c6ac",
            "f39_final": "8df63494e9f4f1228d78b851e5fe8866d567fe3b",
            "standard_shogi_fingerprint": "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635",
        },
        "inputs": {path: bind(path) for path in source_paths},
        "constraints": {
            "HUMAN_MATERIAL_REFERENCE_VALIDATION_ONLY": True,
            "NO_FITTING_TO_HUMAN_RATIOS": True,
            "NO_LEARNING_RUN": True,
            "NO_NEW_EVALUATOR_FEATURE": True,
            "PRODUCTION_DIFF_ZERO": True,
            "NO_PRODUCTION_EVALUATOR_SEARCH_NATIVE_RULE_RUNTIME_CHANGE": True,
            "NO_ALPHASHO_EXECUTION": True,
            "NO_PAIRED_BENCHMARK": True,
            "NO_SELF_PLAY_OR_TRAINING": True,
            "NO_COEFFICIENT_FITTING": True,
            "NO_R37_RESCUE_OR_RESELECTION": True,
            "NO_NATIVE_SEARCH_MIGRATION": True,
            "NO_XIANGQI_MATERIAL_CLAIM": True,
        },
        "authoritative_rulesets": ["Western Chess", "Standard Shogi"],
        "recomposition": {
            "required_fields": ["type_identity", "rule_capability_quantities", "raw_capability_score", "normalization_denominator", "normalization_scale", "pre_clamp_integer", "final_board_value", "floor_fired", "upper_clamp_fired", "hand_value", "hand_board_ratio", "promotion_gain", "promotion_base_relation"],
            "exact_gate": "CURRENT_PROFILE_EXACT_RECOMPOSITION",
        },
        "western_reference": {
            "pawn": [1.0, 1.0], "knight": [2.5, 3.5], "bishop": [2.5, 3.75], "rook": [4.0, 6.0], "queen": [7.5, 11.0],
            "ordinal": ["Pawn<Knight", "Pawn<Bishop", "Knight<Rook", "Bishop<Rook", "Rook<Queen"],
            "knight_bishop_ratio": [0.75, 1.25],
            "floor_collapse": "non-anchor at floor and next-smallest non-anchor >= 20 * floor",
            "severe_pathology": "floor collapse OR major ratio > 5 * upper band OR major ratio < lower band / 5 OR ordinal failure",
        },
        "shogi_reference": {
            "pieces": ["pawn", "knight", "lance", "silver", "gold", "bishop", "rook"],
            "healthy_gates": {"cosine_min": 0.95, "spearman_min": 0.90, "pairwise_ordering_min": 0.90},
            "historical_control_approximation": {"cosine": 0.989, "pearson": 0.976, "spearman": 0.952, "pairwise_ordering": 0.965},
        },
        "utilization_ledger": {
            "states": ["SOURCE_RULE_SEMANTIC", "COMPUTED", "STORED", "USED_IN_BOARD_PRIOR", "USED_IN_HAND_PRIOR", "USED_IN_PROMOTION_PRIOR", "USED_BY_PYTHON_EVALUATOR", "COMPILED_INTO_NATIVE_EVALUATION", "AVAILABLE_TO_LEARNING", "COMPUTED_BUT_UNUSED", "COLLAPSED_BY_NORMALIZATION", "UNIFORM_FACTOR_ERASES_VARIATION"],
            "required_signal_families": ["movement_density_capability", "coverage", "reachability", "path_ray", "promotion", "drop_freedom", "drop_mobility", "anchor_structure", "normalization"],
            "meaningful_gap": "computed-but-unused signal has material nonzero variation and semantics unavailable through the final scalar",
        },
        "normalization_audit": ["raw_score_range", "final_score_range", "floor_count", "smallest_positive_ratio", "near_floor_sensitivity", "low_capability_collapse", "uniform_rescale_pairwise_ratio", "integer_rounding_floor_loss"],
        "learning": {
            "historical_findings": ["clean_paired_arena_no_strength_reproduction", "parameter_updates_real", "decision_flip_rate_approximately_0.2_to_2.9_percent", "updates_low_leverage", "global_scale_energy_about_0.531", "shogi_gen0_material_prior_near_reference"],
            "low_leverage_gate": "historical evidence plus current parameter basis demonstrate primarily weak-decision-leverage dimensions",
        },
        "native_sidecar": {"path": ["RuleSet", "compiled_semantics", "Native_rule_evaluation_tables", "NativeSearchEngine", "AlphaBetaPlayer"], "conclusions": ["SECOND_RULE_COMPILER_REQUIRED", "COMPILED_SEMANTIC_RESULTS_UNDERCONSUMED_BY_PRODUCT_SEARCH"]},
        "classification_precedence": [
            "MATERIAL_PRIOR_PATHOLOGY_PRIMARY if severe material pathology and no meaningful utilization gap",
            "MATERIAL_AND_FEATURE_UTILIZATION_GAP if severe material pathology and meaningful utilization gap",
            "FEATURE_UTILIZATION_GAP_PRIMARY if mature material priors healthy and meaningful utilization gap",
            "MATERIAL_PRIOR_HEALTHY_STRUCTURAL_REPRESENTATION_GAP if mature priors healthy and no meaningful precomputed signal wasted",
            "MIXED_OR_UNRESOLVED otherwise",
        ],
        "boundary_mapping": {
            "MATERIAL_PRIOR_PATHOLOGY_PRIMARY": "F41_RULE_DERIVED_MATERIAL_PRIOR_CORRECTIVE",
            "MATERIAL_AND_FEATURE_UTILIZATION_GAP": "F41_RULE_DERIVED_MATERIAL_PRIOR_AND_SIGNAL_UTILIZATION_CORRECTIVE",
            "FEATURE_UTILIZATION_GAP_PRIMARY": "F41_RULE_FEATURE_UTILIZATION_PROTOTYPE",
            "MATERIAL_PRIOR_HEALTHY_STRUCTURAL_REPRESENTATION_GAP": "F41_LEARNABLE_STRUCTURAL_FEATURE_SCHEMA_REASSESSMENT",
            "MIXED_OR_UNRESOLVED": "F41_GENERIC_EVALUATOR_ARCHITECTURE_REASSESSMENT",
        },
        "flags": ["F39_BROAD_TRANSFER_FAILURE_CONSUMED", "MATURE_RULESET_MATERIAL_PRIORS_AUDITED", "PROFILE_NORMALIZATION_PATHOLOGY_AUDITED", "RULE_INFORMATION_UTILIZATION_LEDGER_COMPLETE", "HISTORICAL_LEARNING_LEVERAGE_CONSUMED", "COMPILED_NATIVE_INFORMATION_FLOW_AUDITED", "NEXT_GENERIC_EVALUATOR_FOUNDATION_BOUNDARY_SELECTED"],
    }
    value["manifest_sha256"] = hashlib.sha256(canonical(value).encode()).hexdigest()
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args(argv)
    if not args.freeze:
        parser.error("use --freeze")
    value = manifest()
    OUT.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest_sha256": value["manifest_sha256"], "status": "PASS"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
