"""Focused regression coverage for the Round 3 corrective audit."""

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QFileDialog

from generic_chess.ai.budget import ThinkingConfig
from generic_chess.clock import SideTimeConfig, TimeControl, TimeControlMode
from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from generic_chess.ui.controller import UIController
from generic_chess.ui.dialogs.new_match_dialog import NewMatchDialog
from generic_chess.ui.i18n.manager import LocalizationManager
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.match import MatchConfig, ParticipantKind
from generic_chess.ui.settings import KEY_ENABLE_ANIMATIONS, KEY_LANGUAGE
from generic_chess.ui.stores import DictSettingsStore

from test_ui_persistent_renderer import _capture_ruleset, _first_legal_move, _wait_until_idle

import pytest


def _interaction_snapshot(model):
    return {
        sv.square: (
            sv.is_last_move_from,
            sv.is_last_move_to,
            sv.is_selected,
            sv.is_legal_move,
            sv.is_legal_capture,
            sv.is_preview,
            sv.is_check_anchor,
        )
        for sv in model.squares
        if (
            sv.is_last_move_from
            or sv.is_last_move_to
            or sv.is_selected
            or sv.is_legal_move
            or sv.is_legal_capture
            or sv.is_preview
            or sv.is_check_anchor
        )
    }


def _window(qapp, *, animations=False, language="en", ruleset=None, now=None):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, language)
    settings.set(KEY_ENABLE_ANIMATIONS, animations)
    ctrl = UIController(settings=settings, clock_now=now)
    if ruleset is not None:
        assert ctrl.new_game_from_ruleset(ruleset)
    else:
        assert ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    win.show()
    qapp.processEvents()
    return ctrl, win


def _close_windows(qapp, baseline):
    for widget in list(qapp.topLevelWidgets()):
        if widget in baseline:
            continue
        if isinstance(widget, MainWindow):
            widget._shutdown()
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qapp.processEvents()


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _qt_cleanup(qapp):
    baseline = set(qapp.topLevelWidgets())
    yield
    _close_windows(qapp, baseline)


def test_animation_completion_refreshes_final_interaction_layer(qapp):
    ctrl, win = _window(qapp, animations=True)
    source_model = ctrl.board_view_model()
    action = _first_legal_move(ctrl)
    ctrl.square_clicked(action.from_square)
    selected_model = ctrl.board_view_model()
    assert selected_model is not None
    assert selected_model != source_model
    assert win._scene.interaction_snapshot() == _interaction_snapshot(selected_model)

    ctrl.square_clicked(action.to_square)
    target = ctrl.board_view_model()
    assert target is not None
    _wait_until_idle(qapp, win)

    assert win._scene.rendered_occupancy()
    assert win._scene.interaction_snapshot() == _interaction_snapshot(target)
    assert not win._scene.motion_active()
    assert win._board_view.input_enabled()
    assert not any(sv.is_selected or sv.is_legal_move or sv.is_legal_capture for sv in target.squares)


def test_queued_animation_refreshes_each_completed_target(qapp):
    ctrl, win = _window(qapp, animations=True)
    seen = []
    original_refresh = win._scene._refresh_interaction

    def record(model):
        seen.append(model)
        original_refresh(model)

    win._scene._refresh_interaction = record
    assert ctrl.submit_action(_first_legal_move(ctrl))
    first_target = ctrl.board_view_model()
    assert ctrl.submit_action(_first_legal_move(ctrl))
    second_target = ctrl.board_view_model()
    _wait_until_idle(qapp, win)

    assert first_target in seen
    assert second_target in seen
    assert win._scene.interaction_snapshot() == _interaction_snapshot(second_target)


def _nav_state(panel):
    return (
        panel._btn_first.isEnabled(),
        panel._btn_prev.isEnabled(),
        panel._btn_next.isEnabled(),
        panel._btn_last.isEnabled(),
        panel._return_btn.isEnabled(),
    )


