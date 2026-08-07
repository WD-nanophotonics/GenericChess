"""Machine-readable architecture inventory for the rule-semantics audit
(Learning Phase 1.9A-1).

Read-only: computes source inventory (files/LOC), a module-level dependency
map, game-name token locations in core/native, the FFI entry-point table and
hot-path allocation markers, then writes
``artifacts/rule_semantics_audit/architecture_inventory.json``.
"""

from __future__ import annotations

import ast
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "generic_chess"
NATIVE_C = PKG / "_native"
TESTS = ROOT / "tests"
OUT = ROOT / "artifacts" / "rule_semantics_audit" / "architecture_inventory.json"


def _py_files(directory: Path) -> list[Path]:
    return sorted(directory.rglob("*.py")) if directory.exists() else []


def _c_files(directory: Path) -> list[Path]:
    return sorted(directory.rglob("*.c")) + sorted(directory.rglob("*.h"))


def _loc(paths: list[Path]) -> int:
    total = 0
    for path in paths:
        try:
            total += sum(1 for _ in path.open(encoding="utf-8", errors="ignore"))
        except OSError:
            pass
    return total


def _module_name(path: Path) -> str:
    rel = path.relative_to(ROOT).with_suffix("")
    return ".".join(rel.parts)


def _imported_modules(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, SyntaxError):
        return set()
    out: set[str] = set()
    package_parts = path.relative_to(ROOT).parent.parts
    package = ".".join(package_parts) if path.parent != ROOT else ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")[: node.level - 1] if node.level > 1 else []
                module = ".".join(base + ([node.module] if node.module else []))
                out.add(module.split(".")[0] if module else package)
            elif node.module:
                out.add(node.module.split(".")[0])
    return {m for m in out if m and not m.startswith("_")}


def _dependency_map() -> dict:
    modules: dict[str, dict] = {}
    for path in _py_files(PKG):
        name = _module_name(path)
        modules[name] = {
            "file": str(path.relative_to(ROOT)),
            "loc": _loc([path]),
            "imports": sorted(_imported_modules(path)),
        }
    return modules


def _token_scan() -> dict:
    tokens = (
        "pawn",
        "king",
        "rook",
        "bishop",
        "knight",
        "shogi",
        "chess",
        "xiangqi",
        "cannon",
        "castl",
        "nifu",
        "en_passant",
        "uchifuzume",
    )
    results: dict[str, list[dict]] = {}
    for token in tokens:
        hits: list[dict] = []
        for directory, suffix in ((PKG / "core", ".py"), (NATIVE_C, None)):
            for path in sorted(directory.rglob("*")):
                if suffix and path.suffix != suffix:
                    continue
                if not suffix and path.suffix not in (".c", ".h"):
                    continue
                try:
                    for lineno, line in enumerate(
                        path.open(encoding="utf-8", errors="ignore"), 1
                    ):
                        if token.lower() in line.lower():
                            hits.append(
                                {
                                    "file": str(path.relative_to(ROOT)),
                                    "line": lineno,
                                    "text": line.strip()[:120],
                                }
                            )
                except OSError:
                    continue
        results[token] = hits
    return results


def _ffi_scan() -> dict:
    method_defs: list[str] = []
    py_calls: list[dict] = []
    hot_malloc: list[dict] = []
    module_c = NATIVE_C / "native_module.c"
    search_c = NATIVE_C / "native_search.c"
    if module_c.exists():
        for lineno, line in enumerate(
            module_c.open(encoding="utf-8", errors="ignore"), 1
        ):
            stripped = line.strip()
            if stripped.startswith('{"'):
                method_defs.append(stripped.split('"')[1])
    for path in sorted(NATIVE_C.glob("*.c")):
        for lineno, line in enumerate(
            path.open(encoding="utf-8", errors="ignore"), 1
        ):
            if "PyObject_Call" in line or "PyEval_" in line or "PyCallable" in line:
                py_calls.append(
                    {
                        "file": str(path.relative_to(ROOT)),
                        "line": lineno,
                        "text": line.strip()[:120],
                    }
                )
    if search_c.exists():
        for lineno, line in enumerate(
            search_c.open(encoding="utf-8", errors="ignore"), 1
        ):
            if "malloc" in line or "calloc" in line:
                hot_malloc.append(
                    {"file": "generic_chess/_native/native_search.c", "line": lineno}
                )
    return {
        "entry_points": method_defs,
        "python_runtime_calls_in_c": py_calls,
        "malloc_in_search_c": hot_malloc,
    }


def main() -> int:
    timing: dict[str, float] = {}
    start = time.perf_counter()

    t0 = time.perf_counter()
    py_files = _py_files(PKG)
    c_files = _c_files(NATIVE_C)
    test_files = _py_files(TESTS)
    native_bridge = _py_files(PKG / "native")
    timing["source_inventory"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    dependencies = _dependency_map()
    timing["dependency_audit"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    tokens = _token_scan()
    timing["token_scan"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    ffi = _ffi_scan()
    timing["ffi_scan"] = time.perf_counter() - t0

    timing["total_wall_seconds"] = time.perf_counter() - start

    inventory = {
        "schema_version": 1,
        "repository": str(ROOT),
        "python": {
            "files": len(py_files),
            "loc": _loc(py_files),
        },
        "c": {
            "files": len(c_files),
            "loc": _loc(c_files),
        },
        "tests": {
            "files": len(test_files),
            "loc": _loc(test_files),
        },
        "native_bridge_python": {
            "files": len(native_bridge),
            "loc": _loc(native_bridge),
        },
        "directory_loc": {
            str(path.relative_to(PKG)): _loc(_py_files(path))
            for path in sorted(p for p in PKG.iterdir() if p.is_dir())
        },
        "module_dependencies": dependencies,
        "token_scan": tokens,
        "ffi": ffi,
        "timing_seconds": timing,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "python_files": inventory["python"]["files"],
                "python_loc": inventory["python"]["loc"],
                "c_files": inventory["c"]["files"],
                "c_loc": inventory["c"]["loc"],
                "test_files": inventory["tests"]["files"],
                "test_loc": inventory["tests"]["loc"],
                "ffi_entry_points": len(ffi["entry_points"]),
                "python_runtime_calls_in_c": len(ffi["python_runtime_calls_in_c"]),
                "timing_seconds": timing,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
