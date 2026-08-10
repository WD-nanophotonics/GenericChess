"""Capture the deterministic Round 3 visual QA matrix offscreen."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.ui.controller import UIController
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.settings import KEY_ENABLE_ANIMATIONS, KEY_LANGUAGE
from generic_chess.ui.stores import DictSettingsStore

from scripts.ui_redesign_smoke import _base_ruleset


def _hand_ruleset():
    from generic_chess.core.pieces import PieceType
    from generic_chess.rules.schema import RuleSet

    king = PieceType(
        "K",
        "King",
        tuple(
            LeapAtom((df, dr))
            for df in (-1, 0, 1)
            for dr in (-1, 0, 1)
            if (df, dr) != (0, 0)
        ),
        is_anchor=True,
    )
    rook = PieceType(
        "R",
        "Rook",
        (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0))),
    )
    filler = PieceType("F", "Filler", (LeapAtom((1, 0)),))
    from generic_chess.core.pieces import Piece

    board = [[None] * 8 for _ in range(8)]
    board[0][0] = Piece(0, "K", "K", False)
    board[0][1] = Piece(0, "R", "R", False)
    board[0][2] = Piece(1, "F", "F", False)
    board[7][7] = Piece(1, "K", "K", False)
    mask = (True,) * 64
    return RuleSet(
        schema_version=1,
        board_size=8,
        piece_types=(king, rook, filler),
        initial_position=tuple(tuple(row) for row in board),
        drop_allowed={"R": (mask, mask), "F": (mask, mask)},
        promotion_allowed={},
        promotion_forced={},
        repetition_limit=4,
        max_ply=512,
        stalemate_result="draw",
    )


def _window(language: str = "en"):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, language)
    settings.set(KEY_ENABLE_ANIMATIONS, False)
    controller = UIController(settings=settings)
    controller.new_game_from_ruleset(_base_ruleset())
    window = MainWindow(controller, settings)
    return controller, window


def _save(window: MainWindow, path: Path, size: tuple[int, int]) -> None:
    window.resize(*size)
    window.show()
    window._refresh()
    QApplication.processEvents()
    window.grab().save(str(path))


def _close(window: MainWindow) -> None:
    window._shutdown()
    window.close()
    window.deleteLater()
    QApplication.processEvents()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    output = Path(
        os.environ.get(
            "GENERICCHESS_ROUND3_OUTPUT",
            str(ROOT / "artifacts" / "ui_round3"),
        )
    )
    output.mkdir(parents=True, exist_ok=True)

    controller, window = _window("en")
    _save(window, output / "round3_en_760x540_live.png", (760, 540))
    _close(window)

    controller, window = _window("en")
    square = next(
        sv.square
        for sv in controller.board_view_model().squares
        if sv.piece is not None and sv.piece.owner == 0
    )
    controller.square_clicked(square)
    _save(window, output / "round3_en_1180x760_selected.png", (1180, 760))
    _close(window)

    controller, window = _window("zh_CN")
    window._sidebar.setCurrentWidget(window._rules_panel)
    if window._rules_panel._types.count():
        type_id = window._rules_panel._types.item(0).data(256)
        window._rules_panel.inspect_type(type_id)
    _save(window, output / "round3_zh_900x620_rules.png", (900, 620))
    _close(window)

    controller, window = _window("ja_JP")
    for _ in range(2):
        actions = controller.session.legal_actions()
        if not actions:
            break
        controller.submit_action(next((a for a in actions if isinstance(a, BoardMove)), actions[0]))
    controller.display_ply(1)
    window._sidebar.setCurrentWidget(window._moves_panel)
    _save(window, output / "round3_ja_1180x760_history.png", (1180, 760))
    _close(window)

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    settings.set(KEY_ENABLE_ANIMATIONS, False)
    controller = UIController(settings=settings)
    controller.new_game_from_ruleset(_hand_ruleset())
    controller.resign()
    window = MainWindow(controller, settings)
    window._sidebar.setCurrentWidget(window._moves_panel)
    _save(window, output / "round3_en_1440x900_gameover.png", (1440, 900))
    _close(window)

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    settings.set(KEY_ENABLE_ANIMATIONS, False)
    controller = UIController(settings=settings)
    controller.new_game_from_ruleset(_hand_ruleset())
    controller.submit_action(BoardMove(Square(1, 0), Square(2, 0)))
    window = MainWindow(controller, settings)
    _save(window, output / "round3_en_900x620_hand.png", (900, 620))
    _close(window)

    for path in sorted(output.glob("round3_*.png")):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
