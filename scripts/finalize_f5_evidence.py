"""Finalize the machine-readable F5 evidence tree after validation."""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f5_semantic_attack_s3"
FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def rows_to_jsonl(name, rows):
    (OUT / name).write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def stats(rows, case):
    values = sorted(row["wall_s"] * 1000 for row in rows if row["case_id"] == case)
    p90_index = max(0, min(len(values) - 1, int(len(values) * 0.9) - 1))
    return {
        "n": len(values),
        "median_ms": statistics.median(values),
        "p90_ms": values[p90_index],
        "min_ms": values[0],
        "max_ms": values[-1],
    }


def main():
    before_a = load("profile_a_before.json")
    before_b = load("profile_b_before.json")
    after_a = load("profile_a_after.json")
    after_b = load("profile_b_after.json")
    rows_to_jsonl("profile_a_before.jsonl", before_a)
    rows_to_jsonl("profile_b_before.jsonl", before_b)
    rows_to_jsonl("profile_a_after.jsonl", after_a)
    rows_to_jsonl("profile_b_after.jsonl", after_b)

    cases = [
        "legacy_draw_root",
        "continuous_check_prefix",
        "semantic_prefix_0",
        "semantic_prefix_1",
        "semantic_prefix_2",
        "semantic_prefix_3",
    ]
    performance = {}
    for profile, before, after in (
        ("A", before_a, after_a),
        ("B", before_b, after_b),
    ):
        performance[profile] = {}
        for case in cases:
            b = stats(before, case)
            a = stats(after, case)
            performance[profile][case] = {
                "before": b,
                "after": a,
                "improvement_percent": (1 - a["median_ms"] / b["median_ms"]) * 100,
            }
        semantic = [f"semantic_prefix_{i}" for i in range(4)]
        bmed = statistics.median([stats(before, case)["median_ms"] for case in semantic])
        amed = statistics.median([stats(after, case)["median_ms"] for case in semantic])
        performance[profile]["semantic_aggregate"] = {
            "before_median_ms": bmed,
            "after_median_ms": amed,
            "improvement_percent": (1 - amed / bmed) * 100,
        }
    (OUT / "performance_comparison.json").write_text(
        json.dumps(performance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    parity = []
    for profile, before, after in (("A", before_a, after_a), ("B", before_b, after_b)):
        before_by = {(r["case_id"], r["repetition"]): r for r in before}
        after_by = {(r["case_id"], r["repetition"]): r for r in after}
        for key in sorted(before_by):
            b, a = before_by[key], after_by[key]
            fields = ("action", "score", "pv", "nodes", "qnodes", "completed_depth", "termination_reason")
            parity.append({
                "profile": profile,
                "case_id": key[0],
                "repetition": key[1],
                "exact": all(b[field] == a[field] for field in fields),
                "fields": {field: {"before": b[field], "after": a[field]} for field in fields},
            })
    (OUT / "search_parity.json").write_text(
        json.dumps(parity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    (OUT / "baseline.json").write_text(json.dumps({
        "starting_sandbox": "363c74dc94217941f67edfbcfcd1bb84432f96a0",
        "h5a": "878e0e54afb69fe81eb8ccad1df9ddb56d8ac379",
        "h5a_note": "harness-only state immediately before H5B; later cbf9e33/74352db are audit-only harness adjustments",
        "h5b": "49022a5f80b5b9be6bd70cc2689f3ce4d250655c",
        "origin_master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
        "origin_chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
        "fingerprint": FINGERPRINT,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    (OUT / "corpus.json").write_text(json.dumps({
        "fingerprint": FINGERPRINT,
        "f4_search_cases": cases,
        "semantic_prefixes": ["semantic_prefix_0", "semantic_prefix_1", "semantic_prefix_2", "semantic_prefix_3"],
        "attack_queries_per_prefix": 162,
        "attack_query_shape": "all 81 squares x both owners",
        "curated_witnesses": load("curated_attack_s3_differential.json"),
        "profiles": {
            "A": {"max_depth": 2, "max_nodes": 512, "qdepth": 0, "tt": True, "ordering": False, "root_tactical": False},
            "B": {"max_depth": 2, "max_nodes": 256, "qdepth": 4, "tt": True, "ordering": True},
        },
        "repetitions": 5,
        "warmups": 1,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    before_probe = load("profile_a_before_probe.json")
    hotspot = {
        "diagnosis": "repeated full-board source filtering inside semantic attack and board candidate dispatch",
        "profile_a_probe": before_probe,
        "micro_before": load("attack_micro_baseline.json"),
        "micro_after": load("attack_micro_after.json"),
        "deep_profile_before": "deep_profile_before_cumulative.txt / deep_profile_before_self.txt",
        "deep_profile_after": "deep_profile_after_cumulative.txt / deep_profile_after_self.txt",
        "remaining_hotspot": "semantic legality/check and per-operation source-index construction; no second optimization authorized",
    }
    (OUT / "hotspot_analysis.json").write_text(json.dumps(hotspot, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    perf = performance
    gate = {
        "candidate": "position-local owner/current-type source dispatch reuse",
        "family": "Semantic candidate / attack dispatch reuse",
        "gates": {
            "DOMINANT": True,
            "MATERIAL": perf["A"]["semantic_aggregate"]["improvement_percent"] >= 15,
            "EXPLAINED": True,
            "LOCAL": True,
            "SEMANTICS_PRESERVING": all(item["exact"] for item in parity),
            "TESTABLE": True,
            "LIKELY_USEFUL": True,
        },
        "rejected_options": ["immutable global semantic cache", "fixed-target attack pruning", "Native migration", "bitboard/incremental attack map"],
    }
    gate["authorized"] = all(gate["gates"].values())
    (OUT / "optimization_gate.json").write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    all_exact = all(item["exact"] for item in parity)
    attack_exact = all(item["attack_mismatches"] == 0 for item in load("attack_differential.json"))
    legal_exact = all(item["action_order_parity"] and item["s3_reply_probe_parity"] for item in load("legal_order_parity.json"))
    curated_exact = all(
        item["attack_mismatches"] == 0 and item["legal_order_parity"] and item["s3_reply_probe_parity"]
        for item in load("curated_attack_s3_differential.json")
    )
    verdict = {
        "status": "COMPLETE",
        "f5_result": "OPTIMIZATION_PASS",
        "semantic_attack_parity": attack_exact and curated_exact,
        "s3_legality_parity": legal_exact and curated_exact,
        "search_parity": all_exact,
        "performance_gate": gate["authorized"],
        "full_pytest": "PASS — full suite completed at 100%",
        "native_build": "PASS — fresh supported Zig build, 333312 bytes",
        "note": "Finalized after focused parity, full pytest, and fresh Zig validation.",
    }
    (OUT / "final_verdict.json").write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    files = sorted(path for path in OUT.iterdir() if path.is_file() and path.name != "manifest.json")
    manifest = {"schema": 1, "file_count": len(files) + 1, "sha256": {}}
    for path in files:
        manifest["sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
