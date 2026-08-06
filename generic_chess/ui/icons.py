"""Theme-aware painted toolbar icons (no external icon assets)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)

from .theme import Theme

_SIZE = 24


def toolbar_icon(kind: str, theme: Theme) -> QIcon:
    """Return a distinct semantic icon for a high-frequency toolbar action."""
    pixmap = QPixmap(_SIZE, _SIZE)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    color = QColor(theme.toolbar_icon if theme.dark_mode else "#3a4a5a")
    accent = QColor(theme.selection_accent if theme.dark_mode else "#1a6fd1")
    pen = QPen(color, 1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    if kind == "new":
        painter.drawRoundedRect(QRectF(4, 4, 12, 15), 2, 2)
        painter.drawLine(QPointF(10, 7), QPointF(10, 16))
        painter.drawLine(QPointF(6, 11.5), QPointF(14, 11.5))
    elif kind == "open":
        painter.drawRoundedRect(QRectF(4, 8, 16, 11), 2, 2)
        painter.drawRoundedRect(QRectF(8, 5, 6, 4), 1, 1)
    elif kind == "save":
        painter.drawRoundedRect(QRectF(4, 4, 16, 16), 2, 2)
        painter.drawRoundedRect(QRectF(8, 6, 8, 4), 1, 1)
        painter.drawRoundedRect(QRectF(8, 14, 8, 6), 1, 1)
    elif kind == "undo":
        _draw_arc_arrow(painter, forward=False)
    elif kind == "redo":
        _draw_arc_arrow(painter, forward=True)
    elif kind == "flip":
        painter.drawLine(QPointF(5, 9), QPointF(19, 9))
        _arrow_head(painter, QPointF(19, 9), QPointF(1, 0), color)
        painter.drawLine(QPointF(19, 15), QPointF(5, 15))
        _arrow_head(painter, QPointF(5, 15), QPointF(-1, 0), color)
    painter.end()
    return QIcon(pixmap)


def _draw_arc_arrow(painter: QPainter, *, forward: bool) -> None:
    color = painter.pen().color()
    if forward:
        points = (QPointF(8, 7), QPointF(14, 7), QPointF(17, 10), QPointF(17, 15))
        tip = QPointF(17, 15)
        direction = QPointF(1, 0)
    else:
        points = (QPointF(16, 7), QPointF(10, 7), QPointF(7, 10), QPointF(7, 15))
        tip = QPointF(7, 15)
        direction = QPointF(-1, 0)
    painter.drawPolyline(points)
    _arrow_head(painter, tip, direction, color)


def _arrow_head(painter: QPainter, tip: QPointF, direction: QPointF, color: QColor) -> None:
    length = 5.0
    ux, uy = direction.x(), direction.y()
    base = QPointF(tip.x() - ux * length, tip.y() - uy * length)
    left = QPointF(base.x() + uy * 2.2, base.y() - ux * 2.2)
    right = QPointF(base.x() - uy * 2.2, base.y() + ux * 2.2)
    painter.setBrush(color)
    painter.setPen(QPen(color, 1))
    painter.drawPolygon(QPolygonF([tip, left, right]))
