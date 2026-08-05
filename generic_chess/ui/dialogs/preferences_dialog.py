"""Preferences dialog: edits a plain dict of values applied by the caller."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..settings import (
    KEY_AUTO_PROMOTE_UNIQUE,
    KEY_BOARD_ORIENTATION,
    KEY_ENABLE_PREVIEW,
    KEY_SHOW_COORDINATES,
    KEY_SHOW_HOVER,
    KEY_SHOW_LAST_MOVE,
    KEY_SHOW_LEGAL_MOVES,
    KEY_TEXTURE_RATIO,
)


class PreferencesDialog(QDialog):
    """Reads ``initial`` values, writes nothing; ``values()`` returns the result."""

    def __init__(self, initial: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._board_tab(initial), "Board")
        tabs.addTab(self._interaction_tab(initial), "Interaction")
        layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _board_tab(self, initial: dict) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self._texture_ratio = QDoubleSpinBox()
        self._texture_ratio.setRange(0.55, 0.95)
        self._texture_ratio.setSingleStep(0.05)
        self._texture_ratio.setValue(float(initial.get(KEY_TEXTURE_RATIO, 0.8)))
        form.addRow("Texture size (fraction of square)", self._texture_ratio)
        self._orientation = QComboBox()
        self._orientation.addItems(["White / Player 0 (先手) at bottom", "Black / Player 1 (後手) at bottom"])
        self._orientation.setCurrentIndex(int(initial.get(KEY_BOARD_ORIENTATION, 0)))
        form.addRow("Board orientation", self._orientation)
        self._coords = QCheckBox("Show coordinates")
        self._coords.setChecked(bool(initial.get(KEY_SHOW_COORDINATES, True)))
        form.addRow("", self._coords)
        self._legal = QCheckBox("Show legal moves")
        self._legal.setChecked(bool(initial.get(KEY_SHOW_LEGAL_MOVES, True)))
        form.addRow("", self._legal)
        self._lastmove = QCheckBox("Show last move")
        self._lastmove.setChecked(bool(initial.get(KEY_SHOW_LAST_MOVE, True)))
        form.addRow("", self._lastmove)
        self._hover = QCheckBox("Show hover highlight")
        self._hover.setChecked(bool(initial.get(KEY_SHOW_HOVER, True)))
        form.addRow("", self._hover)
        return page

    def _interaction_tab(self, initial: dict) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self._preview = QCheckBox("Allow enemy movement preview")
        self._preview.setChecked(bool(initial.get(KEY_ENABLE_PREVIEW, True)))
        form.addRow("", self._preview)
        self._auto_promo = QCheckBox("Auto-select a unique promotion")
        self._auto_promo.setChecked(bool(initial.get(KEY_AUTO_PROMOTE_UNIQUE, True)))
        form.addRow("", self._auto_promo)
        return page

    def values(self) -> dict[str, Any]:
        return {
            KEY_TEXTURE_RATIO: self._texture_ratio.value(),
            KEY_BOARD_ORIENTATION: self._orientation.currentIndex(),
            KEY_SHOW_COORDINATES: self._coords.isChecked(),
            KEY_SHOW_LEGAL_MOVES: self._legal.isChecked(),
            KEY_SHOW_LAST_MOVE: self._lastmove.isChecked(),
            KEY_SHOW_HOVER: self._hover.isChecked(),
            KEY_ENABLE_PREVIEW: self._preview.isChecked(),
            KEY_AUTO_PROMOTE_UNIQUE: self._auto_promo.isChecked(),
        }
