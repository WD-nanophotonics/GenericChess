"""F89 desktop acceptance through the real Human-vs-AI worker path."""

from __future__ import annotations

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from generic_chess.ai.budget import ThinkingConfig, ThinkingStrategy
from generic_chess.clock import TimeControl, TimeControlMode
from generic_chess.core.actions import (
    SemanticBoardMove,
    SemanticDropMove,
    action_is_board,
    action_promotion_target_id,
)
from generic_chess.core.identity import position_identity_key
from generic_chess.core.coordinates import Square
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import (
    deserialize_game_record,
    serialize_game_record,
)
from generic_chess.ui.controller import UIController
from generic_chess.ui.dialogs.new_match_dialog import NewMatchRequest
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.match import ParticipantKind
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


def _semantic_occupancy(session: GameSession) -> dict:
    position = session.state.position
    board_size = position.board_size()
    return {
        Square(index % board_size, index // board_size): (
            piece.owner,
            piece.base_type_id,
            piece.current_type_id,
            piece.promoted,
        )
        for index, piece in enumerate(position.board)
        if piece is not None
    }


def _first_unambiguous_board_action(controller: UIController):
    legal_actions = controller.session.legal_actions()
    promotion_pairs = {
        (action.from_square, action.to_square)
        for action in legal_actions
        if action_is_board(action) and action_promotion_target_id(action) is not None
    }
    return next(
        action
        for action in legal_actions
        if action_is_board(action)
        and action_promotion_target_id(action) is None
        and (action.from_square, action.to_square) not in promotion_pairs
    )


@pytest.mark.parametrize("name", ("western_chess", "standard_shogi"))
def test_builtin_desktop_real_ai_reply(qapp, name):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    settings.set(KEY_ENABLE_ANIMATIONS, False)
    controller = UIController(settings=settings)
    assert controller.new_game_from_builtin(name)
    window = MainWindow(controller, settings)
    window.show()
    qapp.processEvents()

    request = NewMatchRequest(
        ruleset_mode="builtin",
        participants=(ParticipantKind.HUMAN, ParticipantKind.AI),
        time_control=TimeControl(mode=TimeControlMode.NONE),
        ai_config=ThinkingConfig(
            strategy=ThinkingStrategy.FIXED_NODES,
            preset="quick",
            max_nodes=500,
            max_depth=2,
        ),
        builtin_name=name,
    )
    window._apply_new_match(request)
    assert controller.match_config is not None
    assert controller.match_config.participants == (
        ParticipantKind.HUMAN,
        ParticipantKind.AI,
    )

    human_action = _first_unambiguous_board_action(controller)
    controller.square_clicked(human_action.from_square)
    assert human_action in controller.interaction.legal_actions
    controller.square_clicked(human_action.to_square)
    assert controller.history_entries()[-1].action == human_action
    assert controller.session.state.ply_count == 1

    ai_root_key = position_identity_key(
        controller.session.state.position, controller.compiled
    )
    ai_root_actions = tuple(controller.session.legal_actions())
    window._refresh()

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        qapp.processEvents()
        if controller.session.state.ply_count == 2 and not controller.ai_thinking:
            break
        time.sleep(0.02)

    assert window._ai_error is None
    assert window._ai_thread is None
    assert not controller.ai_thinking
    assert controller.session.state.ply_count == 2
    assert controller.session.state.position.side_to_move == 0
    assert position_identity_key(
        controller.session.state.position, controller.compiled
    ) != ai_root_key

    ai_action = controller.history_entries()[-1].action
    assert isinstance(ai_action, (SemanticBoardMove, SemanticDropMove))
    assert ai_action in ai_root_actions
    live_actions = tuple(entry.action for entry in controller.session.history)
    replayed = GameSession.replay(
        controller.compiled,
        deserialize_game_record(serialize_game_record(controller.session.to_record())),
    )
    assert tuple(entry.action for entry in replayed.history) == live_actions
    assert _semantic_occupancy(replayed) == _semantic_occupancy(controller.session)
    assert replayed.state.position.side_to_move == controller.session.state.position.side_to_move
    assert tuple(hand.counts for hand in replayed.state.position.hands) == tuple(
        hand.counts for hand in controller.session.state.position.hands
    )
    assert position_identity_key(
        replayed.state.position, controller.compiled
    ) == position_identity_key(controller.session.state.position, controller.compiled)
    assert _occupancy(controller) == window._scene.rendered_occupancy()
    assert _semantic_occupancy(controller.session) == _occupancy(controller)
