"""Read-only validation helpers for immutable pre-R1 checkpoints."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# R1 is an explicitly bounded semantic-native corrective.  Historical
# production-scope checks may therefore exclude only these files; all other
# paths must remain identical to the pinned checkpoint.
R1_ALLOWED_PRODUCTION_PATHS = frozenset({
    "generic_chess/native/compiler.py",
    "generic_chess/native/semantic.py",
    "generic_chess/_native/native_module.c",
    "generic_chess/_native/native_semantic_rules.c",
    "generic_chess/_native/native_semantic_rules.h",
    "generic_chess/_native/native_semantic_runtime.c",
    "generic_chess/_native/native_semantic_runtime.h",
    "generic_chess/_native/native_semantic_state.c",
    "generic_chess/_native/native_semantic_state.h",
})


def git_blob_sha256(ref: str, relative_path: str) -> str:
    """Hash the exact historical blob, never the mutable working tree file."""
    raw = subprocess.run(
        ["git", "cat-file", "blob", f"{ref}:{relative_path}"],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout
    return hashlib.sha256(raw).hexdigest()


def historical_scope_unchanged(ref: str, scope: str = "generic_chess") -> bool:
    """Return whether only the explicitly authorized R1 files differ."""
    changed = subprocess.run(
        ["git", "diff", "--name-only", ref, "HEAD", "--", scope],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    return all(path.replace("\\", "/") in R1_ALLOWED_PRODUCTION_PATHS
               for path in changed)


def historical_scope_unchanged_worktree(scope: str = "generic_chess") -> bool:
    """Working-tree form used while R1 is being developed."""
    changed = subprocess.run(
        ["git", "diff", "--name-only", "--", scope],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    return all(path.replace("\\", "/") in R1_ALLOWED_PRODUCTION_PATHS
               for path in changed)
