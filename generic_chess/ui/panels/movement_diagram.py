"""QPainter-based canonical movement diagram for the rules explorer.

The diagram shows one piece type's movement atoms from a center cell in the
canonical owner-0 frame (forward = up).  It never follows the board
orientation or the owner of the currently selected concrete piece, so the
same type always renders identically.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from ...core.movement import LeapAtom, RayAtom
from ..board.texture_cache import TextureCache
from ..i18n.manager import LocalizationManager
from ..theme import Theme

MIN_VIEW_RADIUS = 2  # guarantees the minimum 5x5 view
RAY_VIEW_RADIUS = 3  # unlimited rays get at least a 7x7 view
MAX_VIEW_RADIUS = 5  # at most an 11x11 full-size view; farther gets edge markers


@dataclass(frozen=True)
class RayInfo:
    """One ray atom rendered inside the view.

    ``path`` holds the ordered offsets from the center that stay inside the
    view.  ``unlimited`` marks an unbounded ray; ``clipped`` marks a ray whose
    visible path reaches the view edge even though it may continue.
    """

    direction: tuple[int, int]
    path: tuple[tuple[int, int], ...]
    unlimited: bool
    clipped: bool


@dataclass(frozen=True)
class DiagramLayout:
    """Pure geometry of the diagram; independent of painting and themes."""

    cols: int
    rows: int
    center: tuple[int, int]
    leap_targets: frozenset[tuple[int, int]]
    rays: tuple[RayInfo, ...]
    clipped_leaps: tuple[tuple[tuple[int, int], tuple[int, int]], ...]
    has_forward: bool


def _within(offset: tuple[int, int], radius_x: int, radius_y: int) -> bool:
    df, dr = offset
    return abs(df) <= radius_x and abs(dr) <= radius_y


def compute_diagram_layout(atoms) -> DiagramLayout:
    """Compute the view size and targets from a piece type's atoms.

    Finite leaps and finite rays contribute their farthest offset; unlimited
    rays contribute at least ``RAY_VIEW_RADIUS``.  Every dimension keeps one
    extra ring of non-highlighted cells, and nothing smaller than 5x5.
    """
    leap_offsets: set[tuple[int, int]] = set()
    ray_specs: list[tuple[tuple[int, int], int | None]] = []
    has_forward = False
    max_df = 0
    max_dr = 0

    for atom in atoms:
        if isinstance(atom, LeapAtom):
            df, dr = atom.offset
            if (df, dr) == (0, 0):
                continue
            leap_offsets.add((df, dr))
            max_df = max(max_df, abs(df))
            max_dr = max(max_dr, abs(dr))
            if dr > 0:
                has_forward = True
        elif isinstance(atom, RayAtom):
            df, dr = atom.direction
            if (df, dr) == (0, 0):
                continue
            ray_specs.append(((df, dr), atom.max_steps))
            if dr > 0:
                has_forward = True
            if atom.max_steps is None:
                max_df = max(max_df, RAY_VIEW_RADIUS - 1)
                max_dr = max(max_dr, RAY_VIEW_RADIUS - 1)
            else:
                max_df = max(max_df, abs(df) * atom.max_steps)
                max_dr = max(max_dr, abs(dr) * atom.max_steps)

    radius_x = max(MIN_VIEW_RADIUS, max_df + 1)
    radius_y = max(MIN_VIEW_RADIUS, max_dr + 1)
    radius_x = min(MAX_VIEW_RADIUS, radius_x)
    radius_y = min(MAX_VIEW_RADIUS, radius_y)

    leaps = frozenset(o for o in leap_offsets if _within(o, radius_x, radius_y))
    clipped: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for df, dr in sorted(leap_offsets - leaps):
        direction = (1 if df > 0 else -1, 1 if dr > 0 else -1)
        clipped.append((direction, (df, dr)))

    rays: list[RayInfo] = []
    for (df, dr), max_steps in ray_specs:
        path: list[tuple[int, int]] = []
        step = 0
        unlimited = max_steps is None
        while unlimited or step < max_steps:
            offset = ((step + 1) * df, (step + 1) * dr)
            if not _within(offset, radius_x, radius_y):
                break
            path.append(offset)
            step += 1
        rays.append(
            RayInfo(
                direction=(df, dr),
                path=tuple(path),
                unlimited=unlimited,
                clipped=unlimited
                or (
                    max_steps is not None
                    and not _within(
                        (max_steps * df, max_steps * dr), radius_x, radius_y
                    )
                ),
            )
        )

    return DiagramLayout(
        cols=2 * radius_x + 1,
        rows=2 * radius_y + 1,
        center=(radius_x, radius_y),
        leap_targets=leaps,
        rays=tuple(rays),
        clipped_leaps=tuple(clipped),
        has_forward=has_forward,
    )


class MovementDiagram(QWidget):
    """Small fixed-view board painting a piece type's canonical movement."""

    _PAD_TOP = 26  # forward-direction label
    _LEGEND_H = 20  # legend line at the bottom

    def __init__(
        self,
        cache: TextureCache,
        theme: Theme,
        tr: LocalizationManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._cache = cache
        self._theme = theme
        self._tr = tr
        self._compiled = None
        self._type_id: str | None = None
        self._layout: DiagramLayout | None = None
        self._cell = 26
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumWidth(5 * self._cell)

    # ------------------------------------------------------------------ state

    def set_type(self, compiled, type_id: str) -> None:
        self._compiled = compiled
        self._type_id = type_id
        self._layout = (
            compute_diagram_layout(compiled.types_by_id[type_id].movement_atoms)
            if compiled is not None and type_id in compiled.types_by_id
            else None
        )
        self._refresh_cell()
        self.update()

    def clear_type(self) -> None:
        self._compiled = None
        self._type_id = None
        self._layout = None
        self.update()

    def layout_data(self) -> DiagramLayout | None:
        return self._layout

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.update()

    # ------------------------------------------------------------------ sizing

    def _refresh_cell(self) -> None:
        if self._layout is None:
            return
        width = max(1, self.width())
        cell = min(30, max(16, width // self._layout.cols))
        if cell != self._cell:
            self._cell = cell
            self.updateGeometry()

    def sizeHint(self) -> QSize:
        if self._layout is None:
            return QSize(0, 0)
        return QSize(
            self._layout.cols * self._cell,
            self._PAD_TOP
            + self._layout.rows * self._cell
            + self._LEGEND_H,
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_cell()

    # ------------------------------------------------------------------ paint

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._layout is None or self._compiled is None:
            painter.end()
            return
        layout = self._layout
        cell = self._cell
        board_w = layout.cols * cell
        origin_x = max(0, (self.width() - board_w) // 2)
        board_y = self._PAD_TOP
        theme = self._theme

        self._paint_forward_label(painter, layout, origin_x, board_y)
        self._paint_board(painter, layout, origin_x, board_y)
        self._paint_rays(painter, layout, origin_x, board_y)
        self._paint_leaps(painter, layout, origin_x, board_y)
        self._paint_center(painter, layout, origin_x, board_y)
        self._paint_clipped(painter, layout, origin_x, board_y)
        self._paint_legend(painter, board_y + layout.rows * cell)
        painter.end()

    def _center_point(self, layout, origin_x, board_y, offset):
        cx, cy = layout.center
        df, dr = offset
        return QPointF(
            origin_x + (cx + df + 0.5) * self._cell,
            board_y + (cy + dr + 0.5) * self._cell,
        )

    def _paint_forward_label(self, painter, layout, origin_x, board_y) -> None:
        painter.setPen(QColor(self._theme.diagram_forward))
        font = QFont(self.font())
        font.setPointSize(max(8, self.font().pointSize() - 1))
        painter.setFont(font)
        label = f"↑ {self._tr.text('diagram.forward')}"
        rect = QRectF(origin_x, 0, layout.cols * self._cell, self._PAD_TOP - 4)
        painter.drawText(rect, Qt.AlignCenter, label)

    def _paint_board(self, painter, layout, origin_x, board_y) -> None:
        cell = self._cell
        for row in range(layout.rows):
            for col in range(layout.cols):
                color = (
                    self._theme.light_square
                    if (col + row) % 2 == 0
                    else self._theme.dark_square
                )
                painter.fillRect(
                    QRectF(origin_x + col * cell, board_y + row * cell, cell, cell),
                    QColor(color),
                )
        grid = QColor(self._theme.diagram_grid)
        grid.setAlpha(70)
        pen = QPen(grid, 1)
        painter.setPen(pen)
        for col in range(layout.cols + 1):
            x = origin_x + col * cell
            painter.drawLine(QPointF(x, board_y), QPointF(x, board_y + layout.rows * cell))
        for row in range(layout.rows + 1):
            y = board_y + row * cell
            painter.drawLine(QPointF(origin_x, y), QPointF(origin_x + layout.cols * cell, y))

    def _paint_rays(self, painter, layout, origin_x, board_y) -> None:
        theme = self._theme
        for ray in layout.rays:
            if not ray.path:
                continue
            color = QColor(theme.diagram_ray)
            color.setAlpha(int(255 * theme.diagram_ray_alpha))
            pen = QPen(color, max(2.0, self._cell * 0.12))
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            points = [self._center_point(layout, origin_x, board_y, (0, 0))]
            points.extend(
                self._center_point(layout, origin_x, board_y, off) for off in ray.path
            )
            for a, b in zip(points, points[1:]):
                painter.drawLine(a, b)
            end = points[-1]
            df, dr = ray.direction
            if ray.clipped or ray.unlimited:
                self._draw_arrow(painter, end, (df, dr), QColor(theme.diagram_arrow))
                if ray.unlimited:
                    painter.setPen(QColor(theme.diagram_arrow))
                    font = QFont(self.font())
                    font.setPointSize(max(8, self.font().pointSize() - 1))
                    painter.setFont(font)
                    label_rect = QRectF(end.x(), end.y(), 18, 14)
                    if df < 0:
                        label_rect.moveLeft(end.x() - 18)
                    if dr < 0:
                        label_rect.moveTop(end.y() - 14)
                    painter.drawText(label_rect, Qt.AlignCenter, "∞")
            else:
                # Finite ray ends inside the view: solid endpoint marker.
                painter.setBrush(QColor(theme.diagram_leap))
                painter.setPen(QPen(QColor(theme.diagram_arrow), 1))
                r = max(3.0, self._cell * 0.14)
                painter.drawEllipse(end, r, r)

    def _paint_leaps(self, painter, layout, origin_x, board_y) -> None:
        theme = self._theme
        r = max(3.0, self._cell * 0.16)
        painter.setBrush(QColor(theme.diagram_leap))
        painter.setPen(QPen(QColor(theme.diagram_arrow), 1))
        for offset in sorted(layout.leap_targets):
            point = self._center_point(layout, origin_x, board_y, offset)
            painter.drawEllipse(point, r, r)

    def _paint_center(self, painter, layout, origin_x, board_y) -> None:
        point = self._center_point(layout, origin_x, board_y, (0, 0))
        size = int(self._cell * 0.86)
        if self._compiled is not None and self._type_id is not None:
            pixmap = self._cache.pixmap(self._compiled, self._type_id, 0, size)
            painter.drawPixmap(
                QPointF(point.x() - size / 2, point.y() - size / 2),
                pixmap,
            )
        else:
            painter.setPen(QColor(self._theme.diagram_forward))
            painter.drawEllipse(point, self._cell * 0.3, self._cell * 0.3)

    def _paint_clipped(self, painter, layout, origin_x, board_y) -> None:
        theme = self._theme
        if not layout.clipped_leaps:
            return
        font = QFont(self.font())
        font.setPointSize(max(7, self.font().pointSize() - 2))
        painter.setFont(font)
        painter.setPen(QColor(theme.diagram_leap))
        for direction, offset in layout.clipped_leaps:
            edge = (
                layout.center[0] + direction[0] * layout.center[0],
                layout.center[1] + direction[1] * layout.center[1],
            )
            point = self._center_point(layout, origin_x, board_y, edge)
            self._draw_arrow(painter, point, direction, QColor(theme.diagram_leap))
            df, dr = offset
            label = f"+{abs(df)},{abs(dr)}"
            rect = QRectF(point.x() - 20, point.y() - 16, 40, 14)
            painter.drawText(rect, Qt.AlignCenter, label)

    def _paint_legend(self, painter, y: float) -> None:
        theme = self._theme
        font = QFont(self.font())
        font.setPointSize(max(7, self.font().pointSize() - 2))
        painter.setFont(font)
        x = 4
        # Leap legend.
        painter.setBrush(QColor(theme.diagram_leap))
        painter.setPen(QPen(QColor(theme.diagram_arrow), 1))
        painter.drawEllipse(QPointF(x + 4, y + 9), 3, 3)
        painter.setPen(QColor(theme.diagram_forward))
        painter.drawText(
            QRectF(x + 10, y, 100, 20),
            Qt.AlignVCenter | Qt.AlignLeft,
            self._tr.text("diagram.leap_legend"),
        )
        # Ray legend.
        ray_x = x + 112
        pen = QPen(QColor(theme.diagram_ray), 2)
        painter.setPen(pen)
        painter.drawLine(QPointF(ray_x, y + 9), QPointF(ray_x + 16, y + 9))
        painter.setPen(QColor(theme.diagram_forward))
        painter.drawText(
            QRectF(ray_x + 20, y, 130, 20),
            Qt.AlignVCenter | Qt.AlignLeft,
            self._tr.text("diagram.ray_legend"),
        )

    def _draw_arrow(
        self, painter: QPainter, tip: QPointF, direction: tuple[int, int], color: QColor
    ) -> None:
        df, dr = direction
        length = max(4.0, self._cell * 0.22)
        base = QPointF(tip.x() - df * length, tip.y() - dr * length)
        pen = QPen(color, max(2.0, self._cell * 0.1))
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(base, tip)
        head = max(3.5, self._cell * 0.2)
        dx, dy = df, dr
        length_d = (dx * dx + dy * dy) ** 0.5 or 1.0
        ux, uy = dx / length_d, dy / length_d
        left = QPointF(tip.x() - ux * head + uy * head * 0.5, tip.y() - uy * head - ux * head * 0.5)
        right = QPointF(tip.x() - ux * head - uy * head * 0.5, tip.y() - uy * head + ux * head * 0.5)
        painter.setBrush(color)
        painter.setPen(QPen(color, 1))
        painter.drawPolygon(QPolygonF([tip, left, right]))
