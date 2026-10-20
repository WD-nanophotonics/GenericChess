"""Create deterministic, verified publication copies of run-002 JSONL traces."""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path


TASK = Path(__file__).resolve().parent
RUN = TASK / "run-002"
OUT = RUN / "published-traces"
SENSITIVE_KEY = re.compile(r"(password|secret|credential|api[_-]?key|bearer|email|phone)", re.I)
SENSITIVE_VALUE = re.compile(
    r"(gh[pousr]_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{15,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)",
    re.I,
)


def walk_and_check(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if SENSITIVE_KEY.search(key):
                raise ValueError(f"sensitive-looking key in publication input at {child_path}")
            yield from walk_and_check(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_and_check(child, f"{path}[{index}]")
    elif isinstance(value, str) and SENSITIVE_VALUE.search(value):
        raise ValueError(f"credential-looking value in publication input at {path}")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def archive(name: str) -> dict:
    source = RUN / name
    target = OUT / f"{name}.gz"
    OUT.mkdir(parents=True, exist_ok=True)
    original_sha = hashlib.sha256()
    raw_bytes = 0
    rows = 0
    with source.open("rb") as src, target.open("wb") as dst:
        with gzip.GzipFile(fileobj=dst, mode="wb", compresslevel=9, mtime=0, filename="") as gz:
            for line_number, line in enumerate(src, 1):
                if not line.endswith(b"\n"):
                    raise ValueError(f"incomplete JSONL line {line_number} in {source}")
                value = json.loads(line)
                tuple(walk_and_check(value))
                original_sha.update(line)
                raw_bytes += len(line)
                rows += 1
                gz.write(line)
    decompressed_sha = hashlib.sha256()
    decompressed_bytes = 0
    decompressed_rows = 0
    with gzip.open(target, "rb") as stream:
        for line in stream:
            decompressed_sha.update(line)
            decompressed_bytes += len(line)
            decompressed_rows += 1
    original_hash = original_sha.hexdigest()
    if (decompressed_sha.hexdigest(), decompressed_bytes, decompressed_rows) != (original_hash, raw_bytes, rows):
        raise AssertionError(f"gzip round-trip differs from {source}")
    return {
        "original": name,
        "original_bytes": raw_bytes,
        "original_sha256": original_hash,
        "rows": rows,
        "archive": str(target.relative_to(TASK.parent.parent.parent)).replace("\\", "/"),
        "archive_bytes": target.stat().st_size,
        "archive_sha256": digest(target),
        "compression": "gzip level 9, mtime=0, empty filename",
        "decompressed_exactly": True,
        "credential_pattern_scan": "PASS",
    }


def main() -> None:
    manifest = [archive(name) for name in ("eval-games.jsonl", "eval-queries.jsonl")]
    (RUN / "compressed-streams.json").write_text(
        json.dumps({"task": "DEV_AUX2617", "run": "run-002", "raw_sources_preserved_locally": True, "artifacts": manifest}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
