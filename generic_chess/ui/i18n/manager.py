"""Qt-free localization manager with live language switching."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

SUPPORTED_LANGUAGES = ("en", "zh_CN", "ja_JP")


def _system_language() -> str:
    raw = (
        os.environ.get("LC_ALL", "")
        or os.environ.get("LANG", "")
        or os.environ.get("LANGUAGE", "")
    )
    if raw.lower().startswith("zh"):
        return "zh_CN"
    if raw.lower().startswith("ja"):
        return "ja_JP"
    return "en"


class LocalizationManager:
    """Loads flat JSON string tables and formats ``{placeholder}`` values."""

    def __init__(self, language: str | None = None) -> None:
        self._listeners: list[Callable[[str], None]] = []
        self._language = self._resolve(language)
        self._tables: dict[str, dict[str, str]] = {}
        self._load()

    def _resolve(self, language: str | None) -> str:
        if language in SUPPORTED_LANGUAGES:
            return language
        return _system_language()

    def _load(self) -> None:
        base = Path(__file__).resolve().parent
        for lang in ("en", self._language):
            table = self._read(base / f"{lang}.json")
            self._tables.setdefault(lang, table)
        self._active = dict(self._tables.get("en", {}))
        self._active.update(self._tables.get(self._language, {}))

    def _read(self, path: Path) -> dict[str, str]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    @property
    def language(self) -> str:
        return self._language

    def subscribe(self, callback: Callable[[str], None]) -> None:
        self._listeners.append(callback)

    def set_language(self, language: str) -> None:
        language = self._resolve(language)
        if language == self._language:
            return
        self._language = language
        self._load()
        for listener in self._listeners:
            listener(self._language)

    def text(self, key: str, **values: object) -> str:
        template = self._active.get(key, key)
        if not values:
            return template
        try:
            return template.format(**values)
        except (KeyError, IndexError, ValueError):
            return template

    def t(self, key: str, **values: object) -> str:
        return self.text(key, **values)

    def has(self, key: str) -> bool:
        return key in self._active
