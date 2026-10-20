"""Deterministic byte-exact archive of the interrupted task2623 traces."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent / "run"
OUT = RUN / "public-partial-traces.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def package() -> dict:
    if OUT.exists():
        raise FileExistsError("partial trace archive manifest is write-once")
    members = []
    for name in ("queries.jsonl", "episodes.jsonl"):
        source, archive = RUN / name, RUN / (name + ".gz")
        if not source.is_file() or archive.exists():
            raise FileNotFoundError(f"missing source or pre-existing archive: {name}")
        source_sha, lines = digest(source), 0
        with source.open("rb") as raw, archive.open("wb") as dst:
            with gzip.GzipFile(filename="", mode="wb", fileobj=dst,
                               compresslevel=9, mtime=0) as gz:
                for line in raw:
                    lines += bool(line.strip())
                    gz.write(line)
        h = hashlib.sha256()
        with source.open("rb") as expected, gzip.open(archive, "rb") as actual:
            while True:
                a, b = expected.read(1024 * 1024), actual.read(1024 * 1024)
                if a != b:
                    raise ValueError(f"archive differs from original: {name}")
                if not a:
                    break
                h.update(b)
        if h.hexdigest() != source_sha:
            raise ValueError(f"source hash changed during archive: {name}")
        members.append({"source": name, "archive": archive.name,
                        "source_bytes": source.stat().st_size,
                        "source_sha256": source_sha,
                        "archive_bytes": archive.stat().st_size,
                        "archive_sha256": digest(archive),
                        "nonblank_lines": lines, "roundtrip": "BYTE_EXACT"})
    result = {"status": "PASS_PARTIAL_TRACE_ROUNDTRIP",
              "members": members,
              "interpretation": "Exact interrupted task2623 traces; preserve partial/open/missing status, no top-up."}
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    package()
