import hashlib, json
from pathlib import Path

out = Path(__file__).resolve().parents[1] / "artifacts" / "f9_terminal_legal_probe_reuse"
manifest = {}
for path in sorted(out.iterdir()):
    if path.name == "manifest.json" or not path.is_file():
        continue
    manifest[path.name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
(out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
