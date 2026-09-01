"""Freeze the F39 diagnosis protocol before any new A/B holdout computation."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
OUT = FIXTURES / "f39_generalization_manifest.json"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind(path: str) -> dict[str, str]:
    return {"path": path, "sha256": sha_file(ROOT / path)}


def manifest() -> dict[str, Any]:
    inputs = {
        "f37_ranks": bind("tests/fixtures/f37_evaluator_representation_ranks.json"),
        "f37_search": bind("tests/fixtures/f37_evaluator_search_shadow.json"),
        "f37_selection": bind("tests/fixtures/f37_evaluator_selection.json"),
        "f37_r1": bind("tests/fixtures/f37r1_gate_recertification.json"),
        "h38a_manifest": bind("tests/fixtures/f38_activity_anchor_manifest.json"),
        "h38a_descriptor": bind("tests/fixtures/f38_external_holdout_descriptor.json"),
        "f38_identity": bind("tests/fixtures/f38_activity_anchor_prototype_identity.json"),
        "f38_ranks": bind("tests/fixtures/f38_activity_anchor_holdout_ranks.json"),
        "f38_search": bind("tests/fixtures/f38_activity_anchor_holdout_search.json"),
        "f38_cost": bind("tests/fixtures/f38_activity_anchor_micro_cost.json"),
        "f38_selection": bind("tests/fixtures/f38_activity_anchor_selection.json"),
        "f38_r1": bind("tests/fixtures/f38r1_frozen_r37c_search_parity.json"),
        "evaluator_source": bind("generic_chess/ai/evaluation/evaluator.py"),
        "profile_source": bind("generic_chess/ai/evaluation/profile.py"),
        "config_source": bind("generic_chess/ai/evaluation/config.py"),
    }
    value = {
        "schema_version": 1,
        "kind": "F39_EVALUATOR_REENTRY_GENERALIZATION_DIAGNOSIS",
        "work_order": "GENERICCHESS-F39-EVALUATOR-REENTRY-GENERALIZATION-CORRECTIVE",
        "baseline": {
            "master": "44fce4f9dfeee0ef9480597c7ab34195db984100",
            "sandbox_before_f39": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
            "f38_r1": "c982386983c86b1c8f2798bc6670c76212af9701",
            "f37_final": "6174c773eea1ab40fb57066a8266295ad14ce1f9",
            "product_authority": "a389adc50ed42096874ee38f818584978468c6ac",
            "standard_shogi_fingerprint": "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635",
        },
        "inputs": inputs,
        "constraints": {
            "NO_HOLDOUT_DRIVEN_CANDIDATE_SELECTION": True,
            "NO_TUNING_FROM_F38_LABELS": True,
            "ALPHASHO_ACTION_IS_VALIDATION_LABEL_NOT_ORACLE": True,
            "PRODUCTION_DIFF_ZERO": True,
            "NO_ALPHASHO_EXECUTION": True,
            "NO_PAIRED_BENCHMARK_RERUN": True,
            "NO_HOLDOUT_RESELECTION": True,
            "NO_NEW_EXTERNAL_LABELS": True,
            "NO_COEFFICIENT_FITTING": True,
            "NO_FEATURE_TUNING": True,
            "NO_PRODUCTION_EVALUATOR_SEARCH_NATIVE_RULE_RUNTIME_CHANGE": True,
        },
        "rank_protocol": {
            "evaluators": ["V1", "R37A", "R37B", "R37C"],
            "deterministic_rank": "score descending, then canonical action key ascending",
            "strict_rank": "1 + count(score strictly greater than target score)",
            "tie_span_low": "strict_rank",
            "tie_span_high": "count(score greater than or equal to target score)",
            "rank_percentile": "strict_rank / legal_action_count",
            "margin_from_top": "top_score - target_score",
            "normalized_margin": "margin_from_top / max(1, median_non_anchor_board_value)",
            "material_normalized_margin_delta": 0.01,
            "material_deterministic_rank_delta": 3,
            "row_classification_precedence": [
                "MATERIAL_VALUE_WORSENING: strict_rank_delta > 0 and normalized_margin_delta >= 0.01",
                "RANK_TIE_INSTABILITY: deterministic_rank_delta >= 3 and strict_rank_delta == 0 and normalized_margin_delta < 0.01",
                "MIXED_RANK_AND_MARGIN: exactly one of strict_rank_delta > 0 and normalized_margin_delta >= 0.01",
                "UNCHANGED_OR_IMPROVED: otherwise",
            ],
        },
        "component_protocol": {
            "allowed_counterfactuals": ["V1", "R37A", "R37B", "R37C"],
            "required_terms": ["board_material", "hand_inventory", "promotion_potential", "global_pseudo_control", "anchor_escape", "check_penalty", "raw_total", "side_to_move_score"],
            "additivity": "R37C_score - V1_score == (R37A_score - V1_score) + (R37B_score - V1_score)",
            "causal_label_precedence": [
                "TIE_STRUCTURE_DOMINATED if row classification is RANK_TIE_INSTABILITY",
                "BOTH_SAME_DIRECTION if activity and anchor normalized target-vs-V1-top margin effects are both >= 0.01",
                "ACTIVITY_DRIVEN if activity >= 0.01 and anchor < 0.01",
                "ANCHOR_DRIVEN if anchor >= 0.01 and activity < 0.01",
                "COMPONENTS_OPPOSE if effects have opposite signs and either absolute effect >= 0.01",
                "UNRESOLVED otherwise",
            ],
        },
        "distribution_protocol": {
            "quantities": ["legal_action_count", "board_occupancy", "total_hand_inventory", "drop_action_fraction", "capture_action_fraction", "promotion_action_fraction", "checking_action_fraction", "in_check", "material_imbalance_magnitude", "v1_pseudo_control", "activity_term", "v1_anchor_escape", "anchor_ring_term", "legal_child_term_ranges"],
            "summary": "median and IQR per F37/F38 corpus",
            "pooled_iqr": "max(1.0, (IQR_F37 + IQR_F38) / 2)",
            "material_shift": "non-overlapping IQR or absolute median delta / pooled_iqr >= 1",
        },
        "action_strata": ["board/drop", "capture/non-capture", "promotion/non-promotion", "checking/non-checking", "anchor-actor/non-anchor-actor"],
        "component_search_protocol": {"only_missing_counterfactuals": ["R37A", "R37B"], "holdout_prefix": 10, "nodes": 2048, "max_depth": 8, "qdepth": 4, "qhard": 8, "fresh_tt": True, "native_legality_requested": True, "no_512_rerun": True, "no_wall_time_run": True, "no_v1_or_r37c_rerun": True},
        "aggregate_classification_precedence": [
            "ACTIVITY_NEGATIVE_TRANSFER: A strict rank and normalized margin both worse than V1, and C is not better than B on both",
            "ANCHOR_NEGATIVE_TRANSFER: B strict rank and normalized margin both worse than V1, and C is not better than A on both",
            "COMBINATION_NEGATIVE_TRANSFER: A and B do not both materially worsen, but C does",
            "METRIC_INSTABILITY_PRIMARY: majority deterministic regressions are RANK_TIE_INSTABILITY and C mean normalized margin does not worsen by 0.01",
            "BROAD_REPRESENTATION_TRANSFER_FAILURE: A, B, and C all lack positive transfer on both strict rank and normalized margin",
            "MIXED_OR_UNRESOLVED: otherwise",
        ],
        "boundary_mapping": {"METRIC_INSTABILITY_PRIMARY": "F40_EVALUATOR_VALIDATION_METRIC_AND_HOLDOUT_REASSESSMENT", "ACTIVITY_NEGATIVE_TRANSFER": "F40_RULE_DERIVED_DYNAMIC_FEATURE_REDESIGN", "ANCHOR_NEGATIVE_TRANSFER": "F40_RULE_DERIVED_DYNAMIC_FEATURE_REDESIGN", "COMBINATION_NEGATIVE_TRANSFER": "F40_RULE_DERIVED_DYNAMIC_FEATURE_REDESIGN", "BROAD_REPRESENTATION_TRANSFER_FAILURE": "F40_RULE_DERIVED_MATERIAL_AND_FEATURE_UTILIZATION_AUDIT", "MIXED_OR_UNRESOLVED": "F40_GENERIC_EVALUATOR_ARCHITECTURE_REASSESSMENT"},
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
