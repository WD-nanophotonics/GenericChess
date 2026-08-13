"""Materialize the H11A post-F10 re-baseline evidence."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "f11_post_f10_rebaseline"


def write(name, value):
    (ART / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rows(profile):
    return [json.loads(line) for line in (ART / f"whole_search_profile_{profile}.jsonl").read_text(encoding="utf-8").splitlines()]


def aggregate(profile):
    data = rows(profile)
    semantic = [r for r in data if r["case_id"].startswith("semantic_")]
    by_case = defaultdict(list)
    for row in semantic:
        by_case[row["case_id"]].append(row)
    cases = {}
    for case, values in sorted(by_case.items()):
        walls = [v["wall_s"] for v in values]
        cases[case] = {
            "median_s": statistics.median(walls),
            "p90_s": sorted(walls)[max(0, int(len(walls) * 0.9) - 1)],
            "min_s": min(walls),
            "max_s": max(walls),
            "median_nodes": statistics.median(v["nodes"] for v in values),
            "median_qnodes": statistics.median(v["qnodes"] for v in values),
            "completed_depths": sorted(set(v["completed_depth"] for v in values)),
            "termination_reasons": sorted(set(v["termination_reason"] for v in values)),
        }
    category = defaultdict(lambda: {"calls": 0, "inclusive_s": 0.0})
    structural = defaultdict(int)
    for row in semantic:
        for name, value in row["f11_probe"].items():
            category[name]["calls"] += value["calls"]
            category[name]["inclusive_s"] += value["inclusive_s"]
        for name, value in row["f11_structural_counts"].items():
            structural[name] += value
    return {
        "rows": len(data),
        "semantic_rows": len(semantic),
        "semantic_wall_sum_s": sum(v["wall_s"] for v in semantic),
        "semantic_cases": cases,
        "category_totals": dict(category),
        "structural_totals": dict(structural),
    }


def main():
    ART.mkdir(parents=True, exist_ok=True)
    write("baseline.json", {
        "origin/sandbox": "83b921a07277ca7186f66a65ecc95fb040838a34",
        "origin/master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
        "origin/chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
        "ruleset_fingerprint": "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345",
        "gmail_message_id": "19ffc98a5c4d7faa",
    })
    write("corpus.json", {
        "semantic_prefixes": [f"semantic_prefix_{i}" for i in range(4)],
        "controls": ["legacy_draw_root", "continuous_check_prefix"],
        "repetitions": 5,
        "warmup": 1,
        "certified_fingerprint": "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345",
    })
    write("tuning.json", {
        "A": {"tt": True, "ordering": False, "quiescence_max_depth": 0, "max_depth": 2, "max_nodes": 512, "wall_clock": False, "fresh_tt": True},
        "B": {"production_features": True, "max_depth": 2, "max_nodes": 256, "wall_clock": False, "fresh_tt": True},
    })
    a, b = aggregate("a"), aggregate("b")
    write("category_attribution.json", {
        "Profile A": a["category_totals"],
        "Profile B": b["category_totals"],
        "methodology": "Inclusive timings are reported per category; nested categories are not summed as a wall decomposition. cProfile self-time is the non-overlap authority for ranking.",
    })
    write("structural_counts.json", {"Profile A": a["structural_totals"], "Profile B": b["structural_totals"], "stats_fields": "See each whole-search JSONL row for pushes/pops, history/hash, legal actions, successors, evaluation, qnodes, and TT counters."})
    write("hotspot_ranking.json", [
        {"rank": 1, "name": "semantic attack/check path", "scope": "necessary semantic work; inclusive/nested", "representative_functions": ["SemanticEngine.in_check", "SemanticEngine.is_square_attacked", "pseudo_attacks", "geometry_candidates"], "profile_a_cost": "dominant inclusive category; cProfile is_square_attacked self 0.349s / 18.1%", "profile_b_cost": "dominant inclusive category; cProfile is_square_attacked self 2.237s / 23.1%", "root_cause": "Every candidate legality/check path evaluates exact attack truth.", "why_after_f10": "F10 only shortened legality-operation source-index lifetime; attack queries remain isolated by contract.", "possible_local_optimization": "attack memoization/target-directed geometry", "class": "necessary/forbidden architecture", "semantic_risk": "high", "architectural_risk": "high", "expected_benefit": "material but forbidden in F11"},
        {"rank": 2, "name": "checkpoint dispatch", "scope": "non-overlap/self", "representative_functions": ["semantic_executor._checkpoint", "search._Context.checkpoint"], "profile_a_cost": "0.486s executor self plus 0.186s callback self in representative cProfile", "profile_b_cost": "1.896s executor self plus 1.201s callback self in representative cProfile", "root_cause": "Cooperative node-limit checks are called at semantic loop boundaries.", "why_after_f10": "F4 already specialized fixed-node checkpoint policy; remaining checks preserve bounded interruption/node-limit semantics.", "possible_local_optimization": "further dispatch reduction", "class": "necessary runtime safety / closed F4 family", "semantic_risk": "medium", "architectural_risk": "medium", "expected_benefit": "uncertain without changing checkpoint coverage"},
        {"rank": 3, "name": "runtime push/terminal/hash", "scope": "partially nested", "representative_functions": ["SearchPathRuntime._push_impl", "terminal_from_search_runtime", "_semantic_component_diff_hash"], "profile_a_cost": "push inclusive about 5.714s across semantic audit rows", "profile_b_cost": "push inclusive about 27.710s across semantic audit rows", "root_cause": "Exact child transition, terminal precedence, identity, and history updates.", "why_after_f10": "F10 addresses only source-index lifetime; runtime identity/history remains required.", "possible_local_optimization": "global/terminal cache or identity redesign", "class": "necessary/forbidden architecture", "semantic_risk": "high", "architectural_risk": "high", "expected_benefit": "not eligible"},
        {"rank": 4, "name": "geometry candidate enumeration", "scope": "non-overlap/self", "representative_functions": ["rules.ir.geometry_candidates", "SemanticEngine._iter_board_candidates"], "profile_a_cost": "cProfile geometry generator self 0.118s / 6.1%", "profile_b_cost": "cProfile geometry generator self 0.758s / 7.8%", "root_cause": "Exact canonical geometry/path enumeration.", "why_after_f10": "F10 does not alter geometry enumeration.", "possible_local_optimization": "local allocation/dispatch reduction", "class": "allowed but subdominant", "semantic_risk": "medium", "architectural_risk": "medium", "expected_benefit": "below G1 without a broad rewrite"},
        {"rank": 5, "name": "source-index construction residual", "scope": "attack-query dominated", "representative_functions": ["_sources_by_owner_type"], "profile_a_cost": "cProfile self 0.059s / 3.1%", "profile_b_cost": "cProfile self 0.379s / 3.9%", "root_cause": "Independent attack queries intentionally rebuild local dispatch.", "why_after_f10": "F10 deliberately does not create cross-query/general caches.", "possible_local_optimization": "F7-style memoization", "class": "forbidden", "semantic_risk": "high", "architectural_risk": "high", "expected_benefit": "not eligible"},
        {"rank": 6, "name": "evaluator and evaluator-side anchor escape", "scope": "non-overlap/inclusive", "representative_functions": ["Evaluator.evaluate", "Evaluator._anchor_escape"], "profile_a_cost": "representative cProfile evaluate cumulative 0.537s", "profile_b_cost": "representative cProfile evaluate cumulative 0.283s", "root_cause": "Necessary score computation and anchor safety evaluation.", "why_after_f10": "Independent of source-index reuse.", "possible_local_optimization": "exact evaluator implementation optimization", "class": "allowed but not dominant", "semantic_risk": "high", "architectural_risk": "medium", "expected_benefit": "below G1 on current corpus"},
    ])
    write("candidate_matrix.json", [
        {"family": "attack memoization / target-directed geometry", "status": "FORBIDDEN", "reason": "F6/F7 forbidden classes; no F11 resurrection"},
        {"family": "general Position/terminal cache", "status": "FORBIDDEN", "reason": "explicit F11 scope prohibition"},
        {"family": "checkpoint dispatch reduction", "status": "NO_AUTHORIZATION", "reason": "F4 family already closed; exact node-limit/interruptibility coverage makes no local probe clearly safe"},
        {"family": "geometry enumeration allocation reduction", "status": "NO_CLEAR_SINGLE_WINNER", "reason": "below 12% in both representative self-time profiles and no end-to-end material probe"},
        {"family": "identity/history/runtime redesign", "status": "FORBIDDEN", "reason": "architecture redesign and TT/history semantic risk"},
        {"family": "evaluator implementation", "status": "NO_CLEAR_SINGLE_WINNER", "reason": "not dominant under current whole-search evidence; exact score corpus would be required"},
    ])
    write("single_winner_decision.json", {"selected": None, "status": "NO_CLEAR_SINGLE_WINNER", "H11B_CREATED": False, "reason": "No allowed Python-local family is both clearly dominant and locally probeable after F10."})
    write("optimization_gate.json", {"G1_material": False, "G2_explained": True, "G3_local": False, "G4_semantics": "NOT_RUN_NOT_AUTHORIZED", "G5_testable": "NOT_RUN_NOT_AUTHORIZED", "G6_probe": "NOT_RUN_NOT_AUTHORIZED", "reason": "NO_CLEAR_SINGLE_WINNER"})
    write("python_local_headroom.json", {"value": "LIMITED", "reason": "Current dominant work is necessary semantic attack/check and runtime safety, while remaining eligible Python-local work is subdominant or lacks a safe material probe.", "recommended_next_boundary": "NATIVE_SEMANTIC_EXECUTION_AUDIT"})


if __name__ == "__main__":
    main()
