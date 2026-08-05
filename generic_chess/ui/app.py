"""QApplication bootstrap and entry point."""

from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .controller import UIController
from .main_window import MainWindow
from .settings import QtSettingsStore


def create_application(argv: list[str] | None = None) -> QApplication:
    QCoreApplication.setOrganizationName("GenericChess")
    QCoreApplication.setApplicationName("GenericChess")
    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationVersion("0.5.0")
    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="generic-chess-ui")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--board-size", type=int, default=8)
    parser.add_argument("--preset", default="classic_like")
    parser.add_argument("--hybrid", action="store_true")
    parser.add_argument("--ruleset", type=str, default=None)
    parser.add_argument(
        "--smoke", action="store_true", help="quit immediately after the window shows (headless check)"
    )
    args, _ = parser.parse_known_args(argv)

    app = create_application(argv)
    settings = QtSettingsStore()
    controller = UIController(settings=settings)
    if args.ruleset:
        controller.open_ruleset(args.ruleset)
    else:
        controller.new_game(
            seed=args.seed,
            board_size=args.board_size,
            preset=args.preset,
            hybrid=args.hybrid,
        )
    window = MainWindow(controller, settings)
    window.show()
    if args.smoke:
        QTimer.singleShot(0, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
