"""Main window: menus, toolbar, status bar, board and side panels."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGridLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.actions import Action, BoardMove
from ..rules.compiler import compile_ruleset
from .board.scene import BoardRenderConfig, BoardScene
from .board.texture_cache import TextureCache
from .board.view import BoardView
from .controller import UIController
from .dialogs.error_dialog import show_error, show_info
from .dialogs.new_game_dialog import NewGameDialog
from .dialogs.preferences_dialog import PreferencesDialog
from .dialogs.promotion_dialog import PromotionDialog
from .panels.game_panel import GamePanel
from .panels.history_panel import HistoryPanel
from .panels.piece_panel import PiecePanel
from .panels.rules_panel import RulesPanel
from .settings import (
    KEY_BOARD_ORIENTATION,
    KEY_SHOW_COORDINATES,
    KEY_SHOW_HOVER,
    KEY_SHOW_LAST_MOVE,
    KEY_SHOW_LEGAL_MOVES,
    KEY_SHOW_SIDEBAR,
    KEY_SHOW_TOOLBAR,
    KEY_SPLITTER_STATE,
    KEY_TEXTURE_RATIO,
    KEY_WINDOW_GEOMETRY,
    SettingsStore,
)
from .shortcuts import SHORTCUTS
from .theme import default_theme


class MainWindow(QMainWindow):
    def __init__(
        self,
        controller: UIController,
        settings: SettingsStore,
        cache: TextureCache | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._settings = settings
        self._cache = cache or TextureCache()
        self._theme = default_theme()
        self._promotion_open = False
        self.setWindowTitle("GenericChess")

        controller.interaction.orientation_owner = int(
            settings.get(KEY_BOARD_ORIENTATION, 0)
        )

        self._scene = BoardScene(self._cache)
        self._board_view = BoardView(controller, self._scene)

        self._piece_panel = PiecePanel(controller, self._cache)
        self._game_panel = GamePanel(controller, self._cache, new_game_cb=self._new_game)
        self._history_panel = HistoryPanel(controller)
        self._rules_panel = RulesPanel(
            controller, self._cache, inspect_type_cb=self._piece_panel.show_type
        )
        self._tabs = QTabWidget()
        self._tabs.addTab(self._piece_panel, "Piece")
        self._tabs.addTab(self._game_panel, "Game")
        self._tabs.addTab(self._history_panel, "History")
        self._tabs.addTab(self._rules_panel, "Rules")

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._board_view)
        splitter.addWidget(self._tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)
        self._splitter = splitter

        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()
        controller.subscribe(self._refresh)
        self._restore_window_state()
        self._refresh()

    # ------------------------------------------------------------------ actions

    def _build_actions(self) -> None:
        self._act_new = self._action("New Game", "Ctrl+N", self._new_game)
        self._act_open_ruleset = self._action("Open RuleSet…", None, self._open_ruleset)
        self._act_open_record = self._action("Open Record…", "Ctrl+O", self._open_record)
        self._act_save_record = self._action("Save Record", "Ctrl+S", self._save_record)
        self._act_save_record_as = self._action(
            "Save Record As…", "Ctrl+Shift+S", self._save_record_as
        )
        self._act_export_ruleset = self._action("Export RuleSet…", None, self._export_ruleset)
        self._act_gallery = self._action("Export Texture Gallery…", None, self._texture_gallery)
        self._act_exit = self._action("Exit", "Ctrl+Q", self.close)

        self._act_undo = self._action("Undo", "Ctrl+Z", self._controller.undo)
        self._act_redo = self._action("Redo", "Ctrl+Y", self._controller.redo)
        self._act_restart = self._action("Restart", None, self._controller.restart)
        self._act_resign = self._action("Resign", None, self._resign)
        self._act_flip = self._action("Flip Board", "F", self._controller.flip_board)
        self._act_return = self._action(
            "Return to Current Position", None, self._controller.return_to_current
        )

        self._act_coords = self._check_action("Show Coordinates", True, self._refresh)
        self._act_legal = self._check_action("Show Legal Moves", True, self._refresh)
        self._act_lastmove = self._check_action("Show Last Move", True, self._refresh)
        self._act_sidebar = self._check_action("Show Side Panel", True, self._toggle_sidebar)
        self._act_toolbar = self._check_action("Show Toolbar", True, self._toggle_toolbar)
        self._act_zoom_in = self._action("Zoom In", "Ctrl+=", lambda: self._board_view.scale(1.2, 1.2))
        self._act_zoom_out = self._action("Zoom Out", "Ctrl+-", lambda: self._board_view.scale(1 / 1.2, 1 / 1.2))
        self._act_zoom_reset = self._action("Reset Zoom", "Ctrl+0", self._board_view.reset_zoom)
        self._act_fullscreen = self._action("Full Screen", "F11", self._toggle_fullscreen)

        self._act_prefs = self._action("Preferences…", "Ctrl+,", self._preferences)
        self._act_inspector = self._action("RuleSet Inspector", None, self._show_rules_tab)
        self._act_validate = self._action("Validate RuleSet…", None, self._validate_ruleset)
        self._act_shortcuts = self._action("Keyboard Shortcuts", None, self._show_shortcuts)
        self._act_about = self._action("About GenericChess", None, self._show_about)

    def _action(self, text: str, shortcut: str | None, slot) -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        return action

    def _check_action(self, text: str, checked: bool, slot) -> QAction:
        action = QAction(text, self)
        action.setCheckable(True)
        action.setChecked(checked)
        action.triggered.connect(slot)
        return action

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        for action in (
            self._act_new,
            self._act_open_ruleset,
            self._act_open_record,
            self._act_save_record,
            self._act_save_record_as,
            self._act_export_ruleset,
            self._act_gallery,
        ):
            file_menu.addAction(action)
        file_menu.addSeparator()
        file_menu.addAction(self._act_exit)

        game_menu = self.menuBar().addMenu("&Game")
        for action in (
            self._act_undo,
            self._act_redo,
            self._act_restart,
            self._act_resign,
            self._act_flip,
            self._act_return,
        ):
            game_menu.addAction(action)

        view_menu = self.menuBar().addMenu("&View")
        for action in (
            self._act_coords,
            self._act_legal,
            self._act_lastmove,
            self._act_sidebar,
            self._act_toolbar,
            self._act_zoom_in,
            self._act_zoom_out,
            self._act_zoom_reset,
            self._act_fullscreen,
        ):
            view_menu.addAction(action)

        tools_menu = self.menuBar().addMenu("&Tools")
        tools_menu.addAction(self._act_inspector)
        tools_menu.addAction(self._act_gallery)
        tools_menu.addAction(self._act_validate)
        tools_menu.addAction(self._act_prefs)

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self._act_shortcuts)
        help_menu.addAction(self._act_about)

    def _build_toolbar(self) -> None:
        bar = self.addToolBar("Main")
        bar.setObjectName("main_toolbar")
        for action in (
            self._act_new,
            self._act_open_ruleset,
            self._act_open_record,
            self._act_save_record,
            self._act_undo,
            self._act_redo,
            self._act_flip,
            self._act_resign,
            self._act_prefs,
        ):
            bar.addAction(action)
        self._toolbar = bar

    def _build_statusbar(self) -> None:
        self._status_main = QLabel("Ready")
        self.statusBar().addWidget(self._status_main, 1)

    # ------------------------------------------------------------------ refresh

    def _refresh(self) -> None:
        compiled = self._controller.compiled
        model = self._controller.board_view_model()
        if model is None or compiled is None:
            self._scene.clear()
            self._status_main.setText("No game loaded | Ready")
        else:
            config = BoardRenderConfig(
                theme=self._theme,
                texture_ratio=float(self._settings.get(KEY_TEXTURE_RATIO, 0.8)),
                show_coordinates=bool(self._settings.get(KEY_SHOW_COORDINATES, True))
                and self._act_coords.isChecked(),
                show_legal_moves=bool(self._settings.get(KEY_SHOW_LEGAL_MOVES, True))
                and self._act_legal.isChecked(),
                show_last_move=bool(self._settings.get(KEY_SHOW_LAST_MOVE, True))
                and self._act_lastmove.isChecked(),
            )
            self._scene.build(
                model,
                compiled,
                config,
                self._controller.interaction.orientation_owner,
            )
            self._status_main.setText(self._status_text())

        self._piece_panel.refresh()
        self._game_panel.refresh()
        self._history_panel.refresh()
        self._rules_panel.refresh()
        self._update_action_enabled()
        self._open_promotion_if_pending()
        QTimer.singleShot(0, self._board_view.fit_board)

    def _status_text(self) -> str:
        info = self._controller.game_info()
        interaction = self._controller.interaction
        if info is None:
            return "Ready"
        side = "White" if info.side_to_move == 0 else "Black"
        base = f"{side} to move | Ply {info.ply_count} | RuleSet {info.fingerprint_short}"
        if interaction.preview_piece_square is not None:
            base += (
                f" | Movement preview ({len(interaction.preview_squares)} squares) "
                f"| Not currently actionable"
            )
        elif interaction.selected_square is not None:
            base += f" | {len(interaction.legal_actions)} legal actions"
        if interaction.selected_hand_piece_type_id is not None:
            base += f" | drop {interaction.selected_hand_piece_type_id}: {len(interaction.legal_actions)} targets"
        base += " | " + ("Saved" if info.record_path else "Ready")
        if info.result.status.value != "ongoing":
            base += f" | {info.result}"
        return base

    def _update_action_enabled(self) -> None:
        has_game = self._controller.session is not None
        self._act_undo.setEnabled(has_game and self._controller.can_undo)
        self._act_redo.setEnabled(has_game and self._controller.can_redo)
        self._act_resign.setEnabled(has_game)
        self._act_return.setEnabled(
            self._controller.interaction.displayed_ply is not None
        )

    def _open_promotion_if_pending(self) -> None:
        pending = self._controller.interaction.pending_promotion_actions
        if not pending or self._promotion_open:
            return
        self._promotion_open = True
        try:
            info = self._controller.piece_info()
            owner = info.owner if info is not None else 0
            type_id = info.type_id if info is not None else None
            if type_id is None:
                return
            dialog = PromotionDialog(
                self._controller.compiled,
                self._cache,
                pending,
                type_id,
                owner,
                self,
            )
            if dialog.exec() == QDialog.Accepted and dialog.chosen() is not None:
                self._controller.choose_promotion(dialog.chosen())
            else:
                self._controller.cancel_promotion()
        finally:
            self._promotion_open = False

    # ------------------------------------------------------------------ slots

    def _new_game(self) -> None:
        dialog = NewGameDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        request = dialog.request()
        if request is None:
            return
        if request.mode == "generate":
            ok = self._controller.new_game(
                seed=request.seed,
                board_size=request.board_size,
                preset=request.preset,
                hybrid=request.hybrid,
            )
        else:
            ok = self._controller.open_ruleset(request.ruleset_path)
        if not ok:
            show_error(
                self,
                "New Game",
                f"Could not start the requested game:\n{self._controller.last_error}",
            )

    def _open_ruleset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open RuleSet", "", "JSON files (*.json)")
        if not path:
            return
        if not self._controller.open_ruleset(path):
            show_error(self, "Open RuleSet", self._controller.last_error)

    def _open_record(self) -> None:
        if self._controller.compiled is None:
            show_info(self, "Open Record", "Load a RuleSet first (File > Open RuleSet).")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open Record", "", "JSON files (*.json)")
        if not path:
            return
        if not self._controller.open_record(path):
            show_error(self, "Open Record", self._controller.last_error)

    def _save_record(self) -> None:
        if self._controller.session is None:
            return
        info = self._controller.game_info()
        if info is not None and info.record_path:
            self._save_to(info.record_path)
        else:
            self._save_record_as()

    def _save_record_as(self) -> None:
        if self._controller.session is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Record", "", "JSON files (*.json)")
        if path:
            self._save_to(path)

    def _save_to(self, path: str) -> None:
        if not self._controller.save_record(path):
            show_error(self, "Save Record", self._controller.last_error)

    def _export_ruleset(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export RuleSet", "", "JSON files (*.json)")
        if path and not self._controller.export_ruleset(path):
            show_error(self, "Export RuleSet", self._controller.last_error)

    def _resign(self) -> None:
        answer = QMessageBox.question(
            self, "Resign", "Resign as the current player?", QMessageBox.Yes | QMessageBox.No
        )
        if answer == QMessageBox.Yes:
            self._controller.resign()

    def _preferences(self) -> None:
        dialog = PreferencesDialog(self._settings, self)
        if dialog.exec() == QDialog.Accepted:
            self._refresh()

    def _validate_ruleset(self) -> None:
        ruleset = self._controller.ruleset
        if ruleset is None:
            show_info(self, "Validate RuleSet", "No RuleSet is loaded.")
            return
        try:
            compiled = compile_ruleset(ruleset)
        except ValueError as exc:
            show_error(self, "Validate RuleSet", f"RuleSet is invalid:\n{exc}", str(exc))
            return
        show_info(
            self,
            "Validate RuleSet",
            f"RuleSet is valid.\nFingerprint: {compiled.ruleset_fingerprint[:16]}…",
        )

    def _show_rules_tab(self) -> None:
        self._tabs.setCurrentWidget(self._rules_panel)

    def _texture_gallery(self) -> None:
        compiled = self._controller.compiled
        if compiled is None:
            show_info(self, "Texture Gallery", "Load a RuleSet first.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Texture Gallery")
        layout = QVBoxLayout(dialog)
        grid = QGridLayout()
        row = 0
        for owner in (0, 1):
            for pt in compiled.piece_types:
                pixmap = self._cache.pixmap(compiled, pt.type_id, owner, 64)
                label = QLabel()
                label.setPixmap(pixmap)
                label.setToolTip(f"{pt.type_id} owner {owner}")
                grid.addWidget(label, row, owner * 2)
                grid.addWidget(QLabel(f"{pt.type_id} P{owner}"), row, owner * 2 + 1)
                row += 1
        scroll = QScrollArea()
        content = QWidget()
        content.setLayout(grid)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        dialog.resize(420, 480)
        dialog.exec()

    def _show_shortcuts(self) -> None:
        lines = [f"{s.action}: {s.keys} — {s.description}" for s in SHORTCUTS]
        show_info(self, "Keyboard Shortcuts", "\n".join(lines))

    def _show_about(self) -> None:
        show_info(
            self,
            "About GenericChess",
            "GenericChess 0.3.0\nDeterministic generic chess/shogi-like engine "
            "with a PySide6 desktop UI.",
        )

    def _toggle_sidebar(self) -> None:
        self._tabs.setVisible(self._act_sidebar.isChecked())

    def _toggle_toolbar(self) -> None:
        self._toolbar.setVisible(self._act_toolbar.isChecked())

    def _toggle_fullscreen(self) -> None:
        self.showFullScreen() if not self.isFullScreen() else self.showNormal()

    # ------------------------------------------------------------------ persistence

    def _restore_window_state(self) -> None:
        geometry = self._settings.get(KEY_WINDOW_GEOMETRY)
        if geometry:
            self.restoreGeometry(geometry)
        splitter_state = self._settings.get(KEY_SPLITTER_STATE)
        if splitter_state:
            self._splitter.restoreState(splitter_state)
        self._tabs.setVisible(bool(self._settings.get(KEY_SHOW_SIDEBAR, True)))
        self._act_sidebar.setChecked(bool(self._settings.get(KEY_SHOW_SIDEBAR, True)))
        self._toolbar.setVisible(bool(self._settings.get(KEY_SHOW_TOOLBAR, True)))
        self._act_toolbar.setChecked(bool(self._settings.get(KEY_SHOW_TOOLBAR, True)))

    def closeEvent(self, event) -> None:
        self._settings.set(KEY_WINDOW_GEOMETRY, self.saveGeometry())
        self._settings.set(KEY_SPLITTER_STATE, self._splitter.saveState())
        self._settings.set(KEY_SHOW_SIDEBAR, self._act_sidebar.isChecked())
        self._settings.set(KEY_SHOW_TOOLBAR, self._act_toolbar.isChecked())
        super().closeEvent(event)
