"""F91 release-version authority contract tests."""

from __future__ import annotations

import importlib.metadata
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from generic_chess import __version__
from generic_chess.ui.app import create_application
from generic_chess.ui.controller import UIController
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.settings import KEY_LANGUAGE
from generic_chess.ui.stores import DictSettingsStore


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _close_windows(qapp):
    yield
    for widget in list(qapp.topLevelWidgets()):
        if isinstance(widget, MainWindow):
            widget._shutdown()
            widget.close()
            widget.deleteLater()
    qapp.processEvents()


def test_distribution_metadata_and_setuptools_are_bound_to_runtime_authority():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "version" not in metadata["project"]
    assert "version" in metadata["project"]["dynamic"]
    assert metadata["tool"]["setuptools"]["dynamic"]["version"]["attr"] == (
        "generic_chess.__version__"
    )
    assert importlib.metadata.version("generic-chess") == __version__


def test_qt_application_and_about_use_runtime_authority(qapp, monkeypatch):
    app = create_application([])
    assert app.applicationVersion() == __version__

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    controller = UIController(settings=settings)
    assert controller.new_game(seed=42, board_size=8)
    window = MainWindow(controller, settings)

    shown: dict[str, str] = {}

    def capture_info(parent, title, message):
        shown["title"] = title
        shown["message"] = message

    monkeypatch.setattr("generic_chess.ui.main_window.show_info", capture_info)
    window._show_about()
    assert window._app_version == __version__
    assert __version__ in shown["message"]


@pytest.mark.parametrize("command", [[sys.executable, "-m", "generic_chess.ui"], [str(ROOT / ".venv" / "Scripts" / "generic-chess-ui.exe")]])
def test_ui_version_entry_points(command):
    executable = Path(command[0])
    if executable.suffix.lower() == ".exe" and not executable.exists():
        pytest.skip("generated console executable is not available")
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    proc = subprocess.run(
        [*command, "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == __version__


def test_console_script_declaration_remains_stable():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["scripts"]["generic-chess-ui"] == "generic_chess.ui.app:main"
