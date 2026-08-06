"""Native Phase 1 rule kernel (optional CPython C extension).

The extension is built by ``scripts/build_native_zig.py`` (or a standard
MSVC setuptools build on compiler-equipped machines).  When it is not built,
``native_available()`` returns False and native tests are skipped; the Python
Core remains the specification and correctness oracle either way.
"""

from __future__ import annotations

from typing import Any

_MODULE = None


def _load() -> Any:
    global _MODULE
    if _MODULE is None:
        import importlib

        _MODULE = importlib.import_module("generic_chess._native_core")
    return _MODULE


def native_available() -> bool:
    try:
        _load()
        return True
    except ImportError:
        return False


def native_version() -> str:
    if not native_available():
        return "unavailable"
    return str(_load().native_version())


def native_capabilities() -> dict:
    if not native_available():
        return {"available": False}
    caps = dict(_load().native_capabilities())
    caps["available"] = True
    return caps


def _module():
    return _load()


__all__ = [
    "native_available",
    "native_version",
    "native_capabilities",
]
