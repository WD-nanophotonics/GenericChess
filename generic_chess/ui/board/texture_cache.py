"""Cache for QSvgRenderer / QPixmap instances derived from the visual module."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from ...visual.textures import generate_piece_texture


class TextureCache:
    """Renders piece textures once per (ruleset, type, owner, size)."""

    def __init__(self) -> None:
        self._renderers: dict[tuple, QSvgRenderer] = {}
        self._pixmaps: dict[tuple, QPixmap] = {}

    def _key(self, compiled, type_id: str, owner: int | None, size: int) -> tuple:
        return (compiled.ruleset_fingerprint, type_id, owner, size)

    def renderer(self, compiled, type_id: str, owner: int | None, size: int) -> QSvgRenderer:
        key = self._key(compiled, type_id, owner, size)
        renderer = self._renderers.get(key)
        if renderer is None:
            svg = generate_piece_texture(
                compiled.types_by_id[type_id], owner=owner, size=size
            ).svg
            renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
            self._renderers[key] = renderer
        return renderer

    def pixmap(self, compiled, type_id: str, owner: int | None, size: int) -> QPixmap:
        key = self._key(compiled, type_id, owner, size)
        pixmap = self._pixmaps.get(key)
        if pixmap is None:
            renderer = self.renderer(compiled, type_id, owner, size)
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter, QRectF(0, 0, size, size))
            painter.end()
            self._pixmaps[key] = pixmap
        return pixmap
