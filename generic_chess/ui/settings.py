"""Persistent UI settings (QSettings-backed, with a storable interface)."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSettings


class SettingsStore:
    """Duck-typed settings interface so the controller stays Qt-free."""

    def get(self, key: str, default: Any = None) -> Any:
        raise NotImplementedError

    def set(self, key: str, value: Any) -> None:
        raise NotImplementedError

    def contains(self, key: str) -> bool:
        raise NotImplementedError


class QtSettingsStore(SettingsStore):
    def __init__(self, organization: str = "GenericChess", application: str = "GenericChess") -> None:
        self._q = QSettings(organization, application)

    def get(self, key: str, default: Any = None) -> Any:
        return self._q.value(key, default)

    def set(self, key: str, value: Any) -> None:
        self._q.setValue(key, value)

    def contains(self, key: str) -> bool:
        return self._q.contains(key)


class DictSettingsStore(SettingsStore):
    """In-memory store for tests and headless runs."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def contains(self, key: str) -> bool:
        return key in self._data


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
KEY_RECENT_RULESET_DIR = "files/recent_ruleset_dir"
KEY_RECENT_RECORD_DIR = "files/recent_record_dir"
