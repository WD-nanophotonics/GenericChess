"""Promotion choice dialog driven by the backend legal-action set."""

from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ...core.actions import Action, BoardMove
from ..board.texture_cache import TextureCache
from ..i18n.manager import LocalizationManager


class PromotionDialog(QDialog):
    def __init__(
        self,
        compiled,
        cache: TextureCache,
        actions: tuple[Action, ...],
        piece_type_id: str,
        owner: int,
        parent=None,
        tr: LocalizationManager | None = None,
    ) -> None:
        super().__init__(parent)
        tr = tr or LocalizationManager("en")
        self.setWindowTitle(tr.text("promotion.title"))
        self._chosen: Action | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr.text("promotion.choose")))
        row = QHBoxLayout()
        for action in actions:
            label, pixmap = _option(compiled, cache, action, piece_type_id, owner, tr)
            btn = QPushButton()
            btn.setIcon(QIcon(pixmap))
            btn.setIconSize(pixmap.size())
            btn.setText(label)
            btn.clicked.connect(lambda _=False, a=action: self._pick(a))
            row.addWidget(btn)
        layout.addLayout(row)
        if row.count():
            row.itemAt(0).widget().setFocus()

    def _pick(self, action: Action) -> None:
        self._chosen = action
        self.accept()

    def chosen(self) -> Action | None:
        return self._chosen


def _option(
    compiled,
    cache: TextureCache,
    action: Action,
    piece_type_id: str,
    owner: int,
    tr: LocalizationManager | None = None,
):
    tr = tr or LocalizationManager("en")
    if isinstance(action, BoardMove) and action.promotion_target_id is not None:
        tid = action.promotion_target_id
        label = tr.text("promotion.promote_to", target=tid)
    else:
        tid = piece_type_id
        label = tr.text("promotion.none")
    pixmap = cache.pixmap(compiled, tid, owner, 64)
    return label, pixmap
