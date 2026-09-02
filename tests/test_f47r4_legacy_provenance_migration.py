"""H47R4A freezes the legacy-to-canonical provenance migration ledger."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "tests" / "fixtures" / "f47r4_legacy_provenance_migration.json"


def _blob_sha256(ref: str, path: str) -> str:
    blob = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "blob", f"{ref}:{path}"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    return hashlib.sha256(blob).hexdigest()


def test_h47r4a_ledger_is_frozen_complete_and_raw_blob_bound():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "ledger_sha256"}
    assert hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == data["ledger_sha256"]
    assert data["kind"] == "H47R4A_LEGACY_PROVENANCE_MIGRATION"
    assert len(data["bindings"]) == 34
    assert {row["stage"] for row in data["bindings"]} == {"F42", "F43", "F44", "F45", "H47R1A"}
    for row in data["bindings"]:
        assert len(row["legacy_sha256"]) == 64
        assert len(row["repository_blob_sha256"]) == 64
        assert _blob_sha256(row["canonical_ref"], row["canonical_path"]) == row["repository_blob_sha256"]


def test_h47r4a_preserves_each_source_manifest_legacy_value_verbatim():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    manifests = {path: json.loads((ROOT / path).read_text(encoding="utf-8")) for path in data["source_manifests"]}
    for row in data["bindings"]:
        source = manifests[row["manifest"]]
        if row["stage"] == "H47R1A":
            name, suffix = row["binding"].rsplit(".", 1)
            binding = source["provenance_bindings"][name]
            expected = binding["sha256"] if suffix == "authority" else binding["protocol_sha256"]
        else:
            expected = source["input_files"][row["binding"]]["sha256"]
        assert row["legacy_sha256"] == expected
