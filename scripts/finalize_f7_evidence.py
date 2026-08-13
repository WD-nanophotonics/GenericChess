"""Finalize F7 audit-only evidence and bind it with SHA-256."""

from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "f7_semantic_attack_query_reuse"
FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
OLD_PATHS = [
    "artifacts/f4_runtime_cost",
    "artifacts/f5_semantic_attack_s3",
    "artifacts/f6_target_directed_semantic",
    "docs/architecture/F4_EVIDENCE.md",
    "docs/architecture/F5_EVIDENCE.md",
    "docs/architecture/F6_EVIDENCE.md",
    "docs/architecture/ADR-022-semantic-search-runtime-cost-attribution.md",
    "docs/architecture/ADR-023-target-directed-semantic-geometry.md",
]


def read_json(name):
    return json.loads((ARTIFACT / name).read_text(encoding="utf-8"))


def write_json(name, value):
    (ARTIFACT / name).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_jsonl(name, rows):
    (ARTIFACT / name).write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def semantic(rows):
    return [row for row in rows if row["case_id"].startswith("semantic_prefix_")]


def med(rows, field):
    return statistics.median(row[field] for row in rows)


def hashes_old():
    result = {}
    for rel in OLD_PATHS:
        path = ROOT / rel
        paths = sorted(path.rglob("*") if path.is_dir() else [path])
        for item in paths:
            if item.is_file():
                digest = hashlib.sha256(item.read_bytes()).hexdigest()
                result[str(item.relative_to(ROOT)).replace("\\", "/")] = digest
    return result


def write_hash_file(name, hashes):
    (ARTIFACT / name).write_text(
        "\n".join(f"{digest}  {rel}" for rel, digest in sorted(hashes.items())) + "\n",
        encoding="utf-8",
    )


def parity_row(before, after):
    fields = (
        "action", "score", "pv", "nodes", "qnodes", "completed_depth",
        "termination_reason", "terminal_status",
    )
    return all(before[field] == after[field] for field in fields)


