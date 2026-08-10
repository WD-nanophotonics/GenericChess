"""PlayerBar: owner name, status, clock and compact clickable hand."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..board.texture_cache import TextureCache
from ..controller import UIController
from ..i18n.manager import LocalizationManager


class PlayerBar(QWidget):
    """One row per player: name, to-move/thinking marker, clock, compact hand."""

    def __init__(
        self,
        controller: UIController,
        cache: TextureCache,
        tr: LocalizationManager,
        owner: int,
        inspect_type_cb=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._cache = cache
        self._tr = tr
        self._owner = owner
        self._inspect_type = inspect_type_cb
        self.setObjectName(f"player_bar_{owner}")
        # The board column owns a fixed-height information rail.  Hand
        # contents and thinking text may change, but they must not steal a few
        # pixels from the board and trigger a new fit transform.
        self.setFixedHeight(46)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 2, 8, 2)
        outer.setSpacing(8)

        self._name = QLabel()
        self._name.setObjectName("player_name")
        outer.addWidget(self._name)

        self._marker = QLabel()
        self._marker.setObjectName("player_marker")
        outer.addWidget(self._marker)

        self._clock = QLabel()
        self._clock.setObjectName("player_clock")
        outer.addWidget(self._clock)

        outer.addSpacing(4)
        hand_label = QLabel()
        hand_label.setObjectName("player_hand_label")
        outer.addWidget(hand_label)

        self._hand = QWidget()
        self._hand_layout = QHBoxLayout(self._hand)
        self._hand_layout.setContentsMargins(0, 0, 0, 0)
        self._hand_layout.setSpacing(4)
        outer.addWidget(self._hand, 1)
        self._hand_label = hand_label

    def owner(self) -> int:
        return self._owner

    def hand_buttons(self):
        buttons = []
        for i in range(self._hand_layout.count()):
            widget = self._hand_layout.itemAt(i).widget()
            if isinstance(widget, QToolButton):
                buttons.append(widget)
        return buttons

    def is_hand_empty(self) -> bool:
        return not self.hand_buttons()

    def refresh(self) -> None:
        tr = self._tr
        name_key = "player.white" if self._owner == 0 else "player.black"
        order_key = "player.first" if self._owner == 0 else "player.second"
        self._name.setText(f"{tr.text(name_key)}（{tr.text(order_key)}）")

        info = self._controller.game_info()
        marker = ""
        marker_state = ""
        clock_text = ""
        if info is not None:
            side = info.side_to_move
            displayed = self._controller.interaction.displayed_ply
            is_live = displayed is None
            if self._owner == side and is_live and info.result.status.value == "ongoing":
                if self._controller.ai_thinking:
                    marker = tr.text("player.thinking")
                    marker_state = "thinking"
                else:
                    marker = tr.text("player.to_move")
                    marker_state = "active"
            clock_state = self._controller.clock_state()
            if clock_state is not None:
                total = clock_state.remaining_for(self._owner) / 1000.0
                if clock_state.running and clock_state.active_owner == self._owner:
                    total += clock_state.overtime_for(self._owner) / 1000.0
                minutes, seconds = divmod(int(total), 60)
                clock_text = f"{minutes:02d}:{seconds:02d}"
        self._marker.setText(marker)
        self._marker.setProperty("state", marker_state)
        self._marker.style().unpolish(self._marker)
        self._marker.style().polish(self._marker)
        self._clock.setText(clock_text)

        self._hand_label.setText(tr.text("player.hand") + "：")
        while self._hand_layout.count():
            item = self._hand_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        compiled = self._controller.compiled
        if info is None or compiled is None:
            self._add_hand_text(tr.text("player.hand_empty"))
            return
        entries = info.hands[self._owner]
        if not entries:
            self._add_hand_text(tr.text("player.hand_empty"))
            return
        selected = self._controller.interaction.selected_hand_piece_type_id
        actionable = (
            self._controller.interaction.displayed_ply is None
            and info.result.status.value == "ongoing"
            and info.side_to_move == self._owner
        )
        for entry in entries:
            button = QToolButton()
            pixmap = self._cache.pixmap(compiled, entry.type_id, self._owner, 24)
            button.setIcon(QIcon(pixmap))
            button.setText(f"{entry.type_id} ×{entry.count}")
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            button.setAutoRaise(True)
            button.setProperty("selected", actionable and entry.type_id == selected)
            button.setEnabled(actionable)
            button.clicked.connect(
                lambda _=False, tid=entry.type_id: self._on_hand_clicked(tid)
            )
            if self._inspect_type is not None:
                button.setContextMenuPolicy(Qt.CustomContextMenu)
                button.customContextMenuRequested.connect(
                    lambda _pos, tid=entry.type_id: self._on_hand_inspect(tid)
                )
            self._hand_layout.addWidget(button)
        self._hand_layout.addStretch(1)

    def _add_hand_text(self, text: str) -> None:
        label = QLabel(text)
        label.setObjectName("player_hand_empty")
        self._hand_layout.addWidget(label)
        self._hand_layout.addStretch(1)

    def _on_hand_clicked(self, type_id: str) -> None:
        self._controller.hand_piece_clicked(type_id)

    def _on_hand_inspect(self, type_id: str) -> None:
        if self._inspect_type is not None:
            self._inspect_type(type_id)
