"""Game panel: status, hands and game-level actions."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..board.texture_cache import TextureCache
from ..controller import UIController


class GamePanel(QWidget):
    def __init__(
        self,
        controller: UIController,
        cache: TextureCache,
        new_game_cb: Callable[[], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._cache = cache
        layout = QVBoxLayout(self)
        self._status = QLabel()
        self._status.setTextFormat(Qt.RichText)
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._hand0 = QLabel()
        self._hand0.setWordWrap(True)
        self._hand1 = QLabel()
        self._hand1.setWordWrap(True)
        layout.addWidget(QLabel("Player 0 hand (click to drop)"))
        layout.addWidget(self._hand0)
        layout.addWidget(QLabel("Player 1 hand"))
        layout.addWidget(self._hand1)

        buttons = QHBoxLayout()
        for label, cb in (
            ("New", new_game_cb),
            ("Restart", controller.restart),
            ("Resign", controller.resign),
            ("Flip", controller.flip_board),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(cb)
            buttons.addWidget(btn)
        layout.addLayout(buttons)
        layout.addStretch(1)

    def refresh(self) -> None:
        info = self._controller.game_info()
        compiled = self._controller.compiled
        if info is None or compiled is None:
            self._status.setText("<i>No game loaded.</i>")
            self._hand0.clear()
            self._hand1.clear()
            return
        side = "White / Player 0" if info.side_to_move == 0 else "Black / Player 1"
        state = (
            f"<b>To move:</b> {side}<br>"
            f"<b>Ply:</b> {info.ply_count}<br>"
            f"<b>Result:</b> {info.result}<br>"
            f"<b>RuleSet seed:</b> {info.seed if info.seed is not None else '—'}<br>"
            f"<b>Fingerprint:</b> {info.fingerprint}<br>"
            f"<b>RuleSet file:</b> {info.ruleset_path or '—'}<br>"
            f"<b>Record file:</b> {info.record_path or '—'}"
        )
        self._status.setText(state)
        self._fill_hand(self._hand0, info.hands[0], 0, compiled)
        self._fill_hand(self._hand1, info.hands[1], 1, compiled)

    def _fill_hand(self, label: QLabel, entries, owner: int, compiled) -> None:
        row = QWidget()
        box = QHBoxLayout(row)
        box.setContentsMargins(0, 0, 0, 0)
        session = self._controller.session
        side_to_move = (
            session.state.position.side_to_move
            if session is not None and session.result.status.value == "ongoing"
            else None
        )
        clickable = owner == side_to_move
        for entry in entries:
            pixmap = self._cache.pixmap(compiled, entry.type_id, owner, 40)
            btn = QToolButton()
            btn.setIcon(QIcon(pixmap))
            btn.setIconSize(pixmap.size())
            btn.setToolTip(f"{entry.type_id} x{entry.count}")
            btn.setEnabled(clickable)
            if clickable:
                btn.clicked.connect(lambda _=False, tid=entry.type_id: self._controller.hand_piece_clicked(tid))
            box.addWidget(btn)
            box.addWidget(QLabel(f"x{entry.count}"))
        box.addStretch(1)
        label.setLayout(box)
