"""Game-over overlay drawn above the board without touching its transform."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..i18n.manager import LocalizationManager
from ..theme import Theme


class GameOverOverlay(QWidget):
    """Lightly translucent scrim with a centered result card.

    The overlay is a sibling *above* the ``BoardView`` (positioned by
    ``BoardWithOverlay``), so showing or hiding it never re-fits the board.
    """

    view_moves_requested = Signal()
    play_again_requested = Signal()
    dismiss_requested = Signal()

    def __init__(self, tr: LocalizationManager, theme: Theme, parent=None) -> None:
        super().__init__(parent)
        self._tr = tr
        self._theme = theme
        self.setObjectName("game_over_overlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch(1)

        self._card = QFrame()
        self._card.setObjectName("game_over_card")
        card = QVBoxLayout(self._card)
        card.setContentsMargins(24, 20, 24, 20)
        card.setSpacing(6)

        self._title = QLabel()
        self._title.setObjectName("overlay_title")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.addWidget(self._title)

        self._winner = QLabel()
        self._winner.setObjectName("overlay_winner")
        self._winner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.addWidget(self._winner)

        self._reason = QLabel()
        self._reason.setObjectName("overlay_reason")
        self._reason.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.addWidget(self._reason)

        card.addSpacing(8)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self._btn_view_moves = QPushButton()
        self._btn_view_moves.setObjectName("overlay_button")
        self._btn_view_moves.clicked.connect(self.view_moves_requested)
        buttons.addWidget(self._btn_view_moves)
        self._btn_play_again = QPushButton()
        self._btn_play_again.setObjectName("overlay_button")
        self._btn_play_again.clicked.connect(self.play_again_requested)
        buttons.addWidget(self._btn_play_again)
        self._btn_dismiss = QPushButton()
        self._btn_dismiss.setObjectName("overlay_button")
        self._btn_dismiss.clicked.connect(self.dismiss_requested)
        buttons.addWidget(self._btn_dismiss)
        card.addLayout(buttons)

        layout.addWidget(self._card, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        self._apply_style()
        self._retranslate()
        self.hide()

    # ------------------------------------------------------------------ state

    def show_game_over(self, winner_line: str, reason_line: str) -> None:
        self._winner.setText(winner_line)
        self._reason.setText(reason_line)
        self.show()
        self.raise_()

    def retranslate(self) -> None:
        self._retranslate()

    def _retranslate(self) -> None:
        self._title.setText(self._tr.text("overlay.game_over"))
        self._btn_view_moves.setText(self._tr.text("overlay.view_moves"))
        self._btn_play_again.setText(self._tr.text("overlay.play_again"))
        self._btn_dismiss.setText(self._tr.text("overlay.view_board"))

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self._apply_style()

    def _apply_style(self) -> None:
        t = self._theme
        self.setStyleSheet(
            f"""
            QFrame#game_over_card {{
                background: {t.overlay_card_bg};
                border-radius: 10px;
            }}
            QLabel#overlay_title {{
                color: {t.overlay_title};
                font-size: 16px;
                font-weight: bold;
            }}
            QLabel#overlay_winner {{
                color: {t.overlay_text};
                font-size: 13px;
                font-weight: bold;
            }}
            QLabel#overlay_reason {{
                color: {t.overlay_text};
                font-size: 11px;
            }}
            QPushButton#overlay_button {{
                background: {t.overlay_button_bg};
                color: {t.overlay_button_fg};
                border: none;
                border-radius: 4px;
                padding: 5px 12px;
            }}
            QPushButton#overlay_button:hover {{
                background: {t.selection_accent};
            }}
            """
        )

    # ------------------------------------------------------------------ paint

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        scrim = QColor(0, 0, 0)
        scrim.setAlpha(int(255 * self._theme.overlay_scrim_alpha))
        painter.fillRect(self.rect(), scrim)
        painter.end()


class BoardWithOverlay(QWidget):
    """Board column container keeping the overlay pinned to the viewport."""

    def __init__(
        self,
        board_view,
        overlay: GameOverOverlay,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._board_view = board_view
        self._overlay = overlay
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(board_view)
        overlay.setParent(self)
        overlay.raise_()
        self._sync_overlay()

    def board_view(self):
        return self._board_view

    def _sync_overlay(self) -> None:
        self._overlay.setGeometry(self.rect())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_overlay()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_overlay()
