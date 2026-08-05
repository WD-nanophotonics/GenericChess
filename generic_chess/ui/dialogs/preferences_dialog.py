"""Preferences dialog persisted through the settings store."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QSpinBox,
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
    SettingsStore,
)


class PreferencesDialog(QDialog):
    def __init__(self, settings: SettingsStore, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self._settings = settings
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._board_tab(), "Board")
        tabs.addTab(self._interaction_tab(), "Interaction")
        layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _board_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self._texture_ratio = QDoubleSpinBox()
        self._texture_ratio.setRange(0.55, 0.95)
        self._texture_ratio.setSingleStep(0.05)
        self._texture_ratio.setValue(float(self._settings.get(KEY_TEXTURE_RATIO, 0.8)))
        form.addRow("Texture size (fraction of square)", self._texture_ratio)
        self._orientation = QComboBox()
        self._orientation.addItems(["White / Player 0 at bottom", "Black / Player 1 at bottom"])
        self._orientation.setCurrentIndex(int(self._settings.get(KEY_BOARD_ORIENTATION, 0)))
        form.addRow("Board orientation", self._orientation)
        self._coords = QCheckBox("Show coordinates")
        self._coords.setChecked(bool(self._settings.get(KEY_SHOW_COORDINATES, True)))
        form.addRow("", self._coords)
        self._legal = QCheckBox("Show legal moves")
        self._legal.setChecked(bool(self._settings.get(KEY_SHOW_LEGAL_MOVES, True)))
        form.addRow("", self._legal)
        self._lastmove = QCheckBox("Show last move")
        self._lastmove.setChecked(bool(self._settings.get(KEY_SHOW_LAST_MOVE, True)))
        form.addRow("", self._lastmove)
        self._hover = QCheckBox("Show hover highlight")
        self._hover.setChecked(bool(self._settings.get(KEY_SHOW_HOVER, True)))
        form.addRow("", self._hover)
        return page

    def _interaction_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self._preview = QCheckBox("Allow enemy movement preview")
        self._preview.setChecked(bool(self._settings.get(KEY_ENABLE_PREVIEW, True)))
        form.addRow("", self._preview)
        self._auto_promo = QCheckBox("Auto-select a unique promotion")
        self._auto_promo.setChecked(bool(self._settings.get(KEY_AUTO_PROMOTE_UNIQUE, True)))
        form.addRow("", self._auto_promo)
        return page

    def _save(self) -> None:
        self._settings.set(KEY_TEXTURE_RATIO, self._texture_ratio.value())
        self._settings.set(KEY_BOARD_ORIENTATION, self._orientation.currentIndex())
        self._settings.set(KEY_SHOW_COORDINATES, self._coords.isChecked())
        self._settings.set(KEY_SHOW_LEGAL_MOVES, self._legal.isChecked())
        self._settings.set(KEY_SHOW_LAST_MOVE, self._lastmove.isChecked())
        self._settings.set(KEY_SHOW_HOVER, self._hover.isChecked())
        self._settings.set(KEY_ENABLE_PREVIEW, self._preview.isChecked())
        self._settings.set(KEY_AUTO_PROMOTE_UNIQUE, self._auto_promo.isChecked())
        self.accept()
