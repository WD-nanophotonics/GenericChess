"""Dynamic, outcome-blind exact-history inventory; never writes a root pool."""
from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
POOL = ROOT / "results/dev_aux/task2626/rule15-root-pools.json"
OUTPUT = ROOT / "results/dev_aux/task2627/source-inventory-v2.json"
FP = "dfc95a6d4fc8bb14730a3163c71670822b88ee2f20ef6eaf1ea44b5b1c292020"
FP_BYTES = FP.encode("ascii")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def walk_records(value: object):
    if isinstance(value, dict):
        if value.get("ruleset_fingerprint") == FP and isinstance(value.get("actions"), list):
            yield value
        for child in value.values():
            yield from walk_records(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_records(child)


def read_jsonl(path: Path, compressed: bool):
    opener = gzip.open if compressed else open
    with opener(path, "rb") as stream:
        for line_number, line in enumerate(stream, 1):
            if FP_BYTES not in line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"matching JSONL row is invalid: {path}:{line_number}") from exc
            yield from walk_records(row)


def main() -> None:
    pinned = json.loads(POOL.read_text(encoding="utf-8"))
    if pinned["candidate"]["ruleset_fingerprint"] != FP:
        raise ValueError("pinned task2626 rule fingerprint changed")
    results = ROOT / "results/dev_aux"
    plain = sorted(p for p in results.rglob("*") if p.is_file() and p.suffix.lower() in (".json", ".jsonl") and "__pycache__" not in p.parts)
    compressed = sorted(p for p in results.rglob("*") if p.is_file() and p.name.lower().endswith((".jsonl.gz", ".json.gz")) and "__pycache__" not in p.parts)
    rel_plain = [p.relative_to(ROOT).as_posix() for p in plain]
    rel_compressed = [p.relative_to(ROOT).as_posix() for p in compressed]
    file_manifest_hash = sha_bytes(json.dumps({"plain": rel_plain, "compressed": rel_compressed}, separators=(",", ":")).encode())

    scan = subprocess.run(
        ["rg", "-F", "-l", "--no-messages", "--no-ignore", "--glob", "*.json", "--glob", "*.jsonl", "--", FP, str(results)],
        cwd=ROOT, capture_output=True, check=False,
    )
    if scan.returncode not in (0, 1):
        raise RuntimeError(f"dynamic plain-file fingerprint scan failed ({scan.returncode})")
    text_matches = {Path(s.decode("utf-8")).resolve() for s in scan.stdout.splitlines()}
    if len(text_matches) > len(plain):
        raise ValueError("search returned a path outside the enumerated results inventory")

    sources = []
    unique: set[bytes] = set()
    occurrences = 0
    for path in sorted(text_matches):
        local: set[bytes] = set()
        n = 0
        if path.suffix.lower() == ".jsonl":
            for record in read_jsonl(path, False):
                encoded = canonical(record)
                local.add(encoded); unique.add(encoded); n += 1
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
            for record in walk_records(data):
                encoded = canonical(record)
                local.add(encoded); unique.add(encoded); n += 1
        occurrences += n
        sources.append({"path": path.relative_to(ROOT).as_posix(), "format": "jsonl" if path.suffix.lower() == ".jsonl" else "json", "bytes": path.stat().st_size, "sha256": sha_file(path), "record_occurrences": n, "unique_records_in_file": len(local)})

    compressed_sources = []
    for path in compressed:
        local: set[bytes] = set()
        n = 0
        try:
            if path.name.lower().endswith(".json.gz"):
                with gzip.open(path, "rb") as stream:
                    values = walk_records(json.loads(stream.read()))
                    records = values
            else:
                records = read_jsonl(path, True)
            for record in records:
                encoded = canonical(record)
                local.add(encoded); unique.add(encoded); n += 1
        except (OSError, EOFError, gzip.BadGzipFile):
            raise
        if n:
            occurrences += n
            compressed_sources.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha_file(path), "record_occurrences": n, "unique_records_in_file": len(local)})

    result = {
        "status": "DYNAMIC_EXACT_HISTORY_INVENTORY_ONLY_NO_ROOTS_WRITTEN",
        "candidate": {"source_pool": POOL.relative_to(ROOT).as_posix(), "source_pool_sha256": sha_file(POOL), "ruleset_fingerprint": FP},
        "scope": "All current DEV_AUX results JSON/JSONL plus JSONL.GZ/JSON.GZ; exact canonical full-record matches only. No claim about descendants, transpositions, or distributional independence.",
        "enumeration": {"plain_files": len(plain), "compressed_files": len(compressed), "path_manifest_sha256": file_manifest_hash, "plain_fingerprint_scan_exit_code": scan.returncode, "matched_plain_files": len(text_matches)},
        "matched_sources": sources,
        "matched_compressed_sources": compressed_sources,
        "exact_candidate_record_occurrences": occurrences,
        "unique_exact_candidate_records": len(unique),
        "unique_record_sha256": sorted(sha_bytes(record) for record in unique),
        "family_ranges_selected": False,
        "pool_created": False,
        "training_or_evaluation_started": False,
    }
    if OUTPUT.exists():
        raise FileExistsError(f"write-once inventory already exists: {OUTPUT}")
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "enumeration": result["enumeration"], "exact_candidate_record_occurrences": occurrences, "unique_exact_candidate_records": len(unique), "compressed_matches": compressed_sources, "pool_created": False}, sort_keys=True))


if __name__ == "__main__":
    main()
