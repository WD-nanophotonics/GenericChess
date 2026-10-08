"""Build the supported Native extension with the installed Zig compiler.

Restored from the isolated cleanup snapshot when a Native source fix required
rebuilding. Uses the current Python ABI and sources, without installing tools.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)
    bundled = ROOT / ".venv/Lib/site-packages/ziglang/zig.exe"
    zig = os.environ.get("ZIG") or (str(bundled) if bundled.exists() else shutil.which("zig"))
    if not zig:
        parser.error("Zig is unavailable; set ZIG to an installed compiler")
    output = Path(os.environ.get("NATIVE_BUILD_OUT", str(
        ROOT / "generic_chess" / ("_native_core" + sysconfig.get_config_var("EXT_SUFFIX")))))
    command = [zig, "cc", "-target", "x86_64-windows-gnu", "-shared",
               "-O0" if args.debug else "-O2",
               "-I" + sysconfig.get_paths()["include"],
               "-L" + str(Path(sys.base_prefix) / "libs"),
               "-lpython" + str(sys.version_info.major) + str(sys.version_info.minor)]
    command.extend(str(p) for p in sorted((ROOT / "generic_chess/_native").glob("*.c")))
    command.extend(["-o", str(output)])
    env = dict(os.environ)
    cache = Path(env.get("ZIG_GLOBAL_CACHE_DIR", str(ROOT / ".gc_zig_cache")))
    cache.mkdir(parents=True, exist_ok=True)
    env["ZIG_GLOBAL_CACHE_DIR"] = str(cache)
    print("Building", output, flush=True)
    result = subprocess.run(command, env=env, timeout=180)
    if result.returncode:
        return result.returncode
    print("Built", output, output.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
