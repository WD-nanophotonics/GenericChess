"""Outcome-blind inventory of exact full-history records for task2633 candidates."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2636"
PLAN = TASK / "plan.json"
OUTPUT = TASK / "candidate-history-inventory.json"
STATUS = TASK / "status.json"
INDEX = ROOT / "results/dev_aux/task2633/generated/candidate-index.json"
HARD_SECONDS = 600.0

sys.path.insert(0, str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def walk_records(value: object, fingerprints: set[str]):
    if isinstance(value, dict):
        if value.get("ruleset_fingerprint") in fingerprints and isinstance(value.get("actions"), list):
            yield value
        for child in value.values():
            yield from walk_records(child, fingerprints)
    elif isinstance(value, list):
        for child in value:
            yield from walk_records(child, fingerprints)


def checked_inputs(plan: dict) -> tuple[dict, list[dict], dict[str, str]]:
    for rel, expected in plan["source_sha256"].items():
        actual = file_sha(ROOT / rel)
        if actual != expected:
            raise ValueError(f"pinned input changed: {rel}")
    index_raw = INDEX.read_bytes()
    if sha(index_raw) != plan["candidate_index_sha256"]:
        raise ValueError("candidate-index source pin mismatch")
    index = json.loads(index_raw)
    expected_rows = index["rows"]
    if len(expected_rows) != 16 or index["candidate_count"] != 16:
        raise ValueError("candidate index does not contain the frozen 16-rule set")
    rows, fingerprints = [], {}
    for row in expected_rows:
        rule_path = ROOT / row["source_file"]
        raw_rule = rule_path.read_bytes()
        if sha(raw_rule) != row["ruleset_sha256"]:
            raise ValueError(f"candidate rule hash mismatch: {row['source_file']}")
        rule = json.loads(raw_rule)
        compiled = compile_ruleset_for_execution(ruleset_from_dict(rule))
        fingerprint = GameSession(compiled).to_record().ruleset_fingerprint
        if fingerprint in fingerprints.values():
            raise ValueError("candidate ruleset fingerprints are not unique")
        fingerprints[row["source_file"]] = fingerprint
        rows.append({
            "seed": row["seed"], "rule_path": row["source_file"],
            "rule_sha256": sha(raw_rule), "ruleset_fingerprint": fingerprint,
        })
    return index, rows, fingerprints


def source_records(path: Path, fingerprints: set[str]):
    if path.name.lower().endswith(".jsonl.gz"):
        opener = gzip.open
        jsonl = True
    elif path.name.lower().endswith(".json.gz"):
        opener = gzip.open
        jsonl = False
    else:
        opener = open
        jsonl = path.suffix.lower() == ".jsonl"
    with opener(path, "rb") as stream:
        if jsonl:
            for line_no, line in enumerate(stream, 1):
                if not any(fp.encode("ascii") in line for fp in fingerprints):
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"matching JSONL row is invalid: {path}:{line_no}") from exc
                yield from walk_records(value, fingerprints)
        else:
            raw = stream.read()
            if not any(fp.encode("ascii") in raw for fp in fingerprints):
                return
            value = json.loads(raw)
            yield from walk_records(value, fingerprints)


def save_status(value: dict) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> dict:
    if OUTPUT.exists():
        raise FileExistsError(f"write-once inventory already exists: {OUTPUT}")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    index, candidates, rule_fps = checked_inputs(plan)
    fingerprints = set(rule_fps.values())
    results = ROOT / "results/dev_aux"
    plain = sorted(p for p in results.rglob("*") if p.is_file() and p.suffix.lower() in (".json", ".jsonl") and "__pycache__" not in p.parts)
    compressed = sorted(p for p in results.rglob("*") if p.is_file() and p.name.lower().endswith((".jsonl.gz", ".json.gz")) and "__pycache__" not in p.parts)
    rel_plain = [p.relative_to(ROOT).as_posix() for p in plain]
    rel_compressed = [p.relative_to(ROOT).as_posix() for p in compressed]
    manifest = json.dumps({"plain": rel_plain, "compressed": rel_compressed}, separators=(",", ":")).encode()
    started = time.perf_counter()
    by_fp = {fp: {"records": set(), "occurrences": 0, "sources": []} for fp in fingerprints}
    sources_scanned = 0
    for path in plain + compressed:
        if time.perf_counter() - started >= HARD_SECONDS:
            save_status({"status": "HARD_CAP_NO_COMPLETE_INVENTORY", "sources_scanned": sources_scanned,
                         "sources_total": len(plain) + len(compressed), "outputs_written": False,
                         "elapsed_seconds": time.perf_counter() - started})
            raise TimeoutError("600-second exact-history inventory cap reached; no complete inventory written")
        hits = {fp: {"records": set(), "occurrences": 0} for fp in fingerprints}
        for record in source_records(path, fingerprints):
            fp = record["ruleset_fingerprint"]
            encoded = canonical(record)
            hits[fp]["records"].add(sha(encoded))
            hits[fp]["occurrences"] += 1
        matched = []
        for fp, item in hits.items():
            if item["occurrences"]:
                by_fp[fp]["records"].update(item["records"])
                by_fp[fp]["occurrences"] += item["occurrences"]
                matched.append({"ruleset_fingerprint": fp, "record_occurrences": item["occurrences"],
                                "unique_records_in_file": len(item["records"])})
        if matched:
            sources_scanned_file = {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
                                    "sha256": file_sha(path), "matches": matched}
            for fp in (entry["ruleset_fingerprint"] for entry in matched):
                by_fp[fp]["sources"].append(sources_scanned_file)
        sources_scanned += 1
        if sources_scanned % 500 == 0:
            save_status({"status": "SCANNING", "sources_scanned": sources_scanned,
                         "sources_total": len(plain) + len(compressed),
                         "elapsed_seconds": time.perf_counter() - started, "outputs_written": False})
    candidate_results = []
    for candidate in candidates:
        fp = candidate["ruleset_fingerprint"]
        item = by_fp[fp]
        candidate_results.append({**candidate, "record_occurrences": item["occurrences"],
                                  "unique_exact_records": len(item["records"]),
                                  "exact_record_sha256": sorted(item["records"]),
                                  "matched_sources": item["sources"]})
    result = {
        "status": "COMPLETE_DYNAMIC_EXACT_HISTORY_INVENTORY_ONLY_NO_ROOTS_WRITTEN",
        "task": plan["task"], "plan_sha256": sha(PLAN.read_bytes()),
        "candidate_index_sha256": sha(INDEX.read_bytes()), "candidate_count": len(candidate_results),
        "enumeration": {"plain_files": len(plain), "compressed_files": len(compressed),
                        "path_manifest_sha256": sha(manifest), "sources_scanned": sources_scanned,
                        "total_bytes": sum(p.stat().st_size for p in plain + compressed)},
        "candidate_histories": candidate_results,
        "total_exact_record_occurrences": sum(x["record_occurrences"] for x in candidate_results),
        "total_unique_exact_records": sum(x["unique_exact_records"] for x in candidate_results),
        "family_ranges_selected": False, "pool_created": False,
        "training_or_evaluation_started": False,
        "limits": plan["limits"],
    }
    raw = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    with OUTPUT.open("xb") as stream:
        stream.write(raw)
    receipt = {"status": result["status"], "inventory_sha256": sha(raw),
               "candidate_count": len(candidate_results), "enumeration": result["enumeration"],
               "total_exact_record_occurrences": result["total_exact_record_occurrences"],
               "total_unique_exact_records": result["total_unique_exact_records"],
               "candidates_with_records": sum(bool(x["record_occurrences"]) for x in candidate_results),
               "elapsed_seconds": time.perf_counter() - started, "outputs_written": True}
    save_status(receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
