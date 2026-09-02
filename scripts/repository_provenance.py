"""Non-mutating repository-content provenance helpers for audit/test code."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


LEDGER = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "f47r4_legacy_provenance_migration.json"


class RepositoryBlobError(RuntimeError):
    """Raised when a frozen Git blob cannot be retrieved."""


def _blob_spec(path: str | Path) -> str:
    relative = str(path).replace("\\", "/")
    if not relative or relative.startswith("/") or ":" in relative:
        raise ValueError(f"repository provenance path must be relative: {path!r}")
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"repository provenance path must be normalized: {path!r}")
    return relative


def repository_blob_bytes(repo_root: Path, ref: str, path: str | Path) -> bytes:
    """Return raw bytes for ``ref:path`` without touching the worktree."""

    if not ref or any(character in ref for character in "\r\n"):
        raise ValueError("repository provenance ref must be a non-empty single line")
    relative = _blob_spec(path)
    result = subprocess.run(
        ["git", "-C", str(repo_root), "cat-file", "blob", f"{ref}:{relative}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RepositoryBlobError(f"unable to read Git blob {ref}:{relative}: {detail}")
    return result.stdout


def repository_blob_sha256(repo_root: Path, ref: str, path: str | Path) -> str:
    """Compute SHA-256 over exact raw Git blob bytes at ``ref:path``."""

    return hashlib.sha256(repository_blob_bytes(repo_root, ref, path)).hexdigest()


def verify_repository_blob(repo_root: Path, ref: str, path: str | Path, expected_sha256: str) -> dict[str, Any]:
    """Return a non-mutating comparison record with explicit error reporting."""

    relative = _blob_spec(path)
    result: dict[str, Any] = {"ref": ref, "path": relative, "expected_sha256": expected_sha256, "repository_blob_sha256": None, "match": False, "error": None}
    try:
        actual = repository_blob_sha256(repo_root, ref, relative)
    except (RepositoryBlobError, ValueError) as exc:
        result["error"] = str(exc)
    else:
        result["repository_blob_sha256"] = actual
        result["match"] = actual == expected_sha256
    return result


def require_repository_blob(repo_root: Path, ref: str, path: str | Path, expected_sha256: str) -> dict[str, Any]:
    """Return a matching comparison record or raise a useful assertion error."""

    result = verify_repository_blob(repo_root, ref, path, expected_sha256)
    if not result["match"]:
        raise AssertionError(f"repository provenance mismatch: {result['ref']}:{result['path']} expected={result['expected_sha256']} actual={result['repository_blob_sha256']} error={result['error']}")
    return result


def _load_ledger() -> dict[str, Any]:
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "ledger_sha256"}
    actual = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if actual != data["ledger_sha256"]:
        raise AssertionError("H47R4A migration ledger hash mismatch")
    return data


def require_migrated_binding(repo_root: Path, stage: str, manifest: str, binding: str, canonical_ref: str, canonical_path: str, legacy_sha256: str) -> dict[str, Any]:
    """Validate a legacy binding against its explicit canonical ledger row."""

    matches = [row for row in _load_ledger()["bindings"] if row["stage"] == stage and row["manifest"] == manifest and row["binding"] == binding]
    if len(matches) != 1:
        raise AssertionError(f"H47R4A migration binding is not unique: {stage}/{manifest}/{binding}")
    row = matches[0]
    for field, actual, expected in (("canonical_ref", canonical_ref, row["canonical_ref"]), ("canonical_path", _blob_spec(canonical_path), row["canonical_path"]), ("legacy_sha256", legacy_sha256, row["legacy_sha256"])):
        if actual != expected:
            raise AssertionError(f"H47R4A migration mismatch for {binding}: {field}")
    result = require_repository_blob(repo_root, row["canonical_ref"], row["canonical_path"], row["repository_blob_sha256"])
    result["legacy_sha256"] = row["legacy_sha256"]
    result["legacy_hash_semantics"] = row["legacy_hash_semantics"]
    return result
