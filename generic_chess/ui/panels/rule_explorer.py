"""Rule explorer: RuleSet overview, piece-type list, scrollable detail and
entity selection banner."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...core.movement import LeapAtom, RayAtom
from ..board.texture_cache import TextureCache
from ..controller import UIController
from ..i18n.manager import LocalizationManager
from ..theme import Theme, default_theme
from .movement_diagram import MovementDiagram


def localized_direction(df: int, dr: int, tr: LocalizationManager) -> str:
    key = "movement.direction.sideways"
    if dr > 0 and df > 0:
        key = "movement.direction.forward_right"
    elif dr > 0 and df < 0:
        key = "movement.direction.forward_left"
    elif dr < 0 and df > 0:
        key = "movement.direction.backward_right"
    elif dr < 0 and df < 0:
        key = "movement.direction.backward_left"
    elif dr > 0:
        key = "movement.direction.forward"
    elif dr < 0:
        key = "movement.direction.backward"
    elif df > 0:
        key = "movement.direction.right"
    elif df < 0:
        key = "movement.direction.left"
    return tr.text(key)


def localized_atom(atom, tr: LocalizationManager) -> str:
    if isinstance(atom, RayAtom):
        direction = localized_direction(atom.direction[0], atom.direction[1], tr)
        if atom.max_steps is None:
            return tr.text("movement.ray.unlimited", direction=direction)
        return tr.text(
            "movement.ray.max", direction=direction, n=atom.max_steps
        )
    if isinstance(atom, LeapAtom):
        direction = localized_direction(atom.offset[0], atom.offset[1], tr)
        span = max(abs(atom.offset[0]), abs(atom.offset[1]))
        return tr.text("movement.leap", direction=direction, span=span)
    return tr.text("common.unknown")


def localized_movement(piece_type, tr: LocalizationManager) -> tuple[str, ...]:
    return tuple(localized_atom(a, tr) for a in piece_type.movement_atoms)


class SelectionBanner(QWidget):
    """High-contrast banner for the concrete piece currently selected."""

    def __init__(self, theme: Theme, parent=None) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setObjectName("selection_banner")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        self._accent = QWidget()
        self._accent.setObjectName("selection_accent")
        self._accent.setFixedWidth(4)
        layout.addWidget(self._accent)

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(2)
        self._title = QLabel()
        self._title.setObjectName("selection_title")
        text.addWidget(self._title)
        self._body = QLabel()
        self._body.setObjectName("selection_body")
        self._body.setWordWrap(True)
        text.addWidget(self._body)
        layout.addLayout(text, 1)

        self.hide()
        self._apply_style()

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self._apply_style()

    def _apply_style(self) -> None:
        t = self._theme
        self.setStyleSheet(
            f"""
            SelectionBanner {{
                background: {t.selection_bg};
                border-radius: 5px;
            }}
            QLabel#selection_title {{
                color: {t.selection_fg};
                font-weight: bold;
                font-size: 13px;
            }}
            QLabel#selection_body {{
                color: {t.selection_secondary};
                font-size: 12px;
            }}
            """
        )
        self._accent.setStyleSheet(
            f"background: {t.selection_accent}; border-radius: 2px;"
        )

    def set_entity(
        self,
        *,
        tr: LocalizationManager,
        owner_name: str,
        type_id: str,
        square,
        promoted: bool,
        base_type_id: str | None,
    ) -> None:
        status = tr.text("rules.promoted" if promoted else "rules.not_promoted")
        lines = [
            tr.text("rules.selection_line", owner=owner_name, type=type_id),
            tr.text("rules.position_line", square=str(square)),
            tr.text("rules.status_line", value=status),
        ]
        if base_type_id is not None:
            lines.append(
                tr.text("rules.base_type_line", type=base_type_id)
            )
        self._title.setText(tr.text("rules.current_selection"))
        self._body.setText("<br>".join(lines))
        self.show()

    def clear(self) -> None:
        self._title.clear()
        self._body.clear()
        self.hide()


class RuleExplorerPanel(QWidget):
    """Master-detail rules browser with live entity inspection.

    Overview and the piece-type list stay fixed on top; the detail area lives
    in one vertical ``QScrollArea`` so long movement content never overflows
    the window.
    """

    def __init__(
        self,
        controller: UIController,
        cache: TextureCache,
        tr: LocalizationManager,
        theme: Theme | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._cache = cache
        self._tr = tr
        self._theme = theme if theme is not None else default_theme()
        self._expanded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._entity = SelectionBanner(self._theme)
        layout.addWidget(self._entity)

        self._overview = QLabel()
        self._overview.setWordWrap(True)
        layout.addWidget(self._overview)

        self._types = QListWidget()
        self._types.setSizeAdjustPolicy(QListWidget.AdjustToContents)
        self._types.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._types.setWordWrap(True)
        self._types.itemClicked.connect(self._on_type_clicked)
        layout.addWidget(self._types)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._content = QWidget()
        self._detail_layout = QVBoxLayout(self._content)
        self._detail_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._detail_layout.setContentsMargins(4, 2, 4, 4)
        self._detail_layout.setSpacing(6)
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, 1)

        header = QHBoxLayout()
        header.setSpacing(8)
        self._detail_image = QLabel()
        self._detail_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_image.setFixedWidth(72)
        header.addWidget(self._detail_image, 0, Qt.AlignmentFlag.AlignTop)
        self._title = QLabel()
        self._title.setWordWrap(True)
        header.addWidget(self._title, 1)
        self._detail_layout.addLayout(header)

        self._diagram = MovementDiagram(self._cache, self._theme, self._tr)
        self._detail_layout.addWidget(self._diagram)

        self._detail = QLabel()
        self._detail.setWordWrap(True)
        self._detail_layout.addWidget(self._detail)

        self._tech_button = QToolButton()
        self._tech_button.setCheckable(True)
        self._tech_button.clicked.connect(self._toggle_technical)
        self._detail_layout.addWidget(self._tech_button)
        self._table = QTableWidget(0, 3)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.hide()
        self._detail_layout.addWidget(self._table)

    # ------------------------------------------------------------------ state

    def refresh(self) -> None:
        tr = self._tr
        compiled = self._controller.compiled
        self._types.clear()
        if compiled is None:
            self._overview.setText(tr.text("rules.no_rules"))
            self._entity.clear()
            self._detail.setText(tr.text("rules.select_type"))
            self._detail_image.clear()
            self._title.clear()
            self._diagram.clear_type()
            self._tech_button.hide()
            self._table.hide()
            self._types.setMaximumHeight(180)
            return
        self._render_overview(compiled)
        self._render_type_list(compiled)
        self._render_entity()
        self._render_detail()
        self._tech_button.setText(tr.text("rules.technical_section"))
        self._tech_button.show()
        self._tech_button.setChecked(self._expanded)
        self._table.setVisible(self._expanded)

    def _render_overview(self, compiled) -> None:
        tr = self._tr
        n = compiled.board_size
        drop_types = [
            tid
            for tid, masks in compiled.drop_allowed.items()
            if any(any(m) for m in masks)
        ]
        promotable = [pt for pt in compiled.piece_types if pt.is_promotable]
        lines = [
            f"<b>{tr.text('rules.board')}:</b> {n} × {n}",
            f"<b>{tr.text('rules.piece_types')}:</b> {len(compiled.piece_types)}",
            f"<b>{tr.text('rules.drops_enabled' if drop_types else 'rules.drops_disabled')}</b>",
            f"<b>{tr.text('rules.promotion_enabled' if promotable else 'rules.promotion_disabled')}</b>",
            f"<b>{tr.text('rules.repetition', n=compiled.repetition_limit)}</b>",
            f"<b>{tr.text('rules.win_condition')}</b>",
        ]
        self._overview.setText("<br>".join(lines))

    def _render_type_list(self, compiled) -> None:
        tr = self._tr
        for pt in compiled.piece_types:
            flags = []
            if pt.is_anchor:
                flags.append(tr.text("rules.anchor"))
            if pt.is_promotable:
                flags.append(tr.text("rules.promotable"))
            if pt.type_id in compiled.drop_allowed:
                flags.append(tr.text("rules.droppable"))
            flags_text = " · ".join(flags)
            item = QListWidgetItem(f"{pt.type_id}    {flags_text}")
            pixmap = self._cache.pixmap(compiled, pt.type_id, 0, 24)
            item.setIcon(QIcon(pixmap))
            item.setData(Qt.UserRole, pt.type_id)
            self._types.addItem(item)
        count = self._types.count()
        self._types.setMaximumHeight(max(60, min(180, count * 36 + 8)))

    def _render_entity(self) -> None:
        tr = self._tr
        info = self._controller.piece_info()
        if info is None or info.owner is None or info.square is None:
            self._entity.clear()
            return
        owner_name = tr.text("player.white" if info.owner == 0 else "player.black")
        self._entity.set_entity(
            tr=tr,
            owner_name=owner_name,
            type_id=info.type_id,
            square=info.square,
            promoted=info.promoted,
            base_type_id=info.base_type_id,
        )

    def _render_detail(self) -> None:
        tr = self._tr
        compiled = self._controller.compiled
        if compiled is None:
            return
        info = self._controller.piece_info()
        type_id = info.type_id if info is not None else None
        if type_id is None:
            self._detail.setText(tr.text("rules.select_type"))
            self._detail_image.clear()
            self._title.clear()
            self._diagram.clear_type()
            self._table.setRowCount(0)
            return
        pt = compiled.types_by_id[type_id]
        owner = info.owner if info is not None else None
        pixmap = self._cache.pixmap(compiled, type_id, owner if owner is not None else 0, 64)
        self._detail_image.setPixmap(pixmap)
        self._diagram.set_type(compiled, type_id)

        flags = []
        if pt.is_anchor:
            flags.append(tr.text("rules.anchor"))
        if pt.is_promotable:
            flags.append(tr.text("rules.promotable"))
        if type_id in compiled.drop_allowed:
            flags.append(tr.text("rules.droppable"))
        self._title.setText(
            f"<b>{type_id}</b>" + (f"<br><span style='color:#78909c'>{' · '.join(flags)}</span>" if flags else "")
        )

        movement = localized_movement(pt, tr)
        parts = [tr.text("rules.movement_section")]
        parts.extend(f"• {m}" for m in movement)
        if pt.is_promotable:
            targets = "、".join(pt.promotion_target_ids)
            parts.append("")
            parts.append(tr.text("rules.promotion_section"))
            parts.append(f"• {tr.text('rules.promotion_targets')}: {targets}")
        if type_id in compiled.drop_allowed:
            mask = compiled.drop_allowed[type_id][0]
            restricted = any(not ok for ok in mask)
            parts.append("")
            parts.append(tr.text("rules.drop_section"))
            parts.append(
                f"• {tr.text('rules.drop_forbidden') if restricted else tr.text('rules.droppable')}"
            )
        self._detail.setText("<br>".join(parts))
        self._render_technical_table(compiled, pt)

    def _render_technical_table(self, compiled, pt) -> None:
        tr = self._tr
        atoms = list(pt.movement_atoms)
        self._table.setRowCount(len(atoms))
        headers = [
            tr.text("rules.movement"),
            tr.text("rules.technical_details"),
            tr.text("rules.advanced"),
        ]
        self._table.setHorizontalHeaderLabels(headers)
        for row, atom in enumerate(atoms):
            if isinstance(atom, LeapAtom):
                kind = "leap"
                vector = f"{atom.offset[0]}, {atom.offset[1]}"
                dist = "1"
            else:
                kind = "ray"
                vector = f"{atom.direction[0]}, {atom.direction[1]}"
                dist = "∞" if atom.max_steps is None else str(atom.max_steps)
            self._table.setItem(row, 0, QTableWidgetItem(kind))
            self._table.setItem(row, 1, QTableWidgetItem(vector))
            self._table.setItem(row, 2, QTableWidgetItem(dist))

    def _toggle_technical(self) -> None:
        self._expanded = not self._expanded
        self._table.setVisible(self._expanded)

    # ------------------------------------------------------------------ inspect

    def _on_type_clicked(self, item: QListWidgetItem) -> None:
        type_id = item.data(Qt.UserRole)
        if type_id is not None:
            self.inspect_type(type_id)

    def inspect_type(self, type_id: str) -> None:
        self._controller.browse_type(type_id)
        self.refresh()
        self._select_row(type_id)

    def _select_row(self, type_id: str) -> None:
        for row in range(self._types.count()):
            item = self._types.item(row)
            if item.data(Qt.UserRole) == type_id:
                self._types.setCurrentRow(row)
                return
