"""Outcome-blind exact-history source inventory for a future rules15 panel.

This tool only inventories already exposed full records. It does not select or
write roots, inspect outcome labels, register a run, or launch computation.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE_POOL = ROOT / "results/dev_aux/task2626/rule15-root-pools.json"
OUTPUT = ROOT / "results/dev_aux/task2627/source-inventory.json"
RULE_FINGERPRINT = "dfc95a6d4fc8bb14730a3163c71670822b88ee2f20ef6eaf1ea44b5b1c292020"

# Preserve the previously audited source set, then append every history-bearing
# task2626 artifact. Missing legacy files are reported rather than silently
# treated as empty. The current task2626 pool is included because it stores its
# selected full records directly.
HISTORY_FILES = (
    "results/dev_aux/task2525/queries.jsonl", "results/dev_aux/task2525/episodes.jsonl",
    "results/dev_aux/task2565/generic/queries.jsonl", "results/dev_aux/task2565/generic/games.jsonl",
    "results/dev_aux/task2565/generic/eval-queries.jsonl", "results/dev_aux/task2565/generic/eval-games.jsonl",
    "results/dev_aux/task2606/queries.jsonl", "results/dev_aux/task2606/games.jsonl",
    "results/dev_aux/task2606/eval-queries.jsonl", "results/dev_aux/task2606/eval-games.jsonl",
    "results/dev_aux/task2608/eval-queries.jsonl", "results/dev_aux/task2608/eval-games.jsonl",
    "results/dev_aux/task2609/eval-queries.jsonl", "results/dev_aux/task2609/eval-games.jsonl",
    "results/dev_aux/task2610/eval-queries.jsonl", "results/dev_aux/task2610/eval-games.jsonl",
    "results/dev_aux/task2610/attempt-2/eval-queries.jsonl", "results/dev_aux/task2610/attempt-2/eval-games.jsonl",
    "results/dev_aux/task2618/learner-comparison-v2/queries.jsonl", "results/dev_aux/task2618/learner-comparison-v2/games.jsonl",
    "results/dev_aux/task2618/learner-comparison-v3/queries.jsonl", "results/dev_aux/task2618/learner-comparison-v3/games.jsonl",
    "results/dev_aux/task2621/active-feature-probe/queries.jsonl",
    "results/dev_aux/task2621/cost-scan/queries.jsonl", "results/dev_aux/task2621/cost-scan/episodes.jsonl",
    "results/dev_aux/task2622/run/queries.jsonl", "results/dev_aux/task2622/run/episodes.jsonl",
    "results/dev_aux/task2623/run/queries.jsonl", "results/dev_aux/task2623/run/episodes.jsonl",
    "results/dev_aux/task2625/run/queries.jsonl", "results/dev_aux/task2625/run/episodes.jsonl",
    "results/dev_aux/task2625/run/eval-queries.jsonl", "results/dev_aux/task2625/run/eval-games.jsonl",
    "results/dev_aux/task2626/rule15-training/queries.jsonl",
    "results/dev_aux/task2626/rule15-training/episodes.jsonl",
    "results/dev_aux/task2626/trajectory-feasibility/queries.jsonl",
    "results/dev_aux/task2626/rule15-trajectory-feasibility/queries.jsonl",
    "results/dev_aux/task2626/rule15-root-pools.json",
)
JSON_MANIFESTS = (
    "results/dev_aux/task2607/root-candidates.json", "results/dev_aux/task2609/root-manifest.json",
    "results/dev_aux/task2610/root-manifest.json", "results/dev_aux/task2622/root-pools.json",
    "results/dev_aux/task2622/root-pools-v2.json", "results/dev_aux/task2624/root-pools-v2.json",
    "results/dev_aux/task2433/inputs.json", "results/dev_aux/task2626/task2433-unvisited-variant-screen.json",
)
RULE_ONLY_METADATA = ("results/dev_aux/task2475/result.json",)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def records(value: object):
    if isinstance(value, dict):
        if value.get("ruleset_fingerprint") == RULE_FINGERPRINT and isinstance(value.get("actions"), list):
            yield value
        for child in value.values():
            yield from records(child)
    elif isinstance(value, list):
        for child in value:
            yield from records(child)


def main() -> None:
    pool = json.loads(SOURCE_POOL.read_text(encoding="utf-8"))
    if pool["candidate"]["ruleset_fingerprint"] != RULE_FINGERPRINT:
        raise ValueError("task2626 source pool fingerprint changed")
    all_sources = tuple(dict.fromkeys((*HISTORY_FILES, *JSON_MANIFESTS, *RULE_ONLY_METADATA)))
    present = [rel for rel in all_sources if (ROOT / rel).is_file()]
    missing = [rel for rel in all_sources if not (ROOT / rel).is_file()]
    scan = subprocess.run(
        ["rg", "-F", "-l", "--no-messages", "--", RULE_FINGERPRINT, *present],
        cwd=ROOT, capture_output=True, check=False,
    )
    if scan.returncode not in (0, 1):
        raise RuntimeError(f"fingerprint inventory failed ({scan.returncode})")
    matched = sorted(line.replace(b"\\", b"/").decode("utf-8") for line in scan.stdout.splitlines())
    hits = set(matched)
    excluded: set[bytes] = set()
    source_receipts = []
    for rel in all_sources:
        path = ROOT / rel
        if not path.is_file():
            source_receipts.append({"path": rel, "status": "MISSING", "candidate_occurrences": 0})
            continue
        status = "PRESENT_NO_FINGERPRINT"
        occurrences = 0
        local_unique: set[bytes] = set()
        if rel in hits:
            status = "READ_EXACT_CANDIDATE_RECORDS"
            if path.suffix.lower() == ".jsonl":
                with path.open("rb") as stream:
                    for line in stream:
                        if RULE_FINGERPRINT.encode() not in line:
                            continue
                        try:
                            row = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        for record in records(row):
                            encoded = canonical(record)
                            local_unique.add(encoded)
                            excluded.add(encoded)
                            occurrences += 1
            else:
                data = json.loads(path.read_text(encoding="utf-8"))
                for record in records(data):
                    encoded = canonical(record)
                    local_unique.add(encoded)
                    excluded.add(encoded)
                    occurrences += 1
        source_receipts.append({
            "path": rel, "status": status, "bytes": path.stat().st_size,
            "sha256": file_sha(path), "candidate_occurrences": occurrences,
            "candidate_unique_records": len(local_unique),
        })

    metadata = []
    for rel in RULE_ONLY_METADATA:
        path = ROOT / rel
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            metadata.append({"path": rel, "sha256": file_sha(path), "has_candidate_fingerprint": RULE_FINGERPRINT in path.read_text(encoding="utf-8"), "full_candidate_records": sum(1 for _ in records(raw))})
    result = {
        "status": "EXACT_HISTORY_INVENTORY_ONLY_NO_ROOTS_WRITTEN",
        "candidate": {"source_pool": SOURCE_POOL.relative_to(ROOT).as_posix(), "source_pool_sha256": file_sha(SOURCE_POOL), "ruleset_fingerprint": RULE_FINGERPRINT},
        "scope": "Enumerated DEV_AUX results sources only; exact canonical full-record matches. Does not establish descendant, transposition, or distributional independence.",
        "search": {"enumerated_sources": len(all_sources), "present_sources": len(present), "missing_sources": missing, "fingerprint_scan_exit_code": scan.returncode, "matched_files": matched},
        "source_receipts": source_receipts,
        "rule_only_metadata": metadata,
        "exact_candidate_record_occurrences": sum(item["candidate_occurrences"] for item in source_receipts),
        "unique_exact_candidate_records": len(excluded),
        "unique_record_sha256": sorted(sha(record) for record in excluded),
        "root_ranges_selected": False,
        "pool_created": False,
        "training_or_evaluation_started": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        raise FileExistsError(f"write-once inventory already exists: {OUTPUT}")
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "search", "exact_candidate_record_occurrences", "unique_exact_candidate_records", "root_ranges_selected", "pool_created")}, sort_keys=True))


if __name__ == "__main__":
    main()
