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
from generic_chess.ui.settings import KEY_ENABLE_PREVIEW, KEY_SHOW_HOVER, KEY_TEXTURE_RATIO
from generic_chess.ui.stores import DictSettingsStore


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def _window(qapp, seed=42, board_size=8):
    ctrl = UIController(settings=DictSettingsStore())
    assert ctrl.new_game(seed=seed, board_size=board_size)
    win = MainWindow(ctrl, DictSettingsStore())
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
    assert "legal actions" in win._status_main.text()
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
    dialog = PreferencesDialog({})
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
    assert "Type:" in win._piece_panel._info.text()


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


def test_hand_stand_shows_empty_state(qapp):
    ctrl, win = _window(qapp)
    assert win._hand_bottom.is_empty_shown()
    assert win._hand_bottom.piece_buttons() == ()


def test_hand_stand_drop_flow(qapp):
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
    ctrl = UIController(settings=settings)
    assert ctrl.new_game_from_ruleset(ruleset)
    win = MainWindow(ctrl, settings)
    win.show()
    assert win._hand_bottom.is_empty_shown()

    ctrl.square_clicked(Square(1, 0))
    ctrl.square_clicked(Square(2, 0))  # capture -> hand
    win._refresh()
    buttons = win._hand_bottom.piece_buttons()
    assert not win._hand_bottom.is_empty_shown()
    assert buttons and "F" in buttons[0].text()

    # Player 1 moves so player 0 can drop.
    ctrl.square_clicked(Square(7, 7))
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    win._refresh()
    buttons = win._hand_bottom.piece_buttons()
    assert buttons and buttons[0].isEnabled()  # side to move can drop
    buttons[0].click()
    assert ctrl.interaction.selected_hand_piece_type_id == "F"
    assert ctrl.interaction.legal_actions
    target = ctrl.interaction.legal_actions[0].to_square
    ctrl.square_clicked(target)
    win._refresh()
    assert ctrl.session.state.position.hands[0].count("F") == 0
    assert win._hand_bottom.is_empty_shown()


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
    win._board_view.scale(1.5, 1.5)
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
    selected = win._history_panel._list.selectedItems()
    assert selected and selected[0].data(Qt.UserRole) == 1
    ctrl.return_to_current()
    win._refresh()
    selected = win._history_panel._list.selectedItems()
    assert selected and selected[0].data(Qt.UserRole) == 1  # back to live (last move)


def test_owner_mapping_ui_text(qapp):
    ctrl, win = _window(qapp)
    assert "White" in win._game_panel._status.text()
    model = ctrl.board_view_model()
    pawn = next(
        sv.square
        for sv in model.squares
        if sv.piece is not None and sv.piece.owner == 0 and sv.piece.base_type_id == "P"
    )
    ctrl.square_clicked(pawn)
    win._refresh()
    assert "White / Player 0 (先手)" in win._piece_panel._info.text()


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


def test_match_setup_dialog_values_and_persistence(qapp):
    from generic_chess.ai.budget import ThinkingStrategy
    from generic_chess.ui.dialogs.match_setup_dialog import MatchSetupDialog

    settings = DictSettingsStore()
    dialog = MatchSetupDialog(settings)
    dialog._side.setCurrentIndex(1)  # play black
    dialog._mode.setCurrentIndex(1)  # byoyomi
    dialog._main_seconds.setValue(120)
    dialog._overtime_seconds.setValue(15)
    dialog._strategy.setCurrentIndex(0)  # preset
    dialog._preset.setCurrentIndex(2)  # deep
    dialog._accept()
    match = dialog.match_config()
    assert match.participants[0].value == "ai"
    assert match.participants[1].value == "human"
    assert match.time_control.mode.value == "byoyomi"
    assert match.time_control.owner0.main_seconds == 120
    assert match.ai_config.strategy is ThinkingStrategy.FIXED_NODES
    dialog.persist_defaults()
    assert settings.get("match/human_owner") == 1
    assert settings.get("match/main_seconds") == 120


def test_main_window_ai_match_smoke(qapp):
    import time as _time

    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.budget import ThinkingConfig
    from generic_chess.clock import TimeControl, TimeControlMode
    from generic_chess.ui.match import MatchConfig, ParticipantKind

    settings = DictSettingsStore()
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
