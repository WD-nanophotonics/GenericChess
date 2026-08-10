"""Persistent board renderer with a bounded, cancel-safe presentation pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation, Signal
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
from ...core.pieces import Piece
from ...ui.theme import Theme
from ...ui.view_models import BoardViewModel
from ...visual.texture_style import PieceTextureStyle
from .texture_cache import TextureCache


CELL = 100.0


@dataclass(frozen=True)
class MotionConfig:
    """Shared timing and easing policy for every board transition."""

    move_ms: int = 145
    capture_ms: int = 110
    drop_ms: int = 125
    promotion_ms: int = 125
    easing: QEasingCurve.Type = QEasingCurve.Type.InOutCubic


DEFAULT_MOTION = MotionConfig()


@dataclass(frozen=True)
class BoardRenderConfig:
    theme: Theme
    texture_ratio: float = 0.8
    texture_style: PieceTextureStyle = PieceTextureStyle()
    show_coordinates: bool = True
    show_legal_moves: bool = True
    show_last_move: bool = True
    show_hover: bool = True


@dataclass(frozen=True)
class _Transition:
    kind: str
    source: Square | None
    destination: Square
    piece: Piece
    captured: Piece | None = None


class PersistentPieceItem(QGraphicsSvgItem):
    """One graphics object per logical piece identity while it remains live."""

    def __init__(self) -> None:
        super().__init__()
        self.logical_square: Square | None = None
        self.piece: Piece | None = None
        self.setZValue(10)

    def apply_piece(self, scene: "BoardScene", piece: Piece, square: Square) -> None:
        self.logical_square = square
        self.piece = piece
        compiled = scene._compiled
        config = scene._config
        if compiled is None or config is None:
            return
        size = int(CELL * config.texture_ratio)
        renderer = scene._cache.renderer(
            compiled,
            piece.current_type_id,
            piece.owner,
            size,
            style=config.texture_style,
        )
        self.setSharedRenderer(renderer)
        default = renderer.defaultSize()
        self.setTransform(
            QTransform().scale(
                size / max(1, default.width()),
                size / max(1, default.height()),
            )
        )
        scene.set_piece_position(self, square)


class BoardScene(QGraphicsScene):
    """Layered renderer whose static and piece items survive normal refreshes."""

    presentation_busy_changed = Signal(bool)

    def __init__(self, cache: TextureCache, parent=None) -> None:
        super().__init__(parent)
        self._cache = cache
        self._config: BoardRenderConfig | None = None
        self._compiled = None
        self._orientation = 0
        self._n = 8
        self._hover_item: QGraphicsRectItem | None = None
        self._square_items: dict[Square, QGraphicsRectItem] = {}
        self._coordinate_items: dict[tuple[str, int], QGraphicsSimpleTextItem] = {}
        self._piece_items: dict[Square, PersistentPieceItem] = {}
        self._interaction_items: list[QGraphicsItem] = []
        self._interaction_model: BoardViewModel | None = None
        self._effect_items: set[QGraphicsItem] = set()
        self._visual_model: BoardViewModel | None = None
        self._authoritative_model: BoardViewModel | None = None
        self._pending_model: BoardViewModel | None = None
        self._transition_target_model: BoardViewModel | None = None
        self._active_transition: _Transition | None = None
        self._animation: QVariantAnimation | None = None
        self._generation = 0
        self._animation_enabled = True

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

    # ------------------------------------------------------------------ evidence helpers

    def piece_item_at(self, square: Square) -> PersistentPieceItem | None:
        return self._piece_items.get(square)

    def piece_items(self) -> dict[Square, PersistentPieceItem]:
        return dict(self._piece_items)

    def piece_item_count(self) -> int:
        return len(self._piece_items)

    def static_item_count(self) -> int:
        return len(self._square_items) + len(self._coordinate_items)

    def effect_item_count(self) -> int:
        return len(self._effect_items)

    def motion_active(self) -> bool:
        return self._active_transition is not None

    def animation_child_count(self) -> int:
        return len(self.findChildren(QVariantAnimation))

    def rendered_occupancy(self) -> dict[Square, tuple[int, str, str, bool]]:
        return {
            square: (
                item.piece.owner,
                item.piece.base_type_id,
                item.piece.current_type_id,
                item.piece.promoted,
            )
            for square, item in self._piece_items.items()
            if item.piece is not None
        }

    # ------------------------------------------------------------------ lifecycle

    def clear(self) -> None:
        self.cancel_motion()
        QGraphicsScene.clear(self)
        self._square_items.clear()
        self._coordinate_items.clear()
        self._piece_items.clear()
        self._interaction_items.clear()
        self._interaction_model = None
        self._effect_items.clear()
        self._hover_item = None
        self._visual_model = None
        self._authoritative_model = None
        self._pending_model = None
        self._transition_target_model = None
        self._config = None
        self._compiled = None

    def build(
        self,
        model: BoardViewModel,
        compiled,
        config: BoardRenderConfig,
        orientation: int,
    ) -> None:
        """Compatibility entry point for callers that explicitly request a reset."""
        self.clear()
        self._set_structure(model, compiled, config, orientation)
        self._sync_pieces(model)
        self._authoritative_model = model
        self._visual_model = model
        self._refresh_interaction(model)

    def present(
        self,
        model: BoardViewModel,
        compiled,
        config: BoardRenderConfig,
        orientation: int,
        *,
        animation_enabled: bool = True,
    ) -> None:
        structural = self._needs_structure(model, compiled, config, orientation)
        self._animation_enabled = bool(animation_enabled)
        if structural:
            self.cancel_motion()
            self._set_structure(model, compiled, config, orientation)
            self._sync_pieces(model)
            self._authoritative_model = model
            self._visual_model = model
            self._refresh_interaction(model)
            return

        if orientation != self._orientation:
            self.cancel_motion()
            self._orientation = orientation
            self._reposition_existing()

        old_config = self._config
        coordinates_changed = old_config is not None and (
            old_config.show_coordinates != config.show_coordinates
        )
        texture_changed = old_config is not None and (
            old_config.texture_ratio != config.texture_ratio
            or old_config.texture_style != config.texture_style
        )
        self._config = config
        if coordinates_changed:
            self._set_coordinates_enabled(config.show_coordinates)
        if texture_changed and self._active_transition is None:
            for square, item in self._piece_items.items():
                if item.piece is not None:
                    item.apply_piece(self, item.piece, square)
        previous = self._authoritative_model or self._visual_model
        if previous is not None and (
            previous.is_history_preview or model.is_history_preview
        ):
            self.cancel_motion()
            self._authoritative_model = model
            self._sync_pieces(model)
            self._visual_model = model
            self._refresh_interaction(model)
            return
        if previous is not None and (
            self._is_movement_preview(previous) or self._is_movement_preview(model)
        ):
            self.cancel_motion()
            self._authoritative_model = model
            self._sync_pieces(model)
            self._visual_model = model
            self._refresh_interaction(model)
            return
        if self._active_transition is not None:
            self._refresh_interaction(
                self._transition_target_model or self._visual_model or model
            )
            if not self._animation_enabled:
                self._cancel_and_snap(model)
                return
            if self._same_occupancy(model, previous):
                return
            if self._same_occupancy(model, self._visual_model):
                return
            if self._pending_model is None and self._animation_enabled:
                transition = self._infer_transition(previous, model)
                if transition is not None:
                    self._pending_model = model
                    self._authoritative_model = model
                    return
            self._cancel_and_snap(model)
            return

        self._authoritative_model = model
        if self._same_occupancy(model, self._visual_model):
            self._visual_model = model
            self._refresh_interaction(model)
            return
        transition = self._infer_transition(previous, model)
        if transition is not None and self._animation_enabled:
            # Keep overlays on the currently presented frame while the piece
            # travels; authoritative state may already contain another move.
            self._refresh_interaction(self._visual_model or previous or model)
            self._start_transition(transition, model)
        else:
            self._sync_pieces(model)
            self._visual_model = model
            self._refresh_interaction(model)

    def cancel_motion(self) -> None:
        self._generation += 1
        if self._animation is not None:
            self._animation.stop()
            self._animation.deleteLater()
            self._animation = None
        for item in tuple(self._effect_items):
            for square, current in tuple(self._piece_items.items()):
                if current is item:
                    self._piece_items.pop(square, None)
            self.removeItem(item)
        self._effect_items.clear()
        self._active_transition = None
        self._pending_model = None
        self._transition_target_model = None
        self._emit_busy(False)

    # ------------------------------------------------------------------ structure and layers

    def _needs_structure(self, model, compiled, config, orientation) -> bool:
        if self._config is None or self._compiled is None:
            return True
        return (
            model.board_size != self._n
            or compiled.ruleset_fingerprint != self._compiled.ruleset_fingerprint
            or self._static_theme_key(self._config) != self._static_theme_key(config)
        )

    @staticmethod
    def _static_theme_key(config: BoardRenderConfig):
        theme = config.theme
        return (theme.light_square, theme.dark_square, theme.coordinate_text)

    def _set_structure(self, model, compiled, config, orientation) -> None:
        self._remove_interaction()
        for item in tuple(self._piece_items.values()):
            self.removeItem(item)
        self._piece_items.clear()
        for item in tuple(self._square_items.values()):
            self.removeItem(item)
        self._square_items.clear()
        for item in tuple(self._coordinate_items.values()):
            self.removeItem(item)
        self._coordinate_items.clear()
        self._config = config
        self._compiled = compiled
        self._orientation = orientation
        self._n = model.board_size
        theme = config.theme
        for sv in model.squares:
            x, y = self.logical_to_scene(sv.square)
            rect = QGraphicsRectItem(QRectF(x, y, CELL, CELL))
            color = theme.light_square if (sv.square.file + sv.square.rank) % 2 == 0 else theme.dark_square
            rect.setBrush(QBrush(QColor(color)))
            rect.setPen(QPen(Qt.NoPen))
            rect.setZValue(0)
            self.addItem(rect)
            self._square_items[sv.square] = rect
        if config.show_coordinates:
            self._add_coordinates(model.board_size)
        self.setSceneRect(0, 0, self._n * CELL, self._n * CELL)

    def _reposition_existing(self) -> None:
        for square, item in self._square_items.items():
            x, y = self.logical_to_scene(square)
            item.setRect(QRectF(x, y, CELL, CELL))
        for (kind, index), item in self._coordinate_items.items():
            if kind == "file":
                square = Square(index, 0)
            else:
                square = Square(0, index)
            x, y = self.logical_to_scene(square)
            offset_x = CELL * 0.75 if kind == "file" else CELL * 0.04
            offset_y = CELL * 0.78 if kind == "file" else CELL * 0.03
            item.setPos(x + offset_x, y + offset_y)
        for square, item in self._piece_items.items():
            self.set_piece_position(item, square)

    def _sync_pieces(self, model: BoardViewModel) -> None:
        wanted = {sv.square: sv.piece for sv in model.squares if sv.piece is not None}
        # Reconcile a snap through the same identity map as an animated move:
        # a model refresh may be immediate, but it must not recreate the mover.
        for destination, new_piece in wanted.items():
            existing = self._piece_items.get(destination)
            if (
                existing is not None
                and existing.piece is not None
                and existing.piece.owner == new_piece.owner
                and existing.piece.base_type_id == new_piece.base_type_id
            ):
                continue
            source = next(
                (
                    square
                    for square, item in self._piece_items.items()
                    if square not in wanted
                    and item.piece is not None
                    and item.piece.owner == new_piece.owner
                    and item.piece.base_type_id == new_piece.base_type_id
                ),
                None,
            )
            if source is not None:
                captured = self._piece_items.pop(destination, None)
                if captured is not None:
                    self.removeItem(captured)
                self._piece_items[destination] = self._piece_items.pop(source)
            elif destination in self._piece_items:
                continue
        for square in tuple(self._piece_items):
            if square not in wanted:
                item = self._piece_items.pop(square)
                self.removeItem(item)
        for square, piece in wanted.items():
            item = self._piece_items.get(square)
            if item is None:
                item = PersistentPieceItem()
                self._piece_items[square] = item
                self.addItem(item)
            item.setOpacity(1.0)
            item.apply_piece(self, piece, square)

    def set_piece_position(self, item: PersistentPieceItem, square: Square) -> None:
        x, y = self.logical_to_scene(square)
        size = int(CELL * (self._config.texture_ratio if self._config else 0.8))
        item.setPos(x + (CELL - size) / 2, y + (CELL - size) / 2)

    def _remove_interaction(self) -> None:
        for item in self._interaction_items:
            self.removeItem(item)
        self._interaction_items.clear()
        self._hover_item = None

    def interaction_snapshot(self) -> dict[Square, tuple[bool, bool, bool, bool, bool, bool, bool]]:
        """Expose the rendered interaction flags for focused renderer tests."""
        model = self._interaction_model
        if model is None:
            return {}
        return {
            sv.square: (
                sv.is_last_move_from,
                sv.is_last_move_to,
                sv.is_selected,
                sv.is_legal_move,
                sv.is_legal_capture,
                sv.is_preview,
                sv.is_check_anchor,
            )
            for sv in model.squares
            if (
                sv.is_last_move_from
                or sv.is_last_move_to
                or sv.is_selected
                or sv.is_legal_move
                or sv.is_legal_capture
                or sv.is_preview
                or sv.is_check_anchor
            )
        }

    def _refresh_interaction(self, model: BoardViewModel) -> None:
        self._remove_interaction()
        self._interaction_model = model
        if self._config is None:
            return
        theme = self._config.theme
        for sv in model.squares:
            x, y = self.logical_to_scene(sv.square)
            rect = QRectF(x, y, CELL, CELL)
            if self._config.show_last_move and sv.is_last_move_from:
                self._add_rect(rect, theme.last_move_from, 150, 1)
            if self._config.show_last_move and sv.is_last_move_to:
                self._add_rect(rect, theme.last_move_to, 170, 1)
            if sv.is_preview:
                self._add_rect(rect, theme.preview_fill, int(255 * theme.preview_opacity), 3)
            if sv.is_legal_move and self._config.show_legal_moves:
                self._add_dot(rect, theme.legal_move_dot, 4)
            if sv.is_legal_capture and self._config.show_legal_moves:
                self._add_ring(rect, theme.capture_ring, 5)
            if sv.is_selected:
                self._add_border(rect, theme.selected_border, 6)
            if sv.is_check_anchor:
                self._add_border(rect, theme.threat_border, 7)

    def _register_interaction(self, item: QGraphicsItem) -> None:
        self._interaction_items.append(item)
        self.addItem(item)

    def _add_rect(self, rect: QRectF, color: str, alpha: int, z: int) -> None:
        item = QGraphicsRectItem(rect)
        c = QColor(color)
        c.setAlpha(alpha)
        item.setBrush(QBrush(c))
        item.setPen(QPen(Qt.NoPen))
        item.setZValue(z)
        self._register_interaction(item)

    def _add_dot(self, rect: QRectF, color: str, z: int) -> None:
        r = CELL * 0.13
        item = QGraphicsEllipseItem(rect.center().x() - r, rect.center().y() - r, 2 * r, 2 * r)
        item.setBrush(QBrush(QColor(color)))
        item.setPen(QPen(Qt.NoPen))
        item.setZValue(z)
        self._register_interaction(item)

    def _add_ring(self, rect: QRectF, color: str, z: int) -> None:
        margin = CELL * 0.08
        item = QGraphicsEllipseItem(rect.x() + margin, rect.y() + margin, CELL - 2 * margin, CELL - 2 * margin)
        pen = QPen(QColor(color))
        pen.setWidthF(CELL * 0.06)
        item.setPen(pen)
        item.setBrush(QBrush(Qt.NoBrush))
        item.setZValue(z)
        self._register_interaction(item)

    def _add_border(self, rect: QRectF, color: str, z: int) -> None:
        item = QGraphicsRectItem(rect.adjusted(2, 2, -2, -2))
        pen = QPen(QColor(color))
        pen.setWidthF(CELL * 0.05)
        item.setPen(pen)
        item.setBrush(QBrush(Qt.NoBrush))
        item.setZValue(z)
        self._register_interaction(item)

    def _add_coordinates(self, n: int) -> None:
        if self._config is None:
            return
        color = QColor(self._config.theme.coordinate_text)
        for file in range(n):
            x, y = self.logical_to_scene(Square(file, 0))
            label = chr(ord("a") + file) if file < 26 else str(file)
            text = QGraphicsSimpleTextItem(label)
            text.setBrush(QBrush(color))
            text.setPos(x + CELL * 0.75, y + CELL * 0.78)
            text.setZValue(8)
            self.addItem(text)
            self._coordinate_items[("file", file)] = text
        for rank in range(n):
            x, y = self.logical_to_scene(Square(0, rank))
            text = QGraphicsSimpleTextItem(str(rank + 1))
            text.setBrush(QBrush(color))
            text.setPos(x + CELL * 0.04, y + CELL * 0.03)
            text.setZValue(8)
            self.addItem(text)
            self._coordinate_items[("rank", rank)] = text

    def _set_coordinates_enabled(self, enabled: bool) -> None:
        if enabled:
            if not self._coordinate_items:
                self._add_coordinates(self._n)
            return
        for item in tuple(self._coordinate_items.values()):
            self.removeItem(item)
        self._coordinate_items.clear()

    def set_hover(self, square: Square | None) -> None:
        if self._hover_item is not None:
            self.removeItem(self._hover_item)
            if self._hover_item in self._interaction_items:
                self._interaction_items.remove(self._hover_item)
            self._hover_item = None
        if square is None or self._config is None or not self._config.show_hover:
            return
        x, y = self.logical_to_scene(square)
        c = QColor(self._config.theme.hover_fill)
        c.setAlpha(int(255 * self._config.theme.hover_opacity))
        item = QGraphicsRectItem(QRectF(x, y, CELL, CELL))
        item.setBrush(QBrush(c))
        item.setPen(QPen(Qt.NoPen))
        item.setZValue(2)
        self._register_interaction(item)
        self._hover_item = item

    # ------------------------------------------------------------------ transition inference

    @staticmethod
    def _occupancy(model: BoardViewModel | None) -> dict[Square, Piece]:
        if model is None:
            return {}
        return {sv.square: sv.piece for sv in model.squares if sv.piece is not None}

    @classmethod
    def _same_occupancy(cls, left, right) -> bool:
        return cls._occupancy(left) == cls._occupancy(right)

    @staticmethod
    def _is_movement_preview(model: BoardViewModel | None) -> bool:
        return bool(model and any(square.is_preview for square in model.squares))

    @classmethod
    def _infer_transition(cls, old, new) -> _Transition | None:
        before = cls._occupancy(old)
        after = cls._occupancy(new)
        changed = set(before) | set(after)
        changed = {square for square in changed if before.get(square) != after.get(square)}
        if not changed:
            return None
        removed = [square for square in changed if square in before and square not in after]
        added = [square for square in changed if square in after and square not in before]
        replaced = [square for square in changed if square in before and square in after]
        if not removed and len(added) == 1:
            destination = added[0]
            return _Transition("drop", None, destination, after[destination])
        if len(removed) != 1 or len(replaced) > 1 or len(added) > 1:
            return None
        source = removed[0]
        if len(added) == 1:
            destination = added[0]
            captured = None
        elif len(replaced) == 1:
            destination = replaced[0]
            captured = before[destination]
        else:
            return None
        piece = after[destination]
        if destination == source:
            return None
        if before[source].owner != piece.owner:
            return None
        kind = "promotion" if piece.promoted or piece.current_type_id != piece.base_type_id else "move"
        if captured is not None:
            kind = "capture" if kind == "move" else kind
        return _Transition(kind, source, destination, piece, captured)

    # ------------------------------------------------------------------ motion pipeline

    def _emit_busy(self, busy: bool) -> None:
        self.presentation_busy_changed.emit(bool(busy))

    def _cancel_and_snap(self, model: BoardViewModel) -> None:
        self.cancel_motion()
        self._sync_pieces(model)
        self._visual_model = model
        self._authoritative_model = model
        self._refresh_interaction(model)

    def _start_transition(self, transition: _Transition, target: BoardViewModel) -> None:
        if transition.source is None:
            item = PersistentPieceItem()
            self._piece_items[transition.destination] = item
            item.apply_piece(self, transition.piece, transition.destination)
            item.setOpacity(0.0)
            self.addItem(item)
            self._effect_items.add(item)
        else:
            item = self._piece_items.pop(transition.source, None)
            if item is None:
                self._sync_pieces(target)
                self._visual_model = target
                return
            captured = self._piece_items.pop(transition.destination, None)
            if captured is not None:
                self._effect_items.add(captured)
            self._piece_items[transition.destination] = item
            item.logical_square = transition.destination
            item.setOpacity(1.0)
            self.set_piece_position(item, transition.source)
            transition = _Transition(transition.kind, transition.source, transition.destination, transition.piece, captured.piece if captured and captured.piece else None)

        self._generation += 1
        generation = self._generation
        self._active_transition = transition
        self._transition_target_model = target
        self._emit_busy(True)
        animation = QVariantAnimation(self)
        self._animation = animation
        duration = {
            "move": DEFAULT_MOTION.move_ms,
            "capture": DEFAULT_MOTION.capture_ms,
            "drop": DEFAULT_MOTION.drop_ms,
            "promotion": DEFAULT_MOTION.promotion_ms,
        }[transition.kind]
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(DEFAULT_MOTION.easing)

        def update(value) -> None:
            if generation != self._generation or self._active_transition is not transition:
                return
            progress = float(value)
            moving = self._piece_items.get(transition.destination)
            if moving is not None and transition.source is not None:
                sx, sy = self.logical_to_scene(transition.source)
                dx, dy = self.logical_to_scene(transition.destination)
                size = int(CELL * (self._config.texture_ratio if self._config else 0.8))
                moving.setPos(
                    sx + (dx - sx) * progress + (CELL - size) / 2,
                    sy + (dy - sy) * progress + (CELL - size) / 2,
                )
            elif moving is not None:
                moving.setOpacity(progress)
            captured = next((x for x in self._effect_items if x is not moving), None)
            if captured is not None:
                captured.setOpacity(max(0.0, 1.0 - progress))

        def finished() -> None:
            if generation != self._generation or self._active_transition is not transition:
                return
            moving = self._piece_items.get(transition.destination)
            if moving is not None:
                moving.apply_piece(self, transition.piece, transition.destination)
                moving.setOpacity(1.0)
                self._effect_items.discard(moving)
            for item in tuple(self._effect_items):
                self.removeItem(item)
            self._effect_items.clear()
            self._animation = None
            self._active_transition = None
            self._visual_model = target
            self._transition_target_model = None
            self._refresh_interaction(target)
            self._emit_busy(False)
            pending = self._pending_model
            self._pending_model = None
            if pending is not None:
                transition_next = self._infer_transition(target, pending)
                if transition_next is not None and self._animation_enabled:
                    self._refresh_interaction(target)
                    self._start_transition(transition_next, pending)
                else:
                    self._sync_pieces(pending)
                    self._visual_model = pending
                    self._refresh_interaction(pending)
            animation.deleteLater()

        animation.valueChanged.connect(update)
        animation.finished.connect(finished)
        animation.start()
