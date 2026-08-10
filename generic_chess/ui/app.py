"""QApplication bootstrap and entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .controller import UIController
from .main_window import MainWindow
from .settings import QtSettingsStore


def _window_size(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", 1)
        width, height = int(width_text), int(height_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("window size must be WIDTHxHEIGHT") from exc
    if width < 320 or height < 240:
        raise argparse.ArgumentTypeError("window size is too small")
    return width, height


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
    parser.add_argument(
        "--smoke-ms",
        type=int,
        default=None,
        metavar="N",
        help="show the window, let Qt settle for N milliseconds, then exit",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        metavar="PATH",
        help="save a settled main-window screenshot to PATH and exit",
    )
    parser.add_argument(
        "--window-size",
        type=_window_size,
        default=None,
        metavar="WIDTHxHEIGHT",
        help="resize the window before a smoke/snapshot run",
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
    if args.window_size is not None:
        window.resize(*args.window_size)
    window.show()

    def finish_unattended() -> None:
        if args.snapshot is not None:
            if not window.grab().save(str(args.snapshot)):
                print(f"Could not save GUI snapshot: {args.snapshot}", file=sys.stderr)
                app.exit(2)
                return
        app.quit()

    if args.smoke_ms is not None:
        if args.smoke_ms < 0:
            parser.error("--smoke-ms must be non-negative")
        QTimer.singleShot(args.smoke_ms, finish_unattended)
    elif args.snapshot is not None:
        # A short event-loop settle makes layout, fonts, and the first board
        # fit deterministic in both desktop and offscreen Qt platforms.
        QTimer.singleShot(250, finish_unattended)
    elif args.smoke:
        QTimer.singleShot(0, finish_unattended)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
