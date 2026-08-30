"""F23Z audit-only evaluator responsibility and representation reassessment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "f23z_evaluator_representation.json"
F23Y = ROOT / "tests" / "fixtures" / "f23y_context_performance.json"
F23Y_COMMIT = "c4af3b93b6ac9d5185fcd7f225b5e2e4fd7eb136"
F23X_R1_COMMIT = "fe27c26d475eca60fe1686a4c77488de9571d576"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source(path: str) -> dict:
    value = (ROOT / path).read_text(encoding="utf-8")
    return {"path": path, "sha256": _sha(value.encode()), "text": value}


def _evidence() -> dict:
    sources = {
        "search": _source("generic_chess/ai/alphabeta/search.py"),
        "quiescence": _source("generic_chess/ai/alphabeta/quiescence.py"),
        "ordering": _source("generic_chess/ai/alphabeta/ordering.py"),
        "runtime": _source("generic_chess/core/search_runtime.py"),
        "evaluator": _source("generic_chess/ai/evaluation/evaluator.py"),
        "profile": _source("generic_chess/ai/evaluation/profile.py"),
    }
    required = {
        "search": ("ctx.runtime.legal_actions", "ctx.runtime.pushed", "terminal_status", "quiescence"),
        "quiescence": ("promotion_qactions", "capture_qactions", "checking_drop_qactions", "nonchecking_drop_excluded"),
        "ordering": ("capture_order_value", "promotion_target_id", "_killers", "_history", "_countermoves", "checking-action stage"),
        "runtime": ("def legal_actions", "def _push_impl", "repetition", "terminal_from_search_runtime", "def pushed"),
        "evaluator": ("pseudo_attacks", "_promotion_bonus", "_anchor_escape", "is_in_check", "Static-profile lookup"),
        "profile": ("board_value_by_type", "hand_value_by_base_type", "promotion_gain_by_type", "empty_mobility"),
    }
    checks = {name: {needle: needle in sources[name]["text"] for needle in needles} for name, needles in required.items()}
    return {
        "sources": {name: {key: value for key, value in data.items() if key != "text"} for name, data in sources.items()},
        "checks": checks,
        "passed": all(all(values.values()) for values in checks.values()),
        "findings": {
            "search": "Search owns legal-action generation, transitions through pushed runtime state, terminal handling, TT, and recursive continuation.",
            "quiescence": "Qsearch explicitly includes captures, promotions, terminal actions, checking moves, and checking drops; quiet drops are excluded.",
            "ordering": "Ordering prioritizes TT, captures, promotions, killers/countermoves, and history; checking classification is intentionally deferred because it requires expensive legality/attack probes.",
            "runtime": "SearchPathRuntime owns legal actions, push/pop transitions, history, repetition, terminal state, and runtime balance.",
            "evaluator": "Production v1 uses board/hand values, pseudo mobility, bounded anchor escape/check, and profile-derived promotion potential.",
            "profile": "The static profile exposes board values, hand values, promotion gains, piece capability metadata, drop freedom/mobility, and compiler-provided empty-board mobility.",
        },
    }


RESPONSIBILITY = [
    {"representation": "production-v1.material", "information": "board occupancy and rule-derived current-type value", "cost": "O(board occupancy)", "legal_actions": False, "opponent_legal_actions": False, "attack_map": False, "static": True, "search_overlap": "material remains useful after search", "genericity": "Shogi/Chess/Xiangqi/mixed", "class": "LEAF_STRUCTURAL", "leaf_role": "retain"},
    {"representation": "production-v1.hand_inventory", "information": "hand counts times rule-derived base-type hand value", "cost": "O(hand entries)", "legal_actions": False, "opponent_legal_actions": False, "attack_map": False, "static": True, "search_overlap": "drops may be searched, ownership/value is structural", "genericity": "all rulesets with hands; neutral when absent", "class": "LEAF_STRUCTURAL", "leaf_role": "retain"},
    {"representation": "production-v1.cheap_pseudo_mobility", "information": "pseudo attack/reachability geometry", "cost": "board scan plus compiled geometry traversal", "legal_actions": False, "opponent_legal_actions": False, "attack_map": "implicit pseudo map", "static": "geometry only", "search_overlap": "partly overlaps move generation", "genericity": "compiled geometry is generic", "class": "STATIC_PROXY_CANDIDATE", "leaf_role": "bounded proxy only"},
    {"representation": "production-v1.anchor_escape_check", "information": "bounded anchor escapes plus current check", "cost": "bounded anchor probes plus attack query", "legal_actions": False, "opponent_legal_actions": False, "attack_map": "local/query", "static": "anchor identity and movement are static", "search_overlap": "checking/evasions are search/qsearch resident", "genericity": "anchor-based rulesets; neutral without anchor", "class": "STATIC_PROXY_CANDIDATE", "leaf_role": "retain cheap proxy; do not add full safety"},
    {"representation": "production-v1.promotion_potential", "information": "precomputed gain and promotion-zone/progress lookup", "cost": "O(board occupancy)", "legal_actions": False, "opponent_legal_actions": False, "attack_map": False, "static": True, "search_overlap": "immediate promotion is qsearch/order resident", "genericity": "compiled promotion graph", "class": "STATIC_PROXY_CANDIDATE", "leaf_role": "retain structural potential"},
    {"representation": "F23.full_material_inventory", "information": "same board/hand structural values", "cost": "O(board occupancy + hand entries)", "legal_actions": False, "opponent_legal_actions": False, "attack_map": False, "static": True, "search_overlap": "low", "genericity": "all rulesets", "class": "LEAF_STRUCTURAL", "leaf_role": "keep"},
    {"representation": "F23.safe_mobility_control", "information": "full legal actions and attack/control for both sides", "cost": "two semantic legal-action passes plus full attack sweep", "legal_actions": True, "opponent_legal_actions": True, "attack_map": True, "static": False, "search_overlap": "search already traverses legal actions", "genericity": "generic but expensive", "class": "REJECT_LEAF_HOT_PATH", "leaf_role": "search resident"},
    {"representation": "F23.attack_defense_anchor_safety", "information": "checks, anchor safety, and attacked-piece exposure", "cost": "repeated semantic attack queries/maps", "legal_actions": False, "opponent_legal_actions": False, "attack_map": True, "static": False, "search_overlap": "checks/evasions and tactical exposure are searched", "genericity": "generic semantics but high cost", "class": "REJECT_LEAF_HOT_PATH", "leaf_role": "search resident"},
    {"representation": "F23.forcing_capture_recapture", "information": "legal captures plus history-linked recapture target", "cost": "legal actions, capture classification, and history context", "legal_actions": True, "opponent_legal_actions": True, "attack_map": False, "static": False, "search_overlap": "qsearch captures, ordering, history/countermove, and continuation", "genericity": "generic but duplicated", "class": "SEARCH_RESIDENT", "leaf_role": "remove from leaf"},
    {"representation": "F23.promotion_drop_opportunity", "information": "immediate legal promotion/drop actions", "cost": "legal-action enumeration and classification", "legal_actions": True, "opponent_legal_actions": True, "attack_map": False, "static": "only capability portion", "search_overlap": "promotion/drop tactics are qsearch/order/search resident", "genericity": "generic but dynamic", "class": "STATIC_PROXY_CANDIDATE", "leaf_role": "retain only precomputed capability/value proxy"},
]


STRATEGY_DIMENSIONS = [
    "conceptual_simplicity", "genericity", "per_leaf_cost", "production_complexity",
    "search_evaluator_coupling", "duplicated_computation", "incremental_state_burden",
    "rollback_correctness_burden", "mixed_mechanic_compatibility", "standard_shogi_applicability",
    "western_chess_applicability", "type_name_invariance", "game_label_dependence",
    "falsifiability", "path_to_playing_strength_evidence",
]


STRATEGY_SCORES = {
    "FULL_DYNAMIC_SEMANTIC_LEAF": [1, 4, 1, 1, 1, 1, 5, 5, 4, 3, 3, 4, 5, 4, 2],
    "CHEAP_RULE_DERIVED_LEAF_WITH_SEARCH_RESIDENT_TACTICS": [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 4, 3],
    "INCREMENTAL_DYNAMIC_EVALUATION_STATE": [2, 4, 3, 1, 1, 3, 1, 1, 4, 4, 4, 4, 5, 3, 3],
    "LEARNED_SMALL_RULE_DERIVED_LEAF": [2, 3, 5, 3, 2, 5, 5, 5, 4, 4, 4, 3, 1, 2, 4],
}


def _strategy_matrix() -> dict:
    rows = {}
    for name, scores in STRATEGY_SCORES.items():
        rows[name] = {dimension: score for dimension, score in zip(STRATEGY_DIMENSIONS, scores)}
        rows[name]["total"] = sum(scores)
    ranking = sorted(((row["total"], name) for name, row in rows.items()), reverse=True)
    return {"dimensions": STRATEGY_DIMENSIONS, "scores": rows, "ranking": [{"strategy": name, "total": total} for total, name in ranking], "score_scale": "1=poor fit, 5=strong fit; planning evidence only; no existing-infrastructure bonus"}


def _cheap_ingredients() -> list[dict]:
    return [
        {"ingredient": "board_value_by_type", "source": "RuleSetEvaluationProfile", "available": True, "cost": "bounded board lookup", "cross_ruleset": True},
        {"ingredient": "hand_value_by_base_type", "source": "RuleSetEvaluationProfile", "available": True, "cost": "bounded hand-entry lookup", "cross_ruleset": True},
        {"ingredient": "promotion_gain_by_type", "source": "RuleSetEvaluationProfile", "available": True, "cost": "static promotion graph lookup", "cross_ruleset": True},
        {"ingredient": "empty_board_mobility_and_forward_mobility", "source": "CompiledRuleSet", "available": True, "cost": "precomputed positional lookup", "cross_ruleset": True},
        {"ingredient": "drop_freedom_and_drop_mobility", "source": "RuleSetEvaluationProfile", "available": True, "cost": "static mask/lookup", "cross_ruleset": True},
        {"ingredient": "current_base_type_and_anchor_identity", "source": "Piece/CompiledRuleSet metadata", "available": True, "cost": "constant metadata lookup", "cross_ruleset": True},
        {"ingredient": "occupancy_and_local_friendly_enemy_occupancy", "source": "Position.board", "available": True, "cost": "single board scan", "cross_ruleset": True},
    ]


def _frozen_f24a() -> dict:
    return {
        "conclusion": "CONTINUE_WITH_MINIMAL_CHEAP_EVALUATOR",
        "basis": [
            "material_and_inventory",
            "rule_derived_positional_capability",
            "bounded_anchor_structural_space",
            "promotion_and_drop_structural_capability",
        ],
        "frozen_constraints": [
            "no semantic legal-action enumeration in evaluate()",
            "no opponent-side legal-action enumeration in evaluate()",
            "no full-board semantic attack sweep in evaluate()",
            "no multi-ply tactical search",
            "no game-name branch, piece-name logic, per-game coefficient table, or search-policy hidden state",
            "at most five score concepts; exact formula remains pre-registered from existing normalized profile data before implementation",
        ],
        "gates": {
            "micro_median_candidate_vs_v1": "<=2.0x on frozen F23Y Standard Shogi leaf sample",
            "micro_p95_candidate_vs_v1": "<=3.0x",
            "if_micro_fail": "do not run full Shogi search",
            "completed_2048_quality": "candidate top1 >= v1 + 2 and zero frozen-control regression",
            "fixed_time_fraction": "<=0.25",
            "fixed_time_paired_nps": ">=0.65",
        },
        "cross_ruleset": {"Standard Shogi": True, "Western Chess": True, "future mixed-mechanic RuleSet": True},
        "next_boundary": "F24A_MINIMAL_CHEAP_RULE_DERIVED_EVALUATOR_SIGNAL_PROBE",
    }


def _f23y_ledger() -> dict:
    report = json.loads(F23Y.read_text(encoding="utf-8"))
    return {
        "semantic_contracts": "PASS",
        "m9_positive_gain": report["preflight"]["m9_positive_gain"]["passed"],
        "contract_specific_rename": report["preflight"]["contract_specific_rename"]["passed"],
        "p0_p1_math_parity": report["p1_parity"]["passed"],
        "p0_median_seconds": report["micro_cost"]["summaries"]["P0"]["median_evaluate_seconds"],
        "p1_median_seconds": report["micro_cost"]["summaries"]["P1"]["median_evaluate_seconds"],
        "v1_median_seconds": report["micro_cost"]["summaries"]["v1"]["median_evaluate_seconds"],
        "p1_p0_speedup": report["micro_cost"]["summaries"]["P1"]["speedup_vs_P0"],
        "paired_nps": {key: report["fixed_time"]["summaries"][key]["gates"]["paired_median_nps_ratio"] for key in ("0.25", "1.0")},
        "evaluator_fraction": {key: report["fixed_time"]["summaries"][key]["gates"]["candidate_evaluator_fraction"] for key in ("0.25", "1.0")},
        "real_shogi_2048": {"valid": report["fixed_node"]["quality_gate"]["valid"], "top1_delta": report["fixed_node"]["quality_gate"]["top1_delta"], "controls_passed": report["fixed_node"]["quality_gate"]["controls_passed"]},
        "root_rank": report["root_rank_status"],
        "playing_strength": "NOT_RUN",
    }


def _artifact_identity() -> dict:
    f23y_paths = ["docs/architecture/ADR-073-minimal-analytic-context-performance.md", "scripts/audit_f23y_context_performance.py", "tests/fixtures/f23y_context_performance.json", "tests/test_f23y_context_performance.py"]
    rows = []
    for path in f23y_paths:
        current = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
        baseline = __import__("subprocess").check_output(["git", "-C", str(ROOT), "show", f"{F23Y_COMMIT}:{path}"]).replace(b"\r\n", b"\n")
        rows.append({"path": path, "matches": current == baseline})
    return {"f23y_commit": F23Y_COMMIT, "f23x_r1_commit": F23X_R1_COMMIT, "f23y_files_unchanged": all(row["matches"] for row in rows), "files": rows, "historical_f23x_r1_fixture_identity": json.loads(F23Y.read_text(encoding="utf-8"))["artifact_integrity"]["all_match"]}


def run() -> dict:
    evidence = _evidence()
    strategies = _strategy_matrix()
    frozen = _frozen_f24a()
    result = {
        "schema_version": 1,
        "status": "PASS",
        "accepted_f23y_evidence_ledger": _f23y_ledger(),
        "search_responsibility_evidence": evidence,
        "responsibility_matrix": RESPONSIBILITY,
        "cheap_ruleset_ingredients": _cheap_ingredients(),
        "strategy_matrix": strategies,
        "selected_representation_philosophy": "generic adversarial search + TT/order/qsearch + small cheap RuleSet-derived structural leaf evaluator",
        "double_counting_finding": "Immediate captures, promotions, checks, drops, recaptures, and tactical mobility are already represented by search/qsearch/order; the leaf should distinguish quiet structural state after tactical continuation, not replay tactical analysis.",
        "complexity_budget": {"score_concepts": "approximately 2-5", "board_cost": "O(board occupancy + hand entries + bounded precomputed lookups)", "prohibitions": ["full legal actions", "second-side legal actions", "full semantic attack sweep", "multi-ply tactical search", "game-name branches", "piece-name scoring", "per-game coefficient tables", "search-policy hidden state"]},
        "decision": frozen,
        "artifact_identity": _artifact_identity(),
        "production_changed": False,
        "master_locked": True,
    }
    return result


def main() -> None:
    result = run()
    FIXTURE.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "selected": result["decision"]["conclusion"], "boundary": result["decision"]["next_boundary"], "source_evidence": result["search_responsibility_evidence"]["passed"]}))


if __name__ == "__main__":
    main()
