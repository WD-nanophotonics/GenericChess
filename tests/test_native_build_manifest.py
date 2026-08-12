from __future__ import annotations

from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def test_packaging_manifest_contains_every_native_source():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    configured = {
        Path(source).as_posix()
        for source in config["tool"]["setuptools"]["ext-modules"][0]["sources"]
    }
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "generic_chess" / "_native").glob("*.c")
    }
    assert configured == actual
