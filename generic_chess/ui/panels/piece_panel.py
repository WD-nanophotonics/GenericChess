"""Piece panel: texture, movement summary and structured atom table."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..board.texture_cache import TextureCache
from ..adapters import owner_label
from ..controller import UIController


class PiecePanel(QWidget):
    def __init__(self, controller: UIController, cache: TextureCache, parent=None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._cache = cache

        layout = QVBoxLayout(self)
        self._image = QLabel()
        self._image.setAlignment(Qt.AlignCenter)
        self._image.setFixedHeight(160)
        layout.addWidget(self._image)

        self._info = QLabel()
        self._info.setTextFormat(Qt.RichText)
        self._info.setWordWrap(True)
        layout.addWidget(self._info)

        layout.addWidget(QLabel("Movement summary"))
        self._summary = QLabel()
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        layout.addWidget(QLabel("Structured atoms"))
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Direction", "Kind", "Distance / Notes"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._table)
        layout.addStretch(1)

    def show_type(self, type_id: str) -> None:
        self._controller.browse_type(type_id)
        self.refresh()

    def refresh(self) -> None:
        info = self._controller.piece_info()
        if info is None:
            self._image.clear()
            self._info.setText("<i>Select a piece to inspect.</i>")
            self._summary.clear()
            self._table.setRowCount(0)
            return

        compiled = self._controller.compiled
        if compiled is not None and info.owner is not None:
            pixmap = self._cache.pixmap(compiled, info.type_id, info.owner, 128)
            self._image.setPixmap(pixmap)
        else:
            self._image.clear()

        owner_text = owner_label(info.owner)
        pos_text = str(info.square) if info.square is not None else "—"
        lines = [
            f"<b>Type:</b> {info.type_id} ({info.name})",
            f"<b>Owner:</b> {owner_text}",
            f"<b>Position:</b> {pos_text}",
            f"<b>Base type:</b> {info.base_type_id or '—'}",
            f"<b>Promoted:</b> {'Yes' if info.promoted else 'No'}",
        ]
        if info.legal_action_count is not None:
            lines.append(
                f"<b>Legal actions:</b> {info.legal_action_count} "
                f"(captures {info.capture_count or 0}, promotions {info.promotion_count or 0})"
            )
        if info.is_preview:
            lines.append(
                f"<b>Movement preview:</b> {info.preview_count or 0} candidate squares"
                "<br><i>Not currently actionable</i>"
            )
        elif not info.is_actionable:
            lines.append("<i>Not currently actionable</i>")
        self._info.setText("<br>".join(lines))
        self._summary.setText("<br>".join("• " + m for m in info.movement_lines) or "—")
        self._fill_table(info.movement_lines)

    def _fill_table(self, movement_lines: tuple[str, ...]) -> None:
        self._table.setRowCount(len(movement_lines))
        for row, line in enumerate(movement_lines):
            parts = line.split(", ")
            direction = parts[0] if parts else line
            rest = ", ".join(parts[1:]) if len(parts) > 1 else ""
            kind = "ray" if "ray" in line else "leap"
            self._table.setItem(row, 0, QTableWidgetItem(direction))
            self._table.setItem(row, 1, QTableWidgetItem(kind))
            self._table.setItem(row, 2, QTableWidgetItem(rest))
        self._table.resizeColumnsToContents()
