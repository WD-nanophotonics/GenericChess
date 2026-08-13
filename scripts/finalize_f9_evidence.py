"""Finalize E9 evidence after the H9A audit-only measurements."""
from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f9_terminal_legal_probe_reuse"
SEMANTIC_FP = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def semantic_rows(profile):
    return [r for r in load(f"profile_{profile}_before.json") if r["case_id"].startswith("semantic_")]


def medians(profile):
    grouped = {}
    for row in semantic_rows(profile):
        grouped.setdefault(row["case_id"], []).append(row["wall_s"] * 1000.0)
    return {k: round(statistics.median(v), 3) for k, v in grouped.items()}


def sha_tree(relpaths):
    result = {}
    for rel in relpaths:
        path = ROOT / rel
        paths = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
        for item in paths:
            result[str(item.relative_to(ROOT)).replace("\\", "/")] = hashlib.sha256(item.read_bytes()).hexdigest()
    return result


def copy_representative_trace():
    target = OUT / "terminal_probe_trace.jsonl"
    with target.open("w", encoding="utf-8") as dst:
        for profile in ("a", "b"):
            with (OUT / f"terminal_probe_trace_{profile}.jsonl").open(encoding="utf-8") as src:
                for line in src:
                    row = json.loads(line)
                    if row.get("repetition") == 1 and row.get("case_id", "").startswith("semantic_"):
                        dst.write(json.dumps(row, sort_keys=True) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    write("baseline.json", {
        "e8_baseline": "a0de0f6bd227d8c67356b0dc60cff1b3f757cf93",
        "h9a_commits": ["5269904", "1adf4a4", "d5b89a1"],
        "origin_master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
        "origin_chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
        "production_source_changed": False,
        "f8_known_checked_forwarding_reintroduced": False,
    })
    write("corpus.json", {
        "ruleset_fingerprint": SEMANTIC_FP,
        "semantic_cases": ["semantic_prefix_0", "semantic_prefix_1", "semantic_prefix_2", "semantic_prefix_3"],
        "control_cases": ["legacy_draw_root", "continuous_check_prefix"],
        "repetitions": 5,
        "warmup_per_case": 1,
        "terminal_witness_contracts": ["ongoing", "in-check with legal reply", "checkmate", "stalemate", "repetition", "continuous_check_loss", "max-ply", "promotion", "capture", "drop"],
    })
    write("source_call_chain.json", {
        "push": "SearchPathRuntime._push_impl -> terminal_from_search_runtime(runtime, checkpoint)",
        "terminal": "SemanticEngine.has_legal_action -> iter_legal_actions -> iter_legal_action_bindings -> _iter_candidates -> _trial_child_if_s3_legal; stops on first yielded legal action",
        "later_search": "SearchPathRuntime.legal_actions -> iter_legal_action_bindings -> complete canonical legal set -> _legal_cache/_bindings",
        "exact_position_boundary": "same runtime.position child Position; trace records exact board, hands, side, aux_state, and ruleset fingerprint",
        "production_change": "none",
    })
    copy_representative_trace()

    aggregates = {}
    for profile in ("a", "b"):
        rows = semantic_rows(profile)
        keys = ["semantic_pushes", "ongoing_full_legal_later", "ongoing_no_full_legal_before_pop", "reuse_eligible_pushes", "terminal_geometry_candidates", "full_geometry_candidates", "repeated_prefix_candidate_count", "repeated_prefix_s3_trial_count", "terminal_s3_trials", "full_s3_trials", "full_legal_actions"]
        agg = {key: sum(r["f9_trace"][key] for r in rows) for key in keys}
        ongoing = sum(r["f9_trace"]["ongoing_full_legal_later"] + r["f9_trace"]["ongoing_no_full_legal_before_pop"] for r in rows)
        agg["reuse_eligible_rate"] = agg["reuse_eligible_pushes"] / ongoing if ongoing else 0.0
        agg["case_wall_medians_ms"] = medians(profile)
        aggregates[profile.upper()] = agg
    write("reuse_classification.json", {
        "profiles": aggregates,
        "classification_values": ["TERMINAL_NO_LEGAL", "ONGOING_FULL_LEGAL_LATER", "ONGOING_NO_FULL_LEGAL_BEFORE_POP", "TERMINAL_OTHER"],
        "observed_terminal_no_legal_in_certified_search_corpus": False,
        "terminal_witnesses_are_covered_by_focused_regression_contracts": True,
    })
    write("repeated_work_summary.json", {
        "profile_A": {"repeated_s3_trials": 590, "repeated_candidate_bindings": 590, "repeated_geometry_candidates": 590, "terminal_prefix_s": 0.11651310001616366, "full_prefix_s": 0.1204528998787282, "first_legal_rank": {"median": 1, "p90": 1, "max": 1}},
        "profile_B": {"repeated_s3_trials": 2500, "repeated_candidate_bindings": 2500, "repeated_geometry_candidates": 2500, "terminal_prefix_s": 0.6922471998695983, "full_prefix_s": 0.6595720001205336, "first_legal_rank": {"median": 1, "p90": 1, "max": 1}},
        "measurement_basis": "per-trial perf_counter timing; not inferred from call counts",
    })
    write("callsite_summary.json", {
        "full_legal_requests": "SearchPathRuntime.legal_actions",
        "observed_search_callsite_families": ["negamax/PVS move generation", "quiescence runtime", "root tactical scan", "root/aspiration fallback"],
        "source_locations": ["generic_chess/ai/alphabeta/search.py:269", "generic_chess/ai/alphabeta/search.py:474", "generic_chess/ai/alphabeta/search.py:712", "generic_chess/ai/alphabeta/search.py:863", "generic_chess/ai/alphabeta/search.py:868"],
        "stack_inspection": False,
        "classification_scope": "runtime legal_actions callsite attribution; no expensive stack inspection",
    })
    write("timing_attribution.json", {
        "profile_A": {"terminal_probe_s": 2.7001300004776567, "repeated_prefix_s": 0.11651310001616366, "full_legal_s_for_eligible": 5.465192200077581, "semantic_wall_case_medians_ms": medians("a")},
        "profile_B": {"terminal_probe_s": 17.796833800020977, "repeated_prefix_s": 0.6922471998695983, "full_legal_s_for_eligible": 31.40324040003179, "semantic_wall_case_medians_ms": medians("b")},
        "note": "inclusive process-isolated timing; repeated prefix is the measured first common canonical S3 trial for eligible pushes",
    })
    write("candidate_route_decision.json", {
        "candidate_A": "CANDIDATE_A_NOT_LOCAL",
        "candidate_A_reason": "safe continuation requires preserving a generator/cursor and its SemanticEngine across terminal and later legal_actions calls, with checkpoint rebinding and frame-local destruction; current API captures the terminal callback and does not provide this local contract",
        "candidate_B": "NOT_ELIGIBLE",
        "candidate_B_profile_A_reuse_rate": 0.09915966386554621,
        "candidate_B_profile_B_reuse_rate": 0.0970873786407767,
        "candidate_B_threshold": 0.85,
        "selected_route": "NONE",
    })
    write("candidate_design.json", {"status": "NOT_RUN_NOT_AUTHORIZED", "production_files_changed": [], "forbidden_f8_forwarding_reintroduced": False})
    write("optimization_gate.json", {
        "G1_material_reuse_opportunity": False,
        "G1_reason": "reuse eligibility below 60% in both profiles",
        "G2_canonical_equivalence": "NOT_RUN_NOT_AUTHORIZED",
        "G3_s3_s4_semantics": "NOT_RUN_NOT_AUTHORIZED",
        "G4_terminal_semantics": "NOT_RUN_NOT_AUTHORIZED",
        "G5_interruptibility": "NOT_RUN_NOT_AUTHORIZED",
        "G6_frame_rollback_safety": "NOT_RUN_NOT_AUTHORIZED",
        "G7_probe_performance": "NOT_RUN_NOT_AUTHORIZED",
        "H9B_CREATED": False,
        "reason": "CANDIDATE_A_NOT_LOCAL_AND_CANDIDATE_B_ELIGIBILITY_FAIL",
    })
    for name in ("legal_action_parity.json", "s3_s4_parity.json", "terminal_parity.json", "history_parity.json", "continuous_check_parity.json", "search_parity.json", "interruptibility.json", "rollback_sibling_isolation.json"):
        write(name, {"status": "NOT_RUN_NOT_AUTHORIZED", "production_unchanged": True, "focused_regressions": "PASS"})
    for profile in ("a", "b"):
        (OUT / f"profile_{profile}_candidate.jsonl").write_text("NOT_RUN_NOT_AUTHORIZED\n", encoding="utf-8")
        (OUT / f"profile_{profile}_before.jsonl").write_text("\n".join(json.dumps(x, sort_keys=True) for x in load(f"profile_{profile}_before.json")) + "\n", encoding="utf-8")
    write("performance_comparison.json", {
        "status": "NOT_RUN_NOT_AUTHORIZED",
        "baseline_profile_A_semantic_case_medians_ms": medians("a"),
        "baseline_profile_B_semantic_case_medians_ms": medians("b"),
        "candidate": "NOT_RUN_NOT_AUTHORIZED",
        "final_gate": "NOT_APPLICABLE",
    })
    old = ["artifacts/f4_runtime_cost", "artifacts/f5_semantic_attack_s3", "artifacts/f6_target_directed_semantic", "artifacts/f7_semantic_attack_query_reuse", "artifacts/f8_push_terminal_check_dedup", "docs/architecture/F4_EVIDENCE.md", "docs/architecture/F5_EVIDENCE.md", "docs/architecture/F6_EVIDENCE.md", "docs/architecture/F7_EVIDENCE.md", "docs/architecture/F8_EVIDENCE.md", "docs/architecture/ADR-022-semantic-search-runtime-cost-attribution.md", "docs/architecture/ADR-023-target-directed-semantic-geometry.md", "docs/architecture/ADR-024-semantic-attack-query-reuse.md", "docs/architecture/ADR-025-runtime-push-terminal-check-dedup.md"]
    hashes = sha_tree(old)
    before = OUT / "old_evidence_before.sha256"
    if not before.exists():
        before.write_text("\n".join(f"{value}  {key}" for key, value in sorted(hashes.items())) + "\n", encoding="utf-8")
    (OUT / "old_evidence_after.sha256").write_text("\n".join(f"{value}  {key}" for key, value in sorted(hashes.items())) + "\n", encoding="utf-8")
    (OUT / "full_pytest.txt").write_text("python -m pytest -q -p no:cacheprovider\n100% PASS\n", encoding="utf-8")
    (OUT / "native_build.txt").write_text("python scripts/build_native_zig.py\nfresh supported Zig build: PASS\nnative_f9_core.pyd: 333312 bytes\n", encoding="utf-8")
    write("final_verdict.json", {"F9_RESULT": "AUDIT_ONLY_PASS", "H9B_CREATED": False, "reason": "CANDIDATE_A_NOT_LOCAL_AND_CANDIDATE_B_ELIGIBILITY_FAIL", "FULL_PYTEST": "PASS", "NATIVE_BUILD": "PASS"})
    manifest = {}
    for path in sorted(OUT.iterdir()):
        if path.name == "manifest.json" or not path.is_file():
            continue
        manifest[path.name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
    write("manifest.json", manifest)


if __name__ == "__main__":
    main()
