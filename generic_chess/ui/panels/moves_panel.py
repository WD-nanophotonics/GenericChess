"""Moves panel: game status, move list and replay controls (Game + History)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.actions import BoardMove, DropMove
from ...core.coordinates import square_to_index
from ...core.transition import initial_state
from ..controller import UIController
from ..i18n.manager import LocalizationManager


class MovesPanel(QWidget):
    """Unified game-overview + move history with ply replay."""

    def __init__(
        self,
        controller: UIController,
        tr: LocalizationManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._tr = tr

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._primary = QLabel()
        self._primary.setObjectName("moves_primary")
        self._primary.setWordWrap(True)
        layout.addWidget(self._primary)
        self._secondary = QLabel()
        self._secondary.setObjectName("moves_secondary")
        self._secondary.setWordWrap(True)
        layout.addWidget(self._secondary)

        layout.addSpacing(4)
        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list, 1)

        controls = QGridLayout()
        controls.setHorizontalSpacing(4)
        controls.setVerticalSpacing(4)
        for col, (key, slot) in enumerate(
            (
                ("moves.first", self._go_first),
                ("moves.prev", self._go_prev),
                ("moves.next", self._go_next),
                ("moves.last", self._go_last),
            )
        ):
            button = QPushButton(tr.text(key))
            button.clicked.connect(slot)
            controls.addWidget(button, 0, col)
            setattr(self, f"_btn_{key.split('.')[1]}", button)
        self._return_btn = QPushButton(tr.text("moves.return_live"))
        self._return_btn.clicked.connect(controller.return_to_current)
        controls.addWidget(self._return_btn, 1, 0, 1, 4)
        controls.setColumnStretch(3, 1)
        layout.addLayout(controls)

    # ------------------------------------------------------------------ state

    def refresh(self) -> None:
        tr = self._tr
        info = self._controller.game_info()
        displayed = self._controller.interaction.displayed_ply
        if info is None:
            self._primary.setText(tr.text("status.no_game"))
            self._secondary.clear()
            self._list.clear()
            self._update_controls(displayed, live=0)
            return

        self._render_status(info)
        self._render_moves(displayed)
        live_ply = info.ply_count
        self._update_controls(displayed, live=live_ply)

    def _render_status(self, info) -> None:
        tr = self._tr
        result = info.result
        status_value = result.status.value
        side = info.side_to_move
        name = tr.text("player.white" if side == 0 else "player.black")
        if status_value != "ongoing":
            self._primary.setText(tr.text("result.game_over"))
            secondary = self._result_line(result)
            if secondary:
                self._secondary.setText(secondary)
            else:
                self._secondary.setText(tr.text("moves.title"))
            return
        if self._controller.ai_thinking:
            self._primary.setText(tr.text("turn.thinking", player=name))
        else:
            self._primary.setText(tr.text("turn.to_move", player=name))
        self._secondary.setText(f"{tr.text('moves.title')} · {info.ply_count}")

    def _result_line(self, result) -> str:
        tr = self._tr
        status = result.status.value
        if status == "checkmate":
            winner_name = tr.text(
                "player.white" if result.winner == 0 else "player.black"
            )
            return f"{tr.text('result.checkmate')} · {tr.text('result.wins', player=winner_name)}"
        if status == "stalemate":
            return tr.text("result.stalemate") + " · " + tr.text("result.draw")
        if status == "repetition":
            return tr.text("result.repetition") + " · " + tr.text("result.draw")
        if status == "max_ply":
            return tr.text("result.max_ply") + " · " + tr.text("result.draw")
        if status == "resignation":
            loser = result.resigned_by
            loser_name = tr.text("player.white" if loser == 0 else "player.black")
            return tr.text("result.resigned", player=loser_name)
        return ""

    def _render_moves(self, displayed) -> None:
        tr = self._tr
        compiled = self._controller.compiled
        entries = self._controller.history_entries()
        self._list.clear()
        if not entries or compiled is None:
            if not entries:
                self._list.addItem(tr.text("moves.no_moves"))
            return
        labels = self._build_move_labels(entries, compiled)
        for entry, label in zip(entries, labels):
            owner_name = tr.text("player.white" if entry.player == 0 else "player.black")
            text = tr.text("move.prefix", number=entry.ply, owner=owner_name, move=label)
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, entry.ply)
            self._list.addItem(item)
        if self._list.count():
            target = displayed if displayed is not None else len(entries)
            index = max(0, min(target - 1, self._list.count() - 1))
            item = self._list.item(index)
            item.setSelected(True)
            self._list.scrollToItem(item)

    def _build_move_labels(self, entries, compiled):
        """Replay once from the initial state to label each ply."""
        tr = self._tr
        labels = []
        state = initial_state(compiled)
        n = compiled.board_size
        for entry in entries:
            action = entry.action
            if isinstance(action, DropMove):
                labels.append(
                    f"{action.base_type_id} {tr.text('move.drop', square=str(action.to_square))}"
                )
                from ...core.transition import apply_action

                state = apply_action(state, action, compiled)
                continue
            piece = state.position.board[square_to_index(action.from_square, n)]
            tid = piece.current_type_id if piece is not None else "?"
            occupied = state.position.board[square_to_index(action.to_square, n)]
            capture = occupied is not None
            if action.promotion_target_id is not None:
                text = tr.text(
                    "move.promotion",
                    **{"from": str(action.from_square), "to": str(action.to_square)},
                    target=action.promotion_target_id,
                )
            elif capture:
                text = tr.text(
                    "move.capture",
                    **{"from": str(action.from_square), "to": str(action.to_square)},
                )
            else:
                text = tr.text(
                    "move.plain",
                    **{"from": str(action.from_square), "to": str(action.to_square)},
                )
            labels.append(f"{tid} {text}")
            from ...core.transition import apply_action

            state = apply_action(state, action, compiled)
        return labels

    def _update_controls(self, displayed, live: int) -> None:
        viewing = displayed is not None
        self._return_btn.setEnabled(viewing)
        first = displayed is None or displayed <= 1
        last = displayed is None or live == 0 or displayed >= live
        self._btn_first.setEnabled(not first)
        self._btn_prev.setEnabled(not first)
        self._btn_next.setEnabled(not last and live > 0)
        self._btn_last.setEnabled(not last and live > 0)

    # ------------------------------------------------------------------ replay

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        ply = item.data(Qt.UserRole)
        if ply is not None:
            self._controller.display_ply(ply)

    def _go_first(self) -> None:
        self._controller.display_ply(0)

    def _go_prev(self) -> None:
        displayed = self._controller.interaction.displayed_ply
        target = (displayed - 1) if displayed is not None else (
            self._controller.game_info().ply_count - 1
        )
        self._controller.display_ply(max(0, target))

    def _go_next(self) -> None:
        displayed = self._controller.interaction.displayed_ply
        if displayed is None:
            return
        live = self._controller.game_info().ply_count
        self._controller.display_ply(min(live, displayed + 1))

    def _go_last(self) -> None:
        self._controller.return_to_current()
