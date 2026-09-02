"""Cross-platform contracts for canonical and migrated provenance."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from repository_provenance import (  # noqa: E402
    RepositoryBlobError,
    repository_blob_bytes,
    repository_blob_sha256,
    require_migrated_binding,
    verify_repository_blob,
)


PROBE_PATH = "docs/architecture/ADR-114-f44-structural-capability-feature-diagnosis.md"
CHANGED_PATH = "scripts/audit_f47_endpoint_density_composite.py"
OLD_F47_SHA = "d8d39bb4ef15f018e97afedf97733041490686b2"


def test_repository_blob_is_raw_git_content_and_does_not_use_worktree():
    blob = repository_blob_bytes(ROOT, "HEAD", PROBE_PATH)
    direct = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob", f"HEAD:{PROBE_PATH}"], check=True, stdout=subprocess.PIPE).stdout
    assert blob == direct
    assert repository_blob_sha256(ROOT, "HEAD", PROBE_PATH) == hashlib.sha256(blob).hexdigest()


def test_migrated_binding_preserves_legacy_value_and_uses_canonical_blob():
    result = require_migrated_binding(ROOT, "F42", "tests/fixtures/f42_capability_prior_manifest.json", "evaluation_config", "fa9a9c334fce331a5059f05a3e261e1fd85fbc7c", "generic_chess/ai/evaluation/config.py", "465a0d38335c45ac95ac91e458e5fb4b81d4be051c8e83da3af6130b01f6343e")
    assert result["match"] is True
    assert result["legacy_sha256"] != result["repository_blob_sha256"]
    assert result["legacy_hash_semantics"] == "LEGACY_CRLF_WORKTREE_HASH"


def test_provenance_reports_wrong_sha_path_and_ref_without_normalizing():
    expected = repository_blob_sha256(ROOT, "HEAD", CHANGED_PATH)
    wrong_sha = verify_repository_blob(ROOT, "HEAD", CHANGED_PATH, "0" * 64)
    assert wrong_sha["match"] is False
    assert wrong_sha["repository_blob_sha256"] == expected
    assert wrong_sha["error"] is None
    wrong_path = verify_repository_blob(ROOT, "HEAD", "scripts/not-a-real-file.py", expected)
    assert wrong_path["match"] is False
    assert "unable to read Git blob" in wrong_path["error"]
    old_sha = repository_blob_sha256(ROOT, OLD_F47_SHA, CHANGED_PATH)
    assert old_sha != expected
    wrong_ref = verify_repository_blob(ROOT, OLD_F47_SHA, CHANGED_PATH, expected)
    assert wrong_ref["match"] is False
    assert wrong_ref["repository_blob_sha256"] == old_sha


def test_require_contract_rejects_invalid_repository_blob():
    with pytest.raises(RepositoryBlobError):
        repository_blob_bytes(ROOT, "HEAD", "scripts/not-a-real-file.py")


def test_windows_autocrlf_worktree_bytes_do_not_define_canonical_provenance():
    if os.name != "nt":
        pytest.skip("Windows checkout semantics are not available")
    autocrlf = subprocess.run(["git", "-C", str(ROOT), "config", "--get", "core.autocrlf"], check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
    if autocrlf.lower() != "true":
        pytest.skip("core.autocrlf=true is required for this semantic check")
    working_tree_sha = hashlib.sha256((ROOT / PROBE_PATH).read_bytes()).hexdigest()
    frozen_sha = repository_blob_sha256(ROOT, "HEAD", PROBE_PATH)
    if working_tree_sha == frozen_sha:
        pytest.skip("this checkout is not materialized with CRLF; pristine Windows run required")
    assert working_tree_sha != frozen_sha
    assert frozen_sha == repository_blob_sha256(ROOT, "HEAD", PROBE_PATH)
