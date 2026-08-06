"""Desktop UI redesign acceptance: board stability, architecture, replay,
inspect, localization and PlayerBar behavior."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from generic_chess.ui.controller import UIController
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.settings import (
    KEY_LANGUAGE,
    KEY_SHOW_DEV_STATUS,
    KEY_ZOOM_MODE,
)
from generic_chess.ui.stores import DictSettingsStore


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def _window(qapp, seed=42, board_size=8, language="en"):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, language)
    ctrl = UIController(settings=settings)
    assert ctrl.new_game(seed=seed, board_size=board_size)
    win = MainWindow(ctrl, settings)
    win.show()
    return ctrl, win


def _first_pawn_square(ctrl):
    model = ctrl.board_view_model()
    return next(
        sv.square
        for sv in model.squares
        if sv.piece is not None and sv.piece.owner == 0 and sv.piece.base_type_id == "P"
    )


def _mate_setup(qapp):
    from test_ai_match import _mate_ruleset

    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    ctrl.new_game_from_ruleset(_mate_ruleset())
    win = MainWindow(ctrl, settings)
    win.show()
    return ctrl, win


# --------------------------------------------------------------- board stability

def test_board_transform_stable_across_refresh_and_moves(qapp):
    ctrl, win = _window(qapp)
    win._refresh()
    before = win._board_view.transform()
    win._refresh()
    assert win._board_view.transform() == before

    pawn = _first_pawn_square(ctrl)
    ctrl.square_clicked(pawn)
    win._refresh()
    assert win._board_view.transform() == before  # selection does not resize
    target = ctrl.interaction.legal_actions[0].to_square
    ctrl.square_clicked(target)
    win._refresh()
    assert win._board_view.transform() == before  # a move does not resize

    win._sidebar.setCurrentIndex(1)  # tab switch
    win._refresh()
    assert win._board_view.transform() == before

    win._clock_tick()
    assert win._board_view.transform() == before


def test_replay_does_not_resize_board(qapp):
    ctrl, win = _window(qapp)
    pawn = _first_pawn_square(ctrl)
    ctrl.square_clicked(pawn)
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    win._refresh()
    before = win._board_view.transform()
    assert ctrl.display_ply(1)
    win._refresh()
    assert win._board_view.transform() == before
    ctrl.return_to_current()
    win._refresh()
    assert win._board_view.transform() == before


def test_resize_updates_fit_transform(qapp):
    ctrl, win = _window(qapp)
    win.resize(900, 700)
    win._refresh()
    small = win._board_view.transform().m11()
    win.resize(600, 500)
    win._refresh()
    larger_scale = win._board_view.transform().m11()
    assert larger_scale < small  # smaller viewport -> smaller scale


def test_zoom_gated_by_zoom_mode(qapp):
    _, win = _window(qapp)
    assert not win._board_view.zoom_mode_enabled()
    before = win._board_view.transform()
    win._board_view.zoom_in()
    win._board_view.zoom_out()
    assert win._board_view.transform() == before  # wheel/zoom no-op by default

    win._act_zoom_mode.setChecked(True)
    win._toggle_zoom_mode()
    assert win._board_view.zoom_mode_enabled()
    win._board_view.zoom_in()
    assert win._board_view.transform() != before
    win._board_view.reset_zoom()
    assert win._board_view.transform() == before


def test_zoom_mode_default_from_settings(qapp):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    settings.set(KEY_ZOOM_MODE, True)
    ctrl = UIController(settings=settings)
    ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    assert win._board_view.zoom_mode_enabled()


# ------------------------------------------------------------- info architecture

def test_sidebar_has_only_moves_and_rules(qapp):
    _, win = _window(qapp)
    assert [win._sidebar.tabText(i) for i in range(win._sidebar.count())] == [
        "Moves",
        "Rules",
    ]


def test_developer_info_absent_from_main_ui(qapp):
    _, win = _window(qapp)
    assert "fingerprint" not in win._status_main.text().lower()
    assert "Player 0" not in win._status_main.text()
    assert "Player 1" not in win._status_main.text()
    overview = win._rules_panel._overview.text()
    assert "fingerprint" not in overview.lower()
    assert "seed" not in overview.lower()


def test_diagnostics_dialog_contains_developer_info(qapp):
    from generic_chess.ui.dialogs.diagnostics_dialog import DiagnosticsDialog

    ctrl, win = _window(qapp)
    dialog = DiagnosticsDialog(ctrl, win._tr, win._app_version)
    fingerprint = dialog._labels["diagnostics.ruleset_fingerprint"].text()
    assert ctrl.compiled.ruleset_fingerprint == fingerprint


# ---------------------------------------------------------------------- replay

def test_replay_selects_ply_and_blocks_submission(qapp):
    ctrl, win = _window(qapp)
    pawn = _first_pawn_square(ctrl)
    ctrl.square_clicked(pawn)
    ctrl.square_clicked(ctrl.interaction.legal_actions[0].to_square)
    win._refresh()
    live = ctrl.session.state.ply_count
    assert ctrl.display_ply(1)
    win._refresh()
    selected = win._moves_panel._list.selectedItems()
    assert selected and selected[0].data(Qt.UserRole) == 1
    # Submitting while viewing history must not touch the live session.
    before = ctrl.session.state.ply_count
    ctrl.submit_action(ctrl.session.legal_actions()[0])
    assert ctrl.session.state.ply_count == before
    ctrl.return_to_current()
    win._refresh()
    assert ctrl.session.state.ply_count == live


def test_game_over_hides_to_move(qapp):
    from generic_chess.ai.budget import ThinkingConfig
    from generic_chess.clock import TimeControl, TimeControlMode
    from generic_chess.ui.match import MatchConfig, ParticipantKind

    ctrl, win = _mate_setup(qapp)
    ctrl.start_match(
        MatchConfig(
            (ParticipantKind.HUMAN, ParticipantKind.HUMAN),
            TimeControl(mode=TimeControlMode.NONE),
            ThinkingConfig(),
        )
    )
    ctrl.submit_action(BoardMove(Square(1, 4), Square(0, 4)))
    win._refresh()
    assert ctrl.session.result.status.value == "checkmate"
    assert "Game over" in win._moves_panel._primary.text()
    assert "to move" not in win._status_main.text().lower()


# ---------------------------------------------------------------------- inspect

def test_board_piece_inspect_shows_rules_detail(qapp):
    ctrl, win = _window(qapp)
    pawn = _first_pawn_square(ctrl)
    ctrl.square_clicked(pawn)
    win._refresh()
    type_id = ctrl.piece_info().type_id
    assert type_id in win._rules_panel._detail.text()


def test_inspect_type_switches_to_rules_tab(qapp):
    ctrl, win = _window(qapp)
    win._sidebar.setCurrentIndex(0)
    first = ctrl.compiled.piece_types[0].type_id
    win._inspect_type(first)
    assert win._sidebar.currentWidget() is win._rules_panel
    assert win._rules_panel._types.currentItem() is not None


# ---------------------------------------------------------------- localization

def test_language_switch_updates_main_surfaces(qapp):
    _, win = _window(qapp, language="en")
    assert win._sidebar.tabText(0) == "Moves"
    assert "White" in win._player_bars[0]._name.text()
    win._tr.set_language("ja_JP")
    assert win._sidebar.tabText(0) == "棋譜"
    assert "白" in win._player_bars[0]._name.text()
    assert "Player 0" not in win._player_bars[0]._name.text()


def test_localization_cover_key_surfaces(qapp):
    for language in ("en", "zh_CN", "ja_JP"):
        _, win = _window(qapp, language=language)
        tab = win._sidebar.tabText(0)
        assert tab and tab != "tab.moves"
        assert win._player_bars[0]._name.text()
        assert win._moves_panel._primary.text()


# ------------------------------------------------------------------- player bar

def test_player_bar_flip_swaps_bars_but_not_semantics(qapp):
    ctrl, win = _window(qapp)
    assert win._bar_bottom.owner() == 0
    assert win._bar_top.owner() == 1
    ctrl.flip_board()
    win._refresh()
    assert win._bar_bottom.owner() == 1
    assert win._bar_top.owner() == 0
    assert win._player_bars[0].owner() == 0  # semantics never change
