"""Round 2 acceptance tests for the persistent Qt board renderer."""

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.ui.controller import UIController
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.settings import KEY_ENABLE_ANIMATIONS, KEY_LANGUAGE
from generic_chess.ui.stores import DictSettingsStore

from conftest import T, king_type, make_ruleset


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _qt_cleanup(qapp):
    baseline = set(qapp.topLevelWidgets())
    yield
    for widget in list(qapp.topLevelWidgets()):
        if widget in baseline:
            continue
        if isinstance(widget, MainWindow):
            widget._shutdown()
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qapp.processEvents()


def _window(qapp, *, animations=False, ruleset=None):
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    settings.set(KEY_ENABLE_ANIMATIONS, animations)
    ctrl = UIController(settings=settings)
    if ruleset is None:
        assert ctrl.new_game(seed=42)
    else:
        assert ctrl.new_game_from_ruleset(ruleset)
    win = MainWindow(ctrl, settings)
    win.show()
    qapp.processEvents()
    return ctrl, win


def _occupancy(model):
    return {
        item.square: (
            item.piece.owner,
            item.piece.base_type_id,
            item.piece.current_type_id,
            item.piece.promoted,
        )
        for item in model.squares
        if item.piece is not None
    }


def _assert_exact(win, ctrl):
    assert win._scene.rendered_occupancy() == _occupancy(ctrl.board_view_model())
    assert win._scene.effect_item_count() == 0


def _first_legal_move(ctrl):
    return next(action for action in ctrl.session.legal_actions() if isinstance(action, BoardMove))


def _wait_until_idle(qapp, win, timeout_ms=1200):
    deadline = time.monotonic() + timeout_ms / 1000
    while win._scene.motion_active() and time.monotonic() < deadline:
        qapp.processEvents()
        QTest.qWait(5)
    qapp.processEvents()
    assert not win._scene.motion_active()


def _capture_ruleset():
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    filler = T("F", LeapAtom((1, 0)))
    return make_ruleset(
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


def _promotion_ruleset():
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    gold = T("G", LeapAtom((1, 0)), LeapAtom((-1, 0)), LeapAtom((0, -1)))
    return make_ruleset(
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


def test_static_and_piece_identity_survive_refreshes(qapp):
    ctrl, win = _window(qapp)
    scene = win._scene
    squares = {square: id(item) for square, item in scene._square_items.items()}
    coordinates = {key: id(item) for key, item in scene._coordinate_items.items()}
    pieces = {square: id(item) for square, item in scene.piece_items().items()}

    ctrl.cancel()
    win._scene.set_hover(Square(0, 0))
    win._clock_tick()
    win._refresh()

    assert squares == {square: id(item) for square, item in scene._square_items.items()}
    assert coordinates == {key: id(item) for key, item in scene._coordinate_items.items()}
    assert pieces == {square: id(item) for square, item in scene.piece_items().items()}
    ctrl.flip_board()
    assert squares == {square: id(item) for square, item in scene._square_items.items()}
    assert coordinates == {key: id(item) for key, item in scene._coordinate_items.items()}
    assert pieces == {square: id(item) for square, item in scene.piece_items().items()}
    _assert_exact(win, ctrl)


def test_mover_and_unrelated_piece_identity_are_preserved(qapp):
    ctrl, win = _window(qapp)
    source = next(
        item.square
        for item in ctrl.board_view_model().squares
        if item.piece is not None and item.piece.owner == 0 and item.piece.base_type_id == "P"
    )
    action = next(a for a in ctrl.session.legal_actions() if a.from_square == source)
    unrelated_square = next(
        item.square for item in ctrl.board_view_model().squares
        if item.piece is not None and item.square != source
    )
    mover = win._scene.piece_item_at(source)
    unrelated = win._scene.piece_item_at(unrelated_square)
    assert ctrl.submit_action(action)
    destination = action.to_square
    assert win._scene.piece_item_at(destination) is mover
    assert win._scene.piece_item_at(unrelated_square) is unrelated
    assert win._scene.piece_item_at(source) is None
    _assert_exact(win, ctrl)


def test_capture_drop_and_promotion_have_exact_final_occupancy(qapp):
    ctrl, win = _window(qapp, ruleset=_capture_ruleset())
    rook = win._scene.piece_item_at(Square(1, 0))
    assert ctrl.submit_action(BoardMove(Square(1, 0), Square(2, 0)))
    assert win._scene.piece_item_at(Square(2, 0)) is rook
    _assert_exact(win, ctrl)

    assert ctrl.submit_action(ctrl.session.legal_actions()[0])
    drop = next(a for a in ctrl.session.legal_actions() if isinstance(a, DropMove))
    assert ctrl.submit_action(drop)
    _assert_exact(win, ctrl)

    ctrl2, win2 = _window(qapp, ruleset=_promotion_ruleset())
    pawn = win2._scene.piece_item_at(Square(4, 6))
    assert ctrl2.submit_action(BoardMove(Square(4, 6), Square(4, 7), "G"))
    assert win2._scene.piece_item_at(Square(4, 7)) is pawn
    assert pawn.piece.promoted is True
    _assert_exact(win2, ctrl2)


def test_animation_is_bounded_and_cancel_safe(qapp):
    ctrl, win = _window(qapp, animations=True)
    action = _first_legal_move(ctrl)
    assert ctrl.submit_action(action)
    qapp.processEvents()
    assert win._scene.motion_active()
    assert not win._board_view.input_enabled()

    # A second authoritative move queues at most one adjacent transition.
    second = _first_legal_move(ctrl)
    assert ctrl.submit_action(second)
    assert win._scene.motion_active()
    assert win._scene._pending_model is not None
    _wait_until_idle(qapp, win)
    _assert_exact(win, ctrl)

    # A history preview is an atomic snap and invalidates the old callback.
    action3 = _first_legal_move(ctrl)
    assert ctrl.submit_action(action3)
    assert win._scene.motion_active()
    assert ctrl.display_ply(0)
    qapp.processEvents()
    assert not win._scene.motion_active()
    assert win._board_view.input_enabled()
    _assert_exact(win, ctrl)


def test_close_during_animation_and_item_counts_remain_bounded(qapp):
    ctrl, win = _window(qapp, animations=True)
    initial_count = win._scene.piece_item_count()
    assert ctrl.submit_action(_first_legal_move(ctrl))
    qapp.processEvents()
    assert win._scene.motion_active()
    win._shutdown()
    qapp.processEvents()
    assert not win._scene.motion_active()
    assert win._scene.effect_item_count() == 0
    assert win._scene.piece_item_count() <= initial_count
