"""Rebuild the public evidence copy into a temp dir and compare with the published one.

Determinism check for publication: the sanitizer must reproduce the exact
published bytes from the private originals, otherwise the copy is stale.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
PUBLISHED = ROOT / "docs" / "research" / "data" / "profile_transform_invariance_20261018"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    spec = importlib.util.spec_from_file_location("mpe", HERE / "make_public_evidence.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    with tempfile.TemporaryDirectory() as tmp:
        module.DEST = Path(tmp)
        module.main()
        rebuilt = {p.name: sha256(p) for p in Path(tmp).iterdir() if p.is_file()}

    manifest = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    published = {e["file"]: e["sha256"] for e in manifest["files"]}
    published["manifest.json"] = sha256(PUBLISHED / "manifest.json")
    problems = []
    for name, digest in sorted(published.items()):
        if name not in rebuilt:
            problems.append(f"missing_in_rebuild {name}")
        elif rebuilt[name] != digest:
            problems.append(f"differs {name} published={digest} rebuilt={rebuilt[name]}")
    for name in sorted(set(rebuilt) - set(published)):
        problems.append(f"extra_in_rebuild {name}")
    print(f"published_entries={len(published)} rebuilt_entries={len(rebuilt)}")
    for item in problems:
        print(item)
    print("rebuild_reproduces_published_copy" if not problems else "rebuild_differs_from_published")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
