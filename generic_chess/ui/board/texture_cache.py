"""Cache for QSvgRenderer / QPixmap instances derived from the visual module."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from ...visual.texture_style import PieceTextureStyle
from ...visual.textures import generate_piece_texture
from ..theme import style_fingerprint


class TextureCache:
    """Renders piece textures once per (ruleset, type, owner, size, style)."""

    def __init__(self, style: PieceTextureStyle | None = None) -> None:
        self._renderers: dict[tuple, QSvgRenderer] = {}
        self._pixmaps: dict[tuple, QPixmap] = {}
        self._style = style or PieceTextureStyle()

    def _effective_style(self, style: PieceTextureStyle | None) -> PieceTextureStyle:
        return style if style is not None else self._style

    def _key(self, compiled, type_id: str, owner: int | None, size: int, style: PieceTextureStyle) -> tuple:
        return (compiled.ruleset_fingerprint, type_id, owner, size, style_fingerprint(style))

    def renderer(
        self,
        compiled,
        type_id: str,
        owner: int | None,
        size: int,
        style: PieceTextureStyle | None = None,
    ) -> QSvgRenderer:
        effective = self._effective_style(style)
        key = self._key(compiled, type_id, owner, size, effective)
        renderer = self._renderers.get(key)
        if renderer is None:
            svg = generate_piece_texture(
                compiled.types_by_id[type_id], owner=owner, size=size, style=effective
            ).svg
            renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
            self._renderers[key] = renderer
        return renderer

    def pixmap(
        self,
        compiled,
        type_id: str,
        owner: int | None,
        size: int,
        style: PieceTextureStyle | None = None,
    ) -> QPixmap:
        effective = self._effective_style(style)
        key = self._key(compiled, type_id, owner, size, effective)
        pixmap = self._pixmaps.get(key)
        if pixmap is None:
            renderer = self.renderer(compiled, type_id, owner, size, effective)
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter, QRectF(0, 0, size, size))
            painter.end()
            self._pixmaps[key] = pixmap
        return pixmap
