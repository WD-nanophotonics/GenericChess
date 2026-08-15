"""Run the supported Native build and write machine-readable text evidence."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
output = ROOT / "artifacts" / "f22_post_f21_rebaseline_strength" / sys.argv[1]
out_binary = Path(sys.argv[2])
zig = Path(r"C:\Users\icywo\PycharmProjects\GenericChess\.venv\Lib\site-packages\ziglang\zig.exe")
cache = Path(os.environ.get("ZIG_GLOBAL_CACHE_DIR", r"C:\Users\icywo\AppData\Local\Temp\generic_chess_zig_cache_f22_final"))
env = dict(os.environ)
env["ZIG"] = str(zig)
env["ZIG_GLOBAL_CACHE_DIR"] = str(cache)
env["NATIVE_BUILD_OUT"] = str(out_binary)
result = subprocess.run([sys.executable, "-u", "scripts/build_native_zig.py"], cwd=ROOT, env=env, capture_output=True, text=True)
lines = [result.stdout, result.stderr, f"exit_code={result.returncode}"]
if out_binary.exists():
    digest = hashlib.sha256(out_binary.read_bytes()).hexdigest()
    lines.append(f"bytes={out_binary.stat().st_size}")
    lines.append(f"sha256={digest}")
output.write_text("\n".join(lines) + "\n", encoding="utf-8")
raise SystemExit(result.returncode)
