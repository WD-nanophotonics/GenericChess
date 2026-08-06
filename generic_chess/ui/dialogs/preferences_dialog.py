"""Preferences dialog: General (language), Board & Interaction, Advanced."""

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

from ..i18n.manager import LocalizationManager, SUPPORTED_LANGUAGES
from ..settings import (
    KEY_AUTO_PROMOTE_UNIQUE,
    KEY_BOARD_ORIENTATION,
    KEY_ENABLE_PREVIEW,
    KEY_LANGUAGE,
    KEY_SHOW_COORDINATES,
    KEY_SHOW_DEV_STATUS,
    KEY_SHOW_HOVER,
    KEY_SHOW_LAST_MOVE,
    KEY_SHOW_LEGAL_MOVES,
    KEY_TEXTURE_RATIO,
    KEY_ZOOM_MODE,
)

LANGUAGE_NAMES = {
    "zh_CN": "简体中文",
    "ja_JP": "日本語",
    "en": "English",
}


class PreferencesDialog(QDialog):
    """Reads ``initial`` values, writes nothing; ``values()`` returns the result."""

    def __init__(self, initial: dict[str, Any], tr: LocalizationManager, parent=None) -> None:
        super().__init__(parent)
        self._tr = tr
        self.setWindowTitle(tr.text("prefs.title"))
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._general_tab(initial), tr.text("prefs.general"))
        tabs.addTab(self._board_tab(initial), tr.text("prefs.board_interaction"))
        tabs.addTab(self._advanced_tab(initial), tr.text("prefs.advanced"))
        layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _general_tab(self, initial: dict) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self._language = QComboBox()
        current = str(initial.get(KEY_LANGUAGE, "en"))
        for index, lang in enumerate(SUPPORTED_LANGUAGES):
            self._language.addItem(LANGUAGE_NAMES[lang], lang)
            if lang == current:
                self._language.setCurrentIndex(index)
        form.addRow(self._tr.text("prefs.language"), self._language)
        return page

    def _board_tab(self, initial: dict) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self._texture_ratio = QDoubleSpinBox()
        self._texture_ratio.setRange(0.55, 0.95)
        self._texture_ratio.setSingleStep(0.05)
        self._texture_ratio.setValue(float(initial.get(KEY_TEXTURE_RATIO, 0.8)))
        form.addRow(self._tr.text("prefs.texture_size"), self._texture_ratio)
        self._orientation = QComboBox()
        self._orientation.addItems(
            [
                self._tr.text("player.white") + "（" + self._tr.text("player.first") + "）",
                self._tr.text("player.black") + "（" + self._tr.text("player.second") + "）",
            ]
        )
        self._orientation.setCurrentIndex(int(initial.get(KEY_BOARD_ORIENTATION, 0)))
        form.addRow(self._tr.text("menu.flip"), self._orientation)
        self._coords = QCheckBox()
        self._coords.setChecked(bool(initial.get(KEY_SHOW_COORDINATES, True)))
        form.addRow("", self._coords)
        self._legal = QCheckBox()
        self._legal.setChecked(bool(initial.get(KEY_SHOW_LEGAL_MOVES, True)))
        form.addRow("", self._legal)
        self._lastmove = QCheckBox()
        self._lastmove.setChecked(bool(initial.get(KEY_SHOW_LAST_MOVE, True)))
        form.addRow("", self._lastmove)
        self._hover = QCheckBox()
        self._hover.setChecked(bool(initial.get(KEY_SHOW_HOVER, True)))
        form.addRow("", self._hover)
        self._preview = QCheckBox()
        self._preview.setChecked(bool(initial.get(KEY_ENABLE_PREVIEW, True)))
        form.addRow("", self._preview)
        self._auto_promo = QCheckBox()
        self._auto_promo.setChecked(bool(initial.get(KEY_AUTO_PROMOTE_UNIQUE, True)))
        form.addRow("", self._auto_promo)
        self._coords.setText(self._tr.text("prefs.coordinates"))
        self._legal.setText(self._tr.text("prefs.legal_moves"))
        self._lastmove.setText(self._tr.text("prefs.last_move"))
        self._hover.setText(self._tr.text("prefs.hover"))
        self._preview.setText(self._tr.text("prefs.preview"))
        self._auto_promo.setText(self._tr.text("prefs.auto_promote"))
        return page

    def _advanced_tab(self, initial: dict) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self._zoom_mode = QCheckBox()
        self._zoom_mode.setChecked(bool(initial.get(KEY_ZOOM_MODE, False)))
        self._zoom_mode.setText(self._tr.text("prefs.zoom_mode_default"))
        form.addRow("", self._zoom_mode)
        self._dev_status = QCheckBox()
        self._dev_status.setChecked(bool(initial.get(KEY_SHOW_DEV_STATUS, False)))
        self._dev_status.setText(self._tr.text("prefs.dev_status"))
        form.addRow("", self._dev_status)
        return page

    def values(self) -> dict[str, Any]:
        return {
            KEY_TEXTURE_RATIO: self._texture_ratio.value(),
            KEY_BOARD_ORIENTATION: self._orientation.currentIndex(),
            KEY_LANGUAGE: str(self._language.currentData()),
            KEY_SHOW_COORDINATES: self._coords.isChecked(),
            KEY_SHOW_LEGAL_MOVES: self._legal.isChecked(),
            KEY_SHOW_LAST_MOVE: self._lastmove.isChecked(),
            KEY_SHOW_HOVER: self._hover.isChecked(),
            KEY_ENABLE_PREVIEW: self._preview.isChecked(),
            KEY_AUTO_PROMOTE_UNIQUE: self._auto_promo.isChecked(),
            KEY_ZOOM_MODE: self._zoom_mode.isChecked(),
            KEY_SHOW_DEV_STATUS: self._dev_status.isChecked(),
        }
