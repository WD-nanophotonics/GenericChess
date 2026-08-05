"""BoardScene: layered squares, highlights, coordinates and SVG piece items."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen, QTransform
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)

from ...core.coordinates import Square
from ...ui.view_models import BoardViewModel
from ...ui.theme import Theme
from .texture_cache import TextureCache


CELL = 100.0


@dataclass(frozen=True)
class BoardRenderConfig:
    theme: Theme
    texture_ratio: float = 0.8
    show_coordinates: bool = True
    show_legal_moves: bool = True
    show_last_move: bool = True


class BoardScene(QGraphicsScene):
    def __init__(self, cache: TextureCache, parent=None) -> None:
        super().__init__(parent)
        self._cache = cache
        self._config: BoardRenderConfig | None = None
        self._compiled = None
        self._orientation = 0
        self._n = 8
        self._hover_item: QGraphicsRectItem | None = None

    # ------------------------------------------------------------------ mapping

    def logical_to_scene(self, square: Square) -> tuple[float, float]:
        file, rank = square.file, square.rank
        if self._orientation == 1:
            file = self._n - 1 - file
            rank = self._n - 1 - rank
        return (file * CELL, (self._n - 1 - rank) * CELL)

    def scene_to_logical(self, x: float, y: float) -> Square | None:
        if self._n <= 0:
            return None
        file = int(x // CELL)
        view_rank = int(y // CELL)
        if not (0 <= file < self._n and 0 <= view_rank < self._n):
            return None
        rank = self._n - 1 - view_rank
        if self._orientation == 1:
            file = self._n - 1 - file
            rank = self._n - 1 - rank
        return Square(file, rank)

    # ------------------------------------------------------------------ build

    def build(
        self,
        model: BoardViewModel,
        compiled,
        config: BoardRenderConfig,
        orientation: int,
    ) -> None:
        self.clear()
        self._config = config
        self._compiled = compiled
        self._orientation = orientation
        self._n = model.board_size
        self._hover_item = None
        theme = config.theme

        last_from = {s.square for s in model.squares if s.is_last_move_from}
        last_to = {s.square for s in model.squares if s.is_last_move_to}

        for sv in model.squares:
            x, y = self.logical_to_scene(sv.square)
            rect = QRectF(x, y, CELL, CELL)
            color = theme.light_square if (sv.square.file + sv.square.rank) % 2 == 0 else theme.dark_square
            square_item = QGraphicsRectItem(rect)
            square_item.setBrush(QBrush(QColor(color)))
            square_item.setPen(QPen(Qt.NoPen))
            square_item.setZValue(0)
            self.addItem(square_item)

            if config.show_last_move and sv.square in last_from:
                self._add_rect(rect, theme.last_move_from, 150, 1)
            if config.show_last_move and sv.square in last_to:
                self._add_rect(rect, theme.last_move_to, 170, 1)
            if sv.is_hovered:
                self._add_rect(rect, theme.hover_fill, int(255 * theme.hover_opacity), 2)
            if sv.is_preview:
                self._add_rect(rect, theme.preview_fill, int(255 * theme.preview_opacity), 3)
            if sv.is_legal_move and config.show_legal_moves:
                self._add_dot(rect, theme.legal_move_dot, 4)
            if sv.is_legal_capture and config.show_legal_moves:
                self._add_ring(rect, theme.capture_ring, 5)
            if sv.is_selected:
                self._add_border(rect, theme.selected_border, 6)
            if sv.is_check_anchor:
                self._add_border(rect, theme.threat_border, 7)

        # Pieces on top of highlights.
        for sv in model.squares:
            if sv.piece is None:
                continue
            self._add_piece(sv, config)

        if config.show_coordinates:
            self._add_coordinates(model.board_size)
        self.setSceneRect(0, 0, self._n * CELL, self._n * CELL)

    def _add_rect(self, rect: QRectF, color: str, alpha: int, z: int) -> None:
        item = QGraphicsRectItem(rect)
        c = QColor(color)
        c.setAlpha(alpha)
        item.setBrush(QBrush(c))
        item.setPen(QPen(Qt.NoPen))
        item.setZValue(z)
        self.addItem(item)

    def _add_dot(self, rect: QRectF, color: str, z: int) -> None:
        r = CELL * 0.13
        item = QGraphicsEllipseItem(rect.center().x() - r, rect.center().y() - r, 2 * r, 2 * r)
        item.setBrush(QBrush(QColor(color)))
        item.setPen(QPen(Qt.NoPen))
        item.setZValue(z)
        self.addItem(item)

    def _add_ring(self, rect: QRectF, color: str, z: int) -> None:
        margin = CELL * 0.08
        item = QGraphicsEllipseItem(
            rect.x() + margin,
            rect.y() + margin,
            CELL - 2 * margin,
            CELL - 2 * margin,
        )
        pen = QPen(QColor(color))
        pen.setWidthF(CELL * 0.06)
        item.setPen(pen)
        item.setBrush(QBrush(Qt.NoBrush))
        item.setZValue(z)
        self.addItem(item)

    def _add_border(self, rect: QRectF, color: str, z: int) -> None:
        item = QGraphicsRectItem(rect.adjusted(2, 2, -2, -2))
        pen = QPen(QColor(color))
        pen.setWidthF(CELL * 0.05)
        item.setPen(pen)
        item.setBrush(QBrush(Qt.NoBrush))
        item.setZValue(z)
        self.addItem(item)

    def _add_piece(self, sv, config: BoardRenderConfig) -> None:
        if self._compiled is None or sv.piece is None:
            return
        size = int(CELL * config.texture_ratio)
        renderer = self._cache.renderer(
            self._compiled, sv.piece.current_type_id, sv.piece.owner, size
        )
        item = QGraphicsSvgItem()
        item.setSharedRenderer(renderer)
        x, y = self.logical_to_scene(sv.square)
        default = renderer.defaultSize()
        scale_x = size / max(1, default.width())
        scale_y = size / max(1, default.height())
        item.setTransform(QTransform().scale(scale_x, scale_y))
        offset_x = x + (CELL - size) / 2
        offset_y = y + (CELL - size) / 2
        item.setPos(offset_x, offset_y)
        item.setZValue(10)
        self.addItem(item)

    def _add_coordinates(self, n: int) -> None:
        pen = QPen(QColor(self._config.theme.coordinate_text))
        for file in range(n):
            x, y = self.logical_to_scene(Square(file, 0))
            label = chr(ord("a") + file) if file < 26 else str(file)
            text = QGraphicsSimpleTextItem(label)
            text.setBrush(QBrush(pen.color()))
            text.setPos(x + CELL * 0.75, y + CELL * 0.78)
            text.setZValue(8)
            self.addItem(text)
        for rank in range(n):
            x, y = self.logical_to_scene(Square(0, rank))
            text = QGraphicsSimpleTextItem(str(rank + 1))
            text.setBrush(QBrush(pen.color()))
            text.setPos(x + CELL * 0.04, y + CELL * 0.03)
            text.setZValue(8)
            self.addItem(text)

    def set_hover(self, square: Square | None) -> None:
        if self._hover_item is not None:
            self.removeItem(self._hover_item)
            self._hover_item = None
        if square is None or self._config is None:
            return
        x, y = self.logical_to_scene(square)
        c = QColor(self._config.theme.hover_fill)
        c.setAlpha(int(255 * self._config.theme.hover_opacity))
        item = QGraphicsRectItem(QRectF(x, y, CELL, CELL))
        item.setBrush(QBrush(c))
        item.setPen(QPen(Qt.NoPen))
        item.setZValue(2)
        self.addItem(item)
        self._hover_item = item