def test_replay_controls_follow_live_and_history_matrix_and_clicks(qapp):
    ctrl, win = _window(qapp, animations=False)
    panel = win._moves_panel
    assert _nav_state(panel) == (False, False, False, False, False)

    assert ctrl.submit_action(_first_legal_move(ctrl))
    assert ctrl.submit_action(_first_legal_move(ctrl))
    assert _nav_state(panel) == (True, True, False, False, False)

    panel._btn_prev.click()
    assert ctrl.interaction.displayed_ply == 1
    assert _nav_state(panel) == (True, True, True, True, True)
    panel._btn_prev.click()
    assert ctrl.interaction.displayed_ply == 0
    assert _nav_state(panel) == (False, False, True, True, True)

    panel._btn_next.click()
    assert ctrl.interaction.displayed_ply == 1
    panel._btn_last.click()
    assert ctrl.interaction.displayed_ply == 2
    assert _nav_state(panel) == (True, True, False, False, True)
    panel._return_btn.click()
    assert ctrl.interaction.displayed_ply is None
    assert _nav_state(panel) == (True, True, False, False, False)


def test_player_bar_clock_ticks_without_full_refresh_or_rebuild(qapp):
    class FakeNow:
        value = 100.0

        def __call__(self):
            return self.value

    now = FakeNow()
    ctrl, win = _window(qapp, animations=False, ruleset=_capture_ruleset(), now=now)
    ctrl.start_match(
        MatchConfig(
            participants=(ParticipantKind.HUMAN, ParticipantKind.HUMAN),
            time_control=TimeControl(
                mode=TimeControlMode.FISCHER,
                owner0=SideTimeConfig(10, 0),
                owner1=SideTimeConfig(10, 0),
            ),
            ai_config=ThinkingConfig(),
        )
    )
    assert ctrl.submit_action(BoardMove(Square(1, 0), Square(2, 0)))
    bar0 = win._player_bars[0]
    bar1 = win._player_bars[1]
    button_ids = [id(button) for button in bar0.hand_buttons()]
    piece_ids = {square: id(item) for square, item in win._scene.piece_items().items()}
    transform = win._board_view.transform()
    before = (bar0._clock.text(), bar1._clock.text())
    refresh_calls = []
    win._refresh = lambda: refresh_calls.append(True)

    now.value += 2.0
    win._clock_tick()

    assert (bar0._clock.text(), bar1._clock.text()) != before
    assert [id(button) for button in bar0.hand_buttons()] == button_ids
    assert {square: id(item) for square, item in win._scene.piece_items().items()} == piece_ids
    assert win._board_view.transform() == transform
    assert refresh_calls == []


@pytest.mark.parametrize(
    ("language", "labels"),
    (
        ("en", ("Classic-like", "Bilateral random", "Free random")),
        ("zh_CN", ("经典类", "双边随机", "完全随机")),
        ("ja_JP", ("クラシック系", "双方向ランダム", "自由ランダム")),
    ),
)
def test_preset_labels_are_localized_but_request_keeps_backend_id(qapp, language, labels):
    dialog = NewMatchDialog(DictSettingsStore(), tr=LocalizationManager(language))
    assert tuple(dialog._preset.itemText(i) for i in range(3)) == labels
    assert tuple(dialog._preset.itemData(i) for i in range(3)) == (
        "classic_like",
        "bilateral_random",
        "free_random",
    )
    dialog._source.setCurrentIndex(1)
    dialog._preset.setCurrentIndex(1)
    dialog._accept()
    assert dialog.request().preset == "bilateral_random"
    dialog.close()


def test_file_dialog_filters_use_localized_key_for_all_record_surfaces(qapp, monkeypatch):
    for language in ("en", "zh_CN", "ja_JP"):
        ctrl, win = _window(qapp, language=language)
        filters = []

        def open_file(*args):
            filters.append(args[3])
            return "", ""

        def save_file(*args):
            filters.append(args[3])
            return "", ""

        monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(open_file))
        monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(save_file))
        win._open_ruleset()
        win._open_record()
        win._save_record_as()
        assert filters == [win._tr.text("new_match.json_files")] * 3
        win.close()


def test_localization_tables_contain_corrective_keys():
    base = Path(__file__).resolve().parents[1] / "generic_chess" / "ui" / "i18n"
    for language in ("en", "zh_CN", "ja_JP"):
        table = json.loads((base / f"{language}.json").read_text(encoding="utf-8"))
        assert table["new_match.json_files"]
        assert table["new_match.preset_classic_like"]
        assert table["new_match.preset_bilateral_random"]
        assert table["new_match.preset_free_random"]
