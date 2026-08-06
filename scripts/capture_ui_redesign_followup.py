"""Generate deterministic follow-up UI screenshots for visual acceptance.

Outputs to ``artifacts/ui_redesign_followup/`` (gitignored). Scenes:

1. zh_CN rules page with a board piece selected (selection banner + diagram)
2. zh_CN king-like one-step diagram (5x5, outer ring empty)
3. zh_CN rook ray diagram (continuation arrows + forward label)
4. zh_CN checkmate with the board-center game-over overlay
5. ja_JP checkmate overlay (localization check)
6. small 1024x700 window with a scrolled rules page
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from generic_chess.ui.controller import UIController
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.settings import KEY_LANGUAGE
from generic_chess.ui.stores import DictSettingsStore


def _mate_ruleset():
    from generic_chess.core.movement import LeapAtom, RayAtom
    from generic_chess.core.pieces import Piece, PieceType
    from generic_chess.rules.compiler import compile_ruleset
    from generic_chess.rules.schema import RuleSet

    n = 8
    king = PieceType(
        "K",
        "K",
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
        "R",
        (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0))),
    )
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(1, "K", "K", False)
    rows[0][2] = Piece(0, "K", "K", False)
    rows[4][1] = Piece(0, "R", "R", False)
    rows[1][5] = Piece(0, "R", "R", False)
    mask = (False,) * (n * n)
    ruleset = RuleSet(
        schema_version=1,
        board_size=n,
        piece_types=(king, rook),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"R": (mask, mask)},
        promotion_allowed={},
        promotion_forced={},
        repetition_limit=4,
        max_ply=512,
        stalemate_result="draw",
    )
    return compile_ruleset(ruleset)


def _base_ruleset():
    from generic_chess.rules.schema import RuleSet
    from generic_chess.core.pieces import Piece, PieceType
    from generic_chess.core.movement import LeapAtom, RayAtom

    king = PieceType(
        "K",
        "K",
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
        "R",
        (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0))),
    )
    filler = PieceType("F", "F", (LeapAtom((1, 0)), LeapAtom((-1, 0))))
    n = 8
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(1, "K", "K", False)
    rows[7][7] = Piece(0, "K", "K", False)
    rows[6][0] = Piece(1, "R", "R", False)
    rows[6][7] = Piece(0, "R", "R", False)
    rows[0][6] = Piece(0, "F", "F", False)
    mask = (True,) * (n * n)
    return RuleSet(
        schema_version=1,
        board_size=n,
        piece_types=(king, rook, filler),
        initial_position=tuple(tuple(r) for r in rows),
        drop_allowed={"R": (mask, mask), "F": (mask, mask)},
        promotion_allowed={},
        promotion_forced={},
        repetition_limit=4,
        max_ply=512,
        stalemate_result="draw",
    )


def _window(ruleset, language="zh_CN"):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, language)
    ctrl = UIController(settings=settings)
    ctrl.new_game_from_ruleset(ruleset)
    win = MainWindow(ctrl, settings)
    return ctrl, win


def _shoot(win, path: Path, size=(1280, 800)) -> None:
    win.resize(*size)
    win.show()
    win._refresh()
    QApplication.processEvents()
    win.grab().save(str(path))


def main() -> int:
    app = QApplication.instance() or QApplication([])
    out = ROOT / "artifacts" / "ui_redesign_followup"
    out.mkdir(parents=True, exist_ok=True)

    # 1. zh_CN rules page, board piece selected -> banner + diagram.
    ctrl, win = _window(_base_ruleset(), language="zh_CN")
    win._sidebar.setCurrentWidget(win._rules_panel)
    piece_sq = next(
        sv.square
        for sv in ctrl.board_view_model().squares
        if sv.piece is not None and sv.piece.owner == 0
    )
    ctrl.square_clicked(piece_sq)
    _shoot(win, out / "zh_CN_rules_selection.png")

    # 2. King-like one-step diagram (5x5).
    ctrl, win = _window(_base_ruleset(), language="zh_CN")
    win._sidebar.setCurrentWidget(win._rules_panel)
    win._rules_panel.inspect_type("K")
    _shoot(win, out / "zh_CN_one_step_king.png")

    # 3. Ray rook diagram (continuation arrows + forward label).
    ctrl, win = _window(_base_ruleset(), language="zh_CN")
    win._sidebar.setCurrentWidget(win._rules_panel)
    win._rules_panel.inspect_type("R")
    _shoot(win, out / "zh_CN_ray_rook.png")

    # 4. zh_CN checkmate with the board-center overlay.
    ctrl, win = _window(_mate_ruleset(), language="zh_CN")
    ctrl.submit_action(BoardMove(Square(1, 4), Square(0, 4)))
    win._sidebar.setCurrentWidget(win._moves_panel)
    _shoot(win, out / "zh_CN_game_over_overlay.png")

    # 5. ja_JP checkmate overlay (localization).
    ctrl, win = _window(_mate_ruleset(), language="ja_JP")
    ctrl.submit_action(BoardMove(Square(1, 4), Square(0, 4)))
    win._sidebar.setCurrentWidget(win._moves_panel)
    _shoot(win, out / "ja_JP_game_over_overlay.png")

    # 6. Small 1024x700 window; scroll the rules detail to show the bottom.
    ctrl, win = _window(_base_ruleset(), language="zh_CN")
    win._sidebar.setCurrentWidget(win._rules_panel)
    win._rules_panel.inspect_type("R")
    _shoot(win, out / "small_1024x700.png", size=(1024, 700))
    win._rules_panel._scroll.verticalScrollBar().setValue(
        win._rules_panel._scroll.verticalScrollBar().maximum()
    )
    QApplication.processEvents()
    win.grab().save(str(out / "small_1024x700_scrolled.png"))

    for path in sorted(out.glob("*.png")):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
