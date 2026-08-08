"""Headless Qt tests (QT_QPA_PLATFORM=offscreen)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.ui import adapters
from generic_chess.ui.board.texture_cache import TextureCache
from generic_chess.ui.controller import UIController
from generic_chess.ui.dialogs.preferences_dialog import PreferencesDialog
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.i18n.manager import LocalizationManager
from generic_chess.ui.settings import (
    KEY_AUTO_PROMOTE_UNIQUE,
    KEY_BOARD_ORIENTATION,
    KEY_ENABLE_PREVIEW,
    KEY_LANGUAGE,
    KEY_SHOW_COORDINATES,
    KEY_SHOW_DEV_STATUS,
    KEY_SHOW_HOVER,
    KEY_SHOW_LAST_MOVE,
    KEY_SHOW_LEGAL_MOVES,
    KEY_TEXTURE_RATIO,
    KEY_ZOOM_MODE,
)
from generic_chess.ui.stores import DictSettingsStore


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _qt_cleanup(qapp):
    """Deterministic per-test Qt teardown.

    Every widget created by the test is deterministically closed, shut down
    (MainWindow lifecycle: timer stop, subscriptions removed, AI thread
    cancelled/waited) and scheduled for deletion, then deferred deletes are
    flushed.  Without this, accumulated window object graphs are only freed
    by a later cyclic-GC batch, which can destroy Qt C++ objects while the
    event loop / AI thread is active (Windows access violation).
    """
    import time as _time
    import gc

    from PySide6.QtCore import QCoreApplication, QEvent

    baseline = set(qapp.topLevelWidgets())
    yield
    for widget in list(qapp.topLevelWidgets()):
        if widget in baseline:
            continue
        if isinstance(widget, MainWindow):
            if not widget._shutdown():
                # Worker still running after the bounded wait: wait
                # cooperatively, then require a completed shutdown before the
                # owning widget may be deleted.
                thread = widget._ai_thread
                deadline = _time.monotonic() + 5.0
                while (
                    thread is not None
                    and thread.isRunning()
                    and _time.monotonic() < deadline
                ):
                    qapp.processEvents()
                    _time.sleep(0.02)
                if thread is not None and thread.isRunning():
                    thread.requestInterruption()
                    thread.wait(3000)
                if thread is not None and thread.isRunning():
                    raise AssertionError(
                        "refusing to delete MainWindow while it still owns a "
                        f"running QThread after bounded shutdown wait: {widget!r}"
                    )
                if not widget._shutdown():
                    raise AssertionError(
                        f"MainWindow shutdown did not complete: {widget!r}"
                    )
        try:
            widget.close()
        except RuntimeError:
            pass
        try:
            widget.deleteLater()
        except RuntimeError:
            pass
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qapp.processEvents()
    # Collect wrapper cycles at an idle Qt point so a later batch cyclic-GC
    # cannot destroy Qt C++ objects while the event loop or AI thread runs.
    gc.collect()


def _window(qapp, seed=42, board_size=8):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    assert ctrl.new_game(seed=seed, board_size=board_size)
    win = MainWindow(ctrl, settings)
    win.show()
    return ctrl, win


def test_main_window_initializes_with_sample_game(qapp):
    ctrl, win = _window(qapp)
    assert "GenericChess" in win.windowTitle()
    assert len(win._scene.items()) > 0
    assert "to move" in win._status_main.text()


def test_board_size_and_flip_mapping(qapp):
    ctrl, win = _window(qapp, board_size=4)
    model = ctrl.board_view_model()
    assert model.board_size == 4
    scene = win._scene
    # logical origin maps to the bottom-left square; flip maps it to top-right.
    x0, y0 = scene.logical_to_scene(Square(0, 0))
    assert (x0, y0) == (0.0, 300.0)
    ctrl.flip_board()
    win._refresh()
    x1, y1 = scene.logical_to_scene(Square(0, 0))
    assert (x1, y1) == (300.0, 0.0)
    assert scene.scene_to_logical(x1, y1) == Square(0, 0)


def test_texture_cache_owner_distinct_and_cached(qapp):
    ctrl = _window(qapp)[0]
    compiled = ctrl.compiled
    cache = TextureCache()
    renderer_w = cache.renderer(compiled, "P", 0, 96)
    renderer_b = cache.renderer(compiled, "P", 1, 96)
    assert renderer_w is cache.renderer(compiled, "P", 0, 96)  # cached
    pm_w = cache.pixmap(compiled, "P", 0, 96)
    pm_b = cache.pixmap(compiled, "P", 1, 96)
    assert pm_w.toImage() != pm_b.toImage()


def test_click_flow_updates_scene_and_status(qapp):
    ctrl, win = _window(qapp)
    model = ctrl.board_view_model()
    pawn = next(
        sv.square
        for sv in model.squares
        if sv.piece is not None and sv.piece.owner == 0 and sv.piece.base_type_id == "P"
    )
    ctrl.square_clicked(pawn)
    assert ctrl.interaction.selected_square == pawn
    win._refresh()
    target = ctrl.interaction.legal_actions[0].to_square
    ctrl.square_clicked(target)
    win._refresh()
    assert ctrl.session.state.ply_count == 1
    assert len(win._scene.items()) > 0


def test_promotion_dialog_instantiates(qapp):
    from generic_chess.core.actions import BoardMove
    from generic_chess.core.movement import LeapAtom
    from generic_chess.ui.dialogs.promotion_dialog import PromotionDialog

    from conftest import king_type, make_compiled, T

    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    gold = T("G", LeapAtom((1, 0)))
    compiled = make_compiled(
        8,
        [king_type(), pawn, gold],
        auto_promotion=True,
        lines=[
            ".......k",
            "....P...",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K.......",
        ],
    )
    actions = (
        BoardMove(Square(4, 6), Square(4, 7), "G"),
        BoardMove(Square(4, 6), Square(4, 7)),
    )
    dialog = PromotionDialog(compiled, TextureCache(), actions, "P", 0)
    assert dialog.chosen() is None


def test_preferences_dialog_persists(qapp):
    settings = DictSettingsStore()
    dialog = PreferencesDialog({}, LocalizationManager("en"))
    values = dialog.values()
    assert KEY_TEXTURE_RATIO in values
    assert values[KEY_TEXTURE_RATIO] == 0.8  # default from empty initial


def test_view_menu_toggle_syncs_to_settings(qapp):
    settings = DictSettingsStore()
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    win._act_coords.setChecked(False)  # View menu toggle
    assert settings.get("board/coordinates", True) is False


def test_settings_restore_view_state_on_startup(qapp):
    settings = DictSettingsStore()
    settings.set("board/coordinates", False)
    settings.set("board/legal_moves", False)
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    assert win._act_coords.isChecked() is False
    assert win._act_legal.isChecked() is False


def test_piece_panel_shows_selected_piece(qapp):
    ctrl, win = _window(qapp)
    model = ctrl.board_view_model()
    pawn = next(
        sv.square
        for sv in model.squares
        if sv.piece is not None and sv.piece.owner == 0 and sv.piece.base_type_id == "P"
    )
    ctrl.square_clicked(pawn)
    win._refresh()
    type_id = ctrl.piece_info().type_id
    assert type_id in win._rules_panel._detail.text()


def test_ui_module_entry_smoke():
    import subprocess
    import sys

    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    proc = subprocess.run(
        [sys.executable, "-m", "generic_chess.ui", "--seed", "42", "--smoke"],
        capture_output=True,
        text=True,
        env=env,
        encoding="utf-8",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Traceback" not in proc.stderr


def test_run_ui_launcher_smoke():
    import subprocess
    import sys
    from pathlib import Path

    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    root = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, str(root / "run_ui.py"), "--smoke"],
        capture_output=True,
        text=True,
        env=env,
        encoding="utf-8",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Traceback" not in proc.stderr


def test_player_bar_shows_empty_hand(qapp):
    ctrl, win = _window(qapp)
    assert win._player_bars[0].is_hand_empty()
    assert win._player_bars[0].hand_buttons() == []


def test_player_bar_drop_flow(qapp):
    from conftest import king_type, make_ruleset, T

    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    filler = T("F", LeapAtom((1, 0)))
    ruleset = make_ruleset(
        8,
        [king_type(), rook, filler],
        lines=[
            ".......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "KRf.....",
        ],
    )
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    assert ctrl.new_game_from_ruleset(ruleset)
    win = MainWindow(ctrl, settings)
    win.show()
    assert win._player_bars[0].is_hand_empty()

    ctrl.square_clicked(Square(1, 0))
    ctrl.square_clicked(Square(2, 0))  # capture -> hand
    win._refresh()
    buttons = win._player_bars[0].hand_buttons()
    assert not win._player_bars[0].is_hand_empty()
    assert buttons and "F" in buttons[0].text()

    # Player 1 moves so player 0 can drop.
    ctrl.square_clicked(Square(7, 7))
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    win._refresh()
    buttons = win._player_bars[0].hand_buttons()
    assert buttons and buttons[0].isEnabled()  # side to move can drop
    buttons[0].click()
    assert ctrl.interaction.selected_hand_piece_type_id == "F"
    assert ctrl.interaction.legal_actions
    target = ctrl.interaction.legal_actions[0].to_square
    ctrl.square_clicked(target)
    win._refresh()
    assert ctrl.session.state.position.hands[0].count("F") == 0
    assert win._player_bars[0].is_hand_empty()


def test_board_view_mouse_tracking_enabled(qapp):
    _, win = _window(qapp)
    assert win._board_view.hasMouseTracking()
    assert win._board_view.viewport().hasMouseTracking()


def test_hover_preference_gates_scene_hover(qapp):
    ctrl, win = _window(qapp)
    win._scene.set_hover(Square(0, 0))
    assert win._scene._hover_item is not None
    win._settings.set(KEY_SHOW_HOVER, False)
    win._refresh()
    win._scene.set_hover(Square(0, 0))
    assert win._scene._hover_item is None


def test_manual_zoom_survives_refresh(qapp):
    _, win = _window(qapp)
    win._board_view.set_zoom_mode(True)
    win._board_view.zoom_in()
    before = win._board_view.transform()
    win._refresh()
    assert win._board_view.transform() == before  # refresh does not reset zoom
    win._board_view.reset_zoom()
    assert win._board_view.transform() != before


def test_history_preview_selects_same_ply(qapp):
    ctrl, win = _window(qapp)
    model = ctrl.board_view_model()
    pawn = next(
        sv.square
        for sv in model.squares
        if sv.piece is not None and sv.piece.owner == 0 and sv.piece.base_type_id == "P"
    )
    ctrl.square_clicked(pawn)
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    win._refresh()
    assert ctrl.display_ply(1)
    win._refresh()
    selected = win._moves_panel._list.selectedItems()
    assert selected and selected[0].data(Qt.UserRole) == 1
    ctrl.return_to_current()
    win._refresh()
    selected = win._moves_panel._list.selectedItems()
    assert selected and selected[0].data(Qt.UserRole) == 1  # back to live (last move)


def test_owner_mapping_ui_text(qapp):
    ctrl, win = _window(qapp)
    assert "White" in win._moves_panel._primary.text()
    model = ctrl.board_view_model()
    pawn = next(
        sv.square
        for sv in model.squares
        if sv.piece is not None and sv.piece.owner == 0 and sv.piece.base_type_id == "P"
    )
    ctrl.square_clicked(pawn)
    win._refresh()
    assert "Player 0" not in win._rules_panel._detail.text()
    type_id = ctrl.piece_info().type_id
    assert type_id in win._rules_panel._detail.text()


def test_texture_cache_style_dimension(qapp):
    from generic_chess.visual.texture_style import PieceTextureStyle

    ctrl = _window(qapp)[0]
    compiled = ctrl.compiled
    cache = TextureCache()
    style_a = PieceTextureStyle(white_fill="#ff0000")
    style_b = PieceTextureStyle(white_fill="#0000ff")
    pm_a = cache.pixmap(compiled, "P", 0, 64, style=style_a)
    pm_b = cache.pixmap(compiled, "P", 0, 64, style=style_b)
    assert pm_a.toImage() != pm_b.toImage()  # different styles never collide
    assert cache.pixmap(compiled, "P", 0, 64, style=style_a).toImage() == pm_a.toImage()


def test_new_match_dialog_values_and_persistence(qapp):
    from generic_chess.ai.budget import ThinkingStrategy
    from generic_chess.ui.dialogs.new_match_dialog import NewMatchDialog

    settings = DictSettingsStore()
    dialog = NewMatchDialog(settings)
    dialog._source.setCurrentIndex(1)  # generate
    dialog._side0.setCurrentIndex(0)  # side0 human
    dialog._side1.setCurrentIndex(1)  # side1 AI
    dialog._mode.setCurrentIndex(1)  # byoyomi
    dialog._main_seconds.setValue(120)
    dialog._overtime_seconds.setValue(15)
    dialog._strategy.setCurrentIndex(1)  # preset node budget
    dialog._preset_ai.setCurrentIndex(2)  # deep
    dialog._accept()
    request = dialog.request()
    assert request.ruleset_mode == "generate"
    assert request.participants[0].value == "human"
    assert request.participants[1].value == "ai"
    assert request.time_control.mode.value == "byoyomi"
    assert request.time_control.owner0.main_seconds == 120
    assert request.ai_config.strategy is ThinkingStrategy.FIXED_NODES
    dialog.persist_defaults()
    assert settings.get("match/side1") == 1
    assert settings.get("match/main_seconds") == 120


def test_new_match_dialog_auto_strategy_default(qapp):
    from generic_chess.ai.budget import ThinkingStrategy
    from generic_chess.ui.dialogs.new_match_dialog import NewMatchDialog
    from generic_chess.ui.match import ParticipantKind

    dialog = NewMatchDialog(DictSettingsStore())
    dialog._accept()
    request = dialog.request()
    assert request.ruleset_mode == "current"
    assert request.participants == (ParticipantKind.HUMAN, ParticipantKind.AI)
    assert request.ai_config.strategy is ThinkingStrategy.AUTO_TIME


def test_apply_new_match_starts_fresh(qapp):
    from generic_chess.ui.dialogs.new_match_dialog import NewMatchRequest
    from generic_chess.ui.match import MatchConfig, ParticipantKind

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    win.show()
    # Play a couple of moves so the position is not the initial one.
    ctrl.square_clicked(Square(1, 0))
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    assert ctrl.session.state.ply_count == 1
    request = NewMatchRequest(
        ruleset_mode="current",
        participants=(ParticipantKind.HUMAN, ParticipantKind.AI),
    )
    win._apply_new_match(request)
    assert ctrl.session.state.ply_count == 0  # fresh from the initial position
    assert ctrl.history_entries() == ()
    assert ctrl.match_active


def test_game_over_banner_shown(qapp):
    from generic_chess.ai.budget import ThinkingConfig
    from generic_chess.clock import TimeControl, TimeControlMode
    from generic_chess.ui.match import MatchConfig, ParticipantKind
    from test_ai_match import _mate_ruleset

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    ctrl.new_game_from_ruleset(_mate_ruleset())
    win = MainWindow(ctrl, DictSettingsStore())
    win.show()
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.HUMAN),
            TimeControl(mode=TimeControlMode.NONE),
            ThinkingConfig(),
        )
    )
    ctrl.submit_action(BoardMove(Square(1, 4), Square(0, 4)))  # mate in one
    win._refresh()
    assert "Game over" in win._moves_panel._primary.text()
    assert "to move" not in win._status_main.text()
    assert "White" not in win._moves_panel._primary.text()


def test_main_window_ai_match_smoke(qapp):
    import time as _time

    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.budget import ThinkingConfig
    from generic_chess.clock import TimeControl, TimeControlMode
    from generic_chess.ui.match import MatchConfig, ParticipantKind

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    win.show()
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.AI),
            TimeControl(mode=TimeControlMode.FISCHER),
            ThinkingConfig(strategy="fixed_nodes", preset="quick", max_nodes=500),
        )
    )
    win._ai_player = AlphaBetaPlayer(ctrl.compiled, use_disk_cache=False)
    ctrl.square_clicked(Square(1, 0))
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    win._refresh()
    deadline = _time.monotonic() + 30
    while _time.monotonic() < deadline:
        qapp.processEvents()
        if ctrl.session.state.ply_count == 2 and not ctrl.ai_thinking:
            break
        _time.sleep(0.02)
    assert ctrl.session.state.ply_count == 2
    assert "White" in win._clock_label.text()
    assert not win._act_stop_ai.isEnabled()


def test_clock_label_updates_on_tick(qapp):
    from generic_chess.ai.budget import ThinkingConfig
    from generic_chess.clock import TimeControl, TimeControlMode
    from generic_chess.ui.match import MatchConfig, ParticipantKind

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.AI),
            TimeControl(mode=TimeControlMode.BYOYOMI),
            ThinkingConfig(strategy="fixed_nodes", preset="quick"),
        )
    )
    win._clock_tick()
    assert "White" in win._clock_label.text()
    assert "Black" in win._clock_label.text()


def test_preferences_no_nameerror(qapp, monkeypatch):
    from PySide6.QtWidgets import QDialog

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    values = {
        KEY_TEXTURE_RATIO: 0.8,
        KEY_BOARD_ORIENTATION: 0,
        KEY_SHOW_COORDINATES: True,
        KEY_SHOW_LEGAL_MOVES: True,
        KEY_SHOW_LAST_MOVE: True,
        KEY_SHOW_HOVER: True,
        KEY_ENABLE_PREVIEW: True,
        KEY_AUTO_PROMOTE_UNIQUE: True,
        KEY_LANGUAGE: "en",
        KEY_ZOOM_MODE: False,
        KEY_SHOW_DEV_STATUS: False,
    }
    monkeypatch.setattr(PreferencesDialog, "exec", lambda self: QDialog.Accepted)
    monkeypatch.setattr(PreferencesDialog, "values", lambda self: values)
    win._preferences()  # must not raise NameError
    assert settings.get(KEY_ENABLE_PREVIEW, True) is True
    assert settings.get(KEY_AUTO_PROMOTE_UNIQUE, True) is True


def test_ai_worker_error_clears_thinking_and_stops_restart(qapp):
    import time as _time

    from generic_chess.ai.budget import ThinkingConfig, ThinkingStrategy
    from generic_chess.clock import TimeControl, TimeControlMode
    from generic_chess.ui.match import MatchConfig, ParticipantKind

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    win.show()
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.AI, ParticipantKind.HUMAN),
            TimeControl(mode=TimeControlMode.NONE),
            ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick"),
        )
    )

    class BoomPlayer:
        def choose_action(self, *args, **kwargs):
            raise RuntimeError("boom")

    win._ai_player = BoomPlayer()
    win._maybe_start_ai()
    assert ctrl.ai_thinking
    deadline = _time.monotonic() + 10
    while _time.monotonic() < deadline:
        qapp.processEvents()
        if not ctrl.ai_thinking and win._ai_thread is None:
            break
        _time.sleep(0.02)
    assert not ctrl.ai_thinking
    assert win._ai_thread is None
    assert "AI error" in win._status_main.text()
    assert ctrl.ai_stop_requested  # AI must not silently restart after an error


def test_new_match_dialog_requires_file_path(qapp, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from generic_chess.ui.dialogs.new_match_dialog import NewMatchDialog

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    dialog = NewMatchDialog(DictSettingsStore())
    dialog._source.setCurrentIndex(2)  # file mode without a chosen path
    dialog._accept()
    assert dialog.request() is None
    assert dialog.result() != 1  # not accepted


def test_apply_new_match_file_mode_requires_path(qapp, monkeypatch):
    from generic_chess.ai.budget import ThinkingConfig, ThinkingStrategy
    from generic_chess.clock import TimeControl, TimeControlMode
    from generic_chess.ui.dialogs.new_match_dialog import NewMatchRequest
    from generic_chess.ui.match import MatchConfig, ParticipantKind

    messages = []
    monkeypatch.setattr(
        "generic_chess.ui.main_window.show_error",
        lambda parent, title, text: messages.append(text),
    )
    settings = DictSettingsStore()
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    request = NewMatchRequest(
        ruleset_mode="file",
        ruleset_path=None,
        participants=(ParticipantKind.HUMAN, ParticipantKind.HUMAN),
        time_control=TimeControl(mode=TimeControlMode.NONE),
        ai_config=ThinkingConfig(strategy=ThinkingStrategy.AUTO_TIME),
    )
    win._apply_new_match(request)
    assert messages
    assert ctrl.session is not None
    assert ctrl.session.state.ply_count == 0


def test_restart_recreates_ai_player(qapp):
    from generic_chess.ai.budget import ThinkingConfig, ThinkingStrategy
    from generic_chess.clock import TimeControl, TimeControlMode
    from generic_chess.ui.match import MatchConfig, ParticipantKind

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.AI),
            TimeControl(mode=TimeControlMode.NONE),
            ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick"),
        )
    )
    win._ai_player = None
    win._restart()
    assert win._ai_player is not None
    assert ctrl.session.state.ply_count == 0


def test_cancel_ai_state_keeps_running_thread_reference(qapp):
    import time as _time

    from PySide6.QtCore import QThread

    class SlowThread(QThread):
        def run(self) -> None:
            while not self.isInterruptionRequested():
                _time.sleep(0.05)

    ctrl, win = _window(qapp)
    thread = SlowThread()
    thread.start()
    win._ai_thread = thread
    win._cancel_ai_state()
    assert win._ai_thread is thread  # still running -> reference kept
    assert thread.isRunning()
    thread.requestInterruption()
    thread.wait(5000)
    win._ai_thread = None


def test_open_ruleset_cancel_preserves_ai_player(qapp, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    settings = DictSettingsStore()
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    sentinel = object()
    win._ai_player = sentinel
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        staticmethod(lambda *a, **k: ("", "")),
    )
    win._open_ruleset()
    assert win._ai_player is sentinel  # cancel must not destroy the AI player


def test_open_record_cancel_preserves_ai_player(qapp, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    settings = DictSettingsStore()
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    sentinel = object()
    win._ai_player = sentinel
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        staticmethod(lambda *a, **k: ("", "")),
    )
    win._open_record()
    assert win._ai_player is sentinel


def test_close_waits_for_ai_thread_then_closes(qapp):
    import time as _time
    from types import SimpleNamespace

    from generic_chess.ai.budget import ThinkingConfig, ThinkingStrategy
    from generic_chess.clock import TimeControl, TimeControlMode
    from generic_chess.ui.match import MatchConfig, ParticipantKind

    class SlowPlayer:
        def choose_action(
            self, session, limits, cancel_token=None, progress_callback=None
        ):
            while cancel_token is None or not cancel_token.is_cancelled():
                _time.sleep(0.02)
            return SimpleNamespace(
                action=None,
                score=0,
                principal_variation=(),
                completed_depth=0,
                selective_depth=0,
                nodes=0,
                qnodes=0,
                elapsed_seconds=0.0,
                tt_probes=0,
                tt_hits=0,
                tt_cutoffs=0,
                beta_cutoffs=0,
                evaluation_profile_cache_hit=False,
                termination_reason="cancelled",
            )

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    win.show()
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.AI, ParticipantKind.HUMAN),
            TimeControl(mode=TimeControlMode.NONE),
            ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES, preset="quick"),
        )
    )
    win._ai_player = SlowPlayer()
    win._maybe_start_ai()
    assert ctrl.ai_thinking

    win.close()
    assert win.isVisible()  # closeEvent ignored while the AI thread runs
    assert win._closing_after_ai
    assert "Stopping AI" in win._status_main.text()

    deadline = _time.monotonic() + 10
    while _time.monotonic() < deadline and win.isVisible():
        qapp.processEvents()
        _time.sleep(0.02)
    assert not win.isVisible()  # closed after the worker finished
    assert not ctrl.ai_thinking
