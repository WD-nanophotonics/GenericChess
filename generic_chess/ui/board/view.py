"""BoardView: QGraphicsView wiring mouse input to the controller."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsView

from ...core.coordinates import Square
from ..controller import UIController
from .scene import BoardScene


class BoardView(QGraphicsView):
    def __init__(self, controller: UIController, scene: BoardScene, parent=None) -> None:
        super().__init__(scene, parent)
        self._controller = controller
        self._scene = scene
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setFocusPolicy(Qt.StrongFocus)

    def _logical_square(self, event) -> Square | None:
        pos = self.mapToScene(event.position().toPoint())
        return self._scene.scene_to_logical(pos.x(), pos.y())

    def mousePressEvent(self, event) -> None:
        square = self._logical_square(event)
        if square is None:
            super().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton:
            self._controller.square_clicked(square)
        elif event.button() == Qt.RightButton:
            self._controller.cancel()
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        square = self._logical_square(event)
        self._controller.set_hover(square)
        self._scene.set_hover(square)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._controller.set_hover(None)
        self._scene.set_hover(None)
        super().leaveEvent(event)

    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)
        event.accept()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fit_board()

    def fit_board(self) -> None:
        if self.scene() is not None and not self.scene().itemsBoundingRect().isEmpty():
            self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)

    def reset_zoom(self) -> None:
        self.resetTransform()
        self.fit_board()
