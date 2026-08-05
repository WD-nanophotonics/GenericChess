"""History panel: move list, latest-move highlight, ply preview."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..controller import UIController


class HistoryPanel(QWidget):
    def __init__(self, controller: UIController, parent=None) -> None:
        super().__init__(parent)
        self._controller = controller
        layout = QVBoxLayout(self)
        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._list)
        self._return_btn = QPushButton("Return to Current Position")
        self._return_btn.clicked.connect(controller.return_to_current)
        layout.addWidget(self._return_btn)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        ply = item.data(Qt.UserRole)
        if ply is not None:
            self._controller.display_ply(ply)

    def refresh(self) -> None:
        self._list.clear()
        entries = self._controller.history_entries()
        displayed = self._controller.interaction.displayed_ply
        for entry in entries:
            item = QListWidgetItem(f"{entry.ply:>3}. P{entry.player}: {entry.label}")
            item.setData(Qt.UserRole, entry.ply)
            self._list.addItem(item)
        if self._list.count():
            if displayed is not None and 1 <= displayed <= self._list.count():
                item = self._list.item(displayed - 1)
                item.setSelected(True)
                self._list.scrollToItem(item)
            else:
                last_item = self._list.item(self._list.count() - 1)
                last_item.setSelected(True)
                self._list.scrollToBottom()
        self._return_btn.setEnabled(displayed is not None)
