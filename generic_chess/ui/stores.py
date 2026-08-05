"""Qt-free settings storage interface (pure Python, UI-agnostic)."""

from __future__ import annotations

from typing import Any


class SettingsStore:
    """Duck-typed settings interface so the controller stays Qt-free."""

    def get(self, key: str, default: Any = None) -> Any:
        raise NotImplementedError

    def set(self, key: str, value: Any) -> None:
        raise NotImplementedError

    def contains(self, key: str) -> bool:
        raise NotImplementedError


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
