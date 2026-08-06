"""Build the native CPython extension with the bundled zig compiler.

This is the supported build on machines without MSVC (the project's dev
machine has no Visual Studio C++ toolchain).  It produces
``generic_chess/_native_core.<abi>.pyd`` using zig cc targeting
``x86_64-windows-gnu`` (Zig-bundled MinGW CRT), which loads in the MSVC-built
CPython on Windows.

Usage::

    python scripts/build_native_zig.py [--debug]

Set ``ZIG`` to override the zig executable location.
"""

from __future__ import annotations

import argparse
import importlib.machinery
import os
import pathlib
import shutil
import subprocess
import sys
import sysconfig


ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = sorted((ROOT / "generic_chess" / "_native").glob("*.c"))
INCLUDE = pathlib.Path(sysconfig.get_paths()["include"])
BASE = pathlib.Path(sys.base_prefix)
OUT = ROOT / "generic_chess" / f"_native_core{sysconfig.get_config_var('EXT_SUFFIX')}"


def find_zig() -> str:
    env_zig = os.environ.get("ZIG")
    if env_zig:
        return env_zig
    venv_candidate = ROOT / ".venv" / "Lib" / "site-packages" / "ziglang" / "zig.exe"
    if venv_candidate.exists():
        return str(venv_candidate)
    found = shutil.which("zig")
    if found:
        return found
    raise RuntimeError(
        "zig compiler not found: pip install ziglang or set ZIG"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="unoptimized build")
    args = parser.parse_args(argv)
    zig = find_zig()
    libs = BASE / "libs"
    python_lib = f"python{sys.version_info.major}{sys.version_info.minor}"
    cmd = [
        zig,
        "cc",
        "-target",
        "x86_64-windows-gnu",
        "-shared",
        "-O0" if args.debug else "-O2",
        f"-I{INCLUDE}",
        f"-L{libs}",
        f"-l{python_lib}",
    ] + [str(s) for s in SOURCES] + ["-o", str(OUT)]
    env = dict(os.environ)
    cache = ROOT / ".gc_zig_cache"
    cache.mkdir(exist_ok=True)
    env["ZIG_GLOBAL_CACHE_DIR"] = str(cache)
    print("zig:", zig)
    print("command:", " ".join(cmd))
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        print("native build FAILED", file=sys.stderr)
        return result.returncode
    print(f"built {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
