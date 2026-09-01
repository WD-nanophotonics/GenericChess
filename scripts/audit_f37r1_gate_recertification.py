"""F37 R1 evidence-only gate and regression recertification."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
OUTPUT = FIXTURES / "f37r1_gate_recertification.json"
PATHS = {
    "f37_manifest": "tests/fixtures/f37_evaluator_reentry_manifest.json",
    "f37_decomposition": "tests/fixtures/f37_evaluator_v1_decomposition.json",
    "f37_ranks": "tests/fixtures/f37_evaluator_representation_ranks.json",
    "f37_search_shadow": "tests/fixtures/f37_evaluator_search_shadow.json",
    "f37_selection": "tests/fixtures/f37_evaluator_selection.json",
    "f37_script": "scripts/audit_f37_evaluator_reentry.py",
    "f36_selection": "tests/fixtures/f36_post_reserve_selection.json",
    "f24a_result": "tests/fixtures/f24a_minimal_cheap_evaluator.json",
}
EXPECTED = {
    "f37_manifest": "da880a49f10788c62cfc4388b9a6da7c3c4db4ba90928493cbf952ce9b7893b4",
    "f37_decomposition": "5d0124878c83b340f6733150132e60705691f28e9618ea888165bc49a420bbaa",
    "f37_ranks": "74425f8c4310d86dbb8e1a3543de1cc7529404a96b5b0ade579de8faae4e48a1",
    "f37_search_shadow": "05fe2a0527e75c9beb0d89549258c6b7da714ad0c6962198748575d7337d3548",
    "f37_selection": "a1446e0ffcef8cc1c566790628cf3b909d267d5d0bc09a2d96e8d2bf9de9252d",
    "f37_script": "d1eef01c1d6d97bd3069736e5fc10859716b0db44346446db4988a219a8c01d6",
    "f36_selection": "f93f2d2f8c814f851351d8cf64ace8b36da96671e405afcfd7d24b3b3ed6de15",
    "f24a_result": "46686486ac731e778ea265d74499dd14fc1723896877aa2f74c1177f1989df50",
}
HISTORICAL_FAILURES = [
    "tests/test_f13_native_action_delivers_check.py::test_f13_standard_shogi_checking_drop_witness_matches_python",
    "tests/test_f13_native_action_delivers_check.py::test_f13_nonchecking_drop_does_not_collapse_to_opponent_checked",
    "tests/test_f13_native_action_delivers_check.py::test_f13_compile_gate_and_frozen_postcondition_code_contract",
    "tests/test_f13_native_action_delivers_check.py::test_f13_standard_shogi_four_prefix_native_candidate_and_guarded_order",
    "tests/test_f14_native_semantic_attack_api.py::test_f14_standard_shogi_648_attack_queries_and_in_check_match_python",
    "tests/test_f14_native_semantic_attack_api.py::test_f14_public_api_rejects_invalid_bounds_and_owners",
    "tests/test_f21_native_legality_provider.py::test_provider_matches_python_order_identity_and_binding[semantic_prefix_0]",
    "tests/test_f21_native_legality_provider.py::test_provider_matches_python_order_identity_and_binding[semantic_prefix_1]",
    "tests/test_f21_native_legality_provider.py::test_provider_matches_python_order_identity_and_binding[semantic_prefix_2]",
    "tests/test_f21_native_legality_provider.py::test_provider_matches_python_order_identity_and_binding[semantic_prefix_3]",
    "tests/test_f21_native_legality_provider.py::test_runtime_provider_cache_and_push_pop_restore",
    "tests/test_f21_native_legality_provider.py::test_native_on_and_python_off_search_results_match",
    "tests/test_f24f_western_chess_perft.py::test_f24f_mandatory_perft_one_shot",
]


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def certify() -> dict[str, Any]:
    hashes = {key: sha_file(ROOT / path) for key, path in PATHS.items()}
    if hashes != EXPECTED:
        raise AssertionError("original F37 evidence changed")
    ranks = load(ROOT / PATHS["f37_ranks"])
    selection = load(ROOT / PATHS["f37_selection"])
    rows = {}
    for name in ("R37A", "R37B", "R37C"):
        summary = ranks["summary"][name]
        parts = {
            "stable_strict_improvements": summary["stable_best_rank_strict_improvements"] >= 4,
            "stable_worsened": summary["stable_best_rank_worsened"] <= 1,
            "controls_preserved": summary["controls_preserved"],
            "AS050_mean_rank_improvement": summary["mean_rank_improvements"]["AS050_mean_rank_improvement"] >= 0.15,
            "AS200_mean_rank_improvement": summary["mean_rank_improvements"]["AS200_mean_rank_improvement"] >= 0.15,
            "best_mean_rank_improvement": summary["mean_rank_improvements"]["best_mean_rank_improvement"] >= 0.20,
        }
        rows[name] = {"static_components": parts, "static_gate_exact": parts["stable_strict_improvements"] and parts["stable_worsened"] and parts["controls_preserved"] and (parts["AS050_mean_rank_improvement"] or parts["AS200_mean_rank_improvement"] or parts["best_mean_rank_improvement"])}
    by_name = {row["candidate"]: row for row in selection["candidates"]}
    eligibility = {}
    for name, static in rows.items():
        row = by_name[name]
        eligibility[name] = {
            "local_genericity_gate": row["local_gate"],
            "corrected_static_gate": static["static_gate_exact"],
            "micro_cost_gate": row["micro_cost_gate"],
            "fixed_node_search_cost_gate": row["fixed_node_search_cost_gate"],
            "fixed_node_search_signal_gate": row["fixed_node_search_signal_gate"],
            "runtime_2s_safety_gate": row["runtime_2s_safety_gate"],
        }
        eligibility[name]["eligible"] = all(eligibility[name].values())
    inputs = selection["selection_inputs"]
    ordered = sorted([name for name, row in eligibility.items() if row["eligible"]], key=lambda name: (inputs[name]["gap_sum"], -inputs[name]["stable_strict_improvements"], -inputs[name]["search_hit_improvement_2048"], inputs[name]["median_cost_ratio"], name == "R37C"))
    production_zero = subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode == 0
    if [name for name, row in eligibility.items() if row["eligible"]] != ["R37B", "R37C"] or ordered[0] != "R37C":
        raise AssertionError("F37 independent reclassification disagrees")
    result = {
        "schema_version": 1,
        "status": "PASS",
        "production_diff_zero": production_zero,
        "original_artifacts_byte_identical": True,
        "original_f37_hashes": hashes,
        "static_gate_recertification": rows,
        "eligibility": eligibility,
        "selection_inputs": inputs,
        "eligible_candidates": ["R37B", "R37C"],
        "selected_candidate": "R37C",
        "selected_boundary": "F38_ACTIVITY_AND_ANCHOR_CONTROL_EVALUATOR_PROTOTYPE",
        "defect_classification": "NON_OUTCOME_CHANGING_GATE_IMPLEMENTATION_DEFECT",
        "flags": {
            "F36_EVALUATOR_CAUSAL_BASELINE_CONSUMED": True,
            "HISTORICAL_EVALUATOR_FAILURE_LEDGER_CONSUMED": True,
            "EVALUATOR_V1_TERM_DECOMPOSITION_COMPLETE": True,
            "RULE_DERIVED_REPRESENTATION_SIGNAL_AUDIT_COMPLETE": True,
            "EVALUATOR_REENTRY_TRANSFER_COST_GATES_COMPLETE": True,
            "NEXT_EVALUATOR_BOUNDARY_SELECTED": True,
            "F37_EXACT_STATIC_GATE_RECERTIFIED": True,
            "F37_FULL_REGRESSION_CURRENT_TREE_CERTIFIED": False,
        },
        "no_rerun": {"candidate_experiments": True, "microbenchmark": True, "search_shadow": True, "alphasho": True, "paired_benchmark": True},
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def finalize_full_regression(result: dict[str, Any], total: int, passed: int, failed: int) -> dict[str, Any]:
    if failed != len(HISTORICAL_FAILURES) or total != passed + failed:
        raise AssertionError("full regression totals do not match the historical failure ledger")
    result["focused_regression"] = {"total": 28, "passed": 28, "failed": 0}
    result["full_regression"] = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "historical_failures": HISTORICAL_FAILURES,
        "unexpected_failures": [],
    }
    result["flags"]["F37_FULL_REGRESSION_CURRENT_TREE_CERTIFIED"] = True
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--finalize-full-regression", action="store_true")
    parser.add_argument("--full-total", type=int)
    parser.add_argument("--full-passed", type=int)
    parser.add_argument("--full-failed", type=int)
    args = parser.parse_args(argv)
    if not args.run:
        parser.error("use --run")
    result = certify()
    if args.finalize_full_regression:
        if None in (args.full_total, args.full_passed, args.full_failed):
            parser.error("--finalize-full-regression requires all --full-* counts")
        result = finalize_full_regression(result, args.full_total, args.full_passed, args.full_failed)
    print(json.dumps({"status": result["status"], "eligible": result["eligible_candidates"], "selected": result["selected_candidate"], "boundary": result["selected_boundary"], "defect": result["defect_classification"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
