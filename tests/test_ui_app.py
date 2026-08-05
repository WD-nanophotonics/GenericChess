"""Headless Qt tests (QT_QPA_PLATFORM=offscreen)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from generic_chess.ui.board.texture_cache import TextureCache
from generic_chess.ui.controller import UIController
from generic_chess.ui.dialogs.preferences_dialog import PreferencesDialog
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.settings import DictSettingsStore, KEY_TEXTURE_RATIO


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
    dialog = PreferencesDialog(settings)
    dialog._save()
    assert settings.contains(KEY_TEXTURE_RATIO)


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