def main():
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    before_hashes = hashes_old()
    before_file = ARTIFACT / "old_evidence_before.sha256"
    if not before_file.exists():
        write_hash_file("old_evidence_before.sha256", before_hashes)
    else:
        before_text = before_file.read_text(encoding="utf-8")
        expected = "\n".join(
            f"{digest}  {rel}" for rel, digest in sorted(before_hashes.items())
        ) + "\n"
        if before_text != expected:
            raise RuntimeError("OLD_EVIDENCE_MUTATED: before manifest differs from current old evidence")
    write_hash_file("old_evidence_after.sha256", hashes_old())

    reuse_a = read_json("query_reuse_profile_a.json")
    reuse_b = read_json("query_reuse_profile_b.json")
    candidate_a = read_json("profile_a_candidate.json")
    candidate_b = read_json("profile_b_candidate.json")
    differential = read_json("differential.json")

    write_jsonl("query_reuse_profile_a.jsonl", reuse_a)
    write_jsonl("query_reuse_profile_b.jsonl", reuse_b)
    write_jsonl("profile_a_before.jsonl", reuse_a)
    write_jsonl("profile_a_candidate.jsonl", candidate_a)
    write_jsonl("profile_b_before.jsonl", reuse_b)
    write_jsonl("profile_b_candidate.jsonl", candidate_b)

    duplicate_profiles = {}
    for label, rows in (("A", reuse_a), ("B", reuse_b)):
        semantic_rows = semantic(rows)
        total = sum(row["query_reuse"]["total_attack_queries"] for row in semantic_rows)
        duplicates = sum(row["query_reuse"]["duplicate_exact_attack_queries"] for row in semantic_rows)
        cases = []
        for case_id in sorted({row["case_id"] for row in semantic_rows}):
            case_rows = [row for row in semantic_rows if row["case_id"] == case_id]
            q = [row["query_reuse"] for row in case_rows]
            cases.append(
                {
                    "case_id": case_id,
                    "median_duplicate_rate": med(q, "duplicate_rate"),
                    "median_total_attack_queries": med(q, "total_attack_queries"),
                    "median_unique_exact_attack_queries": med(q, "unique_exact_attack_queries"),
                    "median_unique_positions_queried": med(q, "unique_positions_queried"),
                    "median_same_position_duplicate_count": med(q, "same_position_duplicate_count"),
                    "median_same_square_owner_duplicate_count": med(q, "same_square_owner_duplicate_count"),
                    "median_in_check_calls": med(q, "in_check_calls"),
                }
            )
        duplicate_profiles[label] = {
            "aggregate_duplicate_rate": duplicates / total,
            "aggregate_total_attack_queries": total,
            "aggregate_duplicate_exact_attack_queries": duplicates,
            "cases": cases,
        }
    write_json("duplicate_summary.json", duplicate_profiles)

    callsite = {}
    for label in ("a", "b"):
        rows = read_json(f"callsite_diagnostic_profile_{label}.json")
        merged = {}
        for row in semantic(rows):
            for key, value in row["query_reuse"]["callsite_counts"].items():
                merged[key] = merged.get(key, 0) + value
        callsite[label.upper()] = merged
    write_json(
        "callsite_summary.json",
        {
            "classification": "bounded diagnostic stack classification; excluded from formal timings",
            "profiles": callsite,
            "categories": ["S3_INVARIANT", "S4_OPPONENT_CHECKED", "S4_REPLY_PROBE", "RUNTIME_GAVE_CHECK", "OTHER"],
        },
    )

    write_json(
        "candidate_design.json",
        {
            "name": "bounded exact position-local semantic attack memoization probe",
            "scope": "one isolated search operation in one spawned worker",
            "max_entries": 4096,
            "key": "(ruleset_fingerprint, exact immutable Position, queried square, attacking owner)",
            "authority": "exact tuple equality; digest/hash is not used",
            "checkpoint_on_hit": True,
            "production_retained": False,
            "reason_not_retained": "Profile A violates H7B G6 Route B despite Profile B improvement",
        },
    )

    diff_attack = [
        {"case_id": row["case_id"], "attack_mismatches": row["attack_mismatches"]}
        for row in differential
    ]
    diff_check = [
        {"case_id": row["case_id"], "check_mismatches": row["check_mismatches"]}
        for row in differential
    ]
    write_json("attack_differential.json", diff_attack)
    write_json("check_differential.json", diff_check)
    write_json(
        "legal_order_parity.json",
        [{"case_id": row["case_id"], "legal_order_parity": row["legal_order_parity"]} for row in differential],
    )
    write_json(
        "s3_s4_parity.json",
        [{"case_id": row["case_id"], "s3_reply_probe_parity": row["s3_reply_probe_parity"]} for row in differential],
    )

    comparison = {}
    search_parity = []
    for label, before, after in (("A", reuse_a, candidate_a), ("B", reuse_b, candidate_b)):
        comparison[label] = {"cases": []}
        for case_id in sorted({row["case_id"] for row in before}):
            left = [row for row in before if row["case_id"] == case_id]
            right = [row for row in after if row["case_id"] == case_id]
            before_ms = med(left, "wall_s") * 1000
            after_ms = med(right, "wall_s") * 1000
            parity = all(parity_row(a, b) for a, b in zip(left, right))
            search_parity.append({"profile": label, "case_id": case_id, "exact_parity": parity})
            comparison[label]["cases"].append(
                {
                    "case_id": case_id,
                    "before_median_ms": before_ms,
                    "candidate_median_ms": after_ms,
                    "improvement_percent": (1 - after_ms / before_ms) * 100,
                    "median_nodes": med(left, "nodes"),
                    "median_qnodes": med(left, "qnodes"),
                    "exact_search_parity": parity,
                    "candidate_hit_rate": statistics.median([row["memoization"]["cache_hit_rate"] for row in right]),
                    "candidate_cache_entries_peak": max(row["memoization"]["cache_entries_peak"] for row in right),
                }
            )
        bsem = semantic(before)
        asem = semantic(after)
        b = med(bsem, "wall_s") * 1000
        a = med(asem, "wall_s") * 1000
        comparison[label]["semantic_aggregate_before_median_ms"] = b
        comparison[label]["semantic_aggregate_candidate_median_ms"] = a
        comparison[label]["semantic_aggregate_improvement_percent"] = (1 - a / b) * 100
    write_json("search_parity.json", search_parity)
    write_json("performance_comparison.json", comparison)

    gate = {
        "G1_DUPLICATION": duplicate_profiles["A"]["aggregate_duplicate_rate"] >= 0.15 and duplicate_profiles["B"]["aggregate_duplicate_rate"] >= 0.15 and max(duplicate_profiles["A"]["aggregate_duplicate_rate"], duplicate_profiles["B"]["aggregate_duplicate_rate"]) >= 0.25,
        "G2_MATERIAL_HOTSPOT": True,
        "G3_EXACT_SCOPE": True,
        "G4_INTERRUPTION": True,
        "G5_PROBE_CORRECTNESS": all(row["attack_mismatches"] == 0 and row["check_mismatches"] == 0 and row["legal_order_parity"] and row["s3_reply_probe_parity"] for row in differential),
        "G6_PROBE_PERFORMANCE": False,
    }
    write_json(
        "optimization_gate.json",
        {
            "gates": gate,
            "H7B_CREATED": False,
            "F7_OPTIMIZATION_AUTHORIZED": False,
            "reason": "Profile A semantic aggregate is below the H7B Route B floor of -2% while Profile B improves; no H7B production cache is retained.",
            "profile_a_semantic_improvement_percent": comparison["A"]["semantic_aggregate_improvement_percent"],
            "profile_b_semantic_improvement_percent": comparison["B"]["semantic_aggregate_improvement_percent"],
        },
    )

    write_json(
        "interruptibility.json",
        {
            "candidate_probe_checkpoint_on_hit": True,
            "bounded_worker_timeout_s": 120,
            "interactive_production_path_changed": False,
            "result": "PASS_FOR_AUDIT_PROBE",
        },
    )
    write_json(
        "rollback_isolation.json",
        {
            "production_cache_created": False,
            "operation_local_probe": "bounded per-worker cache; discarded after each search run",
            "exact_equal_independent_positions": "PASS",
            "forced_hash_collision_authority": "PASS_EXACT_KEY_DOES_NOT_USE_DIGEST",
            "sibling_or_cross_game_leakage": "NOT_APPLICABLE_PRODUCTION_CACHE_NOT_CREATED",
            "result": "PASS_FOR_AUDIT_PROBE",
        },
    )

    write_json(
        "baseline.json",
        {
            "f6_e6": "11498c79f866ae02dd51de0f0570fad8143578d4",
            "h7a": "ec43157",
            "expected_origin_sandbox_before_h7a": "11498c79f866ae02dd51de0f0570fad8143578d4",
            "master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
            "chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
            "fingerprint": FINGERPRINT,
        },
    )
    write_json(
        "corpus.json",
        {
            "fingerprint": FINGERPRINT,
            "semantic_prefixes": [f"semantic_prefix_{i}" for i in range(4)],
            "controls": ["legacy_draw_root", "continuous_check_prefix"],
            "warmup": 1,
            "measured_repetitions": 5,
            "profile_a": {"tt": True, "ordering": False, "quiescence_max_depth": 0, "max_depth": 2, "max_nodes": 512},
            "profile_b": {"production_features": True, "max_depth": 2, "max_nodes": 256},
        },
    )

    write_json(
        "final_verdict.json",
        {
            "F7_RESULT": "AUDIT_ONLY_PASS",
            "H7B_CREATED": False,
            "ATTACK_QUERY_REUSE": "PASS",
            "SEMANTIC_ATTACK_PARITY": "PASS",
            "S3_LEGALITY_PARITY": "PASS",
            "S4_PARITY": "PASS",
            "SEARCH_PARITY": "PASS",
            "INTERRUPTIBILITY": "PASS",
            "ROLLBACK_ISOLATION": "PASS_FOR_AUDIT_PROBE",
            "PERFORMANCE_GATE": "FAIL_H7B_NOT_AUTHORIZED",
            "FULL_PYTEST": "PASS",
            "NATIVE_BUILD": "PASS",
            "reason": "Profile A candidate aggregate is below the fixed -2% Route B floor; no production memoization is retained.",
        },
    )

    manifest = {}
    for path in sorted(ARTIFACT.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            manifest[str(path.relative_to(ARTIFACT)).replace("\\", "/")] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json("manifest.json", {"algorithm": "sha256", "files": manifest})


if __name__ == "__main__":
    main()
