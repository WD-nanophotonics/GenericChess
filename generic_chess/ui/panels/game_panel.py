"""Game panel: status, hands and game-level actions."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..adapters import owner_label
from ..controller import UIController


class GamePanel(QWidget):
    def __init__(
        self,
        controller: UIController,
        new_game_cb: Callable[[], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        layout = QVBoxLayout(self)
        self._status = QLabel()
        self._status.setTextFormat(Qt.RichText)
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

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
            return
        side = owner_label(info.side_to_move)
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
