"""Main window: menu bar, compact toolbar, PlayerBars, board and Moves|Rules sidebar."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..ai.alphabeta.player import AlphaBetaPlayer
from ..ai.cancellation import CancellationToken
from .board.scene import BoardRenderConfig, BoardScene
from .board.texture_cache import TextureCache
from .board.view import BoardView
from .controller import UIController
from .dialogs.diagnostics_dialog import DiagnosticsDialog
from .dialogs.error_dialog import show_error, show_info
from .dialogs.new_match_dialog import NewMatchDialog
from .dialogs.preferences_dialog import PreferencesDialog
from .dialogs.promotion_dialog import PromotionDialog
from .icons import toolbar_icon
from .i18n.manager import LocalizationManager, SUPPORTED_LANGUAGES
from .match import MatchConfig, ParticipantKind
from .panels.game_over_overlay import BoardWithOverlay, GameOverOverlay
from .panels.moves_panel import MovesPanel
from .panels.player_bar import PlayerBar
from .panels.rule_explorer import RuleExplorerPanel
from .settings import (
    KEY_AUTO_PROMOTE_UNIQUE,
    KEY_BOARD_ORIENTATION,
    KEY_ENABLE_PREVIEW,
    KEY_LANGUAGE,
    KEY_SHOW_COORDINATES,
    KEY_SHOW_DEV_STATUS,
    KEY_SHOW_HOVER,
    KEY_SHOW_LAST_MOVE,
    KEY_SHOW_LEGAL_MOVES,
    KEY_SHOW_SIDEBAR,
    KEY_SPLITTER_STATE,
    KEY_TEXTURE_RATIO,
    KEY_WINDOW_GEOMETRY,
    KEY_ZOOM_MODE,
    SettingsStore,
)
from .theme import default_theme


class _AiThread(QThread):
    finished_signal = Signal(object)
    progress_signal = Signal(int, int, int)
    error_signal = Signal(str)

    def __init__(self, player, snapshot, token) -> None:
        super().__init__()
        self._player = player
        self._snapshot = snapshot
        self._token = token

    def run(self) -> None:
        try:
            def progress(depth: int, nodes: int, qnodes: int) -> None:
                self.progress_signal.emit(depth, nodes, qnodes)

            decision = self._player.choose_action(
                self._snapshot.session,
                self._snapshot.limits,
                cancel_token=self._token,
                progress_callback=progress,
            )
        except Exception as exc:  # worker boundary: never crash the GUI thread
            self.error_signal.emit(f"{type(exc).__name__}: {exc}")
            self.finished_signal.emit(None)
            return
        self.finished_signal.emit(decision)


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
        self._tr = LocalizationManager(settings.get(KEY_LANGUAGE))
        self._promotion_open = False
        self._ai_error: str | None = None
        self._closing_after_ai = False
        self._shutting_down = False
        self._app_version = "0.7.0a1"
        self.setWindowTitle(self._tr.text("app.title"))

        controller.interaction.orientation_owner = int(
            settings.get(KEY_BOARD_ORIENTATION, 0)
        )

        self._scene = BoardScene(self._cache)
        self._board_view = BoardView(controller, self._scene)
        self._board_view.set_zoom_mode(bool(settings.get(KEY_ZOOM_MODE, False)))

        self._player_bars = {
            0: PlayerBar(
                controller, self._cache, self._tr, 0, inspect_type_cb=self._inspect_type
            ),
            1: PlayerBar(
                controller, self._cache, self._tr, 1, inspect_type_cb=self._inspect_type
            ),
        }
        self._moves_panel = MovesPanel(controller, self._tr)
        self._rules_panel = RuleExplorerPanel(
            controller, self._cache, self._tr, theme=self._theme
        )

        self._sidebar = QTabWidget()
        self._sidebar.setDocumentMode(True)
        self._sidebar.addTab(self._moves_panel, self._tr.text("tab.moves"))
        self._sidebar.addTab(self._rules_panel, self._tr.text("tab.rules"))

        self._board_column = QWidget()
        board_layout = QVBoxLayout(self._board_column)
        board_layout.setContentsMargins(0, 0, 0, 0)
        board_layout.setSpacing(2)
        self._bar_top = None
        self._bar_bottom = None
        self._overlay = GameOverOverlay(self._tr, self._theme)
        self._overlay.view_moves_requested.connect(self._overlay_view_moves)
        self._overlay.play_again_requested.connect(self._restart)
        self._overlay.dismiss_requested.connect(self._overlay.hide)
        self._board_container = BoardWithOverlay(self._board_view, self._overlay)
        board_layout.addWidget(self._player_bars[0])
        board_layout.addWidget(self._board_container, 1)
        board_layout.addWidget(self._player_bars[1])
        self._board_layout = board_layout
        self._place_player_bars(controller.interaction.orientation_owner)

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.addWidget(self._board_column)
        self._splitter.addWidget(self._sidebar)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([760, 380])
        self.setCentralWidget(self._splitter)

        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()
        self._clock_label = QLabel("")
        self.statusBar().addPermanentWidget(self._clock_label)
        self._ai_thread: _AiThread | None = None
        self._ai_player: AlphaBetaPlayer | None = None
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(100)
        self._clock_timer.timeout.connect(self._clock_tick)
        self._clock_timer.start()
        self._fit_timer = QTimer(self)
        self._fit_timer.setSingleShot(True)
        self._fit_timer.timeout.connect(self._board_view.fit_board)
        self._fit_timer.start(0)
        controller.subscribe(self._refresh)
        self._tr.subscribe(self._on_language_changed)
        self._restore_window_state()
        self._retranslate()
        self._refresh()

    # ------------------------------------------------------------------ layout

    def _place_player_bars(self, orientation: int) -> None:
        """Owner semantics never change; only the visual order follows orientation."""
        top_owner = 1 - orientation
        bottom_owner = orientation
        if self._bar_top is not None:
            self._board_layout.removeWidget(self._bar_top)
            self._board_layout.removeWidget(self._bar_bottom)
        self._bar_top = self._player_bars[top_owner]
        self._bar_bottom = self._player_bars[bottom_owner]
        self._board_layout.insertWidget(0, self._bar_top)
        self._board_layout.addWidget(self._bar_bottom)

    # ------------------------------------------------------------------ actions

    def _build_actions(self) -> None:
        self._act_new_match = self._action("menu.new_match", "Ctrl+N", self._new_match)
        self._act_open_ruleset = self._action(
            "menu.open_ruleset", None, self._open_ruleset
        )
        self._act_open_record = self._action(
            "menu.open_record", "Ctrl+O", self._open_record
        )
        self._act_save_record = self._action(
            "menu.save_record", "Ctrl+S", self._save_record
        )
        self._act_save_record_as = self._action(
            "menu.save_record_as", "Ctrl+Shift+S", self._save_record_as
        )
        self._act_exit = self._action("menu.exit", "Ctrl+Q", self.close)

        self._act_undo = self._action("menu.undo", "Ctrl+Z", self._controller.undo)
        self._act_redo = self._action("menu.redo", "Ctrl+Y", self._controller.redo)
        self._act_restart = self._action("menu.restart", None, self._restart)
        self._act_resign = self._action("menu.resign", None, self._resign)
        self._act_flip = self._action("menu.flip", "F", self._controller.flip_board)
        self._act_return = self._action(
            "menu.return_live", "Home", self._controller.return_to_current
        )
        self._act_stop_ai = self._action("menu.stop_ai", None, self._stop_ai)
        self._act_stop_ai.setEnabled(False)

        self._act_sidebar = self._check_action("menu.sidebar", True, self._toggle_sidebar)
        self._act_fit = self._action("menu.fit_window", None, self._board_view.fit_board)
        self._act_zoom_mode = self._check_action(
            "menu.zoom_mode", bool(self._settings.get(KEY_ZOOM_MODE, False)),
            self._toggle_zoom_mode,
        )
        self._act_zoom_in = self._action("menu.zoom_in", "Ctrl+=", self._board_view.zoom_in)
        self._act_zoom_out = self._action("menu.zoom_out", "Ctrl+-", self._board_view.zoom_out)
        self._act_zoom_reset = self._action("menu.reset_zoom", "Ctrl+0", self._board_view.reset_zoom)
        self._act_fullscreen = self._action("menu.fullscreen", "F11", self._toggle_fullscreen)

        self._act_rule_analysis = self._action(
            "menu.rule_analysis", None, self._show_rules_tab
        )
        self._act_diagnostics = self._action("menu.diagnostics", None, self._diagnostics)
        self._act_prefs = self._action("menu.preferences", "Ctrl+,", self._preferences)
        self._act_about = self._action("menu.about", None, self._show_about)

        self._act_coords = self._check_action("prefs.coordinates", True, self._refresh)
        self._act_legal = self._check_action("prefs.legal_moves", True, self._refresh)
        self._act_lastmove = self._check_action("prefs.last_move", True, self._refresh)
        self._act_coords.setObjectName("coords")
        self._act_legal.setObjectName("legal")
        self._act_lastmove.setObjectName("lastmove")
        for action in (self._act_coords, self._act_legal, self._act_lastmove):
            action.toggled.connect(self._persist_view_toggle)

    def _action(self, key: str, shortcut: str | None, slot) -> QAction:
        action = QAction(self._tr.text(key), self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        return action

    def _check_action(self, key: str, checked: bool, slot) -> QAction:
        action = QAction(self._tr.text(key), self)
        action.setCheckable(True)
        action.setChecked(checked)
        action.triggered.connect(slot)
        return action

    def _persist_view_toggle(self, checked: bool) -> None:
        action = self.sender()
        name = action.objectName() if action is not None else ""
        key = {
            "coords": KEY_SHOW_COORDINATES,
            "legal": KEY_SHOW_LEGAL_MOVES,
            "lastmove": KEY_SHOW_LAST_MOVE,
        }.get(name)
        if key is not None:
            self._settings.set(key, checked)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu(self._tr.text("menu.file"))
        for action in (
            self._act_new_match,
            self._act_open_ruleset,
            self._act_open_record,
            self._act_save_record,
            self._act_save_record_as,
        ):
            file_menu.addAction(action)
        file_menu.addSeparator()
        file_menu.addAction(self._act_exit)

        game_menu = self.menuBar().addMenu(self._tr.text("menu.game"))
        for action in (
            self._act_new_match,
            self._act_undo,
            self._act_redo,
            self._act_restart,
            self._act_resign,
            self._act_flip,
            self._act_return,
            self._act_stop_ai,
        ):
            game_menu.addAction(action)

        view_menu = self.menuBar().addMenu(self._tr.text("menu.view"))
        for action in (
            self._act_sidebar,
            self._act_fit,
            self._act_zoom_mode,
            self._act_zoom_in,
            self._act_zoom_out,
            self._act_zoom_reset,
            self._act_fullscreen,
        ):
            view_menu.addAction(action)

        tools_menu = self.menuBar().addMenu(self._tr.text("menu.tools"))
        tools_menu.addAction(self._act_rule_analysis)
        tools_menu.addAction(self._act_diagnostics)
        tools_menu.addAction(self._act_prefs)

        help_menu = self.menuBar().addMenu(self._tr.text("menu.help"))
        help_menu.addAction(self._act_about)

    def _build_toolbar(self) -> None:
        bar = QToolBar("Main", self)
        bar.setObjectName("main_toolbar")
        bar.setMovable(False)
        kinds = {
            "menu.new_match": "new",
            "menu.open_record": "open",
            "menu.save_record": "save",
            "menu.undo": "undo",
            "menu.redo": "redo",
            "menu.flip": "flip",
        }
        for key, action in (
            ("menu.new_match", self._act_new_match),
            ("menu.open_record", self._act_open_record),
            ("menu.save_record", self._act_save_record),
            ("menu.undo", self._act_undo),
            ("menu.redo", self._act_redo),
            ("menu.flip", self._act_flip),
        ):
            action.setIcon(toolbar_icon(kinds[key], self._theme))
            action.setToolTip(self._tr.text(f"toolbar.{key.split('.')[1]}"))
            bar.addAction(action)
        self._toolbar = bar
        self.addToolBar(bar)

    def _build_statusbar(self) -> None:
        self._status_main = QLabel(self._tr.text("status.ready"))
        self.statusBar().addWidget(self._status_main, 1)

    # ------------------------------------------------------------------ refresh

    def _refresh(self) -> None:
        compiled = self._controller.compiled
        model = self._controller.board_view_model()
        hover_enabled = bool(self._settings.get(KEY_SHOW_HOVER, True))
        self._board_view.set_hover_enabled(hover_enabled)
        self._place_player_bars(self._controller.interaction.orientation_owner)
        if model is None or compiled is None:
            self._scene.clear()
            self._board_view.set_board_size(None)
            self._status_main.setText(self._tr.text("status.no_game"))
        else:
            config = BoardRenderConfig(
                theme=self._theme,
                texture_ratio=float(self._settings.get(KEY_TEXTURE_RATIO, 0.8)),
                texture_style=self._theme.texture_style,
                show_coordinates=self._act_coords.isChecked(),
                show_legal_moves=self._act_legal.isChecked(),
                show_last_move=self._act_lastmove.isChecked(),
                show_hover=hover_enabled,
            )
            self._scene.build(
                model,
                compiled,
                config,
                self._controller.interaction.orientation_owner,
            )
            self._board_view.set_board_size(compiled.board_size)
            self._board_view.refresh_position()
            self._status_main.setText(self._status_text())
        for bar in self._player_bars.values():
            bar.refresh()
        self._moves_panel.refresh()
        self._rules_panel.refresh()
        self._update_overlay()
        self._update_action_enabled()
        self._open_promotion_if_pending()
        self._maybe_start_ai()

    def _overlay_view_moves(self) -> None:
        self._sidebar.setCurrentWidget(self._moves_panel)

    def _overlay_lines(self, info):
        tr = self._tr
        result = info.result
        status = result.status.value
        if status == "checkmate":
            winner = tr.text("player.white" if result.winner == 0 else "player.black")
            return tr.text("result.wins", player=winner), tr.text("result.checkmate")
        if status == "stalemate":
            return tr.text("result.draw"), tr.text("result.stalemate")
        if status == "repetition":
            return tr.text("result.draw"), tr.text("result.repetition")
        if status == "max_ply":
            return tr.text("result.draw"), tr.text("result.max_ply")
        if status == "resignation":
            loser = result.resigned_by
            winner = 1 - loser
            winner_name = tr.text("player.white" if winner == 0 else "player.black")
            loser_name = tr.text("player.white" if loser == 0 else "player.black")
            return (
                tr.text("result.wins", player=winner_name),
                tr.text("result.resigned", player=loser_name),
            )
        return "", ""

    def _update_overlay(self) -> None:
        info = self._controller.game_info()
        displayed = self._controller.interaction.displayed_ply
        if (
            info is None
            or displayed is not None
            or info.result.status.value == "ongoing"
        ):
            self._overlay.hide()
            return
        winner_line, reason_line = self._overlay_lines(info)
        if winner_line:
            self._overlay.show_game_over(winner_line, reason_line)
        else:
            self._overlay.hide()

    def _status_text(self) -> str:
        tr = self._tr
        info = self._controller.game_info()
        if info is None:
            return tr.text("status.ready")
        result_status = info.result.status.value
        if result_status != "ongoing":
            base = self._moves_panel._result_line(info.result)
        else:
            side = info.side_to_move
            name = tr.text("player.white" if side == 0 else "player.black")
            base = tr.text("turn.to_move", player=name)
        if self._controller.interaction.displayed_ply is not None:
            base += " · " + tr.text(
                "status.viewing_ply", ply=self._controller.interaction.displayed_ply
            )
        if self._controller.ai_thinking:
            base += " · " + tr.text("status.ai_thinking")
        if self._ai_error is not None:
            base += f" · {tr.text('status.ai_error')}: {self._ai_error}"
        if info.record_path:
            base += " · " + tr.text("status.saved")
        if self._settings.get(KEY_SHOW_DEV_STATUS, False):
            base += f" · fp {info.fingerprint_short} seed {info.seed}"
        return base

    def _update_action_enabled(self) -> None:
        has_game = self._controller.session is not None
        self._act_undo.setEnabled(has_game and self._controller.can_undo)
        self._act_redo.setEnabled(has_game and self._controller.can_redo)
        self._act_resign.setEnabled(has_game)
        self._act_stop_ai.setEnabled(self._controller.ai_thinking)
        self._act_return.setEnabled(
            self._controller.interaction.displayed_ply is not None
        )
        zoom_mode = self._board_view.zoom_mode_enabled()
        self._act_zoom_in.setEnabled(zoom_mode)
        self._act_zoom_out.setEnabled(zoom_mode)
        self._act_zoom_reset.setEnabled(zoom_mode)

    def _clock_tick(self) -> None:
        self._controller.clock_tick()
        state = self._controller.clock_state()
        if state is None:
            self._clock_label.setText("")
            return

        def fmt(owner: int) -> str:
            total = state.remaining_for(owner) / 1000.0
            if state.running and state.active_owner == owner:
                total += state.overtime_for(owner) / 1000.0
            minutes, seconds = divmod(int(total), 60)
            return f"{minutes:02d}:{seconds:02d}"

        marker = "▶" if state.running else "❚❚"
        white = self._tr.text("player.white")
        black = self._tr.text("player.black")
        text = f"{white} {fmt(0)} | {black} {fmt(1)} {marker}"
        if self._controller.timeout_owner is not None:
            text += f" | {self._tr.text('status.ai_timeout')}"
        self._clock_label.setText(text)

    # ------------------------------------------------------------------ language

    def _on_language_changed(self, _language: str) -> None:
        self._retranslate()
        self._refresh()

    def _retranslate(self) -> None:
        tr = self._tr
        self.setWindowTitle(tr.text("app.title"))
        self._sidebar.setTabText(0, tr.text("tab.moves"))
        self._sidebar.setTabText(1, tr.text("tab.rules"))
        for key, action in self._actions_by_key().items():
            action.setText(tr.text(key))
        for name, action in self._toolbar_actions().items():
            action.setToolTip(tr.text(f"toolbar.{name}"))
        self._toolbar.setWindowTitle("Main")
        self._overlay.retranslate()
        for bar in self._player_bars.values():
            bar.refresh()

    def _toolbar_actions(self) -> dict[str, QAction]:
        return {
            "new": self._act_new_match,
            "open": self._act_open_record,
            "save": self._act_save_record,
            "undo": self._act_undo,
            "redo": self._act_redo,
            "flip": self._act_flip,
        }

    def _actions_by_key(self) -> dict[str, QAction]:
        return {
            "menu.new_match": self._act_new_match,
            "menu.open_ruleset": self._act_open_ruleset,
            "menu.open_record": self._act_open_record,
            "menu.save_record": self._act_save_record,
            "menu.save_record_as": self._act_save_record_as,
            "menu.exit": self._act_exit,
            "menu.undo": self._act_undo,
            "menu.redo": self._act_redo,
            "menu.restart": self._act_restart,
            "menu.resign": self._act_resign,
            "menu.flip": self._act_flip,
            "menu.return_live": self._act_return,
            "menu.stop_ai": self._act_stop_ai,
            "menu.sidebar": self._act_sidebar,
            "menu.fit_window": self._act_fit,
            "menu.zoom_mode": self._act_zoom_mode,
            "menu.zoom_in": self._act_zoom_in,
            "menu.zoom_out": self._act_zoom_out,
            "menu.reset_zoom": self._act_zoom_reset,
            "menu.fullscreen": self._act_fullscreen,
            "menu.rule_analysis": self._act_rule_analysis,
            "menu.diagnostics": self._act_diagnostics,
            "menu.preferences": self._act_prefs,
            "menu.about": self._act_about,
            "prefs.coordinates": self._act_coords,
            "prefs.legal_moves": self._act_legal,
            "prefs.last_move": self._act_lastmove,
        }

    # ------------------------------------------------------------------ AI

    def _maybe_start_ai(self) -> None:
        if self._shutting_down or self._closing_after_ai:
            return
        if self._ai_thread is not None and self._ai_thread.isRunning():
            return
        if not self._controller.ai_move_needed() or self._ai_player is None:
            return
        self._ai_error = None
        token = CancellationToken()
        snapshot = self._controller.capture_ai_search(token)
        if snapshot is None:
            return
        thread = _AiThread(self._ai_player, snapshot, token)
        thread.progress_signal.connect(self._on_ai_progress)
        thread.finished_signal.connect(self._on_ai_finished)
        thread.error_signal.connect(self._on_ai_error)
        self._ai_thread = thread
        thread.start()
        self._update_action_enabled()

    def _on_ai_progress(self, depth: int, nodes: int, qnodes: int) -> None:
        self._status_main.setText(
            f"{self._tr.text('status.ai_thinking')} · depth {depth} · {nodes:,} nodes"
        )

    def _on_ai_finished(self, _decision) -> None:
        thread = self.sender()
        if thread is not self._ai_thread:
            if thread is not None:
                thread.deleteLater()
            return
        self._ai_thread = None
        if thread is not None:
            thread.deleteLater()
        snapshot = getattr(thread, "_snapshot", None)
        self._controller.finish_ai_move(_decision, snapshot)
        if self._closing_after_ai:
            self.close()
            return
        self._refresh()
        if not self._controller.ai_stop_requested:
            self._maybe_start_ai()

    def _on_ai_error(self, message: str) -> None:
        self._controller.cancel_ai()
        self._ai_error = message
        self._refresh()

    def _stop_ai(self) -> None:
        if self._controller.ai_thinking:
            self._controller.cancel_ai()
        else:
            self._controller.clear_stop_request()
            self._maybe_start_ai()

    def _cancel_ai_state(self) -> bool:
        """Request AI cancellation, wait briefly, and clear owned references
        only when the owned AI thread has actually finished.

        Returns ``True`` when no running owned AI thread remains (references
        are cleared).  Returns ``False`` when the thread is still running
        after the bounded wait: the ``_ai_thread`` reference is then
        retained, the thread is never ``deleteLater``-ed, and the owning
        window must not be deleted until the worker exits.
        """
        self._controller.cancel_ai()
        self._controller.clear_stop_request()
        thread = self._ai_thread
        if thread is not None and thread.isRunning():
            thread.wait(2000)
            if thread.isRunning():
                self._ai_player = None
                return False
        self._ai_thread = None
        self._ai_player = None
        return True

    def _shutdown(self) -> bool:
        """Deterministic, idempotent shutdown of window-owned lifecycle.

        Stops timers, blocks new AI work, cancels/waits for the owned AI
        thread and removes controller/localization subscriptions so the
        Python object graph is collectable without racing Qt destruction.

        Returns ``True`` when shutdown completed (no owned running AI
        thread; ``_ai_thread`` is cleared).  Returns ``False`` when the AI
        worker is still running after the bounded wait: its reference stays
        owned and the window must not be deleted.
        """
        if self._shutting_down:
            return self._cancel_ai_state()
        self._shutting_down = True
        if self._clock_timer.isActive():
            self._clock_timer.stop()
        if self._fit_timer.isActive():
            self._fit_timer.stop()
        self._controller.unsubscribe(self._refresh)
        self._tr.unsubscribe(self._on_language_changed)
        return self._cancel_ai_state()

    # ------------------------------------------------------------------ dialogs

    def _new_match(self) -> None:
        dialog = NewMatchDialog(self._settings, self)
        if dialog.exec() != QDialog.Accepted:
            return
        dialog.persist_defaults()
        request = dialog.request()
        if request is None:
            return
        if request.ruleset_mode == "current" and self._controller.compiled is None:
            show_info(self, self._tr.text("dialog.new_match"), self._tr.text("dialog.load_ruleset_first"))
            return
        self._apply_new_match(request)

    def _apply_new_match(self, request) -> None:
        self._cancel_ai_state()
        self._ai_error = None
        if request.ruleset_mode == "generate":
            ok = self._controller.new_game(
                seed=request.seed,
                board_size=request.board_size,
                preset=request.preset,
                hybrid=request.hybrid,
            )
        elif request.ruleset_mode == "file":
            if not request.ruleset_path:
                show_error(self, self._tr.text("dialog.new_match"), self._tr.text("dialog.new_match_error"))
                return
            ok = self._controller.open_ruleset(request.ruleset_path)
        else:
            self._controller.restart()
            ok = self._controller.session is not None
        if not ok:
            show_error(
                self,
                self._tr.text("dialog.new_match"),
                f"{self._tr.text('dialog.new_match_error')}:\n{self._controller.last_error}",
            )
            return
        self._controller.start_match(
            MatchConfig(
                participants=request.participants,
                time_control=request.time_control,
                ai_config=request.ai_config,
            )
        )
        self._ai_player = AlphaBetaPlayer(self._controller.compiled, use_disk_cache=True)
        self._board_view.fit_board()
        self._refresh()
        self._maybe_start_ai()

    def _open_ruleset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "", "", "JSON files (*.json)")
        if not path:
            return
        self._cancel_ai_state()
        if not self._controller.open_ruleset(path):
            show_error(self, "", self._controller.last_error)
            return
        self._board_view.fit_board()

    def _open_record(self) -> None:
        if self._controller.compiled is None:
            show_info(self, "", self._tr.text("dialog.load_ruleset_first"))
            return
        path, _ = QFileDialog.getOpenFileName(self, "", "", "JSON files (*.json)")
        if not path:
            return
        self._cancel_ai_state()
        if not self._controller.open_record(path):
            show_error(self, "", self._controller.last_error)
            return
        self._board_view.fit_board()

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
        path, _ = QFileDialog.getSaveFileName(self, "", "", "JSON files (*.json)")
        if path:
            self._save_to(path)

    def _save_to(self, path: str) -> None:
        if not self._controller.save_record(path):
            show_error(self, "", self._controller.last_error)

    def _resign(self) -> None:
        answer = QMessageBox.question(
            self,
            self._tr.text("menu.resign"),
            self._tr.text("dialog.resign_question"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self._controller.resign()

    def _restart(self) -> None:
        self._cancel_ai_state()
        self._controller.restart()
        match = self._controller.match_config
        if match is not None and any(
            p is ParticipantKind.AI for p in match.participants
        ):
            self._ai_player = AlphaBetaPlayer(
                self._controller.compiled, use_disk_cache=True
            )
        self._board_view.fit_board()
        self._maybe_start_ai()

    def _diagnostics(self) -> None:
        dialog = DiagnosticsDialog(self._controller, self._tr, self._app_version, self)
        dialog.exec()

    def _preferences(self) -> None:
        initial = {
            KEY_TEXTURE_RATIO: float(self._settings.get(KEY_TEXTURE_RATIO, 0.8)),
            KEY_BOARD_ORIENTATION: self._controller.interaction.orientation_owner,
            KEY_LANGUAGE: self._tr.language,
            KEY_SHOW_COORDINATES: self._act_coords.isChecked(),
            KEY_SHOW_LEGAL_MOVES: self._act_legal.isChecked(),
            KEY_SHOW_LAST_MOVE: self._act_lastmove.isChecked(),
            KEY_SHOW_HOVER: bool(self._settings.get(KEY_SHOW_HOVER, True)),
            KEY_ENABLE_PREVIEW: bool(self._settings.get(KEY_ENABLE_PREVIEW, True)),
            KEY_AUTO_PROMOTE_UNIQUE: bool(
                self._settings.get(KEY_AUTO_PROMOTE_UNIQUE, True)
            ),
            KEY_ZOOM_MODE: self._act_zoom_mode.isChecked(),
            KEY_SHOW_DEV_STATUS: bool(self._settings.get(KEY_SHOW_DEV_STATUS, False)),
        }
        dialog = PreferencesDialog(initial, self._tr, self)
        if dialog.exec() != QDialog.Accepted:
            return
        values = dialog.values()
        for key, value in values.items():
            self._settings.set(key, value)
        self._act_coords.setChecked(values[KEY_SHOW_COORDINATES])
        self._act_legal.setChecked(values[KEY_SHOW_LEGAL_MOVES])
        self._act_lastmove.setChecked(values[KEY_SHOW_LAST_MOVE])
        self._act_zoom_mode.setChecked(values[KEY_ZOOM_MODE])
        self._board_view.set_zoom_mode(values[KEY_ZOOM_MODE])
        if values[KEY_BOARD_ORIENTATION] != self._controller.interaction.orientation_owner:
            self._controller.set_orientation(values[KEY_BOARD_ORIENTATION])
        if values[KEY_LANGUAGE] != self._tr.language:
            self._settings.set(KEY_LANGUAGE, values[KEY_LANGUAGE])
            self._tr.set_language(values[KEY_LANGUAGE])
        self._refresh()

    def _show_rules_tab(self) -> None:
        self._sidebar.setCurrentWidget(self._rules_panel)

    def _inspect_type(self, type_id: str) -> None:
        self._rules_panel.inspect_type(type_id)
        self._sidebar.setCurrentWidget(self._rules_panel)

    def _show_about(self) -> None:
        show_info(
            self,
            self._tr.text("dialog.about"),
            self._tr.text("dialog.about_text", version=self._app_version),
        )

    def _toggle_sidebar(self) -> None:
        self._sidebar.setVisible(self._act_sidebar.isChecked())

    def _toggle_zoom_mode(self) -> None:
        enabled = self._act_zoom_mode.isChecked()
        self._settings.set(KEY_ZOOM_MODE, enabled)
        self._board_view.set_zoom_mode(enabled)
        self._update_action_enabled()

    def _toggle_fullscreen(self) -> None:
        self.showFullScreen() if not self.isFullScreen() else self.showNormal()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            if self._board_view.zoom_mode_enabled():
                self._act_zoom_mode.setChecked(False)
                self._toggle_zoom_mode()
            elif self._controller.interaction.displayed_ply is not None:
                self._controller.return_to_current()
            else:
                self._controller.cancel()
            event.accept()
            return
        super().keyPressEvent(event)

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

    # ------------------------------------------------------------------ persistence

    def _restore_window_state(self) -> None:
        geometry = self._settings.get(KEY_WINDOW_GEOMETRY)
        if geometry:
            self.restoreGeometry(geometry)
        splitter_state = self._settings.get(KEY_SPLITTER_STATE)
        if splitter_state:
            self._splitter.restoreState(splitter_state)
        self._sidebar.setVisible(bool(self._settings.get(KEY_SHOW_SIDEBAR, True)))
        self._act_sidebar.setChecked(bool(self._settings.get(KEY_SHOW_SIDEBAR, True)))
        self._act_coords.setChecked(bool(self._settings.get(KEY_SHOW_COORDINATES, True)))
        self._act_legal.setChecked(bool(self._settings.get(KEY_SHOW_LEGAL_MOVES, True)))
        self._act_lastmove.setChecked(bool(self._settings.get(KEY_SHOW_LAST_MOVE, True)))

    def _save_window_state(self) -> None:
        self._settings.set(KEY_WINDOW_GEOMETRY, self.saveGeometry())
        self._settings.set(KEY_SPLITTER_STATE, self._splitter.saveState())
        self._settings.set(KEY_SHOW_SIDEBAR, self._act_sidebar.isChecked())

    def closeEvent(self, event) -> None:
        if self._ai_thread is not None and self._ai_thread.isRunning():
            self._controller.cancel_ai()
            self._closing_after_ai = True
            self._status_main.setText(self._tr.text("dialog.stop_ai"))
            event.ignore()
            return
        if not self._shutdown():
            # A worker is still running after the bounded wait: keep the
            # window alive and owned; close again once it finishes.
            self._closing_after_ai = True
            self._status_main.setText(self._tr.text("dialog.stop_ai"))
            event.ignore()
            return
        self._save_window_state()
        super().closeEvent(event)
