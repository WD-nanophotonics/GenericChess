"""Double-click launcher for the GenericChess desktop UI.

If PySide6 is importable in the current interpreter it starts the UI
directly; otherwise it re-launches itself with the project venv Python
(``.venv\\Scripts\\python.exe``), so double-clicking works regardless of the
default ``.py`` file association.

Usage:  python run_ui.py [--seed 42] [--board-size 8] [--preset classic_like]
                         [--hybrid] [--ruleset path] [--smoke]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def _relaunch_with_venv() -> int:
    if Path(sys.executable).resolve() == VENV_PYTHON.resolve():
        print(
            "PySide6 is not installed in the project venv.\n"
            'Install it with:  .venv\\Scripts\\python.exe -m pip install -e ".[gui]"',
            file=sys.stderr,
        )
        return 1
    if not VENV_PYTHON.exists():
        print(
            "PySide6 is not installed and no project venv was found.\n"
            'Create/install it with:  python -m pip install -e ".[gui]"',
            file=sys.stderr,
        )
        return 1
    print(f"Relaunching with {VENV_PYTHON} ...", file=sys.stderr)
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
    return 1  # unreachable


def main() -> int:
    try:
        import PySide6  # noqa: F401
    except ImportError:
        return _relaunch_with_venv()
    from generic_chess.ui.app import main as ui_main

    return ui_main(sys.argv[1:])


if __name__ == "__main__":
    code = main()
    if code != 0 and sys.stdin.isatty():
        input("Press Enter to exit...")
    raise SystemExit(code)
