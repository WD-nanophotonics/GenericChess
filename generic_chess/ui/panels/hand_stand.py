"""Hand stand (持ち駒台): a fixed, stable per-owner piece stand."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..adapters import owner_label
from ..board.texture_cache import TextureCache
from ..controller import UIController


class HandStandWidget(QFrame):
    """A bordered, always-visible hand area for one owner.

    The container and layout are fixed; ``refresh`` clears and rebuilds the
    piece buttons so items never accumulate or leak between states.  Pieces of
    the side to move are clickable (drop mode); the opponent's stand is
    view-only.  An explicit empty state is shown when the hand is empty.
    """

    def __init__(
        self,
        controller: UIController,
        cache: TextureCache,
        owner: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._cache = cache
        self._owner = owner
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName(f"hand_stand_{owner}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 4)
        self._title = QLabel()
        outer.addWidget(self._title)

        self._container = QWidget()
        outer.addWidget(self._container)
        self._row = QHBoxLayout(self._container)
        self._row.setContentsMargins(4, 2, 4, 2)
        self._buttons: list[QToolButton] = []
        self._empty_shown = False
        self._row.addStretch(1)
        self.refresh()

    def refresh(self) -> None:
        for button in self._buttons:
            button.deleteLater()
        self._buttons.clear()
        while self._row.count() > 1:  # keep the trailing stretch
            item = self._row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._title.setText(f"{owner_label(self._owner)} hand")

        info = self._controller.game_info()
        compiled = self._controller.compiled
        entries = info.hands[self._owner] if info is not None else ()
        session = self._controller.session
        side_to_move = (
            session.state.position.side_to_move
            if session is not None and session.result.status.value == "ongoing"
            else None
        )
        clickable = self._owner == side_to_move

        if not entries:
            self._empty_shown = True
            empty = QLabel("(no pieces in hand)")
            empty.setEnabled(False)
            self._row.insertWidget(0, empty)
            return
        self._empty_shown = False
        for entry in entries:
            pixmap = self._cache.pixmap(compiled, entry.type_id, self._owner, 40)
            button = QToolButton()
            button.setIcon(QIcon(pixmap))
            button.setIconSize(pixmap.size())
            button.setText(f"{entry.type_id} x{entry.count}")
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            button.setToolTip(f"drop {entry.type_id} ({entry.count} in hand)")
            button.setEnabled(clickable)
            if clickable:
                button.clicked.connect(
                    lambda _=False, tid=entry.type_id: self._controller.hand_piece_clicked(tid)
                )
            self._buttons.append(button)
            self._row.insertWidget(self._row.count() - 1, button)

    def set_owner(self, owner: int) -> None:
        """Switch which owner this stand displays (used when the board flips)."""
        if owner not in (0, 1):
            raise ValueError(f"owner must be 0 or 1, got {owner!r}")
        self._owner = owner
        self.refresh()

    def is_empty_shown(self) -> bool:
        return self._empty_shown

    def piece_buttons(self) -> tuple[QToolButton, ...]:
        return tuple(self._buttons)
