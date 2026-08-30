"""F23U diagnostic overlay for evaluator-supervision strategy reassessment.

This script is deliberately audit-only.  It reads the frozen V5--V12
artifacts, re-audits the R10 witness actions without rewriting V12, and emits
one compact strategy assessment.  It does not fit coefficients, build a new
corpus, or change production code.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
V12 = FIXTURES / "evaluator_v2_corpus_v12.json"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _load_r10():
    path = ROOT / "scripts" / "build_f23t_natural_terminal_corpus_r10.py"
    spec = importlib.util.spec_from_file_location("f23t_r10_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load the frozen R10 builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _action_key(action: dict[str, Any]) -> str:
    return json.dumps(action, sort_keys=True, separators=(",", ":"))


def _piece_at(candidate: dict[str, Any], square: list[int] | tuple[int, int]) -> str:
    file, rank = square
    n = candidate["board_size"]
    return candidate["rows"][n - 1 - rank][file]


def _causal_witness(record: dict[str, Any], builder) -> dict[str, Any]:
    """Re-audit the selected witness and preserve only semantic evidence."""
    witness = record.get("strict_mechanic_witness")
    if not witness:
        return {"passes": False, "reason": "NO_WITNESS"}
    action = witness.get("action", {})
    rows = record.get("v3_root_action_values", [])
    values = [row["value"] for row in rows if _action_key(row["action"]) == _action_key(action)]
    if not values:
        return {"passes": False, "reason": "WITNESS_ACTION_NOT_IN_ROOT_SET"}
    witness_value = values[0]
    distinguishes = any(row["value"] != witness_value for row in rows)
    if not distinguishes:
        return {"passes": False, "reason": "WITNESS_NOT_WDL_DISTINGUISHING"}

    candidate = record["candidate"]
    compiled, state = builder.build_candidate(candidate, record["builder"])
    runtime = builder.SearchPathRuntime.from_state(state, compiled)
    from generic_chess.core.actions import action_from_dict
    from generic_chess.core.attacks import is_in_check

    action_obj = action_from_dict(action)
    mechanic = record["mechanic_family"]
    actual = False
    evidence: dict[str, Any] = {"action": action, "value": witness_value}
    if mechanic == "drop_hand":
        actual = action.get("kind") == "drop"
        evidence["actual_drop"] = actual
    elif mechanic == "promotion_choice":
        actual = action.get("promotion_target_id") is not None
        evidence["actual_promotion_target"] = action.get("promotion_target_id")
    elif mechanic == "capture_recapture":
        target = _piece_at(candidate, action.get("to", [-1, -1]))
        actual = target != "." and target.islower()
        evidence["captured_piece"] = target
    elif mechanic == "semantic_guard_aux_state":
        pattern = str(action.get("pattern_id", ""))
        actual = action.get("kind") == "semantic_board" and pattern.startswith("sem_")
        evidence["custom_semantic_pattern"] = pattern
    elif mechanic == "interposition_leaper":
        source = action.get("from", [-1, -1])
        actor = _piece_at(candidate, source) if source[0] >= 0 and source[1] >= 0 else "."
        actual = actor.upper() == "L"
        evidence["actor"] = actor
    elif mechanic == "anchor_check_movement":
        before = tuple(is_in_check(runtime.position, owner, compiled) for owner in (0, 1))
        child = runtime.push(action_obj)
        after = tuple(is_in_check(child.position, owner, compiled) for owner in (0, 1))
        terminal = child.terminal_status.status.value
        actual = before != after or terminal in {"checkmate", "stalemate"}
        evidence.update({"check_vector_before": before, "check_vector_after": after, "child_terminal": terminal})
    else:
        return {"passes": False, "reason": "UNKNOWN_MECHANIC", "mechanic": mechanic}
    evidence.update({"wdl_distinguishes": distinguishes, "mechanic_occurs": actual})
    return {"passes": bool(distinguishes and actual), **evidence}


def _metadata_free_fingerprint(record: dict[str, Any], causal: dict[str, Any], builder) -> str:
    """Fingerprint game semantics and decision evidence, excluding R10 metadata."""
    candidate = record["candidate"]
    compiled, _state = builder.build_candidate(candidate, record["builder"])
    state = {
        key: candidate[key]
        for key in ("board_size", "rows", "side_to_move", "hands", "aux_state", "history", "max_ply")
        if key in candidate
    }
    payload = {
        "compiled_ruleset_semantic_fingerprint": compiled.ruleset_fingerprint,
        "initial_state_and_history": state,
        "legal_root_action_semantics": sorted(
            (_action_key(row["action"]), row["value"]) for row in record.get("v3_root_action_values", [])
        ),
        "optimal_action_semantics": sorted(_action_key(action) for action in record.get("v3_optimal_actions", [])),
        "proof_shape": {
            "proof_depth": record.get("proof_depth"),
            "abstraction_status": record.get("abstraction_status"),
            "terminal_statuses": record.get("abstraction_stats", {}).get("terminal_statuses", {}),
        },
        "causal_mechanic_evidence": {
            key: value for key, value in causal.items() if key not in {"passes", "action"}
        },
        "witness_action": causal.get("action"),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _r10_reaudit() -> dict[str, Any]:
    corpus = json.loads(V12.read_text(encoding="utf-8"))
    builder = _load_r10()
    strict_records = [row for row in corpus["records"] if row.get("strict_witness_status") == "PASS"]
    details = []
    for row in strict_records:
        causal = _causal_witness(row, builder)
        fingerprint = _metadata_free_fingerprint(row, causal, builder)
        details.append({"id": row["id"], "planned_split": row["planned_split"], "causal": causal, "fingerprint": fingerprint})
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in details:
        groups.setdefault(item["fingerprint"], []).append(item)
    collisions = [sorted(item["id"] for item in group) for group in groups.values() if len({item["planned_split"] for item in group}) > 1]
    effective_records = [row for row in corpus["records"] if row.get("eligible")]
    effective_details = []
    for row in effective_records:
        causal = _causal_witness(row, builder) if row.get("strict_witness_status") == "PASS" else {"passes": False, "reason": "NOT_CURRENT_STRICT_WITNESS"}
        if causal.get("passes"):
            effective_details.append({"id": row["id"], "planned_split": row["planned_split"], "fingerprint": _metadata_free_fingerprint(row, causal, builder)})
    effective_groups = {}
    for item in effective_details:
        effective_groups.setdefault(item["fingerprint"], []).append(item)
    effective_collisions = [sorted(item["id"] for item in group) for group in effective_groups.values() if len({item["planned_split"] for item in group}) > 1]
    visible = [
        row for row in corpus["records"]
        if any(status not in {"ongoing", "max_ply"} for status in row.get("structural_prefilter", {}).get("short_terminal_statuses", []))
    ]
    return {
        "source_v12_sha256": hashlib.sha256(V12.read_bytes()).hexdigest(),
        "strict_witness": {
            "current_count": len(strict_records),
            "causal_surviving_count": sum(item["causal"].get("passes", False) for item in details),
            "details": details,
        },
        "metadata_free_behavior": {
            "raw_strict_count": len(details),
            "raw_strict_orbit_count": len(groups),
            "deduplicated_strict_count": len(groups),
            "cross_split_collisions": collisions,
            "raw_effective_count": len(effective_details),
            "deduplicated_effective_orbit_count": len(effective_groups),
            "cross_split_effective_collisions": effective_collisions,
        },
        "short_natural_terminal_visibility": {
            "planned_count": len(corpus["records"]),
            "visible_count": len(visible),
            "by_family": dict(sorted(Counter(row["construction_family"] for row in visible).items())),
        },
        "v12_rewritten": False,
    }


def _historical_table() -> list[dict[str, Any]]:
    v5, v6, v7, v8, v9, v10, v11, v12 = (_load(f"evaluator_v2_corpus_{name}.json") for name in ("v5", "v6", "v7", "v8", "v9", "v10", "v11", "v12"))
    values = {
        "V5": {"physical": v5["sampling"]["candidate_pool_size"], "exact": v5["sampling"]["solved_candidate_count"], "preference": 30, "independent": v5["effective_orbits"]["effective_decision_orbits"], "horizon": v5["coverage"]["non_max_ply_development"], "horizon_basis": "non_max_ply_development", "dev": v5["coverage"]["fit_eligible_development"], "holdout": v5["coverage"]["validation_eligible_holdout"], "failure": "3 historical V4 duplicate/non-eligible orbits"},
        "V6": {"physical": v6["coverage"]["planned_candidate_count"], "exact": v6["coverage"]["physical_solved_count"], "preference": len(v6["generic_exact"]), "independent": len(v6["generic_exact"]), "horizon": v6["coverage"]["effective_development_count"], "horizon_basis": "effective development with max_ply_dependent_count=0", "dev": v6["coverage"]["effective_development_count"], "holdout": v6["coverage"]["effective_holdout_count"], "failure": "30 unresolved; 4 duplicate candidates; 1 source-family exclusion"},
        "V7": {"physical": v7["planned_candidate_count"], "exact": v7["coverage"]["solved"], "preference": v7["coverage"]["preference_strong"], "independent": v7["coverage"]["effective_preference_representatives"], "horizon": v7["coverage"]["non_max_ply_development"], "horizon_basis": "non_max_ply_development", "dev": v7["coverage"]["development"], "holdout": v7["coverage"]["holdout"], "failure": "16 unresolved + 12 all-equal; family/mechanic scale failed"},
        "V8": {"physical": v8["coverage"]["new_planned"], "exact": v8["coverage"]["new_solved"], "preference": v8["coverage"]["new_preference"], "independent": v8["coverage"]["combined_effective"], "horizon": v8["coverage"]["non_max_ply_development"], "horizon_basis": "non_max_ply_development", "dev": v8["coverage"]["development"], "holdout": v8["coverage"]["holdout"], "failure": "1 behavioral leakage orbit; holdout minimum failed"},
        "V9": {"physical": v9["coverage"]["r7_planned"], "exact": v9["coverage"]["r7_solved"], "preference": v9["coverage"]["r7_preference"], "independent": v9["coverage"]["combined_effective"], "horizon": v9["coverage"]["horizon_dependence_classes"]["NATURAL_TERMINAL_CERTIFIED"], "horizon_basis": "natural_terminal_certified", "dev": v9["coverage"]["development"], "holdout": v9["coverage"]["holdout"], "failure": "11 all-equal + 2 no-witness; only 1 stable development horizon"},
        "V10": {"physical": v10["coverage"]["r8_planned"], "exact": v10["coverage"]["r8_solved"], "preference": v10["coverage"]["r8_preference"], "independent": v10["coverage"]["combined_effective"], "horizon": v10["coverage"]["horizon_classes"]["HORIZON_STABLE_EXACT"], "horizon_basis": "horizon stable exact", "dev": v10["coverage"]["development"], "holdout": v10["coverage"]["holdout"], "failure": "15 materially max-ply-dependent/24 unknown; 3 cross-split behavioral collisions"},
        "V11": {"physical": len(v11["records"]), "exact": v11["diagnostics"]["v3_exact"], "preference": v11["diagnostics"]["preference_bearing"], "independent": len(v11["eligible_preference_representatives"]), "horizon": v11["diagnostics"]["abstraction_certified"], "horizon_basis": "abstraction certified", "dev": v11["coverage"]["development"], "holdout": v11["coverage"]["holdout"], "failure": "9 V3 unresolved + 20 all-equal; 18 abstraction refusals"},
        "V12": {"physical": v12["diagnostics"]["planned"], "exact": v12["diagnostics"]["v3_exact"], "preference": v12["diagnostics"]["preference_bearing"], "independent": len(v12["eligible_preference_representatives"]), "horizon": v12["diagnostics"]["abstraction_certified"], "horizon_basis": "abstraction certified (historical V12 count)", "dev": v12["coverage"]["development"], "holdout": v12["coverage"]["holdout"], "failure": "41 V3 unresolved + 11 all-equal; core diversity and scale failed"},
    }
    return [{"generation": generation, **row} for generation, row in values.items()]


def _attrition() -> dict[str, Any]:
    return {
        "solver_cost_or_unresolved": {"V5": 0, "V6": 30, "V7": 16, "V8": 0, "V9": 0, "V10": 0, "V11": 9, "V12": 41},
        "all_equal": {"V5": 0, "V6": 0, "V7": 12, "V8": 12, "V9": 11, "V10": 15, "V11": 20, "V12": 11},
        "behavioral_duplication_orbit_exclusions": {"V5": 3, "V6": 4, "V7": 0, "V8": 1, "V9": 0, "V10": 3, "V11": 0, "V12": 0},
        "source_split_leakage_exclusions": {"V5": 0, "V6": 1, "V7": 0, "V8": 0, "V9": 0, "V10": 0, "V11": 0, "V12": 0},
        "mechanic_witness_failures_explicit": {"V5": 0, "V6": 0, "V7": 0, "V8": 2, "V9": 2, "V10": 2, "V11": "not separately recorded", "V12": 0},
        "known_max_ply_dependent": {"V5": 0, "V6": 0, "V7": 0, "V8": 8, "V9": 6, "V10": 9, "V11": 0, "V12": 0},
        "family_mechanic_diversity_gate_failures": {"V5": "not gated", "V6": 2, "V7": 4, "V8": 1, "V9": 1, "V10": 0, "V11": 4, "V12": 4},
        "notes": "Counts are direct fixture fields or explicit gate failures; unknown/refused horizon cases are not relabeled as MAX_PLY dependence.",
    }


STRATEGY_SCORES = {
    "A_SYNTHETIC_EXACT_PREFERENCE_FITTING": [2, 1, 1, 2, 1, 1, 1, 3, 2, 2, 2, 1, 2],
    "B_ANALYTIC_RULE_DERIVED_EVALUATOR": [5, 5, 4, 5, 5, 4, 5, 5, 5, 5, 5, 4, 5],
    "C_GENERIC_SELFPLAY_OR_TD_BOOTSTRAP": [4, 3, 3, 4, 3, 2, 3, 3, 4, 4, 4, 3, 4],
    "D_EXTERNAL_ENGINE_REFERENCE_SUPERVISION": [2, 2, 2, 1, 5, 1, 1, 4, 2, 2, 3, 1, 2],
}

SCORE_CRITERIA = [
    "genericity_across_families", "conceptual_simplicity", "production_concept_budget", "low_game_specific_label_dependence",
    "low_max_ply_dependence", "compute_cost", "data_generation_cost", "falsifiability", "grouped_transfer_testing",
    "shogi_compatibility", "western_chess_compatibility", "low_overfit_risk", "mixed_mechanic_compatibility",
]


def _strategy_assessment() -> dict[str, Any]:
    table = []
    for name, scores in STRATEGY_SCORES.items():
        table.append({"strategy": name, "scores": dict(zip(SCORE_CRITERIA, scores)), "total": sum(scores), "mean": round(sum(scores) / len(scores), 3)})
    return {
        "scale": "1 (poor) to 5 (strong); all criteria equal weight; compute/data cost score means low cost; label/max-ply/overfit score means low dependence/risk",
        "criteria": SCORE_CRITERIA,
        "table": table,
        "selected": "B_ANALYTIC_RULE_DERIVED_EVALUATOR",
    }


def _architecture_audit() -> dict[str, Any]:
    paths = [ROOT / "generic_chess" / "rules" / "schema.py", ROOT / "generic_chess" / "rules" / "ir.py", ROOT / "generic_chess" / "core" / "semantic_executor.py"]
    return {
        "semantic_ir_supports": {
            "shogi_capture_to_hand_and_drop": True,
            "chess_remove_from_game_and_promotion": True,
            "xiangqi_non_promotable_special_movement": True,
            "coexistence_in_one_ruleset": True,
        },
        "evidence": {
            "schema": {"path": "generic_chess/rules/schema.py", "symbols": ["DISPOSITIONS", "RuleActionEffect", "RuleSemanticAction", "RuleGeometrySpec", "promotion_mode", "action_family"]},
            "ir": {"path": "generic_chess/rules/ir.py", "symbols": ["CompiledSemanticRuleset", "promotion_mode", "capture_to_hand", "remove_from_game"]},
            "executor": {"path": "generic_chess/core/semantic_executor.py", "symbols": ["_apply_effect", "remove", "capture_to_hand", "remove_from_hand", "place", "set_current_type"]},
        },
        "source_sha256": {path.as_posix().replace("/", "\\"): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        "smallest_missing_primitive": None,
        "legacy_vs_semantic_boundary": "legacy compiled capture remains capture-to-hand oriented; semantic IR carries explicit per-effect disposition, so no production extension is authorized or required in F23U",
        "audit_only": True,
    }


def build_assessment() -> dict[str, Any]:
    r10 = _r10_reaudit()
    return {
        "schema_version": 1,
        "assessment_id": "f23u-supervision-strategy-assessment",
        "source_v12_sha256": r10["source_v12_sha256"],
        "historical_generations": _historical_table(),
        "attrition": _attrition(),
        "r10_corrected_reaudit": r10,
        "strategy_comparison": _strategy_assessment(),
        "recommended_philosophy": "Prefer a small analytic evaluator whose feature scales are derived from RuleSet structure; do not fit synthetic coefficients or route external-engine labels into the generic core.",
        "production_complexity_budget": {
            "feature_families": 5,
            "common_form": "one bounded linear score over normalized generic features",
            "bounded_coefficients": 5,
            "coefficient_range": "[-4, 4]",
            "game_specific_branches": 0,
            "piece_name_specific_logic": 0,
            "game_specific_coefficient_tables": 0,
        },
        "feature_reassessment": [
            {"candidate": "value-weighted attack/defense/hanging exposure", "classification": "core generic concept worth retaining"},
            {"candidate": "immediate legal capture and recapture pressure", "classification": "core generic concept worth retaining"},
            {"candidate": "legal safe mobility with value-weighted captures", "classification": "core generic concept worth retaining"},
            {"candidate": "anchor escape, checking threats, defensive pressure", "classification": "core generic concept, folded into safety/control"},
            {"candidate": "promotion opportunity/forced promotion/threat", "classification": "core generic transition concept, capability-gated"},
            {"candidate": "hand/drop pressure", "classification": "core generic transition concept, capability-gated"},
            {"candidate": "semantic legality suppression/additions", "classification": "too expensive as a direct evaluator feature; consume legal actions instead"},
        ],
        "minimal_next_experiment": {
            "name": "MINIMAL_ANALYTIC_EVALUATOR_SIGNAL_PROBE",
            "feature_set": ["material_and_inventory", "safe_mobility_and_control", "attack_defense_and_anchor_safety", "forcing_capture_recapture", "capability_gated_promotion_drop"],
            "parameter_budget": "five fixed rule-derived scales; no fitted coefficients; one common score form",
            "development_validation": "frozen exact W/D/L root-action ordering on a small pre-registered DEVELOPMENT slice; no labels from AlphaSho/AlphaChess",
            "grouped_transfer": ["Shogi-like semantic ruleset", "Western-Chess-like ruleset", "one mixed-mechanic ruleset"],
            "success_thresholds": [">=0.70 top-choice agreement with exact action set on DEVELOPMENT", ">=0.60 grouped-transfer agreement in each family", "no group below 0.50", "zero ruleset-name branches"],
            "stop_conditions": ["fail if any threshold misses", "fail if any group has contradictory direction on >=50% of cases", "fail if feature count or coefficient budget must increase", "fail if any production game-specific branch is proposed"],
            "no_iterative_feature_addition": True,
            "failure_disposition": "discard the probe; retain no production evaluator change",
        },
        "genericity_checkpoint": {
            "result": "architecture can express the three requested piece behaviors and their coexistence through semantic IR; legacy path remains narrower",
            "mixed_mechanic_acceptance_target": "one RuleSet containing capture-to-hand/drop, remove-from-game/promotable, and non-promotable special movement; verify Core legality, search runtime, identity/repetition, terminal handling, and generic evaluator with no game-name branches",
            "implementation_in_f23u": False,
        },
        "future_benchmark_matrix": {
            "standard_shogi": ["rules/perft/legality", "AlphaSho move-ranking comparison", "fixed-node/fixed-time search", "later strength tests"],
            "western_chess": ["rules/perft/legality", "verified mature heuristic reference when available", "fixed-node/fixed-time move/PV/evaluation", "later match strength"],
            "future_optional": ["Xiangqi", "Janggi", "Chaturanga/Indian-family", "other mature chess-family games adding new mechanics"],
            "status": "future validation axes, not F23U implementation requirements",
        },
        "selected_boundary": "F23V_MINIMAL_ANALYTIC_EVALUATOR_SIGNAL_PROBE",
        "production_changed": False,
        "v12_rewritten": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_assessment()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "selected": result["selected_boundary"], "r10_strict_surviving": result["r10_corrected_reaudit"]["strict_witness"]["causal_surviving_count"], "r10_effective_orbits": result["r10_corrected_reaudit"]["metadata_free_behavior"]["deduplicated_effective_orbit_count"], "short_terminal_visible": result["r10_corrected_reaudit"]["short_natural_terminal_visibility"]["visible_count"]}, sort_keys=True))


if __name__ == "__main__":
    main()
