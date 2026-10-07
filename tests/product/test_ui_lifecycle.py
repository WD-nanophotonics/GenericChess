"""Deterministic UI lifecycle regression tests (native-crash fix).

These tests freeze the window ownership contract that prevents the
accumulated-window cyclic-GC batch destruction: timers are stopped,
controller/localization subscriptions are removed, AI threads are
cancelled/waited, and repeated create/close cycles must not accumulate
top-level widgets.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from generic_chess.ui.controller import UIController
from generic_chess.ui.main_window import MainWindow
from generic_chess.ui.settings import KEY_LANGUAGE
from generic_chess.ui.stores import DictSettingsStore


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _qt_cleanup(qapp):
    import gc

    baseline = set(qapp.topLevelWidgets())
    yield
    for widget in list(qapp.topLevelWidgets()):
        if widget in baseline:
            continue
        if isinstance(widget, MainWindow):
            if not widget._shutdown():
                thread = widget._ai_thread
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
    gc.collect()


def _make_window():
    settings = DictSettingsStore()
    settings.set(KEY_LANGUAGE, "en")
    ctrl = UIController(settings=settings)
    assert ctrl.new_game(seed=42)
    win = MainWindow(ctrl, settings)
    win.show()
    return ctrl, win


def _flush(qapp) -> None:
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qapp.processEvents()


def _main_windows(qapp) -> list:
    return [w for w in qapp.topLevelWidgets() if isinstance(w, MainWindow)]


def test_shutdown_stops_clock_timer(qapp):
    _ctrl, win = _make_window()
    assert win._clock_timer.isActive()
    win._shutdown()
    assert not win._clock_timer.isActive()


def test_shutdown_removes_controller_subscription(qapp):
    ctrl, win = _make_window()
    assert win._refresh in ctrl._listeners
    win._shutdown()
    assert win._refresh not in ctrl._listeners
    # idempotent; absent callbacks are ignored
    ctrl.unsubscribe(win._refresh)
    ctrl.unsubscribe(lambda: None)


def test_shutdown_removes_localization_subscription(qapp):
    _ctrl, win = _make_window()
    assert win._on_language_changed in win._tr._listeners
    win._shutdown()
    assert win._on_language_changed not in win._tr._listeners
    win._tr.unsubscribe(win._on_language_changed)


def test_shutdown_is_idempotent(qapp):
    ctrl, win = _make_window()
    win._shutdown()
    win._shutdown()  # second call must be a no-op
    assert not win._clock_timer.isActive()
    assert win._refresh not in ctrl._listeners


def test_close_flushes_window(qapp):
    import shiboken6

    _ctrl, win = _make_window()
    win.close()
    win.deleteLater()
    _flush(qapp)
    assert not shiboken6.isValid(win)
    assert _main_windows(qapp) == []


def test_repeated_create_close_does_not_accumulate_windows(qapp):
    for _ in range(30):
        _ctrl, win = _make_window()
        win._shutdown()
        win.close()
        win.deleteLater()
        _flush(qapp)
        assert _main_windows(qapp) == []


def test_shutdown_does_not_start_new_ai(qapp):
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
            TimeControl(mode=TimeControlMode.NONE),
            ThinkingConfig(strategy="fixed_nodes", preset="quick"),
        )
    )
    win._ai_player = object()  # would otherwise be enough to start a thread
    win._shutdown()
    win._maybe_start_ai()
    assert win._ai_thread is None


def test_shutdown_cancels_and_waits_owned_ai_thread(qapp):
    import time as _time

    from generic_chess.ai.budget import ThinkingConfig, ThinkingStrategy
    from generic_chess.clock import TimeControl, TimeControlMode
    from generic_chess.ui.match import MatchConfig, ParticipantKind

    class SlowPlayer:
        def choose_action(
            self, session, limits, cancel_token=None, progress_callback=None
        ):
            while cancel_token is None or not cancel_token.is_cancelled():
                _time.sleep(0.02)
            return type(
                "Decision",
                (),
                {
                    "action": None,
                    "score": 0,
                    "principal_variation": (),
                    "completed_depth": 0,
                    "selective_depth": 0,
                    "nodes": 0,
                    "qnodes": 0,
                    "elapsed_seconds": 0.0,
                    "tt_probes": 0,
                    "tt_hits": 0,
                    "tt_cutoffs": 0,
                    "beta_cutoffs": 0,
                    "evaluation_profile_cache_hit": False,
                    "termination_reason": "cancelled",
                },
            )()

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
    thread = win._ai_thread
    assert thread is not None
    win._shutdown()
    assert not thread.isRunning()
    assert win._ai_thread is None
    assert not ctrl.ai_thinking


def test_shutdown_retains_running_thread_reference_after_timeout(qapp):
    """A non-cooperative worker that outlives the bounded wait must keep its
    owned reference; the window must not lose the running QThread."""
    import time as _time

    from PySide6.QtCore import QThread

    class StubbornThread(QThread):
        """Stays alive until the test releases it (ignores interruption)."""

        def __init__(self):
            super().__init__()
            self._release = False

        def run(self):
            while not self._release:
                _time.sleep(0.02)

        def release(self):
            self._release = True

    ctrl, win = _make_window()
    thread = StubbornThread()
    thread.start()
    win._ai_thread = thread
    try:
        assert win._shutdown() is False
        # timeout path: the running thread reference must be retained
        assert win._ai_thread is thread
        assert thread.isRunning()
    finally:
        thread.release()
        thread.wait(5000)
        assert not thread.isRunning()
        win._ai_thread = None
        assert win._shutdown() is True
        assert not ctrl.ai_thinking
