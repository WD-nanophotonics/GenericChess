"""Create deterministic, byte-verifiable public trace archives."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent / "run"
OUT = RUN / "public-traces.json"
SOURCES = ("queries.jsonl", "episodes.jsonl", "eval-games.jsonl", "eval-queries.jsonl")


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package() -> dict:
    if OUT.exists():
        raise FileExistsError("public trace manifest is write-once")
    members = []
    for name in SOURCES:
        source = RUN / name
        archive = RUN / (name + ".gz")
        if not source.is_file() or archive.exists():
            raise FileNotFoundError(f"missing source or pre-existing archive: {name}")
        source_sha = sha_file(source)
        lines = 0
        with source.open("rb") as raw, archive.open("wb") as compressed:
            with gzip.GzipFile(filename="", mode="wb", fileobj=compressed,
                               compresslevel=9, mtime=0) as stream:
                for line in raw:
                    if line.strip():
                        lines += 1
                    stream.write(line)
        # Verify exact decompression against the original bytes.
        digest = hashlib.sha256()
        with source.open("rb") as expected, gzip.open(archive, "rb") as actual:
            while True:
                a, b = expected.read(1024 * 1024), actual.read(1024 * 1024)
                if a != b:
                    raise ValueError(f"archive round-trip differs: {name}")
                if not a:
                    break
                digest.update(b)
        if digest.hexdigest() != source_sha:
            raise ValueError(f"source hash changed during packaging: {name}")
        members.append({"source": name, "archive": archive.name,
                        "source_bytes": source.stat().st_size,
                        "source_sha256": source_sha,
                        "archive_bytes": archive.stat().st_size,
                        "archive_sha256": sha_file(archive), "nonblank_lines": lines,
                        "roundtrip": "BYTE_EXACT"})
    manifest = {"status": "PASS_DETERMINISTIC_BYTE_EXACT_TRACE_ARCHIVES",
                "members": members,
                "sensitive_originals": "Uncompressed originals remain local; only project-generated game/query traces are archived."}
    OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


if __name__ == "__main__":
    package()
