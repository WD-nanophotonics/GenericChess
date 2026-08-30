"""Deterministic F23W evaluator-validation strategy reassessment.

This is a small design/assessment artifact.  It does not run F23V again,
create a corpus, change production search, or implement F23X.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
OUTPUT = FIXTURES / "f23w_evaluator_strategy_r2.json"
F22_COMMIT = "3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38"
F23V_CLOSE = "3b2a104ce2f13863720ecde601578e7795fa2d65"
GROUPS = ("SHOGI_LIKE", "WESTERN_CHESS_LIKE", "MIXED_MECHANIC")
FEATURES = ("material_and_inventory", "safe_mobility_and_control", "attack_defense_and_anchor_safety", "forcing_capture_recapture", "capability_gated_promotion_drop")


def _git_show(path: str, commit: str = F22_COMMIT) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _f22_evidence() -> dict:
    paths = {
        "positions": "artifacts/f22_post_f21_rebaseline_strength/round5_frozen_positions.json",
        "provenance": "artifacts/f22_post_f21_rebaseline_strength/alphasho_reference_provenance.json",
        "agreement": "artifacts/f22_post_f21_rebaseline_strength/alphasho_move_agreement.json",
        "rank": "artifacts/f22_post_f21_rebaseline_strength/one_ply_reference_rank.json",
    }
    values = {name: _git_show(path) for name, path in paths.items()}
    positions = json.loads(values["positions"])
    provenance = json.loads(values["provenance"])
    rank = json.loads(values["rank"])
    return {"source_commit": F22_COMMIT, "source_paths": paths, "sha256": {name: _sha(value) for name, value in values.items()}, "position_count": len(positions["positions"]), "reference_count": provenance["reference_count"], "rank_rows": len(rank), "read_only": bool(provenance["read_only"])}


def _strategy_table() -> dict:
    criteria = ("conceptual_simplicity", "genericity", "artificial_horizon_dependence", "benchmark_leakage_resistance", "production_complexity", "data_generation_burden", "compute_cost", "falsifiability", "mixed_mechanic_validation", "standard_shogi_validation", "western_chess_validation", "overfit_resistance", "playing_strength_evidence")
    scores = {
        "LOCAL_METAMORPHIC_PLUS_REAL_GAME_SEARCH_SHADOW": [5, 5, 5, 5, 4, 4, 4, 5, 5, 5, 4, 4, 5],
        "GENERIC_SELFPLAY_TD_SCALE_LEARNING": [3, 5, 4, 4, 3, 2, 2, 4, 5, 4, 4, 2, 4],
        "EXTERNAL_ENGINE_DIRECT_SUPERVISION": [2, 1, 4, 1, 2, 3, 3, 4, 1, 5, 3, 1, 5],
        "CONTINUE_EXACT_SYNTHETIC_SUPERVISION": [1, 3, 1, 2, 2, 1, 1, 3, 2, 2, 2, 1, 2],
    }
    return {name: {criterion: value for criterion, value in zip(criteria, values)} for name, values in scores.items()}


def _metamorphic_matrix() -> list[dict]:
    return [
        {"feature": "material_and_inventory", "transformation": "remove opponent non-anchor piece with unrelated state fixed", "expected": "actor term must not decrease", "variants": ["renamed-equivalent", "capture-to-hand", "remove-from-game"]},
        {"feature": "material_and_inventory", "transformation": "add legal owned hand inventory", "expected": "actor term must not decrease", "variants": ["renamed-equivalent", "drop-capable", "no-drop"]},
        {"feature": "safe_mobility_and_control", "transformation": "unblock an otherwise identical own legal path", "expected": "actor term must not decrease", "variants": ["renamed-equivalent", "semantic", "legacy-profile-only"]},
        {"feature": "safe_mobility_and_control", "transformation": "remove one legal opponent action without changing actor actions", "expected": "relative term must not decrease", "variants": ["renamed-equivalent", "mixed-mechanic"]},
        {"feature": "attack_defense_and_anchor_safety", "transformation": "move actor anchor from attacked to equivalent unattacked square", "expected": "actor term must improve", "variants": ["renamed-equivalent", "semantic-check"]},
        {"feature": "attack_defense_and_anchor_safety", "transformation": "add an actual attack against opponent anchor while preserving actor safety", "expected": "relative term must not decrease", "variants": ["renamed-equivalent", "mixed-mechanic"]},
        {"feature": "forcing_capture_recapture", "transformation": "introduce a profitable legal capture", "expected": "actor term must not decrease", "variants": ["renamed-equivalent", "capture-to-hand", "remove-from-game"]},
        {"feature": "forcing_capture_recapture", "transformation": "provide legal recapture onto authoritative previous-action target", "expected": "recapture component must increase", "variants": ["renamed-equivalent", "history-present", "history-absent-control"]},
        {"feature": "capability_gated_promotion_drop", "transformation": "make a positive-gain legal promotion available", "expected": "actor term must not decrease", "variants": ["renamed-equivalent", "promotable", "non-promotable-control"]},
        {"feature": "capability_gated_promotion_drop", "transformation": "add usable hand inventory with a legal drop", "expected": "actor term must not decrease", "variants": ["renamed-equivalent", "capture-to-hand", "mixed-mechanic"]},
    ]


def _shogi_shadow_plan() -> dict:
    return {"source": {"commit": F22_COMMIT, "artifact": "round5_frozen_positions.json", "positions": 10, "reference": "read-only preserved mature-engine moves"}, "same_search_policy": True, "same_legality_runtime": True, "evaluators": ["production_evaluator_v1", "unchanged_five_feature_analytic_candidate"], "fixed_node_budgets": [128, 512, 2048], "fixed_time_budgets_seconds": [0.25, 1.0], "tt_policy": "same enabled policy and fresh deterministic table per comparison", "move_ordering": "same production move ordering", "required_per_position": ["selected_move", "reference_move_rank", "reference_move_top_k", "root_score_ordering", "pv_if_available", "nodes", "completed_depth", "nodes_per_second", "evaluator_calls", "evaluator_time", "total_search_wall", "evaluator_fraction"], "quality_gate": {"candidate_reference_top1_agreement_delta": ">= +2 positions out of 10 over evaluator-v1 OR", "candidate_mean_reference_rank": "strictly better than evaluator-v1 by pre-registered material margin >= 10%", "agreement_controls": "zero catastrophic regression: no frozen control agreement may be lost", "completion": "all 10 positions complete under every declared budget"}, "performance_gate": {"candidate_evaluator_fraction": "<= 25% of total search wall time", "fixed_time_nodes_per_second": "not below evaluator-v1 by >35% on median", "fixed_node_completion": "all declared node budgets complete"}, "interpretation": "signal validation only; no parity or playing-strength claim"}


def _evaluation_context_design() -> dict:
    return {"status": "DESIGN_ONLY", "scope": "audit-only next experiment; no production framework change", "one_shared_read_only_pass": True, "facts": ["legal actions by side where safely obtainable", "captures", "promotions", "drops", "semantic attack/check information", "anchor locations and safety", "authoritative recent-action target", "RuleSet-derived values/profile"], "consumers": list(FEATURES), "invalidation": "per-position immutable; rebuild after transition", "purpose": "separate local semantic correctness from search-shadow playing evidence and avoid five independent legality scans"}


def _artifact_integrity() -> dict:
    paths = ["docs/architecture/ADR-067-f23v-minimal-analytic-evaluator-signal-probe.md", "docs/architecture/ADR-068-f23v-mechanic-active-signal-corrective.md", "docs/architecture/ADR-069-f23v-admission-correction-final.md", "scripts/audit_f23v_minimal_analytic_evaluator.py", "scripts/audit_f23v_minimal_analytic_evaluator_r1.py", "scripts/audit_f23v_minimal_analytic_evaluator_r2.py", "tests/fixtures/f23v_minimal_analytic_plan.json", "tests/fixtures/f23v_minimal_analytic_signal.json", "tests/fixtures/f23v_minimal_analytic_plan_r1.json", "tests/fixtures/f23v_minimal_analytic_signal_r1.json", "tests/fixtures/f23v_minimal_analytic_signal_r2.json"]
    matches = []
    for path in paths:
        current = (ROOT / path).read_bytes()
        historical = _git_show(path, F23V_CLOSE)
        normalized_current = current.replace(b"\r\n", b"\n")
        matches.append({"path": path, "sha256": _sha(normalized_current), "matches_f23v_close": normalized_current == historical})
    return {"baseline_commit": F23V_CLOSE, "all_match": all(row["matches_f23v_close"] for row in matches), "files": matches}


def run() -> dict:
    strategies = _strategy_table()
    totals = {name: sum(values.values()) for name, values in strategies.items()}
    selected = max(totals, key=totals.get)
    ledger_corrections = {"max_ply": "R2 certified abstraction may have nonzero MAX_PLY diagnostics; the earlier four-certification field used V3 visitation and must not be restated as abstraction visitation", "western_drop": "structural zero-drop requirement is equality to zero, not >= 0"}
    return {"schema_version": 1, "status": "ASSESSMENT_COMPLETE", "f23v_closure": {"candidate_sha": "3b2a104ce2f13863720ecde601578e7795fa2d65", "exact_supervision_default": "RETIRED", "conclusion": "strict active-mechanic full W/D/L plus abstraction is too sparse/expensive for default evaluator validation", "no_f23v_rerun": True}, "strategy_criteria": list(next(iter(strategies.values())).keys()), "strategies": strategies, "strategy_totals": totals, "selected_philosophy": selected, "feature_budget": {"families": list(FEATURES), "coefficients": [1, 1, 1, 1, 1], "score_form": "S * sum(feature_i)", "game_name_branch": False, "concrete_piece_scoring_branch": False}, "metamorphic_contract_matrix": _metamorphic_matrix(), "evaluation_context_design": _evaluation_context_design(), "standard_shogi_shadow_plan": _shogi_shadow_plan(), "western_chess_future_plan": {"phase_1": "full rule correctness/perft", "phase_2": "verified mature heuristic reference", "phase_3": "fixed-node/fixed-time move/PV/evaluation", "phase_4": "later match-strength evidence", "status": "DESIGN_ONLY"}, "mixed_mechanic_role": ["capture-to-hand/drop coexisting with remove-from-game", "promotion and non-promotion coexistence", "path/special movement", "generic identity/history/runtime/no game-name branch"], "evidence_classes": ["SEMANTIC_CONTRACT_EVIDENCE", "REAL_GAME_BENCHMARK_EVIDENCE", "PLAYING_STRENGTH_EVIDENCE"], "evaluator_v1": {"available_for_standard_shogi": True, "basis": "existing production Evaluator and F22 component-parity audit", "candidate_comparison_required": True}, "performance_warning": "pre-registered candidate evaluator fraction <=25% and fixed-time median nodes/second decline <=35%", "ledger_corrections": ledger_corrections, "f22_evidence": _f22_evidence(), "artifact_integrity": _artifact_integrity(), "selected_boundary": "F23X_MINIMAL_ANALYTIC_EVALUATOR_METAMORPHIC_AND_SHOGI_SHADOW", "f23x_implemented": False, "production_changed": False}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=OUTPUT); args = parser.parse_args()
    result = run(); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps({"status": result["status"], "selected": result["selected_boundary"], "f22_positions": result["f22_evidence"]["position_count"]}, sort_keys=True))


if __name__ == "__main__":
    main()
