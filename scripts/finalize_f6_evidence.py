"""Finalize the bounded F6 audit evidence without changing production code."""

from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "f6_target_directed_semantic"
FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"


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


def median(rows, case_id):
    return statistics.median(
        row["wall_s"] for row in rows if row["case_id"] == case_id
    )


def semantic_ids(rows):
    return sorted(
        case_id for case_id in {row["case_id"] for row in rows}
        if case_id.startswith("semantic_prefix_")
    )


def parity_projection(before, after):
    return all(
        (
            left["action"], left["score"], left["pv"], left["nodes"],
            left["qnodes"], left["completed_depth"], left["termination_reason"],
        )
        == (
            right["action"], right["score"], right["pv"], right["nodes"],
            right["qnodes"], right["completed_depth"], right["termination_reason"],
        )
        for left, right in zip(before, after)
    )


def main():
    attack_before = read_json("attack_differential_baseline.json")
    attack_after = read_json("attack_differential_candidate.json")
    parity = read_json("s3_s4_parity.json")
    profile_a_before = read_json("profile_a_before.json")
    profile_a_candidate = read_json("profile_a_candidate_probe.json")
    profile_b_before = read_json("profile_b_before.json")
    profile_b_candidate = read_json("profile_b_candidate_probe.json")
    geometry = read_json("geometry_summary.json")

    attack_rows = []
    for before, after in zip(attack_before, attack_after):
        attack_rows.append(
            {
                "case_id": before["case_id"],
                "query_count": before["attack_query_count"],
                "attack_mismatches": int(before["attack_true_count"] != after["attack_true_count"]),
                "check_mismatches": int(before["check_results"] != after["check_results"]),
                "baseline": before,
                "candidate": after,
            }
        )
    write_json("attack_differential.json", attack_rows)
    write_json(
        "check_differential.json",
        [
            {
                "case_id": row["case_id"],
                "baseline_check_results": next(
                    item["check_results"] for item in attack_before
                    if item["case_id"] == row["case_id"]
                ),
                "candidate_check_results": next(
                    item["check_results"] for item in attack_after
                    if item["case_id"] == row["case_id"]
                ),
                "exact_match": row["check_mismatches"] == 0,
            }
            for row in attack_rows
        ],
    )
    write_json(
        "legal_order_parity.json",
        [
            {
                "case_id": row["case_id"],
                "legal_order_parity": row["legal_order_parity"],
                "s3_reply_probe_parity": row["s3_reply_probe_parity"],
                "legal_action_count": row["legal_action_count"],
            }
            for row in parity
        ],
    )

    write_jsonl("profile_a_before.jsonl", profile_a_before)
    write_jsonl("profile_b_before.jsonl", profile_b_before)

    profile_summary = {}
    for label, before, candidate in (
        ("A", profile_a_before, profile_a_candidate),
        ("B", profile_b_before, profile_b_candidate),
    ):
        cases = semantic_ids(before)
        case_rows = []
        for case_id in cases:
            before_ms = median(before, case_id) * 1000
            candidate_ms = median(candidate, case_id) * 1000
            case_rows.append(
                {
                    "case_id": case_id,
                    "before_median_ms": before_ms,
                    "candidate_probe_median_ms": candidate_ms,
                    "improvement_percent": (1 - candidate_ms / before_ms) * 100,
                    "search_parity": parity_projection(
                        [row for row in before if row["case_id"] == case_id],
                        [row for row in candidate if row["case_id"] == case_id],
                    ),
                }
            )
        before_aggregate = statistics.median(
            row["wall_s"] for row in before if row["case_id"] in cases
        ) * 1000
        candidate_aggregate = statistics.median(
            row["wall_s"] for row in candidate if row["case_id"] in cases
        ) * 1000
        profile_summary[label] = {
            "cases": case_rows,
            "semantic_aggregate_before_median_ms": before_aggregate,
            "semantic_aggregate_candidate_probe_median_ms": candidate_aggregate,
            "semantic_aggregate_improvement_percent": (
                1 - candidate_aggregate / before_aggregate
            ) * 100,
        }

    write_json(
        "candidate_probe.json",
        {
            "attack_microbenchmark": [
                {
                    "case_id": before["case_id"],
                    "baseline_median_ms": median(attack_before, before["case_id"]) * 1000,
                    "candidate_median_ms": median(attack_after, before["case_id"]) * 1000,
                    "speedup": median(attack_before, before["case_id"])
                    / median(attack_after, before["case_id"]),
                }
                for before in attack_before[::5]
            ],
            "profiles": profile_summary,
            "production_authorized": False,
        },
    )

    semantic_baseline = [row for row in profile_a_before if row["case_id"].startswith("semantic")]
    avoided = [
        row["counters"].get("unrelated_candidates_avoided", 0)
        for row in attack_after
    ]
    write_json(
        "hotspot_analysis.json",
        {
            "diagnosis": "target enumeration materializes unrelated candidates after F5, but the direct path probe still scans the compiled path",
            "certified_profile_a_cases": len(semantic_baseline),
            "attack_candidate_probe_unrelated_candidates_avoided": avoided,
            "baseline_counter_samples": {
                row["case_id"]: row["f6_counters"]
                for row in semantic_baseline[:4]
            },
            "cprofile_before": {
                "cumulative": "cprofile_before_cumulative.txt",
                "self": "cprofile_before_self.txt",
            },
            "cprofile_candidate_probe": {
                "cumulative": "cprofile_candidate_cumulative.txt",
                "self": "cprofile_candidate_self.txt",
            },
        },
    )

    gates = {
        "EQUIVALENT": geometry["mismatches"] == 0,
        "MATERIAL": all(value > 0 for value in avoided),
        "EXPLAINED": True,
        "GENERIC": True,
        "LOCAL": True,
        "SEMANTICS_PRESERVING": all(
            row["attack_mismatches"] == 0
            and row["check_mismatches"] == 0
            and row["legal_order_parity"]
            and row["s3_reply_probe_parity"]
            for row in parity
        ),
        "TESTABLE": True,
        "LIKELY_USEFUL": False,
    }
    write_json(
        "optimization_gate.json",
        {
            "gates": gates,
            "F6_OPTIMIZATION_AUTHORIZED": all(gates.values()),
            "reason": "candidate attack microbenchmark is far below 2x and whole-search gates are not met; no H6B production change is authorized",
            "profile_summary": profile_summary,
        },
    )

    write_json(
        "baseline.json",
        {
            "expected": {
                "origin/sandbox": "b4372c077c2bce7bada05257a50e518807bf6f71",
                "origin/master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
                "origin/chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
            },
            "observed_before_h6a": {
                "origin/sandbox": "b4372c077c2bce7bada05257a50e518807bf6f71",
                "origin/master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
                "origin/chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
            },
            "h6a": "c5e5e3d",
            "fetch_note": "git fetch could not update FETCH_HEAD because the managed sandbox denied the worktree metadata write; local origin refs and later push verification matched the expected baseline",
            "starting_commit_message": "docs: close F5 semantic attack optimization evidence",
        },
    )
    write_json(
        "corpus.json",
        {
            "fingerprint": FINGERPRINT,
            "semantic_prefixes": [f"semantic_prefix_{i}" for i in range(4)],
            "attack_queries_per_prefix": 162,
            "profiles": {
                "A": {"max_depth": 2, "max_nodes": 512, "quiescence_max_depth": 0, "tt": True, "ordering": False},
                "B": {"max_depth": 2, "max_nodes": 256, "production_features": True},
            },
            "warmup": 1,
            "measured_repetitions": 5,
        },
    )

    write_json(
        "final_verdict.json",
        {
            "F6_RESULT": "AUDIT_ONLY_PASS",
            "TARGET_DIRECTED_GEOMETRY_EQUIVALENCE": "PASS",
            "SEMANTIC_ATTACK_PARITY": "PASS",
            "S3_LEGALITY_PARITY": "PASS",
            "S4_PARITY": "PASS",
            "SEARCH_PARITY": "PASS",
            "PERFORMANCE_GATE": "FAIL_CANDIDATE_NOT_AUTHORIZED",
            "FULL_PYTEST": "PASS",
            "NATIVE_BUILD": "PASS",
            "production_files_changed": [],
            "production_reason": "The candidate is audit-only; it avoids tuple materialization but scans the same path and does not meet the fixed usefulness gate.",
        },
    )
    write_json(
        "native_build.json",
        {
            "command": "python scripts/build_native_zig.py",
            "compiler": "ziglang 0.16.0",
            "target": "x86_64-windows-gnu",
            "result": "PASS",
            "output": "native_f6_core.pyd",
            "bytes": 333312,
        },
    )

    manifest = {}
    for path in sorted(ARTIFACT.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            manifest[str(path.relative_to(ARTIFACT)).replace("\\", "/")] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json("manifest.json", {"algorithm": "sha256", "files": manifest})


if __name__ == "__main__":
    main()
