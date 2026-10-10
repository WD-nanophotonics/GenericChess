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

# Preserve the desktop settings import interface.
from .settings_keys import *  # noqa: F401,F403
