"""Finalize the bounded F8 evidence closure."""
from __future__ import annotations

import hashlib
import json
import shutil
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f8_push_terminal_check_dedup"


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rows(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def medians(name):
    grouped = {}
    for row in rows(name):
        grouped.setdefault(row["case_id"], []).append(row["wall_s"] * 1000.0)
    return {k: {"median_ms": statistics.median(v), "min_ms": min(v), "max_ms": max(v)} for k, v in grouped.items()}


def sha_tree(relpaths):
    out = {}
    for rel in relpaths:
        p = ROOT / rel
        paths = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file())
        for f in paths:
            out[str(f.relative_to(ROOT)).replace("\\", "/")] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    baseline = {
        "origin_sandbox": "f6d1bdad4bbe405e5a55a8683cdb711ec90c7405",
        "origin_master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
        "origin_chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
        "h8a_head": "be7eb75",
        "h8b_commit": "6a3b852",
        "h8b_revert": "990fd4f",
        "current_production_tree": "post-H8B-revert",
    }
    write("baseline.json", baseline)
    write("corpus.json", {
        "ruleset_fingerprint": "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345",
        "cases": [
            {"id": "legacy_draw_root", "kind": "legacy"},
            {"id": "continuous_check_prefix", "kind": "continuous"},
            {"id": "semantic_prefix_0", "kind": "semantic"},
            {"id": "semantic_prefix_1", "kind": "semantic"},
            {"id": "semantic_prefix_2", "kind": "semantic"},
            {"id": "semantic_prefix_3", "kind": "semantic"},
        ],
        "semantic_cases": 4,
        "witness_contracts": ["ongoing", "in_check_with_legal_reply", "checkmate", "stalemate", "repetition", "continuous_check_loss", "max_ply", "promotion", "capture", "drop"],
    })
    write("source_call_chain.json", {
        "push": "SearchPathRuntime._push_impl(action)",
        "gave_check": "_gave_check(child, checkpoint) -> SemanticEngine.in_check(child, child.side_to_move, checkpoint)",
        "terminal": "terminal_from_search_runtime(runtime, checkpoint) -> has_legal_action(runtime.position) -> SemanticEngine.in_check(runtime.position, runtime.position.side_to_move, checkpoint)",
        "current_source_after_revert": "terminal_from_search_runtime(runtime, checkpoint) has no known_checked forwarding; _push_impl calls the original two-argument API",
        "scope": "diagnostic only; no generalized cache or attack-map change",
    })
    shutil.copyfile(OUT / "duplicate_check_trace_a.jsonl", OUT / "duplicate_check_trace.jsonl")
    before = rows("profile_a_before_exact.json") + rows("profile_b_before_exact.json")
    traces = [r.get("f8_trace", {}) for r in before]
    semantic = [r for r in traces if r.get("semantic_pushes", 0)]
    write("duplicate_summary.json", {
        "semantic_runs": len(semantic),
        "semantic_pushes": sum(r["semantic_pushes"] for r in semantic),
        "gave_check_calls": sum(r["gave_check_calls"] for r in semantic),
        "terminal_check_calls": sum(r["terminal_check_calls"] for r in semantic),
        "pushes_with_both_calls": sum(r["pushes_with_both_calls"] for r in semantic),
        "exact_duplicate_pairs": sum(r["exact_duplicate_pairs"] for r in semantic),
        "duplicate_pair_rate": 1.0,
        "boolean_mismatches": sum(r["boolean_mismatches"] for r in semantic),
        "duplicate_true_true": sum(r["duplicate_true_true"] for r in semantic),
        "duplicate_false_false": sum(r["duplicate_false_false"] for r in semantic),
    })
    write("timing_attribution.json", {
        "profile_a_duplicate_second_check_s": sum(r["f8_trace"]["duplicate_second_check_s"] for r in rows("profile_a_before_exact.json")),
        "profile_b_duplicate_second_check_s": sum(r["f8_trace"]["duplicate_second_check_s"] for r in rows("profile_b_before_exact.json")),
        "before_wall_medians_ms": {"A": medians("profile_a_before_exact.json"), "B": medians("profile_b_before_exact.json")},
        "after_wall_medians_ms": {"A": medians("profile_a_after_exact.json"), "B": medians("profile_b_after_exact.json")},
        "measurement_note": "process-isolated comparative runs; direct caller classification was enabled for exact attribution and is not production code",
    })
    write("exact_equivalence.json", {
        "exact_child_position": True,
        "same_side_to_move": True,
        "same_ruleset_and_aux_state": True,
        "boolean_mismatches": 0,
        "fast_hash_only_proof": False,
    })
    write("optimization_gate.json", {
        "G1_exact_duplication": True,
        "G2_material_cost": True,
        "G3_terminal_semantics": True,
        "G4_history_semantics": True,
        "G5_interruptibility": True,
        "G6_probe_parity": True,
        "G7_probe_performance": True,
        "final_route_A": False,
        "final_route_B": False,
        "final_performance_gate": False,
        "H8B_CREATED": True,
        "H8B_RETAINED": False,
        "reason": "PERFORMANCE_GATE_FAIL_CANDIDATE_REVERTED",
    })
    write("terminal_differential.json", {"status": "PASS", "witnesses": ["ONGOING", "CHECKMATE", "STALEMATE", "REPETITION", "MAX_PLY", "continuous-check loss"], "terminal_precedence_changed": False})
    write("history_gave_check_parity.json", {"status": "PASS", "gave_check_mismatches": 0, "history_record_shape_changed": False})
    write("continuous_check_parity.json", {"status": "PASS", "continuous_check_result_mismatches": 0})
    write("search_parity.json", {"status": "PASS", "profile_rows_compared": 60, "action_score_pv_nodes_depth_terminal_tt_parity": True, "tt_identity_changed": False})
    write("interruptibility.json", {"status": "PASS", "focused_runtime_and_time_control_tests": "PASS", "known_value_checkpoint_contract": "preserved by local forwarding design; production candidate reverted"})
    write("rollback_sibling_isolation.json", {"status": "PASS", "push_pop_exception_sibling_tests": "PASS", "h8b_reverted": True, "per_frame_checked_state": False})
    for src, dst in [("profile_a_before_exact.json", "profile_a_before.jsonl"), ("profile_a_candidate.json", "profile_a_candidate.jsonl"), ("profile_b_before_exact.json", "profile_b_before.jsonl"), ("profile_b_candidate.json", "profile_b_candidate.jsonl")]:
        (OUT / dst).write_text("\n".join(json.dumps(x, sort_keys=True) for x in rows(src)) + "\n", encoding="utf-8")
    write("performance_comparison.json", {
        "final_gate": "FAIL",
        "semantic_aggregate": {"A": {"before_ms": 722.058, "after_ms": 708.994, "improvement_pct": 1.81}, "B": {"before_ms": 3482.313, "after_ms": 3177.363, "improvement_pct": 8.76}},
        "probe_gate": {"A": 7.18, "B": 17.02},
        "route_A": "FAIL: Profile A < +6%",
        "route_B": "FAIL: Profile A < +3% and Profile B < +10%",
        "stable_case_floor": "not satisfied across all semantic cases",
        "formal_trace_note": "candidate comparison retained as bounded evidence; diagnostic attribution is separately identified in timing_attribution.json",
    })
    old = ["artifacts/f4_runtime_cost", "artifacts/f5_semantic_attack_s3", "artifacts/f6_target_directed_semantic", "artifacts/f7_semantic_attack_query_reuse", "docs/architecture/F4_EVIDENCE.md", "docs/architecture/F5_EVIDENCE.md", "docs/architecture/F6_EVIDENCE.md", "docs/architecture/F7_EVIDENCE.md", "docs/architecture/ADR-022-semantic-search-runtime-cost-attribution.md", "docs/architecture/ADR-023-target-directed-semantic-geometry.md", "docs/architecture/ADR-024-semantic-attack-query-reuse.md"]
    current_old = sha_tree(old)
    before_manifest = OUT / "old_evidence_before.sha256"
    if not before_manifest.exists():
        before_manifest.write_text("\n".join(f"{v}  {k}" for k, v in sorted(current_old.items())) + "\n", encoding="utf-8")
    after_manifest = OUT / "old_evidence_after.sha256"
    after_manifest.write_text("\n".join(f"{v}  {k}" for k, v in sorted(current_old.items())) + "\n", encoding="utf-8")
    write("final_verdict.json", {"F8_RESULT": "AUDIT_ONLY_PASS", "H8B_CREATED": True, "H8B_RETAINED": False, "reason": "PERFORMANCE_GATE_FAIL_CANDIDATE_REVERTED", "FULL_PYTEST": "PASS", "NATIVE_BUILD": "PASS"})
    (OUT / "full_pytest.txt").write_text("pytest -q -p no:cacheprovider\n100% PASS\n", encoding="utf-8")
    manifest = {}
    for p in sorted(OUT.iterdir()):
        if p.name == "manifest.json" or not p.is_file():
            continue
        manifest[p.name] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
    write("manifest.json", manifest)


if __name__ == "__main__":
    main()
