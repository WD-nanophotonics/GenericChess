"""Persistent UI settings keys and the Qt-backed store.

The pure Python settings interface lives in :mod:`generic_chess.ui.stores`
so the Controller stays Qt-free; this module only adds the QSettings adapter.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSettings

from .stores import SettingsStore


class QtSettingsStore(SettingsStore):
    def __init__(self, organization: str = "GenericChess", application: str = "GenericChess") -> None:
        self._q = QSettings(organization, application)

    def get(self, key: str, default: Any = None) -> Any:
        return self._q.value(key, default)

    def set(self, key: str, value: Any) -> None:
        self._q.setValue(key, value)

    def contains(self, key: str) -> bool:
        return self._q.contains(key)
KEY_WINDOW_GEOMETRY = "window/geometry"
KEY_SPLITTER_STATE = "window/splitter"
KEY_SHOW_TOOLBAR = "window/toolbar"
KEY_SHOW_SIDEBAR = "window/sidebar"
KEY_BOARD_ORIENTATION = "board/orientation"
KEY_THEME = "board/theme"
KEY_TEXTURE_RATIO = "board/texture_ratio"
KEY_SHOW_COORDINATES = "board/coordinates"
KEY_SHOW_LEGAL_MOVES = "board/legal_moves"
KEY_SHOW_LAST_MOVE = "board/last_move"
KEY_SHOW_HOVER = "board/hover"
KEY_ENABLE_PREVIEW = "interaction/preview"
KEY_AUTO_PROMOTE_UNIQUE = "interaction/auto_promote_unique"
KEY_LANGUAGE = "ui/language"
KEY_ZOOM_MODE = "board/zoom_mode"
# Descriptive alias retained for callers that want to express the product
# meaning.  KEY_ZOOM_MODE remains the persisted compatibility key.
KEY_ENABLE_WHEEL_ZOOM = KEY_ZOOM_MODE
KEY_SHOW_DEV_STATUS = "ui/dev_status"
KEY_RECENT_RULESET_DIR = "files/recent_ruleset_dir"
KEY_RECENT_RECORD_DIR = "files/recent_record_dir"
