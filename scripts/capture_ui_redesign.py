"""Generate deterministic UI screenshots for visual acceptance.

Outputs to ``artifacts/ui_redesign/`` (gitignored). Scenes:

1. zh_CN opening (9x9, Rules tab, a piece type selected)
2. ja_JP midgame (hand non-empty, Moves tab, >= 10 plies)
3. en_GB checkmate (game over, no "to move", history visible)
4. small-window sanity (1024x700, zh_CN opening)
"""

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


def _window(seed=42, board_size=8, language="zh_CN", preset="classic_like"):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, language)
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=seed, board_size=board_size, preset=preset)
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
    out = ROOT / "artifacts" / "ui_redesign"
    out.mkdir(parents=True, exist_ok=True)

    # 1. zh_CN opening on 9x9, Rules tab with a selected piece type.
    ctrl, win = _window(seed=7, board_size=9, language="zh_CN")
    win._sidebar.setCurrentWidget(win._rules_panel)
    if win._rules_panel._types.count():
        first_type = win._rules_panel._types.item(0).data(256)
        win._rules_panel.inspect_type(first_type)
    _shoot(win, out / "zh_CN_opening_rules.png")

    # 2. ja_JP midgame with a non-empty hand and >= 10 plies on Moves tab.
    ctrl, win = _window(seed=42, board_size=6, language="ja_JP")
    for _ in range(16):
        actions = ctrl.session.legal_actions()
        if not actions or ctrl.session.result.status.value != "ongoing":
            break
        ctrl.submit_action(actions[0])
    win._sidebar.setCurrentWidget(win._moves_panel)
    win._refresh()
    _shoot(win, out / "ja_JP_midgame_moves.png")

    # 3. en checkmate: mate ruleset + the known mating move.
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    ctrl.new_game_from_ruleset(_mate_ruleset())
    ctrl.submit_action(BoardMove(Square(1, 4), Square(0, 4)))
    win = MainWindow(ctrl, settings)
    win._sidebar.setCurrentWidget(win._moves_panel)
    _shoot(win, out / "en_checkmate.png")

    # 4. Small window sanity.
    ctrl, win = _window(seed=7, board_size=9, language="zh_CN")
    win._sidebar.setCurrentWidget(win._rules_panel)
    _shoot(win, out / "small_1024x700.png", size=(1024, 700))

    for path in sorted(out.glob("*.png")):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
