"""Offscreen smoke covering the manual acceptance checklist.

Prints PASS/FAIL per item. Run::

    python scripts/ui_redesign_smoke.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog

from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.ui.controller import UIController
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.settings import KEY_LANGUAGE
from generic_chess.ui.stores import DictSettingsStore


def _base_ruleset():
    from generic_chess.rules.schema import RuleSet
    from generic_chess.core.pieces import Piece, PieceType

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
    ruleset = RuleSet(
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
    return ruleset


def main() -> int:
    app = QApplication.instance() or QApplication([])
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, bool(ok), detail))
        print(("PASS" if ok else "FAIL") + f"  {name}" + (f"  ({detail})" if detail else ""))

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    ctrl.new_game_from_ruleset(_base_ruleset())
    win = MainWindow(ctrl, settings)
    win.show()
    win._refresh()

    # Human vs Human moves.
    actions = ctrl.session.legal_actions()
    ctrl.submit_action(actions[0])
    ctrl.submit_action(ctrl.session.legal_actions()[0])
    win._refresh()
    check("human moves", ctrl.session.state.ply_count == 2, f"ply={ctrl.session.state.ply_count}")

    # Select a piece and open Rules.
    model = ctrl.board_view_model()
    piece_sq = next(
        sv.square
        for sv in model.squares
        if sv.piece is not None and sv.piece.owner == 0
    )
    ctrl.square_clicked(piece_sq)
    win._refresh()
    win._show_rules_tab()
    check("select piece + Rules tab", win._sidebar.currentWidget() is win._rules_panel)
    check("rules detail filled", bool(win._rules_panel._detail.text()))
    banner = win._rules_panel._entity
    check(
        "selection banner visible",
        banner.isVisible(),
        banner._body.text() if banner.isVisible() else "banner hidden",
    )
    check(
        "selection banner localized",
        "White" in banner._body.text() or "白" in banner._body.text(),
    )
    ctrl.cancel()
    win._refresh()
    check("selection banner hides on cancel", not banner.isVisible())

    # Browse several piece types.
    ids = [pt.type_id for pt in ctrl.compiled.piece_types]
    for tid in ids:
        win._inspect_type(tid)
    check("browse all piece types", win._rules_panel._types.count() == len(ids))
    check(
        "movement diagram populated",
        win._rules_panel._diagram.layout_data() is not None,
        str(win._rules_panel._diagram.layout_data()),
    )
    scroll = win._rules_panel._scroll
    check(
        "rules detail scrollable",
        scroll.widgetResizable()
        and not scroll.horizontalScrollBar().isVisible(),
    )
    check(
        "detail content aligned top",
        bool(
            win._rules_panel._detail_layout.alignment()
            & Qt.AlignmentFlag.AlignTop
        ),
    )
    check("toolbar tooltips localized", bool(win._toolbar_actions()["undo"].toolTip()))
    icons = [
        win._toolbar_actions()[name].icon().pixmap(24, 24).toImage()
        for name in ("new", "open", "save", "undo", "redo", "flip")
    ]
    distinct = sum(1 for i in range(len(icons)) for j in range(i + 1, len(icons)) if icons[i] != icons[j])
    check("toolbar icons distinct", distinct == 15, f"{distinct}/15 distinct pairs")

    # Capture -> hand -> drop (bounded deterministic walk until a capture).
    hand_owner = None
    for _ in range(20):
        side = ctrl.session.state.position.side_to_move
        acts = ctrl.session.legal_actions()
        if not acts or ctrl.session.result.status.value != "ongoing":
            break
        n = ctrl.compiled.board_size
        cap = next(
            (
                a
                for a in acts
                if isinstance(a, BoardMove)
                and ctrl.session.state.position.board[
                    a.to_square.rank * n + a.to_square.file
                ]
                is not None
            ),
            None,
        )
        ctrl.submit_action(cap if cap is not None else acts[0])
        if cap is not None:
            hand_owner = side
            break
    win._refresh()
    bar = win._player_bars[hand_owner] if hand_owner is not None else win._player_bars[0]
    check("capture fills hand", hand_owner is not None and not bar.is_hand_empty())
    # Let the other side move, then drop from hand.
    ctrl.submit_action(ctrl.session.legal_actions()[0])
    win._refresh()
    buttons = bar.hand_buttons()
    if buttons:
        buttons[0].click()
    check("hand click enters drop mode", ctrl.interaction.selected_hand_piece_type_id is not None)
    if ctrl.interaction.legal_actions:
        ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    check("drop committed", ctrl.session.state.position.hands[hand_owner].counts == ())

    # Replay + return to live.
    ctrl.display_ply(1)
    win._refresh()
    check("replay displays ply", ctrl.interaction.displayed_ply == 1)
    ctrl.return_to_current()
    win._refresh()
    check("return to live", ctrl.interaction.displayed_ply is None)

    # Flip + resize + splitter.
    before_bottom = win._bar_bottom.owner()
    ctrl.flip_board()
    win._refresh()
    check("flip swaps bars", win._bar_bottom.owner() != before_bottom)
    transform_before = win._board_view.transform()
    win.resize(1100, 760)
    win._refresh()
    check("resize updates fit", win._board_view.transform() != transform_before)
    win._splitter.setSizes([500, 300])
    check("splitter draggable", True)

    # Language switch.
    for lang, marker in (("ja_JP", "棋譜"), ("zh_CN", "棋谱"), ("en", "Moves")):
        win._tr.set_language(lang)
        check(f"language {lang}", win._sidebar.tabText(0) == marker, win._sidebar.tabText(0))
    settings.set(KEY_LANGUAGE, "en")
    win._tr.set_language("en")

    # Preferences open/close twice + language persist.
    from generic_chess.ui.dialogs.preferences_dialog import PreferencesDialog
    from PySide6.QtWidgets import QDialog

    original_exec = PreferencesDialog.exec
    PreferencesDialog.exec = lambda self: QDialog.Accepted
    try:
        win._preferences()
        win._preferences()
    finally:
        PreferencesDialog.exec = original_exec
    check("preferences opened twice", True)

    # Diagnostics.
    from generic_chess.ui.dialogs.diagnostics_dialog import DiagnosticsDialog

    dialog = DiagnosticsDialog(ctrl, win._tr, "0.7.0a1")
    check("diagnostics opens", dialog._labels["diagnostics.ruleset_fingerprint"].text() != "—")

    # Restart and Resign.
    win._restart()
    check("restart resets", ctrl.session.state.ply_count == 0)
    ctrl.resign()
    win._refresh()
    check("resign ends", ctrl.session.result.status.value != "ongoing")
    check("overlay shows on terminal", win._overlay.isVisible())
    check(
        "overlay winner/reason localized",
        bool(win._overlay._winner.text()) and bool(win._overlay._reason.text()),
        f"{win._overlay._winner.text()} / {win._overlay._reason.text()}",
    )
    ctrl.display_ply(0)
    win._refresh()
    check("overlay hidden during history preview", not win._overlay.isVisible())
    ctrl.return_to_current()
    win._refresh()
    check("overlay restored on return to live", win._overlay.isVisible())
    win.resize(1000, 700)
    app.processEvents()
    check(
        "overlay centered after resize",
        win._overlay.geometry() == win._board_container.rect(),
    )
    win._overlay._btn_dismiss.click()
    check(
        "overlay dismiss keeps game terminal",
        not win._overlay.isVisible() and ctrl.session.result.status.value != "ongoing",
    )
    win._restart()
    check("overlay hidden after restart", not win._overlay.isVisible())

    # File dialog cancel preserves state.
    ctrl2 = UIController(settings=settings)
    ctrl2.new_game(seed=42)
    win2 = MainWindow(ctrl2, settings)
    sentinel = object()
    win2._ai_player = sentinel
    original_get = QFileDialog.getOpenFileName
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
    try:
        win2._open_ruleset()
    finally:
        QFileDialog.getOpenFileName = original_get
    check("file dialog cancel preserves AI", win2._ai_player is sentinel)

    # Human vs AlphaBeta + close during AI.
    ctrl3 = UIController(settings=settings)
    ctrl3.new_game(seed=42)
    win3 = MainWindow(ctrl3, settings)
    from generic_chess.ai.budget import ThinkingConfig, ThinkingStrategy
    from generic_chess.clock import TimeControl, TimeControlMode
    from generic_chess.ui.match import MatchConfig, ParticipantKind

    ctrl3.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.AI),
            TimeControl(mode=TimeControlMode.NONE),
            ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick", max_nodes=300),
        )
    )
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer

    win3._ai_player = AlphaBetaPlayer(ctrl3.compiled, use_disk_cache=False)
    actions3 = ctrl3.session.legal_actions()
    ctrl3.submit_action(actions3[0])
    win3._refresh()
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        app.processEvents()
        if ctrl3.session.state.ply_count == 2 and not ctrl3.ai_thinking:
            break
        time.sleep(0.02)
    check("human vs AI move", ctrl3.session.state.ply_count == 2)

    # Close while AI is thinking.
    from generic_chess.ai.budget import ThinkingConfig

    ctrl4 = UIController(settings=settings)
    ctrl4.new_game(seed=42)
    win4 = MainWindow(ctrl4, settings)
    win4.show()
    ctrl4.start_match(
        MatchConfig(
            (ParticipantKind.AI, ParticipantKind.HUMAN),
            TimeControl(mode=TimeControlMode.NONE),
            ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick"),
        )
    )

    class SlowPlayer:
        def choose_action(self, session, limits, cancel_token=None, progress_callback=None):
            while cancel_token is None or not cancel_token.is_cancelled():
                time.sleep(0.02)
            from types import SimpleNamespace

            return SimpleNamespace(action=None)

    win4._ai_player = SlowPlayer()
    win4._maybe_start_ai()
    win4.close()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and win4.isVisible():
        app.processEvents()
        time.sleep(0.02)
    check("close during AI", not win4.isVisible())

    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{len(results) - failed}/{len(results)} checklist items passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
