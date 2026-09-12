"""F90 persistence acceptance for production built-in records."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json

import pytest
from PySide6.QtWidgets import QApplication

from generic_chess.core.actions import action_is_board
from generic_chess.core.identity import position_identity_key
from generic_chess.rules.catalog import build_builtin_ruleset
from generic_chess.session.serialization import serialize_game_record
from generic_chess.ui.controller import UIController
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.settings import KEY_ENABLE_ANIMATIONS, KEY_LANGUAGE
from generic_chess.ui.stores import DictSettingsStore


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _close_windows(qapp):
    yield
    for widget in list(qapp.topLevelWidgets()):
        if isinstance(widget, MainWindow):
            widget._shutdown()
            widget.close()
            widget.deleteLater()
    qapp.processEvents()


def _occupancy(controller: UIController) -> dict:
    model = controller.board_view_model()
    assert model is not None
    return {
        square.square: (
            square.piece.owner,
            square.piece.base_type_id,
            square.piece.current_type_id,
            square.piece.promoted,
        )
        for square in model.squares
        if square.piece is not None
    }


def _submit_two_production_actions(controller: UIController) -> None:
    for _ in range(2):
        action = next(action for action in controller.session.legal_actions() if action_is_board(action))
        controller.square_clicked(action.from_square)
        assert action in controller.interaction.legal_actions
        controller.square_clicked(action.to_square)
        assert controller.history_entries()[-1].action == action


@pytest.mark.parametrize(
    ("saved_name", "current_name"),
    (("western_chess", "standard_shogi"), ("standard_shogi", "western_chess")),
)
def test_builtin_record_reopens_after_switching_builtins(qapp, tmp_path, saved_name, current_name):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    settings.set(KEY_ENABLE_ANIMATIONS, False)
    controller = UIController(settings=settings)
    assert controller.new_game_from_builtin(saved_name)
    window = MainWindow(controller, settings)
    window.show()
    qapp.processEvents()

    _submit_two_production_actions(controller)
    saved_actions = tuple(entry.action for entry in controller.session.history)
    saved_key = position_identity_key(controller.session.state.position, controller.compiled)
    saved_fingerprint = controller.compiled.ruleset_fingerprint
    path = tmp_path / f"{saved_name}.json"
    assert controller.save_record(str(path))

    assert controller.new_game_from_builtin(current_name)
    assert controller.compiled.ruleset_fingerprint != saved_fingerprint
    assert controller.open_record(str(path))
    window._refresh()

    assert controller.compiled.ruleset_fingerprint == saved_fingerprint
    assert tuple(entry.action for entry in controller.session.history) == saved_actions
    assert position_identity_key(controller.session.state.position, controller.compiled) == saved_key
    assert _occupancy(controller) == window._scene.rendered_occupancy()


def test_unknown_record_fingerprint_fails_closed_without_mutation(qapp, tmp_path):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    controller = UIController(settings=settings)
    assert controller.new_game_from_builtin("western_chess")
    path = tmp_path / "unknown.json"
    payload = json.loads(serialize_game_record(controller.session.to_record()))
    payload["ruleset_fingerprint"] = "f" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")

    before_fingerprint = controller.compiled.ruleset_fingerprint
    before_key = position_identity_key(controller.session.state.position, controller.compiled)
    before_history = controller.history_entries()
    assert not controller.open_record(str(path))
    assert "not a production built-in" in controller.last_error
    assert controller.compiled.ruleset_fingerprint == before_fingerprint
    assert position_identity_key(controller.session.state.position, controller.compiled) == before_key
    assert controller.history_entries() == before_history
