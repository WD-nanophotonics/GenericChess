"""BoardView: QGraphicsView wiring mouse input to the controller.

Board sizing is fully controlled: the view keeps a base fit scale computed
only from the viewport size and the board dimensions, plus an explicit user
zoom that is only editable in zoom mode.  Position refreshes never touch the
transform, so moves/selections/clock updates cannot resize the board.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPainter, QTransform
from PySide6.QtWidgets import QGraphicsView

from ...core.coordinates import Square
from ..controller import UIController
from .scene import CELL, BoardScene


MIN_ZOOM = 0.5
MAX_ZOOM = 8.0
ZOOM_STEP = 1.15


class BoardView(QGraphicsView):
    def __init__(self, controller: UIController, scene: BoardScene, parent=None) -> None:
        super().__init__(scene, parent)
        self._controller = controller
        self._scene = scene
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self._hover_enabled = True
        self._board_size: int | None = None
        self._base_scale = 1.0
        self._user_zoom = 1.0
        self._zoom_mode = False
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    # The scene rect is 800x800 but the viewport must be shrinkable; otherwise
    # the window cannot go below the scene size on small screens.
    def sizeHint(self) -> QSize:
        return QSize(320, 320)

    def minimumSizeHint(self) -> QSize:
        return QSize(240, 240)

    # ------------------------------------------------------------------ sizing

    def set_board_size(self, size: int | None) -> None:
        """Recompute the fit transform only when the board size changes."""
        if size != self._board_size:
            self._board_size = size
            self._recompute_fit_transform()

    def refresh_position(self) -> None:
        """Hook called after a scene rebuild; intentionally does not touch the
        transform so ordinary refreshes never resize the board."""

    def fit_board(self) -> None:
        """Reset user zoom and fit the board to the current viewport."""
        self._user_zoom = 1.0
        self._recompute_fit_transform()

    def reset_zoom(self) -> None:
        self.fit_board()

    def set_zoom_mode(self, enabled: bool) -> None:
        self._zoom_mode = bool(enabled)
        if not self._zoom_mode:
            self._user_zoom = 1.0
        self._recompute_fit_transform()

    def zoom_mode_enabled(self) -> bool:
        return self._zoom_mode

    def zoom_in(self) -> None:
        if not self._zoom_mode:
            return
        self._user_zoom = min(MAX_ZOOM, self._user_zoom * ZOOM_STEP)
        self._apply_transform()

    def zoom_out(self) -> None:
        if not self._zoom_mode:
            return
        self._user_zoom = max(MIN_ZOOM, self._user_zoom / ZOOM_STEP)
        self._apply_transform()

    def user_zoom(self) -> float:
        return self._user_zoom

    def _recompute_fit_transform(self) -> None:
        if self._board_size is None:
            return
        viewport = self.viewport().size()
        scene_width = self._board_size * CELL
        if viewport.width() <= 0 or viewport.height() <= 0 or scene_width <= 0:
            return
        self._base_scale = min(
            viewport.width() / scene_width, viewport.height() / scene_width
        )
        self._apply_transform()

    def _apply_transform(self) -> None:
        transform = QTransform()
        scale = self._base_scale * self._user_zoom
        transform.scale(scale, scale)
        self.setTransform(transform)
        if self._zoom_mode and self._user_zoom > 1.0:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def set_hover_enabled(self, enabled: bool) -> None:
        self._hover_enabled = enabled
        if not enabled:
            self._controller.set_hover(None)
            self._scene.set_hover(None)

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
        if self._hover_enabled:
            square = self._logical_square(event)
            self._controller.set_hover(square)
            self._scene.set_hover(square)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._controller.set_hover(None)
        self._scene.set_hover(None)
        super().leaveEvent(event)

    def wheelEvent(self, event) -> None:
        if not self._zoom_mode:
            event.ignore()
            return
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._recompute_fit_transform()
