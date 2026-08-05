"""Rules panel: RuleSet overview and a browsable piece-type list."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..board.texture_cache import TextureCache
from ..controller import UIController


class RulesPanel(QWidget):
    def __init__(
        self,
        controller: UIController,
        cache: TextureCache,
        inspect_type_cb: Callable[[str], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._cache = cache
        self._inspect_type = inspect_type_cb

        layout = QVBoxLayout(self)
        self._info = QLabel()
        self._info.setTextFormat(Qt.RichText)
        self._info.setWordWrap(True)
        layout.addWidget(self._info)
        layout.addWidget(QLabel("Piece types (click to inspect)"))
        self._types = QListWidget()
        self._types.itemDoubleClicked.connect(
            lambda item: self._inspect_type(item.data(Qt.UserRole))
        )
        layout.addWidget(self._types)

    def refresh(self) -> None:
        info = self._controller.rules_info()
        compiled = self._controller.compiled
        self._types.clear()
        if info is None or compiled is None:
            self._info.setText("<i>No ruleset loaded.</i>")
            return
        self._info.setText(
            f"<b>Board:</b> {info.board_size} x {info.board_size}<br>"
            f"<b>Seed:</b> {info.seed if info.seed is not None else '—'}<br>"
            f"<b>Fingerprint:</b> {info.fingerprint}<br>"
            f"<b>Piece types:</b> {info.piece_type_count}<br>"
            f"<b>Initial entities:</b> {info.initial_entity_count}<br>"
            f"<b>Promotions:</b> {', '.join(info.promotion_relations) or 'none'}<br>"
            f"<b>Drop:</b> {info.drop_summary}<br>"
            f"<b>Terminal:</b> {info.terminal_summary}"
        )
        for type_id, name, _lines in info.piece_types:
            pixmap = self._cache.pixmap(compiled, type_id, 0, 32)
            item = QListWidgetItem(QIcon(pixmap), f"{type_id} — {name}")
            item.setData(Qt.UserRole, type_id)
            self._types.addItem(item)
