"""F92 acceptance of the built, non-editable wheel artifact."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

from generic_chess import __version__


ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


def test_current_wheel_installs_and_runs_outside_checkout(tmp_path):
    wheel_dir = tmp_path / "wheel"
    wheel_dir.mkdir()
    build = _run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--no-cache-dir",
            "--no-build-isolation",
            "-w",
            str(wheel_dir),
        ],
        cwd=ROOT,
        env=dict(os.environ),
    )
    assert build.returncode == 0, build.stderr
    wheels = list(wheel_dir.glob("*.whl"))
    assert len(wheels) == 1
    wheel = wheels[0]

    required_entries = {
        "generic_chess/__init__.py",
        "generic_chess/ui/__init__.py",
        "generic_chess/ui/i18n/en.json",
        "generic_chess/ui/i18n/zh_CN.json",
        "generic_chess/ui/i18n/ja_JP.json",
    }
    with zipfile.ZipFile(wheel) as archive:
        entries = set(archive.namelist())
        assert required_entries <= entries
        metadata_name = next(name for name in entries if name.endswith(".dist-info/METADATA"))
        entry_points_name = next(name for name in entries if name.endswith(".dist-info/entry_points.txt"))
        metadata = archive.read(metadata_name).decode("utf-8")
        entry_points = archive.read(entry_points_name).decode("utf-8")
    assert "Name: generic-chess" in metadata.splitlines()
    assert f"Version: {__version__}" in metadata.splitlines()
    assert "generic-chess-ui = generic_chess.ui.app:main" in entry_points

    target = tmp_path / "target"
    outside = tmp_path / "outside"
    target.mkdir()
    outside.mkdir()
    install = _run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-cache-dir",
            "--target",
            str(target),
            str(wheel),
        ],
        cwd=outside,
        env=dict(os.environ),
    )
    assert install.returncode == 0, install.stderr

    env = dict(os.environ)
    env["PYTHONPATH"] = str(target)
    env["QT_QPA_PLATFORM"] = "offscreen"
    runtime = textwrap.dedent(
        """
        import importlib.metadata
        import os
        from pathlib import Path

        import generic_chess
        from generic_chess import __version__
        from generic_chess.core.movegen import legal_actions
        from generic_chess.core.transition import initial_state
        from generic_chess.rules.compiler import compile_ruleset_for_execution
        from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
        from generic_chess.rules.western_chess import build_western_chess_ruleset
        from generic_chess.ui.i18n.manager import LocalizationManager

        target = Path(os.environ["F92_TARGET"]).resolve()
        assert Path(generic_chess.__file__).resolve().is_relative_to(target)
        assert importlib.metadata.version("generic-chess") == __version__
        counts = []
        for builder, expected in ((build_western_chess_ruleset, 20), (build_standard_shogi_ruleset, 30)):
            compiled = compile_ruleset_for_execution(builder())
            count = len(legal_actions(initial_state(compiled), compiled))
            assert count == expected
            counts.append(count)
        for language in ("en", "zh_CN", "ja_JP"):
            assert LocalizationManager(language).text("app.title") != "app.title"
        print(generic_chess.__file__, __version__, counts)
        """
    ).strip()
    env["F92_TARGET"] = str(target)
    check = _run([sys.executable, "-c", runtime], cwd=outside, env=env)
    assert check.returncode == 0, check.stderr
    assert str(target) in check.stdout

    version = _run([sys.executable, "-m", "generic_chess.ui", "--version"], cwd=outside, env=env)
    assert version.returncode == 0, version.stderr
    assert version.stdout.strip() == __version__

    smoke = _run([sys.executable, "-m", "generic_chess.ui", "--smoke"], cwd=outside, env=env)
    assert smoke.returncode == 0, smoke.stderr
    assert "Traceback" not in smoke.stderr
