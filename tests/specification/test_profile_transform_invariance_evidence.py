"""Guards for the published DEEPSEEK_AUX profile-transform evidence copy.

The evidence directory under ``docs/research/data/profile_transform_invariance_20261018``
carries its own ``manifest.json`` (sizes and SHA-256 of every published file) and
a README table with the same values.  Both have drifted by hand before, and the
existing rebuild check cannot see it because it rebuilds the copy from itself.
These checks only read stored files; they run no scan, no game and no search.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import tokenize
from pathlib import Path

import pytest


EVIDENCE = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "research"
    / "data"
    / "profile_transform_invariance_20261018"
)

ROW = re.compile(r"^\|\s*`(?P<name>[^`]+)`\s*\|\s*(?P<bytes>\d+)\s*\|\s*`(?P<sha>[0-9a-f]{64})`\s*\|\s*$")


def _manifest() -> dict:
    return json.loads((EVIDENCE / "manifest.json").read_text(encoding="utf-8"))


def _entries() -> dict[str, dict]:
    return {entry["file"]: entry for entry in _manifest()["files"]}


def test_evidence_directory_exists() -> None:
    assert EVIDENCE.is_dir(), f"missing evidence copy at {EVIDENCE}"
    assert (EVIDENCE / "manifest.json").is_file()
    assert (EVIDENCE / "README.md").is_file()


def test_every_manifest_entry_matches_the_stored_file() -> None:
    entries = _entries()
    assert entries, "manifest lists no files"
    for name, entry in entries.items():
        path = EVIDENCE / name
        assert path.is_file(), f"{name} is listed in the manifest but absent"
        blob = path.read_bytes()
        assert len(blob) == entry["bytes"], f"{name} size drifted"
        digest = hashlib.sha256(blob).hexdigest()
        assert digest == entry["sha256"], f"{name} content drifted"


def test_readme_table_rows_match_the_manifest() -> None:
    entries = _entries()
    rows = {}
    for line in (EVIDENCE / "README.md").read_text(encoding="utf-8").splitlines():
        match = ROW.match(line.strip())
        if match:
            rows[match.group("name")] = (int(match.group("bytes")), match.group("sha"))
    assert rows, "README table is missing or unparsable"
    assert set(rows) == set(entries), (
        "README table and manifest list different files: "
        f"missing from README {sorted(set(entries) - set(rows))}, "
        f"extra in README {sorted(set(rows) - set(entries))}"
    )
    for name, (size, sha) in rows.items():
        assert size == entries[name]["bytes"], f"{name} row size drifted"
        assert sha == entries[name]["sha256"], f"{name} row hash drifted"


def test_every_published_artifact_is_in_the_manifest() -> None:
    listed = set(_entries())
    stored = {
        path.name
        for path in EVIDENCE.iterdir()
        if path.is_file()
        and (path.suffix in {".py"} or (path.suffix == ".json" and path.name != "manifest.json"))
    }
    assert stored, "no artifacts found in the evidence copy"
    assert stored == listed, (
        "an artifact was added or removed without updating the manifest: "
        f"unlisted {sorted(stored - listed)}, stale {sorted(listed - stored)}"
    )


def test_withdrawn_in_zone_versus_outside_contrast_stays_out() -> None:
    """The 0-versus-53 rate contrast was withdrawn; nothing may reintroduce it."""

    results = EVIDENCE / "results_zone_promotion_source_classification.json"
    blob = results.read_text(encoding="utf-8").lower()
    for marker in ("outside_zone", "outside-zone-rate", "in_zone_rate_outside"):
        assert marker not in blob, f"{marker} reappeared in the source-classification result"
    payload = json.loads(blob)
    summary = payload["summary"]
    for key in summary:
        assert "outside" not in key, f"summary field {key} reintroduces the outside arm"
    assert summary["in_zone_contact"] == 53
    assert summary["in_zone_paid_observations"] == 2489
    assert summary["decision"] == "missing_contact_is_mostly_zone_geometry"


def test_promotion_table_cache_is_not_keyed_by_object_identity() -> None:
    """The discarded runs leaked promotion tables across seeds via id(compiled)."""

    scan = (EVIDENCE / "scan_zone_promotion_source_classification.py").read_text(encoding="utf-8")
    # The module docstring narrates the defect on purpose, so only executable
    # tokens may be inspected here.
    code_tokens = [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(scan).readline)
        if token.type not in {tokenize.COMMENT, tokenize.STRING}
    ]
    code = " ".join(code_tokens)
    assert "ruleset_fingerprint" in code
    assert "id ( compiled )" not in code
    assert "id(compiled)" not in code
    results = json.loads(
        (EVIDENCE / "results_zone_promotion_source_classification.json").read_text(encoding="utf-8")
    )
    corrections = results["defect_corrections"]
    assert corrections, "the fixed cache defect must stay recorded"
    assert len(corrections[0]["discarded_runs"]) == 2
    assert corrections[0]["status"].startswith("private and unpublished")
