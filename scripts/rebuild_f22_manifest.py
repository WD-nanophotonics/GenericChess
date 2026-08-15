"""Rebuild the F22 artifact manifest after final evidence writes."""

from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
out = root / "artifacts" / "f22_post_f21_rebaseline_strength"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


files = sorted(path for path in out.rglob("*") if path.is_file() and path.name != "manifest.json")
(out / "manifest.json").write_text(json.dumps({"sha256": {str(path.relative_to(out)).replace("\\", "/"): digest(path) for path in files}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"files": len(files), "manifest": str(out / "manifest.json")}, sort_keys=True))
