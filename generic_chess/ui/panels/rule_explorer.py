"""Rule explorer: RuleSet overview, piece-type list/detail and entity info."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
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


class RuleExplorerPanel(QWidget):
    """Master-detail rules browser with live entity inspection."""

    def __init__(
        self,
        controller: UIController,
        cache: TextureCache,
        tr: LocalizationManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._cache = cache
        self._tr = tr
        self._expanded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._entity = QLabel()
        self._entity.setStyleSheet(
            "background: #eef3f8; border: 1px solid #b8cfe0; "
            "border-radius: 4px; padding: 4px;"
        )
        self._entity.setWordWrap(True)
        self._entity.hide()
        layout.addWidget(self._entity)

        self._overview = QLabel()
        self._overview.setWordWrap(True)
        layout.addWidget(self._overview)

        layout.addSpacing(4)
        self._types = QListWidget()
        self._types.itemClicked.connect(self._on_type_clicked)
        layout.addWidget(self._types, 1)

        self._detail = QLabel()
        self._detail.setWordWrap(True)
        layout.addWidget(self._detail)

        self._detail_image = QLabel()
        self._detail_image.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._detail_image)

        self._tech_button = QToolButton()
        self._tech_button.setCheckable(True)
        self._tech_button.clicked.connect(self._toggle_technical)
        layout.addWidget(self._tech_button)
        self._table = QTableWidget(0, 3)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.hide()
        layout.addWidget(self._table)

    # ------------------------------------------------------------------ state

    def refresh(self) -> None:
        tr = self._tr
        compiled = self._controller.compiled
        self._types.clear()
        if compiled is None:
            self._overview.setText(tr.text("rules.no_rules"))
            self._entity.hide()
            self._detail.setText(tr.text("rules.select_type"))
            self._detail_image.clear()
            self._tech_button.hide()
            self._table.hide()
            return
        self._render_overview(compiled)
        self._render_type_list(compiled)
        self._render_entity()
        self._render_detail()
        self._tech_button.setText(tr.text("rules.technical_details"))
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

    def _render_entity(self) -> None:
        tr = self._tr
        info = self._controller.piece_info()
        if info is None or info.owner is None or info.square is None:
            self._entity.hide()
            return
        owner_name = tr.text("player.white" if info.owner == 0 else "player.black")
        status = (
            tr.text("rules.promoted") if info.promoted else tr.text("rules.not_promoted")
        )
        self._entity.setText(
            f"<b>{tr.text('rules.current_selection')}:</b> {owner_name} {info.type_id} · "
            f"{tr.text('rules.position')}: {info.square} · {tr.text('rules.status')}: {status}"
        )
        self._entity.show()

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
            self._table.setRowCount(0)
            return
        pt = compiled.types_by_id[type_id]
        owner = info.owner if info is not None else None
        pixmap = self._cache.pixmap(compiled, type_id, owner if owner is not None else 0, 64)
        self._detail_image.setPixmap(pixmap)
        movement = localized_movement(pt, tr)
        flags = []
        if pt.is_anchor:
            flags.append(tr.text("rules.anchor"))
        if pt.is_promotable:
            targets = "、".join(pt.promotion_target_ids)
            flags.append(f"{tr.text('rules.promotion_targets')}: {targets}")
        if pt.type_id in compiled.drop_allowed:
            mask = compiled.drop_allowed[pt.type_id][0]
            restricted = any(not ok for ok in mask)
            flags.append(
                tr.text("rules.drop_forbidden")
                if restricted
                else tr.text("rules.droppable")
            )
        if flags:
            self._detail.setText(
                "<br>".join([f"• {m}" for m in movement] + flags)
            )
        else:
            self._detail.setText("<br>".join(f"• {m}" for m in movement))
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
