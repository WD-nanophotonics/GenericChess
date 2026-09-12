"""F88 desktop acceptance through the production UI/controller boundary."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from generic_chess.core.actions import (
    action_is_board,
    action_is_drop,
    action_promotion_target_id,
)
from generic_chess.core.coordinates import Square, square_to_index
from generic_chess.core.identity import position_identity_key
from generic_chess.rules.catalog import build_builtin_ruleset
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.ui.controller import UIController
from generic_chess.ui.dialogs.new_match_dialog import NewMatchDialog
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


def _board_snapshot(controller: UIController) -> tuple:
    position = controller.session.state.position
    return tuple(
        None
        if piece is None
        else (piece.owner, piece.base_type_id, piece.current_type_id, piece.promoted)
        for piece in position.board
    )


def _click_production_action(controller: UIController, action_text: str):
    action = next(
        candidate
        for candidate in controller.session.legal_actions()
        if str(candidate) == action_text
    )
    controller.square_clicked(action.from_square)
    assert action in controller.interaction.legal_actions
    controller.square_clicked(action.to_square)
    assert controller.history_entries()[-1].action == action
    return action


@pytest.mark.parametrize(
    ("index", "name"),
    ((3, "western_chess"), (4, "standard_shogi")),
)
def test_new_match_dialog_selects_each_production_builtin(qapp, index, name):
    dialog = NewMatchDialog(DictSettingsStore())
    dialog._source.setCurrentIndex(index)
    dialog._accept()
    request = dialog.request()
    assert request is not None
    assert request.ruleset_mode == "builtin"
    assert request.builtin_name == name
    dialog.close()


@pytest.mark.parametrize("name", ("western_chess", "standard_shogi"))
def test_builtin_desktop_action_projection_invalid_input_and_reset(qapp, name):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    settings.set(KEY_ENABLE_ANIMATIONS, False)
    controller = UIController(settings=settings)
    assert controller.new_game(seed=42)
    window = MainWindow(controller, settings)
    window.show()
    qapp.processEvents()

    dialog = NewMatchDialog(settings)
    dialog._source.setCurrentIndex(3 if name == "western_chess" else 4)
    dialog._accept()
    request = dialog.request()
    assert request is not None
    window._apply_new_match(request)
    dialog.close()

    initial_key = position_identity_key(
        controller.session.state.position, controller.compiled
    )
    initial_board = _board_snapshot(controller)
    initial_fingerprint = controller.compiled.ruleset_fingerprint
    action = next(a for a in controller.session.legal_actions() if action_is_board(a))

    # The click path resolves the exact semantic action supplied by production
    # legal_actions; no test-only engine or second legality implementation is used.
    controller.square_clicked(action.from_square)
    assert controller.interaction.selected_square == action.from_square
    assert action in controller.interaction.legal_actions

    position = controller.session.state.position
    legal_targets = {candidate.to_square for candidate in controller.interaction.legal_actions}
    invalid_target = next(
        Square(index % position.board_size(), index // position.board_size())
        for index, piece in enumerate(position.board)
        if piece is None
        and Square(index % position.board_size(), index // position.board_size())
        not in legal_targets
    )
    controller.square_clicked(invalid_target)
    assert controller.session.state.ply_count == 0
    assert position_identity_key(controller.session.state.position, controller.compiled) == initial_key
    assert _board_snapshot(controller) == initial_board

    controller.square_clicked(action.to_square)
    window._refresh()
    assert controller.session.state.ply_count == 1
    assert controller.compiled.ruleset_fingerprint == initial_fingerprint
    assert position_identity_key(controller.session.state.position, controller.compiled) != initial_key

    model = controller.board_view_model()
    assert model is not None
    assert model.side_to_move == controller.session.state.position.side_to_move
    assert all(
        view_square.piece
        == controller.session.state.position.board[
            square_to_index(view_square.square, controller.session.state.position.board_size())
        ]
        for view_square in model.squares
    )
    assert window._scene.rendered_occupancy() == {
        view_square.square: (
            view_square.piece.owner,
            view_square.piece.base_type_id,
            view_square.piece.current_type_id,
            view_square.piece.promoted,
        )
        for view_square in model.squares
        if view_square.piece is not None
    }

    # Restart is the desktop action's reset path and must restore semantic and
    # projected state together while keeping the selected built-in ruleset.
    window._restart()
    window._refresh()
    assert controller.session.state.ply_count == 0
    assert controller.history_entries() == ()
    assert position_identity_key(controller.session.state.position, controller.compiled) == initial_key
    assert _board_snapshot(controller) == initial_board
    assert controller.compiled.ruleset_fingerprint == initial_fingerprint
    assert window._scene.rendered_occupancy() == {
        view_square.square: (
            view_square.piece.owner,
            view_square.piece.base_type_id,
            view_square.piece.current_type_id,
            view_square.piece.promoted,
        )
        for view_square in controller.board_view_model().squares
        if view_square.piece is not None
    }
    assert not any(
        view_square.is_last_move_from or view_square.is_last_move_to
        for view_square in controller.board_view_model().squares
    )


def test_standard_shogi_desktop_semantic_drop(qapp):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    settings.set(KEY_ENABLE_ANIMATIONS, False)
    controller = UIController(settings=settings)
    assert controller.new_game_from_builtin("standard_shogi")
    window = MainWindow(controller, settings)
    window.show()
    qapp.processEvents()

    # This short deterministic opening is selected from production legal
    # actions, then submitted only through the desktop click path.
    opening = (
        "legacy_028:g21:e3-e4",
        "legacy_028:g21:e7-e6",
        "legacy_028:g21:e4-e5",
        "legacy_029:g21:e6-e5",
        "legacy_028:g21:f3-f4",
        "legacy_028:g21:e5-e4",
        "legacy_028:g21:f4-f5",
        "legacy_028:g21:f7-f6",
        "legacy_029:g21:f5-f6",
        "legacy_028:g21:d7-d6",
        "legacy_028:g21:d3-d4",
        "legacy_028:g21:d6-d5",
        "legacy_029:g21:d4-d5",
        "legacy_028:g21:g7-g6",
        "legacy_028:g21:d5-d6",
        "legacy_026:g20:h9-g7",
        "legacy_028:g21:g3-g4",
        "legacy_026:g20:g7-f5",
        "legacy_002:g1:h2-e5",
        "legacy_028:g21:g6-g5",
        "legacy_022:g19:h1-g3",
        "legacy_029:g21:g5-g4",
    )
    for action_text in opening:
        _click_production_action(controller, action_text)
    capture_text = "legacy_023:g19:g3-f5"
    capture = next(
        action
        for action in controller.session.legal_actions()
        if str(action) == capture_text
    )
    captured_type = controller.session.state.position.board[
        square_to_index(capture.to_square, controller.compiled.board_size)
    ].base_type_id
    _click_production_action(controller, capture_text)
    assert controller.session.state.position.hands[0].count(captured_type) > 0
    window._refresh()

    # The existing PlayerBar hand button is the production drop entry point.
    buttons = window._player_bars[0].hand_buttons()
    assert buttons
    assert any(captured_type in button.text() for button in buttons)

    reply = next(
        action
        for action in sorted(controller.session.legal_actions(), key=str)
        if action_is_board(action) and action_promotion_target_id(action) is None
    )
    _click_production_action(controller, str(reply))
    window._refresh()
    drop_button = next(
        button for button in window._player_bars[0].hand_buttons()
        if captured_type in button.text()
    )
    drop_button.click()
    assert controller.interaction.legal_actions
    drop = next(
        action for action in controller.interaction.legal_actions if action_is_drop(action)
    )
    before_key = position_identity_key(
        controller.session.state.position, controller.compiled
    )
    controller.square_clicked(drop.to_square)
    window._refresh()

    assert controller.session.state.position.hands[0].count(captured_type) == 0
    assert controller.history_entries()[-1].action == drop
    assert position_identity_key(
        controller.session.state.position, controller.compiled
    ) != before_key
    model = controller.board_view_model()
    assert model is not None
    placed = next(square for square in model.squares if square.square == drop.to_square)
    assert placed.piece is not None and placed.piece.owner == 0
    assert window._scene.rendered_occupancy()[drop.to_square] == (
        placed.piece.owner,
        placed.piece.base_type_id,
        placed.piece.current_type_id,
        placed.piece.promoted,
    )


@pytest.mark.parametrize("name", ("western_chess", "standard_shogi"))
def test_builtin_ruleset_file_load_keeps_semantic_actions(tmp_path, name):
    path = tmp_path / f"{name}.json"
    path.write_text(serialize_ruleset(build_builtin_ruleset(name)), encoding="utf-8")
    controller = UIController(DictSettingsStore())
    assert controller.open_ruleset(str(path))
    assert controller.session is not None
    assert controller.session.legal_actions()
    assert all(action_is_board(action) for action in controller.session.legal_actions())
